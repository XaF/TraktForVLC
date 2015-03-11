:: TraktForVLC, to link VLC watching to trakt.tv updating
::
:: Config file for the TraktForVLC batch script
::
:: Copyright (C) 2015      Raphaël Beamonte <raphael.beamonte@gmail.com>
::
:: This file is part of TraktForVLC.  TraktForVLC is free software: you can
:: redistribute it and/or modify it under the terms of the GNU General Public
:: License as published by the Free Software Foundation, version 2.
::
:: This program is distributed in the hope that it will be useful, but WITHOUT
:: ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
:: FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
:: details.
::
:: You should have received a copy of the GNU General Public License
:: along with this program; if not, write to the Free Software Foundation,
:: Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
:: or see <http://www.gnu.org/licenses/>.

:::: Configuration to start TraktForVLC properly
:: Set the full path to the python exe file on your computer
set python=C:\pythonw.exe

:: Set the path to the TraktForVLC.py file on your computer
set tfv_py=C:\your\path\to\TraktForVLC\TraktForVLC.py

:: Set the path to the directory in which you want to store TraktForVLC
:: data. By default, it is the directory in which TraktForVLC.py is.
set tfv_data=C:\your\path\to\TraktForVLC\data\directory\

:: Set the path to the directory in which the TraktForVLC config file
:: is. By default, it is the directory in which TraktForVLC.py is.
set tfv_config=C:\your\path\to\TraktForVLC\config\directory\

:: Set the path to the file in which we will store the processus ID to
:: allow you to stop the process if needed
set tfv_pidfile=C:\your\path\to\TraktForVLC\TraktForVLC.pid


:::: Configuration to set the registry keys
:: Set the full path to the VLC exe file on your computer
set vlc_path=C:\your\path\to\VideoLAN\VLC\vlc.exe

:: Set the IP address VLC will listen to (default: localhost)
set ip=localhost

:: Set the port VLC will listen to (default: 4222)
set port=4222

:: Set the file formats for which you want VLC to be start
:: listening to remote control for TraktForVLC to work. You
:: can add as much format as you want, all format must be
:: separated by a coma.
set formats=avi, mkv, mov, mp4, wmv, ts, mpg

:: Set the options you want to start VLC with. You should at least let
:: the default for remote control (--extraintf=rc --rc-host=ip:port
:: --rc-quiet)
set vlc_opts=--extraintf=rc --rc-host="%ip%":"%port%" --rc-quiet
