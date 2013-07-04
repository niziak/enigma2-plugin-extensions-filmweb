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

import twisted.internet.defer as defer

from logger import print_info, print_debug
from config import config

from enigma import eEPGCache, eServiceReference
from time import localtime, strftime, time
from engine import TelemagEngine, FilmwebTvEngine, MT_MOVIE, MAPPING, MAPPING2
from ServiceReference import ServiceReference

class TvSearcher(object):
    def __init__(self):
        # initialization
        self.epg = eEPGCache.getInstance()

    # parametry:
    #   service: ServiceReference - referencja do przeszukiwanego serwisu
    #   tim: czas przeszukiwania - data do wyszukania zdarzen
    #   RESULT: lista tupli z danymi zdarzen na dzien wyszczegolniony w dacie przeszukiwania
    @defer.inlineCallbacks
    def searchForTime(self, service, tim=None, typ=MT_MOVIE):
        if not tim:
            tim = time()
        result = None
        tms = strftime("%Y%m%d", (localtime(tim)))
        print_debug('----->> Query date', tms + ', service: ' + service.getServiceName())
        df = self.__query(service, tms, typ)
        print_debug('QUERY DEFERED: ', str(df))
        if df:
            result = yield df
        print_debug('Query result: ', str(result))
        print_debug('Service: ', service.getServiceName())
        defer.returnValue(result)

    @defer.inlineCallbacks
    def dataForEvent(self, service, event, typ, callback, param):
        ret = None
        if event and service:
            beginTime = event.getBeginTime()
            tm = beginTime
            if tm < time():
                tm = time()
            result = self.searchForTime(service, tm + 10, typ)
            if result:
                result = yield result
                if result:
                    for x in result:
                        begin = int(x[0])
                        inrange = (begin - 30) < beginTime < (begin + 30)
                        if inrange:
                            ret = self.processSearchForTimeResult(x)
        if callback:
            callback(service, event, ret, param)

    def processSearchForTimeResult(self, result):
        try:
            begin = int(result[0])
            description = result[1]
            eventName = result[2]
            duration = result[3]
            service = result[4]

            tms = strftime("%Y-%m-%d %H:%M", (localtime(begin)))
            print_info('EVT', '[' + tms + ':' + str(duration) + '] - ' + eventName + ' / ' + service.getServiceName())
            evt = self.epg.lookupEventTime(service.ref, begin + 30)
            print_info('Lookup event result: ', str(evt))
            if not evt:
                return None
            title = eventName
            if not title or len(title) == 0:
                return None
            rok = self.__parseYear(description)
            if evt and title == 'Film fabularny':
                title = evt.getEventName()
            title = self.__replaceTitle(title)
            evid = service.getServiceName() + '___' + str(begin)

            return (result, tms, evt, rok, evid, title)
        except:
            import traceback
            traceback.print_exc()

    def serviceList(self, services):
        txt = config.plugins.mfilmweb.selserv.getText()
        if txt:
            entries = txt.split('|')
            for x in entries:
                ref = eServiceReference(x)
                sr = ServiceReference(ref)
                print_info('--> SERV', str(x) + ', name: ' + sr.getServiceName())
                services.append(sr)

    def __query(self, service, tms, typ):
        sname = service.getServiceName();
        sref = str(service)
        print_debug('Query service: ', str(sname) + ', reference: ' + sref)
        if sname and sref:
            sref = sref[:25]
            if MAPPING2.get(sref):
                return FilmwebTvEngine().query(service, typ, tms)
            if MAPPING.get(sref):
                return TelemagEngine().query(service, typ, tms)
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

    def __parseYear(self, description):
        opis = description.strip()
        rok = opis[-4:]
        if not rok.isdigit():
            return None
        return rok


