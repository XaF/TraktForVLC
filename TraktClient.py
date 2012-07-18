#!/usr/bin/env python

import simplejson as json
import urllib
import logging
import time

from hashlib import sha1

class TraktClient(object):
    def __init__(self, apikey, username, password):
        self.username = username
        self.password = sha1(password).hexdigest()
        self.apikey = apikey
        self.log = logging.getLogger("TraktClient")
        
        self.log.debug("TraktClient logger initialized")
    
    def call_method(self, method, data = {}, post=True, retry=3):
        if (retry == -1):
            self.log.error("Failed to call method " + method)
        
        method = method.replace("%API%", self.apikey)
        
        if (post):
            data["username"] = self.username
            data["password"] = self.password
            
            encoded_data = json.dumps(data);
            
            self.log.debug(encoded_data)

            try:
                stream = urllib.urlopen("http://api.trakt.tv/" + method,
                                        encoded_data)
                resp = stream.read()
                self.log.debug("Response from Trakt: " + resp)

                resp = json.loads(resp)
                if ("error" in resp):
                    raise TraktError(resp["error"])
            except (IOError, json.JSONDecodeError):
                self.log.exception("Failed calling method, retrying attempt #" + str(retry - 1) + ".")
                time.sleep(5)
                self.call_method(method, data, post, retry - 1)
                
        else:
            pass #Decisions...

    def update_media_status(self, title, year, duration, progress, plugin_ver,
                            media_center_ver, media_center_date,
                            tv=False, season=-1, episode=-1, scrobble=False):
        data = {'title': title,
                'year': year,
                'duration': duration,
                'progress': progress,
                'plugin_version': plugin_ver,
                'media_center_version': media_center_ver,
                'media_center_date': media_center_date}
        
        method = "%s/%s/" % ("show" if tv else "movie",
                             "scrobble" if scrobble else "watching")
        
        self.log.debug("Calling API Method " + method)
        
        method += "%API%"
        
        if (tv):
            data["season"] = season
            data["episode"] = episode
        
        self.call_method(method, data)
    
    def cancelWatching(self):
        self.call_method("show/cancelwatching/%API%")
        self.call_method("movie/cancelwatching/%API%")

class TraktError(Exception):
    def __init__(self, msg):
        self.msg = msg