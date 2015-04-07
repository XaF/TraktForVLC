#!/usr/bin/env python
# encoding: utf-8
#
# Unit test for TraktClient.py
#
# Copyright (C) 2015        Raphaël Beamonte <raphael.beamonte@gmail.com>
#
# This file is part of TraktForVLC.  TraktForVLC is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
# or see <http://www.gnu.org/licenses/>.

# Python lib imports
import os
import sys
import unittest

# Add TraktToVLC directory to path
sys.path.append(
    os.path.dirname(  # TraktToVLC directory
        os.path.dirname(  # tests directory
            os.path.abspath(__file__)
        )
    )
)

# Local imports
import TraktClient


class TraktClientTest(unittest.TestCase):
    def __get_mock_client(self):
        TraktClient.api_url = (
            "https://private-anon-e4bdfe2c3-trakt.apiary-mock.com/")
        tc = TraktClient.TraktClient("username", "password", "client_id")
        return tc

    def test_mock_startWatching(self):
        tc = self.__get_mock_client()
        ret = tc.startWatching('imdbID', 10, False)

        self.assertTrue(u'action' in ret
                        and ret[u'action'] == u'start')

    def test_mock_pauseWatching(self):
        tc = self.__get_mock_client()
        ret = tc.pauseWatching('imdbID', 10, False)

        self.assertTrue(u'action' in ret
                        and ret[u'progress'] < 80
                        and ret[u'action'] == u'pause')

    def test_mock_stopWatching(self):
        tc = self.__get_mock_client()
        ret = tc.stopWatching('imdbID', 99.9, False)

        self.assertTrue(u'action' in ret
                        and ret[u'progress'] >= 80
                        and ret[u'action'] == u'scrobble')

    def test_mock_cancelWatching(self):
        tc = self.__get_mock_client()
        ret = tc.cancelWatching('imdbID', False)

        self.assertTrue(u'action' in ret
                        and ret[u'action'] == u'start')
