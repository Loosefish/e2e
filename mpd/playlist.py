#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mpd.music import Song, Album
from mpd.daemon import get_dicts, get_query


def get():
    try:
        return [Song(s) for s in get_dicts('playlistinfo')]
    except IndexError:
        return []


def clear():
    get_query('clear')


def add(song):
    get_query('add "{}"'.format(song.path))


def add_album(song):
    query = 'findadd AlbumArtist "{}" Date "{}" Album "{}"'
    get_query(query.format(song.albumartist, song.date, song.album))


def remove(index):
    get_query('delete {}'.format(index))


def move(index, to):
    get_query('move {} {}'.format(index, to))
