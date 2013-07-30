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

import os
import twisted.internet.defer as defer
from enigma import eTimer
from time import localtime, strftime, time

from logger import print_info, print_debug
from tvsearch import TvSearcher
from engine import FilmwebEngine, MT_MOVIE, PAGE_URL
from config import config
from comps import DefaultScreen, sorted_data

from ServiceReference import ServiceReference
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.LoadPixmap import LoadPixmap
from Screens.ChannelSelection import ChannelSelection
from comps import getRescalledPixmap

class AbstractMessageScreen(DefaultScreen):
    def __init__(self, session, eventList, name):
        DefaultScreen.__init__(self, session, name)

        self.loaded = False

        self.session = session
        self.paramList = eventList
        self.imgList = []
        self.eventList = []
        self.eventListData = []

        self.tmppath = config.plugins.mfilmweb.tmpPath.getValue()
        self.servicelist = self.session.instantiateDialog(ChannelSelection)

        self.createGUI()
        self.initActions()

        # self.onLayoutFinish.append(self.__startMe)
        self.__startMe()
        self.onClose.append(self.__closeMe)

        self.closer = eTimer()
        self.closer.callback.append(self.cancelAction)
        # tmier na 10 min.
        self.closer.start(600000, True)

    def createGUI(self):
        self["list"] = List(self.eventList)
        self["list"].style = "default"

    def initActions(self):
        # global globalActionMap
        # globalActionMap.actions['ok'] = self.okAction
        self["actions"] = ActionMap(["OkCancelActions", "InfobarCueSheetActions"], {
            "ok": self.okAction,
            "cancel": self.cancelAction,
            "toggleMark": self.showInfo
        }, -1)


    def showInfo(self):
        try:
            import mainlib
            if self.execing:
                cur = self["list"].index
                if cur:
                    self.session.open(mainlib.Filmweb, (self.eventListData[cur][1], self.eventListData[cur][0]))
        except:
            import traceback
            traceback.print_exc()

    def cancelAction(self):
        print_debug("CANCEL action")
        self.close()

    def okAction(self):
        print_debug("OK action")
        if self.execing:
            cur = self["list"].index
            print_debug('Current', str(cur))
            if cur > -1:
                service = self.eventListData[cur][0]
                if service:
                    self.servicelist.setCurrentSelection(service.ref)
                    self.servicelist.zap()
                    # self.session.nav.playService(service.ref)
        # self.close()

    @defer.inlineCallbacks
    def __loadData(self):
        print_debug("Loading data ...")
        engine = FilmwebEngine()
        for xx in self.paramList:
            pixmap = getRescalledPixmap(40, 54, '/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/bigstar.png')
            if xx[4]:
                ext = 'jpg'
                if len(xx[4]) > 4:
                    ex = xx[4][-4:]
                    if ex[0] == '.':
                        ext = ex[1:]
                picPath = self.tmppath + '/pstr_' + str(time()) + '.' + ext
                print_debug("Picture path: ", ('%s for %s') % (picPath, xx[6]))
                yield engine.loadPoster(xx[4], None, localfile=picPath)
                pixmap = getRescalledPixmap(40, 54, picPath)
                if pixmap:
                    self.imgList.append(picPath)
            if not pixmap:
                pixmap = getRescalledPixmap(40, 54, '/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/bigstar.png')
            progressPixmap = LoadPixmap(cached=True, path="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/progress-fg.png")
            progressBgPixmap = LoadPixmap(cached=True, path="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/progress-bg.png")
            cpt = '%s' % (xx[6])
            if xx[7]:
                cpt = cpt + (' (%s)' % (xx[7]))
            srv = ''
            service = xx[9]
            if service:
                srv = service.getServiceName()
            evtl = ''
            if xx[5]:
                evtl = xx[5]
            evte = ''
            if xx[10]:
                evte = xx[10]
            progress = 0
            if xx[0] and xx[11]:
                now = time()
                co = now - xx[0]
                dur = xx[11] - xx[0]
                if co > 0 and dur > 0:
                    progress = int(100 * (co / dur))
                    if progress > 100:
                        progress = 100
            # (poster, caption, service name, event data, service ref, star pixmap, rate, event ref)
            self.eventList.append((pixmap, cpt, srv, evtl, xx[12], progress, progressPixmap, progressBgPixmap, evte))
            self.eventListData.append((service, xx[8]))

        self["list"].updateList(self.eventList)
        # self["list"].changed((self.CHANGED_ALL,))
        print_debug("Loading data ... done")

    def __startMe(self):
        if self.paramList:
            self.__loadData()

    def __closeMe(self):
        if self.closer:
            self.closer.stop()
            self.closer.callback.remove(self.cancelAction)
        if self.imgList and len(self.imgList) > 0:
            for img in self.imgList:
                if os.path.exists(img):
                    os.remove(img)

