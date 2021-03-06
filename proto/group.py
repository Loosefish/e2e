#!/usr/bin/env python
# -*- coding: utf-8 -*-
from proto.util import PicklingMessage
import network
import mpd.playback
import mpd.playlist


class GroupJoin(PicklingMessage):
    def __init__(self, port):
        self.port = port


class GroupInfo(PicklingMessage):
    def __init__(self, leader, peers):
        self.leader = leader
        self.peers = peers


class GroupMusic(PicklingMessage):
    def __init__(self, hashes):
        self.hashes = hashes


class GroupLeave(PicklingMessage):
    def __init__(self):
        self.port = network.get_group_port()


class GroupPing(PicklingMessage):
    def __init__(self, ping_id, ttl=3):
        self.ping_id = ping_id
        self.ttl = ttl


class GroupPong(PicklingMessage):
    def __init__(self, ping_id, leader, music):
        self.ping_id = ping_id
        self.leader = leader
        self.music = music


class GroupPlaylist(PicklingMessage):
    _add = '+'
    _play = '!'

    def __init__(self, op, arg):
        self.op = op
        self.arg = arg

    @staticmethod
    def play(index=0):
        return GroupPlaylist(GroupPlaylist._play, index)

    @staticmethod
    def add(song):
        return GroupPlaylist(GroupPlaylist._add, song)

    def do(self):
        if self.op == GroupPlaylist._add:
            mpd.playlist.add(mpd.music.get_song(self.arg))
        elif self.op == GroupPlaylist._play:
            mpd.playback.play(self.arg)
