#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (C) 2014-2017   Raphaël Beamonte <raphael.beamonte@gmail.com>
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

try:
    # Python 3
    import xmlrpc.client as xmlrpc
except ImportError:
    # Python 2
    import xmlrpclib as xmlrpc

import fuzzywuzzy.fuzz
import imdbpie
import logging
import math
import os
import requests
import struct
import time
import unicodedata

from TraktForVLC import __version__


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii


# Taken from http://trac.opensubtitles.org/projects/opensubtitles/wiki/, page
# HashSourceCodes#Python
def hashFile(name):
    try:
        longlongformat = '<q'  # little-endian long long
        bytesize = struct.calcsize(longlongformat)

        with open(name, "rb") as f:
            filesize = os.path.getsize(name)
            hash = filesize

            if filesize < 65536 * 2:
                return "SizeError"

            for x in range(65536 / bytesize):
                buffer = f.read(bytesize)
                (l_value,) = struct.unpack(longlongformat, buffer)
                hash += l_value
                hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

            f.seek(max(0, filesize - 65536), 0)
            for x in range(65536 / bytesize):
                buffer = f.read(bytesize)
                (l_value,) = struct.unpack(longlongformat, buffer)
                hash += l_value
                hash = hash & 0xFFFFFFFFFFFFFFFF

        returnedhash = "%016x" % hash
        return returnedhash

    except(IOError):
        return "IOError"


useragent = 'TraktForVLC v{0}'.format(__version__)
proxy = None
login = None


