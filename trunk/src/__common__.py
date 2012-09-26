######################################################################
# Copyright (c) 2012 Marcin Slowik
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#
# You may use and distribute this software under the terms of the
# GNU General Public License, version 3 or later
######################################################################

from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Components.Language import language
from Screens.Screen import Screen
import os
import gettext
import sys


def _(txt):
    t = gettext.dgettext("Filmweb", txt)
    if t == txt:
        t = gettext.gettext(txt)
    return t

def localeInit():
    lang = language.getLanguage()[:2] 
    os.environ["LANGUAGE"] = lang 
    print "Language: " + lang
    gettext.bindtextdomain("Filmweb", resolveFilename(SCOPE_PLUGINS, "Extensions/Filmweb/locale"))

def __print_info(prefix, nfo, data):
    txt = "[" + prefix + "] " + nfo
    if data is not None:
        txt = txt + ": " + data
    print txt

def print_info(nfo, data=None):
    __print_info("FILMWEB", nfo, data)


class DefaultScreen(Screen):
    def __init__(self, session, temat):
        mf = sys.modules[__name__].__file__
        self.ppath = os.path.dirname(mf)
        print_info('Plugin path', self.ppath)
        fn = resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/menu/BlackHoleEpgBackup.png')
        if (os.path.exists(fn)):
            skin = "%s/resource/" + temat + "_skin_bh.xml" % (self.ppath)
        else:
            skin = "%s/resource/" + temat + "_skin_df.xml" % (self.ppath)
        f = open(skin, "r")
        self.skin = f.read()
        f.close()
        
        Screen.__init__(self, session)
        print_info("Screen init")
        
        

localeInit()
language.addCallback(localeInit)
