#!/usr/bin/env python
# encoding: utf-8
#
# TraktForVLC, to link VLC watching to trakt.tv updating
#
# Copyright (C) 2017-2018   Raphaël Beamonte <raphael.beamonte@gmail.com>
#
# This file is part of TraktForVLC.  TraktForVLC is free software:
# you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation,
# version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
# or see <http://www.gnu.org/licenses/>.

from __future__ import (
    absolute_import,
    print_function,
)

import json
import mock
from testfixtures import LogCapture
import unittest

import context
import utils
import trakt_helper

from helper.utils import CommandOutput
from helper.commands.date import CommandDate


class TestHelperCommandDate(utils._TestCase):

    def test_command_date_default(self):
        params = {
            'format': [],
            'from_date': None,
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self._partial_match({
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_date(self):
        params = {
            'format': [],
            'from_date': '2018-06-25T15:37:02.424242Z',
            'from_format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'from_timezone': None,
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '2018-06-25T15:37:02.424242Z',
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_date_from_tz(self):
        params = {
            'format': [],
            'from_date': '2018-06-25T11:37:02.424242Z',
            'from_format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'from_timezone': 'EST5EDT',
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '2018-06-25T15:37:02.424242Z',
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_date_format(self):
        params = {
            'format': ['%d/%m/%Y'],
            'from_date': '2018-06-25T15:37:02.424242Z',
            'from_format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'from_timezone': None,
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '25/06/2018',
            'format': '%d/%m/%Y',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_format_s(self):
        params = {
            'format': [],
            'from_date': '1529941022.424242',
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '2018-06-25T15:37:02.424242Z',
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_format_s_to_tz(self):
        params = {
            'format': [],
            'from_date': '1529941022.424242',
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': 'EST5EDT',
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '2018-06-25T11:37:02.424242Z',
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'EST5EDT',
        }, output.data)

    def test_command_date_from_format_s_to_format_s(self):
        params = {
            'format': [
                '%s.%f',
            ],
            'from_date': '1529941022.424242',
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '1529941022.424242',
            'format': '%s.%f',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_from_format_s_to_format_s_to_tz(self):
        params = {
            'format': [
                '%s.%f',
            ],
            'from_date': '1529941022.424242',
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': 'EST5EDT',
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '1529941022.424242',
            'format': '%s.%f',
            'timezone': 'EST5EDT',
        }, output.data)

    def test_command_date_from_format_s_from_tz_to_format_s(self):
        params = {
            'format': [],
            'from_date': '1529941022.424242',
            'from_format': '%s.%f',
            'from_timezone': 'EST5EDT',
            'timezone': None,
        }
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertDictEqual({
            'date': '2018-06-25T15:37:02.424242Z',
            'format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'timezone': 'UTC',
        }, output.data)

    def test_command_date_multi_format(self):
        params = {
            'format': [
                '%d/%m/%Y %Hh%M\'%S\'\'',
                '%s',
                '%Y-%m-%d %H:%M:%S',
            ],
            'from_date': '2018-06-25T11:37:02.424242Z',
            'from_format': '%Y-%m-%dT%H:%M:%S.%fZ',
            'from_timezone': 'EST5EDT',
            'timezone': None,
        }
        expected = [
            {
                'date': '25/06/2018 15h37\'02\'\'',
                'format': '%d/%m/%Y %Hh%M\'%S\'\'',
                'timezone': 'UTC',
            },
            {
                'date': '1529941022',
                'format': '%s',
                'timezone': 'UTC',
            },
            {
                'date': '2018-06-25 15:37:02',
                'format': '%Y-%m-%d %H:%M:%S',
                'timezone': 'UTC',
            },
        ]
        command = CommandDate()
        output = command.run(**params)
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')
        self.assertListEqual(expected, output.data)

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.date.CommandDate.run')
    def test_trakt_helper_date(self, mock_run, mock_exit):
        params = {
            'format': [],
            'from_date': None,
            'from_format': '%s.%f',
            'from_timezone': None,
            'timezone': None,
        }
        argv = ['date']
        mock_run.return_value = CommandOutput(data='output')

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_with(**params)
            mock_exit.assert_called_with(0)

            mock_print.assert_called_once()
            mock_print.assert_called_with('"output"')


if __name__ == '__main__':
    unittest.main()
