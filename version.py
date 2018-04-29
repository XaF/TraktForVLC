#!/usr/bin/env python
# encoding: utf-8
#
# To read the git and Continuous Integration versions information,
# and easily set those versions in the project files when building
#
# Copyright (C) 2016-2018   Raphaël Beamonte <raphael.beamonte@gmail.com>
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

#
# The aim of this file is to provide a helper for any task that cannot
# be performed easily in the lua interface for VLC. The lua interface
# will thus be able to call this tool to perform those tasks and return
# the results
#

from __future__ import print_function
import argparse
import logging
import os
import platform
import re
import shutil
import struct
import subprocess
import tempfile
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GitVersionException(Exception):
    pass


class GitVersionReader(object):

    pep440_public_version_pattern = (
        "(?:(?P<epoch>[0-9]*)!)?"
        "(?P<release>[0-9]*(\.[0-9]*)*)"
        "((?P<pre_type>a|b|rc)(?P<pre_num>[0-9]*))?"
        "(\.post(?P<post_num>[0-9]*))?"
        "(\.dev(?P<dev_num>[0-9]*))?")
    pep440_local_version_pattern = (
        "{}"
        "(?:\+(?P<local>[a-zA-Z0-9]+"
        "(?:\.[a-zA-Z0-9]*)*))?").format(pep440_public_version_pattern)

    pep440_public_version = re.compile(
        "^v?(?P<full>{})$".format(pep440_public_version_pattern))
    pep440_local_version = re.compile(
        "^v?(?P<full>{})$".format(pep440_local_version_pattern))

    def __init__(self, path=os.path.dirname(__file__),
                 match=False, tags=False):
        self._path = path
        self._match = match
        self._tags = tags

    def call_git_describe(self, abbrev=7, exact=False, always=False,
                          match=False, tags=False, commit=None, dirty=True):
        cmd = ['git', 'describe', '--abbrev={}'.format(abbrev)]
        if tags:
            cmd.append('--tags')
        if match:
            cmd.append(['--match', str(match)])
        if exact:
            cmd.append('--exact-match')
        if always:
            cmd.append('--always')
        if commit:
            cmd.append(commit)
        elif dirty:
            cmd.append('--dirty')

        try:
            version = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                cwd=self._path,
            )
            return version.strip()
        except subprocess.CalledProcessError as e:
            if '.gitconfig' in e.output:
                raise GitVersionException(
                    'You may need to update your git version: {}'.format(
                        e.output))
        except OSError as e:
            if e.strerror != 'No such file or directory':
                raise

        # Version not found, but no error raised
        return None

    def call_git_rev_list(self, branch='HEAD'):
        cmd = ['git', 'rev-list', '--count', branch]

        try:
            count = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                cwd=self._path,
            )
            return int(count.strip())
        except subprocess.CalledProcessError as e:
            if '.gitconfig' in e.output:
                raise GitVersionException(
                    'You may need to update your git version: {}'.format(
                        e.output))
        except OSError as e:
            if e.strerror != 'No such file or directory':
                raise

        # We were not able to get the rev list, but no error raised
        return 0

    def get_version(self, abbrev=7, match=None, tags=None):
        dev = False

        if match is None:
            match = self._match
        if tags is None:
            tags = self._tags

        # Search first for a tag
        version = self.call_git_describe(abbrev, exact=True, match=match,
                                         tags=tags)
        if not version:
            # The current version is not tagged, so it is a dev version
            dev = True

            # Try to find the version computed from the closest tag
            version = self.call_git_describe(abbrev, match=match, tags=tags)
            if not version:
                # We did not find any tag matching, so maybe there is no tag
                # in the repo yet? We will try to find the commit number to
                # define the version
                commit = self.call_git_describe(abbrev, always=True,
                                                match=match, tags=tags)
                if not commit:
                    raise GitVersionException(
                        'Unable to find the version number')

                # If we found the commit, it's the one defining the version
                version = '0.0.0a0-{}-g{}'.format(self.call_git_rev_list(),
                                                  commit)

        if dev or version.endswith('-dirty'):
            vsplit = version.split('-')

            if dev:
                # Check if there is already a dev number in the tag
                m = self.pep440_public_version.search(vsplit[0])
                if m and m.group('dev_num'):
                    vsplit[1] = int(vsplit[1]) + int(m.group('dev_num'))
                    vsplit[0] = re.sub('\.dev{}$'.format(m.group('dev_num')),
                                       '', vsplit[0])

                vsplit[0] = '{}.dev{}'.format(vsplit[0], vsplit[1])

            m = False if vsplit[0][0].isdigit() else re.search('\d', vsplit[0])
            version = '{}+{}'.format(
                vsplit[0][m.start():] if m else vsplit[0],
                '.'.join(vsplit[2 if dev else 1:]))

        return version


