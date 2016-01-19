#!/usr/bin/python3

'''The overlay module takes care of joining, managing and searching the
Gnutella-like overlay.'''

import threading
import socket
import logging
import uuid
import random

from signalqueue import QueueSet
import proto

N_NEIGHBOURS = 2    # number of neighbours every node tries to have


class Overlay(threading.Thread):
    my_address = None  # TODO find cleaner way to make this info available to
                       # the Peer class

    @staticmethod
    def get_address():
        return Overlay.my_address

    @staticmethod
    def get_port():
        return Overlay.my_address.split(':')[1]

    def __init__(self, listenaddress, entrypeers):
        self.logger = logging.getLogger("overlay")

        self.listenaddress = listenaddress
        Overlay.my_address = listenaddress  # TODO validate, prevent injections
        self.entrypeers = entrypeers

        self.state = {
            'neighbours': [],
            'joining': None,   # has data when we are currently trying to join
            'pings': dict(),
        }

        self.queues = QueueSet()
        self.cmdqueue = self.queues.New()  # commands by the user

        self.queue_to_peer = dict()  # remember which queue was used for which peer

        # first connect to the overlay
        if entrypeers is not None:
            self.cmdqueue.put(('join', entrypeers))

        threading.Thread.__init__(self)

    def get_cmd_queue(self):
        '''Returns the queue that can be used by the user to interactively
        issue commands (overlay operations).'''

        return self.cmdqueue

    def _listen_event(self, data):
        self.logger.info('new incoming peer connection')

        # create new objects for communication
        new_queue = self.queues.New()
        new_peer = Peer.from_connection(data, new_queue)

        # remember the Peer and the queue
        self.queue_to_peer[new_queue] = new_peer

        # start the peer thread
        new_peer.start()

    def _user_event(self, data):
        self.logger.info('executing user command: {}'.format(data))

        (cmd, payload) = data

        if cmd == 'join':
            # join the overlay using the given entry peers
            if self.state['joining'] is not None:
                self.logger.error('already joining, ignore command.')
                return

            if len(self.state['neighbours']) == N_NEIGHBOURS:
                self.logger.error("already connected, don't join.")
                return

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
                return

            self.queue_to_peer[new_queue] = good_peer
            good_peer.start()

            ping_id = str(uuid.uuid4())
            self.state['joining']['current_entry'] = good_peer
            self.state['joining']['ping_id'] = ping_id

            good_peer.send(proto.Ping(ping_id, 3))

        elif cmd == 'user_cmd':
            if payload == 'status':
                print(self.state)

        else:
            self.logger.error('unknown command: {}'.format(cmd))

    def _peer_event(self, inqueue, data):
        # a message from another peer
        peer = self.queue_to_peer[inqueue]
        self.logger.info('got a message from peer {}: {}'.format(peer, data))

        if data is None:
            self.logger.info('connection closed')

            if self.state['joining'] is not None and peer == self.state['joining']['current_entry']:
                self.logger.error('error joining, entry died')
                if len(self.state['joining']['candidates']) > 0:
                    self.logger.info('more entries to try...')
                    self.cmdqueue.put(('join',
                                       self.state['joining']['candidates']))
                    self.state['joining'] = None
                else:
                    self.logger.error('joining finally failed.')

            # TODO remove from pongs pending list and trigger
            # processing

            # TODO if neighbour, try to reconnect (peer may have closed
            # it, unaware of the fact that it's a neighbour of ours)
            # TODO update neighbour list

            del self.queue_to_peer[inqueue]

        elif isinstance(data, proto.Ping):
            self.logger.debug('got a PING message!')
            p_id = data.get_id()
            ttl = data.get_ttl()

            # is this my ping?
            # TODO

            # neighbours we'd have to wait for
            dependencies = [x for x in self.state['neighbours'] if x != peer]

            if ttl == 0 or len(dependencies) == 0:
                # do not recurse
                self.logger.debug('answering with PONG directly')
                peer.send(proto.Pong(p_id, []))
                if peer not in self.state['neighbours']:
                    # keep connection to neighbours alive
                    peer.disconnect()
                return

            # is it a new ping?
            if p_id in self.state['pings']:
                self.logger.debug('already know ping {}, send empty Pong'
                                  .format(p_id))
                peer.send(proto.Pong(p_id, []))
                return

            self.state['pings'][p_id] = {
                'from': peer,
                'pending': dependencies,  # pongs we're waiting for
                'collected': set(),  #  peers collected by pongs
            }

            for n in self.state['pings'][p_id]['pending']:
                self.logger.debug('forwarding ping to {}'.format(n))
                n.send(proto.Ping(p_id, ttl-1))

        elif isinstance(data, proto.Pong):
            self.logger.debug('got a PONG message!')
            p_id = data.get_id()
            addrs = data.get_peers()

            if self.state['joining'] is not None and peer == self.state['joining']['current_entry']:
                neighbourset = {peer.get_address_str()} | addrs
                self.logger.debug('got possible neighbours: {}'.
                                  format(neighbourset))

                # choose random neighbours
                neighbourlist = list(neighbourset)
                random.shuffle(neighbourlist)

                for n in neighbourlist:
                    if len(self.state['neighbours']) >= N_NEIGHBOURS:
                        break
                    self.logger.debug('trying peer {} as a neighbour'.format(n))

                    new_queue = self.queues.New()
                    try:
                        new_peer = Peer(n, new_queue)
                        new_peer.connect()
                        # TODO only successful if remote peer also
                        # wants to be our neighbour
                    except OSError as e:
                        self.logger.warning('neighbour {} does not work ({})'
                                            .format(n, e))
                        continue
                    self.logger.debug('peer {} added as a neighbour'.format(n))
                    self.state['neighbours'].append(new_peer)
                    new_peer.start()
                    new_peer.send(proto.Neighbour())
                    self.queue_to_peer[new_queue] = new_peer

                # don't need to close connection, since the peer
                # triggered closing it

                self.state['joining'] = None
                return

            if p_id not in self.state['pings']:
                self.logger.warning('unexpected PONG from {}'.format(peer))
                return

            if peer not in self.state['pings'][p_id]['pending']:
                self.logger.warning('unexpected PONG from {} (not pending)'.format(peer))

            self.state['pings'][p_id]['pending'].remove(peer)
            self.state['pings'][p_id]['collected'].add(peer.get_address_str())
            self.state['pings'][p_id]['collected'] |= (addrs)

            if len(self.state['pings'][p_id]['pending']) == 0:
                self.logger.debug('got all pending PONGs')

                self.state['pings'][p_id]['from'].send(proto.Pong(
                    p_id, self.state['pings'][p_id]['collected']
                ))

                if self.state['pings'][p_id]['from'] not in self.state['neighbours']:
                    # keep connection to neighbours alive
                    self.state['pings'][p_id]['from'].disconnect()

                # TODO already delete pings entry ??
                del self.state['pings'][p_id]

        elif isinstance(data, proto.Neighbour):
            self.logger.debug('peer {} uses us as a neighbour'.format(peer))

            if peer in self.state['neighbours']:
                self.logger.debug('already have it as a neighbour')
                return

            if len(self.state['neighbours']) >= N_NEIGHBOURS:
                self.logger.debug('we have enough neighbours')
                return

            self.logger.debug('peer {} added as a neighbour'.format(peer))
            self.state['neighbours'].append(peer)
            peer.send(proto.Neighbour())

    def run(self):
        # open up our own listen socket
        self.logger.debug('setting up socket...')
        self.listen = socket.socket()
        self.logger.debug('trying to listen on {}...'.format(self.listenaddress))

        self.listen.bind(Peer.parse_address(self.listenaddress))
        self.listen.listen(10)
        self.logger.info('server socket established.')

        self.listenQ = self.queues.New()  # the queue that will be used for
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
                self._listen_event(data)

            elif inqueue == self.cmdqueue:
                # A command from the user
                self._user_event(data)

            elif inqueue in self.queue_to_peer:
                # a message from another peer
                self._peer_event(inqueue, data)

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
                (conn, addr) = self.sock.accept()
                self.logger.debug('new TCP connection from {}'.format(addr))

                self.q.put(conn)
            except OSError as e:
                self.logger.exception(e)


