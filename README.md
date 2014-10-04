photosorter
===========

[![Build Status](https://travis-ci.org/dbader/photosorter.svg?branch=master)](https://travis-ci.org/dbader/photosorter) [![Coverage Status](https://coveralls.io/repos/dbader/photosorter/badge.png?branch=master)](https://coveralls.io/r/dbader/photosorter?branch=master)

A little Python daemon to keep my photos organized on Dropbox.

It watches a *source directory* for modifications and moves new image files to a *target directory* depending on when the photo was taken, using EXIF data and creation date as a fallback.

Directory and file names follow a simple naming convention (`YYYY-MM/YYYY-MM-DD hh:mm:ss.ext`) that keeps everything neatly organized. Duplicates are detected and ignored based on their SHA1 hash. Photos taken in the same instant get deduplicated by adding a suffix (`-1`, `-2`, etc) to their filenames.

The result looks somewhat like this:
```
├── 2013
│   ├── 2013-01
│   │   ├── 2013-01-05\ 13.24.45.jpg
│   │   ├── 2013-01-05\ 14.25.54.jpg
│   │   ├── 2013-01-05\ 21.28.48-1.jpg
│   │   ├── 2013-01-06\ 16.05.02.jpg
│   │   ├── 2013-01-06\ 19.59.25.jpg
│   │   ├── 2013-01-06\ 20.40.28.jpg
│   │   ├── 2013-01-06\ 21.14.38.jpg
│   │   ├── 2013-01-08\ 11.45.51.jpg
│   ├── 2013-02
│   |   ├─ ...
│   ├── ...
│   └── 2013-12
├── 2014
│   ├── 2014-01
│   ├── 2014-02
│   ├── ...
│   └── 2014-12
├── ...
```

I use `~/Dropbox/Camera Uploads` as the source directory and `~/Dropbox/Photos` as the target. This means I can use Dropbox's phone apps to automatically upload and organize new photos.

Inspired by
- http://simplicitybliss.com/exporting-your-iphoto-library-to-dropbox/
- https://github.com/wting/exifrenamer
- http://chambersdaily.com/learning-to-love-photo-management/

## Setup
    $ git clone git@github.com:dbader/photosorter.git
    $ cd photosorter
    $ virtualenv venv
    $ . venv/bin/activate
    $ pip install -r requirements.txt
    $ pip install -r dev-requirements.txt
    $ py.test

## Run

Watch `src_dir` and sort incoming photos into `dest_dir`.

    $ ./sorter.py src_dir dest_dir

## Run on startup

1. Move `photosorter.conf.example` to `/etc/init` as `photosorter.conf`
   and edit it to suit your needs by replacing the user, source and target
   directories.
2. Run `$ sudo start photosorter`.
3. Check the logs at `/var/log/upstart/photosorter.log`.


## Meta

Daniel Bader – [@dbader_org](https://twitter.com/dbader_org) – mail@dbader.org

Distributed under the MIT license. See ``LICENSE`` for more information.

https://github.com/dbader/photosorter
