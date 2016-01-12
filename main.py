#!/usr/bin/python3

import logging
import argparse
import sys

import overlay

def parse_address(s):
    try:
        return ('127.0.0.1', int(s))
    except ValueError:
        pass

    try:
        host,port = s.split(':')
        return (host.strip(), int(port))
    except ValueError:
        raise ValueError('invalid host/port: {}'.format(s))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('main')

    parser = argparse.ArgumentParser()
    parser.add_argument('address')
    parser.add_argument('-c', '--connect', action='store', nargs='+',
                        dest='remotes')
    
    args = parser.parse_args()

    logger.debug('address: {}'.format(args.address))
    logger.debug('connect to: {}'.format(args.remotes))

    local_address = parse_address(args.address)
    if args.remotes is None:
        peer_addresses = None
    else:
        peer_addresses = [ parse_address(a) for a in args.remotes ]

    the_overlay = overlay.Overlay(local_address, peer_addresses)
    overlay_cmd = the_overlay.get_cmd_queue()
    the_overlay.start()

    while True:
        line = sys.stdin.readline()

        overlay_cmd.put(('keyboard_entered', line.strip())) # TODO

