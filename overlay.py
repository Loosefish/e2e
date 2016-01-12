#!/usr/bin/python3

'''The overlay module takes care of joining, managing and searching the
Gnutella-like overlay.'''

import threading
import socket
import logging
import queue
import uuid

from signalqueue import QueueSet
import proto

N_NEIGHBOURS = 2    # number of neighbours every node tries to have

class Overlay(threading.Thread):

    def __init__(self, listenaddress, entrypeers):
        self.logger = logging.getLogger("overlay")

        self.listenaddress = listenaddress
        self.entrypeers = entrypeers

        self.state = {
            'neighbours': [ ],
            'joining': None,   # has data when we are currently trying to join
        }

        self.queues = QueueSet()
        self.cmdqueue = self.queues.New() # commands by the user

        self.peer_to_queue = dict() # remember which queue was used for
        self.queue_to_peer = dict() #   which peer

        # first connect to the overlay
        if entrypeers is not None:
            self.cmdqueue.put(('join', entrypeers))

        threading.Thread.__init__(self)


    def get_cmd_queue(self):
        '''Returns the queue that can be used by the user to interactively
        issue commands (overlay operations).'''

        return self.cmdqueue


    def run(self):
        # open up our own listen socket
        self.logger.debug('setting up socket...')
        self.listen = socket.socket()
        self.logger.debug('trying to listen on {}...'.format(self.listenaddress))
        self.listen.bind(self.listenaddress)
        self.listen.listen(10)
        self.logger.info('server socket established.')

        self.listenQ = self.queues.New() # the queue that will be used for
                                         # signalling new connections

        self.listen_thread = ConnectionWaiter(self.listen, self.listenQ)
        self.listen_thread.start()
        
        # connect to the overlay
        #  - contact entry servers until one is reachable
        #  - TODO

        while True:
            (inqueue, data) = self.queues.get()

            # determine, what kind of event occured
            if inqueue == self.listenQ:
                # A Peer established a connection to us.
                self.logger.info('new incoming peer connection')

                # create new objects for communication
                new_queue = self.queues.New()
                new_peer = Peer.from_connection(data, new_queue)

                # remember the Peer and the queue
                self.peer_to_queue[new_peer] = new_queue
                self.queue_to_peer[new_queue] = new_peer

                # start the peer thread
                new_peer.start()

            elif inqueue == self.cmdqueue:
                # A command from the user
                self.logger.info('have to execute user command: {}'.format(data))

                (cmd, payload) = data

                if cmd == 'join':
                    # join the overlay using the given entry peers
                    if self.state['joining'] is not None:
                        self.logger.error('already joining, ignore command.')
                        continue

                    if len(self.state['neighbours']) == N_NEIGHBOURS:
                        self.logger.error("already connected, don't join.")
                        continue

                    self.logger.info('joining the overlay...')
                    self.state['joining'] = {
                        'candidates': payload,
                    }

                    new_queue = self.queues.New()
                    good_peer = None
                    for entry_addr in self.state['joining']['candidates'][:]:
                        self.state['joining']['candidates'].remove(entry_addr)
                        try:
                            self.logger.info('trying to join via {}'
                                              .format(entry_addr))
                            new_peer = Peer(entry_addr, new_queue)
                            new_peer.connect()
                            good_peer = new_peer
                            break
                        except OSError as e:
                            self.logger.warning('cannot join via {} ({})'
                                                .format(entry_addr, e))

                    if good_peer is None:
                        self.logger.error('no entry peer available, cannot join')
                        self.state['joining'] = None
                        self.queues.remove(new_queue)
                        continue

                    self.peer_to_queue[good_peer] = new_queue
                    self.queue_to_peer[new_queue] = good_peer
                    good_peer.start()
                    
                    ping_id = str(uuid.uuid4())
                    self.state['joining']['current_entry'] = good_peer
                    self.state['joining']['ping_id'] = ping_id

                    good_peer.send(proto.Ping(ping_id, 3))


                else:
                    self.logger.error('unknown command: {}'.format(cmd))

            elif inqueue in self.queue_to_peer:
                # a message from another peer
                peer = self.queue_to_peer[inqueue]
                self.logger.info('got a message from peer {}: {}'.format(peer, data))

                if data is None:
                    self.logger.info('connection closed by peer')

                    if self.state['joining'] is not None and peer == self.state['joining']['current_entry']:
                        self.logger.error('error joining, entry died')
                        if len(self.state['joining']['candidates']) > 0:
                            self.logger.info('more entries to try...')
                            self.cmdqueue.put(('join',
                                               self.state['joining']['candidates']))
                            self.state['joining'] = None
                        else:
                            self.logger.error('joining finally failed.')

                    del self.peer_to_queue[peer]
                    del self.queue_to_peer[inqueue]

                elif isinstance(data, proto.Ping):
                    self.logger.debug('got a PING message!')
                    # TODO dict etc.

            else:
                self.logger.error('unknown input: {}'.format(data))


