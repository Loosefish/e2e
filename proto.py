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

    def from_raw(raw):
        match = re.match(r'\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.Neighbour').error('invalid NEIGHBOUR msg: {}'
                                                  .format(raw))
            return None
        
        return Neighbour()

    def __bytes__(self):
        return 'NEIGHBOUR'.encode('utf-8')

MESSAGE_TYPES = {
    'PING': Ping,
    'PONG': Pong,
    'HELLO': Hello,
    'NEIGHBOUR': Neighbour,
}
