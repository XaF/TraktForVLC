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
import logging
import platform
import shlex
import socket

from helper.parser import (
    parse_args,
)
from helper.utils import (
    Command,
    redirectstd,
)

if platform.system() == 'Windows':
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

LOGGER = logging.getLogger(__name__)


##########################################################################
# The SERVICE command to start the TraktForVLC helper as a service that
# allows for requests and replies through TCP
class CommandService(Command):
    command = 'service'
    description = 'Start the TraktForVLC helper as a service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            help='Host to bind to [default: 127.0.0.1]',
            default='localhost',
        )
        parser.add_argument(
            '--port',
            type=int,
            help='Port to bind to [default: 1984]',
            default=1984,
        )
        if platform.system() == 'Windows':
            parser.add_argument(
                'action',
                nargs='?',
                type=str.lower,
                choices=[
                    'install',
                    'update',
                    'remove',
                    'start',
                    'restart',
                    'stop',
                    'debug',
                    'standalone',
                ],
            )

    def run(self, host, port, action=None):
        if platform.system() == 'Windows' and action != 'standalone':
            return run_windows_service(action=action, host=host, port=port)
        else:
            return run_service(host=host, port=port)


##############################################################################
# Function called to run the Windows service, this can be used to install as
# well as to manage the service
def run_windows_service(action, host=None, port=None, exeName=None):
    # Prepare the arguments that are going to be used with the service
    # command line
    args = ['TraktForVLC', ]
    if action == 'install':
        args.extend(['--startup', 'auto'])
    if action is not None:
        args.append(action)

    # Prepare the args that will be passed to the service executable
    exe_args = [
        'service',
    ]
    if host is not None:
        exe_args.append('--host={}'.format(host))
    if port is not None:
        exe_args.append('--port={}'.format(port))

    # Prepare the class that represents the Windows Service
    class TraktForVLCWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = 'TraktForVLC'
        _svc_display_name_ = 'TraktForVLC'
        _svc_description_ = 'TraktForVLC helper tool'
        _exe_name_ = exeName
        _exe_args_ = ' '.join(exe_args)

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            rc = None  # noqa: F841

            def stop_condition():
                rc = win32event.WaitForSingleObject(self.hWaitStop, 0)
                return rc == win32event.WAIT_OBJECT_0

            try:
                run_service(host, port, stop_condition=stop_condition)
            except Exception as e:
                LOGGER.exception(e)
                raise

    if len(args) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TraktForVLCWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TraktForVLCWindowsService,
                                           argv=args)


##############################################################################
# Function called to run the actual service that will listen and reply to
# commands
def run_service(host, port, stop_condition=lambda: False):
    # Create the TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind it to the host and port
    LOGGER.info('Starting server on {} port {}'.format(host, port))
    sock.bind((host, port))

    try:
        # Put the socket in server mode
        sock.listen(1)

        # Process connections
        while not stop_condition():
            # Wait for a connection to be opened
            LOGGER.debug('Waiting for a connection')
            try:
                sock.settimeout(5)
                conn, client = sock.accept()
            except socket.timeout:
                # If the wait times out, just start waiting again
                continue

            # Now the connection is established, do something
            try:
                LOGGER.info('Connection from {}'.format(client))

                req = io.BytesIO()
                req_ready = False
                while not req_ready:
                    conn.settimeout(15.0)
                    data = conn.recv(2048)
                    print('Received "{}"'.format(data))
                    if not data:
                        print('No more data')
                        break
                    else:
                        if '\n' in data:
                            data = data.splitlines()[0]
                            req_ready = True
                        req.write(data)

                LOGGER.debug('Request: {}'.format(req.getvalue()))

                output = io.BytesIO()
                exit = 0
                try:
                    with redirectstd(output):
                        args, action, params = parse_args(
                            args=shlex.split(req.getvalue()))

                        action_exit = action(**params)
                        if action_exit is not None:
                            exit = action_exit
                except SystemExit as e:
                    exit = e
                except Exception as e:
                    LOGGER.error(e, exc_info=True)
                    exit = -1
                finally:
                    conn.sendall('Exit: {}\n'.format(exit))
                    conn.sendall(output.getvalue())
                    LOGGER.debug('Sent: Exit {}\n{}'.format(
                        exit, output.getvalue()))
            except socket.timeout:
                LOGGER.info('Connection with {} timed out'.format(client))
                continue
            except socket.error as e:
                LOGGER.info('Connection with {} ended in error: {}'.format(
                    client, e))
                continue
            finally:
                # Clean up the client connection
                conn.close()
    except Exception as e:
        LOGGER.exception(e)
        raise
    finally:
        sock.close()

    LOGGER.info('Stopping.')
