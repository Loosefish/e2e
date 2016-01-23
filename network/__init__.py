#!/usr/bin/env python
# -*- coding: utf-8 -*-
_address = None
_port = None
_group_port = None


def set_address(adr, p):
    global _address, _port
    _address, _port = adr, p


def set_group_port(p):
    global _group_port
    _group_port = p


def get_address():
    global _address, _port
    return '{}:{}'.format(_address, _port)


def get_port():
    global _port
    return _port


def get_group_address():
    global _address, _group_port
    return '{}:{}'.format(_address, _group_port)


def get_group_port():
    global _group_port
    return _group_port


def parse_address(s):
    '''Parse an <ip>:<port> string into a proper tuple.'''
    try:
        # do not convert if already an (ip,port)-tuple
        (a, b) = s
        return s
    except (TypeError, ValueError):
        pass

    try:
        return ('127.0.0.1', int(s))
    except ValueError:
        pass

    try:
        host, port = s.split(':')
        return (host.strip(), int(port))
    except ValueError:
        raise ValueError('invalid host/port: {}'.format(s))
