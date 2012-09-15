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

from __future__ import print_function
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.Language import language
from os import environ as os_environ
import gettext
import Filmweb
import mautils
    
def localeInit():
    lang = language.getLanguage()[:2] 
    os_environ["LANGUAGE"] = lang 
    Filmweb.print_info("Language", lang)
    gettext.bindtextdomain("Filmweb", resolveFilename(SCOPE_PLUGINS, "Extensions/Filmweb/locale"))

def _(txt):
    return Filmweb._(txt)

localeInit()
language.addCallback(localeInit)

def main(session, eventName="", **kwargs):    
    reload(mautils)
    reload(Filmweb)
    try:
        session.open(Filmweb.Filmweb, eventName)
    except:
        import traceback
        traceback.print_exc()
        
def eventinfo(session, servicelist, **kwargs):
    reload(mautils)
    reload(Filmweb)    
    try:
        ref = session.nav.getCurrentlyPlayingServiceReference()
        Filmweb.print_info("Current Service ref", str(ref))
        session.open(Filmweb.FilmwebEPGSelection, ref)
    except:
        import traceback
        traceback.print_exc()      
        
def Plugins(path, **kwargs):
    p = [PluginDescriptor(name="Filmweb Details",
                           description=_("Query details from the Filmweb.pl Database"),
                           where=PluginDescriptor.WHERE_PLUGINMENU,
                           needsRestart=False,
                           fnc=main),
         PluginDescriptor(name="Filmweb Details",
            description=_("Query details from the Filmweb.pl Database"),
            where=PluginDescriptor.WHERE_EVENTINFO,
            fnc=eventinfo,
            needsRestart=False,
            )]
    return p