class RemMessage(AbstractMessageScreen):
    def __init__(self, session, eventList):
        AbstractMessageScreen.__init__(self, session, eventList, 'msg')

    def okAction(self):
        AbstractMessageScreen.okAction(self)
        self.close()

class ShortInfoScreen(AbstractMessageScreen):
    def __init__(self, session):
        eventList = []
        import plugin
        if plugin.pReminder.programList:
            tm = time()
            tm1 = tm + (10 * 60)
            for evtp in plugin.pReminder.programList:
                begin = evtp[0]
                end = evtp[11]
                if begin < tm1 and end and end > tm:
                    eventList.append(evtp)

        AbstractMessageScreen.__init__(self, session, eventList, 'shortinfo')

    def okAction(self):
        AbstractMessageScreen.okAction(self)
        # self.close()

class Reminder(object):
    def __init__(self):
        self.updatetimer = eTimer()
        self.updatetimer.callback.append(self.__check)
        self.session = None
        self.updateDate = None
        self.wannaSeeLastUpdate = None

        self.wantSeeList = []
        self.programList = []
        self.processedList = []

        self.tvsearcher = TvSearcher()
        self.processing = False

    def start(self, session):
        print_info('Start reminder for session', str(session))
        # odpalenie timera co 10 min. - 600000
        self.updatetimer.start(1200000, False)
        self.session = session

    def processWannaSeeList(self):
        try:
            tuptime = localtime(time())
            hour = tuptime[3]
            datecheck = strftime("%Y-%m-%d", (tuptime))
            if ((not self.wannaSeeLastUpdate or self.wannaSeeLastUpdate != datecheck) and hour > 5):
                self.wantSeeList = []
                self.wannaSeeLastUpdate = datecheck
            self.__updateWannaSeeList()
        except:
            import traceback
            traceback.print_exc()

    def processProgramList(self, force=False):
        try:
            tuptime = localtime(time())
            hour = tuptime[3]
            datecheck = strftime("%Y-%m-%d", (tuptime))
            if force or ((not self.updateDate or self.updateDate != datecheck) and hour > 3):
                self.programList = []
                self.processedList = []
                self.updateDate = datecheck
                self.__updateProgramList()
        except:
            import traceback
            traceback.print_exc()

    @defer.inlineCallbacks
    def __updateWannaSeeList(self):
        if len(self.wantSeeList) > 0 or self.processing:
            return
        try:
            self.processing = True
            self.wantSeeList.append('OK')

            engine = FilmwebEngine()
            username = config.plugins.mfilmweb.user.getText()
            password = config.plugins.mfilmweb.password.getText()
            # (userToken, sessionId)
            sessionData = yield engine.login(username, password, self.__loginCallback)
            if sessionData:
                print_debug('Filmweb login done - data: ', 'Token:%s, SID:%s' % (sessionData[0], sessionData[1]))
            else:
                print_debug('Filmweb login done - data <NULL>')
            if sessionData and sessionData[1]:
                # (userLink, userName)
                userData = yield engine.queryUserData(self.__dataCallback)
                if userData:
                    resList = yield engine.queryWanaSee(userData[0], self.__dataCallback)
                    if resList:
                        for rx in resList:
                            self.wantSeeList.append(rx[0])
            print_debug('WANNA SEE LIST: ', str(self.wantSeeList))
        except:
            import traceback
            traceback.print_exc()
        finally:
            self.processing = False

    def __dataCallback(self, data):
        print_debug('Data callback - data:', str(data))
        return data

    def __loginCallback(self, userToken, sessionId, data, params):
        print_debug('Login callback - data:', 'userToken:%s, SID:%s' % (userToken, sessionId))
        return (userToken, sessionId)

    @defer.inlineCallbacks
    def __updateProgramList(self):
        if len(self.programList) == 0 and not self.processing:
            try:
                self.processing = True
                print_debug('Updateing program list ...')
                services = []
                self.tvsearcher.serviceList(services)
                ds = []
                for x in services:
                    df = self.__processService(x)
                    ds.append(df)
                print_debug('----- Yield DeferredList -----')
                yield defer.DeferredList(ds, consumeErrors=True)
                print_debug('Updateing program list ... done')
                print_debug('Sorting event list ...')
                if self.programList and len(self.programList) > 0:
                    self.programList = sorted_data(self.programList, 0, False)
                print_debug('Sorting event list ... done')
                # print_debug('EVENT LIST: ', str(self.programList))
            except:
                import traceback
                traceback.print_exc()
            finally:
                self.processing = False

    @defer.inlineCallbacks
    def __processService(self, service):
        print_debug('Processing service: ', str(service))
        result = yield self.tvsearcher.searchForTime(service, time(), MT_MOVIE)
        if result:
            engine = FilmwebEngine()
            for xx in result:
                res = self.tvsearcher.processSearchForTimeResult(xx)
                if res:
                    data = res[0]
                    tms = res[1]
                    evt = res[2]
                    rok = res[3]
                    evid = res[4]
                    title = res[5]

                    df = engine.query(MT_MOVIE, title, rok, False, self.__queryCallback, None)
                    reseng = yield df
                    if reseng:
                        print_debug('Result filmweb query:', str(reseng))
                        tots = '??'
                        end = None
                        begin = int(data[0])
                        duration = data[3] and data[3] * 60
                        if evt:
                            print_debug('Event duration', str(evt.getDuration() / 60))
                            duration = evt.getDuration()
                        if duration:
                            end = begin + duration
                            tots = strftime("%H:%M", (localtime(end)))
                        tup = (begin, reseng[0], reseng[1], evid, reseng[2], tms, title, rok, evt, service, tots, end, reseng[3])
                        self.programList.append(tup)

    def __queryCallback(self, lista, typ, data):
        if lista and len(lista) > 0:
            url = lista[0][1]
            caption = lista[0][0]
            rate = lista[0][4]
            print_debug('Filmweb URL: ', str(url))
            return (url, caption, lista[0][7], rate)
        return None

    def __check(self):
        print_debug('Check reminder', '')
        self.processProgramList(False)

        if not config.plugins.mfilmweb.showNotifications.value:
            return

        self.processWannaSeeList()
        if not self.processing and len(self.wantSeeList) > 0 and len(self.programList) > 0:
            tm = time()
            # biezacy czas plus 10 min.
            tm1 = tm + (10 * 60)
            # biezacy czas minus 10 min.
            tm2 = tm - (10 * 60)
            lista = []
            for evtp in self.programList:
                if evtp[3] not in self.processedList and evtp[0] < tm1 and evtp[0] > tm2:
                    self.processedList.append(evtp[3])
                    if evtp[1]:
                        evx = evtp[1].replace(PAGE_URL, '')
                        print_debug('Checking movie: ', evx)
                        if evx in self.wantSeeList:
                            ref = self.session.nav.getCurrentlyPlayingServiceReference()
                            print_debug("Current Service ref: ", str(ref))
                            serv = ServiceReference(ref)
                            if str(serv) != str(evtp[9]):
                                print_info('Adding movie to notification list: ', evx)
                                lista.append(evtp)
            if len(lista) > 0:
                self.session.open(RemMessage, lista)

