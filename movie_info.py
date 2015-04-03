#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (C) 2014-2015   Raphaël Beamonte <raphael.beamonte@gmail.com>
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

# English stopwords
STOPWORDS_EN = set([
    'a',
    'about',
    'above',
    'after',
    'again',
    'against',
    'all',
    'am',
    'an',
    'and',
    'any',
    'are',
    'aren\'t',
    'as',
    'at',
    'be',
    'because',
    'been',
    'before',
    'being',
    'below',
    'between',
    'both',
    'but',
    'by',
    'can\'t',
    'cannot',
    'could',
    'couldn\'t',
    'did',
    'didn\'t',
    'do',
    'does',
    'doesn\'t',
    'doing',
    'don\'t',
    'down',
    'during',
    'each',
    'few',
    'for',
    'from',
    'further',
    'had',
    'hadn\'t',
    'has',
    'hasn\'t',
    'have',
    'haven\'t',
    'having',
    'he',
    'he\'d',
    'he\'ll',
    'he\'s',
    'her',
    'here',
    'here\'s',
    'hers',
    'herself',
    'him',
    'himself',
    'his',
    'how',
    'how\'s',
    'i',
    'i\'d',
    'i\'ll',
    'i\'m',
    'i\'ve',
    'if',
    'in',
    'into',
    'is',
    'isn\'t',
    'it',
    'it\'s',
    'its',
    'itself',
    'let\'s',
    'me',
    'more',
    'most',
    'mustn\'t',
    'my',
    'myself',
    'no',
    'nor',
    'not',
    'of',
    'off',
    'on',
    'once',
    'only',
    'or',
    'other',
    'ought',
    'our',
    'ours',
    'ourselves',
    'out',
    'over',
    'own',
    'same',
    'shan\'t',
    'she',
    'she\'d',
    'she\'ll',
    'she\'s',
    'should',
    'shouldn\'t',
    'so',
    'some',
    'such',
    'than',
    'that',
    'that\'s',
    'the',
    'their',
    'theirs',
    'them',
    'themselves',
    'then',
    'there',
    'there\'s',
    'these',
    'they',
    'they\'d',
    'they\'ll',
    'they\'re',
    'they\'ve',
    'this',
    'those',
    'through',
    'to',
    'too',
    'under',
    'until',
    'up',
    'very',
    'was',
    'wasn\'t',
    'we',
    'we\'d',
    'we\'ll',
    'we\'re',
    'we\'ve',
    'were',
    'weren\'t',
    'what',
    'what\'s',
    'when',
    'when\'s',
    'where',
    'where\'s',
    'which',
    'while',
    'who',
    'who\'s',
    'whom',
    'why',
    'why\'s',
    'with',
    'won\'t',
    'would',
    'wouldn\'t',
    'you',
    'you\'d',
    'you\'ll',
    'you\'re',
    'you\'ve',
    'your',
    'yours',
    'yourself',
    'yourselves',
])

# Special chars commonly found in movie titles
SPECIALCHARS = set([
    '&',
    ':',
    ',',
    '-',
])


# The base url to do the imdb requests to
BASE_URL = 'http://www.imdbapi.com/?'

# The list of information we want to extract from the requests results
info_list = [
    'Plot',
    'Title',
    'Director',
    'tomatoRating',
    'imdbID',
    'imdbRating',
    'Runtime',
    'Year'
]


def get_movie_info(movi_name, movi_year=''):
    # Formatting query to send
    query = {
        'i': '',
        't': movi_name,
        'y': movi_year,
        'tomatoes': 'true'
    }

    # Searching for the movie directly
    part = urllib.urlencode(query)
    url = BASE_URL + part
    response = requests.get(url)

    # Parsing json
    output = json.loads(response.content)

    # If we don't have a direct match, or if our direct match isn't a movie
    if (('Response' in output.keys() and output['Response'] == 'False')
            or output['Type'] != 'movie'):
        # We set a variable to indicate we haven't found the movie yet
        found = False

        # We didn't find the movie directly, try to 'search' it
        querySearch = {
            'i': '',
            's': movi_name,
            'y': movi_year
        }

        tries = 0
        while tries < 2:
            tries += 1

            # Sending the research
            part = urllib.urlencode(querySearch)
            responseSearch = requests.get(BASE_URL + part)

            # Parsing json
            results = json.loads(responseSearch.content)

            # If we have results
            if 'Search' in results.keys():
                # We need first to filter the results to keep only the movies
                filtered = [i for i in results['Search']
                            if i['Type'] == 'movie']

                # If we had at least a movie in the list
                if filtered:
                    # We sort it by similarity with the request
                    bests = sorted(
                        filtered,
                        key=lambda x: difflib.SequenceMatcher(
                            None,
                            x['Title'],
                            movi_name).ratio(),
                        reverse=True
                    )

                    # We select the most similar
                    selected = bests[0]

                    # And if its similarity is at least 90%, we act as
                    # if it's the movie
                    diff_movi_name = difflib.SequenceMatcher(
                        None,
                        selected['Title'],
                        movi_name).ratio()
                    diff_querySearch = difflib.SequenceMatcher(
                        None,
                        selected['Title'],
                        querySearch['s']).ratio()
                    if (diff_movi_name >= 0.9
                            or (diff_querySearch >= 0.9
                                and diff_movi_name >= 0.8)):
                        found = True

                        # We make a new request using the imdbID of the found
                        # movie to load all of the information we wanted
                        query = {
                            'i': selected['imdbID'],
                            'tomatoes': 'true'
                        }

                        part = urllib.urlencode(query)
                        response = requests.get(BASE_URL + part)

                        # And we parse the new json
                        output = json.loads(response.content)

            # If we found the movie, or if we already tried to remove
            # the common words and special chars, we just stop now
            if found or tries == 2:
                break

            # Last try: we remove common words and chars from the title
            search = movi_name
            search = ' '.join(word for word in search.split()
                              if word not in STOPWORDS_EN)
            search = ' '.join(word for word in search.split()
                              if word not in SPECIALCHARS)

            # We verify that we still have words...
            search = search.split()
            if len(search) < 2:
                # We have only one word...
                break

            # We change the search string to use our new string
            # and profit that we splitted the string to only keep
            # one space between each word
            querySearch['s'] = ' '.join(search)

        # If we didn't find the movie, we raise an error
        if not found:
            raise LookupError("unable to find the movie '%s'" % (movi_name))

    # If we have found the movie, we organize its data to return it
    movie_info = {}
    for info in info_list:
        if info in output.keys():
            movie_info[info] = output[info]
        else:
            movie_info[info] = None

    return movie_info