class Peer(threading.Thread):
    # TODO differentiate sending/receiving socket ???
    def __init__(self, address, inbox, reuse_socket=None):
        self.address = Peer.parse_address(address)
        self.logger = logging.getLogger('peer')

        self.socket_lock = threading.Lock()

        self.inbox = inbox  # the queue object to store incoming messages in

        if reuse_socket is not None:
            self.sock = reuse_socket
            self.state = "connected"
        else:
            self.sock = None  # the socket used for communication
            self.state = "disconnected"

        threading.Thread.__init__(self)

    def parse_address(s):
        '''Parse an <ip>:<port> string into a proper tuple.'''
        try:
            # do not convert if already an (ip,port)-tuple
            (a, b) = s
            return s
        except (TypeError, ValueError):
            pass

        try:
            return ('127.0.0.1', int(s))
        except ValueError:
            pass

        try:
            host, port = s.split(':')
            return (host.strip(), int(port))
        except ValueError:
            raise ValueError('invalid host/port: {}'.format(s))

    @staticmethod
    def from_connection(conn, inbox):
        '''Construct a Peer object from an already-established connection, e.g.
        after accepting it from a listening socket.'''

        new_peer = Peer(conn.getpeername(), inbox, reuse_socket=conn)
        new_peer.send(proto.Hello(Overlay.get_port()))
        return new_peer

    def connect(self):
        if self.address is None:
            raise ValueError('cannot connect to peer without address')
        if self.state != "disconnected":
            self.logger.warning('peer is already connected')
            return

        self.state = "connecting"
        with self.socket_lock:
            try:
                self.sock = socket.socket()  # defaults to IPv4 TCP
                self.sock.connect(self.address)
                self.send(proto.Hello(Overlay.get_port()))
            except OSError:
                self.sock = None
                self.state = "disconnected"
                raise

            self.state = "connected"

    def get_state(self):
        return self.state

    def get_address(self):
        return self.address

    def get_address_str(self):
        ip, port = self.get_address()
        return '{}:{}'.format(ip, port)

    def disconnect(self):
        self.logger.debug('closing connection to peer {}'.format(self))
        self.sock.shutdown(socket.SHUT_WR)
        self.state = "disconnected"

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

    def __str__(self):
        return '{}'.format(self.get_address())

    def run(self):
        '''Run to infinity, reading lines from the socket and putting them as
        protocol messages into the given inbox queue.'''

        # TODO evaluate if we need synchronisation with writers here.
        # If so, use selectors and only read (and lock!) when there is
        # something to read.

        msg = bytes()
        while True:
            try:
                data = self.sock.recv(1)  # TODO more efficient, buffering
            except OSError as e:
                data = None
                self.logger.warning('error reading from socket: {}'.format(e.strerror))

            if data is None or len(data) == 0:
                self.logger.info('TCP connection was closed')

                try:
                    # in case our side was not yet shut down
                    self.sock.shutdown(socket.SHUT_WR)
                except OSError as e:
                    if e.errno != 107:
                        raise

                self.sock.close()
                self.inbox.put(None)
                return

            if data == b'\n':
                parsed = proto.parse(msg)
                msg = bytes()

                if isinstance(parsed, proto.Hello):
                    # update the remote port

                    ip, port = self.address
                    new_port = parsed.get_port()
                    self.logger.debug('remote server port is now known as {} (was: {})'
                                      .format(new_port, port))
                    self.address = (ip, new_port)
                    continue

                self.inbox.put(parsed)

                if parsed is None:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    return
            else:
                msg += data
