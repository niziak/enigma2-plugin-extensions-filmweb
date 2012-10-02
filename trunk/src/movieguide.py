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
from time import localtime, strftime, time
from __common__ import print_info, _
from mselection import FilmwebRateChannelSelection
from comps import DefaultScreen, Scroller
from engine import TelemagEngine, FilmwebTvEngine, FilmwebEngine, MT_MOVIE, MT_SERIE

from ServiceReference import ServiceReference
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText

sorted_data = lambda data, idx: [b for a,b in sorted((tup[idx], tup) for tup in data)]

class MovieGuide(DefaultScreen):
    def __init__(self, session):
        DefaultScreen.__init__(self, session, 'movieguide')
        
        self.scroller = None
        self.list = []
        self.services = []
        self.mapping = {}
        self.epg = eEPGCache.getInstance()        
        
        self.createGUI()
        self.initActions()
        
        #self.onExecBegin.append(self.__installScroller)
        #self.onClose.append(self.__uninstallScroller)
        self.onLayoutFinish.append(self.__startMe)

    # --- Screen Manipulation ------------------------------------------------  
    def createGUI(self):
        self["list"] = List(self.list)
        self["key_red"] = StaticText(_("Config"))
        self["key_green"] = StaticText(_("Refresh"))
        self["key_yellow"] = StaticText("")
        self["key_blue"] = StaticText("")
        
        self["list"].style = "default"
    
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
        if self.execing:
            cur = self['list'].getCurrent()
            print_info('Current', str(cur))        
            service = cur[5]
            event = cur[6]
            if service and service.ref:
                self.session.nav.playService(service.ref)

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
             
    @defer.inlineCallbacks       
    def refreshList(self, res=None):
        try:
            self.list = []
            
            progressList = []
            self["list"].style = "progress"
            self["list"].setList(progressList)
            
            print_info('---- Update services ...')
            self.__updateServices()
            ds = []              
            for x in self.services:
                print_info('Getting events for service', str(x))
                tup = (x.getServiceName(), 0)
                progressList.append((tup))
                self["list"].changed((self["list"].CHANGED_ALL,))
                count = len(progressList)
                df = self.refreshService(x, count - 1)                                    
                ds.append(df)
            print_info('----- Yield DeferredList -----')
            yield defer.DeferredList(ds, consumeErrors=True)
            print_info('----- DeferredList finished -----')
            if self.execing:
                self.list = sorted_data(self.list, 0)
                self["list"].style = "default"
                self["list"].setList(self.list)
        except:
            import traceback
            traceback.print_exc()  
            
    @defer.inlineCallbacks
    def refreshService(self, service, index):
        print_info('----- Refreshing Service', service.getServiceName() + ", index: " + str(index))
        try:
            #eng = TelemagEngine()
            eng = FilmwebTvEngine()
            filmeng = FilmwebEngine()
    
            tim = time()
            count = 4
            rng = int(100 / count)            
            for idx in range(1,count+1):   
                self["list"].modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4))))                 
                tms = strftime("%Y%m%d", (localtime(tim)))
                print_info('Query date', tms + ', service: ' + service.getServiceName())
                tim += idx * 86400  
                df = eng.query(service, MT_MOVIE, tms)
                if not df:
                    continue                
                result = yield df
                self["list"].modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 2)))
                print_info('Query result', str(result) + ', service: ' + service.getServiceName())
                for x in result:
                    df = self.processRes(x, filmeng)
                    if df:
                        result = yield df
                        self["list"].modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 3)))
                        print_info('Query Filmweb result', str(result) + ', service: ' + service.getServiceName())
                        while isinstance(result, defer.Deferred):
                            result = yield result
                        if result:
                            self.list.append((result))
                        self["list"].modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 4)))
            self["list"].modifyEntry(index, ((service.getServiceName(), 100)))
        except:
            import traceback
            traceback.print_exc()  
        
        
    def processRes(self, result, engine):
        try:
            begin = int(result[0])
            tms = strftime("%Y-%m-%d %H:%M", (localtime(begin)))
            print_info('EVT', '[' + tms + '] - ' + result[2] + ' / ' + result[3].getServiceName())
            evt = self.epg.lookupEventTime(result[3].ref,begin)
            if evt:
                title = result[2]
                if not title or len(title) == 0:
                    return None
                opis = result[1].strip()
                rok = opis[-4:]
                if not rok.isdigit():
                    rok = None
                if title == 'Film fabularny':
                    title = evt.getEventName() 
                title = self.__replaceTitle(title)
                df = engine.query(MT_MOVIE, title, rok, False, self.filmwebQueryCallback, (result,tms, evt))
                print_info('EVT EPG 1', 'rok:' + str(rok) + ", name: " + evt.getEventName())
                return df
            return None
        except:
            import traceback
            traceback.print_exc()  
                    
    # (ref.getPath(), evt.getEventName(), evt.getBeginTime(), evt, None)
    # (strig_rep, URL, string_rep_first_line, title, rating, year, country)
    def filmwebQueryCallback(self, lista, typ, data):
        x = data[0]
        tms = data[1]
        evt = data[2]
        
        tot = evt.getBeginTime() + evt.getDuration()
        tots = strftime("%H:%M", (localtime(tot)))
        
        if lista and len(lista) > 0:
            rating = lista[0][4]
            try:
                rt = float(rating.replace(',','.'))
            except:
                rt = 0
            rts = "%1.1f" % rt
            return (int(x[0]),lista[0][2],tms + ' - ' + tots, 
                               x[3].getServiceName(),rts, x[3], evt)
        else:
            return (int(x[0]),x[2],tms + ' - ' + tots, 
                               x[3].getServiceName(),'0.0', x[3], evt)
        
    # --- Private methods ------------------------------------------------
    
    def __replaceTitle(self, title):
        title = title.replace('IV','4')
        title = title.replace('IX','9')
        title = title.replace(' X ',' 10 ')
        title = title.replace('VIII','8')
        title = title.replace('VII','7')
        title = title.replace('VI','6')        
        title = title.replace('III','3')
        title = title.replace('II','2')
        title = title.replace(' I ',' 1 ')        
        title = title.replace(' V ',' 5 ')
        return title
        
    def __uninstallScroller(self):
        if self.scroller:
            self.scroller.deleteScroller()
            
    def __installScroller(self):
        self.scroller = Scroller(self.renderer[0])
        self.scroller.createScroller(self)
        self.scroller.applyScroller(self.desktop, self)
        
    def __startMe(self):
        self.refreshList()
        
    def __updateServices(self):
        self.services = []
        txt = config.plugins.mfilmweb.selserv.getText()
        if txt:
            entries = txt.split('|')
            for x in entries:
                ref = eServiceReference(x)
                sr = ServiceReference(ref)
                print_info('--> SERV', str(x) + ', name: ' + sr.getServiceName())
                self.services.append(sr)
    
    
    
            
            
    