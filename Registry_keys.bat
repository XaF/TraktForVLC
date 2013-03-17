:: -----------------------------------------------------------------------------------
:: Title : Trakt for VLC batch file
:: Contact : wifsimster@gmail.com
:: Last update : 03/17/2013
:: Description : Edit registry keys for VLC. Add needed options to launch extraintf.
:: -----------------------------------------------------------------------------------
@echo off

:: ----------------------------------------------
:: You can edit these data as you want
set ip=192.168.137.1
set port=4222
set formats=avi, mkv, mov, mp4, wmv, ts, mpg
:: ----------------------------------------------

set vlcPath=C:\Program Files (x86)\VideoLAN\VLC\vlc.exe\
set vlcExtraIntf=--extraintf=rc --rc-host="%ip%":"%port%" --rc-quiet

echo ----------------------------------------------------------
echo -            TraktForVLC v0.1 by Wifsimster              -
echo -               last update : 03/16/2013                 -
echo -     Add config to all your vlc files for TraktForVLC   -
echo -          You can share and edit this script !          -
echo -             contact: wifsimster@gmail.com              -
echo ----------------------------------------------------------

echo VLC configuration : %ip%:%port%

echo Editing your registry keys for "%formats%"

FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\AddToPlaylistVLC\command" /ve /t REG_SZ /d "\"%vlcPath%" %vlcExtraIntf% --started-from-file --playlist-enqueue \"%%1\"" /f >NUL
FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\Open\command" /ve /t REG_SZ /d "\"%vlcPath%" %vlcExtraIntf% --started-from-file \"%%1\"" /f >NUL
FOR %%G IN (%formats%) DO REG ADD "HKCR\VLC.%%G\shell\PlayWithVLC\command" /ve /t REG_SZ /d "\"%vlcPath%" %vlcExtraIntf% --started-from-file --no-playlist-enqueue \"%%1\"" /f >NUL

echo Registry keys modified, thanks for using !

pause