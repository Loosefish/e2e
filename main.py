#!/usr/bin/python3

import argparse
import logging
import readline
import sys

from network.overlay import Overlay
import mpd


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('main')

    parser = argparse.ArgumentParser()
    parser.add_argument('music')
    parser.add_argument('address')
    parser.add_argument('-c', '--connect', action='store', nargs='+',
                        dest='remotes')

    args = parser.parse_args()

    logger.debug('music: {}'.format(args.music))
    logger.debug('address: {}'.format(args.address))
    logger.debug('connect to: {}'.format(args.remotes))

    mpd.run(args.music)

    local_address = args.address
    if args.remotes is None:
        peer_addresses = None
    else:
        peer_addresses = args.remotes

    the_overlay = Overlay(local_address, peer_addresses)
    overlay_cmd = the_overlay.get_cmd_queue()
    the_overlay.start()

    readline.set_history_length(1000)
    while True:
        line = input()
        if line in ['x', 'exit']:
            overlay_cmd.put(('user_cmd', 'exit'))
            mpd.kill()
            sys.exit(1)
        overlay_cmd.put(('user_cmd', line))
