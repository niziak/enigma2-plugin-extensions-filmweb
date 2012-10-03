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

from enigma import eEPGCache, eServiceReference, eTimer
from time import localtime, strftime, time
from __common__ import print_info, print_debug, _
from mselection import FilmwebRateChannelSelection
from comps import DefaultScreen
from engine import TelemagEngine, FilmwebTvEngine, FilmwebEngine, MT_MOVIE, MAPPING, MAPPING2

from ServiceReference import ServiceReference

from Screens.Screen import Screen
from Components.Element import cached
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Converter.Converter import Converter

sorted_data = lambda data, idx: [b for _,b in sorted((tup[idx], tup) for tup in data)]

class MovieGuideEventConv(Converter, object):
    def __init__(self, args):
        Converter.__init__(self, args)
        self.type = args
    
    @cached
    def getText(self):
        details = self.source.details
        if details and details.has_key(self.type):
            return details.get(self.type)
        return ''  
            
    text = property(getText)
    
class MovieGuideEvent(ServiceEvent, object):
    def __init__(self):
        ServiceEvent.__init__(self)
        self._event = None
        self._details = None

    @cached
    def getCurrentEvent(self):
        return self._event

    @cached
    def getMovieDetails(self):
        return self._details 
    
    def updateDetails(self, details, evid):
        if self._event and evid and evid == self._event.getEventId():
            self._details = details
        self.changed((self.CHANGED_ALL,))
            
    def newData(self, ref, evt):
        if not self._event or not evt or self._event != evt or not self.service or not ref or self.service != ref:
            self._event = evt
            self.service = ref
            if not evt:
                self.changed((self.CHANGED_CLEAR,))
            else:
                self.changed((self.CHANGED_ALL,))
                
    details = property(getMovieDetails)
    
class SelectionEventInfo:
    def __init__(self):
        self["ServiceEvent"] = MovieGuideEvent()
        self.eventlist.onSelectionChanged.append(self.__selectionChanged)
        #self.timer = eTimer()
        #self.timer.callback.append(self.updateEventInfo)
        #self.onShown.append(self.__selectionChanged)
            
    def __selectionChanged(self):
        if self.execing:
            #self.timer.start(100, True)
            self.updateEventInfo()

# (begin_time, caption, event_duration_desc, service_name, rating_string, ServiceReference, eServiceEvent, details_URL, movie_year)    
    def updateEventInfo(self):
        cur = self.getCurrentSelection()
        if cur and len(cur) > 7:
            service = cur[5]
            event = cur[6]
            self["ServiceEvent"].newData(service and service.ref, event)
            self.updateDetails(cur[7], event)
    
    @defer.inlineCallbacks
    def updateDetails(self, link, event):   
        try:     
            filmDetails = None
            evid = None        
            if event:
                evid = event.getEventId()
                if link and not self.eventDetails.has_key(evid):
                    filmDetails = yield FilmwebEngine().queryDetails(link)
                    filmDetails['fullname'] = self.__createFullName(filmDetails)
                    self.eventDetails[evid] = filmDetails
                elif self.eventDetails.has_key(evid):
                    filmDetails = self.eventDetails[evid]
            self["ServiceEvent"].updateDetails(filmDetails, evid)
        except:
            import traceback
            traceback.print_exc()
                
    def __createFullName(self, detailsData):
        val = detailsData['title']            
        title = detailsData['org_title']
        if title != '':
            ls = len(val)
            if ls < 64:
                val = val + " (" + title + ")"
        return val
                
