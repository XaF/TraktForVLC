#!/usr/bin/env python
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
import mock
import os
from testfixtures import LogCapture
import unittest
import sys

import context
import utils
import trakt_helper

import helper.utils


class TestHelperUtils(utils._TestCase):

    def _fake_windows_join(self, *args):
        return '\\'.join(args)

    def _fake_unix_join(self, *args):
        return '/'.join(args)

    @mock.patch('os.path.realpath')
    def test_utils_get_resource_path(self, mock_realpath):
        mock_realpath.return_value = '/path/to/my/file.py'

        self.assertEqual(helper.utils.get_resource_path('my_resource'),
                         '/path/to/my_resource')

        mock_realpath.assert_called_once()

    @mock.patch.object(sys, '_MEIPASS', '/mei/path/to',
                       create=True)
    @mock.patch('os.path.realpath')
    def test_utils_get_resource_path(self, mock_realpath):
        self.assertEqual(helper.utils.get_resource_path('my_resource'),
                         '/mei/path/to/my_resource')

    @mock.patch('platform.system')
    @mock.patch('distutils.spawn.find_executable')
    def test_utils_get_vlc_linux(self, mock_find_executable, mock_system):
        mock_system.return_value = 'Linux'
        mock_find_executable.return_value = '/path/to/linux/vlc'

        self.assertEqual(helper.utils.get_vlc(),
                         '/path/to/linux/vlc')

    @mock.patch('os.path.join')
    @mock.patch('os.path.isfile')
    @mock.patch('platform.system')
    @mock.patch('distutils.spawn.find_executable')
    def test_utils_get_vlc_windows(self, mock_find_executable, mock_system,
                                   mock_isfile, mock_join):
        def fake_isfile(path):
            return path == 'C:\\path\\to\\windows\\VideoLAN\\VLC\\vlc.exe'

        mock_system.return_value = 'Windows'
        mock_find_executable.return_value = None
        mock_isfile.side_effect = fake_isfile
        mock_join.side_effect = self._fake_windows_join

        for env in ['ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432']:
            with mock.patch.dict('os.environ', {
                env: 'C:\\path\\to\\windows',
            }, clear=True):
                self.assertEqual(helper.utils.get_vlc(),
                                 'C:\\path\\to\\windows\\'
                                 'VideoLAN\\VLC\\vlc.exe')

            with mock.patch.dict('os.environ', {
                env: 'C:\\bad\\path\\to\\windows',
            }, clear=True):
                self.assertIsNone(helper.utils.get_vlc(), None)

        with mock.patch.dict('os.environ', {}, clear=True):
            self.assertIsNone(helper.utils.get_vlc(), None)

    @mock.patch('os.access')
    @mock.patch('os.path.isfile')
    @mock.patch('platform.system')
    @mock.patch('distutils.spawn.find_executable')
    def test_utils_get_vlc_darwin(self, mock_find_executable, mock_system,
                                  mock_isfile, mock_access):
        mock_system.return_value = 'Darwin'
        mock_find_executable.return_value = None

        mock_isfile.return_value = True
        mock_access.return_value = True
        self.assertEqual(helper.utils.get_vlc(),
                         '/Applications/VLC.app/Contents/MacOS/VLC')

        mock_isfile.return_value = False
        mock_access.return_value = True
        self.assertEqual(helper.utils.get_vlc(), None)

        mock_isfile.return_value = True
        mock_access.return_value = False
        self.assertEqual(helper.utils.get_vlc(), None)

        mock_isfile.return_value = False
        mock_access.return_value = False
        self.assertEqual(helper.utils.get_vlc(), None)

    @mock.patch.dict(os.environ, {
        'SUDO_USER': 'sudouser',
        'EXISTING_KEY': 'existingvalue',
    }, clear=True)
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_run_as_user_not_windows_sudo_user(self, mock_system,
                                                     mock_getpwnam):
        mock_system.return_value = 'Linux'

        mock_pwnam = mock.MagicMock()
        mock_pwnam.pw_name = 'PWNAME'
        mock_pwnam.pw_gid = 'PWGID'
        mock_pwnam.pw_uid = 'PWUID'
        mock_pwnam.pw_dir = 'PWDIR'
        mock_getpwnam.return_value = mock_pwnam

        as_user = helper.utils.run_as_user()

        mock_getpwnam.assert_called_with('sudouser')
        self.assertTrue(isinstance(as_user, dict),
                        'run_as_user() does not return a dict')

        for param in ['preexec_fn', 'env']:
            self.assertTrue(param in as_user,
                            '{} not returned by run_as_user()'.format(param))

        with mock.patch('os.setgid') as mock_setgid, \
                mock.patch('os.setuid') as mock_setuid:
            as_user['preexec_fn']()

            mock_setgid.assert_called_with('PWGID')
            mock_setuid.assert_called_with('PWUID')

        expected_env = {
            'HOME': 'PWDIR',
            'LOGNAME': 'PWNAME',
            'USER': 'PWNAME',
            'USERNAME': 'PWNAME',
            'EXISTING_KEY': 'existingvalue',
        }
        self.assertDictEqual(expected_env, as_user['env'])

    @mock.patch.dict(os.environ, {
        'EXISTING_KEY': 'existingvalue',
    }, clear=True)
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_run_as_user_not_windows_not_sudo_user(self, mock_system,
                                                         mock_getpwnam):
        mock_system.return_value = 'Linux'

        with LogCapture() as l:
            as_user = helper.utils.run_as_user()

            mock_getpwnam.assert_not_called()

            self.assertTrue(isinstance(as_user, dict),
                            'run_as_user() does not return a dict')
            self.assertDictEqual({}, as_user)

            l.check_present(
                ('helper.utils', 'DEBUG',
                 u'No need to change the user'),
            )

    @mock.patch.dict(os.environ, {
        'EXISTING_KEY': 'existingvalue',
    }, clear=True)
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_run_as_user_not_windows_not_sudo_user(self, mock_system,
                                                         mock_getpwnam):
        mock_system.return_value = 'Windows'

        with LogCapture() as l:
            as_user = helper.utils.run_as_user()

            mock_getpwnam.assert_not_called()

            self.assertTrue(isinstance(as_user, dict),
                            'run_as_user() does not return a dict')
            self.assertDictEqual({}, as_user)

            l.check_present(
                ('helper.utils', 'DEBUG',
                 u'No need to change the user'),
            )

    def test_utils_get_os_config_config_lua(self):
        expected = {
            'config': '/path/to/config',
            'lua': '/path/to/lua',
        }

        output = helper.utils.get_os_config(config=expected['config'],
                                            lua=expected['lua'])

        self.assertDictEqual(expected, output)

    @mock.patch.dict(os.environ, {
        'SUDO_USER': 'sudouser',
    }, clear=True)
    @mock.patch('glob.iglob')
    @mock.patch('os.path.join')
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_get_os_config_linux_sudo_user(
            self, mock_system, mock_getpwnam, mock_join, mock_iglob):
        mock_system.return_value = 'Linux'

        mock_pwnam = mock.MagicMock()
        mock_pwnam.pw_name = 'PWNAME'
        mock_pwnam.pw_gid = 'PWGID'
        mock_pwnam.pw_uid = 'PWUID'
        mock_pwnam.pw_dir = '/PWDIR'
        mock_getpwnam.return_value = mock_pwnam

        mock_join.side_effect = self._fake_unix_join

        mock_iglob.return_value = ['/system/path/to/lua']

        expected = {
            'config': '/PWDIR/.config/vlc',
            'lua': '/PWDIR/.local/share/vlc/lua',
        }

        output = helper.utils.get_os_config()
        self.assertDictEqual(expected, output)

        output = helper.utils.get_os_config(config='/path/to/config')
        mock_iglob.assert_not_called()
        self.assertDictEqual({'config': '/path/to/config',
                              'lua': expected['lua']},
                             output)

        output = helper.utils.get_os_config(lua='/path/to/lua')
        mock_iglob.assert_not_called()
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/path/to/lua'},
                             output)

        output = helper.utils.get_os_config(system=True)
        mock_iglob.assert_has_calls([
            mock.call('/usr/lib/*/vlc/lua'),
            mock.call('/usr/lib/vlc/lua'),
        ])
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/system/path/to/lua'},
                             output)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch('os.path.expanduser')
    @mock.patch('glob.iglob')
    @mock.patch('os.path.join')
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_get_os_config_linux_not_sudo_user(
            self, mock_system, mock_getpwnam, mock_join, mock_iglob,
            mock_expanduser):
        mock_system.return_value = 'Linux'
        mock_join.side_effect = self._fake_unix_join
        mock_iglob.return_value = ['/system/path/to/lua']
        mock_expanduser.return_value = '/HOMEDIR'

        expected = {
            'config': '/HOMEDIR/.config/vlc',
            'lua': '/HOMEDIR/.local/share/vlc/lua',
        }

        output = helper.utils.get_os_config()
        mock_getpwnam.assert_not_called()
        mock_iglob.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual(expected, output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(config='/path/to/config')
        mock_getpwnam.assert_not_called()
        mock_iglob.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual({'config': '/path/to/config',
                              'lua': expected['lua']},
                             output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(lua='/path/to/lua')
        mock_getpwnam.assert_not_called()
        mock_iglob.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/path/to/lua'},
                             output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(system=True)
        mock_getpwnam.assert_not_called()
        mock_iglob.assert_has_calls([
            mock.call('/usr/lib/*/vlc/lua'),
            mock.call('/usr/lib/vlc/lua'),
        ])
        mock_expanduser.assert_called_once()
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/system/path/to/lua'},
                             output)
        mock_expanduser.reset_mock()

        mock_iglob.return_value = []
        with self.assertRaises(StopIteration):
            helper.utils.get_os_config(system=True)

    @mock.patch.dict(os.environ, {
        'SUDO_USER': 'sudouser',
    }, clear=True)
    @mock.patch('os.path.join')
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_get_os_config_darwin_sudo_user(
            self, mock_system, mock_getpwnam, mock_join):
        mock_system.return_value = 'Darwin'

        mock_pwnam = mock.MagicMock()
        mock_pwnam.pw_name = 'PWNAME'
        mock_pwnam.pw_gid = 'PWGID'
        mock_pwnam.pw_uid = 'PWUID'
        mock_pwnam.pw_dir = '/PWDIR'
        mock_getpwnam.return_value = mock_pwnam

        mock_join.side_effect = self._fake_unix_join

        expected = {
            'config': '/PWDIR/Library/Preferences/org.videolan.vlc',
            'lua': '/PWDIR/Library/Application Support/org.videolan.vlc/lua',
        }

        output = helper.utils.get_os_config()
        self.assertDictEqual(expected, output)

        output = helper.utils.get_os_config(config='/path/to/config')
        self.assertDictEqual({'config': '/path/to/config',
                              'lua': expected['lua']},
                             output)

        output = helper.utils.get_os_config(lua='/path/to/lua')
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/path/to/lua'},
                             output)

        output = helper.utils.get_os_config(system=True)
        self.assertDictEqual(
            {'config': expected['config'],
             'lua': '/Applications/VLC.app/Contents/MacOS/share/lua'},
            output)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch('os.path.expanduser')
    @mock.patch('os.path.join')
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_get_os_config_darwin_not_sudo_user(
            self, mock_system, mock_getpwnam, mock_join, mock_expanduser):
        mock_system.return_value = 'Darwin'
        mock_join.side_effect = self._fake_unix_join
        mock_expanduser.return_value = '/HOMEDIR'

        expected = {
            'config': '/HOMEDIR/Library/Preferences/org.videolan.vlc',
            'lua': '/HOMEDIR/Library/Application Support/org.videolan.vlc/lua',
        }

        output = helper.utils.get_os_config()
        mock_getpwnam.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual(expected, output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(config='/path/to/config')
        mock_getpwnam.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual({'config': '/path/to/config',
                              'lua': expected['lua']},
                             output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(lua='/path/to/lua')
        mock_getpwnam.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual({'config': expected['config'],
                              'lua': '/path/to/lua'},
                             output)
        mock_expanduser.reset_mock()

        output = helper.utils.get_os_config(system=True)
        mock_getpwnam.assert_not_called()
        mock_expanduser.assert_called_once()
        self.assertDictEqual(
            {'config': expected['config'],
             'lua': '/Applications/VLC.app/Contents/MacOS/share/lua'},
            output)
        mock_expanduser.reset_mock()

    @mock.patch.dict(os.environ, {
        'APPDATA': 'T:\\APPDATA',
        'PROGRAMFILES': 'T:\\PROGRAMFILES',
    }, clear=True)
    @mock.patch('os.path.join')
    @mock.patch('pwd.getpwnam')
    @mock.patch('platform.system')
    def test_utils_get_os_config_windows(self, mock_system, mock_getpwnam,
                                         mock_join):
        mock_system.return_value = 'Windows'
        mock_join.side_effect = self._fake_windows_join

        expected = {
            'config': 'T:\\APPDATA\\vlc',
            'lua': 'T:\\APPDATA\\vlc\\lua',
        }

        output = helper.utils.get_os_config()
        self.assertDictEqual(expected, output)

        output = helper.utils.get_os_config(config='T:\\path\\to\\config')
        self.assertDictEqual({'config': 'T:\\path\\to\\config',
                              'lua': 'T:\\path\\to\\config\\lua'},
                             output)

        output = helper.utils.get_os_config(lua='T:\\path\\to\\lua')
        self.assertDictEqual({'config': expected['config'],
                              'lua': 'T:\\path\\to\\lua'},
                             output)

        output = helper.utils.get_os_config(system=True)
        self.assertDictEqual(
            {'config': expected['config'],
             'lua': 'T:\\PROGRAMFILES\\VideoLAN\\VLC\\lua'},
            output)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch('platform.system')
    def test_utils_get_os_config_unknown_os(self, mock_system):
        mock_system.return_value = 'Unknown OS'

        with self.assertRaises(RuntimeError) as e:
            output = helper.utils.get_os_config()

        self.assertEqual('Unsupported operating system: Unknown OS',
                         str(e.exception))

    @mock.patch('__builtin__.raw_input')
    def test_utils_ask_yes_no(self, mock_input):
        # Check invalid values continue prompting
        mock_input.side_effect = ['these', 'are', 'not', 'valid', 'values']
        with self.assertRaises(StopIteration):
            helper.utils.ask_yes_no('test prompt')
        mock_input.side_effect = None
        mock_input.reset_mock()

        # Check yes values
        for value in ['y', 'yes', '1', 'Y', 'YeS']:
            mock_input.return_value = value
            reply = helper.utils.ask_yes_no('test prompt')
            mock_input.assert_called_once()
            mock_input.assert_called_with('test prompt [y/n] ')
            self.assertTrue(reply,
                            'Value \'{}\' did not result in \'yes\''.format(
                                value))
            mock_input.reset_mock()

        # Check no values
        for value in ['n', 'no', '0', 'N', 'nO']:
            mock_input.return_value = value
            reply = helper.utils.ask_yes_no('test prompt')
            mock_input.assert_called_once()
            mock_input.assert_called_with('test prompt [y/n] ')
            self.assertFalse(reply,
                             'Value \'{}\' did not result in \'no\''.format(
                                 value))
            mock_input.reset_mock()

        # Check manage exceptions
        for exc in [KeyboardInterrupt, EOFError]:
            mock_input.side_effect = exc

            with mock.patch('__builtin__.print') as mock_print:
                try:
                    self.assertIsNone(helper.utils.ask_yes_no('test prompt'),
                                      'Aborted by signal is not None')
                except exc:
                    self.assertFail()

                mock_print.assert_called_with(
                    'Installation aborted by signal.')

            mock_input.reset_mock()

    def test_utils_redirectstd(self):
        output = io.BytesIO()
        with helper.utils.redirectstd(output):
            sys.stdout.write('test stdout')
        self.assertEqual('test stdout', output.getvalue())

        output = io.BytesIO()
        with helper.utils.redirectstd(output):
            sys.stderr.write('test stderr')
        self.assertEqual('test stderr', output.getvalue())

    def test_utils_class_Command(self):
        obj = helper.utils.Command()
        
        for attr in ['command', 'description']:
            self.assertTrue(hasattr(obj, attr),
                            'Object of class {cls} has '
                            'no attribute {attr}'.format(
                                cls=obj.__class__.__name__,
                                attr=attr))
            self.assertEqual(getattr(obj, attr), None)

        for meth in ['add_arguments', 'check_arguments', 'run']:
            self.assertTrue(hasattr(obj, meth),
                            'Object of class {cls} has '
                            'no attribute {attr}'.format(
                                cls=obj.__class__.__name__,
                                attr=meth))
            self.assertTrue(callable(getattr(obj, meth)),
                            'Attribute {attr} of class {cls} is not '
                            'callable (method)'.format(
                                cls=obj.__class__.__name__,
                                attr=meth))

        self.assertIsNone(obj.add_arguments(parser=None))
        self.assertIsNone(obj.check_arguments(parser=None, args=None))
        self.assertIsNone(obj.run())

    def test_utils_class_CommandOutput(self):
        obj = helper.utils.CommandOutput()
        self.assertEqual(obj.exit_code, 0,
                         'Default exit_code is not 0')
        self.assertIsNone(obj.data,
                          'Default data is not None')
        with mock.patch('__builtin__.print') as mock_print:
            obj.print()
            mock_print.assert_not_called()

        obj = helper.utils.CommandOutput(exit_code=1)
        self.assertEqual(obj.exit_code, 1,
                         'Unable to manually define exit_code')
        self.assertIsNone(obj.data,
                          'Default data is not None when exit_code is set')
        with mock.patch('__builtin__.print') as mock_print:
            obj.print()
            mock_print.assert_not_called()

        obj = helper.utils.CommandOutput(data=['list'])
        self.assertListEqual(obj.data, ['list'],
                             'Unable to manually define data')
        self.assertEqual(obj.exit_code, 0,
                         'Default exit_code is not 0 when data is set')
        with mock.patch('__builtin__.print') as mock_print:
            obj.print()
            mock_print.assert_called_once_with(json.dumps(
                obj.data, sort_keys=True, indent=4, separators=(',', ': '),
                ensure_ascii=False))

        obj = helper.utils.CommandOutput(data=['list'], is_json=False)
        self.assertListEqual(obj.data, ['list'],
                             'Unable to manually define data')
        with mock.patch('__builtin__.print') as mock_print:
            obj.print()
            mock_print.assert_called_once_with(obj.data)


if __name__ == '__main__':
    unittest.main()
