#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket


_mpd_socket = None


def set_socket(mpd_socket):
    global _mpd_socket
    _mpd_socket = mpd_socket


def get_query(text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(None)
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
