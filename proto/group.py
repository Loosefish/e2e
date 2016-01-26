#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re


class GroupJoin:
    regex = re.compile(r'\s*myport=(\d+)\s*$')

    def __init__(self, port):
        self.port = port

    @staticmethod
    def from_raw(raw):
        match = GroupJoin.regex.match(raw.strip())
        if match is None:
            logging.getLogger('proto.GroupJoin')\
                .error('invalid msg: {}'.format(raw))
            return None

        port = int(match.group(1))
        return GroupJoin(port)

    def __bytes__(self):
        return 'GJOIN myport={}\n'.format(self.port).encode()


class GroupInfo:
    def __init__(self, leader, peers):
        self.leader = leader
        self.peers = peers

    @staticmethod
    def from_raw(raw):
        leader, peers = raw.split()
        leader = leader.split('=')[1]
        peers = peers.split('=')[1].split(',')
        if peers[0] == '':
            peers = set()
        else:
            peers = set(peers)
        return GroupInfo(leader, peers)

    def __bytes__(self):
        peers = ','.join(self.peers)
        return 'GINFO leader={} peers={}\n'.format(self.leader, peers).encode()


class GroupMusic:
    def __init__(self, hashes):
        self.hashes = hashes

    @staticmethod
    def from_raw(raw):
        return GroupMusic(raw.split())

    def __bytes__(self):
        return 'GMUSIC {}\n'.format(' '.join(str(s) for s in self.hashes)).encode()
