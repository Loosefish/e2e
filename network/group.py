#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import socket
import socketserver
import threading

import mpd
import network
import proto


class BasicGroupServer:
    def update_music(self, hashes):
        # update music by intersection
        self.music = self.music & hashes
        self.logger.debug('updating music {}'.format(len(self.music)))

    def stop(self):
        self.shutdown()
        self.server_close()


class ServerLogger:
    @property
    def logger(self):
        return self.server.logger


class GroupLeader(BasicGroupServer, socketserver.TCPServer):
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

    def remove_peer(self, a, p):
        peer = '{}:{}'.format(a, p)
        self.peers.remove(peer)
        m = proto.GroupInfo(network.get_group_address(), self.peers)
        self.send_all(m)

    def send_all(self, m):
        for p in self.peers:
            GroupLeader.send_peer(p, m)

    @staticmethod
    def send_peer(p, m):
        with socket.socket() as sock:
            sock.settimeout(10)  # TODO: Handle timeout exception
            sock.connect(network.parse_address(p))
            sock.sendall(bytes(m))

    def leave(self):
        self.stop()
        m = proto.GroupLeave()
        self.send_all(m)


class GroupLeaderHandler(ServerLogger, socketserver.BaseRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        # msg = proto.parse(self.rfile.readline())
        msg = proto.receive(self.request)
        self.logger.debug('received {}'.format(type(msg)))

        if isinstance(msg, proto.GroupJoin):
            # peer wants to join group
            self.logger.debug('join request from {} ({})'.format(self.client_address[0], msg.port))
            # answer with GroupInfo
            self.server.add_peer(self.client_address[0], msg.port)

        elif isinstance(msg, proto.GroupMusic):
            self.server.update_music(msg.hashes)
            self.server.send_all(proto.GroupMusic(self.server.music))

        elif isinstance(msg, proto.GroupLeave):
            self.logger.debug('peer leaving: {} ({})'.format(self.client_address[0], msg.port))
            self.server.remove_peer(self.client_address[0], msg.port)


class GroupPeer(BasicGroupServer, socketserver.TCPServer):
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

    def update_peers(self, ps):
        self.peers = ps - {network.get_group_address()}
        self.logger.debug('updating peers: {}'.format(self.peers))

    def update(self, info):
        '''Update group from GroupInfo message'''
        self.update_peers(info.peers)
        if self.join_pending:
            # first GroupInfo - get leader and peers
            self.leader = info.leader
            self.join_pending = False
            # send GroupMusic to leader
            self.send_leader(proto.GroupMusic(self.music))
            self.logger.debug('group join complete')

    def send_leader(self, m):
        self.logger.debug('sending {} to leader {}'.format(m, self.leader))
        with socket.socket() as sock:
            sock.settimeout(10)  # TODO: Handle timeout exception
            sock.connect(network.parse_address(self.leader))
            sock.sendall(bytes(m))

    def leave(self):
        self.logger.debug('leaving group')
        self.send_leader(proto.GroupLeave())
        self.stop()


class GroupPeerHandler(ServerLogger, socketserver.BaseRequestHandler):
    '''Handler for incoming group messages'''
    def handle(self):
        msg = proto.receive(self.request)
        self.logger.debug('received {}'.format(type(msg)))
        if isinstance(msg, proto.GroupInfo):
            self.server.update(msg)

        elif isinstance(msg, proto.GroupMusic):
            self.server.update_music(msg.hashes)

        elif isinstance(msg, proto.GroupLeave):
            # TODO: this is hacky because the overlay still has a reference
            t = threading.Thread(target=self.server.stop())
            t.start()
