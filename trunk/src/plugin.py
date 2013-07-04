######################################################################
# Copyright (c) 2012 - 2013 Marcin Slowik
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
import tvsearch
import rmdr

from Screens.ChannelSelection import ChannelSelection

pReminder = rmdr.Reminder()

'''
ChannelSelection_zap = ChannelSelection.zap

def zap(self):
    print_debug('ChannelSelection_zap')
    if pReminder.session:
        session = pReminder.session
        serv = session.nav.getCurrentService()
        print_debug('ZAP data: ', 'Session: %s, Service: %s' % (str(session), str(serv)))
    ChannelSelection_zap(self)

ChannelSelection.zap = zap
'''

def reloadlibs():
    reload(logger)
    reload(mautils)
    reload(comps)
    reload(config)
    reload(engine)
    reload(mselection)
    reload(tvsearch)
    reload(movieguide)
    reload(mainlib)
    reload(rmdr)

def shortinfo(session, **kwargs):
    reloadlibs()
    try:
        session.open(rmdr.ShortInfoScreen)
    except:
        import traceback
        traceback.print_exc()

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
        session.open(mainlib.Filmweb, None)
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

def sessionstart(reason, **kwargs):
    reloadlibs()
    try:
        if reason == 0:
            pReminder.start(kwargs["session"])
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
         PluginDescriptor(name=_("Short Movie Info"),
                           description=_("Show actually presented movies on selected channels"),
                           where=PluginDescriptor.WHERE_PLUGINMENU,
                           needsRestart=False,
                           fnc=shortinfo),
         PluginDescriptor(name=_("Filmweb Details"),
            description=_("Query details from the Filmweb.pl Database"),
            where=PluginDescriptor.WHERE_EVENTINFO,
            fnc=eventinfo,
            needsRestart=False,
            ),
         PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART,
                          fnc=sessionstart)]
    return p





