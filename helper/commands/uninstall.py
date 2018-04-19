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
from concurrent.futures import TimeoutError
import io
import logging
import os
import platform
import subprocess
import sys
import time

from helper.commands.install import (
    CommandInstallUpdateDelete,
)
from helper.commands.service import (
    run_windows_service,
)
from helper.utils import (
    ask_yes_no,
    get_os_config,
    get_vlc,
    redirectstd,
    run_as_user,
)
from helper.version import (
    __version__,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# The UNINSTALL command to uninstall TraktForVLC
class CommandUninstall(CommandInstallUpdateDelete):
    command = 'uninstall'
    description = 'To install TraktForVLC'

    def add_arguments(self, parser):
        super(CommandUninstall, self).add_arguments(parser)

        if platform.system() == 'Windows':
            parser.add_argument(
                '--max-wait',
                type=int,
                help='Maximum time to wait for files to be deleted on Windows',
            )

    def run(self, dry_run, yes, system, service, service_host, service_port,
            vlc_bin, vlc_config, vlc_lua, vlc_verbose, max_wait=None):
        if service and platform.system() != 'Windows':
            LOGGER.error('The service mode is not supported yet for {}'.format(
                platform.system()))

        os_config = get_os_config(system or service, vlc_config, vlc_lua)

        # Try to find the VLC executable if it has not been passed as parameter
        if not vlc_bin:
            LOGGER.info('Searching for VLC binary...')
            vlc_bin = get_vlc()
        # If we still did not find it, cancel the installation as we will
        # not be able to complete it
        if not vlc_bin:
            raise RuntimeError(
                'VLC executable not found: use the --vlc parameter '
                'to specify VLC location')
        else:
            LOGGER.info('VLC binary: {}'.format(vlc_bin))

        # Compute the path to the directories we need to use after
        lua = os_config['lua']
        lua_intf = os.path.join(lua, 'intf')

        # Search for the files to remove
        to_remove = []

        search_files = {
            # The helper
            lua: [
                'trakt_helper',
                'trakt_helper.exe',
                'trakt_helper.py',
            ],
            # The Lua interfaces
            lua_intf: [
                'trakt.lua',
                'trakt.luac',
            ],
        }

        for path, files in sorted(search_files.items()):
            if not files:
                continue

            LOGGER.info('Searching for the files to remove in {}'.format(path))
            for f in files:
                fp = os.path.join(path, f)
                if os.path.isfile(fp):
                    to_remove.append(fp)

        # Show to the user what's going to be done
        if not to_remove:
            print('No files to be removed. Will still try to disable '
                  'trakt\'s lua interface.')
            me = None
        else:
            to_remove.sort()
            if getattr(sys, 'frozen', False):
                me = sys.executable
            else:
                me = os.path.realpath(__file__)

            # If the executable is in the list of files to remove, push it to
            # the end, we only want it to be removed if we succeeded in
            # removing everything else
            if me in to_remove:
                to_remove.remove(me)
                to_remove.append(me)

            print('Will remove the following files:')
            for f in to_remove:
                if f == me:
                    print(' - {} (this is me!!)'.format(f))
                else:
                    print(' - {}'.format(f))
            print('And try to disable trakt\'s lua interface.')

        # Prompt before continuing, except if --yes was used
        if not yes:
            yes_no = ask_yes_no('Proceed with uninstallation ?')
            if not yes_no:
                print('Uninstallation aborted by {}.'.format(
                    'signal' if yes_no is None else 'user'))
                return

        # We then need to start VLC with the trakt interface enabled, and
        # pass the autostart=disable parameter so we'll disable the interface
        # from VLC
        LOGGER.info('Setting up VLC not to use trakt\'s interface')
        configured = False
        if not dry_run:
            command = [
                vlc_bin,
                '-I', 'luaintf',
                '--lua-intf', 'trakt',
                '--lua-config', 'trakt={autostart="disable"}',
            ]
            if vlc_verbose:
                command.extend(['--verbose', str(vlc_verbose)])
            LOGGER.debug('Running command: {}'.format(
                subprocess.list2cmdline(command)))
            disable = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                **run_as_user()
            )
            output = []
            msg_ok = ('[trakt] lua interface: VLC is configured '
                      'not to use TraktForVLC')
            msg_not_exists = ('[trakt] lua interface error: Couldn\'t find '
                              'lua interface script "trakt".')
            for line in iter(disable.stdout.readline, b''):
                line = line.strip()
                output.append(line)
                LOGGER.debug(line)
                if line.endswith(msg_ok) or line.endswith(msg_not_exists):
                    configured = True
            disable.stdout.close()

            if disable.wait() != 0 and not configured:
                LOGGER.error('Unable to disable VLC '
                             'lua interface:\n{}'.format('\n'.join(output)))
                return -1
        else:
            configured = True

        if configured:
            LOGGER.info('VLC configured')
        else:
            LOGGER.error('Error while configuring VLC')
            return -1

        # We can then stop and remove the service
        if service:
            service_exists = True

            LOGGER.info('Stopping TraktForVLC service')
            if not dry_run:
                output = io.BytesIO()
                with redirectstd(output):
                    run_windows_service(action='stop')

                service_stop_lines = output.getvalue().splitlines()
                if service_stop_lines[-1] == 'Stopping service TraktForVLC':
                    LOGGER.info('Service stopped')
                elif service_stop_lines[-1].endswith('(1062)'):
                    LOGGER.info('Service already stopped')
                elif service_stop_lines[-1].endswith('(1060)'):
                    LOGGER.info('Service does not seem to be installed')
                    service_exists = False
                else:
                    for l in service_stop_lines:
                        LOGGER.error(l)
                    return -1

            if service_exists:
                LOGGER.info('Removing TraktForVLC service')
                if not dry_run:
                    output = io.BytesIO()
                    with redirectstd(output):
                        run_windows_service(action='remove')

                    service_remove_lines = output.getvalue().splitlines()
                    if service_remove_lines[-1] == 'Service removed':
                        LOGGER.info(service_remove_lines[-1])
                    elif service_remove_lines[-1].endswith('(1060)'):
                        LOGGER.info('Service does not seem to be installed')
                        service_exists = False
                    else:
                        for l in service_remove_lines:
                            LOGGER.error(l)

            if not dry_run:
                start = time.time()
                while service_exists:
                    if max_wait is not None and start + max_wait > time.time():
                        LOGGER.error(
                            'Reached maximum wait time and the service '
                            'is still not removed; Aborting.')
                        return -1

                    LOGGER.info('Checking service...')
                    output = io.BytesIO()
                    with redirectstd(output):
                        run_windows_service(action='remove')

                    service_remove_lines = output.getvalue().splitlines()
                    if service_remove_lines[-1].endswith('(1060)'):
                        LOGGER.info('Service is entirely removed')
                        service_exists = False
                    else:
                        # Wait 5 seconds, then check again
                        time.sleep(5)

        # If there is files to remove, wait to get the right to remove them...
        # this is only needed for Windows
        if platform.system() == 'Windows':
            LOGGER.info('Checking that the files can be deleted...')
            open_files = []
            start = time.time()
            interrupt = False
            try:
                for fname in to_remove:
                    if fname == me:
                        # Ignore if the file is ourselves, this will be managed
                        # differently, but for other files it is important
                        # to check
                        continue

                    f = None
                    while not f:
                        if max_wait is not None and \
                                start + max_wait > time.time():
                            raise TimeoutError

                        if not os.path.isfile(fname):
                            break

                        try:
                            f = open(fname, 'a')
                            open_files.append(f)
                        except Exception as e:
                            if isinstance(e, KeyboardInterrupt):
                                raise
                            LOGGER.debug(e)
                            LOGGER.debug(
                                'Waiting 5 seconds before retrying...')
                            time.sleep(5)
            except KeyboardInterrupt:
                LOGGER.info('Aborting.')
                interrupt = None
            except TimeoutError:
                LOGGER.info('Timed out. Aborting.')
                interrupt = -1
            finally:
                # Close the files we were able to open
                while open_files:
                    open_files.pop().close()

            if interrupt is not False:
                return interrupt

        # Then we remove the files
        for f in to_remove:
            LOGGER.info('Removing {}'.format(f))
            if not dry_run:
                try:
                    os.remove(f)
                except WindowsError:
                    if f != me:
                        # If we got a windows error while trying to remove one
                        # of the files that is not the currently running file,
                        # raise the error
                        raise

                    LOGGER.info('Cannot remove myself directly, launching a '
                                'subprocess to do so... Bye bye ;(')
                    command = subprocess.list2cmdline([
                        # Run that as a shell command
                        'CMD', '/C',
                        # Wait two seconds - So the file descriptor is freed
                        'PING', '127.0.0.1', '-n', '2', '>NUL', '&',
                        # Delete the file
                        'DEL', '/F', '/S', '/Q', f,
                    ])
                    LOGGER.debug('Running command: {}'.format(command))
                    subprocess.Popen(command)
                    return

        LOGGER.info('TraktForVLC{} is now uninstalled. :('.format(
            ' {}'.format(__version__) if me in to_remove else ''))
