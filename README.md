TraktForVLC [![Travis Build Status](https://travis-ci.org/XaF/TraktForVLC.svg?branch=master)](https://travis-ci.org/XaF/TraktForVLC) [![AppVeyor Build status](https://ci.appveyor.com/api/projects/status/e1ie51bwhbki60ns/branch/master?svg=true)](https://ci.appveyor.com/project/XaF/traktforvlc/branch/master)
===========

TraktForVLC allows scrobbling VLC content to [trakt.tv](https://trakt.tv/).

TraktForVLC 2.x works by using together a lua VLC module and a Python helper script in order to find information on the media you are watching.
Contrary to previous versions of TraktForVLC, the VLC module allows for a direct binding in your media activity (play, pause, stop) and thus to take immediate actions on your [trakt.tv](https://trakt.tv/) account.


## Table of Contents

* [Information](#information)
    * [Credits](#credits)
    * [License](#license)
    * [External libraries and resources](#external-libraries-and-resources)
* [Installation](#installation)
    * [Finding the installers](#finding-the-installers)
    * [Installation per OS](#installation-per-os)
    * [Initial configuration](#initial-configuration)
* [Configuration file](#configuration-file)
    * [Location](#location)
    * [Sections](#sections)
* [Issues](#issues)


## Information
### Credits

This version of TraktForVLC has been rewritten from scratch.

All licensing and used code is mentionned directly in the code source, except for the external libraries and resources information provided below.

### License

Copyright (C) 2017-2018  Raphaël Beamonte <<raphael.beamonte@gmail.com>>

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  [See the GNU General Public License for more details](https://www.gnu.org/licenses/gpl-2.0.html).

### External libraries and resources

The `vlc-logo-1s.mp4` file in this repository, also distributed in the binary files for Windows, contains a VLC logo that is not owned by this project. This logo is owned by its authors. VideoLAN can be reached on [their website](https://www.videolan.org/).

TraktForVLC uses external libraries and APIs for the media resolution:
* The [OpenSubtitles](https://www.opensubtitles.org/) API
* [The TVDB](https://www.thetvdb.com/) API (through the [tvdb_api](https://github.com/dbr/tvdb_api) Python package); TV information is provided by TheTVDB.com, but we are not endorsed or certified by TheTVDB.com or its affiliates.
* The [IMDB](https://www.imdb.com/) API (through the [imdbpie](https://pypi.python.org/pypi/imdbpie) Python package)
* The [TMDb](https://www.themoviedb.org/) API (through the [tmdbsimple](https://github.com/celiao/tmdbsimple) Python package); This product uses the TMDb API but is not endorsed or certified by TMDb.

TraktForVLC is not endorsed or certified by any of these external libraries and resources owners.


## Installation

### Finding the installers

Installers are provided in the [GitHub release section](https://github.com/XaF/TraktForVLC/releases).
The [latest release is available here](https://github.com/XaF/TraktForVLC/releases/tag/latest); however, we highly recommend using a stable release if you are not sure of what you are doing.

Once you have found the installer that corresponds to your operating system and downloaded it, simply running it will allow you to install TraktForVLC with the default parameters.

### Installation per OS

On Windows, you can right-click and run the file with the administrator privileges to start the install process. The administrator privileges are required as, on Windows, the Python helper is installed as a Windows service.

On Linux and MacOS, make the file executable (using `chmod +x file`) and then run it in the command line (`./TraktForVLC_version_os`).

### Initial configuration

At the end of the first installation, the initial configuration will automatically be started by the installer.
This process aims at authorizing TraktForVLC to access your [trakt.tv](https://trakt.tv/) account.

Depending on your OS, the process is presented a bit differently:
* On Linux and MacOS: a message giving instructions will appear directly at the end of the installation logs
* On Windows: a VLC window will be started and the screen will soon show a message giving instructions

The message shown should look like the following:
```
TraktForVLC is not setup with Trakt.tv yet!
--
PLEASE GO TO https://trakt.tv/activate
AND ENTER THE FOLLOWING CODE:
9EC4F248
```

The instructions are to go to a URL and enter a given code. Please do while keeping the process (VLC window on Windows) active, and wait after entering the code and validating the authorization that the process stops by itself.
If you stops the process before then, you will need to restart the initial configuration manually.

To restart the initial configuration process manually, the following command might be used: `./TraktForVLC_version_os init_trakt_auth`

## Configuration file

The configuration file for TraktForVLC is a JSON file named `trakt_config.json`.

### Location
The `trakt_config.json` file is located in your VLC configuration directory. Depending on your OS, the VLC configuration directory will be located at the following places:
* Linux: `~/.config/vlc`
* MacOS: `~/Library/Preferences/org.videolan.vlc`
* Windows: `%APPDATA%/vlc` (where `%APPDATA%` is the value of the `APPDATA` environment variable)

### Sections

* `config_version`: The version of TraktForVLC that generated the configuration file (present for retrocompatibility purposes)
* `cache`: Configuration relative to the media cache used by TraktForVLC
    * `delay`: The delays for operations performed on the media cache
        * `save`: Delay (in seconds) between save operations on the cache (default: `30`)
        * `cleanup`: Delay (in seconds) between cleanup operations on the cache (default: `60`)
        * `expire`: Time (in seconds) after which an unused entry in the cache expires (default: `2592000` - 30 days)
* `media`: Configuration relative to media resolution and scrobbling
    * `info`: Configuration relative to media resolution
        * `max_try`: Maximum number of times we will try to resolve the current watched item through IMDB (default: `10`)
        * `try_delay_factor`: Delay factor (in seconds) between try attempts; if `try_delay_factor` is `f` and attempt is `n`, next try will be after `n*f` seconds (default: `30`)
    * `start`: Configuration relative to media watching status
        * `time`: Time after which a media will be marked as being watched on [trakt.tv](https://trakt.tv/) (default: `30`)
        * `percent`: Percentage of the media watched after which the media will be marked as being watched on [trakt.tv](https://trakt.tv/) (default: `.25` - 0.25%)
        * `movie`: Whether or not to mark movies as being watched (default: `true`)
        * `episode`: Whether or not to mark episodes as being watched (default: `true`)
    * `stop`: Configuration relative to media scrobbling
        * `watched_percent`: The minimum watched percent for a media to be scrobbled as seen on [trakt.tv](https://trakt.tv); i.e. you must have watched at least that percentage of the media, for it to be scrobbled (default: `50`)
        * `percent`: The minimum percentage of the media duration at which you must currently be for the media to be scrobbled as seen (if the media has a duration of `100mn`, and you configured the `percent` as `90`, you must at least be at the `90th` minute of the media) (default: `90`)
        * `movie`: Whether or not to scrobble movies as watched (default: `true`)
        * `episode`: Whether or not to scrobble episodes as watched (default: `true`)
        * `check_unprocessed_delay`: Delay (in seconds) between checks for medias that should be scrobbled as watched but have not been for any reason (no internet connection, media not identified yet, etc.) (default: `120`)
        * `delay`: Delay (in seconds) between scrobbles for a given media (any subsequent scrobble in the given delay will be ignored) (default: `1200` - 20 minutes)
* `helper`: Configuration relative to the helper tool
    * `mode`: The mode of the helper. Can be one of `standalone` or `service` (default: `standalone`)
    * `service`: The service configuration, when the helper is installed as a service
        * `host`: The host on which the service is listening (default: `localhost`)
        * `port`: The port on which the service is listening (default: `1984`)
    * `update`: To configure the automatic updates for TraktForVLC
        * `check_delay`: Delay (in seconds) in between checks for new updates, disabled if set to `0` (default: `86400` - 24 hours)
        * `release_type`: The type of releases to look for. Can be one of `stable`, `rc`, `beta`, `alpha` or `latest` (default: `stable`)
        * `action`: The action to perform automatically when a new release is found. Can be one of `install`, `download` or `check` (default: `install`)


## Issues
Please use the [GitHub integrated issue tracker](https://github.com/XaF/TraktForVLC/issues) for every problem you can encounter. Please **DO NOT** use my email for issues or walkthrough.

When submitting an issue, please submit a VLC logfile showing the error. You can start VLC in debug mode (`--vv` option) to obtain more thorough logs.

> **Please** be careful to remove any personnal information that might still be in the logfile (password, identification token, ...) before putting your file online.
