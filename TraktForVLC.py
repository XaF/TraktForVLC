#!/usr/bin/env python
# encoding: utf-8
#
# TraktForVLC, to link VLC watching to trakt.tv updating
#
# Copyright (C) 2012        Chris Maclellan <chrismaclellan@gmail.com>
# Copyright (C) 2013        Damien Battistella <wifsimster@gmail.com>
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

# Python lib import
from copy import deepcopy
import datetime
import getopt
import logging
import os
from pkg_resources import parse_version
import re
import requests
import signal
import sys
import time
import traceback
from urllib import unquote
from urlparse import urlparse

# Local import
import ConfigParser
from filenameparser import parse_tv, parse_movie
import movie_info
import TraktClient
import tvdb_api
from vlcrc import VLCRemote


__release_name__ = "Six Feet Under"
__version_info__ = (1, 1, 0, '', 0)
__version__ = "%d.%d.%d%s" % __version_info__[:4]

TIMER_INTERVAL = START_WATCHING_TIMER = 0

# Current date
DATETIME = datetime.datetime.now()

# Available log levels
AVAILABLE_LOGLVL = [
        (logging.NOTSET,    'NOTSET'),      # 0
        (logging.DEBUG,     'DEBUG'),       # 10
        (logging.INFO,      'INFO'),        # 20
        (logging.WARNING,   'WARNING'),     # 30
        (logging.ERROR,     'ERROR'),       # 40
        (logging.CRITICAL,  'CRITICAL'),    # 50
        ]

# Specify default log level
LOG_LEVEL = logging.WARNING

# Use small timers, useful in debug mode
SMALL_TIMERS = False