class CIVersionReader(GitVersionReader):
    PULL_REQUEST_ENV = [
        'TRAVIS_PULL_REQUEST',  # For Travis
        'APPVEYOR_PULL_REQUEST_NUMBER',  # For AppVeyor
    ]

    def read_pullrequest_version(self):
        for pr_env in self.PULL_REQUEST_ENV:
            pr = os.getenv(pr_env)
            if pr and pr.lower() != 'false':
                break

        if not pr or pr.lower() == 'false':
            return None

        m = re.search('\d+', pr)
        return str(m.group(0) if m else pr).strip()

    def check_tag(self, tag=None, abbrev=7):
        if not tag:
            tag = self.call_git_describe(abbrev, exact=True)

        # If we did not find any version, we can return now, there
        # is no tag to check
        if not tag:
            raise GitVersionException(
                'No tag found for the current commit.')

        if not self.pep440_public_version.search(tag):
            raise GitVersionException(
                'Version {} does not match PEP440 for public version '
                'identifiers.'.format(tag))

    def get_version(self, *args, **kwargs):
        try:
            version = super(CIVersionReader, self).get_version(
                *args, **kwargs)
        except GitVersionException as e:
            logger.warning(e)
            version = '0.0.0a0.dev0+unknown'

        pr = self.read_pullrequest_version()
        if pr:
            version = '{version}{sep}{pr}'.format(
                version=version,
                sep='.' if '+' in version else '+',
                pr='pr{}'.format(pr),
            )

        return version

    def get_release_name(self, commit=None, always=False):
        while 'I have not found a release name':
            # Try and get the closest tag
            try:
                tag = self.call_git_describe(abbrev=0, dirty=False,
                                             commit=commit)
            except GitVersionException:
                # No tag, there is no release name
                return None
            else:
                if not tag:
                    return None

            # Get that tag's description
            tag_desc = None
            try:
                tag_desc = subprocess.check_output(
                    ['git', 'tag', '-n', tag],
                    stderr=subprocess.STDOUT,
                    cwd=self._path,
                ).strip()
            except subprocess.CalledProcessError as e:
                if '.gitconfig' in e.output:
                    raise GitVersionException(
                        'You may need to update your git version: {}'.format(
                            e.output))
            except OSError as e:
                if e.strerror != 'No such file or directory':
                    raise

            if tag_desc is None:
                return

            # Use a regular expression to check if this leads to a release name
            relname_re = re.compile(
                '^{}\s*(?:Prer|R)elease: (?P<relname>.*)$'.format(
                    re.escape(tag)))
            m = relname_re.search(tag_desc)
            if not m:
                # This tag did not lead to a release name
                if always:
                    # try with the commit before it!
                    commit = '{}^'.format(tag)
                    continue
                else:
                    return

            return m.group('relname')

    def get_environment(self, version, variables=None, check_previous=True,
                        asdict=False):
        # Depending on the platform, we will output different format of
        # environment variables to be loaded directly with an eval-like
        # command
        if platform.system() == 'Windows':
            env_format = '$env:{key} = {value};'
            true_format = '$true'
            escaped_quote = '`"'
        else:
            env_format = 'export {key}={value}'
            true_format = '1'
            escaped_quote = '\\"'

        # First, match the version with the local version format of PEP440,
        # if it does not match, we're having a problem.
        m = self.pep440_local_version.search(version)
        if not m:
            raise GitVersionException(
                'Version {} does not match PEP440 for local version '
                'identifiers.'.format(version))

        # Prepare a variable to get the release name information
        relname_commit = None

        # Get the results as a dictionary
        values = m.groupdict()

        # Check if there is a local part, in which case we want to split it
        # to have as many information as possible
        if values['local']:
            local = values['local']

            # Check if there was a specific commit number
            re_commit = re.compile("^g(?P<commit>[a-z0-9]+)(\.|$)")
            m_commit = re_commit.search(local)
            if m_commit:
                values['local_commit'] = m_commit.group('commit')
                relname_commit = m_commit.group('commit')
                local = re_commit.sub('', local)

            # Check if the repository was considered as dirty
            re_dirty = re.compile("(^|\.)dirty(\.|$)")
            m_dirty = re_dirty.search(local)
            if m_dirty:
                values['local_dirty'] = True
                local = re_dirty.sub('\g<1>', local)

            # Check if there was a PR being processed
            re_pr = re.compile("(^|\.)pr(?P<pr>[0-9]+)(\.|$)")
            m_pr = re_pr.search(local)
            if m_pr:
                values['local_pr'] = m_pr.group('pr')
                local = re_pr.sub('\g<1>', local)

            # If there is still information, that we thus do not expect, raise
            # an exception: the version is not in an expected format
            if local and local != '.':
                raise GitVersionException(
                    'Version {} does not match the requirements for the '
                    'local version part: \'{}\' is left after parsing the '
                    'known information.'.format(version, local))

            # If a commit information was found, check that commit's parent
            # information
            if check_previous and values['dev_num']:
                same = False

                parent = self.call_git_describe(
                    commit=m_commit.group('commit'))
                if parent:
                    sparent = parent.split('-')
                    m_parent = self.pep440_public_version.search(
                        sparent[0])

                    if m_parent:
                        vparent = m_parent.groupdict()

                        same = True
                        for check in [
                                'epoch', 'release', 'pre_type',
                                'pre_num', 'post_num']:
                            if vparent[check] != values[check]:
                                same = False
                                break

                if same and values['dev_num'] and vparent['dev_num'] and \
                        (int(values['dev_num']) ==
                         int(vparent['dev_num']) + int(sparent[1])):
                    values['parent_dev_num'] = vparent['dev_num']
                    values['relative_dev_num'] = sparent[1]

            # Prepare the local-related information to be added in the
            # description; In the current setup, the dev-num is directly
            # linked to the number of git commit ahead of the given tag,
            # which means that if there is a dev-num, there should always
            # be local information
            local_desc_info = []
            if m_pr:
                local_desc_info.append('pull request {}'.format(
                    values['local_pr']))
            if values['dev_num']:
                local_desc_info.append('{} commit{} ahead'.format(
                    values.get('relative_dev_num', values['dev_num']),
                    's' if int(values['dev_num']) > 1 else ''))
            if m_commit:
                local_desc_info.append('commit {}'.format(
                    values['local_commit']))
            if m_dirty:
                local_desc_info.append('dirty')

            local_desc = 'a development version ({}) based on '.format(
                ', '.join(local_desc_info))
        else:
            relname_commit = version
            local_desc = ''

        # Prepare the dev-related information to be added in the description;
        # we only compute that information if there is no local information,
        # because in that case it means that we are actually using a git tag
        # containing that information
        if (values['dev_num'] and not values['local']) or \
                'parent_dev_num' in values:
            dev_num = values.get('parent_dev_num', values['dev_num'])

            # Ordinal function taken from Gareth on codegolf
            def ordinal(n):
                return "{}{}".format(
                    n, "tsnrhtdd"[(n / 10 % 10 != 1) *
                                  (n % 10 < 4) * n % 10::4])

            dev_desc = 'the {} development release of '.format(
                ordinal(int(dev_num)))
        else:
            dev_desc = ''

        # Prepare the post-related information to be added in the description
        if values['post_num']:
            post_desc = 'the post-release {} of '.format(
                values['post_num'])
        else:
            post_desc = ''

        # Prepare the description messages depending on the type of release
        if values['pre_type']:
            if values['pre_type'] == 'rc':
                values['pre_type'] = 'release candidate'
                compl_desc = (
                    "New features will not be added to the "
                    "release {release}, only bugfixes.").format(
                        release=values['release'])
            elif values['pre_type'] == 'b':
                values['pre_type'] = 'beta'
                compl_desc = (
                    "This should not be considered stable and used with "
                    "precautions.")
            else:
                values['pre_type'] = 'alpha'
                compl_desc = (
                    "This should only be used if you know what you are "
                    "doing.")

            values['description'] = (
                "This is {local_desc}{dev_desc}{post_desc}the "
                "{pre_type} {pre_num} of TraktForVLC {release}. "
                "{compl_desc}").format(
                    local_desc=local_desc, dev_desc=dev_desc,
                    post_desc=post_desc, compl_desc=compl_desc, **values)
        else:
            values['description'] = (
                "This is {local_desc}{dev_desc}{post_desc}"
                "TraktForVLC {release}.").format(
                    local_desc=local_desc, dev_desc=dev_desc,
                    post_desc=post_desc, **values)

        # Add the version name
        values['name'] = 'TraktForVLC {}'.format(values['full'])
        relname = self.get_release_name(commit=relname_commit)
        if relname:
            values['release_name'] = relname
            values['name'] = '{} "{}"'.format(
                values['name'], relname).replace('"', escaped_quote)

        if asdict:
            return {
                k: v for k, v in values.items()
                if variables is None or k in variables
            }

        # Prepare the output, for each entry in our dict, we will format one
        # line of output as an environment variable
        output = []
        for k, v in sorted(values.items()):
            if v is None or (variables is not None and k not in variables):
                continue

            if v is True:
                v = true_format
            else:
                v = '"{}"'.format(v)

            k = 'TRAKT_VERSION' if k == 'full' else \
                'TRAKT_VERSION_{}'.format(k.upper())

            output.append(env_format.format(key=k, value=v))

        # Join the output and return it
        return '\n'.join(output)