class MovieGuide(DefaultScreen, SelectionEventInfo):
    def __init__(self, session):
        DefaultScreen.__init__(self, session, 'movieguide')
        
        self.eventDetails = {}
        self.list = []
        self.services = []
        self.mapping = {}
        self.epg = eEPGCache.getInstance()        
        
        self.createGUI()
        self.initActions()
        
        self.eventlist = self["list"]
        SelectionEventInfo.__init__(self)
        
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
        print_debug("OK action")
        if self.execing:
            cur = self.getCurrentSelection()
            print_debug('Current', str(cur))        
            service = cur[5]
            event = cur[6]
            if service and service.ref:
                self.session.nav.playService(service.ref)

    def cancelAction(self):
        print_debug("CANCEL action")
        self.close()
    
    def redAction(self):
        print_debug("RED action")
        self.session.open(FilmwebRateChannelSelection)
    
    def greenAction(self):
        print_debug("GREEN action")
        self.refreshList()
    
    def yellowAction(self):
        print_debug("YELLOW action")
    
    def blueAction(self):
        print_debug("BLUE action")
            
    # --- Overwrite methods ---------------------------------------------
    
    def createGUIScreen(self, parent, desktop, updateonly = False):                                     
        self.__replaceConverters()
        Screen.createGUIScreen(self, parent, desktop, updateonly)
    
    # --- Public methods ------------------------------------------------    
                  
    def getCurrentSelection(self):
        return self.eventlist.getCurrent()
    
    @defer.inlineCallbacks       
    def refreshList(self, res=None):
        try:
            self.list = []
            
            progressList = []
            self.eventlist.style = "progress"
            self.eventlist.setList(progressList)
            
            print_debug('---- Update services ...')
            self.__updateServices()
            ds = []              
            for x in self.services:
                print_info('Getting events for service', str(x))
                tup = (x.getServiceName(), 0)
                progressList.append((tup))
                self.eventlist.changed((self.eventlist.CHANGED_ALL,))
                count = len(progressList)
                df = self.refreshService(x, count - 1)                                    
                ds.append(df)
            print_debug('----- Yield DeferredList -----')
            yield defer.DeferredList(ds, consumeErrors=True)
            print_debug('----- DeferredList finished -----')
            if self.execing:
                self.list = sorted_data(self.list, 0)
                self.eventlist.style = "default"
                self.eventlist.setList(self.list)
        except:
            import traceback
            traceback.print_exc()  
            
    @defer.inlineCallbacks
    def refreshService(self, service, index):
        print_info('----- Refreshing Service', service.getServiceName() + ", index: " + str(index))
        try:
            filmeng = FilmwebEngine()
    
            tim = time()
            count = 1
            rng = int(100 / count)            
            for idx in range(1,count+1):   
                self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4))))                 
                tms = strftime("%Y%m%d", (localtime(tim)))
                print_debug('----->> Query date', tms + ', service: ' + service.getServiceName())
                tim += 86400  
                df = self.__query(service, tms)
                if not df:
                    continue                
                result = yield df
                self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 2)))
                print_debug('Query result', str(result) + ', service: ' + service.getServiceName())
                if not result:
                    continue
                for x in result:
                    df = self.processRes(x, filmeng)
                    if df:
                        result = yield df
                        self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 3)))
                        print_debug('Query Filmweb result', str(result) + ', service: ' + service.getServiceName())
                        while isinstance(result, defer.Deferred):
                            result = yield result
                        if result:
                            self.list.append((result))
                        self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 4)))
            self.eventlist.modifyEntry(index, ((service.getServiceName(), 100)))
        except:
            import traceback
            traceback.print_exc()  
        
        
    def processRes(self, result, engine):
        try:
            begin = int(result[0])
            description = result[1]
            eventName = result[2]
            service = result[3]
            tms = strftime("%Y-%m-%d %H:%M", (localtime(begin)))
            print_debug('EVT', '[' + tms + '] - ' + eventName + ' / ' + service.getServiceName())
            evt = self.epg.lookupEventTime(service.ref,begin)
            if evt:
                title = eventName
                if not title or len(title) == 0:
                    return None
                opis = description.strip()
                rok = opis[-4:]
                if not rok.isdigit():
                    rok = None
                if title == 'Film fabularny':
                    title = evt.getEventName() 
                title = self.__replaceTitle(title)
                df = engine.query(MT_MOVIE, title, rok, False, self.filmwebQueryCallback, (result,tms, evt, rok))
                print_debug('EVT EPG 1', 'rok:' + str(rok) + ", name: " + evt.getEventName())
                return df
            return None
        except:
            import traceback
            traceback.print_exc()  
                    
    # (strig_rep, URL, string_rep_first_line, title, rating, year, country)
    def filmwebQueryCallback(self, lista, typ, data):
        x = data[0]
        tms = data[1]
        evt = data[2]
        parsed_rok = data[3]
        
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
                               x[3].getServiceName(),rts, x[3], evt, lista[0][1], lista[0][5])
        else:
            return (int(x[0]),x[2],tms + ' - ' + tots, 
                               x[3].getServiceName(),'0.0', x[3], evt, None, parsed_rok)        
        
    # --- Private methods ------------------------------------------------
    
    def __query(self, service, tms):
        res = None
        sname = service.getServiceName();
        if sname:
            if MAPPING2.get(sname):
                return FilmwebTvEngine().query(service, MT_MOVIE, tms)
            if MAPPING.get(sname):
                return TelemagEngine().query(service, MT_MOVIE, tms)
        return res

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

    def __replaceConverter(self, data):
        source = None
        args = data.converter_arguments
        print_debug('Replace converter', args)
        if args and args.startswith('#'):
            args = args[1:]
        else:
            args = None
        if args:
            tags = args.split(';')
            converterClass = tags[0]
            converterParams = tags[1]
            source = globals()[converterClass](converterParams)
        if source:
            src = data.source
            mst = data.master
            data.disconnectAll()
            source.connect(src)
            mst.connect(source) 
                
    def __replaceConverters(self):
        # replace converters
        for key in self:
            val = self[key]
            if isinstance(val, MovieGuideEvent):
                for conv in val.downstream_elements:
                    className = conv.__class__.__name__
                    print_debug('Replace converters', className)
                    if className == 'EventName':
                        try:
                            self.__replaceConverter(conv)
                        except:
                            import traceback
                            traceback.print_exc()  
                                        
    def __startMe(self):
        self.setTitle(_("Movie Guide"))
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
    
    
    
            
            
    