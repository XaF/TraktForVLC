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

from __future__ import print_function
import contextlib
import distutils.spawn
import glob
import logging
import os
import platform
import sys

if platform.system() != 'Windows':
    import pwd

LOGGER = logging.getLogger(__name__)


##############################################################################
# Get a resource from the same directory as the helper, or from the binary
# if we are currently in the binary.
def get_resource_path(relative_path):
    return os.path.join(
        getattr(
            sys, '_MEIPASS',
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        ),
        relative_path
    )


##############################################################################
# Context manager that allows to temporarily redirect what is written to
# stdout and stderr to another stream received as parameter
@contextlib.contextmanager
def redirectstd(output):
    old_stdout, sys.stdout = sys.stdout, output
    old_stderr, sys.stderr = sys.stderr, output
    try:
        yield output
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


##############################################################################
# Class representing a command that will be available through the helper
class Command(object):
    command = None
    description = None

    def add_arguments(self, parser):
        pass

    def check_arguments(self, parser, args):
        pass

    def run(self, *args, **kwargs):
        pass


##############################################################################
# Return the path to the VLC executable
def get_vlc():
    if platform.system() == 'Windows':
        environment = ['ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432']
        program_files = set(
            os.environ[e] for e in environment if e in os.environ)
        for p in program_files:
            fpath = os.path.join(p, 'VideoLAN', 'VLC', 'vlc.exe')
            if os.path.isfile(fpath):
                return fpath
    elif platform.system() == 'Darwin':
        fpath = '/Applications/VLC.app/Contents/MacOS/VLC'
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            return fpath
    return distutils.spawn.find_executable('vlc')


##############################################################################
# To run a subprocess as user
def run_as_user():
    if platform.system() == 'Windows' or not os.getenv('SUDO_USER'):
        LOGGER.debug('No need to change the user')
        return {}

    pw = pwd.getpwnam(os.getenv('SUDO_USER'))
    LOGGER.debug('Providing the parameters to run the command as {}'.format(
        pw.pw_name))

    env = os.environ.copy()
    for k in env.keys():
        if k.startswith('SUDO_'):
            del env[k]

    env['HOME'] = pw.pw_dir
    env['LOGNAME'] = env['USER'] = env['USERNAME'] = pw.pw_name

    def demote():
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)

    return {
        'preexec_fn': demote,
        'env': env,
    }


##############################################################################
# To determine the paths to the LUA and Config directories of VLC
def get_os_config(system=None, config=None, lua=None):
    def itmerge(*iterators):
        for iterator in iterators:
            for value in iterator:
                yield value

    if not config or not lua:
        opsys = platform.system()
        if opsys in ['Linux', 'Darwin']:
            if os.getenv('SUDO_USER'):
                home = pwd.getpwnam(os.getenv('SUDO_USER')).pw_dir
            else:
                home = os.path.expanduser('~')
        if opsys == 'Linux':
            if not config:
                config = os.path.join(home, '.config', 'vlc')
            if not lua:
                if system:
                    lua = next(itmerge(
                        glob.iglob('/usr/lib/*/vlc/lua'),
                        glob.iglob('/usr/lib/vlc/lua'),
                    ))
                else:
                    lua = os.path.join(home, '.local', 'share', 'vlc', 'lua')
        elif opsys == 'Darwin':
            if not config:
                config = os.path.join(home, 'Library', 'Preferences',
                                      'org.videolan.vlc')
            if not lua:
                if system:
                    lua = '/Applications/VLC.app/Contents/MacOS/share/lua'
                else:
                    lua = os.path.join(home, 'Library', 'Application Support',
                                       'org.videolan.vlc', 'lua')
        elif opsys == 'Windows':
            if not config:
                config = os.path.join(os.getenv('APPDATA'), 'vlc')
            if not lua:
                if system:
                    lua = os.path.join(
                        os.getenv('PROGRAMFILES'), 'VideoLAN', 'VLC', 'lua')
                else:
                    lua = os.path.join(config, 'lua')

    if config and lua:
        return {
            'config': config,
            'lua': lua,
        }

    raise RuntimeError('Unsupported operating system: {}'.format(system))


##############################################################################
# To prompt the user for a yes-no answer
def ask_yes_no(prompt):
    try:
        while 'the feeble-minded user has to provide an answer':
            reply = str(raw_input(
                '{} [y/n] '.format(prompt))).lower().strip()
            if reply in ['y', 'yes', '1']:
                return True
            elif reply in ['n', 'no', '0']:
                return False
    except (KeyboardInterrupt, EOFError):
        print('Installation aborted by signal.')
        return
