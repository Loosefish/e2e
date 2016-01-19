#!/usr/bin/python3

import logging
import argparse
import sys

import overlay
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

    the_overlay = overlay.Overlay(local_address, peer_addresses)
    overlay_cmd = the_overlay.get_cmd_queue()
    the_overlay.start()

    while True:
        line = sys.stdin.readline().strip()
        overlay_cmd.put(('keyboard_entered', line))  # TODO
