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

import argparse
import io
import json
import logging
import mock
import os
from testfixtures import LogCapture
import unittest
import sys

import context
import utils
import trakt_helper

import helper.parser


class TestHelperParser(utils._TestCase):

    def test_parser_class_KeepLineBreaksFormatter(self):
        obj = helper.parser.KeepLineBreaksFormatter(None)

        txt = obj._fill_text('this is my\ntext to be filled', 10, 0)
        self.assertEqual('this is my\ntext to be\nfilled', txt)

    def test_parser_class_ActionYesNo(self):
        with self.assertRaises(ValueError) as e:
            obj = helper.parser.ActionYesNo(
                option_strings=['testoption'],
                dest='testdest',
                default=None,
                required=False,
                help=None,
            )
        self.assertEqual('Yes/No arguments must be prefixed with --',
                         str(e.exception))

        with self.assertRaises(ValueError) as e:
            obj = helper.parser.ActionYesNo(
                option_strings=['--testoption', 'testoption2'],
                dest='testdest',
                default=None,
                required=False,
                help=None,
            )
        self.assertEqual('Yes/No arguments must be prefixed with --',
                         str(e.exception))
       
        with self.assertRaises(ValueError) as e:
            obj = helper.parser.ActionYesNo(
                option_strings=['--testoption', '--testoption2'],
                dest='testdest',
                default=None,
                required=False,
                help=None,
            )
        self.assertEqual('Only single argument is allowed with Yes/No action',
                         str(e.exception))

        obj = helper.parser.ActionYesNo(
            option_strings=['--testoption'],
            dest='testdest',
            default=True,
        )
        self.assertTrue(obj.default)

        obj = helper.parser.ActionYesNo(
            option_strings=['--no-testoption'],
            dest='testdest',
            default=False,
        )
        self.assertFalse(obj.default)

        # Test calling parser
        obj = helper.parser.ActionYesNo(
            option_strings=['--no-testoption',
                            '--extra1-testoption',
                            '--no-extra2-testoption',
                            '--extra3-no-testoption'],
            dest='testdest',
            default=None,
            required=False,
            help=None,
        )
        self.assertTrue(obj.default)

        mock_parser = mock.MagicMock()
        mock_namespace = mock.MagicMock()

        obj(parser=mock_parser, namespace=mock_namespace, values=[],
            option_strings='--testoption')
        self.assertTrue(mock_namespace.testdest)

        obj(parser=mock_parser, namespace=mock_namespace, values=[],
            option_strings='--no-testoption')
        self.assertFalse(mock_namespace.testdest)

        obj(parser=mock_parser, namespace=mock_namespace, values=[],
            option_strings='--extra1-testoption')
        self.assertEqual((True, 'extra1'), mock_namespace.testdest)

        obj(parser=mock_parser, namespace=mock_namespace, values=[],
            option_strings='--no-extra2-testoption')
        self.assertEqual((False, 'extra2'), mock_namespace.testdest)

        obj(parser=mock_parser, namespace=mock_namespace, values=[],
            option_strings='--extra3-no-testoption')
        self.assertEqual((False, 'extra3'), mock_namespace.testdest)

    @mock.patch('__builtin__.print')
    def test_parser_class_PrintVersion(self, mock_print):
        obj = helper.parser.PrintVersion(None, None, None)

        with self.assertRaises(SystemExit) as e:
            obj(parser=None, args=None, values=None, option_string=None)
        self.assertEqual('0', str(e.exception))
        mock_print.assert_called_once()
        mock_print.reset_mock()

        with mock.patch.object(helper.parser, '__build_date__', 'BUILDDATE'):
            with self.assertRaises(SystemExit) as e:
                obj(parser=None, args=None, values=None, option_string=None)
            self.assertEqual('0', str(e.exception))
            for call in mock_print.call_args_list:
                args, kwargs = call
                output = args[0].splitlines(False)
                self.assertTrue(
                    'Built on BUILDDATE' in output,
                    'Build date does not appear in version.')
            mock_print.assert_called_once()
            mock_print.reset_mock()

        with mock.patch.object(helper.parser, '__build_system_release__',
                               'BUILDSYSTEMRELEASE'):
            with self.assertRaises(SystemExit) as e:
                obj(parser=None, args=None, values=None, option_string=None)
            self.assertEqual('0', str(e.exception))
            for call in mock_print.call_args_list:
                args, kwargs = call
                output = args[0].splitlines(False)
                self.assertTrue(
                    'Built with BUILDSYSTEMRELEASE' in output,
                    'Build system release does not appear in version.')
            mock_print.assert_called_once()
            mock_print.reset_mock()

        with mock.patch.object(helper.parser, '__build_date__', 'BUILDDATE'), \
                mock.patch.object(helper.parser, '__build_system_release__',
                                  'BUILDSYSTEMRELEASE'):
            with self.assertRaises(SystemExit) as e:
                obj(parser=None, args=None, values=None, option_string=None)
            self.assertEqual('0', str(e.exception))
            for call in mock_print.call_args_list:
                args, kwargs = call
                output = args[0].splitlines(False)
                self.assertTrue(
                    'Built on BUILDDATE with BUILDSYSTEMRELEASE' in output,
                    'Build date and build system release do not appear in '
                    'version.')
            mock_print.assert_called_once()
            mock_print.reset_mock()

        with mock.patch.object(helper.parser, '__version__', 'VERSION'):
            with self.assertRaises(SystemExit) as e:
                obj(parser=None, args=None, values=None,
                    option_string='--short-version')
            self.assertEqual('0', str(e.exception))
            mock_print.assert_called_with('VERSION')
            mock_print.assert_called_once()
            mock_print.reset_mock()

    @mock.patch('platform.system')
    def test_parser_parse_args(self, mock_system):
        mock_system.return_value = 'Windows'
        argv = ['--keep-alive', 'date']
        preargs, left_args = helper.parser.parse_args(argv, preparse=True)
        self.assertTrue(isinstance(preargs, argparse.Namespace),
                        'Preparsed args is not of Namespace type')
        self.assertTrue(getattr(preargs, 'keep_alive', None),
                        'keep_alive value is not set in Namespace')
        self.assertListEqual(left_args, ['date'])

        mock_system.return_value = 'Linux'
        preargs, left_args = helper.parser.parse_args(argv, preparse=True)
        self.assertTrue(isinstance(preargs, argparse.Namespace),
                        'Preparsed args is not of Namespace type')
        self.assertIsNone(getattr(preargs, 'keep_alive', None),
                          'keep_alive value is set in Namespace')
        self.assertListEqual(left_args, argv)

        argv = ['date']
        preargs, left_args = helper.parser.parse_args(argv, preparse=True)
        self.assertTrue(isinstance(preargs, argparse.Namespace),
                        'Preparsed args is not of Namespace type')
        self.assertListEqual(left_args, argv)

        argv = ['date']
        args, func, params = helper.parser.parse_args(argv)
        self.assertTrue(isinstance(args, argparse.Namespace),
                        'Parsed args is not of Namespace type')
        self.assertDictEqual({
            'from_timezone': None,
            'from_format': '%s.%f',
            'format': [],
            'from_date': None,
            'timezone': None
        }, params)
        self.assertEqual(args.command, 'date')


if __name__ == '__main__':
    unittest.main()
