#!/usr/bin/env python3
# coding: utf-8

import hashlib


def checksum(path, algo='sha1', length=-1, offset=0):
    ho = hashlib.new(algo) if isinstance(algo, str) else algo
    if length == 0:
        return ho
    if length < 0:
        length = float('inf')
    chunksize = min(16384, length)
    with open(path, 'rb') as fin:
        fin.seek(offset)
        while chunksize:
            chunk = fin.read(chunksize)
            if not chunk:
                break
            ho.update(chunk)
            length -= chunksize
            chunksize = min(chunksize, length)
    return ho
