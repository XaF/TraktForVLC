#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (C) 2014        Raphaël Beamonte
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


import re
import requests
import urllib
import json
import difflib

# The base url to do the imdb requests to
BASE_URL = 'http://www.imdbapi.com/?'

# The list of information we want to extract from the requests results
info_list = [
        'Plot',
        'Title',
        'Director',
        'tomatoRating',
        'imdbRating',
        'Runtime',
        'Year'
        ]


def get_movie_info(movi_name, movi_year = ''):
    # Formatting query to send
    query = {
            'i': '',
            't': movi_name,
            'y': movi_year,
            'tomatoes': 'true'
        }

    # Searching for the movie directly
    part = urllib.urlencode(query)
    url = BASE_URL+part
    response = requests.get(url)

    # Parsing json
    output = json.loads(response.content)

    # If we don't have a direct match, or if our direct match isn't a movie
    if (('Response' in output.keys() and output['Response'] == 'False')
            or output['Type'] != 'movie'):
        # We set a variable to indicate we didn't found the movie yet
        found = False

        # We didn't find the movie directly, try to 'search' it
        querySearch = {
                'i': '',
                's': movi_name,
                'y': movi_year
            }

        # Sending the research
        part = urllib.urlencode(querySearch)
        responseSearch = requests.get(BASE_URL+part)

        # Parsing json
        results = json.loads(responseSearch.content)

        # If we have results
        if 'Search' in results.keys():
            # We need first to filter the results to keep only the movies
            filtered = [i for i in results['Search'] if i['Type'] == 'movie']

            # If we had at least a movie in the list
            if filtered:
                # We sort it by similarity with the request
                bests = sorted(filtered,
                        key=lambda x: difflib.SequenceMatcher(None, x['Title'], movi_name).ratio(),
                        reverse=True
                        )

                # We select the most similar
                selected = bests[0]

                # And if its similarity is at least 90%, we act as if it's the movie
                if difflib.SequenceMatcher(None, selected['Title'], movi_name).ratio() >= 0.9:
                    found = True

                    # We make a new request using the imdbID of the found movie
                    # to load all of the information we wanted
                    query = {
                            'i': selected['imdbID'],
                            'tomatoes': 'true'
                            }

                    part = urllib.urlencode(query)
                    response = requests.get(BASE_URL+part)

                    # And we parse the new json
                    output = json.loads(response.content)

        # If we didn't find the movie, we raise an error
        if not found:
            raise LookupError("%s: %s" % (movi_name, results['Error']))

    # If we have found the movie, we organize its data to return it
    movie_info = {}
    for info in info_list:
        if info in output.keys():
            movie_info[info] = output[info]
        else:
            movie_info[info] = None

    return movie_info
