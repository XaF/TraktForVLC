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
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# Add TraktToVLC directory to path
sys.path.insert(
    0,
    os.path.dirname(  # TraktToVLC directory
        os.path.dirname(  # tests directory
            os.path.abspath(__file__)
        )
    )
)

# Local imports
import TraktClient
import requests


staging = {
    'available':        None,
    'client_id':        None,
    'client_secret':    None,
    'access_token':     None,
}


def is_staging_available():
    # Temporary disable the staging tests
    return False

    if staging['available'] is not None:
        return staging['available']

    info_url = os.environ.get('TRAKT_INFO_URL')
    staging['client_id'] = os.environ.get('TRAKT_CLIENT_ID')
    staging['client_secret'] = os.environ.get('TRAKT_CLIENT_SECRET')
    if (info_url is None
            or staging['client_id'] is None
            or staging['client_secret'] is None):
        staging['available'] = False
        return False

    stream = requests.get(info_url, verify=False)
    if not stream.ok:
        staging['available'] = False
        return False

    jdata = stream.json()
    if 'access_token' not in jdata:
        staging['available'] = False
        return False

    staging['access_token'] = jdata['access_token']
    staging['available'] = True
    return True


class TraktClientTest(unittest.TestCase):
    def __get_staging_client(self):
        TraktClient.api_url = "http://api.staging.trakt.tv/"

        tc = TraktClient.TraktClient({
            'pin':              None,
            'access_token':     staging['access_token'],
            'refresh_token':    None,
            'client_id':        staging['client_id'],
            'client_secret':    staging['client_secret'],
            'callback_token':   None,
            'app_version':      "TraktClient unit test",
            'app_date':         "unknown"
        })
        return tc

    def __scrobble_answer_gladiator(self, action, progress):
        return {
            u"action": action,
            u"progress": progress,
            u"sharing": {
                u"facebook": False,
                u"twitter": False,
                u"tumblr": False
            },
            u"movie": {
                u"title": u"Gladiator",
                u"year": 2000,
                u"ids": {
                    u"trakt": 463,
                    u"slug": u"gladiator-2000",
                    u"imdb": u"tt0172495",
                    u"tmdb": 98
                }
            }
        }

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_startWatching_Gladiator(self):
        tc = self.__get_staging_client()
        ret = tc.startWatching('tt0172495', 10, False)
        expected = self.__scrobble_answer_gladiator(u"start", 10)

        self.assertEqual(expected, ret)

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_pauseWatching_Gladiator_20(self):
        tc = self.__get_staging_client()
        ret = tc.pauseWatching('tt0172495', 20, False)
        expected = self.__scrobble_answer_gladiator(u"pause", 20)

        self.assertEqual(expected, ret)

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_pauseWatching_Gladiator_90(self):
        tc = self.__get_staging_client()
        ret = tc.pauseWatching('tt0172495', 90, False)
        expected = self.__scrobble_answer_gladiator(u"pause", 90)

        self.assertEqual(expected, ret)

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_stopWatching_Gladiator_70(self):
        tc = self.__get_staging_client()
        ret = tc.stopWatching('tt0172495', 70, False)
        expected = self.__scrobble_answer_gladiator(u"pause", 70)

        self.assertEqual(expected, ret)

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_stopWatching_Gladiator_90(self):
        tc = self.__get_staging_client()
        ret = tc.stopWatching('tt0172495', 90, False)
        expected = self.__scrobble_answer_gladiator(u"scrobble", 90)

        self.assertEqual(expected, ret)

    @unittest.skipUnless(
        is_staging_available(),
        "Staging configuration is not available"
    )
    def test_staging_cancelWatching_Gladiator(self):
        tc = self.__get_staging_client()
        ret = tc.cancelWatching('tt0172495', False)
        expected = self.__scrobble_answer_gladiator(u"start", 99.99)

        self.assertEqual(expected, ret)
