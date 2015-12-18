#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import Popen
from tempfile import TemporaryDirectory
from time import sleep
import os
import sys

from mpd import daemon, music, playback


def run(music_dir):
    with TemporaryDirectory(prefix='e2e-mpd.') as mpd_dir:
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

        # run mpd
        mpd_proc = Popen(['mpd', '--no-daemon', mpd_conf])
        daemon.set_socket(mpd_socket)

        # wait for mpd to start
        while True:
            try:
                playback.get_status()
                break
            except (ConnectionRefusedError, FileNotFoundError):
                pass
        # wait for music database
        daemon.get_query("idle database")

        print(playback.get_status().__dict__)
        print(daemon.get_dicts('stats'))
        assert(int(daemon.get_dicts('stats')[0]['songs']) == len(music.get_songs()))

        mpd_proc.kill()
        mpd_proc.wait()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: ./mpd_example.py path_to_music")
    else:
        run(sys.argv[1])
