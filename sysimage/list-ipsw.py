#!/usr/bin/env python3
"""List the members of an IPSW without downloading it: the archive's directory is read with a
couple of HTTP range requests.

usage: list-ipsw.py            (IPSW_URL and IPSW_SIZE say which archive)

Only the names and the sizes are printed, and the ones this repository wants are marked.
"""
import os
import struct
import sys
import urllib.request

URL = os.environ.get('IPSW_URL') or sys.exit('list-ipsw.py: IPSW_URL is not set')
SIZE = int(os.environ.get('IPSW_SIZE') or sys.exit('list-ipsw.py: IPSW_SIZE is not set'))

# the ones fetch.sh wants, by what they are
WANT = {
    '096-04088-077.dmg': 'the root filesystem',
    '096-04666-078.dmg': 'the OS cryptex',
    '096-03536-083.dmg': 'the App cryptex',
}


def fetch(start, end):
    request = urllib.request.Request(URL, headers={'Range': f'bytes={start}-{end}'})
    return urllib.request.urlopen(request, timeout=120)


tail = fetch(SIZE - 65536, SIZE - 1).read()
at = tail.rfind(b'PK\x06\x06')
cd_size, cd_offset = struct.unpack('<QQ', tail[at + 40:at + 56])
cd = fetch(cd_offset, cd_offset + cd_size - 1).read()
print(f'archive: {URL}')
print(f'size: {SIZE} bytes, directory of {cd_size} bytes at {cd_offset}')
print()
p = 0
n = 0
while cd[p:p + 4] == b'PK\x01\x02':
    method, = struct.unpack('<H', cd[p + 10:p + 12])
    csize, usize, nl, el, cl = struct.unpack('<IIHHH', cd[p + 20:p + 34])
    offset, = struct.unpack('<I', cd[p + 42:p + 46])
    name = cd[p + 46:p + 46 + nl].decode()
    extra = cd[p + 46 + nl:p + 46 + nl + el]
    q = 0
    while q + 4 <= len(extra):
        tag, length = struct.unpack('<HH', extra[q:q + 4])
        if tag == 1:
            values = list(struct.unpack('<' + 'Q' * (length // 8), extra[q + 4:q + 4 + length // 8 * 8]))
            if usize == 0xFFFFFFFF:
                usize = values.pop(0)
            if csize == 0xFFFFFFFF:
                csize = values.pop(0)
            if offset == 0xFFFFFFFF:
                offset = values.pop(0)
        q += 4 + length
    n += 1
    mark = ''
    if name in WANT:
        mark = f'   <-- {WANT[name]}'
    elif name.startswith('20H392__') or name.startswith('20F66__'):
        mark = '   <-- the dyld shared cache directory'
    elif name.endswith('.dmg'):
        mark = '   (a disk image)'
    if mark or name.endswith('.dmg') or '/dyld' in name:
        print(f'  {name:<50} {usize:>12}{mark}')
    p += 46 + nl + el + cl
print(f'\n{n} members')
