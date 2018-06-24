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

#
# The aim of this file is to provide a helper for any task that cannot
# be performed easily in the lua interface for VLC. The lua interface
# will thus be able to call this tool to perform those tasks and return
# the results
#

from __future__ import print_function
import logging
import platform
import sys

from helper.version import *  # noqa: F401, F403
from helper.parser import (
    parse_args,
)
from helper.utils import (
    CommandOutput,
)

LOGGER = logging.getLogger(__name__)


##############################################################################
# Main method that will parse the command line arguments and run the function
# to perform the appropriate actions
def main(argv=None):
    # If no command line arguments, defaults to installation
    if (argv is None and len(sys.argv) == 1) or \
            (argv is not None and len(argv) == 0):
        argv = []
        if platform.system() == 'Windows':
            argv.append('--keep-alive')
        argv.append('install')

    args, action, params = parse_args(argv)

    ##########################################################################
    # Prepare the logger
    if args.loglevel == 'DEFAULT':
        if args.command in ['install', 'uninstall', 'service']:
            args.loglevel = 'INFO'
        else:
            args.loglevel = 'WARNING'

    log_level_value = getattr(logging, args.loglevel)
    logargs = {
        'level': log_level_value,
        'format': args.logformat,
    }
    if args.logfile:
        logargs['filename'] = args.logfile
    logging.basicConfig(**logargs)

    ##########################################################################
    # Call the function
    try:
        command_output = action(**params)
    except Exception as e:
        LOGGER.exception(e, exc_info=True)
        raise

    exit_code = 0
    if isinstance(command_output, CommandOutput):
        exit_code = command_output.exit_code
        command_output.print()
    elif isinstance(command_output, int):
        exit_code = command_output

    if hasattr(args, 'keep_alive') and args.keep_alive:
        print('Press a key to continue.')
        raw_input()

    sys.exit(exit_code)


##############################################################################
# Function to initialize the script as a binary
def init():
    if __name__ == '__main__':
        main()


##############################################################################
# Run the init function
init()
