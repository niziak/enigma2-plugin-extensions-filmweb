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

from __common__ import print_info, _
from enigma import eServiceReference

from Screens.EpgSelection import EPGSelection
#from Screens.InfoBarGenerics import InfoBarEPG
from Screens.ChannelSelection import SimpleChannelSelection

from Components.ActionMap import ActionMap


class FilmwebChannelSelection(SimpleChannelSelection):
    def __init__(self, session):
        SimpleChannelSelection.__init__(self, session, _("Channel Selection"))
        self.skinName = "SimpleChannelSelection"

        self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
            { "showEPGList": self.processSelected }
        )

    def processSelected(self):
        ref = self.getCurrentSelection()
        print_info("Channel selected", str(ref) + ", flags: " + str(ref.flags))
        # flagDirectory = isDirectory|mustDescent|canDescent
        if (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
            # when directory go to descent
            self.enterPath(ref)
        elif not (ref.flags & eServiceReference.isMarker):
            # open the event selection screen and handle on close event
            self.session.openWithCallback(
                self.onClosed,
                FilmwebEPGSelection,
                ref
            )

    def onClosed(self, ret = None):
        print_info("EPG Closed", str(ret)) 
        if ret:
            self.close(ret)
    
class FilmwebEPGSelection(EPGSelection):
    def __init__(self, session, ref, screen=None):
        EPGSelection.__init__(self, session, ref)
        self.skinName = "EPGSelection"
        self["key_red"].setText(_("Lookup"))
        self.screen = screen

    def infoKeyPressed(self):
        print_info("Info Key pressed", "")
        self.lookup()
        
    def zapTo(self):
        self.lookup()
        
    #def onSelectionChanged(self):
    #    cur = self["list"].getCurrent()
    #    evt = cur[0]
    #    print_info("Selection Changed Event", str(evt))        
    
    def lookup(self):
        cur = self["list"].getCurrent()
        evt = cur[0]
        sref = cur[1]        
        print_info("Lookup EVT", str(evt))
        print_info("Lookup SREF", str(sref)) 
        if not evt: 
            return
        
        # when openPlugin is TRUE - open filmweb data window
        # otherwise only return the selected event name           
        if self.screen is not None:
            print_info("EVT short desc", str(evt.getShortDescription()))
            print_info("EVT ext desc", str(evt.getExtendedDescription()))
            print_info("EVT ptr", str(evt.getPtrString()))
            self.session.open(self.screen, evt.getEventName())
        else:
            self.close(evt.getEventName())              
