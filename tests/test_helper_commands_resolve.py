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

from copy import deepcopy
import json
import mock
from testfixtures import LogCapture
import unittest

import context
import utils
import trakt_helper

from helper.utils import CommandOutput
from helper.commands.resolve import (
    CommandResolve,
    parse_filename,
    ResolveException,
)


class TestHelperCommandResolve(utils._TestCase):

    _default_media_by_type = {
        'movie': 'Notorious (1946).avi',
        'episode': 'The Flash (2014) - S04E19 - Fury Rogue.mkv',
        'multiepisode': 'Marvel\'s Agents of S.H.I.E.L.D. - '
                        'S05E01E02 - Orientation.mkv',
        'anime': '[HorribleSubs] Dragon Ball Super - 112 [480p].mkv',
    }

    _test_media_info = {
        'Notorious (1946).avi': {
            'meta': {
                'setting': ' HAS_INDEX IS_INTERLEAVED',
                'filename': 'Notorious (1946).avi',
                'Software': 'VirtualDubMod 1.5.4.1 (build 2178/release)',
            },
            'params': {
                'duration': 6132,
                'oshash': '6763a1dba52355e0',
                'size': 733468672,
            },
            'parser': {
                'movie': {
                    'title': u'Notorious',
                    'type': 'movie',
                    'year': u'1946',
                },
            },
            'check_hash': [
                {
                    'SeenCount': '197',
                    'MovieImdbID': '0038787',
                    'MovieKind': 'movie',
                    'SeriesSeason': '0',
                    'SeriesEpisode': '0',
                    'MovieHash': '6763a1dba52355e0',
                    'SubCount': '23',
                    'MovieName': 'Notorious',
                    'MovieYear': '1946',
                },
            ],
            'resolve': [
                {
                    u'base': {
                        u'id': u'/title/tt0038787/',
                        u'imdbid': u'tt0038787',
                        u'title': u'Notorious',
                        u'titleType': u'movie',
                        u'tmdbid': 303,
                        u'year': 1946,
                        u'runningTimeInMinutes': 101,
                    },
                },
            ],
        },
        'The Flash (2014) - S04E19 - Fury Rogue.mkv': {
            'meta': {
                'episodeNumber': '19',
                'filename': 'The Flash (2014) - S04E19 - Fury Rogue.mkv',
                'seasonNumber': '04',
                'showName': 'The Flash (2014) -',
                'title': 'The Flash (2014) - S04E19',
            },
            'params': {
                'duration': 2505.043968,
                'oshash': '79418a844a7ff565',
                'size': 322031764,
            },
            'parser': {
                'movie': {
                    'year': u'2014',
                    'type': 'movie',
                    'title': u'The Flash',
                },
                'episode': {
                    'absepisodes': False,
                    'season': 4,
                    'episodes': [
                        19,
                    ],
                    'type': 'episode',
                    'show': u'The Flash (2014)',
                },
            },
            'check_hash': [
                {
                    'SeenCount': '4002',
                    'MovieImdbID': '6741970',
                    'MovieKind': 'episode',
                    'SeriesSeason': '4',
                    'SeriesEpisode': '19',
                    'MovieHash': '79418a844a7ff565',
                    'SubCount': '25',
                    'MovieName': '"The Flash" Fury Rogue',
                    'MovieYear': '2018',
                },
            ],
            'resolve': [
                {
                    u'base': {
                        u'episode': 19,
                        u'id': u'/title/tt6741970/',
                        u'imdbid': u'tt6741970',
                        u'nextEpisode': u'/title/tt6741974/',
                        u'parentTitle': {
                            u'id': u'/title/tt3107288/',
                            u'imdbid': u'tt3107288',
                            u'title': u'The Flash',
                            u'titleType': u'tvSeries',
                            u'year': 2014,
                        },
                        u'previousEpisode': u'/title/tt6741968/',
                        u'runningTimeInMinutes': 42,
                        u'season': 4,
                        u'seriesStartYear': 2014,
                        u'title': u'Fury Rogue',
                        u'titleType': u'tvEpisode',
                        u'tmdbid': 1458444,
                        u'year': 2018,
                    },
                },
            ],
            'url': {
                'trakt_search':
                    'https://api.trakt.tv/search/tvdb/6569894?type=episode',
                'trakt_show':
                    'https://api.trakt.tv/shows/the-flash-2014/seasons/4/'
                    'episodes/19?extended=full',
            },
        },
        'Marvel\'s Agents of S.H.I.E.L.D. - S05E01E02 - Orientation.mkv': {
            'meta': {
                'showName': 'Marvel\'s Agents of S H I E L D  -',
                'filename': 'Marvel\'s Agents of S.H.I.E.L.D. - '
                            'S05E01E02 - Orientation.mkv',
                'seasonNumber': '05',
                'title': 'Marvel\'s Agents of S H I E L D  - S05E01',
                'episodeNumber': '01',
            },
            'params': {
                'duration': 5024.520192,
                'oshash': '04d28f798ba3dd87',
                'size': 426653710,
            },
            'parser': {
                'episode': {
                    'absepisodes': False,
                    'episodes': [
                         1,
                         2,
                    ],
                    'season': 5,
                    'show': u"Marvel's Agents of S.H.I.E.L.D",
                    'type': 'episode',
                },
                'movie': {
                    'title': u"Marvel's Agents of S.H.I.E.L.D  - "
                             u"S05E01E02 - Orientation",
                    'type': 'movie',
                    'year': None,
                }
            },
            'check_hash': [
                {
                    'SeenCount': '2035',
                    'MovieImdbID': '6878538',
                    'MovieKind': 'episode',
                    'SeriesSeason': '5',
                    'SeriesEpisode': '1',
                    'MovieHash': '04d28f798ba3dd87',
                    'SubCount': '30',
                    'MovieName': '"Agents of S.H.I.E.L.D." '
                                 'Orientation: Part 1',
                    'MovieYear': '2017',
                },
            ],
            'resolve': [
                {
                    u'base': {
                        u'season': 5,
                        u'year': 2017,
                        u'seriesStartYear': 2013,
                        u'imdbid': u'tt6878538',
                        u'id': u'/title/tt6878538/',
                        u'previousEpisode': u'/title/tt5916882/',
                        u'parentTitle': {
                            u'titleType': u'tvSeries',
                            u'imdbid': u'tt2364582',
                            u'id': u'/title/tt2364582/',
                            u'title': u'Agents of S.H.I.E.L.D.',
                            u'year': 2013,
                        },
                        u'nextEpisode': u'/title/tt7178426/',
                        u'titleType': u'tvEpisode',
                        u'title': u'Orientation: Part 1',
                        u'episode': 1,
                        u'tvdbid': 6276702,
                        u'runningTimeInMinutes': 42,
                        u'tmdbid': 1377164,
                    },
                },
                {
                    u'base':{
                        u'season': 5,
                        u'year': 2017,
                        u'seriesStartYear': 2013,
                        u'imdbid': u'tt7178426',
                        u'id': u'/title/tt7178426/',
                        u'previousEpisode': u'/title/tt6878538/',
                        u'parentTitle': {
                            u'titleType': u'tvSeries',
                            u'imdbid': u'tt2364582',
                            u'id': u'/title/tt2364582/',
                            u'title': u'Agents of S.H.I.E.L.D.',
                            u'year': 2013,
                        },
                        u'nextEpisode': u'/title/tt7183060/',
                        u'titleType': u'tvEpisode',
                        u'title': u'Orientation: Part 2',
                        u'episode': 2,
                        u'tvdbid': 6407853,
                        u'runningTimeInMinutes': 43,
                        u'tmdbid': 1378310,
                    },
                },
            ],
        },
        '[HorribleSubs] Dragon Ball Super - 112 [480p].mkv': {
            'meta': {
                'BPS': '112',
                'DURATION': '00:22:39.780000000',
                'NUMBER_OF_BYTES': '19064',
                'NUMBER_OF_FRAMES': '297',
                '_STATISTICS_TAGS': 'BPS DURATION NUMBER_OF_FRAMES '
                                    'NUMBER_OF_BYTES',
                '_STATISTICS_WRITING_APP': 'no_variable_data',
                '_STATISTICS_WRITING_DATE_UTC': '1970-01-01 00:00:00',
                'filename': '[HorribleSubs] Dragon Ball Super - 112 [480p].mkv'
            },
            'params': {
                'duration': 1388.300032,
                'oshash': 'da0e964de631213d',
                'size': 150362405,
            },
            'parser': {
                'episode': {
                    'absepisodes': True,
                    'episodes': [
                        112,
                    ],
                    'season': None,
                    'show': u'Dragon Ball Super',
                    'type': 'episode',
                },
                'movie': {
                    'title': u'Dragon Ball Super - 112 [480p]',
                    'type': 'movie',
                    'year': None,
                },
            },
            'check_hash': [
                {
                    'SeenCount': '3',
                    'MovieImdbID': '7541994',
                    'MovieKind': 'episode',
                    'SeriesSeason': '1',
                    'SeriesEpisode': '112',
                    'MovieHash': 'da0e964de631213d',
                    'SubCount': '1',
                    'MovieName': '"Dragon Ball Super" A Saiyan\'s '
                                 'Vow! Vegeta\'s Resolution!!',
                    'MovieYear': '2017',
                },
                {
                    'SeenCount': '1',
                    'MovieImdbID': '5017206',
                    'MovieKind': 'episode',
                    'SeriesSeason': '1',
                    'SeriesEpisode': '12',
                    'MovieHash': 'da0e964de631213d',
                    'SubCount': '1',
                    'MovieName': u'"Dragon Ball Super" Uch\xfb ga '
                                 u'kudakeru!? Gekitotsu! Hakai-shin '
                                 u'Tai S\xfbp\xe2 Saiya-jin Goddo!',
                    'MovieYear': '2015',
                },
            ],
            'resolve': [
                {
                    u'base': {
                        u'episode': 112,
                        u'id': u'/title/tt7541994/',
                        u'imdbid': u'tt7541994',
                        u'nextEpisode': u'/title/tt7541998/',
                        u'parentTitle': {
                            u'id': u'/title/tt4644488/',
                            u'imdbid': u'tt4644488',
                            u'title': u'Dragon Ball Super: Doragon bôru cho',
                            u'titleType': u'tvSeries',
                            u'year': 2015,
                        },
                        u'previousEpisode': u'/title/tt7480166/',
                        u'season': 1,
                        u'seriesEndYear': 2018,
                        u'seriesStartYear': 2015,
                        u'title': u'A Saiyan\'s Vow! Vegeta\'s Resolution!!',
                        u'titleType': u'tvEpisode',
                        u'year': 2017,
                    },
                },
            ],
        },
        None: {
            'resolve': [
                {
                    u'base': {
                        u'runningTimeInMinutes': 122,
                        u'title': u'Notorious',
                        u'year': 2009,
                        u'titleType': u'movie',
                        u'id': u'/title/tt0472198/',
                    },
                },
                {
                    u'base': {
                        u'runningTimeInMinutes': 101,
                        u'title': u'Notorious',
                        u'year': 1946,
                        u'titleType': u'movie',
                        u'id': u'/title/tt0038787/',
                    },
                },
            ],
        }
    }

    _test_title_info = {
        'Notorious': [
            {
                u'year': u'2018',
                u'type': u'TV series',
                u'imdb_id': u'tt6233618',
                u'title': (u'Unsolved: The Murders of Tupac and '
                           u'the Notorious B.I.G.'),
            },
            {
                u'year': u'2009',
                u'type': u'feature',
                u'imdb_id': u'tt0472198',
                u'title': u'Notorious',
            },
            {
                u'year': u'1946',
                u'type': u'feature',
                u'imdb_id': u'tt0038787',
                u'title': u'Notorious',
            },
            {
                u'year': u'2016',
                u'type': u'TV series',
                u'imdb_id': u'tt5519574',
                u'title': u'Notorious',
            },
            {
                u'year': u'2005',
                u'type': u'feature',
                u'imdb_id': u'tt0404802',
                u'title': u'The Notorious Bettie Page',
            },
            {
                u'year': u'2017',
                u'type': u'feature',
                u'imdb_id': u'tt7518466',
                u'title': u'Conor McGregor: Notorious',
            },
            {
                u'year': u'2013',
                u'type': u'TV series',
                u'imdb_id': u'tt2245029',
                u'title': u'Deception',
            },
        ],
    }

    _test_tvdb_info = {
        'The Flash (2014)': {
            'seriesName': 'The Flash (2014)',
            'aliases': [],
            4: {
                19: {
                    u'dvdEpisodeNumber': 19,
                    u'airedSeasonID': 715402,
                    u'lastUpdated': 1527787276,
                    u'id': 6569894,
                    u'dvdSeason': 4,
                    u'airedSeason': 4,
                    u'firstAired': u'2018-04-24',
                    u'airedEpisodeNumber': 19,
                    u'episodeName': u'Fury Rogue',
                    u'absoluteNumber': 88,
                },
            },
        },
    }

    _test_requests_get = {
        'https://api.trakt.tv/search/tvdb/6569894?type=episode': {
            'status_code': 200,
            'reason': 'OK',
            'json': [
                {
                    'type': 'episode',
                    'score': 1000,
                    'episode': {
                        'season': 4,
                        'number': 19,
                        'title': 'Fury Rogue',
                        'ids': {
                            'trakt': 2795858,
                            'tvdb': 6569894,
                            'imdb': 'tt6741970',
                            'tmdb': 1458444,
                            'tvrage': 0,
                        },
                    },
                    'show': {
                        'title': 'The Flash',
                        'year': 2014,
                        'ids': {
                            'trakt': 60300,
                            'slug': 'the-flash-2014',
                            'tvdb': 279121,
                            'imdb': 'tt3107288',
                            'tmdb': 60735,
                            'tvrage': 36939,
                        },
                    },
                },
            ],
        },
        'https://api.trakt.tv/shows/the-flash-2014/seasons/4/'
        'episodes/19?extended=full': {
            'status_code': 200,
            'reason': 'OK',
            'json': {
                'season': 4,
                'number': 19,
                'title': 'Fury Rogue',
                'ids': {
                    'trakt': 2795858,
                    'tvdb': 6569894,
                    'imdb': 'tt6741970',
                    'tmdb': 1458444,
                    'tvrage': 0,
                },
                'first_aired': '2018-04-25T00:00:00.000Z',
                'runtime': 42,
            },
        },
    }

    def _mock_parser(self, filename):
         return self._test_media_info.get(filename, {}).get('parser', False)

    def _mock_imdb_get_title(self, imdbid):
        compare_id = '/title/{}/'.format(imdbid)
        for medias in self._test_media_info.values():
            for media in medias['resolve']:
                if media['base']['id'] == compare_id:
                    return media
        raise utils.TestException('Test LookupError for imdbid = {}'.format(
            imdbid))

    def _mock_imdb_search_for_title(self, title):
        results = self._test_title_info.get(title)
        if results:
            return results
        raise utils.TestException('Test LookupError for title = {}'.format(
            title))

    def _mock_check_hash(self, oshashes):
        data = {}
        for oshash in oshashes:
            for media in self._test_media_info.values():
                if media.get('params', {}).get('oshash') == oshash:
                    data.setdefault(oshash, []).extend(media['check_hash'])
        return {'status': '200 OK', 'seconds': 0.006, 'data': data or []}

    def _mock_tvdb(self, *args, **kwargs):
        mm = mock.MagicMock()
        mm.__getitem__.side_effect = self._test_tvdb_info.__getitem__
        mm.__iter__.side_effect = self._test_tvdb_info.__iter__
        mm.__contains__.side_effect = self._test_tvdb_info.__contains__
        mm.search.side_effect = self._mock_tvdb_search
        return mm

    def _mock_tvdb_search(self, show):
        if show in self._test_tvdb_info:
            return [{'seriesName': show}, ]
        return []

    def _mock_requests_get(self, url, *args, **kwargs):
        if not url in self._test_requests_get:
            raise utils.TestException(
                'URL not available for tests: {}'.format(url))

        mm = mock.MagicMock()
        for k, v in self._test_requests_get[url].items():
            if k == 'json':
                getattr(mm, k).return_value = v
            else:
                setattr(mm, k, v)
        return mm

    def _test_media_resolution(self, params, expected):
        # Run the command
        resolved = CommandResolve().run(**params)

        # Check the results
        try:
            self.assertTrue(resolved.data,
                            'Resolution output is not True')
            self.assertTrue(isinstance(resolved.data, list),
                            'Resolution output is not a list')
            self.assertEqual(len(expected), len(resolved.data),
                             'Resolution output does not contain '
                             '{} element(s) ({} element(s) returned)'.format(
                                 len(expected), len(resolved.data)))

            for i, result in enumerate(resolved.data):
                self.assertTrue(isinstance(result, dict),
                                'Resolution output element [{}] is not '
                                'a dictionary'.format(i))

                self._partial_match(expected[i], result)
        except AssertionError, e:
            raise AssertionError('{}\n\nEXPECTED:\n{}\n\nGOT:\n{}'.format(
                str(e),
                json.dumps(expected, sort_keys=True, indent=4),
                json.dumps(resolved.data, sort_keys=True, indent=4)))

    # @mock.patch('helper.commands.resolve.parse_filename')
    # @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    # @mock.patch('imdbpie.Imdb')
    # @mock.patch('tvdb_api.Tvdb')
    # def test_movie_all_parameters(self, mock_parser, mock_hash, mock_imdb,
                                  # mock_tvdb):
        # # Test details
        # params = {
            # 'trakt_api_key': context.trakt_api_key,
            # 'meta': json.dumps({
                # 'setting': ' HAS_INDEX IS_INTERLEAVED',
                # 'filename': 'Notorious (1946).avi',
                # 'Software': 'VirtualDubMod 1.5.4.1 (build 2178/release)',
            # }),
            # 'duration': 6132,
            # 'oshash': '6763a1dba52355e0',
            # 'size': 733468672,
        # }
        # expected = [
            # {
                # u'base': {
                    # u'id': u'/title/tt0038787/',
                    # u'imdbid': u'tt0038787',
                    # u'title': u'Notorious',
                    # u'titleType': u'movie',
                    # u'tmdbid': 303,
                    # u'year': 1946,
                # },
            # },
        # ]

        # # Run the test
        # self._test_media_resolution(params, expected)

    # def test_movie_all_parameters(self):
        # # Test details
        # params = {
            # 'trakt_api_key': context.trakt_api_key,
            # 'meta': json.dumps({
                # 'setting': ' HAS_INDEX IS_INTERLEAVED',
                # 'filename': 'Notorious (1946).avi',
                # 'Software': 'VirtualDubMod 1.5.4.1 (build 2178/release)',
            # }),
            # 'duration': 6132,
            # 'oshash': '6763a1dba52355e0',
            # 'size': 733468672,
        # }
        # expected = [
            # {
                # u'base': {
                    # u'id': u'/title/tt0038787/',
                    # u'imdbid': u'tt0038787',
                    # u'title': u'Notorious',
                    # u'titleType': u'movie',
                    # u'tmdbid': 303,
                    # u'year': 1946,
                # },
            # },
        # ]

        # # Run the test
        # self._test_media_resolution(params, expected)

    # def test_anime_all_parameters(self):
        # # Test details
        # params = {
            # 'trakt_api_key': context.trakt_api_key,
            # 'meta': json.dumps({
                # 'BPS': '112',
                # 'DURATION': '00:22:39.780000000',
                # 'NUMBER_OF_BYTES': '19064',
                # 'NUMBER_OF_FRAMES': '297',
                # '_STATISTICS_TAGS': 'BPS DURATION NUMBER_OF_FRAMES '
                                    # 'NUMBER_OF_BYTES',
                # '_STATISTICS_WRITING_APP': 'no_variable_data',
                # '_STATISTICS_WRITING_DATE_UTC': '1970-01-01 00:00:00',
                # 'filename': '[HorribleSubs] Dragon Ball Super - 112 [480p].mkv'
            # }),
            # 'duration': 1388.300032,
            # 'oshash': 'da0e964de631213d',
            # 'size': 150362405,
        # }
        # expected = [
            # {
                # u'base': {
                    # u'episode': 112,
                    # u'id': u'/title/tt7541994/',
                    # u'imdbid': u'tt7541994',
                    # u'nextEpisode': u'/title/tt7541998/',
                    # u'parentTitle': {
                        # u'id': u'/title/tt4644488/',
                        # u'imdbid': u'tt4644488',
                        # u'title': u'Dragon Ball Super: Doragon bôru cho',
                        # u'titleType': u'tvSeries',
                        # u'year': 2015,
                    # },
                    # u'previousEpisode': u'/title/tt7480166/',
                    # u'season': 1,
                    # u'seriesEndYear': 2018,
                    # u'seriesStartYear': 2015,
                    # u'title': u'A Saiyan\'s Vow! Vegeta\'s Resolution!!',
                    # u'titleType': u'tvEpisode',
                    # u'year': 2017,
                # },
            # },
        # ]

        # # Run the test
        # with LogCapture() as l:
            # self._test_media_resolution(params, expected)

            # l.check_present(
                # ('helper.commands.extraids', 'WARNING',
                 # u'Unable to find series Dragon Ball Super: Doragon bôru cho, '
                 # u'season 1, episode 112 on TheTVDB'),
            # )

    # def test_episode_all_parameters(self):
        # # Test details
        # params = {
            # 'trakt_api_key': context.trakt_api_key,
            # 'meta': json.dumps({
                # 'episodeNumber': '19',
                # 'filename': 'The Flash (2014) - S04E19 - Fury Rogue.mkv',
                # 'seasonNumber': '04',
                # 'showName': 'The Flash (2014) -',
                # 'title': 'The Flash (2014) - S04E19',
            # }),
            # 'duration': 2505.043968,
            # 'oshash': '79418a844a7ff565',
            # 'size': 322031764,
        # }
        # expected = [
            # {
		# u'base': {
		    # u'episode': 19,
		    # u'id': u'/title/tt6741970/',
		    # u'imdbid': u'tt6741970',
		    # u'nextEpisode': u'/title/tt6741974/',
		    # u'parentTitle': {
			# u'id': u'/title/tt3107288/',
			# u'imdbid': u'tt3107288',
			# u'title': u'The Flash',
			# u'titleType': u'tvSeries',
			# u'year': 2014,
		    # },
		    # u'previousEpisode': u'/title/tt6741968/',
		    # u'runningTimeInMinutes': 42,
		    # u'season': 4,
		    # u'seriesStartYear': 2014,
		    # u'title': u'Fury Rogue',
		    # u'titleType': u'tvEpisode',
		    # u'tmdbid': 1458444,
		    # u'year': 2018,
		# },
            # },
        # ]

        # # Run the test
        # self._test_media_resolution(params, expected)

    # def test_multi_episodes_all_parameters(self):
        # # Test details
        # params = {
            # 'trakt_api_key': context.trakt_api_key,
            # 'meta': json.dumps({
                # 'showName': 'Marvel\'s Agents of S H I E L D  -',
                # 'filename': 'Marvel\'s Agents of S.H.I.E.L.D. - '
                            # 'S05E01E02 - Orientation.mkv',
                # 'seasonNumber': '05',
                # 'title': 'Marvel\'s Agents of S H I E L D  - S05E01',
                # 'episodeNumber': '01',
            # }),
            # 'duration': 5024.520192,
            # 'oshash': '04d28f798ba3dd87',
            # 'size': 426653710,
        # }
        # expected = [
            # {
                # u'base': {
                    # u'season': 5,
                    # u'year': 2017,
                    # u'seriesStartYear': 2013,
                    # u'imdbid': u'tt6878538',
                    # u'id': u'/title/tt6878538/',
                    # u'previousEpisode': u'/title/tt5916882/',
                    # u'parentTitle': {
                        # u'titleType': u'tvSeries',
                        # u'imdbid': u'tt2364582',
                        # u'id': u'/title/tt2364582/',
                        # u'title': u'Agents of S.H.I.E.L.D.',
                        # u'year': 2013,
                    # },
                    # u'nextEpisode': u'/title/tt7178426/',
                    # u'titleType': u'tvEpisode',
                    # u'title': u'Orientation: Part 1',
                    # u'episode': 1,
                    # u'tvdbid': 6276702,
                    # u'runningTimeInMinutes': 42,
                    # u'tmdbid': 1377164,
                # },
            # },
            # {
                # u'base':{
                    # u'season': 5,
                    # u'year': 2017,
                    # u'seriesStartYear': 2013,
                    # u'imdbid': u'tt7178426',
                    # u'id': u'/title/tt7178426/',
                    # u'previousEpisode': u'/title/tt6878538/',
                    # u'parentTitle': {
                        # u'titleType': u'tvSeries',
                        # u'imdbid': u'tt2364582',
                        # u'id': u'/title/tt2364582/',
                        # u'title': u'Agents of S.H.I.E.L.D.',
                        # u'year': 2013,
                    # },
                    # u'nextEpisode': u'/title/tt7183060/',
                    # u'titleType': u'tvEpisode',
                    # u'title': u'Orientation: Part 2',
                    # u'episode': 2,
                    # u'tvdbid': 6407853,
                    # u'runningTimeInMinutes': 43,
                    # u'tmdbid': 1378310,
                # },
            # },
        # ]

        # # Run the test
        # self._test_media_resolution(params, expected)

    def test_parse_filename_episode_single(self):
        filename = 'The Flash (2014) - S04E19 - Fury Rogue.mkv'
        parsed = parse_filename(filename)

        self.assertDictEqual({
            'movie': {
                'year': u'2014',
                'type': 'movie',
                'title': u'The Flash',
            },
            'episode': {
                'absepisodes': False,
                'season': 4,
                'episodes': [
                    19,
                ],
                'type': 'episode',
                'show': u'The Flash (2014)',
            },
        }, parsed)

    def test_parse_filename_episode_double(self):
        filename = ('Marvel\'s Agents of S.H.I.E.L.D. - '
                    'S05E01E02 - Orientation.mkv')
        parsed = parse_filename(filename)

        self.assertDictEqual(self._test_media_info[filename]['parser'],
                             parsed)

    def test_parse_filename_episode_double_inverted(self):
        pfilename = ('Marvel\'s Agents of S.H.I.E.L.D. - '
                     'S05E02E01 - Orientation.mkv')
        parsed = parse_filename(pfilename)

        filename = ('Marvel\'s Agents of S.H.I.E.L.D. - '
                    'S05E01E02 - Orientation.mkv')
        expect_parsed = deepcopy(self._test_media_info[filename]['parser'])
        expect_parsed['movie']['title'] = (u'Marvel\'s Agents of S.H.I.E.L.D '
                                           u' - S05E02E01 - Orientation')

        self.assertDictEqual(expect_parsed,
                             parsed)

    def test_parse_filename_episode_multi(self):
        pfilename = ('Marvel\'s Agents of S.H.I.E.L.D. - '
                     'S05E01E04 - Orientation.mkv')
        parsed = parse_filename(pfilename)

        filename = ('Marvel\'s Agents of S.H.I.E.L.D. - '
                    'S05E01E02 - Orientation.mkv')
        expect_parsed = deepcopy(self._test_media_info[filename]['parser'])
        expect_parsed['movie']['title'] = (u'Marvel\'s Agents of S.H.I.E.L.D '
                                           u' - S05E01E04 - Orientation')
        expect_parsed['episode']['episodes'] += [3, 4]

        self.assertDictEqual(expect_parsed,
                             parsed)

    def test_parse_filename_episode_absolute(self):
        filename = '[HorribleSubs] Dragon Ball Super - 112 [480p].mkv'
        parsed = parse_filename(filename)

        self.assertDictEqual(self._test_media_info[filename]['parser'],
                             parsed)

    def test_parse_filename_movie(self):
        filename = 'Notorious (1946).avi'
        parsed = parse_filename(filename)

        self.assertDictEqual(self._test_media_info[filename]['parser'],
                             parsed)

    def _test_insert_hash(self, filename, mock_insert_hash, ratio=80,
                          insert_hash_called=True):
        origparams = self._test_media_info[filename]['params']
        media = self._test_media_info[filename]['resolve'][0]
        params = {
            'oshash': origparams['oshash'],
            'size': origparams['size'],
            'duration': origparams['duration'],
            'meta': self._test_media_info[filename]['meta'],
            'media': media,
            'mediatype': 'movie',
            'ratio': ratio,
        }

        # Run the command
        CommandResolve().insert_hash(**params)

        if insert_hash_called:
            mock_insert_hash.assert_called_once_with([
                {
                    'moviebytesize': origparams['size'],
                    'imdbid': media['base']['imdbid'][2:],
                    'movietimems': origparams['duration'] * 1000.,
                    'moviehash': origparams['oshash'],
                    'moviefilename': filename,
                },
            ])
        else:
            mock_insert_hash.assert_not_called()

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_fail_movie(self, mock_insert_hash):
        filename = self._default_media_by_type['movie']

        mock_insert_hash.return_value = {
            'status': 'NOT OK',
        }

        media = self._test_media_info[filename]['resolve'][0]
        title = media['base']['title']

        with LogCapture() as l:
            self._test_insert_hash(filename, mock_insert_hash)

        l.check_present(
            ('helper.commands.resolve', 'INFO',
             "Unable to submit hash for '{}': NOT OK".format(title)),
        )

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_fail_episode(self, mock_insert_hash):
        filename = self._default_media_by_type['episode']

        mock_insert_hash.return_value = {
            'status': 'NOT OK',
        }

        media = self._test_media_info[filename]['resolve'][0]
        title = '{} - S{:02d}E{:02d} - {}'.format(
            media['base']['parentTitle']['title'],
            media['base']['season'],
            media['base']['episode'],
            media['base']['title'],
        )

        with LogCapture() as l:
            self._test_insert_hash(filename, mock_insert_hash)

        l.check_present(
            ('helper.commands.resolve', 'INFO',
             "Unable to submit hash for '{}': NOT OK".format(title)),
        )

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_succeed(self, mock_insert_hash):
        filename = self._default_media_by_type['movie']

        mock_insert_hash.return_value = {
            'status': '200 OK',
            'data': {
                'accepted_moviehashes': [
                    self._test_media_info[filename]['params']['oshash'],
                ],
            },
        }

        with LogCapture() as l:
            self._test_insert_hash(filename, mock_insert_hash)

        l.check_present(
            ('helper.commands.resolve', 'INFO',
             'New hash submitted and accepted'),
        )

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_not_accepted(self, mock_insert_hash):
        filename = self._default_media_by_type['movie']

        mock_insert_hash.return_value = {
            'status': '200 OK',
            'data': {
                'accepted_moviehashes': [
                ],
            },
        }

        with LogCapture() as l:
            self._test_insert_hash(filename, mock_insert_hash)

        l.check_present(
            ('helper.commands.resolve', 'INFO',
             'New hash submitted but not accepted'),
        )

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_no_insert(self, mock_insert_hash):
        filename = self._default_media_by_type['movie']

        mock_insert_hash.return_value = {
            'status': '200 OK',
            'data': {
                'accepted_moviehashes': [
                ],
            },
        }

        self._test_insert_hash(filename, mock_insert_hash, ratio=60,
                               insert_hash_called=False)

    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.insert_hash')
    def test_command_resolve_insert_hash_insert_raises(self, mock_insert_hash):
        filename = self._default_media_by_type['movie']

        mock_insert_hash.side_effect = utils.TestException('insert error')

        with self.assertRaises(ResolveException) as e:
            self._test_insert_hash(filename, mock_insert_hash)

        self.assertEqual('insert error', str(e.exception))

    def _test_search_hash(self, params, minfo, mock_check_hash, mock_imdb,
                          check_hash_func=None, imdb_func=None, fails=False,
                          check_hash_called=True, imdb_called=True):
        mock_check_hash.side_effect = check_hash_func or self._mock_check_hash
        mock_imdb.side_effect = imdb_func or self._mock_imdb_get_title

        resolve = CommandResolve().search_hash(**params)

        if fails:
            self.assertIsNone(resolve,
                              'search_hash did not return None: {}'.format(
                                  resolve))
        else:
            self.assertTrue(isinstance(resolve, tuple),
                            'search_hash result is not a tuple ({})'.format(
                                type(resolve).__name__))
            self.assertEqual('Imdb', type(resolve[0]).__name__)
            self.assertDictEqual(minfo['resolve'][0], resolve[1])

        if check_hash_called:
            mock_check_hash.assert_called_once_with([
                minfo['params']['oshash'], ])
        else:
            mock_check_hash.assert_not_called()

        if imdb_called:
            mock_imdb.assert_called_once_with(
                minfo['resolve'][0]['base']['imdbid'])
        else:
            mock_imdb.assert_not_called()

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash(self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'oshash': minfo['params']['oshash'],
            'parsed': minfo['parser'],
        }

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_multi(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['anime']
        minfo = self._test_media_info[filename]

        params = {
            'oshash': minfo['params']['oshash'],
            'parsed': minfo['parser'],
        }

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_multi_show_typo(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['anime']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': deepcopy(minfo['parser']),
        }

        params['parsed']['episode']['show'] = \
            minfo['parser']['episode']['show'][:-2] + \
            minfo['parser']['episode']['show'][-1:]

        def mock_check_hash_extra(*args, **kwargs):
            results = self._mock_check_hash(*args, **kwargs)
            if oshash in results['data']:
                extra = [
                    # This should be discarded because season == 3
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000001',
                        'MovieKind': 'episode',
                        'SeriesSeason': '3',
                        'SeriesEpisode': '0',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                ]
                results['data'][oshash] = extra + results['data'][oshash]
            return results

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               check_hash_func=mock_check_hash_extra)

        # Try again, but force the ratio to always be under 80%
        mock_check_hash.reset_mock()
        mock_imdb.reset_mock()
        with mock.patch('fuzzywuzzy.fuzz.ratio') as mock_ratio:
            mock_ratio.return_value = .5

            self._test_search_hash(params, minfo, mock_check_hash,
                                   mock_imdb,
                                   check_hash_func=mock_check_hash_extra,
                                   fails=True, imdb_called=False)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_multi_episode(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['episode']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        def mock_check_hash_extra(*args, **kwargs):
            results = self._mock_check_hash(*args, **kwargs)
            if oshash in results['data']:
                extra = [
                    # This should be discarded because it is a movie
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000001',
                        'MovieKind': 'movie',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake movie name',
                        'MovieYear': '2010',
                    },
                    # This should be discarded because season == 3
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000020',
                        'MovieKind': 'episode',
                        'SeriesSeason': '3',
                        'SeriesEpisode': '0',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                ]
                results['data'][oshash] = extra + results['data'][oshash]
            return results

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               check_hash_func=mock_check_hash_extra)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_multi_movie(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        def mock_check_hash_extra(*args, **kwargs):
            results = self._mock_check_hash(*args, **kwargs)
            if oshash in results['data']:
                extra = [
                    # This should be discarded because of its name
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000001',
                        'MovieKind': 'movie',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake movie name',
                        'MovieYear': '2010',
                    },
                    # This should be discarded because it is an episode
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000020',
                        'MovieKind': 'episode',
                        'SeriesSeason': '3',
                        'SeriesEpisode': '0',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                ]
                results['data'][oshash] = extra + results['data'][oshash]
            return results

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               check_hash_func=mock_check_hash_extra)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_badresults(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['multiepisode']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        def mock_check_hash_badresults(*args, **kwargs):
            results = self._mock_check_hash(*args, **kwargs)
            if oshash in results['data']:
                extra = [
                    # This should be discarded because it is a movie
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000001',
                        'MovieKind': 'movie',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake movie name',
                        'MovieYear': '2010',
                    },
                    # This should be discarded because season == 3
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000020',
                        'MovieKind': 'episode',
                        'SeriesSeason': '3',
                        'SeriesEpisode': '0',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                    # This should be discarded because episode == 3
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000300',
                        'MovieKind': 'episode',
                        'SeriesSeason': '5',
                        'SeriesEpisode': '3',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                ]
                # We replace the good results by the bad ones, this is a
                # false positive!
                results['data'][oshash] = extra
            return results

        with self.assertRaises(ResolveException) as e:
            self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                                   check_hash_func=mock_check_hash_badresults)

        self.assertEqual('Test LookupError for imdbid = tt000001',
                         str(e.exception))

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_baduniqueresult(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        def mock_check_hash_badresults(*args, **kwargs):
            results = self._mock_check_hash(*args, **kwargs)
            if oshash in results['data']:
                extra = [
                    # This should be discarded because it is an episode
                    {
                        'SeenCount': '0',
                        'MovieImdbID': '000300',
                        'MovieKind': 'episode',
                        'SeriesSeason': '5',
                        'SeriesEpisode': '3',
                        'MovieHash': oshash,
                        'SubCount': '0',
                        'MovieName': 'Fake show name',
                        'MovieYear': '2011',
                    },
                ]
                # We replace the good results by the bad ones, this is a
                # false positive!
                results['data'][oshash] = extra
            return results

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               check_hash_func=mock_check_hash_badresults,
                               fails=True, imdb_called=False)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_not_found(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        def mock_check_hash_empty(*args, **kwargs):
            return {'status': '200 OK', 'seconds': 0.003, 'data': []}

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               check_hash_func=mock_check_hash_empty,
                               fails=True, imdb_called=False)

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_check_hash_except(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]
        oshash = minfo['params']['oshash']

        params = {
            'oshash': oshash,
            'parsed': minfo['parser'],
        }

        with self.assertRaises(ResolveException) as e:
            self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                                   check_hash_func=utils.TestException('Nope'))

        mock_check_hash.assert_called_once_with([oshash, ])
        mock_imdb.assert_not_called()
        self.assertEqual('Nope', str(e.exception))

    @mock.patch('imdbpie.Imdb.get_title')
    @mock.patch('helper.commands.resolve.OpenSubtitlesAPI.check_hash')
    def test_command_resolve_search_hash_no_hash(
            self, mock_check_hash, mock_imdb):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'oshash': None,
            'parsed': minfo['parser'],
        }

        self._test_search_hash(params, minfo, mock_check_hash, mock_imdb,
                               fails=True, check_hash_called=False,
                               imdb_called=False)

    def test_command_resolve_weight_movie_by_duration(self):
        movies = [
            {
                'name': 'a',
                'details': {
                    'base': {
                        'runningTimeInMinutes': 5,
                    },
                },
            },
            {
                'name': 'b',
                'details': {
                    'base': {
                        'runningTimeInMinutes': 10,
                    },
                },
            },
            {
                'name': 'c',
                'details': {
                    'base': {
                        'runningTimeInMinutes': 15,
                    },
                },
            },
            {
                'name': 'd',
                'details': {
                    'base': {
                    },
                },
            },
            {
                'name': 'e',
                'details': {
                    'base': {
                        'runningTimeInMinutes': 20,
                    },
                },
            },
        ]

        cmd = CommandResolve()

        tests = [
            {
                'duration': 12 * 60.,
                'result': ['b', 'c', 'a', 'e', 'd'],
            },
            {
                'duration': 13 * 60.,
                'result': ['c', 'b', 'e', 'a', 'd'],
            },
            {
                'duration': 0,
                'result': ['a', 'b', 'c', 'e', 'd'],
            },
            {
                'duration': None,
                'result': ['a', 'b', 'c', 'd', 'e'],
            },

        ]

        for i, case in enumerate(tests):
            ordered = sorted(
                movies, key=cmd.weight_movie_by_duration(case['duration']))
            self._partial_match(
                [{'name': k} for k in case['result']], ordered,
                message='Error ordering testcase {}'.format(i))

    def _test_search_text_movie(self, params, minfo, mock_get_title,
                                mock_search_for_title, get_title_func=None,
                                search_for_title_func=None, fails=False,
                                get_title_called=True,
                                search_for_title_called=True,
                                expected_resolution=None):
        mock_get_title.side_effect = \
                get_title_func or self._mock_imdb_get_title
        mock_search_for_title.side_effect = \
                search_for_title_func or self._mock_imdb_search_for_title

        resolve = CommandResolve().search_text_movie(**params)

        if fails:
            self.assertIsNone(resolve,
                              'search_text_movie did not return '
                              'None: {}'.format(resolve))
        else:
            self.assertTrue(isinstance(resolve, tuple),
                            'search_text_movie result is not a '
                            'tuple ({})'.format(type(resolve).__name__))
            self.assertEqual('Imdb', type(resolve[0]).__name__)
            self.assertDictEqual(
                expected_resolution or minfo['resolve'][0],
                resolve[1])

        if search_for_title_called:
            mock_search_for_title.assert_called_once_with(
                minfo['parser']['movie']['title'])
        else:
            mock_search_for_title.assert_not_called()

        if get_title_called:
            mock_get_title.assert_has_calls([
                mock.call(minfo['resolve'][0]['base']['imdbid']),
            ])
        else:
            mock_get_title.assert_not_called()

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie(self, mock_get_title,
                                               mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        self._test_search_text_movie(params, minfo, mock_get_title,
                                     mock_search_for_title)

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_no_runtime(
            self, mock_get_title, mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        def mock_get_title_no_runtime(*args, **kwargs):
            r = deepcopy(self._mock_imdb_get_title(*args, **kwargs))
            if 'base' in r and 'runningTimeInMinutes' in r['base']:
                del r['base']['runningTimeInMinutes']
            return r

        self._test_search_text_movie(params, minfo, mock_get_title,
                                     mock_search_for_title,
                                     get_title_func=mock_get_title_no_runtime,
                                     fails=True)

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_no_duration_no_runtime(
            self, mock_get_title, mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
        }

        def mock_get_title_no_runtime(*args, **kwargs):
            r = deepcopy(self._mock_imdb_get_title(*args, **kwargs))
            if 'base' in r and 'runningTimeInMinutes' in r['base']:
                del r['base']['runningTimeInMinutes']
            return r

        expected_resolution = deepcopy(minfo['resolve'][0])
        del expected_resolution['base']['runningTimeInMinutes']

        self._test_search_text_movie(params, minfo, mock_get_title,
                                     mock_search_for_title,
                                     get_title_func=mock_get_title_no_runtime,
                                     expected_resolution=expected_resolution)

    @mock.patch('helper.commands.resolve.'
                'CommandResolve.weight_movie_by_duration')
    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_large_duration_difference(
            self, mock_get_title, mock_search_for_title, mock_weight):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        def mock_weight_func(duration):
            def mwf(movie):
                movie['duration_closeness'] = minfo['params']['duration']
                return movie['duration_closeness']
            return mwf

        mock_weight.side_effect = mock_weight_func

        self._test_search_text_movie(params, minfo, mock_get_title,
                                     mock_search_for_title, fails=True)

        mock_weight.assert_called_once()

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_no_exact_year(
            self, mock_get_title, mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        def mock_search_for_title_no_year(*args, **kwargs):
            res = deepcopy(self._mock_imdb_search_for_title(*args, **kwargs))
            for r in res:
                if 'year' in r:
                    r['year'] = u'0'
            return res

        self._test_search_text_movie(params, minfo, mock_get_title,
                                     mock_search_for_title,
                                     search_for_title_func=\
                                        mock_search_for_title_no_year)

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_search_exception(
            self, mock_get_title, mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        with self.assertRaises(ResolveException) as e:
            self._test_search_text_movie(
                params, minfo, mock_get_title, mock_search_for_title,
                search_for_title_func=utils.TestException(
                    'search_for_title raises'))

        self.assertEqual('search_for_title raises',
                         str(e.exception),
                         'search_text_movie did not manage the exception '
                         'properly')

    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_movie_search_no_results(
            self, mock_get_title, mock_search_for_title):
        filename = self._default_media_by_type['movie']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_movie': minfo['parser']['movie'],
            'duration': minfo['params']['duration'],
        }

        def mock_search_for_title_no_results(title):
            return []

        self._test_search_text_movie(
            params, minfo, mock_get_title, mock_search_for_title,
            search_for_title_func=mock_search_for_title_no_results,
            fails=True, get_title_called=False)

    def _test_search_text_episode(
            self, params, minfo, mock_imdb_get_title,
            mock_imdb_search_for_title, mock_imdb_get_title_episodes,
            mock_tvdb, mock_req_get, get_title_func=None,
            search_for_title_func=None, get_title_episodes_func=None,
            tvdb_func=None, requests_get_func=None,
            get_title_called=True, search_for_title_called=True,
            get_title_episodes_called=True, tvdb_called=True,
            requests_get_called_search=True, requests_get_called_show=True,
            fails=False, commandoutput=False, expected_resolution=None):
        mock_tvdb.side_effect = tvdb_func or self._mock_tvdb
        mock_req_get.side_effect = requests_get_func or self._mock_requests_get
        mock_imdb_get_title.side_effect = \
            get_title_func or self._mock_imdb_get_title

        resolve = CommandResolve().search_text_episode(**params)

        if fails:
            self.assertIsNone(resolve,
                              'search_text_episode did not return '
                              'None: {}'.format(resolve))
        elif commandoutput:
            self.assertTrue(isinstance(resolve, CommandOutput),
                            'search_text_episode result is not a '
                            'CommandOutput ({})'.format(
                                type(resolve).__name__))
        else:
            self.assertTrue(isinstance(resolve, tuple),
                            'search_text_episode result is not a '
                            'tuple ({})'.format(type(resolve).__name__))
            self.assertEqual('Imdb', type(resolve[0]).__name__)
            self.assertDictEqual(
                expected_resolution or minfo['resolve'][0],
                resolve[1])

        if requests_get_called_search or requests_get_called_show:
            calls = []
            if requests_get_called_search:
                calls.append(mock.call(minfo['url']['trakt_search']))
            if requests_get_called_show:
                calls.append(mock.call(minfo['url']['trakt_show']))
            mock_req_get.assert_has_calls(calls)
        else:
            mock_req_get.assert_not_called()

        if search_for_title_called:
            mock_imdb_search_for_title.assert_called_once_with(
                minfo['parser']['episode']['title'])
        else:
            mock_imdb_search_for_title.assert_not_called()

        if get_title_called:
            mock_imdb_get_title.assert_has_calls([
                mock.call(minfo['resolve'][0]['base']['imdbid']),
            ])
        else:
            mock_imdb_get_title.assert_not_called()

        if get_title_episodes_called:
            mock_imdb_get_title_episodes.assert_has_calls([
                mock.call(minfo['resolve'][0][
                    'base']['parentTitle']['imdbid']),
            ])
        else:
            mock_imdb_get_title_episodes.assert_not_called()

        return resolve

    @mock.patch('requests.Session.get')
    @mock.patch('tvdb_api.Tvdb')
    @mock.patch('imdbpie.Imdb.get_title_episodes')
    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_ep(
            self, mock_imdb_get_title, mock_imdb_search_for_title,
            mock_imdb_get_title_episodes, mock_tvdb, mock_req_get): 
        filename = self._default_media_by_type['episode']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_episode': minfo['parser']['episode'],
            'trakt_api_key': context.trakt_api_key,
        }

        self._test_search_text_episode(
            params, minfo, mock_imdb_get_title, mock_imdb_search_for_title,
            mock_imdb_get_title_episodes, mock_tvdb, mock_req_get,
            search_for_title_called=False, requests_get_called_show=False,
            get_title_episodes_called=False)

    @mock.patch('requests.Session.get')
    @mock.patch('tvdb_api.Tvdb')
    @mock.patch('imdbpie.Imdb.get_title_episodes')
    @mock.patch('imdbpie.Imdb.search_for_title')
    @mock.patch('imdbpie.Imdb.get_title')
    def test_command_resolve_search_text_ep_trakt_no_imdbid_no_title_eps(
            self, mock_imdb_get_title, mock_imdb_search_for_title,
            mock_imdb_get_title_episodes, mock_tvdb, mock_req_get): 
        filename = self._default_media_by_type['episode']
        minfo = self._test_media_info[filename]

        params = {
            'parsed_episode': minfo['parser']['episode'],
            'trakt_api_key': context.trakt_api_key,
        }

        def mock_requests_get(*args, **kwargs):
            res = self._mock_requests_get(*args, **kwargs)
            results = deepcopy(res.json())
            for r in results:
                if 'episode' in r and 'ids' in r['episode']:
                    r['episode']['ids']['imdb'] = None
            res.json.return_value = results

            return res

        resolve = self._test_search_text_episode(
            params, minfo, mock_imdb_get_title, mock_imdb_search_for_title,
            mock_imdb_get_title_episodes, mock_tvdb, mock_req_get,
            requests_get_func=mock_requests_get, search_for_title_called=False,
            requests_get_called_show=False, get_title_called=False,
            commandoutput=True)

        self.assertDictEqual({
            'base': {
                'episode': 19,
                'id': '/title/tt6741970/',
                'imdbid': 'tt6741970',
                'parentTitle': {
                    'id': '/title/tt3107288/',
                    'imdbid': 'tt3107288',
                    'slugid': 'the-flash-2014',
                    'title': 'The Flash',
                    'titleType': 'tvSeries',
                    'tmdbid': 60735,
                    'traktid': 60300,
                    'tvdbid': 279121,
                    'tvrageid': 36939,
                    'year': 2014,
                },
                'runningTimeInMinutes': 42,
                'season': 4,
                'seriesStartYear': 2014,
                'title': 'Fury Rogue',
                'tmdbid': 1458444,
                'traktid': 2795858,
                'tvdbid': 6569894,
                'tvrageid': 0,
                'year': 2018,
            },
        }, resolve.data[0])

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.resolve.CommandResolve.run')
    def test_trakt_helper_resolve(self, mock_run, mock_exit):
        params = {
            'trakt_api_key': context.trakt_api_key,
            'meta': json.dumps({
               'setting': ' HAS_INDEX IS_INTERLEAVED',
               'filename': 'Notorious (1946).avi',
               'Software': 'VirtualDubMod 1.5.4.1 (build 2178/release)',
            }),
            'duration': 6132.,
            'oshash': '6763a1dba52355e0',
            'size': 733468672.,
        }
        argv = ['resolve']
        for k, v in params.items():
            if v is not None:
                if k == 'oshash':
                    k = 'hash'
                else:
                    k = k.replace('_', '-')
                argv.extend(['--{}'.format(k), str(v)])

        mock_run.return_value = CommandOutput(data='output')

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_with(**params)
            mock_exit.assert_called_with(0)

            mock_print.assert_called_once()
            mock_print.assert_called_with('"output"')


if __name__ == '__main__':
    unittest.main()
