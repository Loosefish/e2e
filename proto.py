#!/usr/bin/python3

'''The different protocol messages.'''

import re
import logging


def parse(rawbytes):
    '''Parse a protocol message from a given bytes object.'''

    try:
        match = re.match(r'(\S+)(.*)$', rawbytes.decode('utf-8').strip())
        return MESSAGE_TYPES[match.group(1)].from_raw(match.group(2))

    except Exception as e:
        logging.getLogger('proto').exception(e)
        return None


class Ping:
    def __init__(self, ping_id, ttl):
        self.ping_id = ping_id
        self.ttl = ttl

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*id=(\S+)\s+ttl=(\d+)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.PING').error('invalid PING msg: {}'
                                                  .format(raw))
            return None

        return Ping(match.group(1), int(match.group(2)))

    def get_id(self):
        return self.ping_id

    def get_ttl(self):
        return self.ttl

    def __bytes__(self):
        return 'PING id={} ttl={}'.format(self.ping_id, self.ttl).encode('utf-8')


class Pong:
    def __init__(self, ping_id, addrs):
        self.ping_id = ping_id
        self.addrs = addrs

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*id=(\S+)\s+peers=(\S*)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.PONG').error('invalid PONG msg: {}'
                                                  .format(raw))
            return None

        ping_id = match.group(1)
        peers = {p for p in match.group(2).split(',') if len(p) > 0}

        return Pong(ping_id, peers)

    def get_id(self):
        return self.ping_id

    def get_peers(self):
        return self.addrs

    def __bytes__(self):
        return 'PONG id={} peers={}'.format(self.ping_id, ','.join(self.addrs)).encode('utf-8')


class Hello:
    def __init__(self, port):
        self.port = port

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*myport=(\d+)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.Hello').error('invalid HELLO msg: {}'
                                                   .format(raw))
            return None

        port = int(match.group(1))

        return Hello(port)

    def get_port(self):
        return self.port

    def __bytes__(self):
        return 'HELLO myport={}'.format(self.port).encode('utf-8')


class Neighbour:
    '''Tell the remote peer that we now use him as a peer.'''
    def __init__(self):
        pass

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.Neighbour').error('invalid NEIGHBOUR msg: {}'
                                                       .format(raw))
            return None

        return Neighbour()

    def __bytes__(self):
        return 'NEIGHBOUR'.encode('utf-8')


class Sample:
    def __init__(self, hashes):
        self.hashes = hashes

    @staticmethod
    def from_raw(raw):
        return Sample(raw.split())

    def __bytes__(self):
        return 'SAMPLE {}'.format(' '.join(str(s) for s in self.hashes)).encode()


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
        return 'GJOIN myport={}'.format(self.port).encode()


class GroupInfo:
    def __init__(self, leader, peers):
        self.leader = leader
        self.peers = peers

    @staticmethod
    def from_raw(raw):
        leader, peers = raw.split()
        peers = peers.split(',')
        if peers[0] == '':
            peers = None
        return GroupInfo(leader, peers)

    def __bytes__(self):
        peers = ','.join(self.peers)
        return 'GINFO leader={} peers={}'.format(self.leader, peers).encode()


MESSAGE_TYPES = {
    'PING': Ping,
    'PONG': Pong,
    'HELLO': Hello,
    'NEIGHBOUR': Neighbour,
    'SAMPLE': Sample,
    'GJOIN': GroupJoin,
    'GINFO': GroupInfo,
}
