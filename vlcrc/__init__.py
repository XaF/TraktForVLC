#!/usr/bin/env python
# encoding: utf-8
#
# TraktForVLC, to link VLC watching to trakt.tv updating
#
# Copyright (C) 2012        Chris Maclellan <chrismaclellan@gmail.com>
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

# Imports
import logging
import re
import telnetlib
from time import sleep


class VLCBadReturn(Exception):
    def __init__(self, msg):
        super(VLCBadReturn, self).__init__(msg)


class VLCRemote(object):

    def __init__(self, hostname, port, timeout=3):
        self.cnx = telnetlib.Telnet(hostname, port)
        self.log = logging.getLogger('VLCRemote')
        self.timeout = timeout

        # False if we're using OLDRC, True if we're using RC
        self.vlcrc = False

        # Open connexion
        self.cnx.open(hostname, port)

        # We want to be sure we have received the greetings
        # FIXME: if there's another cleaner way!
        sleep(0.00001)

        # Verify if there is any welcome message
        cached = self.cnx.read_very_eager()

        # If there is, we are most probably using the 'rc' module,
        # and not 'oldrc'. We can thus identify the version of VLC
        # being used
        self.vlcversion = None
        if cached != '':
            version = re.findall(
                '((?:[0-9]+\.){2}[0-9]+(?:-[a-zA-Z0-9]+)?)', cached)
            if version:
                self.vlcrc = True
                self.vlcversion = version[0]
                self.log.debug('VLC version is %s' % self.vlcversion)

    def _command(self, cmd, return_re=None, raw=False, args=None):

        # Clean out anything waiting before starting the command
        cached = self.cnx.read_very_eager()
        if cached != '':
            self.log.debug('cleaning cache')
            self.log.debug('<- Received: %s' % cached.strip())

        # FIXME - Ugly
        cmd_str = '%s' % cmd
        if args is not None:
            cmd_str += ' '
            cmd_str += ' '.join(args)
        cmd_str += '\n'

        self.log.debug('-> Sending: %s' % cmd_str.strip())
        self.cnx.write(cmd_str)

        if not raw:
            cmd_end = '%s: returned ' % cmd
            cmd_ret = self.cnx.read_until(cmd_end, self.timeout)
            if not cmd_ret.endswith(cmd_end):
                err_str = 'Sent: %s\n' % cmd_str
                err_str += 'Expected: %s\n' % cmd_end
                err_str += 'Got: %s' % cmd_ret
                self.log.warn(err_str)
                raise VLCBadReturn(err_str)

            good = '0 (no error)\r\n'
            cmd_fin = self.cnx.read_until('\r\n', 3)
            cmd_ret += cmd_fin
            if cmd_fin != good:
                err_str = 'Sent: %s\n' % cmd_str
                err_str += 'Expected: %s%s\n' % (cmd_end, good)
                err_str += 'Got: %s' % (cmd_ret)
                self.log.warn(err_str)
                raise VLCBadReturn(err_str)
            self.log.debug('<- Received: %s' % cmd_ret.strip())
        else:
            index, match, cmd_ret = self.cnx.expect([return_re], self.timeout)
            if match is None:
                raise VLCBadReturn(
                    'Pattern: %s\nReceived: %s' % (return_re.pattern, cmd_ret))
            self.log.debug('<- Received: %s' % cmd_ret.strip())
            return match

        if return_re is None:
            return True

        match = return_re.search(''.join((cmd_ret, cmd_fin)))
        return match

    def get_filename(self):
        fn_re = re.compile(
            'input: (?P<path>(?P<ptcl>[a-z]*)://(?P<fn>.+?)) \)',
            re.IGNORECASE | re.MULTILINE)
        match = self._command('status', fn_re, raw=True)
        fn = match.groupdict()['path']
        return fn

    def restart(self):
        self._command('seek', args=(0,))

    def skip(self, duration=60):
        time_re = re.compile('(?P<time>\d+)\r\n')
        ret_match = self._command('get_time', time_re, raw=True)
        time = ret_match.groupdict()['time']
        gt = str(int(time) + duration)
        self._command('seek', args=(gt,))

    def next(self):
        self._command('next')

    def get_title(self):
        fn_re = re.compile(
            '^(?!status change:)>?\s*(?P<title>[^\r\n]+?)\r?\n',
            re.IGNORECASE | re.MULTILINE)
        title = self._command('get_title', fn_re, raw=True)
        title = title.groupdict()['title']
        return title

    def is_playing(self):
        fn_re = re.compile(
            '^(?!status change:)(?P<playing>\d+)\r?\n',
            re.IGNORECASE | re.MULTILINE)
        playing = self._command('is_playing', fn_re, raw=True)
        playing = playing.groupdict()['playing']
        return int(playing)

    def get_info(self):
        fn_re = re.compile(
            '(?P<info>\+----.+\[ end of stream info \])', re.DOTALL)
        info = self._command('info', fn_re, raw=True)
        info = info.groupdict()['info']

        dictinfo = {}
        for match in re.findall(
                "\+----\[ (?P<block>.+?) \](?P<content>.+?)(?=\+----)",
                info, re.DOTALL):
            dictinfo[match[0]] = dict(
                re.findall("([a-zA-Z0-9]*): ([\x20-\x7E]*)", match[1]))

        return dictinfo

    def get_status(self):
        status = self._command('status')
        return status

    def get_length(self):
        fn_re = re.compile(
            '^(?!status change:)(?P<length>\d+)\r?\n',
            re.IGNORECASE | re.MULTILINE)
        length = self._command('get_length', fn_re, raw=True)
        length = length.groupdict()['length']
        return length

    def get_time(self):
        fn_re = re.compile(
            '^(?!status change:)(?P<time>\d+)\r?\n',
            re.IGNORECASE | re.MULTILINE)
        time = self._command('get_time', fn_re, raw=True)
        time = time.groupdict()['time']
        return time

    def close(self):
        self.cnx.close()

if __name__ == "__main__":
    vlc = VLCRemote("localhost", 4222)

    if vlc.vlcversion is not None:
        print "VLC version is %s" % vlc.vlcversion
    else:
        print "VLC version is unknown"

    if vlc.is_playing():
        print "The title of the VLC window is:", vlc.get_title()
        if vlc.vlcrc:
            print "The file currently opened is:", vlc.get_filename()
    else:
        print "Nothing is currently playing"

    vlc.close()
