#!/usr/bin/env python
from easygui import multenterbox, buttonbox, codebox
from vlcrc import VLCRemote
import logging

def get_group(groups, vlc):
    choice = buttonbox(msg='Assign a group', title='Assign a group',
                        choices=groups)
    fn = vlc.get_filename()
    groups_dict[fn] = choice

def main():
    log = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    if 0:
        groups = multenterbox(msg='Enter groups you would like to file to',
                                title='Enter Groups', fields=(1,2,3,4,5),
                                values=('yes','no','maybe','other'))
        groups = filter(None,groups)
    else:
        groups=('yes','no','maybe','other')

    vlc = VLCRemote('localhost', 4222)
    groups_dict = {}

    while 1:
        menu_selection = buttonbox(title='Menu',choices=(
                                    'Next','Set Group','Jump','Quit'))
        if menu_selection == 'Next':
            vlc.next()
        elif menu_selection == 'Set Group':
            choice = buttonbox(msg='Assign a group', title='Assign a group',
                                choices=groups)
            fn = vlc.get_filename()
            groups_dict[fn] = choice
        elif menu_selection == 'Jump':
            vlc.skip()
        else:
            break

    reorg = {}
    for fname in groups_dict:
        l = reorg.get(groups_dict[fname],[])
        l.append(fname)
        reorg[groups_dict[fname]] = l

    str = ''
    for grp in reorg:
        str += '--%s\n'%grp
        for fname in reorg[grp]:
            str += '%s\n'%fname
    print str

