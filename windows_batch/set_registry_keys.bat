:: TraktForVLC, to link VLC watching to trakt.tv updating
::
:: Edit registry keys for VLC. Add needed options to launch extraintf.
::
:: Copyright (C) 2013      Damien Battistella <wifsimster@gmail.com>
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

@echo off

:: Change current directory to the directory where we have out batch file
cd %~dp0

:: Load configuration file for the path needed
call config.bat

echo ----------------------------------------------------------
echo -     Add config to all your vlc files for TraktForVLC   -
echo ----------------------------------------------------------

echo VLC configuration : %ip%:%port%

echo Editing your registry keys for formats "%vlc_formats%"

FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\AddToPlaylistVLC\command" /ve /t REG_SZ /d "\"%vlc_path%" %vlc_opts% --started-from-file --playlist-enqueue \"%%1\"" /f >NUL
FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\Open\command" /ve /t REG_SZ /d "\"%vlc_path%" %vlc_opts% --started-from-file \"%%1\"" /f >NUL
FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\PlayWithVLC\command" /ve /t REG_SZ /d "\"%vlc_path%" %vlc_opts% --started-from-file --no-playlist-enqueue \"%%1\"" /f >NUL

echo Registry keys modified, thanks for using !

pause
