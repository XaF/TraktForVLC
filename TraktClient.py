#!/usr/bin/env python
# encoding: utf-8
#
# TraktForVLC, to link VLC watching to trakt.tv updating
#
# Copyright (C) 2012        Chris Maclellan <chrismaclellan@gmail.com>
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

# Imports
import logging
import requests
import json


# Trakt API URL for v2
api_url = 'https://api-v2launch.trakt.tv/'


# Whether or not to verify HTTPS certificates when calling the API
verifyHTTPS = True


# Function to get the right requests method depending on the verb we
# need to use in the API
def requestHandler(verb):
    return {
        'POST':     requests.post,
        'GET':      requests.get,
        'DELETE':   requests.delete,
        'PUT':      requests.put,
    }[verb]


# Class used for raising errors specifically linked to TraktClient
class TraktError(Exception):

    def __init__(self, msg):
        super(TraktError, self).__init__(msg)


# TraktClient class
class TraktClient(object):

    # Initialize the TraktClient class by passing the username and
    # password of the user
    def __init__(self, username, password, client_id,
                 app_version="unknown", app_date="unknown"):
        # Save those information inside the class
        self.username = username
        self.password = password
        self.app_version = app_version
        self.app_date = app_date

        # Define global headers for API communication
        self.headers = {
            'Content-Type':         'application/json',
            'trakt-api-version':    '2',
            'trakt-api-key':        client_id,
            'trakt-user-login':     username,
        }

        # Prepare the logging interface
        self.log = logging.getLogger("TraktClient")
        self.log.debug("TraktClient logger initialized")

    # Method used to call the API
    def call_method(self, method, verb='POST', data={}, retry=3):
        # if retry < 0:
        #    self.log.error("Failed to call '%s' method '%s'" (verb, method))

        # Only four allowed verbs to make the call
        verb = verb.upper()
        if verb not in ('POST', 'GET', 'DELETE', 'PUT'):
            raise TraktError("verb '%s' unknown" % verb)

        # We prepare the URL we'll connect to
        sendurl = api_url + method

        # We encode the data using json's dumps method
        encoded_data = json.dumps(data)

        self.log.debug("Sending %s to %s data %s" %
                       (verb, sendurl, str(encoded_data)))
        self.log.debug(encoded_data)

        # We call the API using the requests method returned bu the
        # requestHandler function
        stream = requestHandler(verb)(url=sendurl,
                                      data=encoded_data,
                                      headers=self.headers,
                                      verify=verifyHTTPS)

        # We return the response
        return stream

    # Login to Trakt to be able to call authenticated API methods
    def __login(self):
        # Prepare the data to send
        data = {
            'login':    self.username,
            'password': self.password,
        }

        # Use the call_method method to login
        stream = self.call_method('auth/login', 'POST', data)

        # If the return code is not 200 or 201, we had an error
        if not stream.ok:
            raise TraktError("Unable to authenticate: %s %s" % (
                stream.status_code, stream.reason))

        # If everything was fine, we search for the token in the response
        resp = stream.json()
        self.log.debug("Response from Trakt: %s" % str(resp))

        if 'token' in resp.keys():
            # We add that token to the headers we'll send for each request
            self.headers['trakt-user-token'] = resp['token']

            self.log.debug("Authenticated, token found")
            return

        # If no token was found, we raise an error
        raise TraktError(
            "Unable to authenticate: no token found in json %s" % str(resp))

    # Logout to Trakt
    def __logout(self):
        stream = self.call_method('auth/logout', 'DELETE')

        if not stream.ok:
            raise TraktError("Unable to logout: %s %s" %
                             (stream.status_code, stream.reason))

        del self.headers['trakt-user-token']

        self.log.debug("Logged out")
        return

    # Define an item as started, stopped or paused watching using
    # data passed as argument to identify that item
    def __scrobble(self, action, data, retry=False):
        # Only three actions allowed
        action = action.lower()
        if action not in ('start', 'stop', 'pause'):
            raise TraktError("action '%s' unknown" % action)

        # We call scrobble/x where x is one of the actions, using the
        # call_method method.
        stream = self.call_method('scrobble/%s' % action, 'POST', data)

        # If the answer is not 200 nor 201
        if not stream.ok:
            # If it was a 401 HTTP error, we need to authenticate, then
            # we can call again that function. We try again just one time
            # in case the 401 error was not due to authentication
            if not retry and stream.status_code == 401:
                self.__login()
                self.__scrobble(action, data, True)
                return

            # If it was another error, we raise an error, as it's not normal
            videotype = ("episode" if "episode" in data else "movie")
            raise TraktError("Unable to %s %s: %s %s" % (
                action, videotype, stream.status_code,
                stream.reason))
        else:
            # Else, we just return the potential json response from the server
            return stream.json()

    # Define an item as started, stopped or paused watching using
    # its imdb id, its progress and the fact it is or not an episode
    # of a tv show. This method either calls the __scrobble one after
    # having generated the data dict, or the __watchingEpisode one if
    # the item is an episode and the given episode variable is a
    # tuple containing in order the show's imdb id, the season number
    # and the episode number.
    def __watching(self, action, imdb_id, progress, episode=False):
        # If episode is a tuple, we will call __watchingEpisode
        if episode and type(episode) == tuple and len(episode) == 3:
            return self.__watchingEpisode(action=action,
                                          show_imdb_id=episode[0],
                                          season=episode[1],
                                          episode=episode[2],
                                          progress=progress)

        # We prepare the data to send
        videotype = ("episode" if episode else "movie")
        data = {
            videotype: {
                "ids": {
                    "imdb": imdb_id,
                }
            },
            "progress":     progress,
            "app_version":  self.app_version,
            "app_date":     self.app_date,
        }

        return self.__scrobble(action, data)

    # Define an episode as started, stopped or paused watching using
    # its show's imdb id, its season number, its episode number, and
    # its progress. This method calls the __scrobble one after having
    # generated the data dict
    def __watchingEpisode(self, action, show_imdb_id,
                          season, episode, progress):
        # We prepare the data to send
        data = {
            "show": {
                "ids": {
                    "imdb": show_imdb_id,
                }
            },
            "episode": {
                "season":   season,
                "number":   episode,
            },
            "progress":     progress,
            "app_version":  self.app_version,
            "app_date":     self.app_date,
        }

        return self.__scrobble(action, data)

    # Wrapper method that calls the watching method using 'start' as action
    def startWatching(self, imdb_id, progress, episode=False):
        return self.__watching('start', imdb_id, progress, episode)

    # Wrapper method that calls the watching method using 'stop' as action
    def stopWatching(self, imdb_id, progress, episode=False):
        return self.__watching('stop', imdb_id, progress, episode)

    # Wrapper method that calls the watching method using 'pause' as action
    def pauseWatching(self, imdb_id, progress, episode=False):
        return self.__watching('pause', imdb_id, progress, episode)

    # Method to cancel what was currently watched based on its imdb id
    # and the fact it is or not an episode of a show
    def cancelWatching(self, imdb_id, episode=False):
        # As per the Trakt API v2, we need to call the start method
        # saying that the watch is at the end, so it will expire
        # soon after.
        return self.__watching('start', imdb_id, 99.99, episode)
