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
import platform
import subprocess

from helper.utils import (
    Command,
    get_resource_path,
    get_vlc,
    run_as_user,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# The INIT_TRAKT_AUTH command to initialize Trakt.tv authentication
class CommandInitTraktAuth(Command):
    command = 'init_trakt_auth'
    description = 'Initialize TraktForVLC authentication with trakt.tv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vlc',
            dest='vlc_bin',
            help='To specify manually where the VLC executable is',
        )

    def run(self, vlc_bin):
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
            '--lua-config',
            'trakt={init_auth=1}',
        ]
        if platform.system() == 'Windows':
            command.extend([
                '--osd',
                '--repeat',
                get_resource_path('vlc-logo-1s.mp4'),
            ])
            print('A VLC window will open, please follow the instructions')
            print('that will appear in that window: go to the provided link')
            print('and enter the given code, then wait patiently as')
            print('TraktForVLC is configured to get access to your account.')
        else:
            command.extend([
                '--intf', 'cli',
            ])

        LOGGER.debug('Running command: {}'.format(
            subprocess.list2cmdline(command)))

        run = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            **run_as_user()
        )
        try:
            success = None
            grabbing = None
            for line in iter(run.stdout.readline, b''):
                line = line.strip()
                LOGGER.debug(line)

                # If we read a line that encloses messages for the device code
                # process, process it
                if line == '############################':
                    if grabbing is None:
                        grabbing = []
                    else:
                        if grabbing[0] == \
                                'TraktForVLC is not setup with Trakt.tv yet!':
                            grabbing = grabbing[2:]
                        elif grabbing[0] == \
                                ('TraktForVLC setup failed; Restart VLC '
                                 'to try again'):
                            success = False
                        elif grabbing[0] == \
                                'TraktForVLC is now setup with Trakt.tv!':
                            success = True

                        # Skip the print on Windows, as we are using the OSD
                        # to show the code to enter
                        if platform.system() != 'Windows':
                            print('\n'.join(grabbing))

                        grabbing = None
                elif grabbing is not None:
                    # If we are currently grabbing lines, grab this one
                    grabbing.append(line)
        except KeyboardInterrupt:
            run.kill()
        finally:
            run.stdout.close()

        if platform.system() == 'Windows':
            if success:
                print('Yey! TraktForVLC is now configured with trakt.tv! :)')
            elif success is False:
                print('Meh! TraktForVLC setup with trakt.tv failed! :(')
            else:
                print('Well, this is embarrassing... something happened, and '
                      'it does not seem to have worked! :|')

        return run.wait()