def set_version(full, release_name=None, **env):
    base = os.path.dirname(os.path.realpath(__file__))
    reset = (full == '0.0.0a0.dev0')

    def build_system_release():
        if not reset:
            if platform.system() == 'Linux':
                return ' '.join(platform.linux_distribution()[:2])
            elif platform.system() == 'Darwin':
                return 'macOS {}'.format(platform.mac_ver()[0])
            elif platform.system() == 'Windows':
                return 'Windows {}'.format(platform.win32_ver()[0])

        return ''

    def release_type():
        if reset:
            return ''

        system = platform.system().lower()
        if system == 'darwin':
            system = 'osx'
        elif system == 'windows':
            arch = struct.calcsize('P') * 8
            if arch == 32:
                system = '{}_x86'.format(system)
            elif arch == 64:
                system = '{}_x64'.format(system)
        if os.getenv('BIN_SUFFIX'):
            system = '{}_{}'.format(system, os.environ['BIN_SUFFIX'])

        return system

    rules = [
        {
            'files': [
                os.path.join(base, 'trakt.lua'),
            ],
            'patterns': [
                (
                    re.compile("^(local __version__ = )'.*'$", re.MULTILINE),
                    "\g<1>'{}'".format(full),
                ),
            ]
        },
        {
            'files': [
                os.path.join(base, 'helper', 'version.py'),
            ],
            'patterns': [
                (
                    re.compile("^(__version__ = )'.*'$", re.MULTILINE),
                    "\g<1>'{}'".format(full),
                ),
                (
                    re.compile("^(__release_name__ = )'.*'$", re.MULTILINE),
                    "\g<1>'{}'".format(
                        release_name
                        if release_name and not reset else ''),
                ),
                (
                    re.compile("^(__build_date__ = )'.*'$", re.MULTILINE),
                    "\g<1>'{}'".format(
                        time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                      time.gmtime())
                        if not reset else ''),
                ),
                (
                    re.compile("^(__build_system__ = )'.*'$", re.MULTILINE),
                    "\g<1>'{}'".format(
                        platform.system()
                        if not reset else ''),
                ),
                (
                    re.compile("^(__build_system_release__ = )'.*'$",
                               re.MULTILINE),
                    "\g<1>'{}'".format(build_system_release()),
                ),
                (
                    re.compile("^(__release_type__ = )'.*'$",
                               re.MULTILINE),
                    "\g<1>'{}'".format(release_type()),
                ),
            ],
        },
    ]

    for rule in rules:
        for f in rule['files']:
            fd, tmp = tempfile.mkstemp()
            shutil.copystat(f, tmp)

            try:
                with open(f, 'r') as fin, os.fdopen(fd, 'w') as fout:
                    out = fin.read()
                    for p, r in rule['patterns']:
                        out = p.sub(r, out)
                    fout.write(out)
            except Exception:
                os.remove(tmp)
                raise
            else:
                shutil.move(tmp, f)


