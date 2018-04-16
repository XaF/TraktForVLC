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
import logging
import subprocess

from helper.utils import (
    Command,
    get_vlc,
    run_as_user,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# The RUNVLC command to run VLC in a subprocess and get its output
class CommandRunVLC(Command):
    command = 'runvlc'
    description = ('To run VLC in a subprocess and get its output '
                   'even from Windows')

    def add_arguments(self, parser):
        parser.add_argument(
            'parameters',
            nargs='*',
            default=[],
            help='The command line parameters to pass to VLC',
        )
        parser.add_argument(
            '--vlc',
            dest='vlc_bin',
            help='To specify manually where the VLC executable is',
        )

    def run(self, vlc_bin, parameters):
        # Try to find the VLC executable if it has not been passed as
        # parameter
        if not vlc_bin:
            LOGGER.info('Searching for VLC binary...')
            vlc_bin = get_vlc()
        # If we still did not find it, cancel the installation as we will
        # not be able to complete it
        if not vlc_bin:
            raise RuntimeError(
                'VLC executable not found: use the --vlc parameter '
                'to specify VLC location')

        # Preparing the command
        command = [
            vlc_bin,
        ] + parameters

        LOGGER.info('Running command: {}'.format(
            subprocess.list2cmdline(command)))

        run = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            **run_as_user()
        )
        try:
            for line in iter(run.stdout.readline, b''):
                line = line.strip()
                print(line)
        except KeyboardInterrupt:
            run.kill()
        finally:
            run.stdout.close()

        return run.wait()
