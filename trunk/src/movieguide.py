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
import os
import xml.etree.ElementTree as xml
from enigma import eEPGCache, eServiceReference, eTimer
from time import localtime, strftime, time

from __common__ import _
from logger import print_info, print_debug
from mselection import FilmwebRateChannelSelection
from comps import DefaultScreen, StarsComp, MPixmap
from engine import TelemagEngine, FilmwebTvEngine, FilmwebEngine, ImdbEngine, MT_MOVIE, MAPPING, MAPPING2

from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Tools.LoadPixmap import LoadPixmap
from ServiceReference import ServiceReference

from Screens.Screen import Screen
from Screens.TimerEntry import TimerEntry
from Screens.MessageBox import MessageBox

from Components.UsageConfig import preferredTimerPath
from Components.Element import cached
from Components.config import config, configfile
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Converter.Converter import Converter
from Components.Label import Label

sorted_data = lambda data, idx, ordx: [b for _, b in sorted(((tup[idx], tup) for tup in data), reverse=ordx)]
sorted_data2 = lambda data, idx, idx2, ordx: [b for _, b in sorted((((tup[idx], tup[idx2]), tup) for tup in data), reverse=ordx)]

# this is 1 day in seconds
CACHE_INVALIDATE_TIME = 60 * 60 * 24

SORT_BEGIN_TIME = 0
SORT_RATING = 9
SORT_YEAR = 8
SORT_TITLE = 1
SORT_SERVICE = 3

SortData = {_('Begin Time'):SORT_BEGIN_TIME, _('Rating'):SORT_RATING, _('Year'):SORT_YEAR,
            _('Title'):SORT_TITLE, _('Service Name'):SORT_SERVICE}

class MovieGuideEventConv(Converter, object):
    def __init__(self, args):
        Converter.__init__(self, args)
        self.type = args
        self.args = None
        sp = self.type.split(':')
        if len(sp) > 1:
            self.type = sp[0]
            self.args = sp[1]

    @cached
    def getText(self):
        details = self.source.details
        print_debug('searching text for', self.type)
        if details and details.has_key(self.type):
            strg = str(details.get(self.type)) or ''
            print_debug('text for', self.type + "=" + strg)
            return strg
        return ''

    @cached
    def getPixmap(self):
        return self.__getRescalledPixmap()

    pixmap = property(getPixmap)
    text = property(getText)

    def __getRescalledPixmap(self):
        from Components.AVSwitch import AVSwitch
        from enigma import ePicLoad
        details = self.source.details
        if details:
            path = None
            if not self.args:
                return None
            parms = self.args.split(',')
            if not parms or len(parms) != 2:
                return None
            width = int(parms[0])
            height = int(parms[1])
            if details and details.has_key(self.type):
                path = details.get(self.type)
            if path:
                try:
                    picload = ePicLoad()
                    sc = AVSwitch().getFramebufferScale()
                    picload.setPara((width, height,
                                      sc[0], sc[1], False, 1, "#00000000"))
                    res = picload.startDecode(path)
                    print_debug('startDecode result', str(res))
                    picload.waitFinished()
                    ptr = picload.getData()
                    return ptr  # .__deref__()
                except:
                    import traceback
                    traceback.print_exc()
        return None

class MovieGuideEvent(ServiceEvent, object):
    def __init__(self):
        ServiceEvent.__init__(self)
        self._event = None
        self._details = None
        self._id = None

    def getCurrentEvent(self):
        return self._event

    def getMovieDetails(self):
        return self._details

    def updateDetails(self, details, evid):
        print_info('Update Details - EVID', str(evid) + ', this ID: ' + str(self._id))
        if not evid or not self._id:
            self._details = None
        if evid == self._id:
            self._details = details
        self.changed((self.CHANGED_ALL,))

    def newData(self, ref, evt, evid):
        if not self._id or not evid or self._id != evid:
            self._id = evid
            self._event = evt
            self.service = ref
            if not evid:
                self.changed((self.CHANGED_CLEAR,))
            else:
                self.changed((self.CHANGED_ALL,))

    details = property(getMovieDetails)

