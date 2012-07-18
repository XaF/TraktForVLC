# Copyright (c) 2009, Christian Kreutzer
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from urllib2 import urlopen, URLError, quote

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et
    
BASE_URL = 'http://www.tvrage.com/feeds/%s.php?%s=%s'
    
def _fetch(url, node=None):
    """fetches the response of a simple xml-based webservice. If node is omitted 
    the root of the parsed xml doc is returned as an ElementTree object
    otherwise the requested node is returned"""
    retval = None
    try:
        xmldoc = urlopen(url)
    except URLError, e:
        try:
	    print(str(e))
        except:
            return str(e)
    else:
        result = et.parse(xmldoc)
        root = result.getroot()
        if not node:
            retval = root
        else:
            retval = root.find(node)
    return retval
    
def search(show, node=None):
    return _fetch(BASE_URL % ('search','show', quote(show)), node)
    
def full_search(show, node=None):
    return _fetch(BASE_URL % ('full_search','show', quote(show)), node)
    
def showinfo(sid, node=None):
    return _fetch(BASE_URL % ('showinfo', 'sid', sid), node)
    
def episode_list(sid, node=None):
    return _fetch(BASE_URL % ('episode_list', 'sid', sid), node)
    
def full_show_info(sid, node=None):
    return _fetch(BASE_URL % ('full_show_info', 'sid', sid), node)
    
