#!/usr/bin/env python
# encoding: utf-8
#
# Unit test for filenameparser.py
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
import filenameparser


class FilenameParserTest(unittest.TestCase):
    def _filenameparser_parse_tv_test(self, expected, string):
        parsed = filenameparser.parse_tv(string)

        self.assertEqual(expected, parsed)

    def _filenameparser_parse_movie_test(self, expected, string):
        parsed = filenameparser.parse_movie(string)

        self.assertEqual(expected, parsed)

    def test_tvshows(self):
        assertionErrors = []

        shows = (
            (
                "house.of.cards.308.hdtv-lol.mp4",
                {'episodes': [8], 'season': 3, 'show': 'house of cards'}
            ),
            (
                "House.of.Cards.S03E01.HDTV.x264-ASAP.mp4",
                {'episodes': [1], 'season': 3, 'show': 'House of Cards'}
            ),
            (
                "The Flash (2014) - S01E14 - hdtv h264.mp4",
                {'episodes': [14], 'season': 1, 'show': 'The Flash (2014)'}
            ),
            (
                "Arrow - 2x06 - Keep Your Enemies Closer.mp4",
                {'episodes': [6], 'season': 2, 'show': 'Arrow'}
            ),
            (
                "Burn Notice - 1x11-12 - Dead Drop - Loose Ends.avi",
                {'episodes': [11, 12], 'season': 1, 'show': 'Burn Notice'}
            ),
            (
                "Burn Notice - 1x11x12 - Dead Drop - Loose Ends.avi",
                {'episodes': [11, 12], 'season': 1, 'show': 'Burn Notice'}
            ),
            (
                "Burn.Notice-S01E11E12.Dead.Drop-Loose.Ends.avi",
                {'episodes': [11, 12], 'season': 1, 'show': 'Burn Notice'}
            ),
            (
                "Pushing Daisies 211.mp4",
                {'episodes': [11], 'season': 2, 'show': 'Pushing Daisies'}
            ),
            (
                "suits.409.hdtv-lol.mp4",
                {'episodes': [9], 'season': 4, 'show': 'suits'}
            ),
            (
                "the.flash.2014.103.hdtv-lol.mp4",
                {'episodes': [3], 'season': 1, 'show': 'the flash 2014'}
            ),
        )

        for filename, expected in shows:
            self._filenameparser_parse_tv_test(expected, filename)

    def test_movie(self):
        movies = (
            (
                "Anchorman.The.Legend.Of.Ron.Burgundy.2004." +
                "720p.BrRip.x264.BOKUTOX.YIFY.mp4",
                {
                    'title': 'Anchorman The Legend Of Ron Burgundy',
                    'year': '2004'
                }
            ),
            (
                "Caddyshack.1980.720p.BRrip.x264.YIFY.mp4",
                {'title': 'Caddyshack', 'year': '1980'}
            ),
            (
                "Contagion (2011) BDrip 720p ENG-ITA x264 bluray -Shiv@.mp4",
                {'title': 'Contagion', 'year': '2011'}
            ),
            (
                "Donnie Darko[2001]DvDrip[Eng]-Bugz.avi",
                {'title': 'Donnie Darko', 'year': '2001'}
            ),
            (
                "Knocked-Up 2007-720p.avi",
                {'title': 'Knocked-Up', 'year': '2007'}
            ),
            (
                "Kung.Fu.Hustle[2004]DvDrip[Eng]-aXXo.avi",
                {'title': 'Kung Fu Hustle', 'year': '2004'}
            ),
            (
                "Miss.Pettigrew.Lives.for.a.Day.2008.576p." +
                "BDRip.x264-HANDJOB.mp4",
                {'title': 'Miss Pettigrew Lives for a Day', 'year': '2008'}
            ),
            (
                "Silence of the Lambs-480.mp4",
                {'title': 'Silence of the Lambs-480', 'year': None}
            ),
        )

        for filename, expected in movies:
            self._filenameparser_parse_movie_test(expected, filename)
