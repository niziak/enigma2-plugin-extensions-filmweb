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

import twisted.internet.defer as defer

from enigma import eEPGCache, eServiceReference
from time import localtime, strftime
from __common__ import print_info, _
from mselection import FilmwebRateChannelSelection
from comps import DefaultScreen
from engine import FilmwebEngine, MT_MOVIE

from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText

sorted_data = lambda data, idx: [b for a,b in sorted((tup[idx], tup) for tup in data)]

class MovieGuide(DefaultScreen):
    def __init__(self, session, engine=None):
        DefaultScreen.__init__(self, session, 'movieguide')
        
        self.list = []
        self.services = []
        self.epg = eEPGCache.getInstance()        
        
        if engine:
            self.engine = engine
        else:
            self.engine = FilmwebEngine()
            
        self.createGUI()
        self.initActions()
        
        self.refreshList()
                
    # --- Screen Manipulation ------------------------------------------------  
    def createGUI(self):
        self["list"] = List(self.list)
        self["key_red"] = StaticText(_("Config"))
        self["key_green"] = StaticText(_("Refresh"))
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
        self.session.openWithCallback(self.refreshList, FilmwebRateChannelSelection)
    
    def greenAction(self):
        print_info("GREEN action")
        self.refreshList()
    
    def yellowAction(self):
        print_info("YELLOW action")
    
    def blueAction(self):
        print_info("BLUE action")
            
    # --- Overwrite methods ---------------------------------------------
    
    # --- Public methods ------------------------------------------------    
    
    def refreshList(self, res=None):
        def refreshListCallback(resultlist, typ, evt):
            print_info('RESULT', 'type: ' + str(typ) + ', list: ' + str(resultlist))
            if resultlist and len(resultlist) == 1:
                evt[4] = resultlist[0]                 
            return evt
                
        try:
            print_info('Update services ...')
            self.__updateServices()
            print_info('Process events for services ...')
            evts = self.__getEvents()
            # sort events by begin time
            evts = sorted_data(evts, 2)  
            ds = []                  
            print_info('Query events in Filmweb.pl ...')  
            for evt in evts:
                event = evt[3]
                print_info('Query event', str(event.getEventName()))
                df = self.engine.query(self.__getQueryType(event), self.__getQueryTitle(event), 
                                       self.__getQueryYear(event), False, refreshListCallback, evt)
                ds.append(df)
            print_info('Create DeferredList')
            dlist = defer.DeferredList(ds, consumeErrors=True)
            print_info('Add DeferredList callback')
            dlist.addCallback(self.refreshListDone)                
        except:
            import traceback
            traceback.print_exc()  
    
    def refreshListDone(self, result):
        print_info('Refresh List Done')
        self.list = []
        
        # (ref.getPath(), evt.getEventName(), evt.getBeginTime(), evt, None)
        # (strig_rep, URL, string_rep_first_line, title, rating, year, country)
        
        for e, (success, value) in enumerate(result):
            print_info('refreshListDone Entry', '[%d]:' % e),
            if success:
                print_info('refreshListDone Success', str(value))
            else:
                print_info('refreshListDone Failure', str(value.getErrorMessage()))
        
        self["list"].setList(self.list)

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
    
    def __getQueryType(self, evt):
        return MT_MOVIE
        
    def __getQueryTitle(self, evt):
        return evt.getEvetName()
    
    def __getQueryYear(self, evt):
        return None
    
    def __getEvents(self):
        result = []
        for x in self.services:
            if self.epg.startTimeQuery(x) != -1:
                self.__processEvents(x, result)
        return result
    
    def __processEvents(self, ref, result):        
        evt = self.epg.getNextTimeEntry()
        while evt:
            result.append((ref.getPath(), evt.getEventName(), evt.getBeginTime(), evt, None))
                
    def __updateServices(self):
        self.services = []
        txt = config.plugins.mfilmweb.selserv.getText()
        if txt:
            entries = txt.split('|')
            for x in entries:
                ref = eServiceReference(x)
                print_info('--> SERV', str(x) + ', name: ' + ref.getName())
                self.services.append(ref)
    
    
    
            
            
    