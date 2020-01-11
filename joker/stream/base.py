#!/usr/bin/env python3
# coding: utf-8

from __future__ import unicode_literals, print_function

import io
import sys
import weakref


class Stream(object):
    all_opened_files = weakref.WeakValueDictionary()
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
            cls.all_opened_files[id(f)] = f
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
        if id(self.file) in self.all_opened_files:
            self.file.__exit__(exc_type, exc_val, exc_tb)

    def is_binary(self):
        if self.mode:
            return 'b' in self.mode
        try:
            return isinstance(self.file.read(0), bytes)
        except Exception:
            pass


class FilteredStream(Stream):
    def __init__(self, file, *filters):
        super(FilteredStream, self).__init__(file)
        self.filters = list(filters)

    def copy(self):
        return self.__class__(self.file, *self.filters)

    def _apply_filters(self, line):
        for f in self.filters:
            line = f(line)
            if line is None:
                break
        return line

    def _iter_lines(self):
        for line in self.file:
            line = self._apply_filters(line)
            if line is not None:
                yield line

    def __iter__(self):
        if self.filters:
            return self._iter_lines()
        return super(FilteredStream, self).__iter__()

    def lines(self):
        return list(self)

    def add_filters(self, *funcs):
        self.filters.extend(funcs)
        return self

    def __call__(self, func, *args, **kwargs):
        self.filters.append(lambda s: func(s, *args, **kwargs))
        return self

    def positive(self):
        self.filters.append(lambda s: (s or None))
        return self

    def negative(self):
        self.filters.append(lambda s: (s and None))
        return self


class GeneralStream(FilteredStream):
    @staticmethod
    def _apply_a_filter(func, lgen):
        for line in lgen:
            rv = func(line)
            if rv is None:
                continue
            if isinstance(rv, (str, bytes)):
                yield rv
                continue
            try:
                lines = iter(rv)
            except TypeError:
                yield rv
                continue
            while True:
                try:
                    yield next(lines)
                except StopIteration:
                    break

    def _apply_filters(self, lines):
        for f in self.filters:
            lines = (self._apply_a_filter(f, _) for _ in lines)
        for line in lines:
            yield line

    def _iter_lines(self):
        lgen = self.file
        for f in self.filters:
            lgen = self._apply_a_filter(f, lgen)
        for line in lgen:
            yield line
