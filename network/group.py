#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import socket
import socketserver
import threading

import network
import proto


class GroupLeader(socketserver.TCPServer):
    '''Create new group with local peer as leader'''
    def __init__(self):
        self.logger = logging.getLogger('group_leader')

        self.peers = set()

        address = network.parse_address(network.get_group_address())

        self.logger.info('starting group leader server on {}'.format(address))

        super().__init__(address, GroupLeaderHandler)
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.start()


class GroupLeaderHandler(socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        msg = proto.parse(self.rfile.readline())
        if isinstance(msg, proto.GroupJoin):
            self.server.logger\
                .debug('join request from {} ({})'.format(self.client_address[0], msg.port))
            self.peers.add((self.client_address[0], msg.port))
            self.wfile.write(bytes(proto.GroupJoin(network.get_group_port())) + b'\n')


class GroupPeer(socketserver.TCPServer):
    '''Try to join a group'''
    def __init__(self, leader_adr):
        self.logger = logging.getLogger('group_peer')

        self.leader_adr = leader_adr

        self.logger.debug('contacting leader at {}'.format(leader_adr))

        sock = socket.socket()
        sock.settimeout(10)  # TODO: Handle timeout exception
        sock.connect(network.parse_address(leader_adr))

        sock.sendall(bytes(proto.GroupJoin(network.get_group_port())) + b'\n')
        msg = proto.parse(sock.recv(1024))
        if isinstance(msg, proto.GroupJoin):
            address = network.get_group_address()
            self.logger.debug('leader answered {}'.format(msg.port))
            self.logger.info('starting group peer server on {}'.format(address))
            super().__init__(network.parse_address(address), GroupPeerHandler)
            self.thread = threading.Thread(target=self.serve_forever)
            self.thread.start()


class GroupPeerHandler(socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        data = self.rfile.readline().strip()
        self.server.logger.debug('received "{}" from {}'.format(data, self.client_address[0]))
