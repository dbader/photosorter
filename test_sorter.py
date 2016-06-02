"""
Unit tests for sorter.py

Run with:

$ py.test -f test_sorter.py -v

"""
from datetime import datetime
from unittest import mock  # type: ignore
import os
import time
import unittest

import sorter


def set_mtime(path, dt):
    mtime = time.mktime(dt.timetuple())
    os.utime(path, (-1, mtime))


def reset_mtimes():
    """
    Reset the mtimes on our test files because git doesn't keep them.
    """
    set_mtime(
        'test_examples/2004-05-07 20.16.31.jpg',
        datetime(2004, 5, 7, 11, 16, 31))
    set_mtime(
        'test_examples/2006-09-09 07.00.24.jpg',
        datetime(2006, 9, 8, 22, 0, 24))
    set_mtime(
        'test_examples/2006-09-09 07.00.24-alt.jpg',
        datetime(2006, 9, 9, 7, 0, 24))
    set_mtime(
        'test_examples/2014-02-06 09.15.17.jpg',
        datetime(2014, 2, 6, 9, 15, 17))
    set_mtime('test_examples/no-exif.jpg', datetime(2014, 2, 23, 21, 47, 14))
    set_mtime('test_examples/test.png', datetime(2014, 3, 8, 18, 31, 35))


class RenamerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_mtimes()

    def test_basename_from_datetime(self):
        case = sorter.basename_from_datetime(datetime(2004, 5, 7, 20, 16, 31))
        expected = '2004-05-07 20.16.31'
        self.assertEquals(case, expected)

    def test_filename_from_datetime(self):
        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31), 'test_examples/img0001.jpg')
        expected = '2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31), 'test_examples/somefile.JPG')
        expected = '2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31), 'test_examples/no-ext')
        expected = '2004-05-07 20.16.31'
        self.assertEquals(case, expected)

    def test_folder_from_datetime(self):
        self.assertEquals(
            sorter.folder_from_datetime(datetime(2014, 2, 7)), '2014/2014-02')

    def test_path_from_datetime(self):
        case = sorter.path_from_datetime(
            '', datetime(2004, 5, 7, 20, 16, 31), 'test_examples/img0001.jpg')
        expected = '2004/2004-05/2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.path_from_datetime(
            '/home/user/Dropbox', datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/img0001.jpg')
        expected = '/home/user/Dropbox/2004/2004-05/2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

    def test_dest_path(self):
        case = sorter.dest_path(
            '/home/user/Dropbox', 'test_examples/2004-05-07 20.16.31.jpg')
        expected = '/home/user/Dropbox/2004/2004-05/2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

    def test_ignore_non_images(self):
        self.assertTrue(sorter.is_valid_filename('test.png'))
        self.assertTrue(sorter.is_valid_filename('test.jpg'))
        self.assertTrue(sorter.is_valid_filename('test.jpeg'))
        self.assertTrue(sorter.is_valid_filename('test.jPeg'))
        self.assertTrue(sorter.is_valid_filename('test.PNG'))
        self.assertTrue(sorter.is_valid_filename('test.JPG'))
        self.assertFalse(sorter.is_valid_filename('test.img'))
        self.assertFalse(sorter.is_valid_filename('test.txt'))
        self.assertFalse(sorter.is_valid_filename('test'))

    def test_resolve_duplicate(self):
        case = sorter.resolve_duplicate(
            'test_examples/root/2006/2006-09/2006-09-09 07.00.24.jpg')
        expected = 'test_examples/root/2006/2006-09/2006-09-09 07.00.24-2.jpg'
        self.assertEquals(case, expected)

        case = sorter.resolve_duplicate(
            'test_examples/root/2006/2006-09/2006-09-09 07.00.25.jpg')
        expected = 'test_examples/root/2006/2006-09/2006-09-09 07.00.25.jpg'
        self.assertEquals(case, expected)

    @mock.patch('os.makedirs')
    @mock.patch('shutil.move')
    def test_move_file(self, move_mock, makedirs_mock):
        sorter.move_file('/root', 'test_examples/2006-09-09 07.00.24.jpg')
        makedirs_mock.assert_called_with('/root/2006/2006-09')
        move_mock.assert_called_with(
            'test_examples/2006-09-09 07.00.24.jpg',
            '/root/2006/2006-09/2006-09-09 07.00.24.jpg')

        # Ignore non-images
        makedirs_mock.reset_mock()
        move_mock.reset_mock()
        sorter.move_file('/root', 'test_examples/no_image.txt')
        makedirs_mock.assert_not_called()
        move_mock.assert_not_called()

        # Don't overwrite existing images.
        makedirs_mock.reset_mock()
        move_mock.reset_mock()
        sorter.move_file(
            'test_examples/root/', 'test_examples/2006-09-09 07.00.24-alt.jpg')
        makedirs_mock.assert_called_with('test_examples/root/2006/2006-09')
        move_mock.assert_called_with(
            'test_examples/2006-09-09 07.00.24-alt.jpg',
            'test_examples/root/2006/2006-09/2006-09-09 07.00.24-2.jpg')

        # Ignore duplicates.
        makedirs_mock.reset_mock()
        move_mock.reset_mock()
        sorter.move_file(
            'test_examples/root/', 'test_examples/2006-09-09 07.00.24.jpg')
        self.assertFalse(makedirs_mock.called)
        self.assertFalse(move_mock.called)


class CreationDateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_mtimes()

    def test_file_creation_date(self):
        self.assertEquals(
            sorter.file_creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 11, 16, 31))

        self.assertEquals(
            sorter.file_creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 8, 22, 0, 24))

        self.assertEquals(
            sorter.file_creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17))

    def test_exif_creation_date(self):
        self.assertEquals(
            sorter.exif_creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 20, 16, 31))

        self.assertEquals(
            sorter.exif_creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 9, 7, 0, 24))

        self.assertEquals(
            sorter.exif_creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17))

        self.assertIsNone(
            sorter.exif_creation_date('test_examples/no-exif.jpg'), )

        self.assertIsNone(
            sorter.exif_creation_date('test_examples/test.png'), )

    def test_creation_date(self):
        self.assertEquals(
            sorter.creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 20, 16, 31))

        self.assertEquals(
            sorter.creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 9, 7, 0, 24))

        self.assertEquals(
            sorter.creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17))

        self.assertEquals(
            sorter.creation_date('test_examples/no-exif.jpg'),
            datetime(2014, 2, 23, 21, 47, 14))

        self.assertEquals(
            sorter.creation_date('test_examples/test.png'),
            datetime(2014, 3, 8, 18, 31, 35))


class HashCacheTests(unittest.TestCase):
    def test(self):
        cache = sorter.HashCache()
        target_folder = 'test_examples/root/2006/2006-09/'
        f1 = 'test_examples/root/2006/2006-09/2006-09-09 07.00.24.jpg'
        f2 = 'test_examples/2014-02-06 09.15.17.jpg'

        self.assertTrue(cache.has_file(target_folder, f1))
        self.assertFalse(cache.has_file(target_folder, f2))


class ScriptTests(unittest.TestCase):
    def test_parse_args(self):
        args = sorter.parse_args('sorter.py src/ dest/'.split())
        self.assertEqual(args.src_folder, 'src/')
        self.assertEqual(args.dest_folder, 'dest/')

    def test_main(self):
        with self.assertRaises(SystemExit):
            sorter.main(['sorter.py'])
