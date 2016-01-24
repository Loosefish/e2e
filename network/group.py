#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import socket
import socketserver
import threading

import mpd
import network
import proto


class MusicMixin:
    def update_music(self, hashes):
        # update music by intersection
        self.music = self.music & hashes
        self.logger.debug('updating music {}'.format(len(self.music)))


class ServerLogger:
    @property
    def logger(self):
        return self.server.logger


class GroupLeader(MusicMixin, socketserver.TCPServer):
    '''Create new group with local peer as leader'''
    def __init__(self):
        self.logger = logging.getLogger('group_leader')

        self.peers = set()
        self.music = mpd.music.get_hashes()

        address = network.parse_address(network.get_group_address())

        self.logger.info('starting group leader server on {}'.format(address))

        super().__init__(address, GroupLeaderHandler)
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.start()

    def add_peer(self, a, p):
        peer = '{}:{}'.format(a, p)
        self.peers.add(peer)
        m = proto.GroupInfo(network.get_group_address(), self.peers)
        self.send_all(m)

    def send_all(self, m):
        for p in self.peers:
            self.send_peer(p, m)

    @staticmethod
    def send_peer(p, m):
        with socket.socket() as sock:
            sock.settimeout(10)  # TODO: Handle timeout exception
            sock.connect(network.parse_address(p))
            sock.sendall(bytes(m))


class GroupLeaderHandler(ServerLogger, socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        msg = proto.parse(self.rfile.readline())
        self.logger.debug('received {}'.format(type(msg)))

        if isinstance(msg, proto.GroupJoin):
            # peer wants to join group
            self.logger.debug('join request from {} ({})'.format(self.client_address[0], msg.port))
            # answer with GroupInfo
            answer = bytes(proto.GroupInfo(network.get_group_address(), self.server.peers))
            self.wfile.write(answer)
            self.server.add_peer(self.client_address[0], msg.port)

        elif isinstance(msg, proto.GroupMusic):
            self.server.update_music(msg.hashes)
            self.server.send_all(proto.GroupMusic(self.server.music))


class GroupPeer(MusicMixin, socketserver.TCPServer):
    '''Try to join a group'''
    def __init__(self, leader):
        self.logger = logging.getLogger('group_peer')

        self.leader = leader
        self.music = mpd.music.get_hashes()
        self.peers = set()
        self.join_pending = True

        # start server for group messages
        address = network.get_group_address()
        self.logger.info('starting peer server on {}'.format(address))

        super().__init__(network.parse_address(address), GroupPeerHandler)
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.start()

        # try to contact group leader with GroupJoin
        self.logger.debug('contacting leader at {}'.format(leader))
        self.send_leader(proto.GroupJoin(network.get_group_port()))

    def update(self, info):
        '''Update group from GroupInfo message'''
        if self.join_pending:
            # first GroupInfo - get leader and peers
            self.leader = info.leader
            self.peers = info.peers
            self.join_pending = False
            # send GroupMusic to leader
            self.send_leader(proto.GroupMusic(self.music))

    def send_leader(self, m):
        self.logger.debug('sending {} to leader {}'.format(m, self.leader))
        with socket.socket() as sock:
            sock.settimeout(10)  # TODO: Handle timeout exception
            sock.connect(network.parse_address(self.leader))
            sock.sendall(bytes(m))


class GroupPeerHandler(ServerLogger, socketserver.StreamRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        msg = proto.parse(self.rfile.readline().strip())
        self.logger.debug('received {}'.format(type(msg)))
        if isinstance(msg, proto.GroupInfo) and self.server.join_pending:
            # first GroupInfo arrived
            self.server.update(msg)
            self.logger.debug('group join complete')

        elif isinstance(msg, proto.GroupMusic):
            self.server.update_music(msg.hashes)
