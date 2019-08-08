#!/usr/bin/env python3
# coding: utf-8

from __future__ import unicode_literals, print_function

import io
import sys
import weakref


class Stream(object):
    opened = weakref.WeakValueDictionary()
    _preopened = {
        (1, 'w'): sys.stdout,
        (2, 'w'): sys.stderr,
        ('', 'r'): sys.stdin,
        ('', 'w'): sys.stdout,
        ('-', 'r'): sys.stdin,
        ('-', 'w'): sys.stdout,
        ('<stdin>', 'r'): sys.stdin,
        ('<stdout>', 'w'): sys.stdout,
        ('<stderr>', 'w'): sys.stderr,
    }
    _safe_attributes = {'mode', 'name'}

    @classmethod
    def open(cls, file, mode='r', *args, **kwargs):
        k = file, mode
        f = cls._preopened.get(k)
        if f is None:
            f = open(file, mode, *args, **kwargs)
            cls.opened[id(f)] = f
        return cls(f)

    @classmethod
    def wrap(cls, content):
        if isinstance(content, str):
            return cls(io.StringIO(content))
        if isinstance(content, bytes):
            return cls(io.BytesIO(content))
        return cls(io.StringIO(str(content)))

    def __init__(self, file):
        self.file = file

    def __iter__(self):
        return iter(self.file)

    def __getattr__(self, name):
        if name in self._safe_attributes:
            return getattr(self.file, name, None)
        return getattr(self.file, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if id(self.file) in self.opened:
            self.file.__exit__(exc_type, exc_val, exc_tb)

    def is_binary(self):
        if self.mode:
            return 'b' in self.mode
        try:
            return isinstance(self.file.read(0), bytes)
        except Exception:
            pass