class TraktForVLC(object):

    # Check if there's a newer version of TraktForVLC on the project's github,
    # and print informations on that subject in the logs
    def __check_version(self):
        # The leading information for lines printed by this method in logs
        lead = "VERSION:"

        # Request the github API to get the releases information
        github_releases = requests.get(
            url="https://api.github.com/repos/XaF/TraktForVLC/releases")

        # If there was a problem getting the releases
        if not github_releases.ok:
            self.log.error(lead +
                           "Unable to verify new releases of TraktForVLC")
            return

        # Else, we get the json answer
        releases = github_releases.json

        # If we didn't find any release
        if not releases:
            self.log.warning(lead +
                             "No releases found on github")
            return

        # We get the latest release, all included
        newest = sorted(
            releases,
            key=lambda x: x['tag_name'],
            reverse=True)[0]
        newest_V = parse_version(newest['tag_name'])
        if newest_V[0] == '*v':
            newest_V = newest_V[1:]

        # We get the latest _stable_ release
        newest_stbl = sorted(
            [r for r in releases if not r['prerelease']],
            key=lambda x: x['tag_name'],
            reverse=True)[0]
        newest_stbl_V = parse_version(newest_stbl['tag_name'])
        if newest_stbl_V[0] == '*v':
            newest_stbl_V = newest_stbl_V[1:]

        # We parse the current version
        current_V = parse_version(__version__)

        if newest_V <= current_V:
            self.log.info(lead + "TraktForVLC is up to date")
            return

        # We only show the latest stable release if
        # it's newer than our current release
        if newest_stbl_V > current_V:
            # We reformat the publication date of the release
            published = datetime.datetime.strptime(
                newest_stbl['published_at'],
                "%Y-%m-%dT%H:%M:%SZ").strftime('%c')

            self.log.info(lead + "##### RELEASE #####")
            self.log.info(lead + "## Stable release %(name)s" % newest_stbl)
            self.log.info(lead + "## Published on %s" % published)
            self.log.info(lead + "## Available on %(html_url)s" % newest_stbl)

        # We only show the latest release if it's not
        # also the latest stable release
        if newest_V > newest_stbl_V:
            # We reformat the publication date of the release
            published = datetime.datetime.strptime(
                newest['published_at'],
                "%Y-%m-%dT%H:%M:%SZ").strftime('%c')

            self.log.info(lead + "##### RELEASE #####")
            self.log.info(lead + "## Prerelease %(name)s" % newest)
            self.log.info(lead + "## Published on %s" % published)
            self.log.info(lead + "## Available on %(html_url)s" % newest)

        self.log.info(lead + "###################")


    def __init__(self, datadir, configfile):

        # Verify if the log directory exists or create it
        logdir = os.path.join(datadir, 'logs')
        if not os.path.exists(logdir):
            os.mkdir(logdir)

        # Process log file name
        if LOG_LEVEL is logging.DEBUG:
            logfile = os.path.join(logdir, "TraktForVLC-DEBUG.log")

            # Remove existing DEBUG file
            if os.path.isfile(logfile):
                os.remove(logfile)
        else:
            logfile = os.path.join(logdir, "TraktForVLC-" + DATETIME.strftime("%y-%m-%d-%H-%M") + ".log")

        logging.basicConfig(format="%(asctime)s::%(name)s::%(levelname)s::%(message)s",
                            level=LOG_LEVEL,
                            filename=logfile,
                            stream=sys.stdout)

        self.log = logging.getLogger("TraktForVLC")
        self.log.info("----------------------------------------------------------------------------")
        self.log.info("                        TraktForVLC v" + __version__ + " by XaF")
        self.log.info("                           Last update : 07/28/2014")
        self.log.info("                        contact : raphael.beamonte@gmail.com")
        self.log.info("              Description : Allow scrobbling VLC content to Trakt")
        self.log.info("          Download : https://github.com/XaF/TraktForVLC.git")
        self.log.info("----------------------------------------------------------------------------")
        self.log.info("Initializing Trakt for VLC...")

        if not os.path.isfile(configfile):
            self.log.error("Config file " + configfile + " not found, exiting.")
            exit()

        self.__check_version()

        self.config = ConfigParser.RawConfigParser()
        self.config.read(configfile)

        # Initialize timers
        if SMALL_TIMERS:
            self.TIMER_INTERVAL = 5
            self.START_WATCHING_TIMER = 5
        else:
            self.TIMER_INTERVAL = int(self.config.get("TraktForVLC", "Timer"))
            self.START_WATCHING_TIMER = int(self.config.get("TraktForVLC", "StartWatching"))

        # For the use of filenames instead of VLC window title
        self.USE_FILENAME = True if self.config.get("TraktForVLC", "UseFilenames") == 'Yes' else False

        # Do we have to scrobble ?
        self.DO_SCROBBLE_MOVIE = True if self.config.get("TraktForVLC", "ScrobbleMovie") == 'Yes' else False
        self.DO_SCROBBLE_TV = True if self.config.get("TraktForVLC", "ScrobbleTV") == 'Yes' else False

        # Do we have to mark as watching ?
        self.DO_WATCHING_MOVIE = True if self.config.get("TraktForVLC", "WatchingMovie") == 'Yes' else False
        self.DO_WATCHING_TV = True if self.config.get("TraktForVLC", "WatchingTV") == 'Yes' else False

        # What percent should we use to scrobble videos ?
        self.SCROBBLE_PERCENT = int(self.config.get("TraktForVLC", "ScrobblePercent"))

        for loglvl, logstr in AVAILABLE_LOGLVL:
            if LOG_LEVEL <= loglvl:
                loglevelstr = logstr
                break
        if loglevelstr is None:
            loglevelstr = str(LOG_LEVEL)

        self.log.info("Logger level is set to %s" % loglevelstr);
        self.log.info("-- Will scrobble movies ? %s" % ('Yes' if self.DO_SCROBBLE_MOVIE else 'No'))
        self.log.info("-- Will scrobble tv shows ? %s" % ('Yes' if self.DO_SCROBBLE_TV else 'No'))
        self.log.info("-- Will we mark movies as being watched ? %s" % ('Yes' if self.DO_WATCHING_MOVIE else 'No'))
        self.log.info("-- Will we mark tv shows as being watched ? %s" % ('Yes' if self.DO_WATCHING_TV else 'No'))
        self.log.info("-- Videos will be scrobbled after " + str(self.SCROBBLE_PERCENT) + "% of their duration has been exceeded")
        self.log.info("-- Timer set to " + str(self.TIMER_INTERVAL) + " secs")
        self.log.info("-- Video will be marked as \"is watching\" from " + str(self.START_WATCHING_TIMER) + " secs")

        # VLC configuration
        self.vlc_ip = self.config.get("VLC", "IP")
        self.vlc_port = self.config.getint("VLC", "Port")

        self.log.info("Listening VLC to " + self.vlc_ip + ":" + str(self.vlc_port))

        # Trakt configuration
        trakt_api = "0e59f99095515c228d5fbc104e342574941aeeeda95946b8fa50b2b0366609bf"
        trakt_username = self.config.get("Trakt", "Username")
        trakt_password = self.config.get("Trakt", "Password")

        self.log.info("Connect to Trakt(" + trakt_username + ", *********)")

        # Initialize Trakt client
        modifiedTime = time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(__file__)))
        self.trakt_client = TraktClient.TraktClient(trakt_username,
                                                    trakt_password,
                                                    trakt_api,
                                                    __version__,
                                                    modifiedTime)

        self.resetCache()

        # Initialize tvdb api
        self.tvdb = tvdb_api.Tvdb(cache=False, language='en')

        self.watching_now = ""
        self.vlcTime = 0
        self.vlc_connected = True

    def resetCache(self, filename = None, filelength = None):
        self.log.debug("reset cache (%s, %s)" % (filename, filelength))
        self.cache = {
            "vlc_file_name": filename,
            "vlc_file_length": filelength,
            "scrobbled": False,
            "movie_info": None,
            "series_info": None,
            "series_current_ep": -1,
            "started_watching": None,
            "watching": -1,
            "video": {},
        }

    def resetCacheView(self, episode = None):
        self.log.debug('reset cache view status (%s)' % episode)

        self.cache['watching'] = -1
        self.cache['scrobbled'] = False
        self.cache['started_watching'] = None

        if episode is not None:
            self.cache['series_current_ep'] = episode

    def close(self, signal, frame):
        self.log.info("Program closed by SIGINT")
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.close)

        while (True):
            try:
                self.main()
            except Exception, e:
                self.log.error("An unknown error occurred", exc_info=sys.exc_info())
            time.sleep(self.TIMER_INTERVAL)
        self.main()

    def main(self):
        try:
            vlc = VLCRemote(self.vlc_ip, self.vlc_port)
            self.vlc_connected = True
        except:
            if self.vlc_connected:
                self.log.info('Could not find VLC running at ' + str(self.vlc_ip) + ':'+ str(self.vlc_port))
                self.log.debug('Make sure your VLC player is running with --extraintf=rc --rc-host='+ str(self.vlc_ip) +':' + str(self.vlc_port) + ' --rc-quiet', exc_info=sys.exc_info())
                self.vlc_connected = False

                # If we were watching a video but we didn't finish it, we
                # have to cancel the watching status
                if self.cache["watching"] > -1 and not self.cache["scrobbled"]:
                    self.trakt_client.cancelWatching(self.cache["video"]["imdbid"],
                                                     self.get_episode(self.cache["video"]))

                # If there is something in the cache, we can purge the watching and scrobbled
                # information, so if the video is opened again we will consider it's a new watch
                if self.cache['vlc_file_name'] is not None:
                    self.resetCacheView()

            return

        vlcStatus = vlc.is_playing()
        if not vlcStatus:
            vlc.close()
            return

        currentFileLength = vlc.get_length()
        if not int(currentFileLength) > 0:
            self.log.debug("main::File length is 0, can't do anything")
            vlc.close()
            return

        if self.USE_FILENAME:
            currentFileName = vlc.get_filename()
        else:
            currentFileName = vlc.get_title()
        self.vlcTime = int(vlc.get_time())

        # Parse the filename to verify if it comes from a stream
        parsed = urlparse(currentFileName)
        if parsed.netloc:
            # Set the filename using only the basename of the parsed path
            currentFileName = os.path.basename(parsed.path)

            # And use urllib's unquote to bring back special chars
            currentFileName = unquote(currentFileName)
        elif self.USE_FILENAME:
            # Even if it's not from a stream, if it's a filename we're using
            # we need to keep only the basename of the parsed path
            currentFileName = os.path.basename(currentFileName)

        if (currentFileName == self.cache["vlc_file_name"]
                and currentFileLength == self.cache['vlc_file_length']):
            if self.cache["series_info"] is None and self.cache["movie_info"] is None:
                video = None
            elif self.cache["series_info"] is not None:
                video = self.get_TV(vlc, self.cache["series_info"])
            else:
                video = self.get_Movie(vlc, self.cache["movie_info"])
        else:
            self.log.debug("main::New file: %s (%s)" % (currentFileName, currentFileLength))

            # If we were watching a video but we didn't finish it, we
            # have to cancel the watching status
            if self.cache["watching"] > -1 and not self.cache["scrobbled"]:
                self.trakt_client.cancelWatching(self.cache["video"]["imdbid"],
                                                 self.get_episode(self.cache["video"]))

            self.resetCache(currentFileName, currentFileLength)
            self.cache['started_watching'] = (time.time(), self.vlcTime)

            video = self.get_TV(vlc)
            if video is None:
                video = self.get_Movie(vlc)

        if video is None:
            self.log.info("No tv show nor movie found for the current playing video")
            vlc.close()
            return

        # We cache the updated video information
        self.cache["video"] = video

        logtitle = video["title"]
        if video["tv"]:
            logtitle += " - %01dx%02d" % (int(video["season"]), int(video["episode"]))

            # If we changed episode, we have to reset the view status
            if (self.cache['watching'] > -1
                    and self.cache['series_current_ep'] != video['episode']):
                self.resetCacheView(video['episode'])
                self.cache['started_watching'] = (time.time(), self.vlcTime % video['duration'])

        self.log.info(logtitle + " state : " + str(video["percentage"]) + "%")
        self.log.debug("main::Video: %s" % str(video))
        self.log.debug("main::This video is scrobbled : " + str(self.cache["scrobbled"]))

        if (((video['tv'] and self.DO_SCROBBLE_TV) or (not video['tv'] and self.DO_SCROBBLE_MOVIE))
                and video["percentage"] >= self.SCROBBLE_PERCENT
                and not self.cache["scrobbled"]
                and self.cache['started_watching'] is not None
                and (time.time() - self.cache['started_watching'][0]) > (float(video['duration']) / 3.0)
                and (self.vlcTime - self.cache['started_watching'][1]) > (float(video['duration']) / 4.0)
                ):
            self.log.info("Scrobbling "+ logtitle + " to Trakt...")
            try:
                self.trakt_client.stopWatching(video["imdbid"],
                                               video["percentage"],
                                               self.get_episode(video))

                self.cache["scrobbled"] = True
                self.log.info(logtitle + " scrobbled to Trakt !")
            except TraktClient.TraktError, (e):
                self.log.error("An error occurred while trying to scrobble", exc_info=sys.exc_info())
                if ("scrobbled" in e.msg and "already" in e.msg):
                    self.log.info("Seems we've already scrobbled this episode recently, aborting scrobble attempt.")
                    self.cache["scrobbled"] = True

        elif (((video['tv'] and self.DO_WATCHING_TV) or (not video['tv'] and self.DO_WATCHING_MOVIE))
                and video["percentage"] < self.SCROBBLE_PERCENT
                and not self.cache["scrobbled"]
                and (float(video["duration"]) * float(video["percentage"]) / 100.0) >= self.START_WATCHING_TIMER):
            self.log.debug("main::Trying to mark " + logtitle + " watching on Trakt...")

            try:
                self.trakt_client.startWatching(video["imdbid"],
                                                video["percentage"],
                                                self.get_episode(video))

                self.log.info(logtitle + " is currently watching on Trakt...")
                self.cache["watching"] = video["percentage"]
            except TraktClient.TraktError, (e):
                self.log.error("An error occurred while trying to mark as watching " + logtitle, exc_info=sys.exc_info())

        vlc.close()

    def get_episode(self, video):
        episode = video["tv"]
        if episode and not video["imdbid"]:
            episode = (video["show_imdbid"],
                       video["season"],
                       video["episode"])

        return episode

    def get_TV(self, vlc, series_info = (None, None, None)):
        try:
            series, seasonNumber, episodeNumber = series_info
            if series is None:
                now_playing = parse_tv(self.cache['vlc_file_name'])

                if not now_playing:
                    self.log.info("Not able to parse a tvshow from the title file")
                    return

                seriesName = now_playing['show']
                seasonNumber = now_playing['season']
                episodeNumber = now_playing['episodes']

                if self.valid_TV(seriesName):
                    series = self.tvdb[seriesName]
                    self.cache["series_info"] = (deepcopy(series), seasonNumber, episodeNumber)

            if series is not None:
                duration = int(self.cache['vlc_file_length'])
                time = int(self.vlcTime)

                # Calculate the relative time and duration depending on the number of episodes
                duration = int(float(duration) / float(len(episodeNumber)))
                currentEpisode = episodeNumber[time / duration]
                time = time % duration

                # Calculate the given percentage for the current episode
                percentage = time*100/duration

                try:
                    episode = series[int(seasonNumber)][int(currentEpisode)]
                    return self.set_video(True, series['seriesname'], series['firstaired'], episode['imdb_id'], duration, percentage, episode['seasonnumber'], episode['episodenumber'], series['imdb_id'])
                except:
                    self.log.warning("Episode : No valid episode found !")
                    self.log.debug("get_TV::Here's to help debug", exc_info=sys.exc_info())
                    self.cache["series_info"] = None
                    return
        except:
            self.log.info("No matching tv show found for video playing")
            self.log.debug("get_TV::Here's to help debug", exc_info=sys.exc_info())
            return

    def valid_TV(self, seriesName):
        try:
            #series = tvrage_feeds.full_search(seriesName)
            series = self.tvdb.search(seriesName)
            if (len(series) == 0):
                self.log.debug("valid_TV::no series found with the name '%s'" % seriesName)
                return False
            return True
        except:
            self.log.debug("valid_TV::no valid title found.", exc_info=sys.exc_info())
            return False

    def get_Movie(self, vlc, movie = None):
        try:
            duration = int(self.cache['vlc_file_length'])
            if movie is None:
                now_playing = parse_movie(self.cache['vlc_file_name'])
                title = now_playing['title']
                year = now_playing['year']

                self.log.debug("get_Movie::Now playing: %s" % str(now_playing))

                if self.valid_Movie(title, year, duration):
                    movie = self.cache["movie_info"]
                    self.log.debug("get_Movie::Valid movie found: %s" % str(movie))

            if movie is not None:
                playtime = int(self.vlcTime)
                percentage = playtime*100/duration

                return self.set_video(False, movie['Title'], movie['Year'], movie['imdbID'], duration, percentage)

            return
        except:
            self.log.info("No matching movie found for video playing")
            self.log.debug("get_Movie::Here's to help debug", exc_info=sys.exc_info())
            return


    def valid_Movie(self, vlcTitle, vlcYear, vlcDuration):
        try:
            # Get Movie info
            movie = movie_info.get_movie_info(vlcTitle, vlcYear)
            # Compare Movie runtime against VLC runtime
            regex = re.compile('^((?P<hour>[0-9]{1,2}).*?h)?.*?(?P<min>[0-9]+).*?min?',re.IGNORECASE|re.MULTILINE)
            r = regex.search(movie['Runtime'])
            try:
                timeh = 0 if r.group('hour') is None else int(r.group('hour'))
                timem = 0 if r.group('min') is None else int(r.group('min'))
                time = timeh*60*60+timem*60
            except:
                self.log.debug("valid_Movie::unable to compute the duration", exc_info=sys.exc_info())
                return False
            # Verify that the VLC duration is within 5 minutes of the official duration
            if (vlcDuration >= time - 300) and (vlcDuration <= time + 300):
                self.cache["movie_info"] = deepcopy(movie)
                return True
            else:
                self.log.debug("valid_Movie::time range not respected (%d +-300 != %d)" % (time, vlcDuration))
        except:
            self.log.debug("valid_Movie::no valid title found", exc_info=sys.exc_info())
            return False
        return False

    def set_video(self, tv, title, year, imdbid, duration, percentage, season = -1, episode = -1, show_imdbid = None):
        video = {
                'tv': tv,
                'title': title,
                'year': year,
                'imdbid': imdbid,
                'duration': duration,
                'percentage': percentage,
                'season': season,
                'episode': episode,
                'show_imdbid': show_imdbid,
                }
        return video

