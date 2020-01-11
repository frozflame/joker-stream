#!/usr/bin/env python3
# coding: utf-8


import hashlib
from joker.stream import utils


def test_chksum():
    _nonhex_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
    _nonhex_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    chksum = utils.checksum
    params = {
        'algo': 'md5',
        'length': 0,
    }
    assert chksum(__file__, **params).hexdigest() == _nonhex_md5

    params = {
        'algo': hashlib.md5(),
        'length': 0,
    }
    assert chksum(__file__, **params).hexdigest() == _nonhex_md5

    params = {
        'algo': hashlib.md5(),
        'length': -1,
        'offset': 2 ** 32,
    }
    assert chksum(__file__, **params).hexdigest() == _nonhex_md5

    params = {
        'algo': hashlib.md5(),
        'length': 10,
        'offset': 2 ** 32,
    }
    assert chksum(__file__, **params).hexdigest() == _nonhex_md5

    params = {
        'length': 10,
        'offset': 2 ** 32,
    }
    assert chksum(__file__, **params).hexdigest() == _nonhex_sha1


if __name__ == '__main__':
    test_chksum()
