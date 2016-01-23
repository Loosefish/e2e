#!/usr/bin/env python
# -*- coding: utf-8 -*-
_address = None


def set_address(adr):
    global _address
    _address = adr


def get_address():
    global _address
    return _address


def get_port():
    global _address
    return _address.split(':')[1]
