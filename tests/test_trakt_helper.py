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
import logging
import mock
import unittest

import context
import utils
import trakt_helper

from helper.utils import CommandOutput


class TestTraktHelper(utils._TestCase):

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_run_returns_commandoutput(self, mock_run, mock_exit):
        params = {
        }
        argv = ['install']
        for k, v in params.items():
            if v is not None:
                k = k.replace('_', '-')
                argv.extend(['--{}'.format(k), str(v)])

        mock_run.return_value = CommandOutput(data='output', exit_code=2)

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_once()
            mock_exit.assert_called_with(2)

            mock_print.assert_called_once()
            mock_print.assert_called_with('"output"')

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_run_returns_int(self, mock_run, mock_exit):
        argv = ['install']

        mock_run.return_value = 1

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_once()
            mock_exit.assert_called_with(1)

            mock_print.assert_not_called()

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_run_returns_none(self, mock_run, mock_exit):
        argv = ['install']

        mock_run.return_value = None

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_once()
            mock_exit.assert_called_with(0)

            mock_print.assert_not_called()

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_run_exception(self, mock_run, mock_exit):
        argv = ['install']

        mock_run.side_effect = utils.TestException('an exception')

        with self.assertRaises(utils.TestException):
            trakt_helper.main(argv)

    @mock.patch('__builtin__.raw_input')
    @mock.patch('platform.system')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_noargs_not_windows(self, mock_run, mock_exit,
                                             mock_system, mock_input):
        argv = []

        mock_system.return_value = 'Linux'

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_once()
            mock_input.assert_not_called()

            mock_print.assert_not_called()

    @mock.patch('__builtin__.raw_input')
    @mock.patch('platform.system')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_noargs_windows(self, mock_run, mock_exit,
                                             mock_system, mock_input):
        argv = []

        mock_system.return_value = 'Windows'

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_once()
            mock_input.assert_called_once()

            mock_print.assert_called_with('Press a key to continue.')

    @mock.patch('logging.basicConfig')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.install.CommandInstall.run')
    def test_trakt_helper_logging_loglevel_install(self, mock_run, mock_exit,
                                                   mock_basicConfig):
        argv = ['install']
        trakt_helper.main(argv)

        mock_run.assert_called_once()
        mock_basicConfig.assert_called_with(
            format='%(asctime)s::%(levelname)s::%(message)s',
            level=logging.INFO)

    @mock.patch('logging.basicConfig')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.date.CommandDate.run')
    def test_trakt_helper_logging_loglevel_date(self, mock_run, mock_exit,
                                                mock_basicConfig):
        argv = ['date']
        trakt_helper.main(argv)

        mock_run.assert_called_once()
        mock_basicConfig.assert_called_with(
            format='%(asctime)s::%(levelname)s::%(message)s',
            level=logging.WARNING)

    @mock.patch('logging.basicConfig')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.date.CommandDate.run')
    def test_trakt_helper_logging_loglevel(self, mock_run, mock_exit,
                                           mock_basicConfig):
        argv = ['--loglevel', 'ERROR', 'date']
        trakt_helper.main(argv)

        mock_run.assert_called_once()
        mock_basicConfig.assert_called_with(
            format='%(asctime)s::%(levelname)s::%(message)s',
            level=logging.ERROR)

    @mock.patch('logging.basicConfig')
    @mock.patch('sys.exit')
    @mock.patch('helper.commands.date.CommandDate.run')
    def test_trakt_helper_logging_logfile(self, mock_run, mock_exit,
                                          mock_basicConfig):
        argv = ['--logfile', 'testlogfile', 'date']
        trakt_helper.main(argv)

        mock_run.assert_called_once()
        mock_basicConfig.assert_called_with(
            format='%(asctime)s::%(levelname)s::%(message)s',
            level=logging.WARNING,
            filename='testlogfile')

    @mock.patch.object(trakt_helper, '__name__', '__main__')
    @mock.patch('trakt_helper.parse_args')
    def test_trakt_helper_init(self, mock_parse_args):
        mock_parse_args.side_effect = utils.TestException('another exception')

        with self.assertRaises(utils.TestException):
            trakt_helper.init()


if __name__ == '__main__':
    unittest.main()
