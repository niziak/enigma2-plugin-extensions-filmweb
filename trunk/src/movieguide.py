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

from enigma import eEPGCache, eServiceReference
from time import localtime, strftime
from __common__ import print_info, _, DefaultScreen
from mselection import FilmwebRateChannelSelection

from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText

class MovieGuide(DefaultScreen):
    def __init__(self, session):
        DefaultScreen.__init__(self, session, 'movieguide')
        
        self.list = []
        self.services = []
        self.epg = eEPGCache.getInstance()        
        
        self.createGUI()
        self.initActions()
        
        self.__updateServices()
                
    # --- Screen Manipulation ------------------------------------------------  
    def createGUI(self):
        self["list"] = List(self.list)
        self["key_red"] = StaticText(_("Config"))
        self["key_green"] = StaticText("")
        self["key_yellow"] = StaticText("")
        self["key_blue"] = StaticText("")
    
    def initActions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.okAction,
            "cancel": self.cancelAction,
            "red": self.redAction,
            "green": self.greenAction,
            "yellow": self.yellowAction,
            "blue": self.blueAction
        }, -1)
    
    # --- Actions definition ------------------------------------------------   
    def okAction(self):
        print_info("OK action")
    
    def cancelAction(self):
        print_info("CANCEL action")
        self.close()
    
    def redAction(self):
        print_info("RED action")
        self.session.openWithCallback(self.__updateServices, FilmwebRateChannelSelection)
    
    def greenAction(self):
        print_info("GREEN action")
    
    def yellowAction(self):
        print_info("YELLOW action")
    
    def blueAction(self):
        print_info("BLUE action")
            
    # --- Overwrite methods ---------------------------------------------
    
    # --- Public methods ------------------------------------------------
    
    '''
    def selectionScreenClosed(self, res=None):
        
            
        try: 
            #serviceHandler = eServiceCenter.getInstance()
            txt = 
            if txt:
                entries = txt.split('|')
                for x in entries:
                    ref = 
                    print_info('--> SERV', str(x) + ', name: ' + ref.getName())
                    if self.epg.startTimeQuery(ref) != -1:
                        evt = self.epg.getNextTimeEntry()
                        while evt:
                            ename = evt and evt.getEventName()
                            edesc = evt and evt.getShortDescription()
                            eext = evt and evt.getExtendedDescription()
                            ebgn = evt and evt.getBeginTimeString()
                            edur = evt and evt.getDuration()
                            ebgnt = evt and evt.getBeginTime()
                            print_info('----> EVENT', 'name: ' + str(ename) + ', from: ' + strftime("%Y-%m-%d %H:%M", (localtime(ebgnt))) + ' to: ' + strftime("%H:%M",(localtime(ebgnt + edur))))
                            evt = self.epg.getNextTimeEntry()
                            #self.engine.query(MT_MOVIE, ename, None, False, self.searchMoviesCallback)
        except:
            import traceback
            traceback.print_exc()  
    '''        
    # --- Private methods ------------------------------------------------
    
    def __updateServices(self, res=None):
        self.services = []
        txt = config.plugins.mfilmweb.selserv.getText()
        if txt:
            entries = txt.split('|')
            for x in entries:
                self.services.append(eServiceReference(x))
    
    
    
            
            
    