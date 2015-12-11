#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mpd.music import Song
from mpd.daemon import get_dicts, get_query


def get_status():
    return Status(get_dicts('status')[0])


def get_currentsong():
    try:
        return Song(get_dicts('currentsong')[0])
    except IndexError:
        return None


def play(index=0):
    get_query('play {}'.format(index))


def pause_toggle():
    state = get_status().state
    if state == 'play':
        get_query('pause 1')
    elif state == 'pause':
        get_query('pause 0')
    elif state == 'stop':
        get_query('play')


def stop():
    get_query('stop')


def next():
    get_query('next')


def previous():
    get_query('previous')


def repeat_toggle():
    if get_status().repeat:
        get_query('repeat 0')
    else:
        get_query('repeat 1')


def random_toggle():
    if get_status().random:
        get_query('random 0')
    else:
        get_query('random 1')


def single_toggle():
    if get_status().single:
        get_query('single 0')
    else:
        get_query('single 1')


class Status(object):
    mpd_converters = {
        'bitrate': int,
        'consume': lambda x: x == '1',
        'elapsed': float,
        'mixrampdb': float,
        'nextsong': int,
        'nextsongid': int,
        'playlist': int,
        'playlistlength': int,
        'random': lambda x: x == '1',
        'repeat': lambda x: x == '1',
        'single': lambda x: x == '1',
        'song': int,
        'songid': int,
        'volume': int
    }

    def __init__(self, mpd_dict):
        for k, v in mpd_dict.items():
            if k in Status.mpd_converters:
                v = Status.mpd_converters[k](v)
            self.__setattr__(k, v)

        if 'time' in mpd_dict:
            self.time, self.duration = (int(x) for x in mpd_dict['time'].split(':'))
