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
import json
import logging
import os
from pkg_resources import parse_version
import platform
import re
import requests
import stat
import subprocess
import tempfile

from helper.commands.install import (
    CommandInstallUpdateDelete,
)
from helper.utils import (
    ask_yes_no,
)
from helper.version import (
    __version__,
    __release_type__,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# The UPDATE command to check if there are new versions available
class CommandUpdate(CommandInstallUpdateDelete):
    command = 'update'
    description = ('To check and update if there are new versions of '
                   'TraktForVLC available')

    def add_arguments(self, parser):
        super(CommandUpdate, self).add_arguments(parser)

        version_update = parser.add_mutually_exclusive_group()
        version_update.add_argument(
            '-t', '--release-type',
            help='The type of updates to look for; any type will also allow '
                 'for a more stable type (i.e. beta also allows for rc and '
                 'stable) as long as the update is more recent',
            type=str.lower,
            choices=[
                'latest',
                'alpha',
                'beta',
                'rc',
                'stable',
            ],
            default='stable',
        )
        version_update.add_argument(
            '--version',
            help='The version to look for and install; will be used only to '
                 'check for the tag corresponding to that version.',
        )
        version_update.add_argument(
            '--file',
            dest='filepath',
            help='The file to use for install; no check will be performed, '
                 'and the installation step will be launched directly with '
                 'that file.',
        )
        action_update = parser.add_mutually_exclusive_group()
        action_update.add_argument(
            '--download',
            dest='action',
            action='store_const',
            const='download',
            help='If an update is found, it will only be downloaded',
        )
        action_update.add_argument(
            '--install',
            dest='action',
            action='store_const',
            const='install',
            help='If an update is found, it will be downloaded and the '
                 'install process will automatically be started',
        )
        parser.add_argument(
            '--ignore-dev',
            action='store_true',
            help='Run the update process even if the current version is the '
                 'development one',
        )
        output_update = parser.add_mutually_exclusive_group()
        output_update.add_argument(
            '--discard-install-output',
            dest='install_output',
            action='store_const',
            const=False,
            help='If the --install option is used, the output generated from '
                 'the installation will be silenced',
        )
        output_update.add_argument(
            '--install-output',
            help='If the --install option is used, will put the output '
                 'generated from the installation process in the file '
                 'specified here',
        )

    def run(self, dry_run, yes, system, service, service_host, service_port,
            vlc_bin, vlc_config, vlc_lua, vlc_verbose, release_type, version,
            filepath, action, ignore_dev, install_output):
        if service and platform.system() != 'Windows':
            LOGGER.error('The service mode is not supported yet for {}'.format(
                platform.system()))

        if not ignore_dev and __version__ == '0.0.0a0.dev0':
            LOGGER.debug('This is a development version; update is '
                         'not available')
            print('{}')
            return

        if filepath or version:
            release_type = None

        ret = {}

        if release_type or version:
            if not __release_type__:
                print('{}')
                return

            if release_type:
                resp = requests.get(
                    'https://api.github.com/repos/XaF/TraktForVLC/releases')

                if not resp.ok:
                    raise RuntimeError('Unable to get the releases from '
                                       'GitHub (return code {})'.format(
                                           resp.status_code))

                # Determine what release types we will accept during the check
                releases_level = {
                    'latest': 0,
                    'alpha': 1, 'a': 1,
                    'beta': 2, 'b': 2,
                    'rc': 3,
                    'stable': 4,
                }
                search_level = releases_level[release_type]

            # Determine the format of the asset we will check to download
            asset_suffix = __release_type__
            if platform.system() == 'Windows':
                asset_suffix = '{}.exe'.format(asset_suffix)
            asset_re = re.compile('^TraktForVLC_(?P<version>.*)_{}$'.format(
                re.escape(asset_suffix)))

            # Then try and go through the available releases on GitHub to check
            # for the most recent one fitting our parameters
            found_release = None
            for release in resp.json():
                if release_type:
                    release_level = None
                    if release['tag_name'] == 'latest':
                        # This is the latest release
                        release_level = releases_level['latest']
                    else:
                        parsed = parse_version(release['tag_name'])
                        if isinstance(parsed._version, str):
                            continue

                        # Check if it is a prerelease or an actual release
                        if parsed.is_prerelease or release['prerelease']:
                            if not release['prerelease']:
                                LOGGER.debug(
                                    'Release {} considered as prerelease '
                                    'by parse_version but not on '
                                    'GitHub!'.format(release['tag_name']))
                            elif not parsed.is_prerelease:
                                LOGGER.debug(
                                    'Release {} considered as prerelease '
                                    'on GitHub but not by parse_version, '
                                    'ignoring it.'.format(release['tag_name']))
                                continue

                            # Determine the type of prerelease
                            release_level = releases_level.get(
                                parsed._version.pre[0])
                        else:
                            # This is a stable release
                            release_level = releases_level['stable']

                    # If this release does not match our needs, go to next loop
                    if release_level is None or release_level < search_level:
                        continue
                elif version != release['tag_name']:
                    continue

                # Check in the assets that we have what we need
                for asset in release['assets']:
                    m = asset_re.search(asset['name'])
                    if not m:
                        continue

                    version = release['tag_name']
                    if version == 'latest':
                        version = m.group('version')
                        # We might have the commit id, the pr number or a dirty
                        # flag in the version, this needs to be in the 'local'
                        # part of the version number, but GitHub replaces '+'
                        # signs by a dot in the assert names, we thus need to
                        # replace it back
                        version = re.sub(
                            '(\.(dirty|pr[0-9]|g[a-z0-9]+)){1,3}$',
                            '+\g<1>', version)
                        version = version.replace('+.', '+')

                    found_release = {
                        'version': version,
                        'asset_name': asset['name'],
                        'asset_url': asset['browser_download_url'],
                    }
                    break

                # If we found a release, stop now
                if found_release:
                    break

            if found_release:
                # We found a release, but we need to check that its version is
                # greater than ours; if it's not the case, it means that we are
                # at the most recent version currently.
                current_v = parse_version(__version__)
                release_v = parse_version(found_release['version'])
                if current_v >= release_v:
                    found_release = None

            if not found_release:
                # No release found, we can just stop now, there is no update
                LOGGER.debug('No release found')
                print('{}')
                return

            # We found an update
            ret['version'] = found_release['version']

            # If we are not going to download nor install, stop there
            if action is None:
                print(json.dumps(ret, sort_keys=True,
                                 indent=4, separators=(',', ': ')))
                return

            if not yes:
                yes_no = ask_yes_no('Download file {} ?'.format(
                    found_release['asset_name']))
                if not yes_no:
                    print('Installation aborted by {}.'.format(
                        'signal' if yes_no is None else 'user'))
                    return

            filepath = os.path.join(tempfile.gettempdir(),
                                    found_release['asset_name'])

            resp = requests.get(found_release['asset_url'])
            if not resp.ok:
                raise RuntimeError('Error retrieving the asset: {}'.format(
                    resp.status_code))

            with open(filepath, 'wb') as fout:
                fout.write(resp.content)

            if platform.system() != 'Windows':
                LOGGER.info('Setting permissions of {} to 755'.format(
                    filepath))
                os.chmod(filepath,
                         stat.S_IRWXU |
                         stat.S_IRGRP | stat.S_IXGRP |
                         stat.S_IROTH | stat.S_IXOTH)

            ret['downloaded'] = True

        # If we are not going to install, stop there
        if action != 'install':
            print(json.dumps(ret, sort_keys=True,
                             indent=4, separators=(',', ': ')))
            return

        if not yes:
            yes_no = ask_yes_no('Install {} ?'.format(
                os.path.basename(filepath)))
            if not yes_no:
                print('Installation aborted by {}.'.format(
                    'signal' if yes_no is None else 'user'))
                return

        # We just launch the installation. If it can be done right now, it
        # will be, if it cannot, it will wait, that is the job of the
        # installer as of now!
        command = [
            filepath,
            '--loglevel', logging.getLevelName(LOGGER.getEffectiveLevel()),
        ]
        if install_output:
            command.extend(['--logfile', install_output])

        command.extend(['install', '--yes'])
        if vlc_bin:
            command.extend(['--vlc', vlc_bin])
        if vlc_lua:
            command.extend(['--vlc-lua-directory', vlc_lua])
        if vlc_config:
            command.extend(['--vlc-config-directory', vlc_config])
        if vlc_verbose:
            command.extend(['--vlc-verbose', str(vlc_verbose)])
        if system:
            command.append('--system')
        if service:
            command.extend([
                '--service',
                '--service-host', service_host,
                '--service-port', str(service_port),
            ])
        if dry_run:
            command.append('--dry-run')

        LOGGER.debug('Running command: {}'.format(
            subprocess.list2cmdline(command)))

        output = {}
        if install_output is not None:
            output['stdout'] = subprocess.PIPE
            output['stderr'] = subprocess.PIPE
        else:
            output['stderr'] = subprocess.STDOUT
        output['stdin'] = subprocess.PIPE

        subprocess.Popen(
            command,
            **output
        )

        ret['installing'] = True
        print(json.dumps(ret, sort_keys=True,
                         indent=4, separators=(',', ': ')))
