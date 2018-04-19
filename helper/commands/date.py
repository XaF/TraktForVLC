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
import datetime
import json
import logging
import platform
import pytz

from helper.utils import (
    Command,
)

if platform.system() == 'Windows':
    import time

LOGGER = logging.getLogger(__name__)


##########################################################################
# The DATE command to perform operations on dates
class CommandDate(Command):
    command = 'date'
    description = 'To perform operations on dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            action='append',
            default=[],
            help='The format of the date to output',
        )
        parser.add_argument(
            '--timezone',
            help='Which timezone to use for the destination date',
        )
        parser.add_argument(
            '--from',
            dest='from_date',
            help='From which time to print the time',
        )
        parser.add_argument(
            '--from-timezone',
            help='Which timezone to use for the from date, if different than '
                 'the destination date',
        )
        parser.add_argument(
            '--from-format',
            default='%s.%f',
            help='Format of the date passed in the from argument',
        )

    def run(self, format, timezone, from_date, from_timezone, from_format):
        if not format:
            format = ['%Y-%m-%dT%H:%M:%S.%fZ', ]
        if from_date:
            if from_format in ['%s', '%s.%f']:
                from_date = float(from_date)
                from_dt = datetime.datetime.fromtimestamp(from_date)
            else:
                from_dt = datetime.datetime.strptime(from_date, from_format)
            if from_timezone:
                from_tz = pytz.timezone(from_timezone)
                from_dt = from_tz.localize(from_dt)
            else:
                from_dt = pytz.utc.localize(from_dt)
        else:
            from_dt = pytz.utc.localize(datetime.datetime.utcnow())

        if timezone:
            to_tz = pytz.timezone(timezone)
        else:
            to_tz = pytz.utc

        to_dt = from_dt.astimezone(to_tz)

        date = [
            {
                'format': f,
                'date': to_dt.strftime(
                    # On Windows, '%s' is not supported, we thus need to
                    # patch it using the time module
                    f.replace('%s', str(int(time.time())))
                    if platform.system() == 'Windows'
                    else f
                ),
                'timezone': to_tz.zone,
            }
            for f in format
        ]
        if len(date) == 1:
            date = date[0]
        print(json.dumps(date, sort_keys=True,
                         indent=4, separators=(',', ': '),
                         ensure_ascii=False))