def main():
    versionreader = CIVersionReader()
    version = versionreader.get_version()

    parser = argparse.ArgumentParser(
        description='Tool to read and set the version for the different '
                    'files of the project')

    commands = parser.add_subparsers(
        help='Commands',
        dest='command')

    commands.add_parser(
        'version',
        help='Will print the computed version')

    set_parser = commands.add_parser(
        'set',
        help='Will set the current version in the lua and py files')
    set_parser_group = set_parser.add_mutually_exclusive_group()
    set_parser_group.add_argument(
        '--reset',
        dest='version',
        action='store_const',
        const='0.0.0a0.dev0',
        help='Reset version to 0.0.0a0.dev0')
    set_parser_group.add_argument(
        '--version',
        help='Define the version to be set')

    check_tag_parser = commands.add_parser(
        'check-tag',
        help='To check if the current tag is properly formatted for '
             'releasing a version, according to PEP440')
    check_tag_parser.add_argument(
        '-t', '--tag',
        help='The version tag to check. If not given, will look for the '
             'tag set for the current version - and fail if not found')

    environment_parser = commands.add_parser(
        'environment',
        help='Return the environment variables defining the version')
    environment_parser.add_argument(
        '--version',
        help='Define the version to be parsed')
    environment_parser.add_argument(
        '--variable',
        action='append',
        help='Only return that environment variable; can be repeated')

    args = parser.parse_args()
    if args.command == 'version':
        print(version)
    elif args.command in 'set':
        set_version(**versionreader.get_environment(
            args.version or version, asdict=True))
        print('OK')
    elif args.command == 'check-tag':
        versionreader.check_tag(tag=args.tag)
        print('OK')
    elif args.command == 'environment':
        print(versionreader.get_environment(
            args.version or version, args.variable))
    else:
        raise Exception('Unknown command.')


if __name__ == '__main__':
    main()
