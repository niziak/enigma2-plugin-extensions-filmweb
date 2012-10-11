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

from Plugins.Plugin import PluginDescriptor
from __common__ import  _
import logger 
import mselection
import mainlib
import config
import mautils
import comps
import engine
import movieguide
    
def reloadlibs():
    reload(logger)   
    reload(mautils)    
    reload(comps)
    reload(config)
    reload(engine)
    reload(mselection)  
    reload(movieguide)      
    reload(mainlib)
        
def guide(session, **kwargs):
    reloadlibs()
    try:
        session.open(movieguide.MovieGuide)
    except:
        import traceback
        traceback.print_exc()
        
def main(session, eventName="", **kwargs):
    reloadlibs()
    try:
        session.open(mainlib.Filmweb, eventName)
    except:
        import traceback
        traceback.print_exc()
        
def eventinfo(session, servicelist, **kwargs):
    reloadlibs()  
    try:
        ref = session.nav.getCurrentlyPlayingServiceReference()
        print "Current Service ref", str(ref)
        session.open(mselection.FilmwebEPGSelection, ref, mainlib.Filmweb)
    except:
        import traceback
        traceback.print_exc()      
        
def Plugins(path, **kwargs):
    p = [PluginDescriptor(name=_("Filmweb Details"),
                           description=_("Query details from the Filmweb.pl Database"),
                           where=PluginDescriptor.WHERE_PLUGINMENU,
                           needsRestart=False,
                           fnc=main),
         PluginDescriptor(name=_("Movie Guide"),
                           description=_("Query movies info on selected channels"),
                           where=PluginDescriptor.WHERE_PLUGINMENU,
                           needsRestart=False,
                           fnc=guide),
         PluginDescriptor(name=_("Filmweb Details"),
            description=_("Query details from the Filmweb.pl Database"),
            where=PluginDescriptor.WHERE_EVENTINFO,
            fnc=eventinfo,
            needsRestart=False,
            )]
    return p
