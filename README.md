TraktForVLC
===========

## Presentation

TraktForVLC allows scrobbling [VLC] content to [trakt.tv] [1].
Since there is no way for VLC to directly know if you are watching
a TV show or a Movie, this script will attempt to figure it out
using the name of the video and its lenght. It is therefore possible
that the script can't find what you're watching if your files are
not named properly.


## Information
### Credits

The TraktForVLC script is originally based off of [TraktForBoxee] [2]
and works very similarily to it.

This version of the script is forked from [Wifsimster's TraktForVLC] [3],
itself based on the original [quietcore's TraktForVLC] [4].

### Licence

Copyright (C) 2012      quietcore

Copyright (C) 2013      Wifsimster

Copyright (C) 2014      Raphaël Beamonte

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  [See the
GNU General Public License for more details] [GPLv2].


## Installation
### Compatibility
#### Operating System
As I'm a fervent [Linux] [5] user, this version of the script
has only been used and tested on Linux [Debian] [6]. I will
not be able to maintain directly the [Windows] [7] compatibility
but I'm open to pull requests on this side, as we're here to
share.

#### Python version
This version of TraktForVLC has been tested using Python 2.7.7

### Getting sources
To get the sources, you only need to clone the repository using
the following command on Linux:

```sh
git clone https://github.com/XaF/TraktForVLC.git
```

On [Windows] [7], you can download the [last version of the ZIP package] [8].

### Configuring VLC
#### With VLC Settings
Go to:
+ **Tools**
+ then **Preferences**

In the preferences window that just opened, look at the bottom
left and check **All**.

Then, in the menu that appeared in place of the icons on the
left, go to:
+ **Interface**
+ **Main interfaces**

Here, in the list of **Extra interface modules**, check **Telnet**
and **Remote control interface**.

Then, go to:
+ **RC** (submenu of **Main interfaces**)

And in the line **TCP command input** insert *localhost:4222* (you
can adjust the host and port if you want, but you'll have to keep
it in mind for the next steps).

On [Windows] [7], you will also find a checkbox **Do not open a DOS
command box interface** that you should check if you don't want
to see a console each time you start VLC.

#### With command line
Instead of configuring [VLC], you can use parameters in your VLC
command line to start the remote control server. The following line
can be use either way on [Linux] [5] or [Windows] [7] by adjusting
the `vlc` at start by the path to your [VLC] executable (usually
`vlc.exe` on Windows).

```sh
vlc --extraintf=rc --rc-host=localhost:4222 --rc-quiet
```

### Configuring TraktForVLC

TraktForVLC needs its `config.ini` file to work properly. The content
of the file is as follow:

```yaml
[VLC]
IP = localhost              # The host of the VLC Remote Control server
Port = 4222                 # The port of the VLC Remote Control server
```

This is the general server configuration. You should put here the same
information you used in your configuration of VLC to allow TraktForVLC
to connect to your VLC instance.

```yaml
[Trakt]
Username = [username]       # Your trakt.tv username
Password = [password]       # Your trakt.tv password
```

This is your personnal [trakt.tv] [1] credentials. You should be careful
not to share them with anybody, but they're necessary here to connect to
your account, update your current watching and scrobble when necessary.

```yaml
[TraktForVLC]
Timer = 60                  # Time (sec) between each loop and look of TraktForVLC
StartWatching = 30          # Time (sec) before considering a video is currently watched
ScrobbleMovie = Yes         # Whether or not TraktForVLC will automatically scrobble movies
ScrobbleTV = Yes            # Whether or not TraktForVLC will automatically scrobble tv shows
```
This is the script-specific configuration, the time between each loop of
work, the time before considering you're effectively watching a video, and
whether or not scrobble automatically what you're watching on [trakt.tv] [1].

### Automatic start
This script needs to be kept alive, and to be working when you start watching
something. Achieving this need is very different if you're on [Linux] [5] or
[Windows] [7]. This part aims to guide you to do these steps.

#### On Linux
There is different way to realize what we want to do on Linux. I'll just give
here two different and simple ways as reference.

##### Using Gnome
Go to your **Startup Applications Preferences**, then click on the **Add** button.
Here, you can give the name you want to your task, and you only need to add the
following line in the **Command** box:
```sh
path/to/your/TraktForVLC.py --daemon
```

Your task will then automatically be started with your session.

##### Using .bashrc
If you want to start Trakt automatically with your session but don't want to use
Gnome's **Startup Applications Preferences**, you can add the line proposed below
directly in your `.bashrc` script.

#### On Windows
##### Using scheduled tasks
A `start_process.bat` file is joined to the source files of TraktForVLC. You need to
edit it to reflect the data and configuration directory of your TraktForVLC
installation, then you can add this program as a scheduled task that starts when you
open your session.

### Issues
Please use the [GitHub integrated issue tracker] [9] for every problem you can
encounter. Please **DO NOT** use my email for issues or walkthrough.



[1]: https://trakt.tv/
[2]: https://github.com/cold12/Trakt-for-Boxee
[3]: https://github.com/Wifsimster/TraktForVLC
[4]: https://github.com/quietcore/TraktForVLC
[5]: https://www.kernel.org/
[6]: https://www.debian.org/
[7]: http://windows.microsoft.com
[8]: https://github.com/XaF/TraktForVLC/archive/master.zip
[9]: https://github.com/XaF/TraktForVLC/issues
[VLC]: https://videolan.org/
[GPLv2]: https://www.gnu.org/licenses/gpl-2.0.html
