#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import socket
import socketserver
import threading

import network

# TODO: Use proto messages!


class GroupLeader(socketserver.TCPServer):
    '''Create new group with local peer as leader'''
    def __init__(self):
        self.logger = logging.getLogger('group_leader')

        address = network.parse_address(network.get_group_address())

        self.logger.info('starting group leader server on {}'.format(address))

        super().__init__(address, GroupLeaderHandler)
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.start()


class GroupLeaderHandler(socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        data = str(self.rfile.readline().strip(), 'utf-8')
        self.server.logger.debug('received "{}" from {}'.format(data, self.client_address[0]))
        if data.startswith('JOIN'):
            self.wfile.write(bytes('OK\n', 'utf-8'))


class GroupPeer(socketserver.TCPServer):
    '''Try to join a group'''
    def __init__(self, leader_adr):
        self.logger = logging.getLogger('group_peer')

        address = network.parse_address(network.get_group_address())
        self.leader_adr = leader_adr

        self.logger.debug('contacting leader at {}'.format(leader_adr))

        sock = socket.socket()
        sock.settimeout(10)  # TODO: Handle timeout exception
        sock.connect(network.parse_address(leader_adr))

        sock.sendall(bytes('JOIN {}\n'.format(address), 'utf-8'))
        data = str(sock.recv(1024), 'utf-8')
        if data == 'OK\n':
            self.logger.info('starting group peer server on {}'.format(address))
            super().__init__(address, GroupPeerHandler)
            self.thread = threading.Thread(target=self.serve_forever)
            self.thread.start()


class GroupPeerHandler(socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        data = self.rfile.readline().strip()
        self.server.logger.debug('received "{}" from {}'.format(data, self.client_address[0]))
