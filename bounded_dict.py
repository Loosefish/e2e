#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import UserDict


class BoundedDict(UserDict):
    def __init__(self, limit):
        self._limit = limit
        self._keys = []
        super().__init__()

    def __setitem__(self, key, value):
        if key in self.data:
            self._keys.remove(key)
            self._keys.append(key)
        elif len(self._keys) == self._limit:
            del self.data[self._keys.pop(0)]
            self._keys.append(key)
        else:
            self._keys.append(key)
        self.data[key] = value

    def __delitem__(self, key):
        self._keys.remove(key)
        del self.data[key]
