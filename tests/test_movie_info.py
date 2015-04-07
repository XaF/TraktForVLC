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
    def _cleanMovieDict(self, moviedict):
        if 'tomatoRating' in moviedict:
            moviedict['tomatoRating'] = -1
        if 'imdbRating' in moviedict:
            moviedict['imdbRating'] = -1
        return moviedict

    def _movie_info_test(self, expected, searchTitle, searchYear=''):
        search = movie_info.get_movie_info(searchTitle, searchYear)
        search = self._cleanMovieDict(search)

        self.assertEqual(expected, search)

    def _testTheAvengers2012(self, searchTitle, searchYear=''):
        expected = {
            'Director': u'Joss Whedon',
            'Plot': u"Earth's mightiest heroes must come together and " +
                    u"learn to fight as a team if they are to stop the " +
                    u"mischievous Loki and his alien army from enslaving " +
                    u"humanity.",
            'Runtime': u'143 min',
            'Title': u'The Avengers',
            'Year': u'2012',
            'imdbID': u'tt0848228',
            'imdbRating': -1,
            'tomatoRating': -1,
        }

        self._movie_info_test(expected, searchTitle, searchYear)

    def test_the_avengers_2012(self):
        self._testTheAvengers2012("The Avengers", "2012")

    def test_the_avengers(self):
        self._testTheAvengers2012("The Avengers", "")

    def test_avengers_2012(self):
        self._testTheAvengers2012("Avengers", "2012")

    def test_avengers(self):
        self._testTheAvengers2012("Avengers", "")

    def _testTheDarkKnight2008(self, searchTitle, searchYear=''):
        expected = {
            'Director': u'Christopher Nolan',
            'Plot': u"When the menace known as the Joker wreaks havoc and " +
                    u"chaos on the people of Gotham, the caped crusader " +
                    u"must come to terms with one of the greatest " +
                    u"psychological tests of his ability to fight " +
                    u"injustice.",
            'Runtime': u'152 min',
            'Title': u'The Dark Knight',
            'Year': u'2008',
            'imdbID': u'tt0468569',
            'imdbRating': -1,
            'tomatoRating': -1
        }

        self._movie_info_test(expected, searchTitle, searchYear)

    def _testTheDarkKnightRises2012(self, searchTitle, searchYear=''):
        expected = {
            'Director': u'Christopher Nolan',
            'Plot': u"Eight years after the Joker's reign of anarchy, " +
                    u"the Dark Knight is forced to return from his imposed " +
                    u"exile to save Gotham City from the brutal guerrilla " +
                    u"terrorist Bane with the help of the enigmatic Catwoman.",
            'Runtime': u'165 min',
            'Title': u'The Dark Knight Rises',
            'Year': u'2012',
            'imdbID': u'tt1345836',
            'imdbRating': -1,
            'tomatoRating': -1,
        }

        self._movie_info_test(expected, searchTitle, searchYear)

    def test_the_dark_knight_rises_2012(self):
        self._testTheDarkKnightRises2012("The Dark Knight Rises", "2012")

    def test_the_dark_knight_rises(self):
        self._testTheDarkKnightRises2012("The Dark Knight Rises", "")

    def test_the_dark_knight_2012(self):
        self._testTheDarkKnightRises2012("The Dark Knight", "2012")

    def test_dark_knight_2012(self):
        self._testTheDarkKnightRises2012("Dark Knight", "2012")

    def test_dark_knight(self):
        self._testTheDarkKnight2008("Dark Knight", "")

    def test_unexisting_movie(self):
        if sys.version_info[:2] >= (2, 7):
            with self.assertRaises(LookupError):
                movie_info.get_movie_info(
                    "There's no way that movie exists",
                    "1968"
                )
        else:
            self.assertRaises(
                LookupError,
                lambda: movie_info.get_movie_info(
                    "There's no way that movie exists",
                    "1968"
                )
            )
