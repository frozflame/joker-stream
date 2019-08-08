#!/usr/bin/env python3
# coding: utf-8

from __future__ import division, print_function

import io
import os
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


def _grep(line, pattern, flags=0, group=None):
    import re
    mat = re.search(pattern, line, flags)
    if group:
        return mat and mat.group(group)
    return mat and line


def _ungrep(line, pattern, flags=0):
    import re
    if re.search(pattern, line, flags) is None:
        return line


def _sub(line, pattern, repl, count=0, flags=0):
    import re
    s, n = re.sub(pattern, repl, line, count=count, flags=flags)


def _split_format(line, fmt, sep=None, maxsplit=-1, flags=None):
    if flags is None:
        parts = line.split(sep, maxsplit)
    else:
        import re
        parts = re.split(sep, line, maxsplit=maxsplit, flags=flags)
    m = max(fmt.count('{'), 8)
    n = len(parts)
    if m > n:
        parts.extend([''] * (m - n))
    return fmt.format(*parts)


class ShellStream(Stream):
    def __init__(self, file, *filters):
        super(ShellStream, self).__init__(file)
        self.filters = list(filters)

    def copy(self):
        return ShellStream(self.file, *self.filters)

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
        return super(ShellStream, self).__iter__()

    def lines(self):
        return list(self)

    def add_filters(self, *funcs):
        self.filters.extend(funcs)
        return self

    def __call__(self, func, *args, **kwargs):
        self.filters.append(lambda s: func(s, *args, **kwargs))
        return self

    def snl(self, extra_func=None):
        self.filters.append(lambda s: s.rstrip(os.linesep))
        if extra_func is not None:
            self.filters.append(extra_func)
        return self

    def nonblank(self, extra_func=None):
        self.filters.append(lambda s: (s.strip() or None))
        if extra_func is not None:
            self.filters.append(extra_func)
        return self

    def sf(self, fmt, sep=None, maxsplit=-1, flags=None):
        """split and format"""
        _sf = _split_format
        self.filters.append(lambda s: _sf(s, fmt, sep, maxsplit, flags))
        return self

    def strip(self, chars=None):
        self.filters.append(lambda s: s.strip(chars))
        return self

    def replace(self, old, new):
        self.filters.append(lambda s: s.replace(old, new))
        return self

    def method(self, name, *args, **kwargs):
        self.filters.append(lambda s: getattr(name, *args, **kwargs))
        return self

    def ungrep(self, pattern, flags=0):
        self.filters.append(lambda line: _ungrep(line, pattern, flags))
        return self

    def grep(self, pattern, flags=0, group=None):
        self.filters.append(lambda line: _grep(line, pattern, flags, group))
        return self

    def sub(self, pattern):
        pass

    def quote(self, strip=True):
        if self.is_binary():
            raise TypeError('file should be opened in text mode')
        if strip:
            self.strip()
        import shlex
        return self.add_filters(shlex.quote)
