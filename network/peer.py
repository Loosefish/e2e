#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import socket
import logging

from network import get_port, parse_address
import proto


class Peer(threading.Thread):
    # TODO differentiate sending/receiving socket ???
    def __init__(self, address, inbox, reuse_socket=None):
        self.address = parse_address(address)
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

    @staticmethod
    def from_connection(conn, inbox):
        '''Construct a Peer object from an already-established connection, e.g.
        after accepting it from a listening socket.'''

        new_peer = Peer(conn.getpeername(), inbox, reuse_socket=conn)
        new_peer.send(proto.Hello(get_port()))
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
                self.send(proto.Hello(get_port()))
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
        self.logger.debug('sending {} -> {}'.format(type(message), self))
        try:
            self.sock.send(bytes(message))
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

        msg = None
        while True:
            try:
                msg = proto.receive(self.sock)
            except OSError as e:
                msg = None
                self.logger.warning('error reading from socket: {}'.format(e.strerror))

            if msg is None:
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

            if isinstance(msg, proto.Hello):
                # update the remote port
                ip, port = self.address
                new_port = msg.get_port()
                self.logger.debug('remote server port is now known as {} (was: {})'
                                  .format(new_port, port))
                self.address = (ip, new_port)
                continue

            self.inbox.put(msg)

            if msg is None:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                return
