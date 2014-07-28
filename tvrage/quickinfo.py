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
from util import _fetch
from exceptionsTvRage import ShowNotFound

BASE_URL = 'http://services.tvrage.com/tools/quickinfo.php'


def fetch(show, exact=False, ep=None):
    query_string = '?show=' + quote(show)
    if exact:
        query_string = query_string + '&exact=1'
    if ep:
        query_string = query_string + '&ep=' + quote(ep)
    resp = _fetch(BASE_URL + query_string).read()
    show_info = {}
    if 'No Show Results Were Found For' in resp:
        raise ShowNotFound(show)
    else:
        data = resp.replace('<pre>', '').splitlines()
        for line in data:
            k, v = line.split('@')
            # TODO: use datetimeobj for dates
            show_info[k] = (v.split(' | ') if ' | ' in v else
                            (v.split('^') if '^' in v else v))
    return show_info
