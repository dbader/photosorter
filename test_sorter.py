"""
Unit tests for sorter.py

Run with:

$ py.test -f test_sorter.py -v

"""
from datetime import datetime
import unittest

import mock

import sorter


class RenamerTests(unittest.TestCase):
    def test_basename_from_datetime(self):
        case = sorter.basename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31)
        )
        expected = '2004-05-07 20.16.31'
        self.assertEquals(case, expected)

    def test_filename_from_datetime(self):
        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/img0001.jpg'
        )
        expected = '2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/somefile.JPG'
        )
        expected = '2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.filename_from_datetime(
            datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/no-ext'
        )
        expected = '2004-05-07 20.16.31'
        self.assertEquals(case, expected)

    def test_folder_from_datetime(self):
        self.assertEquals(
            sorter.folder_from_datetime(datetime(2014, 2, 7)),
            '2014/2014-02'
        )

    def test_path_from_datetime(self):
        case = sorter.path_from_datetime(
            '',
            datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/img0001.jpg'
        )
        expected = '2004/2004-05/2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

        case = sorter.path_from_datetime(
            '/home/user/Dropbox',
            datetime(2004, 5, 7, 20, 16, 31),
            'test_examples/img0001.jpg'
        )
        expected = '/home/user/Dropbox/2004/2004-05/2004-05-07 20.16.31.jpg'
        self.assertEquals(case, expected)

    def test_dest_path(self):
        case = sorter.dest_path(
            '/home/user/Dropbox',
            'test_examples/2004-05-07 20.16.31.jpg'
        )
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

    # def test_duplicate_marker_index(self):
    #     self.assertEquals(
    #         sorter.duplicate_marker_index('2006-09-09 07.00.24-2.jpg'),
    #         2
    #     )
    #     self.assertEquals(
    #         sorter.duplicate_marker_index('2006-09-09 07.00.24-123.jpg'),
    #         123
    #     )
    #     self.assertEquals(
    #         sorter.duplicate_marker_index('2006-09-09 07.00.24.jpg'),
    #         None
    #     )
    #     self.assertEquals(
    #         sorter.duplicate_marker_index('2006-09-09 07.00.24-9.png'),
    #         9
    #     )

    def test_resolve_duplicate(self):
        case = sorter.resolve_duplicate(
            'test_examples/root/2006/2006-09/2006-09-09 07.00.24.jpg'
        )
        expected = 'test_examples/root/2006/2006-09/2006-09-09 07.00.24-2.jpg'
        self.assertEquals(case, expected)

        case = sorter.resolve_duplicate(
            'test_examples/root/2006/2006-09/2006-09-09 07.00.25.jpg'
        )
        expected = 'test_examples/root/2006/2006-09/2006-09-09 07.00.25.jpg'
        self.assertEquals(case, expected)

    @mock.patch('os.makedirs')
    @mock.patch('shutil.move')
    def test_move_file(self, move_mock, makedirs_mock):
        sorter.move_file('/root', 'test_examples/2006-09-09 07.00.24.jpg')
        makedirs_mock.assert_called_with('/root/2006/2006-09')
        move_mock.assert_called_with(
            'test_examples/2006-09-09 07.00.24.jpg',
            '/root/2006/2006-09/2006-09-09 07.00.24.jpg'
        )

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
            'test_examples/root/',
            'test_examples/2006-09-09 07.00.24.jpg'
        )
        makedirs_mock.assert_called_with('test_examples/root/2006/2006-09')
        move_mock.assert_called_with(
            'test_examples/2006-09-09 07.00.24.jpg',
            'test_examples/root/2006/2006-09/2006-09-09 07.00.24-2.jpg'
        )


class CreationDateTests(unittest.TestCase):
    def test_file_creation_date(self):
        self.assertEquals(
            sorter.file_creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 11, 16, 31)
        )

        self.assertEquals(
            sorter.file_creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 8, 22, 0, 24)
        )

        self.assertEquals(
            sorter.file_creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17)
        )

    def test_exif_creation_date(self):
        self.assertEquals(
            sorter.exif_creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 20, 16, 31)
        )

        self.assertEquals(
            sorter.exif_creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 9, 7, 0, 24)
        )

        self.assertEquals(
            sorter.exif_creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17)
        )

        self.assertIsNone(
            sorter.exif_creation_date('test_examples/no-exif.jpg'),
        )

        self.assertIsNone(
            sorter.exif_creation_date('test_examples/test.png'),
        )

    def test_creation_date(self):
        self.assertEquals(
            sorter.creation_date('test_examples/2004-05-07 20.16.31.jpg'),
            datetime(2004, 5, 7, 20, 16, 31)
        )

        self.assertEquals(
            sorter.creation_date('test_examples/2006-09-09 07.00.24.jpg'),
            datetime(2006, 9, 9, 7, 0, 24)
        )

        self.assertEquals(
            sorter.creation_date('test_examples/2014-02-06 09.15.17.jpg'),
            datetime(2014, 2, 6, 9, 15, 17)
        )

        self.assertEquals(
            sorter.creation_date('test_examples/no-exif.jpg'),
            datetime(2014, 2, 23, 21, 47, 14)
        )

        self.assertEquals(
            sorter.creation_date('test_examples/test.png'),
            datetime(2014, 3, 8, 18, 31, 35)
        )
