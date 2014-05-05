photosorter
===========

[![Build Status](https://travis-ci.org/dbader/photosorter.svg?branch=master)](https://travis-ci.org/dbader/photosorter) [![Coverage Status](https://coveralls.io/repos/dbader/photosorter/badge.png?branch=master)](https://coveralls.io/r/dbader/photosorter?branch=master)

A little Python daemon to keep my photos organized on Dropbox.

It watches a *source directory* for modifications and moves new image files to a *target directory* depending on when the photo was taken, using EXIF data and creation date as a fallback.

The result looks like this:
```
├── 2013
│   ├── 2013-01
│   ├── 2013-02
│   ├── ...
│   └── 2013-12
├── 2014
│   ├── 2014-01
│   ├── 2014-02
│   ├── ...
│   └── 2014-12
├── ...
```

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

Distributed under the MIT license. See ``LICENSE.txt`` for more information.

https://github.com/dbader/photosorter
