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

from urllib2 import urlopen, URLError
from BeautifulSoup import BeautifulSoup


class TvrageError(Exception):
    """ Base class for custom exceptions"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class TvrageRequestError(TvrageError):
    """ Wrapper for HTTP 400 """
    pass


class TvrageNotFoundError(TvrageError):
    """ Wrapper for HTTP 404"""
    pass


class TvrageInternalServerError(TvrageError):
    """ Wrapper for HTTP 500"""
    pass


def _fetch(url):
    try:
        result = urlopen(url)
    except URLError, e:
        if 400 == e.code:
            raise TvrageRequestError(str(e))
        elif 404 == e.code:
            raise TvrageNotFoundError(str(e))
        elif 500 == e.code:
            raise TvrageInternalServerError(str(e))
        else:
            raise TvrageError(str(e))
    except Exception, e:
        raise TvrageError(str(e))
    else:
        return result


def parse_synopsis(page, cleanup=None):
    soup = BeautifulSoup(page)
    try:
        result = soup.find('div', attrs={'class': 'show_synopsis'}).text
        #cleaning up a litle bit
        if cleanup:
            result, _ = result.split(cleanup)
        return result
    except AttributeError, e:
        print('parse_synopyis - BeautifulSoup.find(): %s' % e)
