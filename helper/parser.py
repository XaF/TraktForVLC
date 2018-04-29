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
import argparse
import inspect
import logging
import platform
import sys
import types

from helper.version import (
    __version__,
    __release_name__,
    __build_date__,
    __build_system__,
    __build_system_release__,
    __author__,
)

LOGGER = logging.getLogger(__name__)


##############################################################################
# Class defining the KeepLineBreaksFormatter description help formatter that
# aims at keeping the line breaks in the help, while providing text wrapping
# facilities
class KeepLineBreaksFormatter(argparse.RawDescriptionHelpFormatter):
    def _fill_text(self, text, width, indent):
        return '\n'.join(['\n'.join(argparse._textwrap.wrap(line, width))
                          for line in text.splitlines()])


##############################################################################
# Allow to use --xx and --no-xx options
class ActionYesNo(argparse.Action):
    def __init__(self, option_strings, dest, default=None,
                 required=False, help=None):

        opt = option_strings[0]
        if not opt.startswith('--'):
            raise ValueError('Yes/No arguments must be prefixed with --')

        if opt.startswith('--no-'):
            opt = opt[5:]
            if default is None:
                default = True
        else:
            opt = opt[2:]
            if default is None:
                default = False

        # Save the option as attribute
        self.opt = opt

        # List of options available for that
        opts = ['--{}'.format(opt), '--no-{}'.format(opt)]

        # Check that all other options are acceptable
        for extra_opt in option_strings[1:]:
            if not extra_opt.startswith('--'):
                raise ValueError('Yes/No arguments must be prefixed with --')
            if not extra_opt.endswith('-{}'.format(opt)):
                raise ValueError(
                    'Only single argument is allowed with Yes/No action')

            opts.append(extra_opt)

        super(ActionYesNo, self).__init__(
            opts, dest, nargs=0, const=None, default=default,
            required=required, help=help)

    def __call__(self, parser, namespace, values, option_strings=None):
        if option_strings == '--{}'.format(self.opt):
            setattr(namespace, self.dest, True)
        elif option_strings == '--no-{}'.format(self.opt):
            setattr(namespace, self.dest, False)
        else:
            opt = option_strings[2:-len(self.opt) - 1]
            boolean = True
            if opt.startswith('no-'):
                boolean = False
                opt = opt[3:]
            elif opt.endswith('-no'):
                boolean = False
                opt = opt[:-3]
            setattr(namespace, self.dest, (boolean, opt))


##############################################################################
# Class defining the PrintVersion argument parser to allow for short and
# long versions
class PrintVersion(argparse.Action):
    def __init__(self, help='show program\'s version number and exit',
                 *args, **kwargs):
        super(PrintVersion, self).__init__(
            nargs=0, default=argparse.SUPPRESS, help=help, *args, **kwargs)

    def __call__(self, parser, args, values, option_string=None):
        if option_string == '--short-version':
            print(__version__)
            sys.exit(0)

        version_desc = []
        version_desc.append('TraktForVLC {}{}{}'.format(
            __version__,
            ' "{}"'.format(__release_name__) if __release_name__ else '',
            ' for {}'.format(__build_system__) if __build_system__ else ''))
        version_desc.append('Copyright (C) 2017-2018 {}'.format(__author__))
        if __build_date__ or __build_system_release__:
            version_desc.append('Built{}{}'.format(
                ' on {}'.format(__build_date__) if __build_date__ else '',
                ' with {}'.format(__build_system_release__)
                if __build_system_release__ else ''))
        version_desc.extend([
            '',
            'This program is distributed in the hope that it will be useful,',
            'but WITHOUT ANY WARRANTY; without even the implied warranty of',
            'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the',
            'GNU General Public License (version 2) for more details.',
            '',
            'Source available: https://github.com/XaF/TraktForVLC',
        ])
        print('\n'.join(version_desc))
        sys.exit(0)


