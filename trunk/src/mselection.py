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

from __common__ import  _
from logger import print_info, print_debug
from enigma import eServiceReference, gRGB, eListboxServiceContent
from Components.config import config, configfile
#from Tools.LoadPixmap import LoadPixmap
#from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN

from Screens.EpgSelection import EPGSelection
#from Screens.InfoBarGenerics import InfoBarEPG
from Screens.ChannelSelection import SimpleChannelSelection

from Components.ActionMap import ActionMap

class FilmwebRateChannelSelection(SimpleChannelSelection):
    def __init__(self, session):
        SimpleChannelSelection.__init__(self, session, _("Channel Selection"))
        self.skinName = "SimpleChannelSelection"
        
        self.onLayoutFinish.append(self.__layoutFinished)
        self.onClose.append(self.__onClose)
        
    def channelSelected(self):
        ref = self.getCurrentSelection()
        print_debug("Channel selected", str(ref) + ", flags: " + str(ref.flags))
        if (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
            self.enterPath(ref)
        # when service is not directory and is not marker that means playable service
        elif not (ref.flags & eServiceReference.isMarker):
            refx = self.servicelist.getCurrent()
            if self.servicelist.isMarked(refx):
                self.servicelist.removeMarked(refx)
            else:
                self.servicelist.addMarked(refx)
                
    def __layoutFinished(self):    
        try:
            self.__load()
            self.servicelist.l.setColor(eListboxServiceContent.markedForeground, gRGB(0x58BCFF))
            self.servicelist.l.setColor(eListboxServiceContent.markedForegroundSelected, gRGB(0xF0B400))
            #self.servicelist.instance.setForegroundColorSelected(gRGB(0xF0B400))
        except:
            import traceback
            traceback.print_exc()         
        
    def setModeRadio(self):
        pass
    
    def __load(self):
        txt = config.plugins.mfilmweb.selserv.getText()
        print_debug("config", str(txt))
        if txt:
            entries = txt.split('|')
            for x in entries:
                self.servicelist.addMarked(eServiceReference(x))
        
    def __onClose(self):
        marked = self.servicelist.getMarked()
        txt = ''
        for x in marked:
            print_debug("marked", str(x)) 
            txt += str(x) + '|'   
        txt = txt.strip('|')
        config.plugins.mfilmweb.selserv.setValue(txt)
        config.plugins.mfilmweb.save()
        configfile.save()
        
        '''
        try:
            from ServiceReference import ServiceReference
            sfile = open('/tmp/services.dat', "w")
            lista = self.servicelist.getRootServices()
            for x in lista:
                print_debug('ser', x)
                ref = eServiceReference(x)
                ser = ServiceReference(ref)
                sfile.write(x + ',' + ser.getServiceName() + ',\n')
        except Exception, e:
            import traceback
            traceback.print_exc() 
        finally:
            if sfile is not None:
                sfile.close()
        '''                
    
class FilmwebChannelSelection(SimpleChannelSelection):
    def __init__(self, session):
        SimpleChannelSelection.__init__(self, session, _("Channel Selection"))
        self.skinName = "SimpleChannelSelection"

        self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
            { "showEPGList": self.processSelected }
        )

    def processSelected(self):
        ref = self.getCurrentSelection()
        print_debug("Channel selected", str(ref) + ", flags: " + str(ref.flags))
        # flagDirectory = isDirectory|mustDescent|canDescent
        if (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
            self.enterPath(ref)
        elif not (ref.flags & eServiceReference.isMarker):
            self.session.openWithCallback(
                self.onClosed,
                FilmwebEPGSelection,
                ref
            )

    def onClosed(self, ret = None):
        print_debug("Closed", str(ret)) 
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
    #    print_debug("Selection Changed Event", str(evt))        
    
    def lookup(self):
        cur = self["list"].getCurrent()
        evt = cur[0]
        sref = cur[1]        
        print_debug("Lookup EVT", str(evt))
        print_debug("Lookup SREF", str(sref)) 
        if not evt: 
            return
        
        # when openPlugin is TRUE - open filmweb data window
        # otherwise only return the selected event name           
        if self.screen is not None:
            print_debug("EVT short desc", str(evt.getShortDescription()))
            print_debug("EVT ext desc", str(evt.getExtendedDescription()))
            print_debug("EVT ptr", str(evt.getPtrString()))
            self.session.open(self.screen, evt.getEventName())
        else:
            self.close(evt.getEventName())              
