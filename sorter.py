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
import argparse
import collections
import datetime
import hashlib
import logging
import os
import queue
import re
import shutil
import sys
import threading
import time

import exifread
import watchdog
import watchdog.events
import watchdog.observers

from typing import List, Optional, Mapping, Dict, Set, Tuple  # noqa


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('photosorter')


class HashCache:
    """
    Gives a quick answer to the question if there's an identical file
    in the given target folder.
    """
    def __init__(self) -> None:
        # folder -> (hashes, filename -> hash)
        self.hashes = collections.defaultdict(
            lambda: (set(), dict())
        )  # type: Mapping[str, Tuple[Set[str], Dict[str, str]]]

    def has_file(self, target_folder: str, path: str) -> bool:
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

    def _add_file(self, path: str):
        # Bail out if we already have a hash for the file at `path`.
        folder = self._target_folder(path)
        if path in self.hashes[folder][1]:
            return

        file_hash = self._hash(path)

        basename = os.path.basename(path)
        self.hashes[folder][0].add(file_hash)
        self.hashes[folder][1][basename] = file_hash

    @staticmethod
    def _hash(path: str) -> str:
        hasher = hashlib.sha1()
        with open(path, 'rb') as f:
            data = f.read()
            hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def _target_folder(path: str) -> str:
        return os.path.dirname(path)

    @staticmethod
    def _files_in_folder(folder_path: str) -> List[str]:
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


def move_file(root_folder: str, path: str):
    if not os.path.exists(path):
        logger.debug('File no longer exists: %s', path)
        return

    if not is_valid_filename(path):
        logger.debug('Not a valid filename: %s', path)
        return

    dst = dest_path(root_folder, path)
    dirs = os.path.dirname(dst)

    if hash_cache.has_file(dirs, path):
        logger.info('%s is a duplicate, skipping', path)
        return

    try:
        os.makedirs(dirs)
        logger.debug('Created folder %s', dirs)
    except OSError as ex:
        # Catch "File exists"
        if ex.errno != 17:
            raise ex

    logger.info('Moving %s to %s', path, dst)
    shutil.move(path, dst)


def resolve_duplicate(path: str) -> str:
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
            logger.debug('Deduplicating %s to %s', path, new_path)
            break
        dedup_index += 1

    return new_path


def is_valid_filename(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.mov']


def dest_path(root_folder: str, path: str) -> str:
    cdate = creation_date(path)
    path = path_from_datetime(root_folder, cdate, path)
    return resolve_duplicate(path)


def path_from_datetime(root_folder: str, dt: datetime.datetime,
                       path: str) -> str:
    folder = folder_from_datetime(dt)
    filename = filename_from_datetime(dt, path)
    return os.path.join(root_folder, folder, filename)


def folder_from_datetime(dt: datetime.datetime) -> str:
    return dt.strftime('%Y' + os.sep + '%Y-%m')


def filename_from_datetime(dt: datetime.datetime, path: str) -> str:
    """
    Returns basename + original extension.
    """
    base = basename_from_datetime(dt)
    ext = os.path.splitext(path)[1]
    return base + ext.lower()


def basename_from_datetime(dt: datetime.datetime) -> str:
    """
    Returns a string formatted like this '2004-05-07 20.16.31'.
    """
    return dt.strftime('%Y-%m-%d %H.%M.%S')


def creation_date(path: str) -> datetime.datetime:
    exif_date = exif_creation_date(path)
    if exif_date:
        return exif_date
    return file_creation_date(path)


def file_creation_date(path: str) -> datetime.datetime:
    """
    Use mtime as creation date because ctime returns the
    the time when the file's inode was last modified; which is
    wrong and almost always later.
    """
    mtime = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(mtime)


def exif_creation_date(path: str) -> Optional[datetime.datetime]:
    try:
        ts = exif_creation_timestamp(path)
    except MissingExifTimestampError:
        logger.debug('Missing exif timestamp', exc_info=True)
        return None

    try:
        return exif_timestamp_to_datetime(ts)
    except BadExifTimestampError:
        logger.debug('Failed to parse exif timestamp', exc_info=True)
        return None


class BadExifTimestampError(Exception):
    pass


class MissingExifTimestampError(Exception):
    pass


def exif_creation_timestamp(path: str) -> str:
    with open(path, 'rb') as f:
        tags = exifread.process_file(f, details=False)

    if 'EXIF DateTimeOriginal' in tags:
        return str(tags['EXIF DateTimeOriginal'])
    elif 'EXIF DateTimeDigitized' in tags:
        return str(tags['EXIF DateTimeDigitized'])

    raise MissingExifTimestampError()


def exif_timestamp_to_datetime(ts: str) -> datetime.datetime:
    elements = [int(_) for _ in re.split(':| ', ts)]

    if len(elements) != 6:
        raise BadExifTimestampError

    return datetime.datetime(elements[0], elements[1], elements[2],
                             elements[3], elements[4], elements[5])


class EventHandler(watchdog.events.PatternMatchingEventHandler):
    def __init__(self, shared_queue: queue.Queue, target_folder: str) -> None:
        self.shared_queue = shared_queue
        self.target_folder = target_folder
        super().__init__(ignore_directories=True)

    def on_created(self, event):
        self.shared_queue.put(event.src_path)

    def on_modified(self, event):
        self.shared_queue.put(event.src_path)

    def on_moved(self, event):
        self.shared_queue.put(event.src_path)


class MoveFileThread(threading.Thread):
    def __init__(self, shared_queue: queue.Queue, dest_folder: str) -> None:
        super().__init__()
        self.shared_queue = shared_queue
        self.dest_folder = dest_folder
        self.is_running = True

    def run(self) -> None:
        while self.is_running:
            try:
                file_path = self.shared_queue.get(block=False, timeout=1)
            except queue.Empty:  # type: ignore
                continue
            logger.debug('MoveFileThread got file %s', file_path)
            try:
                move_file(self.dest_folder, file_path)
            except Exception as ex:
                logger.exception(ex)
            self.shared_queue.task_done()
        logger.debug('MoveFileThread exiting')

    def stop(self) -> None:
        self.is_running = False


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('src_folder')
    parser.add_argument('dest_folder')
    return parser.parse_args(argv[1:])


def run(src_folder: str, dest_folder: str):
    shared_queue = queue.Queue()  # type: queue.Queue[str]
    move_thread = MoveFileThread(shared_queue, dest_folder)
    move_thread.start()

    event_handler = EventHandler(shared_queue, dest_folder)
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, src_folder, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('Shutting down')
        pass

    observer.stop()
    observer.join()
    logger.debug('Observer thread stopped')

    shared_queue.join()
    move_thread.stop()
    move_thread.join()


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    logger.info('Watching %s for changes, destination is %s',
                args.src_folder, args.dest_folder)
    run(args.src_folder, args.dest_folder)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
