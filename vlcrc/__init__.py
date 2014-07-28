import telnetlib
import re
import logging

class VLCBadReturn(Exception):
    pass

class VLCRemote(object):
    def __init__(self, hostname, port, timeout=3):
        self.cnx = telnetlib.Telnet(hostname, port)
        self.log = logging.getLogger('VLCRemote')
        self.timeout = timeout

    def _command(self, cmd, return_re=None, raw=False, args=None):
        
        # Clean out anything waiting before starting the command
        cached = self.cnx.read_eager()
        if cached != '':
            self.log.debug('cleaning cache')
            self.log.debug('<- Recived: %s'%cached.strip())

        # FIXME - Ugly
        cmd_str = '%s'%cmd
        if args is not None:
            cmd_str += ' '
            cmd_str += ' '.join(args)
        cmd_str += '\n'

        self.log.debug('-> Sending: %s'%cmd_str.strip())
        self.cnx.write(cmd_str)

        if not raw:
            cmd_end = '%s: returned '%cmd
            cmd_ret = self.cnx.read_until(cmd_end,self.timeout)
            if not cmd_ret.endswith(cmd_end):
                err_str = 'Sent: %s'%cmd_str
                err_str += 'Expected: %s\n'%cmd_end
                err_str += 'Got: %s'%cmd_ret
                self.log.warn(err_str)
                raise VLCBadReturn(cmd_ret)

            good = '0 (no error)\r\n'
            cmd_fin = self.cnx.read_until('\r\n',3)
            cmd_ret += cmd_fin
            if cmd_fin != good:
                err_str = 'Sent: %s'%cmd_str
                err_str += 'Expected: %s%s'%(cmd_end,good)
                err_str += 'Got: %s'%(cmd_ret)
                self.log.warn(err_str)
                raise VLCBadReturn(cmd_ret)
            self.log.debug('<- Recived: %s'%cmd_ret.strip())
        else:
            index, match, cmd_ret = self.cnx.expect([return_re], self.timeout)
            if match is None:
                raise VLCBadReturn(cmd_ret)
            self.log.debug('<- Recived: %s'%cmd_ret.strip())
            return match

        if return_re is None:
            return True

        match = return_re.search(''.join((cmd_ret,cmd_fin)))
        return match

    def get_filename(self):
        fn_re = re.compile('input: file://(?P<fn>.+?) \)',re.MULTILINE)
        match = self._command('status', fn_re)
        fn = match.groupdict()['fn']
        fn = fn.replace('%20',' ')
        return fn

    def restart(self):
        self._command('seek',args=(0,))

    def skip(self, duration=60):
        time_re = re.compile('(?P<time>\d+)\r\n')
        ret_match = self._command('get_time', time_re, raw=True)
        time = ret_match.groupdict()['time']
        gt = str(int(time)+duration)
        self._command('seek',args=(gt,))

    def next(self):
        self._command('next')

    def get_title(self, regex):
      fn_re = re.compile(regex, re.IGNORECASE | re.MULTILINE)
      title = self._command('get_title', fn_re, raw=True)
      return title

    def is_playing(self):
      fn_re = re.compile('(?P<playing>.+)')
      playing = self._command('is_playing', fn_re, raw=True)
      playing = playing.groupdict()['playing']
      return playing

    def get_info(self):
      fn_re = re.compile('(?P<info>.+)')
      info = self._command('info', fn_re, raw=True)
      info = info.groupdict()['info']
      return info

    def get_status(self):
      fn_re = re.compile('(?P<status>.+)')
      status = self._command('status')
      #status = status.groupdict()['status']
      return status

    def get_length(self):
      fn_re = re.compile('(?P<length>[0-9]+)')
      length = self._command('get_length',fn_re, raw=True)
      length = length.groupdict()['length']
      return length

    def get_time(self):
      fn_re = re.compile('(?P<time>[0-9]+)')
      time = self._command('get_time',fn_re, raw=True)
      time = time.groupdict()['time']
      return time

    def close(self):
      self.cnx.close()
