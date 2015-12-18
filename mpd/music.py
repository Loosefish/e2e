#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from mpd.daemon import get_dicts


def get_songs():
    try:
        files = (f['file'] for f in get_dicts('list file'))
        return [Song(get_dicts('lsinfo "{}"'.format(f))[0]) for f in files]
    except IndexError:
        return []


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