class SelectionEventInfo:
    def __init__(self):
        self.eventDetails = {}
        self["ServiceEvent"] = MovieGuideEvent()
        self.eventlist.onSelectionChanged.append(self.__selectionChanged)
        self.timer = eTimer()
        self.timer.callback.append(self.updateEventInfo)
        self.dtimer = eTimer()
        self.dtimer.callback.append(self.updateDetails)
        # self.onShown.append(self.__selectionChanged)

    def __selectionChanged(self):
        if self.execing:
            self.timer.start(100, True)
            # self.updateEventInfo()

    def updateEventInfo(self):
        cur = self.getCurrentSelection()
        self["nstars"].hide()
        if cur and len(cur) > 7:
            service = cur[5]
            event = cur[6]
            rate = cur[9]
            evid = self.getEventId(cur)
            self["nstars"].setValue(int(rate * 10))
            self["nstars"].show()
            self["ServiceEvent"].newData(service and service.ref, event, evid)
            # self.dtimer.stop()
            self.dtimer.start(200, True)
        else:
            self["ServiceEvent"].newData(None, None, None)
            self.updateDetails()


    def getEventIdByData(self, service, begin):
        return str(service) + '__' + str(begin)

    def getEventId(self, cur):
        return self.getEventIdByData(cur[3], cur[0])

    @defer.inlineCallbacks
    def updateDetails(self):
        try:
            if not self.execing:
                return
            cur = self.getCurrentSelection()
            if not cur or len(cur) < 7:
                self["ServiceEvent"].updateDetails(None, None)
                return
            event = cur[6]
            link = cur[7]
            filmDetails = None
            evid = self.getEventId(cur)
            engine = FilmwebEngine()
            # ---> loads data from cache <---
            self.loadNfo(evid)
            if link and not self.eventDetails.has_key(evid):
                filmDetails = yield engine.queryDetails(link)
                filmDetails['fullname'] = self.__createFullName(filmDetails)
                filmDetails['event_time'] = cur[2]
                if not filmDetails.has_key('plot') or len(filmDetails['plot'].strip()) == 0:
                    filmDetails['plot'] = event and event.getExtendedDescription() or ''
                strr = str(filmDetails['runtime'])
                if len(strr.strip()) > 0:
                    filmDetails['runtime'] = strr + ' min.'
                print_debug('Poster URL', filmDetails['poster_url'])
                df = engine.loadPoster(filmDetails['poster_url'], None, self.path + '/poster_' + filmDetails['film_id'] + '.jpg')
                if df:
                    filmDetails['poster'] = yield df
                self.eventDetails[evid] = filmDetails
                # ---> save data to cache <---
                self.saveNfo(evid)
            if self.eventDetails.has_key(evid):
                filmDetails = self.eventDetails[evid]
            self["ServiceEvent"].updateDetails(filmDetails, evid)
        except:
            import traceback
            traceback.print_exc()

    def loadNfo(self, evid):
        sfile = None
        try:
            mp = self.path + '/' + evid + '.nfo'
            if os.path.exists(mp):
                res = {}
                import codecs
                sfile = codecs.open(mp, 'r', encoding='utf-8')
                tree = xml.parse(sfile)
                root = tree.getroot()
                for x in root:
                    print_debug("TAG", str(x))
                    typ = x.attrib.get('typ')
                    value = x.text
                    if typ == 'str':
                        res[x.tag] = value
                    elif typ == 'int':
                        res[x.tag] = int(value)
                self.eventDetails[evid] = res
        except:
            import traceback
            traceback.print_exc()
        finally:
            if sfile is not None:
                sfile.close()

    def saveNfo(self, evid):
        sfile = None
        try:
            details = self.eventDetails[evid]
            root = xml.Element('movie')
            sfile = open(self.path + '/' + evid + '.nfo', "w")
            for key, value in details.items():
                child = xml.Element(key)
                if value:
                    typ = type(value)
                    child.set('typ', typ.__name__);
                    print_debug('element', key + ' - type: ' + str(type(value)))
                    if typ is list:
                        child.text = str(value)
                    else:
                        child.text = str(value)
                root.append(child)
            xml.ElementTree(root).write(sfile, encoding='utf-8')
        except:
            import traceback
            traceback.print_exc()
        finally:
            if sfile is not None:
                sfile.close()

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

        self.sortOrder = config.plugins.mfilmweb.sortOrder.getValue()
        self.sortIndex = config.plugins.mfilmweb.sort.getValue()
        self.timeline = time()

        self.initialized = False
        self.list = []
        self.services = []
        self.mapping = {}
        self.epg = eEPGCache.getInstance()

        self.createGUI()
        self.initActions()

        self.path = config.plugins.mfilmweb.tmpPath.getValue()
        if not os.path.exists(self.path):
            os.mkdir(self.path)

        self.eventlist = self["list"]
        SelectionEventInfo.__init__(self)

        self.clocktimer = eTimer()
        self.clocktimer.callback.append(self.__updateClock)
        self.clocktimer.start(60000, False)

        self.updatetimer = eTimer()
        self.updatetimer.callback.append(self.__updateListData)
        self.updatetimer.start(90000, False)

        self.onShown.append(self.__shown)
        self.onLayoutFinish.append(self.__startMe)
        self.onClose.append(self.__finishMe)

    # --- Screen Manipulation ------------------------------------------------
    def createGUI(self):
        self["list"] = List(self.list)
        self["key_red"] = StaticText('')
        self["key_green"] = StaticText('')
        self["key_yellow"] = StaticText('')
        self["key_blue"] = StaticText("")
        self["nstars"] = StarsComp()
        self["sort"] = Label()
        self["clock"] = MPixmap()
        self["clock-min"] = MPixmap()
        self["clock-hr"] = MPixmap()
        self["clock-str"] = Label('')

        self["list"].style = "progress"

    def initActions(self):
        # global globalActionMap
        # globalActionMap.actions['showClock'] = self.ShowHide
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "InfobarCueSheetActions"], {
            "ok": self.okAction,
            "cancel": self.cancelAction,
            "red": self.redAction,
            "green": self.greenAction,
            "yellow": self.yellowAction,
            "blue": self.blueAction,
            "jumpPreviousMark" : self.prevAction,
            "jumpNextMark": self.nextAction,
            "toggleMark": self.toggleAction
        }, -1)

    # --- Actions definition ------------------------------------------------
    def prevAction(self):
        print_debug("PREV action")
        if self.execing and self["list"].style == 'default' and config.plugins.mfilmweb.imdbData.getValue():
            lst = []
            for ent in self.list:
                ent = list(ent)
                # rate value exchange - filmweb <-> imdb
                x = ent[4]
                ent[4] = ent[15]
                ent[15] = x
                # rate string change - filmweb <-> imdb
                x = ent[9]
                ent[9] = ent[14]
                ent[14] = x
                ent = tuple(ent)
                lst.append(ent)
            self.list = lst
            self.displayEventList()

    def nextAction(self):
        print_debug("NEXT action")

    def toggleAction(self):
        print_debug("TOGGLE action")
        if self["list"].style == 'default':
            self.sortOrder = not self.sortOrder
            self.displayEventList()

    def okAction(self):
        print_debug("OK action")
        if self.execing:
            cur = self.getCurrentSelection()
            print_debug('Current', str(cur))
            self.zapOrTimer(cur)

    def cancelAction(self):
        print_debug("CANCEL action")
        self.close()

    def redAction(self):
        print_debug("RED action")
        if self["list"].style == 'default':
            self.session.open(FilmwebRateChannelSelection)

    def greenAction(self):
        print_debug("GREEN action")
        if self["list"].style == 'default':
            self.list = []
            self.timeline = time()
            self.__updateServices()
            self.refreshList()

    def yellowAction(self):
        print_debug("YELLOW action")
        if self["list"].style == 'default':
            self.refreshList()

    def blueAction(self):
        print_debug("BLUE action")
        if self["list"].style == 'default':
            self.sortIndex += 1
            if self.sortIndex > 4:
                self.sortIndex = 0
            self.displayEventList()

    # --- Overwrite methods ---------------------------------------------

    def createGUIScreen(self, parent, desktop, updateonly=False):
        self.__replaceConverters()
        Screen.createGUIScreen(self, parent, desktop, updateonly)

    # --- Public methods ------------------------------------------------

    def zapOrTimer(self, cur):
        if not cur:
            return
        service = cur[5]
        event = cur[6]

        if not service:
            return

        now = int(time())
        start_time = cur[0]  # event.getBeginTime()
        duration = cur[10]  # event.getDuration()
        if duration and start_time <= now <= (start_time + duration) and service and service.ref:
            self.session.nav.playService(service.ref)
        elif now < start_time:
            self.__tryAddTimer(service, event, cur)

    def getCurrentSelection(self):
        return self.eventlist.getCurrent()

    def displayEventList(self):
        print_debug('Display events - execting: ', str(self.execing))
        if self.execing:
            key, val = SortData.items()[self.sortIndex]
            self["key_red"].setText(_("Config"))
            self["key_green"].setText(_("Refresh"))
            self["key_yellow"].setText(_("Next Period"))
            self["key_blue"].setText(_("Change Sort"))
            self["sort"].setText(_("Sorted by") + ": " + key + " " + (self.sortOrder and _("DESC") or _("ASC")))
            print_debug('SORT_VAL', str(val))
            # print_debug('LIST', str(self.list))
            if self.list and len(self.list) > 0:
                self.list = sorted_data2(self.list, int(val), int(SORT_BEGIN_TIME), self.sortOrder)
            self.eventlist.style = "default"
            self.eventlist.setList((self.list))

    def displayProgressList(self, progressList):
        self["key_red"].setText('')
        self["key_green"].setText('')
        self["key_yellow"].setText('')
        self["key_blue"].setText('')
        self.eventlist.style = "progress"
        self.eventlist.setList(progressList)

    @defer.inlineCallbacks
    def refreshList(self, res=None):
        try:
            progressList = []
            self.displayProgressList(progressList)

            ds = []
            days_count = config.plugins.mfilmweb.guideDays.value
            for x in self.services:
                print_info('Getting events for service', str(x))
                tup = (x.getServiceName(), 0)
                progressList.append((tup))
                self.eventlist.changed((self.eventlist.CHANGED_ALL,))
                count = len(progressList)
                df = self.refreshService(x, count - 1, days_count)
                ds.append(df)
            print_debug('----- Yield DeferredList -----')
            yield defer.DeferredList(ds, consumeErrors=True)
            print_debug('----- DeferredList finished -----')
            self.timeline += 86400 * days_count
            self.displayEventList()
            self.initialized = True
        except:
            import traceback
            traceback.print_exc()

    @defer.inlineCallbacks
    def refreshService(self, service, index, count=1):
        print_info('----- Refreshing Service', service.getServiceName() + ", index: " + str(index))
        try:
            filmeng = FilmwebEngine()

            tim = self.timeline
            rng = int(100 / count)
            for idx in range(1, count + 1):
                self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4))))
                tms = strftime("%Y%m%d", (localtime(tim)))
                print_debug('----->> Query date', tms + ', service: ' + service.getServiceName())
                tim += 86400
                df = self.__query(service, tms)
                print_debug('QUERY DEFERED: ', str(df))
                if not df:
                    continue
                result = yield df
                self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 2)))
                print_debug('Query result', str(result) + ', service: ' + service.getServiceName())
                if not result:
                    continue
                for x in result:
                    res = None
                    df = self.processRes(x, filmeng)
                    if df:
                        if isinstance(df, defer.Deferred):
                            res = yield df
                        else:
                            res = df
                    if res:
                        self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 3)))
                        print_debug('Query Filmweb result', str(res) + ', service: ' + service.getServiceName())
                        while isinstance(res, defer.Deferred):
                            res = yield res
                        imdbrate = '0.0'
                        if res:
                            if config.plugins.mfilmweb.imdbData.getValue():
                                title = res[13]
                                print_debug('Movie title: ', str(title))
                                if title:
                                    idxo = title.find(' / ')
                                    if idxo > -1:
                                        title = title[idxo + 3:]
                                    year = res[8]
                                    title = title.strip()
                                    title = title.replace(', A', '')
                                    title = title.replace(', The', '')
                                    title = title.replace(', La', '')
                                    title = title.replace(", L'", '')
                                    title = title.replace(", Les", '')
                                    title = title.replace(", Das", '')
                                    title = title.replace(", Die", '')
                                    title = title.replace(", Der", '')
                                    print_debug('Movie title: ', str(title) + ', YEAR: ' + str(year))
                                    imdb = ImdbEngine()
                                    rdf = imdb.query(title, year, MT_MOVIE)
                                    if rdf:
                                        print_debug('Yield imdb query: ', str(rdf))
                                        tupimdb = yield rdf
                                        if tupimdb:
                                            imdbrate = tupimdb[0]
                                            imdbid = tupimdb[1]
                                            print_debug('IMDB rate: ', str(imdbrate) + ', ID: ' + str(imdbid))
                                        if not imdbrate:
                                            imdbrate = '0.0'
                            try:
                                rt = float(imdbrate)
                            except:
                                rt = 0
                            rts = "%1.1f" % rt
                            res = list(res)
                            res[14] = rt
                            res[15] = rts
                            res = tuple(res)
                            self.list.append(res)
                self.eventlist.modifyEntry(index, ((service.getServiceName(), (idx - 1) * rng + int(rng / 4) * 4)))
            self.eventlist.modifyEntry(index, ((service.getServiceName(), 100)))
        except:
            import traceback
            traceback.print_exc()

    def parseYear(self, description):
        opis = description.strip()
        rok = opis[-4:]
        if not rok.isdigit():
            return None
        return rok

    def processRes(self, result, engine):
        try:
            begin = int(result[0])
            description = result[1]
            eventName = result[2]
            service = result[4]

            tms = strftime("%Y-%m-%d %H:%M", (localtime(begin)))
            print_debug('EVT', '[' + tms + '] - ' + eventName + ' / ' + service.getServiceName())
            evt = self.epg.lookupEventTime(service.ref, begin + 30)
            if not evt:
                return None
            title = eventName
            if not title or len(title) == 0:
                return None
            rok = self.parseYear(description)
            if evt and title == 'Film fabularny':
                title = evt.getEventName()
            title = self.__replaceTitle(title)
            evid = service.getServiceName() + '___' + str(begin)
            lista = self.__loadNfo(evid)
            if lista:
                # print_debug('----> Lista', str(lista))
                lst = [lista]
                return self.filmwebQueryCallback(lst, MT_MOVIE, (result, tms, evt, rok, False))
            else:
                df = engine.query(MT_MOVIE, title, rok, False, self.filmwebQueryCallback, (result, tms, evt, rok, True))
                evn = evt and evt.getEventName() or '???'
                print_debug('EVT EPG 1', 'rok:' + str(rok) + ", name: " + evn)
                return df
        except:
            import traceback
            traceback.print_exc()

    # LISTA --> (strig_rep, URL, string_rep_first_line, title, rating, year, country)
    def filmwebQueryCallback(self, lista, typ, data):
        x = data[0]
        tms = data[1]
        evt = data[2]
        parsed_rok = data[3]
        begin = int(x[0])
        duration = x[3] and x[3] * 60
        save = data[4]
        service = x[4]

        if evt:
            evtb = evt.getBeginTime()
            inrange = (begin - 30) < evtb < (begin + 30)
            if not inrange:
                print_debug('------> EPG Event is not the same as entry <-----------')
                print_debug('------> EPG', evt.getEventName() + ", RES: " + str(x[2]) + ', service: ' + service.getServiceName())
                evt = None

        tots = '??'
        if evt:
            print_debug('Event duration', str(evt.getDuration() / 60))
            duration = evt.getDuration()

        if duration:
            tot = begin + duration
            tots = strftime("%H:%M", (localtime(tot)))

        print_debug('Result filmweb query list', str(lista))

        pixmap, state = self.__getStateData(evt, service, begin, duration)

        resme = None
        if lista and len(lista) > 0:
            rating = lista[0][4]
            try:
                rt = float(rating.replace(',', '.'))
            except:
                rt = 0
            rts = "%1.1f" % rt
            resme = (begin, lista[0][2], tms + ' - ' + tots,
                               service.getServiceName(), rts, service, evt,
                               lista[0][1], lista[0][5], rt, duration, pixmap,
                               state, lista[0][3], 0, '0.0')
            if save:
                self.__saveNfo(lista[0], service.getServiceName() + '___' + str(begin))
        else:
            resme = (begin, x[2], tms + ' - ' + tots,
                    service.getServiceName(), '0.0', service, evt,
                    None, parsed_rok, 0, duration, pixmap, state, x[2], 0, '0.0')
        return resme

    # --- Private methods ------------------------------------------------

    # (begin_time, caption, event_duration_desc, service_name, rating_string,
    #  ServiceReference, eServiceEvent, details_URL, movie_year, rating_value, duration_in_sec,
    #  pixmap, state, title, imdb_rating_value, imdb_rating_string)

    def __getStateData(self, evt, service, begin, duration):
        pixmap = None
        state = 0
        if self.__isInTimer(evt, service, begin, duration):
            pathe = "%s/resource/clock.png" % (self.ppath)
            pixmap = LoadPixmap(cached=True, path=pathe)
            state = 1
        else:
            now = time()
            if duration and begin + duration < now:
                pathe = "%s/resource/out.png" % (self.ppath)
                pixmap = LoadPixmap(cached=True, path=pathe)
                state = 2
            elif duration and begin <= now <= begin + duration:
                pathe = "%s/resource/play-2.png" % (self.ppath)
                pixmap = LoadPixmap(cached=True, path=pathe)
                state = 3
            else:
                pathe = "%s/resource/next.png" % (self.ppath)
                pixmap = LoadPixmap(cached=True, path=pathe)
                state = 4
        return pixmap, state

    def __updateListData(self):
        try:
            if self.execing and self.eventlist.style == "default":
                lista = self.eventlist.list
                index = 0
                for cur in lista:
                    data = self.__getFreshEntry(index, cur)
                    if data is not None:
                        print_debug('Update list entry - index: ', str(index))
                        self.eventlist.modifyEntry(index, (data))
                    index += 1
        except:
            import traceback
            traceback.print_exc()

    def __getFreshEntry(self, index, cur):
        if not cur:
            return None
        duration = cur[10]
        begin = cur[0]
        pixmap, state = self.__getStateData(cur[6], cur[5], begin, duration)
        if state != cur[12]:
            # print_debug('TUPLE', str(cur))
            lst = list(cur)
            # print_debug('LIST', str(lst))
            lst[12] = state
            lst[11] = pixmap
            return tuple(lst)
        return None

    def __isInTimer(self, evt, service, begin, duration):
        refstr = service.ref.toString()
        eventid = evt and evt.getEventId() or self.getEventIdByData(service.getServiceName(), begin)
        for timer in self.session.nav.RecordTimer.timer_list:
            if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
                return timer
        match = begin and duration and self.session.nav.RecordTimer.isInTimer(eventid, begin, duration, refstr)
        # print_debug('IS IN TIMER match:', str(match))
        if match:
            endt = begin + duration
            for x in self.session.nav.RecordTimer.timer_list:
                if x.service_ref.ref.toString() == refstr:
                    beg = x.begin
                    end = x.end
                    if beg <= begin <= end and endt <= end:
                        return x
        return None

    def __cleareCache(self):
        if os.path.exists(self.path):
            names = os.listdir(self.path)
            now = time()
            for name in names:
                pth = self.path + '/' + name
                if os.path.exists(pth):
                    modtime = os.path.getmtime(pth)
                    if (now - modtime) > CACHE_INVALIDATE_TIME:
                        os.remove(pth)

