#!/usr/bin/python3

import argparse
import logging
import readline
import sys

import network
from network.overlay import Overlay
import mpd


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('main')

    parser = argparse.ArgumentParser()
    parser.add_argument('music')
    parser.add_argument('address')
    parser.add_argument('overlay_port')
    parser.add_argument('group_port')
    parser.add_argument('-c', '--connect', action='store', nargs='+',
                        dest='remotes')

    args = parser.parse_args()

    logger.debug('music: {}'.format(args.music))
    logger.debug('address: {}'.format(args.address))
    logger.debug('connect to: {}'.format(args.remotes))

    mpd.run(args.music)

    network.set_address(args.address, args.overlay_port)
    network.set_group_port(args.group_port)
    if args.remotes is None:
        peer_addresses = None
    else:
        peer_addresses = args.remotes

    the_overlay = Overlay(peer_addresses)
    the_overlay.start()

    readline.set_history_length(1000)
    while True:
        line = input()
        if line in ['x', 'exit']:
            the_overlay.put_cmd(('user_cmd', 'exit'))
            mpd.kill()
            sys.exit()
        the_overlay.put_cmd(('user_cmd', line))