def daemonize(pidfile=""):
    """
    Forks the process off to run as a daemon. Most of this code is from the
    sickbeard project.
    """

    if (pidfile):
        if os.path.exists(pidfile):
            sys.exit("The pidfile " + pidfile + " already exists, Trakt for VLC may still be running.")
        try:
            file(pidfile, 'w').write("pid\n")
        except IOError, e:
            sys.exit("Unable to write PID file: %s [%d]" % (e.strerror, e.errno))

    # Make a non-session-leader child process
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]" % (e.strerror, e.errno))

    os.setsid() #@UndefinedVariable - only available in UNIX

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    if (pidfile):
        file(pidfile, "w").write("%s\n" % str(os.getpid()))

if __name__ == '__main__':
    should_pair = should_daemon = False
    pidfile = ""
    datadir = os.path.dirname(__file__)
    logfile = ""
    config = ""

    def help():
        print "Available options:"
        print '     --config=path           Path to config file'
        print '     -d,--daemon             Run as daemon'
        print '     --datadir=path          Location of the app data (logs,...)'
        print '     --debug                 Enter DEBUG mode'
        print '     -h,--help               This message'
        print '     --loglevel=lvl          Specify the log level'
        print '     --pidfile=path          Indicate pidfile (for daemon mode)'
        print '     --small-timers          Activate small timers (for DEBUG mode)'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "dh", [
            'config=',
            'daemon',
            'datadir=',
            'debug',
            'help',
            'loglevel=',
            'pidfile=',
            'small-timers',
            ])
    except getopt.GetoptError, e:
        print 'Error:', e.msg
        help()
        sys.exit(1)

    for o, a in opts:
        # Determine location of config file
        if o in ('--config',):
            config = str(a)

        # Run as a daemon
        elif o in ('-d', '--daemon'):
            if sys.platform == 'win32':
                print "Daemonize not supported under Windows, starting normally"
            else:
                should_daemon = True

        # Determine location of datadir
        elif o in ('--datadir',):
            datadir = str(a)

        # DEBUG mode
        elif o in ('--debug',):
            LOG_LEVEL = logging.DEBUG

        # Help message
        elif o in ('-h', '--help',):
            help()
            sys.exit(0)

        # Specify log level
        elif o in ('--loglevel',):
            LOG_LEVEL = None
            if a.isdigit():
                LOG_LEVEL = int(a)
            else:
                for loglvl, logstr in AVAILABLE_LOGLVL:
                    if a == logstr: LOG_LEVEL = loglvl
                if LOG_LEVEL is None:
                    raise Exception("LOG_LEVEL %s unknown", a)

        # Create pid file
        elif o in ('--pidfile',):
            pidfile = str(a)

        # Use small timers instead of those in the config file
        elif o in ('--small-timers',):
            SMALL_TIMERS = True

        # An untreated command-line option has been passed
        else:
            raise Exception('Unknown command line option: %s', o)

    if should_daemon:
        daemonize(pidfile)
    elif (pidfile):
        file(pidfile, "w").write("%s\n" % str(os.getpid()))

    if config == "":
        config = datadir
    configfile = os.path.join(config, "config.ini")

    client = TraktForVLC(datadir, configfile)
    client.run()



