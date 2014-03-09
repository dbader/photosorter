#!/usr/bin/env python
"""
Inspired by https://github.com/wting/exifrenamer

watchmedo shell-command --wait --recursive --ignore-directories \
    --command='./sorter.py test/dst "${watch_src_path}"' test/src

todo:
    X ensure we don't overwrite files; append a counter: -1, -2, -3 etc.
    - check other files in the overwrite chain and skip if sha1s are equal
    - fall back to now() if exif time is too old to be true
    - normalize filenames: jpeg -> jpg
"""
import datetime
import os
import re
import shutil

import exifread


def move_file(root_folder, path):
    if not os.path.exists(path):
        return

    if not is_valid_filename(path):
        return

    dst = dest_path(root_folder, path)
    dirs = os.path.dirname(dst)
    try:
        os.makedirs(dirs)
        print('Created folder %s' % dirs)
    except OSError as e:
        # Catch "File exists"
        if e.errno != 17:
            raise e

    print('Moving %s to %s' % (path, dst))
    shutil.move(path, dst)


# def duplicate_marker_index(path):
#     match = re.match(r'.*-(\d+).[a-z]+$', path)
#     if not match:
#         return None
#     return int(match.groups()[0])


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
            print('Deduplicating %s to %s' % (path, new_path))
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
    elements = map(int, re.split(':| ', ts))

    if len(elements) != 6:
        raise BadExifTimestampError

    return datetime.datetime(*elements)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target_folder')
    parser.add_argument('filename')
    args = parser.parse_args()
    move_file(args.target_folder, args.filename)
