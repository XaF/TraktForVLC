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
import json
import logging
import tmdbsimple
import tvdb_api

from helper.utils import (
    Command,
)

LOGGER = logging.getLogger(__name__)

# Set the TMDB API KEY - If you fork this project, please change that
# API KEY to your own!
tmdbsimple.API_KEY = 'ad2d828c5ec2d46c06e1c38e181c125b'


##############################################################################
# To resolve an episode ids
def resolve_episode_ids(series, season, episode, year=None, imdbid=None):
    # To store the IDs found
    ids = {}

    # Initialize a TMDB search object
    tmdb_search = tmdbsimple.Search()

    ##################################################################
    # TVDB
    tvdb = tvdb_api.Tvdb(
        language='en',
    )

    tvdb_series = None
    try:
        # Try getting the series directly, but check the year if available
        # as sometimes series have the same name but are from different years
        tvdb_series = tvdb[series]
        if (imdbid is None or tvdb_series['imdbId'] != imdbid) and \
                year is not None and tvdb_series['firstAired'] and \
                year != int(tvdb_series['firstAired'].split('-')[0]):
            # It is not the expected year, we thus need to perform a search
            tvdb_series = None
            tvdb_search = tvdb.search(series)
            for s in tvdb_search:
                if imdbid is None or s['imdbId'] != imdbid:
                    if not s['seriesName'].startswith(series):
                        LOGGER.debug('TVDB: Discarding result because of the '
                                     'name not beginning with the expected '
                                     'series name: {}'.format(s))
                        continue

                    if int(s['firstAired'].split('-')[0]) != year:
                        LOGGER.debug('TVDB: Discarding result because of the '
                                     'year not matching: {}'.format(s))
                        continue

                tvdb_series = tvdb[s['seriesName']]
                break

        tvdb_season = tvdb_series[season]
        tvdb_episode = tvdb_season[episode]
        ids['tvdb'] = tvdb_episode['id']
    except Exception as e:
        LOGGER.debug(e)
        LOGGER.warning('Unable to find series {}, season {}, '
                       'episode {} on TheTVDB'.format(
                           series, season, episode))

    ##################################################################
    # TMDB
    params = {'query': series}
    if year is not None:
        params['first_air_date_year'] = year

    try:
        tmdb_search.tv(**params)
    except Exception as e:
        LOGGER.debug(e)
        tmdb_search.results = []

    for s in tmdb_search.results:
        if s['name'] != series and \
                (tvdb_series is None or
                 (s['name'] != tvdb_series['seriesName'] and
                  s['name'] not in tvdb_series['aliases'])):
            LOGGER.debug('TMDB: Discarding result because of the name '
                         'not matching with the expected series '
                         'name: {}'.format(s))
            continue

        # Try to get the episode information
        tmdb_episode = tmdbsimple.TV_Episodes(s['id'], season, episode)
        try:
            tmdb_external_ids = tmdb_episode.external_ids()
        except Exception as e:
            continue

        # If we have the tvdb information, check that we got the right
        # id... else, it is probably not the episode we are looking
        # for!
        if 'tvdb' in ids and \
                tmdb_external_ids.get('tvdb_id') is not None and \
                ids['tvdb'] != tmdb_external_ids['tvdb_id']:
            LOGGER.debug('TMDB: Discarding result because of the TVDB id not '
                         'matching with the one found on the TVDB '
                         'side: {}'.format(s))
            continue

        ids['tmdb'] = tmdb_external_ids['id']
        break

    return ids


##############################################################################
# To resolve a movie ids
def resolve_movie_ids(movie, year=None):
    # To store the IDs found
    ids = {}

    # Initialize a TMDB search object
    search = tmdbsimple.Search()

    ##################################################################
    # TMDB
    params = {'query': movie}
    if year is not None:
        params['year'] = year

    try:
        search.movie(**params)
    except Exception as e:
        LOGGER.debug(e)
        search.results = []

    for s in search.results:
        if s['title'] != movie:
            try:
                if s['title'] != movie.decode('utf-8'):
                    continue
            except UnicodeEncodeError as e:
                continue

        ids['tmdb'] = s['id']
        break

    return ids


