photosorter
===========

![](https://api.travis-ci.org/dbader/photosorter.png) ![](https://coveralls.io/repos/dbader/photosorter/badge.png)


Keeps my photos organized on Dropbox.

## Setup
    $ git clone git@github.com:dbader/photosorter.git
    $ cd photosorter
    $ virtualenv venv
    $ . venv/bin/activate
    $ pip install -r requirements.txt
    $ py.test

## Run

Watch `src_dir` and sort incoming photos into `dst_dir`.

    $ watchmedo shell-command --wait --recursive --ignore-directories --command='./sorter.py dst_dir "${watch_src_path}"' src_dir
