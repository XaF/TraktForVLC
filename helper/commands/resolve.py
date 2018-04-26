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
import fuzzywuzzy.fuzz
import imdbpie
import json
import logging
import math
import re
import sys
import tvdb_api

from helper.commands.extraids import (
    resolve_episode_ids,
    resolve_movie_ids,
)
from helper.utils import (
    Command,
)
from helper.version import (
    __version__,
)

try:
    import xmlrpclib as xmlrpc
except ImportError:
    import xmlrpc.client as xmlrpc

LOGGER = logging.getLogger(__name__)


##############################################################################
# Parse a filename to the series/movie
def parse_filename(filename):
    if type(filename) == bytes:
        filename = filename.decode()

    def cleanRegexedName(name):
        name = re.sub("[.](?!.(?:[.]|$))", " ", name)
        name = re.sub("(?<=[^. ]{2})[.]", " ", name)
        name = name.replace("_", " ")
        name = name.strip("- ")
        return name

    found = {}

    # Patterns to parse input series filenames with
    # These patterns come directly from the tvnamer project available
    # on https://github.com/dbr/tvnamer
    series_patterns = [
        # [group] Show - 01-02 [crc]
        '''^\[(?P<group>.+?)\][ ]?
            (?P<seriesname>.*?)[ ]?[-_][ ]?
            (?P<episodenumberstart>\d+)
            ([-_]\d+)*
            [-_](?P<episodenumberend>\d+)
            (?=
              .*
              \[(?P<crc>.+?)\]
            )?
            [^\/]*$''',

        # [group] Show - 01 [crc]
        '''^\[(?P<group>.+?)\][ ]?
            (?P<seriesname>.*)
            [ ]?[-_][ ]?
            (?P<episodenumber>\d+)
            (?=
              .*
              \[(?P<crc>.+?)\]
            )?
            [^\/]*$''',

        # foo s01e23 s01e24 s01e25 *
        '''^((?P<seriesname>.+?)[ \._\-])?
            [Ss](?P<seasonnumber>[0-9]+)
            [\.\- ]?
            [Ee](?P<episodenumberstart>[0-9]+)
            ([\.\- ]+
            [Ss](?P=seasonnumber)
            [\.\- ]?
            [Ee][0-9]+)*
            ([\.\- ]+
            [Ss](?P=seasonnumber)
            [\.\- ]?
            [Ee](?P<episodenumberend>[0-9]+))
            [^\/]*$''',

        # foo.s01e23e24*
        '''^((?P<seriesname>.+?)[ \._\-])?
            [Ss](?P<seasonnumber>[0-9]+)
            [\.\- ]?
            [Ee](?P<episodenumberstart>[0-9]+)
            ([\.\- ]?
            [Ee][0-9]+)*
            [\.\- ]?[Ee](?P<episodenumberend>[0-9]+)
            [^\/]*$''',

        # foo.1x23 1x24 1x25
        '''^((?P<seriesname>.+?)[ \._\-])?
            (?P<seasonnumber>[0-9]+)
            [xX](?P<episodenumberstart>[0-9]+)
            ([ \._\-]+
            (?P=seasonnumber)
            [xX][0-9]+)*
            ([ \._\-]+
            (?P=seasonnumber)
            [xX](?P<episodenumberend>[0-9]+))
            [^\/]*$''',

        # foo.1x23x24*
        '''^((?P<seriesname>.+?)[ \._\-])?
            (?P<seasonnumber>[0-9]+)
            [xX](?P<episodenumberstart>[0-9]+)
            ([xX][0-9]+)*
            [xX](?P<episodenumberend>[0-9]+)
            [^\/]*$''',

        # foo.s01e23-24*
        '''^((?P<seriesname>.+?)[ \._\-])?
            [Ss](?P<seasonnumber>[0-9]+)
            [\.\- ]?
            [Ee](?P<episodenumberstart>[0-9]+)
            (
                 [\-]
                 [Ee]?[0-9]+
            )*
                 [\-]
                 [Ee]?(?P<episodenumberend>[0-9]+)
            [\.\- ]
            [^\/]*$''',

        # foo.1x23-24*
        '''^((?P<seriesname>.+?)[ \._\-])?
            (?P<seasonnumber>[0-9]+)
            [xX](?P<episodenumberstart>[0-9]+)
            (
                 [\-+][0-9]+
            )*
                 [\-+]
                 (?P<episodenumberend>[0-9]+)
            ([\.\-+ ].*
            |
            $)''',

        # foo.[1x09-11]*
        '''^(?P<seriesname>.+?)[ \._\-]
            \[
                ?(?P<seasonnumber>[0-9]+)
            [xX]
                (?P<episodenumberstart>[0-9]+)
                ([\-+] [0-9]+)*
            [\-+]
                (?P<episodenumberend>[0-9]+)
            \]
            [^\\/]*$''',

        # foo - [012]
        '''^((?P<seriesname>.+?)[ \._\-])?
            \[
            (?P<episodenumber>[0-9]+)
            \]
            [^\\/]*$''',
        # foo.s0101, foo.0201
        '''^(?P<seriesname>.+?)[ \._\-]
            [Ss](?P<seasonnumber>[0-9]{2})
            [\.\- ]?
            (?P<episodenumber>[0-9]{2})
            [^0-9]*$''',

        # foo.1x09*
        '''^((?P<seriesname>.+?)[ \._\-])?
            \[?
            (?P<seasonnumber>[0-9]+)
            [xX]
            (?P<episodenumber>[0-9]+)
            \]?
            [^\\/]*$''',

        # foo.s01.e01, foo.s01_e01, "foo.s01 - e01"
        '''^((?P<seriesname>.+?)[ \._\-])?
            \[?
            [Ss](?P<seasonnumber>[0-9]+)[ ]?[\._\- ]?[ ]?
            [Ee]?(?P<episodenumber>[0-9]+)
            \]?
            [^\\/]*$''',

        # foo.2010.01.02.etc
        '''
            ^((?P<seriesname>.+?)[ \._\-])?
            (?P<year>\d{4})
            [ \._\-]
            (?P<month>\d{2})
            [ \._\-]
            (?P<day>\d{2})
            [^\/]*$''',

        # foo - [01.09]
        '''^((?P<seriesname>.+?))
            [ \._\-]?
            \[
            (?P<seasonnumber>[0-9]+?)
            [.]
            (?P<episodenumber>[0-9]+?)
            \]
            [ \._\-]?
            [^\\/]*$''',

        # Foo - S2 E 02 - etc
        '''^(?P<seriesname>.+?)[ ]?[ \._\-][ ]?
            [Ss](?P<seasonnumber>[0-9]+)[\.\- ]?
            [Ee]?[ ]?(?P<episodenumber>[0-9]+)
            [^\\/]*$''',

        # Show - Episode 9999 [S 12 - Ep 131] - etc
        '''(?P<seriesname>.+)
            [ ]-[ ]
            [Ee]pisode[ ]\d+
            [ ]
            \[
            [sS][ ]?(?P<seasonnumber>\d+)
            ([ ]|[ ]-[ ]|-)
            ([eE]|[eE]p)[ ]?(?P<episodenumber>\d+)
            \]
            .*$
            ''',

        # show name 2 of 6 - blah
        '''^(?P<seriesname>.+?)
            [ \._\-]
            (?P<episodenumber>[0-9]+)
            of
            [ \._\-]?
            \d+
            ([\._ -]|$|[^\\/]*$)
            ''',

        # Show.Name.Part.1.and.Part.2
        '''^(?i)
            (?P<seriesname>.+?)
            [ \._\-]
            (?:part|pt)?[\._ -]
            (?P<episodenumberstart>[0-9]+)
            (?:
              [ \._-](?:and|&|to)
              [ \._-](?:part|pt)?
              [ \._-](?:[0-9]+))*
            [ \._-](?:and|&|to)
            [ \._-]?(?:part|pt)?
            [ \._-](?P<episodenumberend>[0-9]+)
            [\._ -][^\\/]*$
            ''',

        # Show.Name.Part1
        '''^(?P<seriesname>.+?)
            [ \\._\\-]
            [Pp]art[ ](?P<episodenumber>[0-9]+)
            [\\._ -][^\\/]*$
            ''',

        # show name Season 01 Episode 20
        '''^(?P<seriesname>.+?)[ ]?
            [Ss]eason[ ]?(?P<seasonnumber>[0-9]+)[ ]?
            [Ee]pisode[ ]?(?P<episodenumber>[0-9]+)
            [^\\/]*$''',

        # foo.103*
        '''^(?P<seriesname>.+)[ \._\-]
            (?P<seasonnumber>[0-9]{1})
            (?P<episodenumber>[0-9]{2})
            [\._ -][^\\/]*$''',

        # foo.0103*
        '''^(?P<seriesname>.+)[ \._\-]
            (?P<seasonnumber>[0-9]{2})
            (?P<episodenumber>[0-9]{2,3})
            [\._ -][^\\/]*$''',

        # show.name.e123.abc
        '''^(?P<seriesname>.+?)
            [ \._\-]
            [Ee](?P<episodenumber>[0-9]+)
            [\._ -][^\\/]*$
            ''',
    ]

    # Search if we find a series
    for pattern in series_patterns:
        m = re.match(pattern, filename, re.VERBOSE | re.IGNORECASE)
        if not m:
            continue

        groupnames = m.groupdict().keys()
        series = {
            'type': 'episode',
            'show': None,
            'season': None,
            'episodes': None,
        }

        # Show name
        series['show'] = cleanRegexedName(m.group('seriesname'))

        # Season
        series['season'] = int(m.group('seasonnumber'))

        # Episodes
        if 'episodenumberstart' in groupnames:
            if m.group('episodenumberend'):
                start = int(m.group('episodenumberstart'))
                end = int(m.group('episodenumberend'))
                if start > end:
                    start, end = end, start
                series['episodes'] = list(range(start, end + 1))
            else:
                series['episodes'] = [int(m.group('episodenumberstart')), ]
        elif 'episodenumber' in groupnames:
            series['episodes'] = [int(m.group('episodenumber')), ]

        found['episode'] = series
        break

    # The patterns that will be used to search for a movie
    movies_patterns = [
        '''^(\(.*?\)|\[.*?\])?( - )?[ ]*?
            (?P<moviename>.*?)
            (dvdrip|xvid| cd[0-9]|dvdscr|brrip|divx|
            [\{\(\[]?(?P<year>[0-9]{4}))
            .*$
            ''',

        '''^(\(.*?\)|\[.*?\])?( - )?[ ]*?
            (?P<moviename>.+?)[ ]*?
            (?:[[(]?(?P<year>[0-9]{4})[])]?.*)?
            (?:\.[a-zA-Z0-9]{2,4})?$
            ''',
    ]

    # Search if we find a series
    for pattern in movies_patterns:
        m = re.match(pattern, filename, re.VERBOSE | re.IGNORECASE)
        if not m:
            continue

        groupnames = m.groupdict().keys()
        movie = {
            'type': 'movie',
            'title': None,
            'year': None,
        }

        # Movie title
        movie['title'] = cleanRegexedName(m.group('moviename'))

        # Year
        if 'year' in groupnames and m.group('year'):
            movie['year'] = m.group('year')

        found['movie'] = movie
        break

    if found:
        return found

    # Not found
    return False


