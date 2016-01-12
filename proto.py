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

    def __bytes__(self):
        return 'PING id={} ttl={}'.format(self.ping_id, self.ttl).encode('utf-8')

MESSAGE_TYPES = {
    'PING': Ping,
}

