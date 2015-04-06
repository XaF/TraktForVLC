:: TraktForVLC, to link VLC watching to trakt.tv updating
::
:: Start TraktForVLC, you can use this batch as a schedule task on Windows
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

:: Change current directory to the directory where we have out batch file
cd /D %~dp0

:: Load configuration file for the path needed
call ".\config.bat"

:: Please change the values of the variables directly in config.bat
start "TraktForVLC" %python% %tfv_py% --datadir %tfv_data% --config %tfv_config% --pidfile %tfv_pidfile% --debug --small-timers