# (caption, url, basic_caption, title, rating, year, country)
    def __saveNfo(self, data, evid):
        sfile = None
        try:
            root = xml.Element('data')
            sfile = open(self.path + '/' + evid + '.nfo', "w")
            idx = 0
            for x in data:
                child = xml.Element('key' + str(idx))
                if x:
                    typ = type(x)
                    child.set('typ', typ.__name__)
                    child.text = str(x)
                else:
                    child.set('typ', 'None')
                root.append(child)
                idx += 1
            xml.ElementTree(root).write(sfile, encoding='utf-8')
        except:
            import traceback
            traceback.print_exc()
        finally:
            if sfile is not None:
                sfile.close()

    def __loadNfo(self, evid):
        sfile = None
        try:
            mp = self.path + '/' + evid + '.nfo'
            if os.path.exists(mp):
                res = []
                import codecs
                sfile = codecs.open(mp, 'r', encoding='utf-8')
                tree = xml.parse(sfile)
                root = tree.getroot()
                for x in root:
                    typ = x.attrib.get('typ')
                    value = x.text
                    if typ == 'str':
                        res.append(str(value))
                    elif typ == 'int':
                        res.append(int(value))
                    elif typ == 'None':
                        res.append(None)
                return res
        except:
            import traceback
            traceback.print_exc()
        finally:
            if sfile is not None:
                sfile.close()
        return None

    def __tryAddTimer(self, service, event, cur):
        if not service or (not cur[10] and not event):
            return

        eventid = event and event.getEventId()
        refstr = service.ref.toString()
        print_debug('Trying to add timer for service', refstr + ' and event: ' + str(eventid))
        tmr = self.__isInTimer(event, service, cur[0], cur[10])
        if tmr:
            cb_func = lambda ret : not ret or self.__removeTimer(tmr)
            self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % cur[1])
            return

        # (begin, end, name, description, eit)
        if event:
            newEntry = RecordTimerEntry(service, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(event))
        else:
            begin = cur[0] - config.recording.margin_before.value * 60
            end = cur[0] + cur[10] + config.recording.margin_after.value * 60
            name = cur[1]
            desc = ''
            evid = self.getEventId(cur)
            if evid and self.eventDetails.has_key(evid):
                name = self.eventDetails[evid]['fullname']
                desc = self.eventDetails[evid]['plot']
            newEntry = RecordTimerEntry(service, begin, end, name, desc, None, checkOldTimers=True, dirname=preferredTimerPath())
        self.session.openWithCallback(self.__finishedAdd, TimerEntry, newEntry)

    def __removeTimer(self, timer):
        timer.afterEvent = AFTEREVENT.NONE
        self.session.nav.RecordTimer.removeEntry(timer)
        self.__updateListData()

    def __finishedAdd(self, answer):
        from Screens.TimerEdit import TimerSanityConflict
        if answer[0]:
            entry = answer[1]
            simulTimerList = self.session.nav.RecordTimer.record(entry)
            if simulTimerList is not None:
                for x in simulTimerList:
                    if x.setAutoincreaseEnd(entry):
                        self.session.nav.RecordTimer.timeChanged(x)
                simulTimerList = self.session.nav.RecordTimer.record(entry)
                if simulTimerList is not None:
                    self.session.openWithCallback(self.__finishedAdd, TimerSanityConflict, simulTimerList)
            self.__updateListData()

    def __query(self, service, tms):
        sname = service.getServiceName();
        print_debug('Query service: ', str(sname))
        if sname:
            if MAPPING2.get(sname):
                return FilmwebTvEngine().query(service, MT_MOVIE, tms)
            if MAPPING.get(sname):
                return TelemagEngine().query(service, MT_MOVIE, tms)
        return None

    def __replaceTitle(self, title):
        title = title.replace('IV', '4')
        title = title.replace('IX', '9')
        title = title.replace(' X ', ' 10 ')
        title = title.replace('VIII', '8')
        title = title.replace('VII', '7')
        title = title.replace('VI', '6')
        title = title.replace('III', '3')
        title = title.replace('II', '2')
        title = title.replace(' I ', ' 1 ')
        title = title.replace(' V ', ' 5 ')
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
                convs = []
                for x in val.downstream_elements:
                    convs.append(x)

                for conv in convs:
                    className = conv.__class__.__name__
                    print_debug('Replace converters', className)
                    if className == 'EventName':
                        try:
                            self.__replaceConverter(conv)
                        except:
                            import traceback
                            traceback.print_exc()

    def __shown(self):
        if self.initialized and self.eventlist.style == "progress":
            self.displayEventList()

    def __startMe(self):
        self.setTitle(_("Movie Guide"))
        self.__updateServices()
        self.refreshList()
        self.__cleareCache()
        self.__updateClock()

    def __finishMe(self):
        config.plugins.mfilmweb.sort.setValue(self.sortIndex)
        config.plugins.mfilmweb.sortOrder.setValue(self.sortOrder)
        config.plugins.mfilmweb.save()
        configfile.save()

        if self.clocktimer:
            self.clocktimer.stop()
            self.clocktimer.callback.remove(self.__updateClock)
        if self.updatetimer:
            self.updatetimer.stop()
            self.updatetimer.callback.remove(self.__updateListData)

    def __updateServices(self):
        print_debug('---- Update services ...')
        self.services = []
        txt = config.plugins.mfilmweb.selserv.getText()
        if txt:
            entries = txt.split('|')
            for x in entries:
                ref = eServiceReference(x)
                sr = ServiceReference(ref)
                print_info('--> SERV', str(x) + ', name: ' + sr.getServiceName())
                self.services.append(sr)

    def __updateClock(self):
        now = localtime(time())

        txt = strftime('%Y-%m-%d | %H:%M', now)
        self["clock-str"].setText(txt)
        hrs = strftime('%I', now)
        mns = strftime('%M', now)
        pathe = "%s/resource/hours/%s-nq8.png" % (self.ppath, hrs)
        print_debug('clock path hours', pathe)
        pixmap = LoadPixmap(cached=True, path=pathe)
        self["clock-hr"].instance.setPixmap(pixmap)

        pathe = "%s/resource/minutes/%s-nq8.png" % (self.ppath, mns)
        print_debug('clock path minutes', pathe)
        pixmap = LoadPixmap(cached=True, path=pathe)
        self["clock-min"].instance.setPixmap(pixmap)

