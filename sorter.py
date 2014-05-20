#!/usr/bin/env python
"""
photosorter - https://github.com/dbader/photosorter
---------------------------------------------------

A little Python daemon to keep my photos organized on Dropbox.

It watches a *source directory* for modifications and moves new image
files to a *target directory* depending on when the photo was taken,
using EXIF data and creation date as a fallback.

Inspired by
    - http://simplicitybliss.com/exporting-your-iphoto-library-to-dropbox/
    - https://github.com/wting/exifrenamer
    - http://chambersdaily.com/learning-to-love-photo-management/

"""
import collections
import datetime
import hashlib
import os
import re
import shutil
import sys
import time

import exifread
import watchdog
import watchdog.events
import watchdog.observers


class HashCache(object):
    """
    Gives a quick answer to the question if there's an identical file
    in the given target folder.

    """
    def __init__(self):
        # folder -> (hashes, filename -> hash)
        self.hashes = collections.defaultdict(lambda: (set(), dict()))

    def has_file(self, target_folder, path):
        # Strip trailing slashes etc.
        target_folder = os.path.normpath(target_folder)

        # Update the cache by ensuring that we have the hashes of all
        # files in the target folder. `_add_file` is smart enough to
        # skip any files we already hashed.
        for f in self._files_in_folder(target_folder):
            self._add_file(f)

        # Hash the new file at `path`.
        file_hash = self._hash(path)

        # Check if we already have an identical file in the target folder.
        return file_hash in self.hashes[target_folder][0]

    def _add_file(self, path):
        # Bail out if we already have a hash for the file at `path`.
        folder = self._target_folder(path)
        if path in self.hashes[folder][1]:
            return

        file_hash = self._hash(path)

        basename = os.path.basename(path)
        self.hashes[folder][0].add(file_hash)
        self.hashes[folder][1][basename] = file_hash

    @staticmethod
    def _hash(path):
        hasher = hashlib.sha1()
        with open(path, 'rb') as f:
            data = f.read()
            hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def _target_folder(path):
        return os.path.dirname(path)

    @staticmethod
    def _files_in_folder(folder_path):
        """
        Iterable with full paths to all files in `folder_path`.
        """
        try:
            names = (
                os.path.join(folder_path, f) for f in os.listdir(folder_path)
            )
            return [f for f in names if os.path.isfile(f)]
        except OSError:
            return []


hash_cache = HashCache()


def move_file(root_folder, path):
    if not os.path.exists(path):
        return

    if not is_valid_filename(path):
        return

    dst = dest_path(root_folder, path)
    dirs = os.path.dirname(dst)

    if hash_cache.has_file(dirs, path):
        print('%s is a duplicate, skipping' % path)
        return

    try:
        os.makedirs(dirs)
        print('Created folder %s' % dirs)
    except OSError as e:
        # Catch "File exists"
        if e.errno != 17:
            raise e

    print('Moving %s to %s' % (path, dst))
    shutil.move(path, dst)


def resolve_duplicate(path):
    if not os.path.exists(path):
        return path

    basename = os.path.basename(path)
    filename, ext = os.path.splitext(basename)
    dirname = os.path.dirname(path)
    dedup_index = 1

    while True:
        new_fname = '%s-%i%s' % (filename, dedup_index, ext)
        new_path = os.path.join(dirname, new_fname)
        if not os.path.exists(new_path):
            # print('Deduplicating %s to %s' % (path, new_path))
            break
        dedup_index += 1

    return new_path


def is_valid_filename(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png']


def dest_path(root_folder, path):
    cdate = creation_date(path)
    path = path_from_datetime(root_folder, cdate, path)
    return resolve_duplicate(path)


def path_from_datetime(root_folder, dt, path):
    folder = folder_from_datetime(dt)
    filename = filename_from_datetime(dt, path)
    return os.path.join(root_folder, folder, filename)


def folder_from_datetime(dt):
    return dt.strftime('%Y' + os.sep + '%Y-%m')


def filename_from_datetime(dt, path):
    '''
    Returns basename + original extension.
    '''
    base = basename_from_datetime(dt)
    ext = os.path.splitext(path)[1]
    return base + ext.lower()


def basename_from_datetime(dt):
    '''
    Returns a string formatted like this '2004-05-07 20.16.31'.
    '''
    return dt.strftime('%Y-%m-%d %H.%M.%S')


def creation_date(path):
    exif_date = exif_creation_date(path)
    if exif_date:
        return exif_date
    return file_creation_date(path)


def file_creation_date(path):
    # Use mtime as creation date because ctime returns the
    # the time when the file's inode was last modified; which is
    # wrong and almost always later.
    mtime = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(mtime)


def exif_creation_date(path):
    try:
        ts = exif_creation_timestamp(path)
    except MissingExifTimestampError as e:
        print(e)
        return None

    try:
        return exif_timestamp_to_datetime(ts)
    except BadExifTimestampError:
        print(e)
        return None


class BadExifTimestampError(Exception):
    pass


class MissingExifTimestampError(Exception):
    pass


def exif_creation_timestamp(path):
    with open(path, 'rb') as f:
        tags = exifread.process_file(f, details=False)

    if 'EXIF DateTimeOriginal' in tags:
        return str(tags['EXIF DateTimeOriginal'])
    elif 'EXIF DateTimeDigitized' in tags:
        return str(tags['EXIF DateTimeDigitized'])

    raise MissingExifTimestampError()


def exif_timestamp_to_datetime(ts):
    elements = [int(_) for _ in re.split(':| ', ts)]

    if len(elements) != 6:
        raise BadExifTimestampError

    return datetime.datetime(*elements)


class EventHandler(watchdog.events.PatternMatchingEventHandler):
    def __init__(self, target_folder):
        self.target_folder = target_folder
        super(EventHandler, self).__init__(ignore_directories=True)

    def on_created(self, event):
        move_file(self.target_folder, event.src_path)

    def on_modified(self, event):
        move_file(self.target_folder, event.src_path)

    def on_moved(self, event):
        move_file(self.target_folder, event.dest_path)


def parse_args(argv):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('src_folder')
    parser.add_argument('dest_folder')
    return parser.parse_args(argv[1:])


def run(src_folder, dest_folder):
    event_handler = EventHandler(dest_folder)
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, src_folder, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def main(argv):
    args = parse_args(argv)
    run(args.src_folder, args.dest_folder)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
