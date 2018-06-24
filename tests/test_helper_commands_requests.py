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

import json
import mock
from testfixtures import LogCapture
import unittest

import context
import utils
import trakt_helper

from helper.utils import CommandOutput
from helper.commands.requests import CommandRequests


class TestHelperCommandRequests(utils._TestCase):

    def _test_req(self, params, mock_requests, json_except=False):
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 'STATUSCODE'
        mock_resp.reason = 'REASON'
        mock_resp.url = 'URL'
        mock_resp.headers = (('HEADER1', 'VALUE1'), ('HEADER2', 'VALUE2'))
        mock_resp.text = 'TEXT'
        mock_resp.request.url = 'REQ_URL'
        mock_resp.request.method = 'REQ_METHOD'
        mock_resp.request.headers = (('REQ_HEADER1', 'VALUE1'), )
        mock_resp.request.body = 'REQ_BODY'

        # If the json() method has to raise an exception
        if json_except:
            mock_resp.json.side_effect = utils.TestException('JSON')
        else:
            mock_resp.json.return_value = 'JSON'

        mock_requests.return_value = mock_resp

        command = CommandRequests()
        output = command.run(**params)

        req_params = {
            'headers': (
                json.loads(params['headers']) if params['headers']
                else {}
            ),
            'url': params['url'],
        }
        if params.get('data'):
            req_params['json'] = json.loads(params['data'])

        mock_requests.assert_called_once_with(**req_params)
        
        self.assertTrue(isinstance(output, CommandOutput),
                        'Output is not of type CommandOutput')

        expected = {
            'body': 'TEXT',
            'headers': {
                'HEADER1': 'VALUE1',
                'HEADER2': 'VALUE2',
            },
            'reason': 'REASON',
            'request': {
                'url': 'REQ_URL',
                'headers': {
                    'REQ_HEADER1': 'VALUE1',
                },
                'body': 'REQ_BODY',
                'method': 'REQ_METHOD'
            },
            'status_code': 'STATUSCODE',
            'url': 'URL',
        } 
        if not json_except:
            expected['json'] = 'JSON'
        self.assertDictEqual(expected, output.data)

    @mock.patch('requests.get')
    def test_command_requests_get(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': None,
        }
        self._test_req(params, mock_requests)

    @mock.patch('requests.post')
    def test_command_requests_post(self, mock_requests):
        params = {
            'method': 'POST',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': None,
        }
        self._test_req(params, mock_requests)

    @mock.patch('requests.get')
    def test_command_requests_headers(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': '{"a": "b", "c": "d"}',
            'data': None,
        }
        self._test_req(params, mock_requests)

    @mock.patch('requests.get')
    def test_command_requests_headers_not_json(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': '{}[]',
            'data': None,
        }

        with self.assertRaises(RuntimeError) as e:
            self._test_req(params, mock_requests)

        self.assertTrue(str(e.exception).startswith(
            'Headers argument could not be parsed as JSON'),
            'Bad exception: {}'.format(str(e.exception)))

    @mock.patch('requests.get')
    def test_command_requests_data(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': '{"a": "b", "c": "d"}',
        }
        self._test_req(params, mock_requests)

    @mock.patch('requests.get')
    def test_command_requests_data_not_json(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': '{}[]',
        }

        with self.assertRaises(RuntimeError) as e:
            self._test_req(params, mock_requests)

        self.assertTrue(str(e.exception).startswith(
            'Data argument could not be parsed as JSON'),
            'Bad exception: {}'.format(str(e.exception)))

    @mock.patch('requests.get')
    def test_command_requests_resp_not_json(self, mock_requests):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': None,
        }
        self._test_req(params, mock_requests, json_except=True)

    def test_command_requests_invalid_method(self):
        params = {
            'method': 'INVALID_METHOD',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': None,
        }

        with self.assertRaises(RuntimeError) as e:
            self._test_req(params, mock.MagicMock())

        self.assertEqual('Function to perform HTTP/HTTPS request for '
                         'method INVALID_METHOD not found',
                         str(e.exception))

    @mock.patch('sys.exit')
    @mock.patch('helper.commands.requests.CommandRequests.run')
    def test_trakt_helper_requests(self, mock_run, mock_exit):
        params = {
            'method': 'GET',
            'url': 'http://localhost/fake/',
            'headers': None,
            'data': None,
        }
        argv = ['requests', params['method'], params['url']]
        mock_run.return_value = CommandOutput(data='output')

        with mock.patch('__builtin__.print') as mock_print:
            trakt_helper.main(argv)

            mock_run.assert_called_with(**params)
            mock_exit.assert_called_with(0)

            mock_print.assert_called_once()
            mock_print.assert_called_with('"output"')


if __name__ == '__main__':
    unittest.main()
