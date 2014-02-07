__author__ = 'clarkmatthew'

import requests


class DownloadPart(object):
    def __init__(self,
                 get_url,
                 part_index,
                 bytes_start,
                 bytes_end,
                 chunk_size=8192):
        self.get_url = get_url
        self.part_index = part_index
        self.bytes_start = long(bytes_start)
        self.bytes_end = long(bytes_end)
        self.size = long(self.bytes_end-self.bytes_start)
        self.chunk_size = chunk_size

    def download(self, dest_fileobj, chunk_size=None):
        bytes = 0
        chunk_size = chunk_size or self.chunk_size
        r = requests.get(self.get_url, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size):
            print 'chunk' + str(chunk)
            dest_fileobj.write(chunk)
            bytes += len(chunk)
        dest_fileobj.flush()
        return bytes

    def __repr__(self):
        return 'DownloadPart({0}, {1}, {2}, {3})'.format(
            repr(self.part_index), repr(self.get_url),
            repr(self.bytes_start), repr(self.bytes_end))
