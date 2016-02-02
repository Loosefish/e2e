#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from random import sample
from hashlib import md5

from mpd.daemon import get_dicts

_hashes = None
_last_uodate = None


def get_songs():
    try:
        files = (f['file'] for f in get_dicts('list file'))
        return [Song(get_dicts('lsinfo "{}"'.format(f))[0]) for f in files]
    except IndexError:
        return []


def _update_hashes():
    global _hashes
    global _last_update
    last_update = get_dicts('stats')[0]['db_update']
    if _hashes is None or last_update != _last_update:
        _hashes = dict((md5(bytes(s)).hexdigest(), s) for s in get_songs())
        _last_update = last_update


def get_hashes():
    global _hashes
    _update_hashes()
    return set(_hashes.keys())


def get_song(song_hash):
    global _hashes
    _update_hashes()
    return _hashes[song_hash]


def search_songs(title):
    return [Song(s) for s in get_dicts('search Title "{}"'.format(title))]


def get_image(song):
    root = get_dicts("config")[0]['music_directory']
    path = os.path.join(root, song.path)
    path = os.path.dirname(path)
    for f in os.listdir(path):
        if os.path.splitext(f)[1] in [".jpg", ".png", ".gif"]:
            return os.path.join(path, f)
    return None


def get_sample(size=100):
    return sample(get_hashes(), size)


def check_sample(to_check):
    return int(len(set(to_check) & get_hashes()) / len(to_check) * 100)


class Song(object):
    mpd_keys = {
        'Artist': 'artist',
        'Title': 'title',
        'AlbumArtist': 'albumartist',
        'Album': 'album',
        'Date': 'date',
        'Disc': 'disc',
        'Track': 'track',
        'Time': 'time',
        'file': 'path'
    }

    def __init__(self, mpd_dict):
        for k, v in mpd_dict.items():
            if k in Song.mpd_keys:
                self.__setattr__(Song.mpd_keys[k], v)
        self.time = int(self.time)

    def __bytes__(self):
        components = (
            self.artist.lower().strip(),
            self.title.lower().strip(),
            str(self.time // 10)
        )
        return b'_'.join(c.encode() for c in components)

    def __repr__(self):
        return 'Song' + repr(self.__dict__)
