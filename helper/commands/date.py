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
import logging
import pytz

from helper.utils import (
    Command,
    CommandOutput,
)

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
        # Set the default values
        if not format:
            format = ['%Y-%m-%dT%H:%M:%S.%fZ', ]
        if not timezone:
            timezone = 'UTC'
        if not from_timezone:
            from_timezone = 'UTC'

        # Prepare the origin and destination timezones
        from_tz = pytz.timezone(from_timezone)
        to_tz = pytz.timezone(timezone)

        # Parse the origin date
        if from_date:
            if from_format in ['%s', '%s.%f']:
                from_date = float(from_date)
                from_dt = datetime.datetime.fromtimestamp(from_date, from_tz)
            else:
                from_dt = from_tz.localize(
                    datetime.datetime.strptime(from_date, from_format))
        else:
            from_dt = pytz.utc.localize(datetime.datetime.utcnow())

        # Convert from the original timezone to the destination timezone
        to_dt = from_dt.astimezone(to_tz)

        # Python's datetime strftime does not support '%s' to compute
        # the epoch, so we're doing it manually
        epoch = (to_dt - datetime.datetime(
            1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

        # Prepare the output message
        date = [
            {
                'format': f,
                'date': to_dt.strftime(
                    f.replace('%s', str(int(epoch)))
                ),
                'timezone': to_tz.zone,
            }
            for f in format
        ]

        # If there is only one result, return it as an object and not a list
        if len(date) == 1:
            date = date[0]

        return CommandOutput(data=date)
