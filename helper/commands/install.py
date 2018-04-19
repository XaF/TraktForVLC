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
import io
import json
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys

from helper.commands.init_trakt_auth import (
    CommandInitTraktAuth,
)
from helper.commands.service import (
    run_windows_service,
)
from helper.parser import (
    ActionYesNo,
)
from helper.utils import (
    ask_yes_no,
    Command,
    get_os_config,
    get_resource_path,
    get_vlc,
    redirectstd,
    run_as_user,
)
from helper.version import (
    __version__,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# Command class that allows to set the common arguments for the INSTALL,
# UPDATE and UNINSTALL commands
class CommandInstallUpdateDelete(Command):
    def add_arguments(self, parser):
        parser.add_argument(
            '--system',
            help='Use system directories instead of per-user',
            action='store_true',
        )
        parser.add_argument(
            '--service',
            help='Install TraktForVLC as a service (only available - and '
                 'mandatory - on Windows currently)',
            action=ActionYesNo,
            default=(platform.system() == 'Windows'),
        )
        parser.add_argument(
            '--service-host',
            help='Host to be used by the service to bind to '
                 '[default: 127.0.0.1]',
            default='localhost',
        )
        parser.add_argument(
            '--service-port',
            type=int,
            help='Port to be used by the service to bind to '
                 '[default: 1984]',
            default=1984,
        )
        parser.add_argument(
            '-y', '--yes',
            help='Do not prompt, approve all changes automatically.',
            action='store_true',
        )
        parser.add_argument(
            '-n', '--dry-run',
            help='Only perform a dry-run for the command (nothing actually '
                 'executed)',
            action='store_true',
        )
        parser.add_argument(
            '--vlc-config-directory',
            dest='vlc_config',
            help='To specify manually where the VLC configuration '
                 'directory is',
        )
        parser.add_argument(
            '--vlc-lua-directory',
            dest='vlc_lua',
            help='To specify manually where the VLC LUA directory is',
        )
        parser.add_argument(
            '--vlc',
            dest='vlc_bin',
            help='To specify manually where the VLC executable is',
        )
        parser.add_argument(
            '--vlc-verbose',
            nargs='?',
            const=1,
            type=int,
            help='To specify the verbose level wanted for VLC logs',
        )


##########################################################################
# The INSTALL command to install TraktForVLC
class CommandInstall(CommandInstallUpdateDelete):
    command = 'install'
    description = 'To install TraktForVLC'

    def add_arguments(self, parser):
        super(CommandInstall, self).add_arguments(parser)

        parser.add_argument(
            '--init-trakt-auth', '--force-init-trakt-auth',
            help='To initialize the authentication with Trakt.tv during the '
                 'installation process; By default, the authentication '
                 'process will be started only if no configuration file '
                 'exists, but the --force-init-trakt-auth option allows to '
                 'execute it in any case.',
            default=True,
            action=ActionYesNo,
        )

    def run(self, dry_run, yes, system, service, service_host, service_port,
            vlc_bin, vlc_config, vlc_lua, vlc_verbose, init_trakt_auth):
        if service and platform.system() != 'Windows':
            LOGGER.error('The service mode is not supported yet for {}'.format(
                platform.system()))

        os_config = get_os_config(system or service, vlc_config, vlc_lua)

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
        else:
            LOGGER.info('VLC binary: {}'.format(vlc_bin))

        # Check that the trakt.luac file can be found
        trakt_lua = get_resource_path('trakt.luac')
        # If it cannot, try to find the trakt.lua file instead
        if not os.path.isfile(trakt_lua):
            trakt_lua = get_resource_path('trakt.lua')
        # If still not found, cancel the installation
        if not os.path.isfile(trakt_lua):
            raise RuntimeError(
                'trakt.luac/trakt.lua file not found, unable to install')

        # Compute the path to the directories we need to use after
        config = os_config['config']
        lua = os_config['lua']
        lua_intf = os.path.join(lua, 'intf')

        # Compute the name of the helper
        if getattr(sys, 'frozen', False):
            trakt_helper = sys.executable
            trakt_helper_dest = 'trakt_helper'
            if platform.system() == 'Windows':
                trakt_helper_dest = '{}.exe'.format(trakt_helper_dest)
        else:
            trakt_helper = os.path.realpath(__file__)
            trakt_helper_dest = os.path.basename(__file__)
        trakt_helper_path = os.path.join(lua, trakt_helper_dest)

        # Show install information to the user, and query for approbation
        # if --yes was not used
        print('\n'.join([
            'TraktForVLC will be installed for the following configuration:',
            ' - OS: {}'.format(platform.system()),
            ' - VLC: {}'.format(vlc_bin),
            ' - VLC configuration: {}'.format(config),
            ' - VLC Lua: {}'.format(lua),
            ' - VLC Lua interface: {}'.format(lua_intf),
            ' - Service ? {}'.format('{}:{}'.format(
                service_host, service_port) if service else 'No'),
        ]))
        if os.path.isfile(trakt_helper_path):
            print('TraktForVLC is currently installed, replacing the current '
                  'installed version will call \'uninstall\' using the '
                  'old binary, and \'install\' with the new one.')
        if not yes:
            yes_no = ask_yes_no('Proceed with installation ?')
            if not yes_no:
                print('Installation aborted by {}.'.format(
                      'signal' if yes_no is None else 'user'))
                return

        if os.path.isfile(trakt_helper_path):
            LOGGER.info('Uninstalling currently installed TraktForVLC')
            command = [
                trakt_helper_path,
                '--logformat', 'UNINSTALL::%(levelname)s::%(message)s',
                '--loglevel', logging.getLevelName(LOGGER.getEffectiveLevel()),
                'uninstall',
                '--vlc', vlc_bin,
                '--vlc-lua-directory', lua,
                '--vlc-config-directory', config,
                '--yes',
            ]
            if vlc_verbose:
                command.extend(['--vlc-verbose', str(vlc_verbose)])
            if system:
                command.append('--system')
            if service:
                command.append('--service')
            if dry_run:
                command.append('--dry-run')

            LOGGER.debug('Running command: {}'.format(
                subprocess.list2cmdline(command)))
            uninstall = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )
            for line in iter(uninstall.stderr.readline, b''):
                LOGGER.info(line.strip())
            uninstall.stderr.close()

            if uninstall.wait() != 0:
                LOGGER.error('Unable to uninstall TraktForVLC')
                return -1

        # Create all needed directories
        needed_dirs = [lua_intf]
        if service:
            needed_dirs.append(config)

        for d in needed_dirs:
            if not os.path.isdir(d):
                LOGGER.info('Creating directory (and parents): {}'.format(d))
                if not dry_run:
                    os.makedirs(d)

        # Copy the trakt helper executable in the Lua directory of VLC
        LOGGER.info('Copying helper ({}) to {}'.format(
            trakt_helper_dest, lua))
        if not dry_run:
            shutil.copy2(trakt_helper, trakt_helper_path)
        if system and platform.system() != 'Windows':
            LOGGER.info('Setting permissions of {} to 755'.format(
                trakt_helper_path))
            if not dry_run:
                os.chmod(trakt_helper_path,
                         stat.S_IRWXU |
                         stat.S_IRGRP | stat.S_IXGRP |
                         stat.S_IROTH | stat.S_IXOTH)

        # Then copy the trakt.lua file in the Lua interface directory of VLC
        LOGGER.info('Copying {} to {}'.format(
            os.path.basename(trakt_lua), lua_intf))
        trakt_lua_path = os.path.join(lua_intf, os.path.basename(trakt_lua))
        if not dry_run:
            shutil.copy2(trakt_lua, lua_intf)
        if system and platform.system() != 'Windows':
            LOGGER.info('Setting permissions of {} to 644'.format(
                trakt_lua_path))
            if not dry_run:
                os.chmod(trakt_lua_path,
                         stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP |
                         stat.S_IROTH)

        # If we are configuring TraktForVLC as a service, we need to
        # install/update the service
        if service:
            LOGGER.info('Setting up TraktForVLC service')
            if not dry_run:
                output = io.BytesIO()
                with redirectstd(output):
                    run_windows_service(action='install',
                                        host=service_host,
                                        port=service_port,
                                        exeName=trakt_helper_path)

                service_install_lines = output.getvalue().splitlines()
                if service_install_lines[-1] in [
                        'Service installed', 'Service updated']:
                    LOGGER.info(service_install_lines[-1])
                else:
                    for l in service_install_lines:
                        LOGGER.error(l)
                    return -1

            LOGGER.info('Starting up TraktForVLC service')
            if not dry_run:
                output = io.BytesIO()
                with redirectstd(output):
                    run_windows_service(action='restart')

                service_restart_lines = output.getvalue().splitlines()
                if service_restart_lines[-1] == \
                        'Restarting service TraktForVLC':
                    LOGGER.info('Service ready')
                else:
                    for l in service_restart_lines:
                        LOGGER.error(l)
                    return -1

        # If we are configuring TraktForVLC as a service, we need to
        # update/create the TraktForVLC configuration file so it will know
        # how to reach the service; if it is not the case, and there is a
        # TraktForVLC configuration file, insure it is set up to use
        # TraktForVLC as a standalone.
        trakt_config = os.path.join(config, 'trakt_config.json')
        data = {}
        data_updated = False
        config_file_exists = False
        if os.path.isfile(trakt_config):
            LOGGER.info('Configuration file exists, reading current values')
            with open(trakt_config, 'r') as f:
                data = json.load(f)
            config_file_exists = True

        if service:
            data_updated = True
            LOGGER.info('Configuring TraktForVLC to use the service')

            if 'helper' not in data:
                data['helper'] = {}
            if 'service' not in data['helper']:
                data['helper']['service'] = {}

            data['helper']['mode'] = 'service'
            data['helper']['service']['host'] = service_host
            data['helper']['service']['port'] = service_port
        elif data.get('helper', {}).get('mode', 'standalone') != 'standalone':
            LOGGER.info(
                'Configuring TraktForVLC helper to be used as standalone')
            data['helper']['mode'] = 'standalone'
            data_updated = True

        # In the future, this might be useful to actually reorganize
        # configuration if there has been any change
        if data and data.get('config_version') != __version__:
            LOGGER.info('Update configuration version')
            data['config_version'] = __version__
            data_updated = True

        if data_updated and not dry_run:
            with open(trakt_config, 'w') as f:
                json.dump(data, f, sort_keys=True,
                          indent=4, separators=(',', ': '))

        # We then need to start VLC with the trakt interface enabled, and
        # pass the autostart=enable parameter so VLC will be setup
        LOGGER.info('Setting up VLC to automatically use trakt\'s interface')
        configured = False
        if not dry_run:
            command = [
                vlc_bin,
                '-I', 'luaintf',
                '--lua-intf', 'trakt',
                '--lua-config', 'trakt={autostart="enable"}',
            ]
            if vlc_verbose:
                command.extend(['--verbose', str(vlc_verbose)])
            LOGGER.debug('Running command: {}'.format(
                subprocess.list2cmdline(command)))
            enable = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                **run_as_user()
            )
            output = []
            for line in iter(enable.stdout.readline, b''):
                line = line.strip()
                output.append(line)
                LOGGER.debug(line)
                if line.endswith('[trakt] lua interface: VLC is configured to '
                                 'automatically use TraktForVLC'):
                    configured = True
            enable.stdout.close()

            if enable.wait() != 0:
                LOGGER.error('Unable to enable VLC '
                             'lua interface:\n{}'.format('\n'.join(output)))
                return -1
        else:
            configured = True

        if configured:
            LOGGER.info('VLC configured')
        else:
            LOGGER.error('Error while configuring VLC')
            return -1

        LOGGER.info('TraktForVLC v{} is now installed. :D'.format(__version__))

        # Initialize the configuration if requested
        if (init_trakt_auth is True and not config_file_exists) or \
                init_trakt_auth == (True, 'force'):
            LOGGER.info('Initializing authentication with Trakt.tv')
            init_trakt = CommandInitTraktAuth()
            init_trakt.run(vlc_bin=vlc_bin, vlc_verbose=vlc_verbose)
