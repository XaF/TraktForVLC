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
import requests

from helper.utils import (
    Command,
    CommandOutput,
)

LOGGER = logging.getLogger(__name__)


##########################################################################
# The REQUESTS command to perform HTTP/HTTPS requests
class CommandRequests(Command):
    command = 'requests'
    description = 'To perform HTTP/HTTPS requests'

    def add_arguments(self, parser):
        parser.add_argument(
            'method',
            help='The method to use for the request',
            type=str.upper,
            choices=[
                'GET',
                'POST',
            ],
        )
        parser.add_argument(
            'url',
            help='The URL to perform the request to',
        )
        parser.add_argument(
            '--headers',
            help='The headers to set for the request',
        )
        parser.add_argument(
            '--data',
            help='The data to be sent with the request',
        )

    def run(self, method, url, headers, data):
        if headers is None:
            headers = {}
        else:
            try:
                headers = {
                    k: str(v)
                    for k, v in json.loads(headers).items()
                }
            except Exception as e:
                raise RuntimeError(
                    'Headers argument could not be parsed as JSON: {}'.format(
                        e.message))

        ######################################################################
        # Prepare the parameters
        params = {
            'url': url,
            'headers': headers,
        }
        if data is not None:
            try:
                data = json.loads(data)
            except Exception as e:
                raise RuntimeError(
                    'Data argument could not be parsed as JSON: {}'.format(
                        e.message))
            params['json'] = data

        ######################################################################
        # Find the request method to use
        req_func = getattr(requests, method.lower(), None)
        if not req_func:
            raise RuntimeError('Function to perform HTTP/HTTPS request for '
                               'method {} not found'.format(method))

        ######################################################################
        # Perform the request
        resp = req_func(**params)

        ######################################################################
        # Prepare the result dict
        result = {
            'status_code': resp.status_code,
            'reason': resp.reason,
            'url': resp.url,
            'headers': dict(resp.headers),
            'body': resp.text,
            'request': {
                'url': resp.request.url,
                'method': resp.request.method,
                'headers': dict(resp.request.headers),
                'body': resp.request.body or '',
            },
        }
        try:
            result['json'] = resp.json()
        except Exception as e:
            pass

        ######################################################################
        # Return the result
        return CommandOutput(data=result)