class ConnectionWaiter(threading.Thread):
    '''Thread that accepts connections on a listen socket and returns them via
    a queue.'''

    def __init__(self, sock, q):
        self.logger = logging.getLogger('listening-socket')
        self.sock = sock
        self.q = q

        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
                (conn,addr) = self.sock.accept()
                self.logger.debug('new TCP connection from {}'.format(addr))

                self.q.put(conn)
            except OSError as e:
                self.logger.exception(e)


class Peer(threading.Thread): # TODO differentiate sending/receiving socket ???
    def __init__(self, address, inbox, reuse_socket=None):
        self.address = address
        self.logger = logging.getLogger('peer.{}'.format(self.address))

        self.socket_lock = threading.Lock()

        self.inbox = inbox # the queue object to store incoming messages in

        if reuse_socket is not None:
            self.sock = reuse_socket
            self.state = "connected"
        else:
            self.sock = None # the socket used for communication
            self.state = "disconnected"

        threading.Thread.__init__(self)


    @staticmethod
    def from_connection(conn, inbox):
        '''Construct a Peer object from an already-established connection, e.g.
        after accepting it from a listening socket.'''

        return Peer(conn.getpeername(), inbox, reuse_socket=conn)


    def connect(self):
        if self.address is None:
            raise ValueError('cannot connect to peer without address')
        if self.state != "disconnected":
            self.logger.warning('peer is already connected')
            return

        self.state = "connecting"
        with self.socket_lock:
            try:
                self.sock = socket.socket() # defaults to IPv4 TCP
                self.sock.connect(self.address)
            except OSError:
                self.sock = None
                self.state = "disconnected"
                raise

            self.state = "connected"


    def get_state(self):
        return state


    def send(self, message):
        '''Send a protocol message to the remote peer'''

        # TODO handle blocking calls -> may lead to a global deadlock, because
        # it's the big overlay handler thread that is blocking here!
        try:
            self.sock.send(bytes(message) + b'\n')
        except OSError as e:
            # do not propagate this error, the reveiver part will report an
            # error if the connection was closed (we don't handle half-closed
            # connctions as we don't "use" them)
            self.logger.exception(e)

    
    def run(self):
        '''Run to infinity, reading lines from the socket and putting them as
        protocol messages into the given inbox queue.'''

        # TODO evaluate if we need synchronisation with writers here.
        # If so, use selectors and only read (and lock!) when there is
        # something to read.

        msg = bytes()
        while True:
            data = self.sock.recv(1) # TODO more efficient, buffering
            
            if data is None or len(data) == 0:
                self.logger.info('TCP connection was closed')
                self.inbox.put(None)
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                return

            if data == b'\n':
                parsed = proto.parse(msg)
                self.inbox.put(parsed)
                msg = bytes()

                if parsed is None:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    return
            else:
                msg += data