##############################################################################
# To represent a media object
class Media(object):
    series = None
    season = None
    episode = None
    movie = None
    year = None
    imdbid = None


##############################################################################
# Allow to represent an episode in the "series season episode [year]" format
class ActionEpisode(argparse.Action):
    def __init__(self, option_strings, dest, default=None,
                 required=False, help=None):
        super(ActionEpisode, self).__init__(
            option_strings, dest, nargs='+', const=None, default=default,
            required=required, help=help)

    def __call__(self, parser, namespace, values, option_strings=None):
        if len(values) < 3 or len(values) > 5:
            parser.error('argument {}: format is SERIES_NAME SEASON_NUMBER '
                         'EPISODE_NUMBER [YEAR [SERIES_IMDBID]]')
            return

        for i, v in enumerate(values[1:-1]):
            try:
                values[i + 1] = int(v)
            except ValueError:
                parser.error('argument {}: invalid int value: \'{}\''.format(
                    option_strings, v))
                return

        media = Media()
        media.series = values[0]
        media.season = values[1]
        media.episode = values[2]
        if len(values) > 3 and values[3]:
            media.year = values[3]
        if len(values) > 4 and values[4]:
            media.imdbid = values[4]

        current = getattr(namespace, self.dest)
        if current is None:
            current = []

        setattr(namespace, self.dest, current + [media, ])


##############################################################################
# Allow to represent a movie in the "movie [year]" format
class ActionMovie(argparse.Action):
    def __init__(self, option_strings, dest, default=None,
                 required=False, help=None):
        super(ActionMovie, self).__init__(
            option_strings, dest, nargs='+', const=None, default=default,
            required=required, help=help)

    def __call__(self, parser, namespace, values, option_strings=None):
        if len(values) < 1 or len(values) > 2:
            parser.error('argument {}: format is MOVIE_NAME [YEAR]')
            return

        for i, v in enumerate(values[1:]):
            try:
                values[i + 1] = int(v)
            except ValueError:
                parser.error('argument {}: invalid int value: \'{}\''.format(
                    option_strings, v))
                return

        media = Media()
        media.movie = values[0]
        if len(values) > 1 and values[1]:
            media.year = values[1]

        current = getattr(namespace, self.dest)
        if current is None:
            current = []

        setattr(namespace, self.dest, current + [media, ])


##########################################################################
# The EXTRAIDS command to find extra ids for a given series/movie
class CommandExtraIDs(Command):
    command = 'extraids'
    description = ('Find extra IDs for a given movie/episode in order to '
                   'find it on Trakt.tv')

    def add_arguments(self, parser):
        parser.add_argument(
            '--episode',
            help='The episode to search extra ids for; must be called with '
                 '--episode SERIES_NAME SEASON_NUMBER EPISODE_NUMBER [YEAR]',
            action=ActionEpisode,
            dest='episodes',
        )
        parser.add_argument(
            '--movie',
            help='The movie to search extra ids for; must be called with '
                 '--movie MOVIE_NAME [YEAR]',
            action=ActionMovie,
            dest='movies',
        )

    def run(self, episodes, movies):
        ids = {}

        if episodes is None:
            episodes = []
        if movies is None:
            movies = []

        for e in episodes:
            ep_ids = resolve_episode_ids(e.series, e.season,
                                         e.episode, e.year, e.imdbid)

            ids.setdefault(
                'episode', {}).setdefault(
                    e.series, {}).setdefault(
                        e.season, {})[e.episode] = ep_ids

        for m in movies:
            mov_ids = resolve_movie_ids(m.movie, m.year)

            ids.setdefault(
                'movie', {})[m.movie] = mov_ids

        print(json.dumps(ids, sort_keys=True,
                         indent=4, separators=(',', ': '),
                         ensure_ascii=False))
