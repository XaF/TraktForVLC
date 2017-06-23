#!/usr/bin/env python
# encoding: utf-8
#
# Unit test for movie_info.py
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
from fuzzywuzzy import fuzz
import pprint
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

# Add tvdb_api directory to path
sys.path.append(os.path.abspath(
    os.path.join(*__file__.split('/')[:-1] + ['tvdb_api'])
))

# Local imports
import movie_info


class MovieInfoTest(unittest.TestCase):
    maxDiff = None

    def _cleanMovieDict(self, moviedict):
        if 'tomatoRating' in moviedict:
            moviedict['tomatoRating'] = -1
        if 'imdbRating' in moviedict:
            moviedict['imdbRating'] = -1
        return moviedict

    def _movie_info_test(self, expected, searchTitle, searchYear='',
                         searchDuration=None):
        search = movie_info.get_movie_info(
            None,
            searchTitle,
            searchYear,
            searchDuration
        )
        search = self._cleanMovieDict(search)

        if 'Plot' in search:
            if 'Plot' in expected:
                ratio = fuzz.partial_ratio(expected['Plot'], search['Plot'])
                self.assertEqual(
                    ratio > 90, True,
                    pprint.pformat(search, indent=4)
                )
                del expected['Plot']
            del search['Plot']

        self.assertEqual(expected, search)

    def _testTheAvengers2012(self, searchTitle, searchYear='',
                             searchDuration=None):
        expected = {
            'Director': u'Joss Whedon',
            'Plot': u"Earth's mightiest heroes must come together and " +
                    u"learn to fight as a team if they are to stop the " +
                    u"mischievous Loki and his alien army from enslaving " +
                    u"humanity.",
            'Runtime': 8580,
            'Title': u'The Avengers',
            'Year': 2012,
            'imdbID': u'tt0848228',
            'imdbRating': -1,
        }

        self._movie_info_test(expected, searchTitle,
                              searchYear, searchDuration)

    def test_the_avengers_2012(self):
        self._testTheAvengers2012("The Avengers", "2012")

    def test_the_avengers(self):
        self._testTheAvengers2012("The Avengers", "")

    def test_avengers_2012(self):
        self._testTheAvengers2012("Avengers", "2012")

    def test_avengers(self):
        self._testTheAvengers2012("Avengers", "", 8580)

    def _testTheDarkKnight2008(self, searchTitle, searchYear='',
                               searchDuration=None):
        expected = {
            'Director': u'Christopher Nolan',
            'Plot': u"When the menace known as the Joker emerges from his " +
                    u"mysterious past, he wreaks havoc and chaos on the " +
                    u"people of Gotham, the Dark Knight must accept one of " +
                    u"the greatest psychological and physical tests of his " +
                    u"ability to fight injustice.",
            'Runtime': 9120,
            'Title': u'The Dark Knight',
            'Year': 2008,
            'imdbID': u'tt0468569',
            'imdbRating': -1,
        }

        self._movie_info_test(expected, searchTitle,
                              searchYear, searchDuration)

    def _testTheDarkKnightRises2012(self, searchTitle, searchYear='',
                                    searchDuration=None):
        expected = {
            'Director': u'Christopher Nolan',
            'Plot': u"Eight years after the Joker's reign of anarchy, " +
                    u"the Dark Knight, with the help of the enigmatic " +
                    u"Selina, is forced from his imposed exile to save " +
                    u"Gotham City, now on the edge of total annihilation, " +
                    u"from the brutal guerrilla terrorist Bane.",
            'Runtime': 9840,
            'Title': u'The Dark Knight Rises',
            'Year': 2012,
            'imdbID': u'tt1345836',
            'imdbRating': -1,
        }

        self._movie_info_test(expected, searchTitle,
                              searchYear, searchDuration)

    def test_the_dark_knight_rises_2012(self):
        self._testTheDarkKnightRises2012("The Dark Knight Rises", "2012")

    def test_the_dark_knight_rises(self):
        self._testTheDarkKnightRises2012("The Dark Knight Rises", "")

    def test_the_dark_knight_2012(self):
        self._testTheDarkKnightRises2012("The Dark Knight", "2012")

    def test_dark_knight_2012(self):
        self._testTheDarkKnightRises2012("Dark Knight", "2012", 9840)

    def test_dark_knight(self):
        self._testTheDarkKnight2008("Dark Knight", "", 9120)

    def test_unexisting_movie(self):
        if sys.version_info[:2] >= (2, 7):
            with self.assertRaises(LookupError):
                movie_info.get_movie_info(
                    '',
                    "There's no way that movie exists",
                    "1968"
                )
        else:
            self.assertRaises(
                LookupError,
                lambda: movie_info.get_movie_info(
                    '',
                    "There's no way that movie exists",
                    "1968"
                )
            )
