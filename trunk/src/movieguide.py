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
from comps import DefaultScreen
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
        
        self.list = []
        self.services = []
        self.mapping = {}
        self.epg = eEPGCache.getInstance()        
        
        self.createGUI()
        self.initActions()
        
        self.onLayoutFinish.append(self.__startMe)

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
                
    def refreshList(self, res=None):
        try:
            self.list = []
            self["list"].setList(self.list)
            
            print_info('Update services ...')
            self.__updateServices()
            ds = []  
            for x in self.services:
                print_info('Getting events for service', str(x))
                #eng = TelemagEngine()
                eng = FilmwebTvEngine()
                tim = time()
                for idx in range(1,3):                    
                    tms = strftime("%Y%m%d", (localtime(tim)))
                    print_info('Query date', tms)
                    tim += idx * 86400  
                    df = eng.query(x, MT_MOVIE, tms)
                    if not df:
                        continue
                    ds.append(df)
            print_info('Create DeferredList')
            dlist = defer.DeferredList(ds, consumeErrors=True)
            print_info('Add DeferredList callback')
            dlist.addCallback(self.queryTelemagDone)                          
        except:
            import traceback
            traceback.print_exc()  
            
    def queryTelemagDone(self, result):
        try:
            print_info('Refresh List Done')            
            
            ds = []
            
            # (begin, opis, tytul, service, typ)
            for e, (success, value) in enumerate(result):
                print_info('refreshListDone Entry', '[%d]:' % e),
                if success:
                    #print_info('refreshListDone Success', str(value))
                    if value:    
                        for x in value:                            
                            begin = int(x[0])
                            tms = strftime("%Y-%m-%d %H:%M", (localtime(begin)))
                            print_info('EVT', '[' + tms + '] - ' + x[2] + ' / ' + x[3].getServiceName())
                            evt = self.epg.lookupEventTime(x[3].ref,begin)
                            if evt:
                                title = x[2]
                                if not title or len(title) == 0:
                                    continue
                                opis = x[1].strip()
                                rok = opis[-4:]
                                if not rok.isdigit():
                                    rok = None
                                if title == 'Film fabularny':
                                    title = evt.getEventName() 
                                title = self.__replaceTitle(title)
                                df = FilmwebEngine().query(MT_MOVIE, title, rok, False, self.filmwebQueryCallback, (x,tms, evt))
                                print_info('EVT EPG 1', 'rok:' + str(rok) + ", name: " + evt.getEventName())  
                                ds.append(df)                                              
                else:
                    print_info('refreshListDone Failure', str(value.getErrorMessage()))
            
            print_info('Create DeferredList')
            dlist = defer.DeferredList(ds, consumeErrors=True)
            print_info('Add DeferredList callback')
            dlist.addCallback(self.refreshListDone)                          
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
            self.list.append(((int(x[0]),lista[0][2],tms + ' - ' + tots, 
                               x[3].getServiceName(),rating, x[3], evt)))
        else:
            self.list.append(((int(x[0]),x[2],tms + ' - ' + tots, 
                               x[3].getServiceName(),'0,0', x[3], evt)))
        return ''
        
    def refreshListDone(self, result):
        if self.execing:
            self.list = sorted_data(self.list, 0)
            #self.list = (x for x in self.list)
            self["list"].setList(self.list)
        
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
    
    
    
            
            
    