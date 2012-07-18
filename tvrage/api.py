# Copyright (c) 2009, Christian Kreutzer
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re
import feeds

from urllib2 import urlopen, URLError
from datetime import date
from time import mktime, strptime

class ShowHasEnded(Exception): pass
class NoNewEpisodesAnnounced(Exception): pass
class FinaleMayNotBeAnnouncedYet(Exception): pass


class Episode(object):
    """represents an tv episode description from tvrage.com"""
    
    def __init__(self, show, season, airdate, title, link, number, prodnumber):
        self.show = show
        self.season = season
        try:
            self.airdate = date.fromtimestamp(mktime(strptime(airdate, '%Y-%m-%d')))
        except ValueError:
            self.airdate = None 
        self.title = title
        self.link = link
        self.number = number
        self.prodnumber = prodnumber
        

    def __unicode__(self):
        return '%s %sx%02d %s' % (self.show, self.season, self.number, self.title)
    
    __str__ = __repr__ = __unicode__
    
    @property
    def summary(self):
        """scraps the plot summary episode's tvrage page using a regular 
        expression this method might break when the page changes. unfortunatly 
        the episode summary isnt available via one of the xml feeds"""
        try:
            page = urlopen(self.link).read()
            if not 'There is no summary added for this episode' in page:
                try:
                    summary = re.search(
                        r"</script><br>(.*?)<br>", page,
                        re.MULTILINE).group(1).strip()
                    return unicode(summary, 'utf-8')
                except Exception, e:
                    print('Episode.summary: %s, %s' % (self, e))
        except URLError, e:
            print('Episode.summary:urlopen: %s, %s' % (self, e))
        return 'No Summary available'


class Season(dict):
    """represents a season container object"""

    is_current = False

    def episode(self, n):
        """returns the nth episode"""
        return self[n]

    @property
    def premiere(self):
        """returns the season premiere episode"""
        return self[1] # analog to the real world, season is 1-based

    @property
    def finale(self):
        """returns the season finale episode"""
        if not self.is_current:
            return self[len(self.keys())]
        else:
            raise FinaleMayNotBeAnnouncedYet, 'this is the current season...'


class Show(object):
    """represents a TV show description from tvrage.com
    
    this class is kind of a wrapper around the following of tvrage's xml feeds:
    * http://www.tvrage.com/feeds/search.php?show=SHOWNAME
    * http://www.tvrage.com/feeds/episode_list.php?sid=SHOWID
    """

    def __init__(self, name):
        self.shortname = name
        self.episodes = {}
        
        # the following properties will be populated dynamically
        self.genres = []
        self.showid = ''
        self.name = ''
        self.link = ''
        self.country = ''
        self.status = ''
        self.classification = ''
        self.started = 0
        self.ended = 0
        self.seasons = 0

        show = feeds.search(self.shortname, node='show')
        # dynamically mapping the xml tags to properties:
        for elem in show:
            # Don't set these yet
            if elem.tag in ('seasons', ):
                continue
            # these properties should be ints
            elif elem.tag in ('started', 'ended'):
                self.__dict__[elem.tag] = int(elem.text)
            # these are fine as strings
            else:
                self.__dict__[elem.tag] = elem.text
        self.genres = [g.text for g in show.find('genres')]

        # and now grabbing the episodes
        eplist = feeds.episode_list(self.showid, node='Episodelist')

        # populating the episode list
        for season in eplist:
            try:
                snum = int(season.attrib['no'])
            except KeyError:
                pass # TODO: adding handeling for specials and movies
                # bsp: http://www.tvrage.com/feeds/episode_list.php?sid=3519
            else:
                self.episodes[snum] = Season()
                for episode in season:
                    epnum = int(episode.find('seasonnum').text)
                    self.episodes[snum][epnum] = Episode(
                        self.name,
                        snum,
                        episode.find('airdate').text,
                        episode.find('title').text,
                        episode.find('link').text,
                        epnum,
                        episode.find('prodnum').text,
                    )
                if snum > 0:
                    self.seasons += 1
        
        self.episodes[self.seasons].is_current = True


    @property
    def pilot(self):
        """returns the pilot/1st episode"""
        return self.episodes[1][1]

    @property
    def current_season(self):
        """returns the season currently running on tv"""
        if not self.ended: # still running
            return self.episodes[self.seasons]
        else:
            raise ShowHasEnded, self.name

    @property
    def next_episode(self):
        """returns the next upcomming episode"""
        try:
            return self.upcomming_episodes.next()
        except StopIteration:
            raise NoNewEpisodesAnnounced, self.name

    @property
    def upcomming_episodes(self):
        """returns all upcomming episodes that have been annouced yet"""
        today = date.today()
        for e in self.current_season.values():
            if (e.airdate != None) and (e.airdate >= today):
                yield e

    @property
    def latest_episode(self):
        """returns the latest episode that has aired already"""
        today = date.today()
        eps = self.season(self.seasons).values()
        eps.reverse()
        for e in eps:
            if (e.airdate != None) and (e.airdate < today):
                return e

    def season(self, n):
        """returns the nth season as dict of episodes"""
        return self.episodes[n]    
        
