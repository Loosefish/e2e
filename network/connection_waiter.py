#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import logging


class ConnectionWaiter(threading.Thread):
    '''Thread that accepts connections on a listen socket and returns them via
    a queue.'''

    def __init__(self, sock, q):
        self.logger = logging.getLogger('listening-socket')
        self.sock = sock
        self.q = q

        threading.Thread.__init__(self, daemon=True)

    def run(self):
        while True:
            try:
                (conn, addr) = self.sock.accept()
                self.logger.debug('new TCP connection from {}'.format(addr))

                self.q.put(conn)
            except OSError as e:
                self.logger.exception(e)
