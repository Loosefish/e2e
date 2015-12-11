#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import Popen
from tempfile import TemporaryDirectory
from time import sleep
import os
import socket
import sys


_mpd_socket = None


def set_socket(mpd_socket):
    global _mpd_socket
    _mpd_socket = mpd_socket


def get_query(text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(_mpd_socket)
    data = s.recv(32)
    s.sendall(bytes(text + '\n', 'utf8'))
    response = b''
    while True:
        data = s.recv(4096)
        response = response + data
        if data[-4:] == b'\nOK\n' or data == b'OK\n':
            break
    s.close()
    return str(response, 'utf8').splitlines()[:-1]


def get_dicts(query):
    response = get_query(query)
    new_token = response[0].split(': ', 1)[0]
    dicts = []
    for r in response:
        tag, value = r.split(': ', 1)
        if tag == new_token:
            d = dict([(tag, value)])
            dicts.append(d)
        else:
            d[tag] = value
    return dicts


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
        sleep(2)
        set_socket(mpd_socket)

        q = "status"
        while q != "exit":
            print(q)
            print(get_dicts(q))
            q = input("enter query: ")

        mpd_proc.kill()
        mpd_proc.wait()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: mpd_example.py path_to_music")
    else:
        run(sys.argv[1])