##############################################################################
# Function that aims at parsing the arguments received; these arguments can
# be received from the command line or from the running service instance
def parse_args(args=None, preparse=False, parser_type=argparse.ArgumentParser):
    ##########################################################################
    # Create a preparser that allows us to know everything that we need to
    # know before actually parsing and processing the arguments
    preparser = parser_type(
        add_help=False,
    )
    preparser.add_argument(
        '-d', '--debug',
        dest='loglevel',
        default='DEFAULT',
        action='store_const', const='DEBUG',
        help='Activate debug output')
    preparser.add_argument(
        '-q', '--quiet',
        dest='loglevel',
        default='DEFAULT',
        action='store_const', const='ERROR',
        help='Only show errors or critical log messages')
    preparser.add_argument(
        '--loglevel',
        dest='loglevel',
        default='DEFAULT',
        choices=('NOTSET', 'DEBUG', 'INFO',
                 'WARNING', 'ERROR', 'CRITICAL'),
        help='Define the specific log level')
    preparser.add_argument(
        '--logformat',
        default='%(asctime)s::%(levelname)s::%(message)s',
        help='To change the log format used')
    preparser.add_argument(
        '--logfile',
        help='To write the logs to a file instead of the standard output')

    if platform.system() == 'Windows':
        preparser.add_argument(
            '-k', '--keep-alive',
            help='To keep the console window alive at the end of the command',
            action='store_true',
        )

    ##########################################################################
    # Parse the known arguments of the preparser
    preargs, left_args = preparser.parse_known_args(args)
    if preparse:
        return preargs, left_args

    ##########################################################################
    # Now create the parser that we will use to actually parse the arguments
    parser = parser_type(
        description='TraktForVLC helper tool, providing an easy way to '
                    'install/uninstall TraktForVLC, as well as all the '
                    'commands and actions that cannot be performed directly '
                    'from the Lua VLC interface.\n\n'
                    'This program is distributed in the hope that it will be '
                    'useful, but WITHOUT ANY WARRANTY; without even the '
                    'implied warranty of MERCHANTABILITY or FITNESS FOR A '
                    'PARTICULAR PURPOSE.  See the GNU General Public License '
                    '(version 2) for more details.\n\n'
                    'Source available: https://github.com/XaF/TraktForVLC',
        formatter_class=KeepLineBreaksFormatter,
        parents=[preparser, ]
    )

    ##########################################################################
    # Parameters available for the tool in general
    parser.add_argument(
        '-V', '--version', '--short-version',
        action=PrintVersion)

    ##########################################################################
    # To define the commands available with the helper and separate them
    commands = parser.add_subparsers(
        help='Helper command',
        dest='command',
    )

    command_instances = {}
    import helper.commands
    # Go through the submodules in helper.commands to find the commands to
    # be made available
    for mname in dir(helper.commands):
        # If the object name starts with '_', discard it
        if mname.startswith('_'):
            continue

        # Else, check if the object is actually a module
        m = getattr(helper.commands, mname)
        if not isinstance(m, types.ModuleType):
            continue

        # If it was a module, go through the objects in it
        for cname in dir(m):
            # If the object name stats with '_', discard it
            if cname.startswith('_'):
                continue

            # Else, check if the object is a class, and if it is a subclass
            # of the helper.utils.Command class
            c = getattr(m, cname)
            if not inspect.isclass(c) or \
                    not issubclass(c, helper.utils.Command):
                continue

            # Finally, check if the command and description are defined for
            # the module
            if c.command is None or c.description is None:
                continue

            command_parser = commands.add_parser(
                c.command,
                help=c.description,
            )
            command_instances[c.command] = c()
            command_instances[c.command].add_arguments(command_parser)

    ##########################################################################
    # Parse the arguments
    args = parser.parse_args(args)

    ##########################################################################
    # Check the arguments for the command requested
    command_instances[args.command].check_arguments(parser, args)

    ##########################################################################
    # Prepare the parameters to be passed to that function
    params = {k: v for k, v in vars(args).items()}
    del params['command']
    for k in vars(preargs):
        del params[k]

    return args, command_instances[args.command].run, params