def get_movie_info(movie_fname, movie_name,
                   movie_year='', movie_duration=None):
    global useragent, proxy, login

    # Load logger
    LOG = logging.getLogger(__name__)

    try:
        movie_name = remove_accents(movie_name)
    except TypeError:
        pass

    LOG.debug(
        (
            'received parameters: {{movie_fname => {0}, movie_name => {1}, '
            'movie_year => {2}, movie_duration => {3}}}'
        ).format(
            movie_fname,
            movie_name,
            movie_year,
            movie_duration,
        )
    )

    # Initialize the imdbpie.Imdb object to get more information about movies
    imdb = imdbpie.Imdb(
        # For this version of TraktForVLC, we only want to return movies,
        # not episodes
        exclude_episodes=True,
    )

    movie_info = None
    movie_hash = None
    movie_found_by_hash = False

    if movie_fname and os.path.isfile(movie_fname):
        # Initialize the connection to opensubtitles
        if proxy is None:
            proxy = xmlrpc.ServerProxy("http://api.opensubtitles.org/xml-rpc")
        if login is None:
            login = proxy.LogIn('', '', 'en', useragent)
            LOG.debug('OpenSubtitles UserAgent: {0}'.format(useragent))

        # Compute the hash for the file
        movie_hash = hashFile(movie_fname)
        LOG.debug('Computed movie hash: {0}'.format(movie_hash))

        # Search for the files corresponding to this hash
        movies = proxy.CheckMovieHash2(login['token'], [movie_hash, ])
        movies = movies['data'] if 'data' in movies else []

        if movie_hash in movies:
            LOG.debug('We found movies using the hash')

            # Use fuzzywuzzy to get the closest file name
            movie_info = (
                max(
                    movies[movie_hash],
                    key=lambda x:
                        fuzzywuzzy.fuzz.ratio(movie_name, x)
                )
                if len(movies[movie_hash]) > 1
                else movies[movie_hash][0]
            )
            movie_info['details'] = imdb.get_title_by_id(
                'tt{0}'.format(movie_info['MovieImdbID']))
            movie_found_by_hash = True

    if movie_info is None:
        # Use imdb to search for the movie
        search = imdb.search_for_title(movie_name)
        if not search:
            raise RuntimeError('Movie not found! 1')

        LOG.debug('Found {0} results using IMDB'.format(len(search)))
        LOG.debug(search)

        # Compute the proximity ratio of the title and search if the actual
        # year exists if it was provided
        year_found = False
        for r in search:
            r['fuzz_ratio'] = fuzzywuzzy.fuzz.ratio(movie_name, r['title'])
            if movie_year and \
                    not year_found and \
                    r['year'] == movie_year and \
                    r['fuzz_ratio'] >= 50.:
                year_found = True

        # If the actual year exists, clean it
        if year_found:
            search = [r for r in search if r['year'] == movie_year]

        LOG.debug('{0} results left after first filters'.format(
            len(search)))
        LOG.debug(search)

        if movie_duration:
            # If we have the movie duration, we can use it to make the
            # research more precise
            sum_ratio = sum(r['fuzz_ratio'] for r in search)
            mean_ratio = sum_ratio / float(len(search))
            std_dev_ratio = math.sqrt(
                sum([
                    math.pow(r['fuzz_ratio'] - mean_ratio, 2)
                    for r in search
                ]) / float(len(search))
            )

            # Select only the titles over a given threshold
            threshold = max(50., mean_ratio + (std_dev_ratio / 2.))

            LOG.debug(
                (
                    'Computed ratio: {{mean => {0}, stdev => {1}, '
                    'threshold => {2}}}'
                ).format(
                    mean_ratio,
                    std_dev_ratio,
                    threshold,
                )
            )

            search = [r for r in search if r['fuzz_ratio'] >= threshold]
        else:
            # If we don't have the movie duration, just use
            # the highest ratio
            max_ratio = max(50., max(r['fuzz_ratio'] for r in search))
            search = [r for r in search if r['fuzz_ratio'] == max_ratio]
            if len(search) > 1:
                search = [search[0], ]

        LOG.debug('{0} results left after second filters'.format(
            len(search)))
        LOG.debug(search)

        if search:
            # Now we need to get more information to identify precisely
            # the movie
            for r in search:
                num_try = 0
                while 'details' not in r:
                    try:
                        r['details'] = imdb.get_title_by_id(r['imdb_id'])
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code != 503:
                            raise

                        num_try += 1
                        if num_try < 3:
                            LOG.info((
                                'Received HTTP 503 error, waiting {0} seconds '
                                'before retrying for movie {1}'
                            ).format(2 ** num_try, r))
                            time.sleep(2 ** num_try)
                        else:
                            LOG.info('Received HTTP 503 error, giving up')
                            break

            # Try to get the closest movie using the movie duration
            # if available
            movie_info = min(
                search,
                key=lambda x:
                    abs(x['details'].runtime - movie_duration)
                    if movie_duration and 'details' in x and
                    x['details'].runtime is not None
                    else float('inf')
            )
        else:
            movie_info = {}

    # We want to use only the details from now on
    details = movie_info.get('details')

    if details is None:
        raise LookupError("unable to find the movie '{0}'".format(movie_name))

    if movie_hash and \
            not movie_found_by_hash and \
            movie_info.get('fuzz_ratio', 0.) > 60.:
        LOG.debug('Sending movie hash information to opensubtitles')
        # Insert the movie hash if possible!
        res = proxy.InsertMovieHash(
            login['token'],
            [
                {
                    'moviehash': movie_hash,
                    'moviebytesize': os.path.getsize(movie_fname),
                    'imdbid': details.imdb_id[2:],
                    'movietimems': (
                        movie_duration
                        if movie_duration
                        else details.runtime
                    ),
                    'moviefilename': os.path.basename(movie_fname),
                },
            ]
        )
        if res['status'] != '200 OK':
            logging.warn('Unable to submit hash for movie \'{0}\': {1}'.format(
                details.title, res['status']))

    dict_info = {
        'Director': details.directors_summary[0].name,
        'Plot': details.plot_outline,
        'Runtime': details.runtime,
        'Title': details.title,
        'Year': details.year,
        'imdbID': details.imdb_id,
        'imdbRating': details.rating,
    }

    return dict_info
