#!/usr/bin/env python

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

import unittest

from datetime import date
from api import Show
from exceptionsTvRage import (ShowHasEnded, FinaleMayNotBeAnnouncedYet,
                               ShowNotFound)


class ShowTest(unittest.TestCase):

    show = Show('Person of Interest')
    dead_show = Show('house')

    def test_show_still_running(self):
        assert self.show.ended == 0

    def test_get_season(self):
        season = self.show.season(1)
        assert len(season) == 23
        assert season.episode(1).title == 'Pilot'

    def test_get_next_episode_from_dead_show(self):
        try:
            self.dead_show.next_episode
        except Exception, e:
            assert isinstance(e, ShowHasEnded)

    # this test may break during off seasons...
    # def testGetNextEpisode(self):
    #     today = date.today()
    #     airdate = self.show.next_episode.airdate
    #     assert airdate >= today

    def test_get_pilot(self):
        p = self.show.pilot
        assert p.season == 1
        assert p.number == 1
        assert p.title == 'Pilot'

    def test_get_current_season_from_dead_show(self):
        try:
            self.dead_show.current_season
        except Exception, e:
            assert isinstance(e, ShowHasEnded)

    # this test may break when new season listings are posted
    #def testGetCurrentSeason(self):
    #    assert self.show.current_season.premiere.season == 6

    def test_get_upcoming_eps(self):
        today = date.today()
        for ep in self.show.upcoming_episodes:
            airdate = ep.airdate
            assert airdate >= today

    def test_get_latest_ep(self):
        today = date.today()
        ep = Show('FlashForward').latest_episode
        assert ep.airdate <= today
        assert ep.title == 'Future Shock'

    def test_non_existant_show_raises_proper_exception(self):
        try:
            Show('yaddayadda')
        except Exception, e:
            assert isinstance(e, ShowNotFound)
            assert e.value == 'yaddayadda'

    def test_synopsis(self):
        assert self.dead_show.synopsis.startswith(
            u"As an infectious disease specialist,Dr. Gregory House"
            "(Hugh Laurie) is a brilliant diagnostician who loves the "
            "challenges of the medical puzzles he must solve in order to save"
            " lives.")

    def test_show_with_missing_seasons_doesnt_mess_up_season_count(self):
        # Seasons 39 - 47 are missing
        s = Show(u'House Hunters')
        assert s.seasons >= 48


class SeasonTest(unittest.TestCase):

    season = Show('house').season(3)

    def test_get_episode(self):
        assert self.season.episode(1).number == 1
        assert self.season.episode(6).number == 6
        assert self.season.episode(24).number == 24

    def test_get_premiere(self):
        ep = self.season.premiere
        assert ep.number == 1

    def test_get_finale(self):
        assert self.season.finale.number == 24
        # and now the execption:
        # NOTE: this test may break, when the season finale actually gets
        # announced
        try:
            Show('Doctor Who 2005').current_season.finale
        except Exception, e:
            assert isinstance(e, FinaleMayNotBeAnnouncedYet)


class EpisodeTest(unittest.TestCase):

    ep = Show('house').season(3).episode(6)

    def test_show(self):
        assert self.ep.show == 'House'

    def test_season(self):
        assert self.ep.season == 3

    def test_num(self):
        assert self.ep.number == 6

    def test_airdate(self):
        assert self.ep.airdate == date(2006, 11, 07)

    def test_title(self):
        assert self.ep.title == 'Que Sera Sera'

    def test_link(self):
        assert self.ep.link == \
            'http://www.tvrage.com/House/episodes/461013'

    def test_summary_old(self):
        s = "An immensely overweight man is brought in after he's found at"\
            " home in a coma. Upon regaining consciousness, he demands"\
            " to be released. When Cameron comes up with a way to force"\
            " him to stay, the man insists the find a reason for his"\
            " illness other than his obesity. Meanwhile, Det. Tritter"\
            " arrests House, searches his home, and questions his"\
            " co-workers about his Vicodin usage."
        assert self.ep.summary == s

    def test_summary_new(self):
        ep = Show('chaos').season(1).episode(8)
        s = 'The agents go against orders to capture an arms dealer, but'\
            ' their actions trouble Rick who must decide whether to report'\
            ' their unauthorized activities to the CIA director.'
        assert ep.summary == s

    def test_recap_url(self):
        ep = Show('house').season(1).episode(1)
        s = 'http://www.tvrage.com/House/episodes/84699/recap'
        assert ep.recap_url == s

    def test_id(self):
        assert self.ep.id == '461013'

    def test_recap(self):
        ep = Show('house').season(1).episode(1)
        s = 'House explains that when someone eats poorly prepared pork,'\
            ' tapeworms lodge in the bowels.'
        assert s in ep.recap
        
    def test_recap_negativ(self):
        ep = Show('house').season(3).episode(6)
        assert ep.recap == 'No recap available'

if __name__ == '__main__':
    unittest.main()