##########################################################################
# Internal function to convert unicode strings to byte strings
def tobyte(input):
    if isinstance(input, dict):
        return {tobyte(key): tobyte(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [tobyte(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


##########################################################################
# Class to represent resolution exceptions
class ResolveException(Exception):
    pass


##########################################################################
# Class to get OpenSubtitles XML-RPC API proxy
class OpenSubtitlesAPI(object):
    _connected = False

    @classmethod
    def _connect(cls):
        if cls._connected:
            return

        # Initialize the connection to opensubtitles
        cls._proxy = xmlrpc.ServerProxy(
            'https://api.opensubtitles.org/xml-rpc')
        cls._login = cls._proxy.LogIn(
            '', '', 'en', 'TraktForVLC v{}'.format(__version__))
        cls._connected = True

    @classmethod
    def check_hash(cls, *args, **kwargs):
        cls._connect()
        return cls._proxy.CheckMovieHash2(
            cls._login['token'], *args, **kwargs)

    @classmethod
    def insert_hash(cls, *args, **kwargs):
        cls._connect()
        return cls._proxy.InsertMovieHash(
            cls._login['token'], *args, **kwargs)


##########################################################################
# The RESOLVE command to get movie/series information from media details
class CommandResolve(Command):
    command = 'resolve'
    description = 'To get the movie/episode information from media details'

    def add_arguments(self, parser):
        parser.add_argument(
            '--meta',
            help='The metadata provided by VLC',
        )
        parser.add_argument(
            '--hash',
            dest='oshash',
            help='The hash of the media for OpenSubtitles resolution',
        )
        parser.add_argument(
            '--size',
            type=float,
            help='The size of the media, in bytes',
        )
        parser.add_argument(
            '--duration',
            type=float,
            help='The duration of the media, in seconds',
        )

    def run(self, meta, oshash, size, duration):
        # Prepare the parameters
        meta = json.loads(meta)

        # Parse the filename to get more information
        parsed = parse_filename(meta['filename'])

        ######################################################################
        # Internal function to search by hash
        def search_hash():
            if not oshash:
                return

            LOGGER.info('Searching media using hash research')

            # Search for the files corresponding to this hash
            try:
                medias = OpenSubtitlesAPI.check_hash([oshash, ])
            except Exception as e:
                raise ResolveException(e)

            # If the hash is not in the results
            medias = medias['data'] if 'data' in medias else []
            if oshash not in medias:
                return

            # We're only interested in that hash
            medias = medias[oshash]

            if len(medias) == 1:
                # There is only one, so might as well be that one!
                media = medias[0]

                # Unless it's not the same type...
                if media['MovieKind'] not in parsed:
                    return
            else:
                # Initialize media to None in case we don't find anything
                media = None

                # Search differently if it's an episode or a movie
                if 'episode' in parsed:
                    episode = parsed['episode']
                    season = episode['season']
                    fepisode = episode['episodes'][0]

                    # Define the prefix that characterize the show
                    show_prefix = '"{}"'.format(episode['show'].lower())

                    # And search if we find the first episode
                    for m in medias:
                        if m['MovieKind'] != 'episode' or \
                                int(m['SeriesSeason']) != season or \
                                int(m['SeriesEpisode']) != fepisode or \
                                not m['MovieName'].lower().startswith(
                                    show_prefix):
                            continue

                        media = m
                        break

                    # If we reach here and still haven't got the episode, try
                    # to see if we had maybe a typo in the name
                    if not media:
                        def weight_episode(x):
                            return fuzzywuzzy.fuzz.ratio(
                                parsed['episode']['show'], re.sub(
                                    '^\"([^"]*)\" .*$', '\\1', x['MovieName']))

                        # Filter only the episodes that can match with the
                        # information we got
                        episodes = [
                            m for m in medias
                            if m['MovieKind'] == 'episode' and
                            int(m['SeriesSeason']) == season and
                            int(m['SeriesEpisode']) == fepisode
                        ]

                        if episodes:
                            # Use fuzzywuzzy to get the closest show name
                            closest = max(
                                episodes,
                                key=weight_episode,
                            )
                            if weight_episode(closest) >= .8:
                                media = closest

                if not media and 'movie' in parsed:
                    movie = parsed['movie']

                    media_name = movie.get('title')

                    # Filter only the movies
                    movies = [
                        m for m in medias
                        if m['MovieKind'] == 'movie'
                    ]

                    if movies:
                        # Use fuzzywuzzy to get the closest movie name
                        media = max(
                            movies,
                            key=lambda x: fuzzywuzzy.fuzz.ratio(
                                media_name, x['MovieName'])
                        )

            # If when reaching here we don't have the media, return None
            if not media:
                return

            # Else, we will need imdb for getting more detailed information on
            # the media; we'll exclude episodes if we know the media is a movie
            imdb = imdbpie.Imdb(
                exclude_episodes=(media['MovieKind'] == 'movie'),
            )

            try:
                result = imdb.get_title('tt{}'.format(media['MovieImdbID']))
            except Exception as e:
                raise ResolveException(e)

            # Find the media
            return imdb, result

        ######################################################################
        # Internal function to search by text for a movie
        def search_text_movie():
            LOGGER.info('Searching media using text research on movie')
            movie = parsed['movie']

            # Initialize the imdb object to perform the research
            imdb = imdbpie.Imdb(
                exclude_episodes=True,
            )

            # Use imdb to search for the movie
            try:
                search = imdb.search_for_title(movie['title'])
            except Exception as e:
                raise ResolveException(e)

            # Filter out everything that is not starting with 'tt', as only
            # IMDB IDs starting with 'tt' represent movies/episodes, and
            # filter out everything considered as a TV series
            search = [s for s in search
                      if s['imdb_id'].startswith('tt') and
                      s['type'] != 'TV series']
            if not search:
                return

            year_found = False
            for r in search:
                r['fuzz_ratio'] = fuzzywuzzy.fuzz.ratio(
                    movie['title'], r['title'])
                if movie['year'] and \
                        not year_found and \
                        r['year'] == movie['year']:
                    year_found = True

            if year_found:
                search = [r for r in search if r['year'] == movie['year']]

            if not duration:
                # If we don't have the movie duration, we won't be able to use
                # it to discriminate the movies, so just use the highest ratio
                max_ratio = max(r['fuzz_ratio'] for r in search)
                search = [r for r in search if r['fuzz_ratio'] == max_ratio]

                # Even if there is multiple with the highest ratio, only
                # return one
                return imdb, imdb.get_title(search[0]['imdb_id'])

            # If we have the movie duration, we can use it to make the
            # research more precise, so we can be more gentle on the ratio
            sum_ratio = sum(r['fuzz_ratio'] for r in search)
            mean_ratio = sum_ratio / float(len(search))
            std_dev_ratio = math.sqrt(
                sum([
                    math.pow(r['fuzz_ratio'] - mean_ratio, 2)
                    for r in search
                ]) / float(len(search))
            )

            # Select only the titles over a given threshold
            threshold = min(mean_ratio + std_dev_ratio,
                            max(r['fuzz_ratio'] for r in search))
            search = [r for r in search if r['fuzz_ratio'] >= threshold]

            # Now we need to get more information to identify precisely
            # the movie
            for r in search:
                r['details'] = imdb.get_title(r['imdb_id'])

            # Try to get the closest movie using the movie duration
            # if available
            def weight_movie_by_duration(movie):
                if not duration:
                    return sys.maxint

                rt = movie['details']['base'].get('runningTimeInMinutes')
                if rt is None:
                    return sys.maxint

                movie['duration_closeness'] = abs(rt * 60. - duration)
                return movie['duration_closeness']

            closest = min(search, key=weight_movie_by_duration,)

            # If the closest still has a duration difference with the expected
            # one that is more than half of the expected duration, it is
            # probably not the right one!
            if duration and closest['duration_closeness'] > (duration / 2.):
                return

            # Return the imdb information of the closest movie found
            return imdb, closest['details'], closest['fuzz_ratio']

        ######################################################################
        # Internal function to search by text for an episode
        def search_text_episode():
            LOGGER.info('Searching media using text research on episode')
            ep = parsed['episode']

            # To allow to search on the tvdb
            tvdb = tvdb_api.Tvdb(
                cache=False,
                language='en',
            )

            # Perform the search, if nothing is found, there's a problem...
            try:
                series = tvdb.search(ep['show'])
            except Exception as e:
                raise ResolveException(e)

            if not series:
                return

            series = tvdb[series[0]['seriesName']]
            episode = series[ep['season']][ep['episodes'][0]]

            # Initialize the imdb object to perform the research
            imdb = imdbpie.Imdb(
                exclude_episodes=False,
            )

            # Use imdb to search for the series using its name or aliases
            search = None
            for seriesName in [series['seriesName'], ] + series['aliases']:
                try:
                    search = imdb.search_for_title(seriesName)
                except Exception as e:
                    raise ResolveException(e)

                # Filter the results by name and type
                search = [
                    s for s in search
                    if s['type'] == 'TV series' and
                    (s['title'] == seriesName or
                     '{title} ({year})'.format(**s) == seriesName)
                ]

                # If there is still more than one, filter by year
                if len(search) > 1:
                    search = [
                        s for s in search
                        if s['year'] == series['firstAired'][:4]
                    ]

                # If we have a series, we can stop there!
                if search:
                    break

            # If we did not find anything that matches
            if not search:
                return

            # Get the series' seasons and episodes
            series = imdb.get_title_episodes(search[0]['imdb_id'])
            for season in series['seasons']:
                if season['season'] != ep['season']:
                    continue

                for episode in season['episodes']:
                    if episode['episode'] != ep['episodes'][0]:
                        continue

                    # id is using format /title/ttXXXXXX/
                    return imdb, imdb.get_title(episode['id'][7:-1])

            # Not found
            return

        ######################################################################
        # Internal function to search by text
        def search_text():
            search = None
            if 'episode' in parsed:
                try:
                    search = search_text_episode()
                except ResolveException as e:
                    LOGGER.warning(
                        'Exception when trying to search manually '
                        'for an episode: {}'.format(e))

            if not search and 'movie' in parsed:
                try:
                    search = search_text_movie()
                except ResolveException as e:
                    LOGGER.warning(
                        'Exception when trying to search manually '
                        'for a movie: {}'.format(e))

            return search

        ######################################################################
        # Internal function to insert a hash
        def insert_hash(media, ratio):
            if not oshash or (parsed['type'] == 'movie' and ratio < 70.):
                return

            LOGGER.info('Sending movie hash information to opensubtitles')

            # Insert the movie hash if possible!
            media_duration = (
                duration * 1000.0
                if duration
                else media['base']['runningTimeInMinutes'] * 60. * 1000.
            )
            try:
                res = OpenSubtitlesAPI.insert_hash(
                    [
                        {
                            'moviehash': oshash,
                            'moviebytesize': size,
                            'imdbid': media['base']['id'][9:-1],
                            'movietimems': media_duration,
                            'moviefilename': meta['filename'],
                        },
                    ]
                )
            except Exception as e:
                raise ResolveException(e)

            LOGGER.info(res)
            if res['status'] != '200 OK':
                title = media['base']['title']
                if media['base']['titleType'] == 'tvEpisode':
                    title = '{} - S{:02d}E{:02d} - {}'.format(
                        media['base']['parentTitle']['title'],
                        media['base']['season'],
                        media['base']['episode'],
                        title,
                    )
                LOGGER.info('Unable to submit hash for \'{0}\': {1}'.format(
                    title, res['status']))
            elif oshash in res['data']['accepted_moviehashes']:
                LOGGER.info('New hash submitted and accepted')
            else:
                LOGGER.info('New hash submitted but not accepted')

        ######################################################################
        # Logic of that function

        # To determine if we'll have to insert the hash
        should_insert_hash = False
        media = None

        # First search using the hash
        try:
            media = search_hash()
        except ResolveException as e:
            LOGGER.warning(
                'Exception when trying to resolve the hash: {}'.format(e))

        # If not found, try using the information we can get from the metadata
        # and the file name
        if not media:
            should_insert_hash = True
            media = search_text()

        # If still not found, print an empty list, and return
        if not media:
            print('[]')
            return

        # Split the imdb object so we can reuse the one that has been
        # instanciated during the research
        ratio = media[2] if len(media) > 2 else 0
        imdb, media = media[:2]

        if media['base']['titleType'] == 'tvEpisode':
            parsed['type'] = 'episode'
        else:
            parsed['type'] = 'movie'

        # If we need to insert the hash, insert it for the first media found
        # only - OpenSubtitles does not allow duplicates, and it will still
        # allow for matches
        if oshash and should_insert_hash:
            try:
                insert_hash(media, ratio)
            except ResolveException as e:
                LOGGER.warning(
                    'Exception when trying to insert the hash: {}'.format(e))

        # Return in the form of a list
        media_list = [media, ]

        # If it was an episode, and we had more episodes in the list...
        if parsed['type'] == 'episode' and \
                len(parsed['episode']['episodes']) > 1:
            while len(media_list) < len(parsed['episode']['episodes']):
                # id is using format /title/ttXXXXXX/ - We just want
                # the ttXXXXXX
                media = imdb.get_title(media['base']['nextEpisode'][7:-1])
                media_list.append(media)

        for m in media_list:
            if m['base']['titleType'] == 'tvEpisode':
                m_series = m['base']['parentTitle']['title']
                m_season = m['base']['season']
                m_ep = m['base']['episode']
                m_year = m['base']['parentTitle']['year']
                m_series_imdbid = m['base']['parentTitle']['id'][7:-1]
                ids = resolve_episode_ids(m_series, m_season, m_ep, m_year,
                                          m_series_imdbid)
            else:
                m_movie = m['base']['title']
                m_year = m['base']['year']
                ids = resolve_movie_ids(m_movie, m_year)

            # Append the found IDs to the media
            for k, v in ids.items():
                m['base']['{}id'.format(k)] = v

        ######################################################################
        # Print the JSON dump of the media list
        print(json.dumps(tobyte(media_list), sort_keys=True,
                         indent=4, separators=(',', ': '),
                         ensure_ascii=False))
