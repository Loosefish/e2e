#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import Popen
from tempfile import TemporaryDirectory
import logging
import os
import socket

from mpd import daemon, playback

_mpd_dir = None
_mpd_proc = None


def run(music_dir):
    music_dir = os.path.abspath(os.path.expanduser(music_dir))
    if not os.path.isdir(music_dir):
        raise FileNotFoundError(music_dir)

    logger = logging.getLogger('mpd')
    global _mpd_dir
    _mpd_dir = TemporaryDirectory(prefix='e2e-mpd.')
    mpd_dir = _mpd_dir.name
    # create temporary config for mpd
    mpd_db = os.path.join(mpd_dir, 'db')
    os.mknod(mpd_db)

    mpd_socket = os.path.join(mpd_dir, 'socket')
    os.mknod(mpd_socket)

    mpd_conf = os.path.join(mpd_dir, 'mpd.conf')
    with open(mpd_conf, 'w') as f:
        f.write('db_file "{}"\n'.format(mpd_db))
        f.write('log_file "syslog"\n')
        f.write('bind_to_address "{}"\n'.format(mpd_socket))
        f.write('music_directory "{}"\n'.format(music_dir))

    logger.debug('created mpd config in {}'.format(mpd_dir))
    logger.debug('starting on {}...'.format(mpd_socket))

    # run mpd
    global _mpd_proc
    _mpd_proc = Popen(['mpd', '--no-daemon', mpd_conf])
    daemon.set_socket(mpd_socket)

    # wait for mpd to start
    while True:
        try:
            playback.get_status()
            break
        except (ConnectionRefusedError, FileNotFoundError):
            pass
    # wait for music database
    while 'db_update' not in daemon.get_dict("stats"):
        try:
            daemon.get_query("idle database", timeout=0.5)
        except socket.timeout:
            pass

    logger.info('ready')


def kill():
    _mpd_proc.kill()
    _mpd_proc.wait()
    _mpd_dir.cleanup()
