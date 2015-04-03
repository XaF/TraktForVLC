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
BASE_URL = 'http://www.imdbapi.com/'

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
    response = requests.get(BASE_URL, params=query)

    # Parsing json
    output = response.json()

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
            responseSearch = requests.get(BASE_URL, params=querySearch)

            # Parsing json
            results = responseSearch.json()

            # If we have results
            if 'Search' in results.keys():
                # We need first to filter the results to keep only the movies
                filtered = [i for i in results['Search']
                            if i['Type'] == 'movie']

                # If we have at least a movie in the list
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

                    # And we now check the similarity following three
                    # steps...
                    # 1/ if the movie title is at least 90% similar to
                    #    our request, we consider that we found it
                    diff_movi_name = difflib.SequenceMatcher(
                        None,
                        selected['Title'].lower(),
                        movi_name.lower()).ratio()

                    similarEnough = False
                    if diff_movi_name >= 0.9:
                        similarEnough = True

                    # 2/ Else, if the search string is different from
                    #    our original request because it has been cleaned
                    #    we check that the movie title is at least 90%
                    #    similar to the search string and 80% similar
                    #    to the original request
                    if (not similarEnough
                            and diff_movi_name >= 0.8):
                        if movi_name != querySearch['s']:
                            diff_querySearch = difflib.SequenceMatcher(
                                None,
                                selected['Title'].lower(),
                                querySearch['s'].lower()).ratio()

                            if diff_querySearch >= 0.9:
                                similarEnough = True
                        else:
                            diff_querySearch = diff_movi_name

                    # 3/ Finally, if we still haven't considered the
                    #    movie we found as the one we searched for, we
                    #    will clean its title using our common words list
                    #    and special chars, and check if the cleaned
                    #    movie title is at least 90% similar to our
                    #    search string and the movie title at least
                    #    80% similar to our search string and 70%
                    #    similar to our original request.
                    if (not similarEnough
                            and diff_querySearch >= 0.8
                            and diff_movi_name >= 0.7):
                        ctitle = selected['Title']
                        ctitle = ' '.join(word for word in ctitle.split()
                                          if word.lower() not in STOPWORDS_EN)
                        ctitle = ' '.join(word for word in ctitle.split()
                                          if word.lower() not in SPECIALCHARS)

                        diff_ctitle = difflib.SequenceMatcher(
                            None,
                            ctitle.lower(),
                            querySearch['s'].lower()).ratio()

                        if diff_ctitle >= 0.9:
                            similarEnough = True

                    if similarEnough:
                        found = True

                        # We make a new request using the imdbID of the found
                        # movie to load all of the information we wanted
                        query = {
                            'i': selected['imdbID'],
                            'tomatoes': 'true'
                        }

                        response = requests.get(BASE_URL, params=query)

                        # And we parse the new json
                        output = response.json()

            # If we found the movie, or if we already tried to remove
            # the common words and special chars, we just stop now
            if found or tries == 2:
                break

            # Last try: we remove common words and chars from the title
            search = movi_name
            search = ' '.join(word for word in search.split()
                              if word.lower() not in STOPWORDS_EN)
            search = ' '.join(word for word in search.split()
                              if word.lower() not in SPECIALCHARS)

            # We verify that the new string is different from the previous
            if search == movi_name:
                # It's the same...
                break

            # We verify that we still have words...
            search = search.split()
            if len(search) < 2 and len(search[0]) < 5:
                # We have only one word of less than 5 characters...
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
