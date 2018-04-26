--[==========================================================================[
 trakt.lua: Trakt.tv Interface for VLC
--[==========================================================================[
 TraktForVLC, to link VLC watching to trakt.tv updating

 Copyright (C) 2017-2018   Raphaël Beamonte <raphael.beamonte@gmail.com>
 $Id$

 This file is part of TraktForVLC.  TraktForVLC is free software:
 you can redistribute it and/or modify it under the terms of the GNU
 General Public License as published by the Free Software Foundation,
 version 2.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software Foundation,
 Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
 or see <http://www.gnu.org/licenses/>.
--]==========================================================================]

-- TraktForVLC version
local __version__ = '0.0.0a0.dev0'

-- The location of the helper`
local path_to_helper

------------------------------------------------------------------------------
-- Local modules
------------------------------------------------------------------------------
-- The variable that will store the ospath module
local ospath = {}
-- The variable that will store the requests module
local requests = {}
-- The variable that will store the timers module
local timers = {}
-- The variable that will store the trakt module
local trakt = {}
-- The variable that will store the file module
local file = {}

------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- LOAD DEPENDENCIES                                                        --
------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- To work with JSON data
local json = require('dkjson')
-- To do math operations
local math = require('math')

------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- OSPATH MODULE TO PERFORM OPERATIONS ON PATHS                             --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
-- The default separator for the current file system
ospath.sep = package.config:sub(1,1)

------------------------------------------------------------------------------
-- Function to return the path to the current lua script, this will not work
-- on all cases as some instances of VLC only return  the script's name
------------------------------------------------------------------------------
function ospath.this()
    return debug.getinfo(2, "S").source:sub(2)
end


------------------------------------------------------------------------------
-- Function to check if a path exists
------------------------------------------------------------------------------
function ospath.exists(path)
    if type(path) ~= "string" then return false end
    local ok, err, code = os.rename(path, path)
    if not ok then
        if code == 13 then
            return true
        end
    end
    return ok, err
end


------------------------------------------------------------------------------
-- Function to check if a path is a file
------------------------------------------------------------------------------
function ospath.isfile(path)
    if type(path) ~= "string" then return false end
    if not ospath.exists(path) then return false end
    local f = io.open(path)
    if f then
        local ff = f:read(1)
        f:close()
        if not ff then
            return false
        end
        return true
    end
    return false
end


------------------------------------------------------------------------------
-- Function to check if a path is a directory
------------------------------------------------------------------------------
function ospath.isdir(path)
    return (ospath.exists(path) and not ospath.isfile(path))
end


------------------------------------------------------------------------------
-- Function to get the directory name from a path
------------------------------------------------------------------------------
function ospath.dirname(path)
    local d = path:match("^(.*)" .. ospath.sep .. "[^" .. ospath.sep .. "]*$")
    if not d or d == '' then
        return path
    end
    return d
end


------------------------------------------------------------------------------
-- Function to get the base name from a path
------------------------------------------------------------------------------
function ospath.basename(path)
    local b = path:match("^.*" .. ospath.sep ..
                         "([^" .. ospath.sep .. "]*)" ..
                         ospath.sep .. "?$")
    if not b or b == '' then
        return path
    end
    return b
end


------------------------------------------------------------------------------
-- Function to join multiple elements using the file system's separator
------------------------------------------------------------------------------
function ospath.join(...)
    local arg
    if type(...) == 'table' then
        arg = ...
    else
        arg = {...}
    end
    local path
    for _, p in pairs(arg) do
        if not path or p.sub(1, 1) == ospath.sep then
            path = p
        else
            if string.sub(path, -string.len(ospath.sep)) ~= ospath.sep then
                path = path .. ospath.sep
            end
            path = path .. p
        end
    end
    return path
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS THAT ARE PROVIDING UTILITIES FOR THE REST OF THIS INTERFACE    --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Sleeps for a given duration (in microseconds)
-- @param microseconds The duration in microseconds
------------------------------------------------------------------------------
local
function usleep(microseconds)
    vlc.misc.mwait(vlc.misc.mdate() + microseconds)
end


------------------------------------------------------------------------------
-- Sleeps for a given duration (in seconds)
-- @param seconds The duration in seconds
------------------------------------------------------------------------------
local
function sleep(seconds)
    usleep(seconds * 1000000)
end


------------------------------------------------------------------------------
-- Repeat a function every delay for a duration
-- @param delay The delay (in microseconds)
-- @param duration The duration (in microseconds)
-- @param func The function to execute
------------------------------------------------------------------------------
local
function ucallrepeat(delay, duration, func)
    local repeat_until = vlc.misc.mdate() + duration
    while vlc.misc.mdate() < repeat_until do
        local ret = func()
        if ret ~= nil then return ret end
        vlc.misc.mwait(vlc.misc.mdate() + delay)
    end
end


------------------------------------------------------------------------------
-- Repeat a function every delay for a duration
-- @param delay The delay (in seconds)
-- @param duration The duration (in seconds)
-- @param func The function to execute
------------------------------------------------------------------------------
local
function callrepeat(delay, duration, func)
    return ucallrepeat(delay * 1000000, duration * 1000000, func)
end


------------------------------------------------------------------------------
-- Dumps the object passed as argument recursively and returns a string that
-- can then be printed.
-- @param o The object to dump
-- @param lvl The current level of indentation
------------------------------------------------------------------------------
local dump_func_path = {}
local
function dump(o,lvl)
    local lvl = lvl or 0
    local indent = ''
    for i=1,lvl do indent = indent .. '\t' end

    if type(o) == 'table' then
        local s = '{\n'
        for k,v in pairs(o) do
            if type(k) == 'function' then
                if not dump_func_path[k] then
                    finf = debug.getinfo(k)
                    dump_func_path[k] = string.gsub(
                        finf['source'], "(.*/)(.*)", "%2") ..
                        ':' .. finf['linedefined']
                end
                k = '"' .. dump_func_path[k] .. '"'
            elseif type(k) ~= 'number' then
                k = '"' .. k .. '"'
            end
            s = s .. indent .. '\t[' .. k .. '] = ' ..
                dump(v, lvl+1) .. ',\n'
        end
        return s .. indent .. '}'
    elseif type(o) == 'string' then
        return '"' .. o .. '"'
    else
        return tostring(o)
    end
end


-- Taken from https://stackoverflow.com/questions/20325332/how-to-check-if-
-- two-tablesobjects-have-the-same-value-in-lua
------------------------------------------------------------------------------
-- Performs a deep comparison that can be applied on tables
-- @param o1 The first object to compare
-- @param o2 The second object to compare
-- @param ignore_mt Whether or not to ignore the built-in equal method
------------------------------------------------------------------------------
local
function equals(o1, o2, ignore_mt)
    if o1 == o2 then return true end
    local o1Type = type(o1)
    local o2Type = type(o2)
    if o1Type ~= o2Type then return false end
    if o1Type ~= 'table' then return false end

    if not ignore_mt then
        local mt1 = getmetatable(o1)
        if mt1 and mt1.__eq then
            --compare using built in method
            return o1 == o2
        end
    end

    local keySet = {}

    for key1, value1 in pairs(o1) do
        local value2 = o2[key1]
        if value2 == nil or equals(value1, value2, ignore_mt) == false then
            return false
        end
        keySet[key1] = true
    end

    for key2, _ in pairs(o2) do
        if not keySet[key2] then return false end
    end
    return true
end


-- Taken from http://trac.opensubtitles.org/projects/opensubtitles/wiki/
-- HashSourceCodes#Lua
------------------------------------------------------------------------------
-- Allows to get the hash that can then be used on opensubtitles to perform a
-- research for the file information
-- @param fileName The path to the filename for which to compute the hash
------------------------------------------------------------------------------
local
function movieHash(fileName)
    local fil = assert(io.open(fileName, 'rb'))
    local lo, hi = 0, 0
    for i = 1, 8192 do
        local a, b, c, d = fil:read(4):byte(1, 4)
        lo = lo + a + b * 256 + c * 65536 + d * 16777216
        a, b, c, d = fil:read(4):byte(1, 4)
        hi = hi + a + b * 256 + c * 65536 + d * 16777216
        while lo >= 4294967296 do
            lo = lo - 4294967296
            hi = hi + 1
        end
        while hi >= 4294967296 do
            hi = hi - 4294967296
        end
    end
    local size = fil:seek('end', -65536) + 65536
    for i=1,8192 do
        local a, b, c, d = fil:read(4):byte(1, 4)
        lo = lo + a + b * 256 + c * 65536 + d * 16777216
        a, b, c, d = fil:read(4):byte(1, 4)
        hi = hi + a + b * 256 + c * 65536 + d * 16777216
        while lo >= 4294967296 do
            lo = lo - 4294967296
            hi = hi + 1
        end
        while hi >= 4294967296 do
            hi = hi - 4294967296
        end
    end
    lo = lo + size
        while lo >= 4294967296 do
            lo = lo - 4294967296
            hi = hi + 1
        end
        while hi >= 4294967296 do
            hi = hi - 4294967296
        end
    fil:close()
    return string.format('%08x%08x', hi, lo), size
end


-- Taken from https://stackoverflow.com/questions/11163748/open-web-browser-
-- using-lua-in-a-vlc-extension
------------------------------------------------------------------------------
-- Open an URL in the client browser
-- @param url The URL to open
------------------------------------------------------------------------------
local open_cmd
local
function open_url(url)
    if not open_cmd then
        if package.config:sub(1,1) == '\\' then -- windows
            open_cmd = function(url)
                -- Should work on anything since (and including) win'95
                os.execute(string.format('start "%s"', url))
            end
        -- the only systems left should understand uname...
        elseif (io.popen("uname -s"):read'*a') == "Darwin" then -- OSX/Darwin ? (I can not test.)
            open_cmd = function(url)
                -- I cannot test, but this should work on modern Macs.
                os.execute(string.format('open "%s"', url))
            end
        else -- that ought to only leave Linux
            open_cmd = function(url)
                -- should work on X-based distros.
                os.execute(string.format('xdg-open "%s"', url))
            end
        end
    end

    open_cmd(url)
end


------------------------------------------------------------------------------
-- Function to get the path to the helper if not provided
------------------------------------------------------------------------------
function get_helper()
    local search_in = {}
    local trakt_helper

    -- Check first if we don't have any configuration value telling us where
    -- the helper is located
    local cfg_location = {}

    -- Or as an environment variable
    if os.getenv('TRAKT_HELPER') and os.getenv('TRAKT_HELPER') ~= '' then
        table.insert(cfg_location, os.getenv('TRAKT_HELPER'))
    end

    -- Or, most common way, in the module's configuration
    if trakt.config and
            trakt.config.helper and
            trakt.config.helper.location and
            trakt.config.helper.location ~= '' then
        table.insert(cfg_location, trakt.config.helper.location)
    end

    -- If we have any of those indication, try to use it
    for _, v in pairs(cfg_location) do
        if v then
            if v == '~' or string.sub(v, 1, 2) == '~/' then
                v = ospath.join(vlc.config.homedir(),
                                string.sub(v, 3))
            elseif os.getenv('PWD') and (
                    (ospath.sep == '/' and
                     string.sub(v, 1, 1) ~= '/') or
                    (ospath.sep == '\\' and
                     not string.match(v, '^[a-zA-Z]:\\'))) then
                v = ospath.join(os.getenv('PWD'), v)
            end
            if not ospath.exists(v) then
                vlc.msg.err('File not found: ' .. v)
                return
            elseif ospath.isdir(v) then
                table.insert(search_in, v)
                break
            else
                trakt_helper = v
                break
            end
        end
    end

    -- Else, fall back on searching manually, first in VLC's
    -- config directory for any local install, else on the
    -- lua directory if we got enough information to do it
    if not trakt_helper then
        for _, dir in ipairs(vlc.config.datadir_list('')) do
            table.insert(search_in, dir)
        end

        local files = {
            'trakt_helper',
            'trakt_helper.exe',
            'trakt_helper.py',
        }
        for _, d in pairs(search_in) do
            for _, f in pairs(files) do
                fp = ospath.join(d, f)
                if ospath.isfile(fp) then
                    return fp
                end
            end
        end
    end
    return trakt_helper
end


------------------------------------------------------------------------------
-- Function to facilitate the calls to perform to the helper
-- @param args The command line arguments to be sent to the helper
------------------------------------------------------------------------------
local
function call_helper(args, discard_stderr)
    if trakt.config.helper.mode ~= 'service' then
        -- Add the helper path to the beginning of the args
        table.insert(args, 1, path_to_helper)
    end

    -- Escape the arguments
    for k, v in pairs(args) do
        v = v:gsub('\\"', '\\\\\\"')
        v = v:gsub('"', '\\"')
        v = '"' .. v .. '"'
        args[k] = v
    end

    -- Concatenate them to generate the command
    local command = table.concat(args, ' ')
    vlc.msg.dbg('(call_helper) Executing command: ' .. command)

    local response
    local exit_code
    if trakt.config.helper.mode == 'service' then
        local maxtry = 1
        local try = 0
        while try < maxtry do
            try = try + 1
            local sent = -2
            local fd = vlc.net.connect_tcp(trakt.config.helper.service.host,
                                           trakt.config.helper.service.port)
            if fd then
                sent = vlc.net.send(fd, command .. '\n')
            end

            if not fd then
                vlc.msg.err('Unable to connect to helper on ' ..
                            trakt.config.helper.service.host .. ':' ..
                            trakt.config.helper.service.port)
            elseif sent < 0 then
                vlc.msg.err('Unable to send request to helper on ' ..
                            trakt.config.helper.service.host .. ':' ..
                            trakt.config.helper.service.port)
                vlc.net.close(fd)
            else
                local pollfds = {
                    [fd] = vlc.net.POLLIN,
                }
                vlc.net.poll(pollfds)

                response = ""
                local buf = vlc.net.recv(fd, 2048)

                -- Get the rest of the message
                while buf and #buf > 0 do
                    vlc.msg.dbg('Reading buffer; content = ' .. buf)
                    response = response .. buf

                    vlc.net.poll(pollfds)
                    buf = vlc.net.recv(fd, 2048)
                end

                -- Close the connection
                vlc.net.close(fd)

                -- Try and get the exit code
                vlc.msg.dbg('Received data before parsing = ' .. response)
                exit_code, response = response:match('^Exit: (-?[0-9]+)\n(.*)')
                if exit_code ~= nil then
                    vlc.msg.dbg('Parsed EXIT_CODE = ' .. exit_code)
                    vlc.msg.dbg('Parsed RESPONSE = ' .. response)
                    exit_code = tonumber(exit_code)
                    break
                end
            end
        end

        if not response then
            vlc.msg.err('Unable to get command output')
            return nil
        end
    elseif ospath.sep == '\\' then
        vlc.msg.err('Only the service mode is available on Windows. ' ..
                    'Standalone mode pops up a window every few ' ..
                    'seconds... Who would have thought \'Windows\' ' ..
                    'was so literal?! ;(')
        return nil
    else
        if not discard_stderr then
            command = command .. ' 2>&1'
        end

        -- Run the command, and get the output
        local fpipe = assert(io.popen(command, 'r'))
        response = assert(fpipe:read('*a'))
        local closed, exit_reason, exit_code = fpipe:close()
        -- Lua 5.1 do not manage properly exit codes when using io.popen,
        -- so if we are using Lua 5.1, or if the exit code is 'nil', we
        -- will skip that step of checking the exit code. In any case,
        -- if there was an issue, the json parsing will fail and we will
        -- be able to catch that error
        if _VERSION == 'Lua 5.1' then
            exit_code = nil
        end
    end

    if exit_code ~= nil and exit_code ~= 0 then
        -- We got a problem...
        vlc.msg.err('(call_helper) Command: ' .. command)
        vlc.msg.err('(call_helper) Command exited with code ' .. tostring(exit_code))
        vlc.msg.err('(call_helper) Command output: ' .. response)
        return nil
    end

    vlc.msg.dbg('(call_helper) Received response: ' .. tostring(response))

    -- Decode the JSON returned as response, and check for errors
    local obj, pos, err = json.decode(response)
    if err then
        vlc.msg.err('(call_helper) Command: ' .. command)
        vlc.msg.err('(call_helper) Unable to parse json')
        vlc.msg.err('(call_helper) Command output: ' .. response)
        return nil
    end

    -- Return the response object
    return obj
end


------------------------------------------------------------------------------
-- Function to merge a number of intervals provided in the parameter, in order
-- to get the lowest number of internals that cover the same area as all the
-- previous intervals
------------------------------------------------------------------------------
local
function merge_intervals(data)
    -- Sort the data
    table.sort(
        data,
        function(a, b)
            return (a.from < b.from or
                    (a.from == b.from and a.to < b.to))
        end
    )

    -- Prepare local variables
    local merged = {}
    local current = nil

    -- Go through the intervals to merge them together
    for k, intv in pairs(data) do
        if current and intv.from <= current.to then
            current.to = math.max(intv.to, current.to)
        else
            if current then
                table.insert(merged, current)
            end
            current = intv
        end
    end

    -- If we have a current data, merge it
    if current then
        table.insert(merged, current)
    end

    -- Return the merged intervals
    return merged
end


------------------------------------------------------------------------------
-- Function that sums the data represented in form of intervals; the sum
-- represents the total area covered by the entirety of the intervals
------------------------------------------------------------------------------
local
function sum_intervals(data)
    local sum = 0

    for k, intv in pairs(data) do
        sum = sum + (intv.to - intv.from)
    end

    return sum
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS PROVIDING TIMER FACILITIES                                     --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
-- The table containing the registered timers
timers._registered = {}


------------------------------------------------------------------------------
-- To register a timer
-- @param func The function to run
-- @param delay The delay to run that function
------------------------------------------------------------------------------
function timers.register(func, delay, expire)
    -- If delay is nil, unregister the timer
    if delay == nil then
        timers._registered[func] = nil
        return
    end

    timers._registered[func] = {
        ['delay'] = delay,
        ['last'] = -1,
        ['expire'] = expire,
    }
end


------------------------------------------------------------------------------
-- To run the timers that need to be run, will return the list of timers with
-- 'true' or 'false' as value whether or not they have been run
------------------------------------------------------------------------------
function timers.run()
    ran_timers = {}
    cur_time = vlc.misc.mdate()
    for f, d in pairs(timers._registered) do
        -- If the timer expired, remove it
        if d['expire'] and d['expire'] < cur_time then
            timers._registered[f] = nil

        -- If we haven't passed the delay to run the timer, don't run it
        elseif d['last'] + d['delay'] > cur_time then
            ran_timers[f] = false

        -- Else, we can run the timer and update the information
        else
            f()
            timers._registered[f]['last'] = cur_time
            ran_timers[f] = true
        end
    end

    return ran_timers
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS PROVIDING HTTP REQUESTS FACILITIES                             --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- To perform a HTTP request
-- @param method The method to use for the request
-- @param url The URL to perform the request to
-- @param headers The headers to define for the request
-- @param body The body of the request
-- @param getbody Whether or not to return the body of the response
------------------------------------------------------------------------------
function requests.http_request(...)
    --------------------------------------------------------------------------
    -- Parse the arguments to allow either positional args or named args
    local method, url, headers, body, getbody
    if type(...) == 'table' then
        local args = ...
        method = args.method or args[1]
        url = args.url or args[2]
        headers = args.headers or args[3]
        body = args.body or args[4]
    else
        method, url, headers, body, getbody = ...
    end

    --------------------------------------------------------------------------
    -- Perform checks on the arguments
    if not method then
        error({message='No method provided'})
    end
    method = string.upper(method)
    if not url then
        error({message='No URL provided for ' .. method .. ' request'})
    end
    headers = headers or {}
    headers['User-Agent'] = 'TraktForVLC ' .. __version__ ..
                            '/VLC ' .. vlc.misc.version()

    --------------------------------------------------------------------------
    -- Function logic

    -- Prepare the arguments to call the helper
    args = {
        'requests',
        method,
        url,
    }

    if headers then
        table.insert(args, '--headers')
        table.insert(args, json.encode(headers))
    end
    if body then
        table.insert(args, '--data')
        table.insert(args, json.encode(body))
    end

    -- Return the response object
    return call_helper(args)
end


------------------------------------------------------------------------------
-- To perform a HTTP GET request
-- @param url The URL to perform the request to
-- @param headers The headers to define for the request
------------------------------------------------------------------------------
function requests.get(...)
    -- Parse the arguments to allow either positional args or named args
    local url, headers
    if type(...) == 'table' then
        local args = ...
        url = assert(args.url or args[1])
        headers = assert(args.headers or args[2])
    else
        url, headers = ...
    end

    -- Function logic
    return requests.http_request{
        method='GET',
        url=url,
        headers=headers,
    }
end


------------------------------------------------------------------------------
-- To perform a HTTP POST request
-- @param url The URL to perform the request to
-- @param headers The headers to define for the request
------------------------------------------------------------------------------
function requests.post(...)
    -- Parse the arguments to allow either positional args or named args
    local url, headers, body
    if type(...) == 'table' then
        local args = ...
        url = assert(args.url or args[1])
        headers = assert(args.headers or args[2])
        body = assert(args.body or args[3])
    else
        url, headers, body = ...
    end

    -- Function logic
    return requests.http_request{
        method='POST',
        url=url,
        headers=headers,
        body=body,
    }
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS TO MANAGE THE CONFIGURATION FILE OF THE INTERFACE              --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
-- Variable to store the path to the configuration file
local config_file = ospath.join(vlc.config.configdir(), 'trakt_config.json')
-- Variable to store the path to the cache file
local cache_file = ospath.join(vlc.config.configdir(), 'trakt_cache.json')
-- Last cache save time
local last_cache_save = -1


------------------------------------------------------------------------------
-- Returns the JSON data read from the file at filepath
-- @param filepath The path to the file to read the data from
-- @param default The default data returned if there is an error
------------------------------------------------------------------------------
function file.get_json(filepath, default)
    local data = {}
    local file = io.open(filepath, 'r')

    if file then
        data = json.decode(file:read('*a'))
        file:close()

        if type(data) == 'table' then
            return data
        else
            vlc.msg.err('(file.get_json) JSON file not in the right format')
        end
    else
        vlc.msg.info('No JSON file found at ' .. filepath)
    end

    return default
end


------------------------------------------------------------------------------
-- Writes the JSON passed as argument to the file at filepath
-- @param filepath The path to the file to write the data to
-- @param data The table containing the JSON data to write
------------------------------------------------------------------------------
function file.save_json(filepath, data)
    local file = io.open(filepath, 'w')
    if file then
        local jsondata = json.encode(data, { indent = true })
        vlc.msg.dbg('Writing to ' .. filepath .. ': ' .. dump(jsondata))
        file:write(jsondata)
        file:close()
    else
        error('Error opening the file ' .. filepath .. ' to save')
    end
end


------------------------------------------------------------------------------
-- Returns the configuration read from the configuration file
------------------------------------------------------------------------------
local
function get_config()
    local lconfig = file.get_json(config_file, {})

    -- Default configuration version
    if not lconfig.config_version then
        lconfig.config_version = __version__
    end

    -- Default cache config
    if not lconfig.cache then
        lconfig.cache = {}
    end
    if not lconfig.cache.delay then
        lconfig.cache.delay = {}
    end
    if not lconfig.cache.delay.save then
        lconfig.cache.delay.save = 30  -- 30 seconds
    end
    if not lconfig.cache.delay.cleanup then
        lconfig.cache.delay.cleanup = 60  -- 60 seconds
    end
    if not lconfig.cache.delay.expire then
        lconfig.cache.delay.expire = 2592000  -- 30 days
    end

    -- Default media config
    if not lconfig.media then
        lconfig.media = {}
    end
    if not lconfig.media.info then
        lconfig.media.info = {}
    end
    if not lconfig.media.info.max_try then
        lconfig.media.info.max_try = 10
    end
    if not lconfig.media.info.try_delay_factor then
        lconfig.media.info.try_delay_factor = 30  -- 30 seconds
    end
    if not lconfig.media.start then
        lconfig.media.start = {}
    end
    if not lconfig.media.start.time then
        lconfig.media.start.time = 30  -- 30 seconds
    end
    if not lconfig.media.start.percent then
        lconfig.media.start.percent = .25  -- 0.25%
    end
    if not lconfig.media.start.movie then
        lconfig.media.start.movie = true
    end
    if not lconfig.media.start.episode then
        lconfig.media.start.episode = true
    end
    if not lconfig.media.stop then
        lconfig.media.stop = {}
    end
    if not lconfig.media.stop.watched_percent then
        lconfig.media.stop.watched_percent = 50  -- 50%
    end
    if not lconfig.media.stop.percent then
        lconfig.media.stop.percent = 90  -- 90%
    end
    if not lconfig.media.stop.movie then
        lconfig.media.stop.movie = true
    end
    if not lconfig.media.stop.episode then
        lconfig.media.stop.episode = true
    end
    if not lconfig.media.stop.check_unprocessed_delay then
        lconfig.media.stop.check_unprocessed_delay = 120  -- 120 seconds
    end

    -- Default helper config
    if not lconfig.helper then
        lconfig.helper = {}
    end
    if not lconfig.helper.mode then
        lconfig.helper.mode = 'standalone'  -- Can be one of 'standalone', 'service'
    end

    -- Default helper service config
    if not lconfig.helper.service then
        lconfig.helper.service = {}
    end
    if not lconfig.helper.service.host then
        lconfig.helper.service.host = 'localhost'
    end
    if not lconfig.helper.service.port then
        lconfig.helper.service.port = 1984
    end

    -- Default helper update config
    if not lconfig.helper.update then
        lconfig.helper.update = {}
    end
    if not lconfig.helper.update.check_delay then
        lconfig.helper.update.check_delay = 86400  -- 24 hours, set to 0 to disable
    end
    if not lconfig.helper.update.release_type then
        lconfig.helper.update.release_type = 'stable' -- Can be one of 'stable',
                                                      -- 'rc', 'beta', 'alpha' or
                                                      -- 'latest'
    end
    if not lconfig.helper.update.action then
        lconfig.helper.update.action = 'install'  -- Can be one of 'install',
                                                  -- 'download' or 'check'
    end

    return lconfig
end


------------------------------------------------------------------------------
-- Writes the configuration to the configuration file
-- @param config The table containing the configuration
------------------------------------------------------------------------------
local
function save_config(config)
    return file.save_json(config_file, config)
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS PROVIDING THE TRAKT LOGIN AND UPDATES                          --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
trakt.base_url = 'https://api.trakt.tv'
trakt.api_key = '0e59f99095515c228d5fbc104e342574' ..
                '941aeeeda95946b8fa50b2b0366609bf'
trakt.api_sec = '3ed1d013ef80eb0bb45d8da8424b4b61' ..
                '3713abb057ed505683caf0baf1b5c650'
trakt.api_version = 2
trakt.config = get_config()
if trakt.config.auth and
        trakt.config.auth.access_token and
        trakt.config.auth.refresh_token then
    trakt.configured = true
else
    trakt.configured = false
end

------------------------------------------------------------------------------
-- Function that allows to start the authentication protocol with trakt.tv
-- through the device code; it will provide the URL and code to use to
-- allow TraktForVLC to work with trakt.tv
------------------------------------------------------------------------------
function trakt.device_code()
    if trakt.configured then
        error('TraktForVLC is already configured for Trakt.tv')
    end

    local url = trakt.base_url .. '/oauth/device/code'
    local headers = {
        ['Content-Type'] = 'application/json',
        ['trakt-api-key'] = trakt.api_key,
        ['trakt-api-version'] = trakt.api_version,
    }
    local body = {
        ['client_id'] = trakt.api_key,
    }

    -- Query the API to get a device code
    resp = requests.post{
        url=url,
        headers=headers,
        body=body,
    }
    if not resp or resp.status_code ~= 200 then
        error('Unable to generate the device code ' ..
              'for Trakt.tv authentication')
    end

    -- If everything went fine, we should have the information that
    -- we need to provide the user for its authentication
    json_body = resp.json

    -- Prepare the message to print that information
    message = {
        'TraktForVLC is not setup with Trakt.tv yet!',
        '--',
        'PLEASE GO TO ' .. json_body['verification_url'],
        'AND ENTER THE FOLLOWING CODE:',
        json_body['user_code'],
    }

    -- Prepare a local function to print the message to the console
    local function print_msg_console()
        vlc.msg.err('\n\t' ..
            '############################' ..
            '\n\t' ..
            table.concat(message, '\n\t') ..
            '\n\t' ..
            '############################')
    end

    -- Prepare a local function to print the message to an OSD channel
    local osd_channel
    local function print_msg_osd(duration)
        if osd_channel then
            vlc.osd.message(
                table.concat(message, '\n'),
                osd_channel,
                'center',
                duration
            )
        end
    end

    -- Print it a first time to the console
    print_msg_console()

    -- Then check every interval if the data is ready
    local left_reset_play = 2
    local was_playing = false
    local message_date = vlc.misc.mdate()
    local poll_url = trakt.base_url .. '/oauth/device/token'
    local got_token = callrepeat(
        json_body['interval'],
        json_body['expires_in'],
        function()
            vlc.msg.dbg('Checking if token has been granted')

            if vlc.input.is_playing() then
                -- We're going to be awful, but if the person starts to play
                -- and TraktForVLC is not configured yet, we're gonna prevent
                -- the media to be played
                if vlc.playlist.status() == 'playing' then
                    if left_reset_play == 0 then
                        -- If we reached the maximum of pauses we force, just
                        -- abandon now!
                        return false
                    end
                    left_reset_play = left_reset_play - 1

                    vlc.playlist.pause()
                    was_playing = true
                    print_msg_console()
                end
                -- If we can, use an OSD channel to print the message to the
                -- user directly on the media screen... that should be
                -- visible!
                if not osd_channel then
                    osd_channel = vlc.osd.channel_register()
                    print_msg_osd(600000000 - (vlc.misc.mdate() - message_date))
                end
            end

            -- Prepare the request to the API to verify if we've got
            -- auth tokens ready
            local body = {
                ['client_id'] = trakt.api_key,
                ['client_secret'] = trakt.api_sec,
                ['code'] = json_body['device_code'],
            }

            -- Query the API (we use the same headers as before)
            resp = requests.post{
                url=poll_url,
                headers=headers,
                body=body,
            }

            if not resp then
                vlc.msg.err('Error when trying to check the ' ..
                            'auth token status')
                return false
            elseif resp.status_code == 400 then
                vlc.msg.dbg('Auth token pending (Waiting for ' ..
                            'the user to authorize the app)')
            elseif resp.status_code == 429 then
                vlc.msg.dbg('Got asked to slow down by the API')
                sleep(2)
            elseif resp.status_code ~= 200 then
                vlc.msg.err('(check_token) Request returned with code ' ..
                            tostring(resp.status_code))
                if resp.json then
                    vlc.msg.err('(check_token) Request body: ' ..
                                dump(resp.json))
                else
                    vlc.msg.err('(check_token) Request body: ' ..
                                dump(resp.body))
                end
                return false
            end

            -- If we reach here, we got status 200, hence the
            -- tokens are ready
            return resp.json
        end
    )

    -- If we're here, clear the OSD channel, it's not useful anymore
    if osd_channel then
        vlc.osd.channel_clear(osd_channel)
    end

    -- If we reach here and we did not have any token... it did not
    -- work... ;( We'll just disable TraktForVLC until VLC is restarted
    if not got_token then
        message = {
            'TraktForVLC setup failed; Restart VLC to try again',
            '(disabled until then)'
        }
        print_msg_console()
        print_msg_osd(5)
        return false
    end

    -- Show a quick thank you message :)
    message = {
        'TraktForVLC is now setup with Trakt.tv!',
        'Thank you :)',
    }
    print_msg_console()
    print_msg_osd(5)

    -- If the media was playing and we paused it, put it back in play
    if was_playing then
        vlc.playlist.play()
    end

    -- Save the tokens information
    if not trakt.config['auth'] then
        trakt.config['auth'] = {}
    end
    trakt.config.auth.access_token = got_token.access_token
    trakt.config.auth.refresh_token = got_token.refresh_token
    save_config(trakt.config)

    trakt.configured = true
    return true
end


------------------------------------------------------------------------------
-- Function that allows to renew authentication tokens using the refresh
-- token; this will allow to keep TraktForVLC authenticated with trakt.tv
-- even after the current auth token has expired.
------------------------------------------------------------------------------
function trakt.renew_token()
    if not trakt.configured then
        error('TraktForVLC is not configured for Trakt.tv')
    end
    vlc.msg.dbg('Renewing tokens')

    local url = trakt.base_url .. '/oauth/token'
    local headers = {
        ['Content-Type'] = 'application/json',
        ['trakt-api-key'] = trakt.api_key,
        ['trakt-api-version'] = trakt.api_version,
    }
    local body = {
        ['refresh_token'] = trakt.config.auth.refresh_token,
        ['client_id'] = trakt.api_key,
        ['client_secret'] = trakt.api_sec,
        ['redirect_uri'] = 'urn:ietf:wg:oauth:2.0:oob',
        ['grant_type'] = 'refresh_token',
    }

    -- Query the API to get the new tokens
    resp = requests.post{
        url=url,
        headers=headers,
        body=body,
    }

    if not resp then
        vlc.msg.err('Error when trying to refresh token')
        return false
    elseif resp.status_code == 401 then
        vlc.msg.err('Refresh token is invalid')

        -- Erase the current auth config... not working
        -- anymore anyway
        trakt.configured = false
        trakt.config.auth = {}
        save_config(trakt.config)

        -- Restart the device_code process!
        return trakt.device_code()
    elseif resp.status_code ~= 200 then
        vlc.msg.err('Error when trying to refresh the tokens: ' ..
                    resp.status_code .. ' ' .. resp.status_text)
        return false
    end

    -- If we reach here, we got status 200, hence the
    -- tokens are ready
    got_token = resp.json

    -- Save the new tokens
    trakt.config.auth.access_token = got_token.access_token
    trakt.config.auth.refresh_token = got_token.refresh_token
    save_config(trakt.config)

    vlc.msg.dbg('Tokens renewed')
    return true
end


------------------------------------------------------------------------------
-- Function that allows to scrobble with trakt.tv; this will allow to start,
-- pause, and stop scrobbling.
------------------------------------------------------------------------------
function trakt.scrobble(action, media, percent)
    if not trakt.configured then
        error('TraktForVLC is not configured for Trakt.tv')
    elseif not media['imdb'] then
        return false
    end
    if not percent then
        percent = media['ratio']['local'] * 100.
    end
    vlc.msg.info(action:sub(1,1):upper() .. action:sub(2) ..
                ' scrobbling ' .. media['name'])

    local url = trakt.base_url .. '/scrobble/' .. action:lower()
    local headers = {
        ['Content-Type'] = 'application/json',
        ['trakt-api-key'] = trakt.api_key,
        ['trakt-api-version'] = trakt.api_version,
        ['Authorization'] = string.format(
            'Bearer %s', trakt.config.auth.access_token)
    }
    local body = {
        [media['type']] = {
            ['ids'] = {
                ['imdb'] = string.sub(media.imdb.id, 8, -2),
                ['tvdb'] = media.imdb.tvdbid,
                ['tmdb'] = media.imdb.tmdbid,
            },
        },
        ['progress'] = percent,
        ['app_version'] = __version__,
    }

    local try = 0
    while true do
        -- Query the API to scrobble
        resp = requests.post{
            url=url,
            headers=headers,
            body=body,
        }

        if not resp then
            vlc.msg.err('Error when trying to ' .. action:lower() ..
                        ' scrobble')
            return false
        elseif resp.status_code == 401 then
            if try > 0 then
                vlc.msg.err('Unable to scrobble')
                return false
            end
            vlc.msg.info('Got 401 while scrobbling, trying to reauth')
            trakt.renew_token()
            try = try + 1
        elseif resp.status_code == 409 then
            vlc.msg.info('Already scrobbled recently')
            return true
        elseif resp.status_code ~= 201 then
            vlc.msg.err('Error when trying to ' .. action:lower() ..
                        ' scrobble: ' .. tostring(resp.status_code) .. ' ' ..
                        tostring(resp.reason))
            vlc.msg.dbg(dump(resp))
            return false
        else
            return resp.json
        end
    end
end


------------------------------------------------------------------------------
-- Function to cancel the currently watching status on trakt.tv
------------------------------------------------------------------------------
function trakt.cancel_watching(media)
    -- As per the Trakt API v2, we need to call the start method saying that
    -- the watch is at the end, so it will expire soon after.
    return trakt.scrobble('start', media, 99.99)
end


------------------------------------------------------------------------------
-- Function to add to trakt.tv history for medias that we could not scrobble
-- in real time (no internet connection, issue identifying media at the time,
-- etc.)
------------------------------------------------------------------------------
function trakt.add_to_history(medias)
    if not trakt.configured then
        error('TraktForVLC is not configured for Trakt.tv')
    end
    vlc.msg.dbg('Syncing past views with trakt')

    local url = trakt.base_url .. '/sync/history'
    local headers = {
        ['Content-Type'] = 'application/json',
        ['trakt-api-key'] = trakt.api_key,
        ['trakt-api-version'] = trakt.api_version,
        ['Authorization'] = string.format(
            'Bearer %s', trakt.config.auth.access_token)
    }

    local movies = {}
    local episodes = {}

    for k, v in pairs(medias) do
        if v.imdbid and v.type and v.watched_at then
            local data = {
                ['watched_at'] = v.watched_at,
                ['ids'] = {
                    ['imdb'] = v.imdbid,
                    ['tvdb'] = v.tvdbid,
                    ['tmdb'] = v.tmdbid,
                },
            }
            if v.type == 'movie' then
                table.insert(movies, data)
            else
                table.insert(episodes, data)
            end
        end
    end

    if next(movies) == nil and next(episodes) == nil then
        error('Nothing to sync ?!')
    end
    vlc.msg.info('Syncing ' .. tostring(#movies) .. ' movie(s) and ' ..
                 tostring(#episodes) .. ' episode(s) with Trakt.tv')

    local body = {}
    if next(movies) ~= nil then
        body['movies'] = movies
    end
    if next(episodes) ~= nil then
        body['episodes'] = episodes
    end

    local try = 0
    while true do
        -- Query the API to add to history
        resp = requests.post{
            url=url,
            headers=headers,
            body=body,
        }

        if not resp then
            vlc.msg.err('Error when trying to add to history')
            return false
        elseif resp.status_code == 401 then
            if try > 0 then
                vlc.msg.err('Unable to add to history')
                return false
            end
            vlc.msg.info('Got 401 while adding to history, trying to reauth')
            trakt.renew_token()
            try = try + 1
        elseif resp.status_code ~= 201 then
            vlc.msg.err('Error when trying to add to history: ' ..
                        tostring(resp.status_code) .. ' ' ..
                        tostring(resp.status_text))
            return false
        else
            return resp.json
        end
    end
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS THAT ARE RELATED TO THE CACHE                                  --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Returns the cache read from the cache file
------------------------------------------------------------------------------
local
function get_cache()
    return file.get_json(cache_file, {})
end


------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
-- Variable containing the cached information
local cache = get_cache()
-- To inform if the cache has changed
local cache_changed = false


------------------------------------------------------------------------------
-- Writes the cache to the cache file
-- @param cache The table containing the cache
-- @param force Whether or not to force the save of the cache right now (else,
--              data might be saved only at a next call after the delay has
--              expired)
------------------------------------------------------------------------------
local
function save_cache(cache, force)
    if not force and
            vlc.misc.mdate() < (trakt.config.cache.delay.save * 1000000. +
                                last_cache_save) then
        return
    end
    last_cache_save = vlc.misc.mdate()
    cache_changed = false
    return file.save_json(cache_file, cache)
end


------------------------------------------------------------------------------
-- Function that cleanup the cache of all the media that were not used
-- recently and that are not waiting to be added to trakt.tv history
------------------------------------------------------------------------------
local
function cleanup_cache()
    -- If there is no delay for cache data to expire, do not do anything
    if not trakt.config.cache.delay.expire then
        vlc.msg.dbg('No cache expiration, nothing to do')
        return
    end

    -- Get the current date
    date = call_helper({'date', '--format', '%s.%f'})
    if not date or not date.date then
        vlc.msg.err('(cleanup_cache) Unable to get the current date')
        return
    end
    date = tonumber(date.date)

    for k, v in pairs(cache) do
        local no_wait_scrobble = (not v['scrobble_ready'] or
                                  next(v['scrobble_ready']) == nil)
        local expired = (
            not v['last_use'] or (
                v['last_use'] + trakt.config.cache.delay.expire) < date)
        if no_wait_scrobble and expired then
            cache[k] = nil
            cache_changed = true
        end
    end

    if cache_changed then
        vlc.msg.info('Saving cache')
        save_cache(cache, true)
    end
end


------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- FUNCTIONS THAT ARE RELATED TO THE PROCESSING OF THE MEDIA INFORMATION    --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Variables
------------------------------------------------------------------------------
-- Variable containing the information about the last media seen
local last_infos = nil
-- Variable containing the information about the current watching status
local watching = nil


------------------------------------------------------------------------------
-- Gets the current play time for the item being played currently
------------------------------------------------------------------------------
local
function get_play_time()
    if not vlc.input.is_playing() then
        return nil
    end
    return vlc.var.get(vlc.object.input(), "time") / 1000000
end


------------------------------------------------------------------------------
-- Gets the current play rate
------------------------------------------------------------------------------
local
function get_play_rate()
    if not vlc.input.is_playing() then
        return nil
    end
    return vlc.var.get(vlc.object.input(), "rate")
end


------------------------------------------------------------------------------
--
------------------------------------------------------------------------------
local
function complete_cache_data(key, max_try_obj)
    local loc_cache_changed = false

    -- If we don't have the imdb information, go get it
    if not cache[key].imdb and (
            not max_try_obj or
            not max_try_obj.num or
            not max_try_obj.last or (
                max_try_obj.num < trakt.config.media.info.max_try and
                vlc.misc.mdate() >= (
                    max_try_obj.last +
                    max_try_obj.num *
                    trakt.config.media.info.try_delay_factor *
                    1000000
                )
            )
    ) then
        -- Check that we have all required information before making the
        -- request
        if not cache[key].meta or not cache[key].duration then
            vlc.msg.err('Missing information for media ' .. key ..
                        ' in order to get the main IMDB information')
            return
        end

        local args = {
            '--quiet',
            'resolve',
            '--meta',
            json.encode(cache[key].meta),
            '--duration',
            tostring(cache[key].duration),
        }
        if cache[key].hash and cache[key].size then
            table.insert(args, '--hash')
            table.insert(args, cache[key].hash)
            table.insert(args, '--size')
            table.insert(args, tostring(cache[key].size))
        end

        local result, err = call_helper(args)
        if result and next(result) ~= nil then
            -- Clean-up results to keep only what's needed
            for k, v in pairs(result) do
                result[k] = {
                    ['base'] = v.base,
                }
            end

            -- And save the information in the cache
            cache[key].imdb = result
            cache_changed = true
            loc_cache_changed = true
            if max_try_obj then
                max_try_obj.num = 0
                max_try_obj.last = -1
            end
        elseif max_try_obj then
            if not max_try_obj.num then
                max_try_obj.num = 0
            end
            max_try_obj.num = max_try_obj.num + 1
            max_try_obj.last = vlc.misc.mdate()
        end
    end

    if cache[key].imdb then
        if not cache[key].imdb_details then
            -- Check that we have all required information before making the
            -- request
            if not cache[key].duration then
                vlc.msg.err('Missing information for media ' .. key ..
                            ' in order to get the IMDB details')
                return
            end

            -- Compute the total duration of the elements
            local total = 0
            local missing_time = 0
            for k, v in pairs(cache[key].imdb) do
                if v.base.runningTimeInMinutes then
                    total = total + v.base.runningTimeInMinutes * 60.
                else
                    missing_time = missing_time + 1
                end
            end

            -- Compute the factor between our media duration information
            -- and the total time returned by imdb
            local missing_time_duration
            if missing_time > 0 then
                if total >= cache[key].duration then
                    vlc.msg.err('(get_current_info) cannot determine duration ' ..
                                'for some episodes')
                    return infos  -- Stop now...
                end
                missing_time_duration = (
                    cache[key].duration - total) / missing_time
                total = cache[key].duration
            end
            cache[key].imdb_details = {
                ['play_total'] = total,
                ['play_factor'] = total / cache[key].duration,
                ['missing_time_duration'] = missing_time_duration,
            }
            cache_changed = true
            loc_cache_changed = true
        end

        if not cache[key].imdb_details.per_media then
            -- Get needed variables locally for performance
            local missing_time_duration = cache[key].imdb_details.missing_time_duration
            local play_factor = cache[key].imdb_details.play_factor
            local play_total = cache[key].imdb_details.play_total
            -- Prepare to save the information per media
            local per_media = {}
            local cur = 0
            for k, v in pairs(cache[key].imdb) do
                local this_media = {}
                if v.base.runningTimeInMinutes then
                    this_media['duration'] = v.base.runningTimeInMinutes * 60.
                else
                    this_media['duration'] = missing_time_duration
                end
                this_media['vlcduration'] = this_media['duration'] / play_factor

                -- Compute the media time
                this_media['from'] = {
                    ['vlctime'] = cur / play_factor,
                    ['time'] = cur,
                    ['percent'] = cur / play_total,
                }
                cur = cur + this_media['duration']
                this_media['to'] = {
                    ['vlctime'] = cur / play_factor,
                    ['time'] = cur,
                    ['percent'] = cur / play_total,
                }

                -- Compute the media name
                if v.base.titleType == 'tvEpisode' then
                    this_media['name'] = string.format(
                        '%s (%d) - S%02dE%02d - %s',
                        v.base.parentTitle.title,
                        v.base.parentTitle.year,
                        v.base.season,
                        v.base.episode,
                        v.base.title)
                    this_media['type'] = 'episode'
                else
                    this_media['name'] = string.format(
                        '%s (%d)',
                        v.base.title,
                        v.base.year)
                    this_media['type'] = 'movie'
                end

                -- Add to the list of media
                table.insert(per_media, this_media)
            end

            -- Add to the cache
            cache[key].imdb_details.per_media = per_media
            cache_changed = true
            loc_cache_changed = true
        end
    end

    return loc_cache_changed
end


------------------------------------------------------------------------------
-- Gets the information for the currently playing item in VLC. and returns it
-- in the form of a table to make it usable
------------------------------------------------------------------------------
local
function get_current_info()
    local loc_cache_changed = false
    infos = {}

    repeat
        item = vlc.input.item()
    until (item and item:is_preparsed())
    repeat
    until item:stats()["demux_read_bytes"] > 0

    if item:stats()['decoded_video'] == 0 then
        -- This is not a video, stop now
        vlc.msg.dbg('Not a video; doing nothing.')
        return
    end

    infos['name'] = item:name()
    infos['uri'] = vlc.strings.decode_uri(item:uri())
    infos['duration'] = item:duration()
    infos['meta'] = item:metas()
    -- infos['info'] = item:info()
    infos['play'] = {
        ['global'] = get_play_time(),
    }
    infos['ratio'] = {
        ['global'] = infos['play']['global'] / infos['duration'],
    }
    infos['time'] = vlc.misc.mdate()

    infos['key'] = infos['uri'] .. '#' .. infos['duration']

    -- Check if the media is already in the cache
    if not cache[infos['key']] then
        cache[infos['key']] = {}
    end

    if not cache[infos['key']].duration or
            infos['duration'] ~= cache[infos['key']].duration then
        cache[infos['key']].duration = infos['duration']
        cache_changed = true
        loc_cache_changed = true
    end

    if not cache[infos['key']].meta or
            not equals(infos['meta'], cache[infos['key']].meta) then
        cache[infos['key']].meta = infos['meta']
        cache_changed = true
        loc_cache_changed = true
    end

    if not cache[infos['key']].uri_proto then
        -- Check if it's a local file or a distant URL... as for a local
        -- file we can compute a hash for the file information resolution
        local uri_proto, uri_path = string.match(
            infos['uri'], '^([a-zA-Z0-9-]+)://(.*)$')
        if not uri_proto and not uri_path then
            uri_proto = 'file'
            uri_path = infos['uri']
        elseif uri_proto == 'file' and
                uri_path:sub(1,1) == '/' and
                ospath.sep == '\\' then
            -- On Windows, remove leading slash for file URIs
            uri_path = uri_path:sub(2)
        end

        cache[infos['key']].uri_proto = uri_proto
        cache[infos['key']].uri_path = uri_path
        cache_changed = true
        loc_cache_changed = true
    end

    if cache[infos['key']].uri_proto == 'file' and
            (not cache[infos['key']].hash or
             not cache[infos['key']].size) then
        -- Compute the media hash and size
        local media_hash, media_size = movieHash(cache[infos['key']].uri_path)

        -- Check if any file in the cache matches those information
        for k,v in pairs(cache) do
            if v.hash == media_hash or v.size == media_size then
                -- Copy the recently computed information in the cache entry
                -- we're about to replace
                cache[k].meta = cache[infos['key']].meta
                cache[k].duration = cache[infos['key']].duration
                cache[k].uri_proto = cache[infos['key']].uri_proto
                cache[k].uri_path = cache[infos['key']].uri_path

                -- Then move that cache entry
                cache[infos['key']] = cache[k]
                cache[k] = nil
                cache_changed = true
                loc_cache_changed = true
                break
            end
        end

        if not cache[infos['key']].hash then
            cache[infos['key']].hash = media_hash
            cache_changed = true
            loc_cache_changed = true
        end
        if not cache[infos['key']].size then
            cache[infos['key']].size = media_size
            cache_changed = true
            loc_cache_changed = true
        end
    end

    local max_try_obj
    if watching and not watching.get_imdb_try then
        watching['get_imdb_try'] = {}
        max_try_obj = watching.get_imdb_try
    end
    if complete_cache_data(infos['key'], max_try_obj) then
        loc_cache_changed = true
    end

    -- Update the cache with the last usage data
    date = call_helper({'date', '--format', '%s.%f'})
    if date and date.date then
        cache[infos['key']]['last_use'] = tonumber(date.date)
    else
        vlc.msg.err('(get_current_info) Unable to update the last use ' ..
                    'date for cache data ' .. infos['key'])
    end
    -- Only force saving the cache now if the cache has changed, else
    -- the cache will be saved if the delay has passed
    if loc_cache_changed then
        vlc.msg.info('Force saving cache')
    end
    save_cache(cache, loc_cache_changed)

    -- Get the information from the cache for the current media
    if cache[infos['key']].imdb then
        -- Get needed variables locally for performance
        local play_factor = cache[infos['key']].imdb_details.play_factor
        local play_time_imdb = infos['play']['global'] * play_factor
        -- Search the current media
        for k, v in pairs(cache[infos['key']].imdb_details.per_media) do
            if v['from'].percent <= infos['ratio'].global and
                    v['to'].percent >= infos['ratio'].global then
                infos['local_idx'] = k
                infos['orig_name'] = infos['name']
                infos['proper_name'] = v['name']
                infos['name'] = v['name']
                infos['type'] = v['type']
                infos['imdb'] = cache[infos['key']].imdb[k].base
                infos['ratio']['local'] = (play_time_imdb - v['from'].time) / v['duration']
                infos['play']['local'] = play_time_imdb
                infos['from'] = v['from']
                infos['to'] = v['to']
                break
            end
        end
    end

    return infos
end


------------------------------------------------------------------------------
--
------------------------------------------------------------------------------
local
function update_watching(media, status)
    local status_changed

    -- If the media has changed
    if not watching or media['key'] ~= watching['key'] then
        -- Create the new watching object for the new media
        watching = {
            ['key'] = media['key'],
            ['status'] = status,
            ['trakt'] = {
                ['watching'] = false,
                ['scrobbled'] = false,
            },
            ['current'] = {
                ['from'] = media['play']['global'],
                ['to'] = media['play']['global'],
            },
        }

        status_changed = true

    -- Or if it hasn't changed and we've moved forward in it
    else
        -- Update the status to the status passed as parameter
        if watching['status'] ~= status then
            watching['status'] = status
            status_changed = true
        end

        -- Update the current play and ratio position
        media_time_diff = media['play']['global'] - watching['play']['global']
        media_time_diff = media_time_diff / get_play_rate()
        intf_time_diff = (media['time'] - watching['last_time']) / 1000000.

        -- Check if there was a jump in time, if it's the case, close the
        -- current time set and open a new one
        if media_time_diff < 0 or (media_time_diff / intf_time_diff) > 1.3 then
            watching['current']['to'] = watching['play']['global']
            table.insert(cache[media['key']].watched,
                         watching['current'])
            cache[media['key']].watched = merge_intervals(
                cache[media['key']].watched)
            cache_changed = true
            watching['current'] = nil
            -- Reset the watching status as we jumped
            watching['trakt']['watching'] = false
        end

        if watching['current'] then
            watching['current']['to'] = media['play']['global']
        elseif status == 'playing' then
            watching['current'] = {
                ['from'] = media['play']['global'],
                ['to'] = media['play']['global'],
            }
        end
    end

    -- Update the watching status
    watching['last_time'] = media['time']
    watching['play'] = media['play']
    watching['ratio'] = media['ratio']

    -- No need to do what is after if we are paused and it is not
    -- the first loop being paused
    if status == 'paused' and not status_changed then
        return
    end

    -- Insure that the cache can receive the watched information
    if not cache[media['key']].watched then
        cache[media['key']].watched = {}
    end

    -- Bring the intervals locally and merge with the current one
    local temp = cache[media['key']].watched
    if watching.current then
        table.insert(temp, {
            ['from'] = watching['current']['from'],
            ['to'] = watching['current']['to'],
        })
    end
    temp = merge_intervals(temp)

    -- Then save it in the cache
    cache[media['key']].watched = temp
    cache_changed = true

    -- Compute the watched ratio and play for the media currently being
    -- watched, from the information that we can read from the cache if
    -- available; if it's not the case, we'll fall back on computing a
    -- global watched ratio and play for the whole file.
    local n = 1
    local sum = 0
    local vlcduration
    if cache[media['key']].imdb_details and
            cache[media['key']].imdb_details.per_media then
        local v = cache[media['key']].imdb_details.per_media[
            media['local_idx']]
        while temp[n] ~= nil and temp[n]['to'] <= v['from'].vlctime do
            n = n + 1
        end
        while temp[n] ~= nil do
            if temp[n]['from'] >= v['to'].vlctime then
                break
            end

            local add_from = math.max(temp[n]['from'], v['from'].vlctime)
            local add_to = math.min(temp[n]['to'], v['to'].vlctime)
            sum = sum + (add_to - add_from)

            if temp[n]['to'] <= v['to'].vlctime then
                n = n + 1
            else
                break
            end
        end
        vlcduration = v['vlcduration']
    else
        while temp[n] ~= nil do
            sum = sum + (temp[n]['to'] - temp[n]['from'])
            n = n + 1
        end
        vlcduration = media['duration']
    end
    watching.play.watched = sum
    watching.ratio.watched = sum / vlcduration
end


------------------------------------------------------------------------------
-- Function being run when the media is currently playing
-- @param media The information about the media
------------------------------------------------------------------------------
local
function media_is_playing(media)
    vlc.msg.info(string.format('%s is playing! :) (%f/%f)',
                               media['name'],
                               media['play']['global'],
                               media['duration']))

    update_watching(media, 'playing')

    -- If we keep the watching status in sync
    if media['type'] and trakt.config.media.start[media['type']] then
        -- Check if we need to scrobble start watching this media on trakt
        if not watching.trakt.watching and media['imdb'] and
                media['play']['local'] and media['ratio']['local'] and
                media['play']['local'] >= trakt.config.media.start.time and
                media['ratio']['local'] * 100. >= trakt.config.media.start.percent then
            -- We need to save the index of the media to know which one we
            -- have already set in watching status
            local is_watching = trakt.scrobble('start', media)
            if is_watching then
                watching.trakt.watching = true
            end
        end
    end

    -- If we want to scrobble
    local might_scrobble = false
    if media['type'] then
        might_scrobble = trakt.config.media.stop[media['type']]
    else
        might_scrobble = (trakt.config.media.stop['episode'] or
                          trakt.config.media.stop['movie'])
    end
    if might_scrobble then
        -- Determine the current scope: if we do not have imdb information,
        -- it means that we cannot work in local scope as we cannot know
        -- the per-media information, we thus need to consider the global
        -- scope of the media file. This global scope will then be
        -- converted when possible to the local scope(s).
        local scope
        local should_scrobble = false
        if not watching.trakt.scrobbled then
            if media['ratio']['local'] then
                scope = 'local'
            else
                scope = 'global'
            end

            -- Check, using the current scope, that we can actually
            -- scrobble, following the configuration
            if media['ratio'][scope] * 100. >= trakt.config.media.stop.percent and
                    media.ratio.watched * 100. >= trakt.config.media.stop.watched_percent then
                should_scrobble = true
            end
        end

        if should_scrobble then
            local idx
            if scope == 'global' then
                idx = 'all'
            else
                idx = media['local_idx']
            end

            -- That way, we won't scrobble the same media two times in a row
            watching.trakt.scrobbled = true

            -- Get the date, we'll get it directly in the two formats we'll
            -- need here, one for checking the delay, the other for storing
            -- the information in the cache in case we need it
            local date = call_helper({'date', '--format', '%s.%f',
                                      '--format', '%Y-%m-%dT%H:%M:%S.%fZ'})
            if not date or not date[1] then
                vlc.msg.err('(media_is_playing) Unable to get the current date')
                return
            end

            -- Check if we can scrobble... or if we're before the delay, in which
            -- case we'll skip that scrobble
            local ts = tonumber(date[1].date)
            local skip_scrobble = false
            local m_cache = cache[media['key']]
            if m_cache.last_scrobble then
                -- If we are in local scope, check if we have a last scrobble
                -- information that was registered in global scope, in which
                -- case, we need to convert it to local scope now that we
                -- have the full information
                if scope == 'local' and m_cache.last_scrobble.all then
                    for kidx, _ in pairs(m_cache.imdb_details.per_media) do
                        m_cache.last_scrobble[kidx] = math.max(
                            m_cache.last_scrobble[kidx],
                            m_cache.last_scrobble.all)
                    end
                    m_cache.last_scrobble.all = nil
                end
                if m_cache.last_scrobble[idx] and
                        (m_cache.last_scrobble[idx] +
                         trakt.config.media.stop.delay) >= ts then
                    skip_scrobble = true
                end
            end

            -- If we do not skip the scrobble, act on it!
            if not skip_scrobble then
                -- Save the fact that we need to scrobble in the cache... in case
                -- anything happens! We do that before as it allows to scrobble
                -- next time if VLC dies or is killed during the scrobble with
                -- trakt! We don't want to lose any scrobble!
                local scrobble_ready = {
                    ['idx'] = idx,
                    ['when'] = date[2].date,
                }

                if not m_cache.last_scrobble then
                    m_cache.last_scrobble = {}
                end
                if not m_cache.scrobble_ready then
                    m_cache.scrobble_ready = {}
                end
                m_cache.last_scrobble[idx] = ts
                table.insert(m_cache.scrobble_ready, scrobble_ready)

                -- Clean the 'watched' part of the cache that concerns this
                -- episode; if we are not in episode scope, just clean everything
                -- from the watched cache as everything should be (and will be)
                -- scrobbled when we'll be able to
                if scope == 'global' then
                    -- By resetting that table, the while for 'per-episode' work
                    -- will just stop before the first loop even starts
                    m_cache.watched = {}
                end

                local i = 1
                while m_cache.watched[i] ~= nil do
                    local watched = m_cache.watched[i]
                    if watched['to'] <= media['from']['vlctime'] then
                        i = i + 1
                    elseif watched['to'] <= media['to']['vlctime'] then
                        if watched['from'] <= media['from']['vlctime'] then
                            m_cache.watched[i]['to'] = media['from']['vlctime']
                        else
                            table.remove(m_cache.watched, i)
                        end
                    else
                        if watched['from'] <= media['from']['vlctime'] then
                            local before = {
                                ['from'] = watched['from'],
                                ['to'] = media['from']['vlctime'],
                            }
                            local after = {
                                ['from'] = media['to']['vlctime'],
                                ['to'] = watched['to'],
                            }
                            m_cache.watched[i] = after
                            table.insert(m_cache.watched, i, before)
                        elseif watched['from'] <= media['to']['vlctime'] then
                            m_cache.watched[i]['from'] = media['to']['vlctime']
                        end
                        break
                    end
                end

                -- Save the cache
                save_cache(cache, true)

                -- Only try to scrobble if we are in the local scope, as if
                -- we are not, it means we are missing the imdb information
                -- that is required to actually scrobble something
                if scope == 'local' then
                    -- Then try to scrobble on trakt
                    -- Do a stop with a ratio that will absolutely scrobble
                    -- as watched; this allows for users to configure to
                    -- use lower ratios than Trakt.tv allows for
                    local is_scrobbled = trakt.scrobble('stop', media, 99.99)
                    -- Then reset the watch status to where we actually are
                    trakt.scrobble('start', media)

                    -- If it worked, remove from the cache
                    if is_scrobbled then
                        table.remove(m_cache.scrobble_ready)
                        save_cache(cache, true)
                    end
                end
            end
        end
    end
end


------------------------------------------------------------------------------
-- Function being run when the media is currently paused
-- @param media The information about the media
------------------------------------------------------------------------------
local
function media_is_paused(media)
    vlc.msg.info(media['name'] .. ' is paused! :| ('
        .. get_play_time() .. '/' .. media['duration'] .. ')')

    update_watching(media, 'paused')

    -- Check if we need to pause scrobble
    if watching.trakt.watching then
        watching.trakt.watching = false
        if media['imdb'] then
            trakt.scrobble('pause', media)
        end
    end
end


------------------------------------------------------------------------------
-- Function being run when the media has been stopped
-- @param media The information about the media
------------------------------------------------------------------------------
local
function media_is_stopped(media)
    vlc.msg.info(media['name'] .. ' is stopped! :(')

    -- If we were currently watching a media, we need to stop
    if watching.trakt.watching then
        --trakt.cancel_watching(media)
    end

    -- Reset the watching information
    watching = nil
end


------------------------------------------------------------------------------
--
------------------------------------------------------------------------------
local
function process_scrobble_ready()
    local max_try_obj = {}
    local medias = {}

    -- Prepare the list of medias to add to the history
    for key, media in pairs(cache) do
        local sr
        if media['scrobble_ready'] then
            sr = media['scrobble_ready']
        else
            sr = {}
        end
        if next(sr) ~= nil then
            -- Insure that we have all the data required for the media
            complete_cache_data(key, max_try_obj)

            -- Update the media object in case anything changed
            media = cache[key]
        end
        if media.imdb and next(sr) ~= nil then
            -- Go through the loop a first time to remove entries that are
            -- not valid (invalid index or 'should not be scrobbled' type),
            -- and if there is entries for 'all', replace them by an entry
            -- for each media that should be scrobbled
            local index = 1
            local size = #sr
            while index <= size do
                while sr[index]['idx'] == 'all' do
                    for k, _ in pairs(media.imdb) do
                        size = size + 1
                        sr[size] = {
                            ['idx'] = k,
                            ['when'] = sr[index]['when'],
                        }
                    end
                    sr[index] = sr[size]
                    sr[size] = nil
                    size = size - 1
                    cache_changed = true
                end
                if not sr[index] or
                        not media.imdb[sr[index].idx] or
                        not trakt.config.media.stop[
                            media.imdb_details.per_media[
                                sr[index].idx]['type']] then
                    sr[index] = sr[size]
                    sr[size] = nil
                    size = size - 1
                    cache_changed = true
                else
                    index = index + 1
                end
            end
            -- Create entries to be sync-ed
            for k, v in pairs(sr) do
                table.insert(medias, {
                    ['watched_at'] = v.when,
                    ['imdbid'] = string.sub(media.imdb[v.idx].base.id, 8, -2),
                    ['tvdbid'] = media.imdb[v.idx].base.tvdbid,
                    ['tmdbid'] = media.imdb[v.idx].base.tmdbid,
                    ['type'] = media.imdb_details.per_media[v.idx].type,
                    ['cache'] = {
                        ['key'] = key,
                        ['idx'] = v.idx,
                    }
                })
            end
        end
    end

    -- Stop there if nothing to do
    if next(medias) == nil then
        return
    end

    -- Execute the command
    local result = trakt.add_to_history(medias)
    if not result then
        return
    end

    -- All the medias that we could not add should be kept for another try
    -- next time, we'll thus remove them from the media list, and show an
    -- error message about them; we will also try to get extra IDs for
    -- these medias in case we did not find them before
    if #medias > result.added.episodes + result.added.movies then
        local not_found = {}
        for k, v in pairs(result.not_found.movies) do
            table.insert(not_found, v.ids.imdb)
        end
        for k, v in pairs(result.not_found.episodes) do
            table.insert(not_found, v.ids.imdb)
        end

        -- Prepare the command to search for extra ids
        command = {
            '--quiet',
            'extraids',
        }
        local need_extra_ids = {}

        for _, v in pairs(not_found) do
            for k, m in pairs(medias) do
                if m and m.imdbid == v then
                    vlc.msg.err('Media ' .. m.cache.key ..
                                ' (idx: ' .. m.cache.idx .. ')' ..
                                ' was not added to history')

                    -- Add the media information to the command in order
                    -- to get extra ids, but only if necessary
                    if (m['type'] == 'episode' and not m.tvdbid) or
                            not m.tmdbid then
                        local imdbinfo = cache[m.cache.key].imdb[m.cache.idx].base
                        if m['type'] == 'episode' then
                            table.insert(command, '--episode')
                            table.insert(command, imdbinfo.parentTitle.title)
                            table.insert(command, tostring(imdbinfo.season))
                            table.insert(command, tostring(imdbinfo.episode))
                            table.insert(
                                command,
                                tostring(imdbinfo.parentTitle.year))
                            table.insert(
                                command,
                                string.sub(imdbinfo.parentTitle.id, 8, -2))
                        else
                            table.insert(command, '--movie')
                            table.insert(command, imdbinfo.title)
                            table.insert(command, tostring(imdbinfo.year))
                        end

                        table.insert(need_extra_ids, m)
                    end

                    medias[k] = nil
                end
            end
        end

        -- Run the helper command if needed
        if #command > 2 then
            local extra_ids = call_helper(command)
            if not extra_ids or next(extra_ids) == nil then
                vlc.msg.dbg('No extra_ids found at all... which is weird')
                return
            end

            local loc_cache_changed = false

            -- Then parse the extra ids found for each media
            for _, m in pairs(need_extra_ids) do
                local found_extra_ids;
                local imdbinfo = cache[m.cache.key].imdb[m.cache.idx].base
                if m['type'] == 'episode' then
                    found_extra_ids = extra_ids['episode'][
                        imdbinfo.parentTitle.title][
                        tostring(imdbinfo.season)][
                        tostring(imdbinfo.episode)]
                else
                    found_extra_ids = extra_ids['movie'][imdbinfo.title]
                end

                -- If any of those ids was missing, add it, and flag the cache
                -- to be saved
                for idname, idvalue in pairs(found_extra_ids) do
                    idfield = idname .. 'id'
                    if not imdbinfo[idfield] then
                        imdbinfo[idfield] = idvalue
                        loc_cache_changed = true
                    end
                end
            end

            if loc_cache_changed then
                -- If we found extra ids, force change cache
                save_cache(cache, true)
            end
        end
    end

    -- Prepare to remove the medias successfully added from the cache
    local rm_scrobble_ready = {}
    for k, v in pairs(medias) do
        if not rm_scrobble_ready[v.cache.key] then
            rm_scrobble_ready[v.cache.key] = {}
        end
        table.insert(rm_scrobble_ready[v.cache.key], v.cache.idx)
    end

    -- Then remove them properly
    for key, listidx in pairs(rm_scrobble_ready) do
        table.sort(listidx, function(a, b) return a > b end)
        for _, idx in pairs(listidx) do
            table.remove(cache[key].scrobble_ready, idx)
        end

        -- If there is no more to scrobble for this media
        if next(cache[key].scrobble_ready) == nil then
            cache[key].scrobble_ready = nil
        end
    end
end


------------------------------------------------------------------------------
-- Function being run to determine the media status
------------------------------------------------------------------------------
local
function determine_media_status()
    ran_timers = timers.run()
    vlc.msg.dbg('Timers ran: ' .. dump(ran_timers))

    if vlc.input.is_playing() then
        -- Get the information on the media being currently played
        local infos = get_current_info()

        -- If the media being played is not the same as during the
        -- previous loop, we have stuff to do
        if last_infos and not equals(last_infos.imdb, infos.imdb) then
            media_is_stopped(last_infos)
        end
        last_infos = infos

        -- If we do not have a current info table (perhaps only using
        -- vlc for music ?), we do not want to do anything
        if not infos then
            return
        end

        -- We're going to run a different function if the media is
        -- currently playing or paused
        if vlc.playlist.status() == 'paused' then
            media_is_paused(infos)
            return
        end

        -- If we reach here, it's that the media is currently playing
        media_is_playing(infos)

    elseif last_infos then
        -- If we reach here, it's that the media has been stopped, and
        -- we still had its information, so we can run the function to
        -- terminate properly all that's related to the media
        media_is_stopped(last_infos)
        last_infos = nil
    end
end


------------------------------------------------------------------------------
-- Function to check if there is any update available for TraktForVLC
------------------------------------------------------------------------------
local
function check_update(filepath, install_output)
    command = {
        'update',
        '--vlc-lua-directory', ospath.dirname(path_to_helper),
        '--vlc-config', vlc.config.configdir(),
        '--yes',
    }
    if install_output then
        table.insert(command, 1, '--loglevel')
        table.insert(command, 2, 'INFO')
    end
    if filepath then
        table.insert(command, '--file')
        table.insert(command, filepath)
    else
        table.insert(command, '--release-type')
        table.insert(command, trakt.config.helper.update.release_type)
    end
    if trakt.config.helper.mode == 'service' then
        table.insert(command, '--service')
        table.insert(command, '--service-host')
        table.insert(command, tostring(trakt.config.helper.service.host))
        table.insert(command, '--service-port')
        table.insert(command, tostring(trakt.config.helper.service.port))
    end
    if trakt.config.helper.update.action == 'install' then
        table.insert(command, '--install')
        if install_output then
            table.insert(command, '--install-output')
            table.insert(command, install_output)
        else
            table.insert(command, '--discard-install-output')
        end
    elseif trakt.config.helper.update.action == 'download' then
        table.insert(command, '--download')
    end
    local update = call_helper(command)
    if not update or next(update) == nil then
        vlc.msg.info('No update found for TraktForVLC.')
        return
    end

    if update.version then
        vlc.msg.info('Found TraktForVLC version ' .. update.version)
    else
        update.version = 'unknown'
    end

    if update.downloaded then
        vlc.msg.info('TraktForVLC version ' ..
                     update.version .. ' has been downloaded')
    end

    if update.installing then
        vlc.msg.info('TraktForVLC version ' ..
                     update.version .. ' is being installed ' ..
                     '(will work after VLC restart)')
    end

    return true
end

------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- MAIN OF THE INTERFACE                                                    --
------------------------------------------------------------------------------
------------------------------------------------------------------------------

-- Print information about the interface when starting up
vlc.msg.info('TraktForVLC ' .. __version__ .. ' - Lua implementation')

-- Check that local configuration parameters are authorized
local bad_config = false
for k, v in pairs(config) do
    if k ~= 'autostart' and
            k ~= 'check_update' and
            k ~= 'init_auth' then
        vlc.msg.error('Configuration option ' .. tostring(k) ..
                      'is not recognized.')
        bad_config = true
    end
end
if bad_config then
    vlc.msg.error('Quitting VLC.')
    vlc.misc.quit()
end

-- Locate the helper
if not path_to_helper then
    path_to_helper = get_helper()
end
if not path_to_helper then
    local func
    if config.autostart then
        func = vlc.msg.err
    else
        func = error
    end
    func('Unable to find the trakt helper, have you installed ' ..
         'TraktForVLC properly? - You can use the TRAKT_HELPER ' ..
         'environment variable to specify the location of the ' ..
         'helper')
else
    vlc.msg.info('helper: ' .. path_to_helper)
end

if config.autostart then
    if config.autostart == 'enable' then
        -- Enable 'lua' as extra VLC interface
        local current_extraintf = vlc.config.get('extraintf')
        local found_lua_intf = false
        if current_extraintf then
            for intf in string.gmatch(current_extraintf, "([^:]*)") do
                if intf == 'luaintf' then
                    found_lua_intf = true
                    break
                end
            end
        end
        if not found_lua_intf then
            if current_extraintf then
                current_extraintf = current_extraintf .. ':luaintf'
            else
                current_extraintf = 'luaintf'
            end
            vlc.config.set('extraintf', current_extraintf)
            vlc.msg.info('Lua interface enabled')
        else
            vlc.msg.info('Lua interface already enabled')
        end

        -- Set the lua interface as being 'trakt'
        local current_lua_intf = vlc.config.get('lua-intf')
        if current_lua_intf ~= 'trakt' then
            vlc.config.set('lua-intf', 'trakt')
            vlc.msg.info('trakt Lua interface enabled')
        else
            vlc.msg.info('trakt Lua interface already enabled')
        end

        vlc.msg.info('VLC is configured to automatically use TraktForVLC')
    elseif config.autostart == 'disable' then
        local current_extraintf = vlc.config.get('extraintf')
        local found_lua_intf = false
        local all_other_intf = {}
        if current_extraintf then
            for intf in string.gmatch(current_extraintf, "([^:]*)") do
                if intf == 'luaintf' then
                    found_lua_intf = true
                else
                    table.insert(all_other_intf, intf)
                end
            end
        end
        if found_lua_intf then
            vlc.config.set('extraintf', table.concat(all_other_intf, ':'))
            vlc.msg.info('Lua interface disabled')
        else
            vlc.msg.info('Lua interface already disabled')
        end

        vlc.msg.info('VLC is configured not to use TraktForVLC')
    else
        vlc.msg.err('Unsupported value defined for autostart; must ' ..
                    'be one of \'enable\' or \'disable\'')
    end
    vlc.misc.quit()
elseif config.check_update then
    if not config.check_update.file then
        vlc.msg.err('You forgot to specify the file to use for the update test')
    else
        vlc.msg.info('Will run check_update with parameter: ' .. config.check_update.file)
        if config.check_update.output then
            vlc.msg.info('Output will be written to ' .. config.check_update.output)
        else
            vlc.msg.info('Output will be discarded')
        end
        worked = check_update(config.check_update.file, config.check_update.output)
        if not worked then
            vlc.msg.err('Error while trying to update!')
        else
            vlc.msg.info('Sleeping ' .. tostring(config.check_update.wait) ..
                         ' seconds to emulate the fact that VLC is using the files...')
            local i = config.check_update.wait
            while i > 0 do
                sleep(1)
                i = i - 1
                if i % 10 == 0 then
                    vlc.msg.info(tostring(i) .. ' seconds left...')
                end
            end
        end
        vlc.msg.info('Exiting.')
    end
    vlc.misc.quit()
elseif config.init_auth then
    -- Delete current configuration, as we are going to regenerate it
    trakt.configured = false
    trakt.config.auth = {}
    save_config(trakt.config)

    -- Start the process to authenticate TraktForVLC with Trakt.tv
    trakt.device_code()

    -- Exit VLC when finished
    vlc.misc.quit()
else
    -- If TraktForVLC is not yet configured with Trakt.tv, launch the device code
    -- authentication process
    if not trakt.configured then
        trakt.device_code()
    end

    -- Register timers
    timers.register(process_scrobble_ready, (
        trakt.config.media.stop.check_unprocessed_delay * 1000000.))
    timers.register(cleanup_cache, (
        trakt.config.cache.delay.cleanup * 1000000.))
    if trakt.config.helper.update.check_delay ~= 0 and
            __version__ ~= '0.0.0a0.dev0' then
        timers.register(check_update, (
            trakt.config.helper.update.check_delay * 1000000.))
    end

    -- Main loop
    while trakt.configured do
        determine_media_status()
        sleep(1)

        -- Check if VLC is still running; if it is not, we want to
        -- stop the loop now - We check that by checking the current
        -- volume, and if VLC has been stopped, this command will
        -- return -256
        if vlc.volume.get() == -256 then
            break
        end
    end
end

vlc.msg.info('TraktForVLC shutting down.')
