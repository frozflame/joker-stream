#!/usr/bin/env python3
# coding: utf-8

from __future__ import unicode_literals, print_function

import os

from joker.stream.base import FilteredStream, GeneralStream


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


class ShellStream(FilteredStream):
    def snl(self, extra_func=None):
        """strip trailing newline charactors (linesep)"""
        self.filters.append(lambda s: s.rstrip(os.linesep))
        if extra_func is not None:
            self.filters.append(extra_func)
        return self

    def sf(self, fmt, sep=None, maxsplit=-1, flags=None):
        """split and format"""
        _sf = _split_format
        self.filters.append(lambda s: _sf(s, fmt, sep, maxsplit, flags))
        return self

    def nonblank(self):
        """discard lines containing only spaces"""
        self.filters.append(lambda s: (s if s.strip() else None))
        return self

    def strip(self, chars=None):
        """strip leading and trailing spaces or specified characters"""
        self.filters.append(lambda s: s.strip(chars))
        return self

    def dense(self):
        """strip and discard empty strings"""
        self.filters.append(lambda s: (s.strip() or None))
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


class GeneralShellStream(GeneralStream, ShellStream):
    pass


class RecursiveInclusionStream(GeneralStream):
    def setup(self, *filters):
        if not filters:
            self.filters = [self.inclusion_filter]
            return self
        _filters = []
        for f in filters:
            if getattr(f, '__name__', None) == 'inclusion_filter':
                f = self.inclusion_filter
            _filters.append(f)
        self.filters = _filters
        return self

    @staticmethod
    def check_for_inclusion(line):
        import shlex
        parts = shlex.split(line, comments=True)
        if len(parts) == 2 and parts[0] in ['.', 'source']:
            path = parts[1]
            if os.path.isfile(path):
                return path

    def inclusion_filter(self, line):
        path = self.check_for_inclusion(line)
        if path:
            return self.include(path)
        return line

    def include(self, path):
        return self.open(path).setup(*self.filters)


class AtomicTailerFilter(object):
    def __init__(self, linesep=os.linesep):
        self.broken_lines = []
        self.linesep = linesep

    def __call__(self, line):
        if not line.endswith(self.linesep):
            self.broken_lines.append(line)
            return
        if self.broken_lines:
            prefix = ''.join(self.broken_lines)
            self.broken_lines = []
            return prefix + line
        return line
