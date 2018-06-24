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
import unittest


class TestException(Exception):
    pass


class _TestCase(unittest.TestCase):

    def _partial_match(self, expected, match, message=None, path=None):
        if path is None:
            path = []
        textpath = ('{}: '.format(', '.join(str(p) for p in path))
                    if path else '')

        self.assertEqual(type(expected), type(match),
                         '{msg}{path}expected ({typeexp}) and match '
                         '({typemat}) are not of the same type'.format(
                             msg='{}: '.format(message) if message else '',
                             path=textpath,
                             typeexp=type(expected).__name__,
                             typemat=type(match).__name__))

        if isinstance(expected, dict):
            for k, v in expected.items():
                self.assertTrue(k in match,
                                '{msg}{path}key \'{key}\' not in match'.format(
                                    msg='{}: '.format(message) if message
                                        else '',
                                    path=textpath,
                                    key=k))

                self._partial_match(v, match[k], path=path + [k],
                                    message=message)
        elif isinstance(expected, list) or isinstance(expected, tuple):
            self.assertEqual(len(expected), len(match),
                             '{msg}{path}expected {ltype} ({lenexp}) and '
                             'match {ltype} ({lenmat}) are not of the same '
                             'length'.format(
                                 msg='{}: '.format(message) if message
                                     else '',
                                 path=textpath,
                                 ltype=type(expected).__name__,
                                 lenexp=len(expected),
                                 lenmat=len(match)))

            for i, v in enumerate(expected):
                self._partial_match(v, match[i], path=path + [i],
                                    message=message)
        else:
            self.assertEqual(expected, match,
                             u'{msg}{path}expected ({valexp}) and match '
                             u'({valmat}) values are different'.format(
                                 msg='{}: '.format(message) if message
                                     else '',
                                 path=textpath,
                                 valexp=expected,
                                 valmat=match))
