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

from time import localtime, strftime, time
from enigma import getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.Language import language
import os
import gettext

WIDTH = getDesktop(0).size().width()
HEIGHT = getDesktop(0).size().height()

APP_PREFIX = "[FILMWEB]"

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

def __print_info(prefix, level, nfo, data):
    #txt = "[" + prefix + "] " + level + '' + nfo
    #if data is not None:
    #    txt = txt + ": " + data
    tm = strftime('%Y-%m-%d %H:%M:%S', localtime(time()))
    print prefix, tm, level, nfo, data or ''

def print_error(nfo, data=None):
    __print_info(APP_PREFIX, 'ERROR', nfo, data)
    
def print_debug(nfo, data=None):
    pass
    #__print_info(APP_PREFIX, 'DEBUG', nfo, data)
    
def print_info(nfo, data=None):
    __print_info(APP_PREFIX, 'INFO', nfo, data)


localeInit()
language.addCallback(localeInit)


