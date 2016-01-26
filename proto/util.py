#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pickle


class PicklingMessage(object):
    def __bytes__(self):
        data = pickle.dumps(self, pickle.HIGHEST_PROTOCOL)
        length = str(len(data)).encode()
        return length + b'\n' + data
        # return pickle.dumps(self, pickle.HIGHEST_PROTOCOL) + b'\n'
