# -*- coding: UTF-8 -*-

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

from enigma import eTimer, ePicLoad, eServiceCenter
import mautils
import os

from config import FilmwebConfig
from engine import ImdbEngine, FilmwebEngine, MT_MOVIE, MT_SERIE, IMDB_POSTER_FILE, FILMWEB_POSTER_FILE
from mselection import FilmwebChannelSelection
from movieguide import MovieGuide
from __common__ import  _
from logger import print_info, print_debug
from comps import ActorChoiceList, ScrollLabelExt, MenuChoiceList, StarsComp, DefaultScreen
from tvsearch import TvSearcher

from ServiceReference import ServiceReference

from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox

from Components.Input import Input
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config

TITLE_MAX_SIZE = 67
WALLPAPER_REFRESH_TIME = 15000
RATE_CHOICES = [(_("Watched"), "0"), (_("Misunderstanding"), "1"), (_("Very Bad"), "2"), \
                (_("Poor"), "3"), (_("It can be"), "4"), (_("Average"), "5"), (_("Good Enough"), "6"), \
                (_("Good"), "7"), (_("Very Good"), "8"), (_("Sensational"), "9"), (_("Masterwork"), "10")]

VT_NONE = 'none'
VT_MENU = 'MENU'
VT_DETAILS = 'DETAILS'
VT_EXTRAS = 'EXTRAS'

class Filmweb(DefaultScreen):
    def __init__(self, session, data):
        DefaultScreen.__init__(self, session, "filmweb")
        print_info("Filmweb Screen - data", str(data))

        self.session = session
        self.mode = ''
        self.detailDir = 0
        self.resultlist = []
        self.initialize = True
        self.sessionId = None
        self.userToken = None
        self.regtitle = ''
        self.orgtitle = ''

        self.user = None
        self.passwd = None

        self.tvsearcher = TvSearcher()

        self.__clearSearch()
        if data:
            self.event = data[0]
            self.service = data[1]

        self.tmppath = config.plugins.mfilmweb.tmpPath.getValue()
        if not os.path.exists(self.tmppath):
            os.mkdir(self.tmppath)
        self.posterpath = self.tmppath + '/'

        self.onClose.append(self.__clearCache)

        self.initVars()
        self.createGUI()

        self.__changeEngine(config.plugins.mfilmweb.engine.value)

        self.initActions()

        self.wallpapertimer = eTimer()
        self.wallpapertimer.callback.append(self.changeWallpaper)
        self.wallpapertimer.start(WALLPAPER_REFRESH_TIME)

        self.reload()

    def __clearSearch(self):
        self.searchTitle = None
        self.searchYear = None
        self.event = None
        self.service = None

    def __clearCache(self):
        if os.path.exists(self.tmppath):
            names = os.listdir(self.tmppath)
            for name in names:
                if name.startswith('poster_') or name.startswith('actor_'):
                    pth = self.tmppath + '/' + name
                    if os.path.exists(pth):
                        os.remove(pth)

    def __changeEngine(self, engine):
        if not engine:
            return

        self.engineType = engine
        if self.engineType == 'IMDB':
            self.user = config.plugins.mfilmweb.imdbUser.getText()
            self.passwd = config.plugins.mfilmweb.imdbPassword.getText()
            self.posterpath = self.posterpath + IMDB_POSTER_FILE
            self.engine = ImdbEngine(self.failureHandler, self["status_bar"])
        else:
            self.user = config.plugins.mfilmweb.user.getText()
            self.passwd = config.plugins.mfilmweb.password.getText()
            self.posterpath = self.posterpath + FILMWEB_POSTER_FILE
            self.engine = FilmwebEngine(self.failureHandler, self["status_bar"])

    def reload(self, refx=True):
        if refx:
            self.searchType = MT_MOVIE
        print_debug("[reload] search type:", str(self.searchType) + ", refx: " + str(refx))
        self.switchView(to_mode=VT_NONE)
        self.sessionId = None
        self.userToken = None
        if self.user is None or self.user == '' or self.engineType == 'IMDB':
            self.processData(refx)
        else:
            self.loginPage(self.processData, refx)

    def initVars(self):
        self.filmId = None
        self.cast_list = []
        self.wallpapers = []
        self.wallpaperidx = -1
        self.myvote = -1
        self.detailslink = None

    def initActions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "InfobarMovieListActions", "InfobarCueSheetActions", "MovieSelectionActions", "DirectionActions"], {
            "ok": self.showDetails,
            "cancel": self.exit,
            "down": self.pageDown,
            "up": self.pageUp,
            "left": self.moveLeft,
            "right": self.moveRight,
            "red": self.exit,
            "green": self.showMenu,
            "yellow": self.showDetails,
            "blue": self.showExtras,
            "contextMenu": self.contextMenuPressed,
            "showEventInfo": self.showDetails,
            "movieList": self.showEPGList,
            "jumpPreviousMark" : self.prevAction,
            "jumpNextMark": self.nextAction,
            "toggleMark": self.toggleAction
        }, -1)

    # ---- ACTIONS ----
    def prevAction(self):
        pass

    def nextAction(self):
        engine = None
        year = self.searchYear
        self.__clearSearch()
        self.searchYear = year
        if self.engineType == 'IMDB':
            engine = 'Filmweb'
            self.searchTitle = self.regtitle
        else:
            engine = 'IMDB'
            self.searchTitle = self.orgtitle
            if not self.searchTitle:
                self.searchTitle = self.regtitle
            self.searchTitle = self.searchTitle.replace(', The', '')
        self.__changeEngine(engine)
        print_info('Loading data for ', str(self.searchTitle) + ' using engine: ' + str(self.engineType))
        self.reload(False)


    def toggleAction(self):
        if self.mode == VT_DETAILS:
            if self.detailslink:
                self["status_bar"].setText(_("Loading cast ..."))
                self.engine.loadCast(self.detailslink, self.loadCastCallback)

    def showEPGList(self):
        self.session.open(MovieGuide)

    def moveLeft(self):
        if self.mode == VT_DETAILS:
            self.detailDir = 0
            self.setFocus(self["cast_label"])

    def moveRight(self):
        if self.mode == VT_DETAILS:
            self.detailDir = 1
            self.setFocus(self["plot_label"])

    def pageDown(self):
        if self.mode == VT_MENU:
            self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
        elif self.mode == VT_DETAILS:
            if self.detailDir == 0:
                self["cast_label"].instance.moveSelection(self["cast_label"].instance.moveDown)
            else:
                self["plot_label"].pageDown()
        else:
            self["extra_label"].pageDown()

    def pageUp(self):
        if self.mode == VT_MENU:
            self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
        elif self.mode == VT_DETAILS:
            if self.detailDir == 0:
                self["cast_label"].instance.moveSelection(self["cast_label"].instance.moveUp)
            else:
                self["plot_label"].pageUp()
        else:
            self["extra_label"].pageUp()

    def exit(self):
        self.close()

    def showDetails(self):
        if self.mode == VT_DETAILS or self.mode == VT_NONE:
            print_debug("Show details - search type:", str(self.searchType))
            if self.searchType == MT_MOVIE:
                self.searchType = MT_SERIE
            else:
                self.searchType = MT_MOVIE
            self.switchView(to_mode=VT_NONE)
            self.processData(False)
        else:
            self.switchView(to_mode=VT_DETAILS)

    def showMenu(self):
        if self.mode == VT_NONE:
            return
        self.switchView(to_mode=VT_MENU)

    def showExtras(self):
        if self.mode == VT_DETAILS and self.detailslink:
            self.switchView(to_mode=VT_EXTRAS)

    def contextMenuPressed(self):
        lista = []
        if self.sessionId is not None and self.userToken is not None:
            lista.append((_("Vote current"), self.voteMovie))
        lista.append((_("Enter movie title"), self.inputMovieName))
        lista.append((_("Enter serie title"), self.inputSerieName))
        lista.append((_("Select from EPG"), self.channelSelection))
        lista.append((_("Configuration"), self.configData))
        self.session.openWithCallback(
            self.menuCallback,
            ChoiceBox,
            list=lista,
        )

    def menuCallback(self, ret=None):
        v = ret and ret[1]()
        print_debug("Context menu selected value", str(v))
        return v


    def channelSelection(self):
        print_debug("Channel selection")
        self.session.openWithCallback(
            self.serachSelectedChannel,
            FilmwebChannelSelection
        )

    def serachSelectedChannel(self, ret=None):
        print_info("Search Selected Channel", str(ret))
        if ret:
            self.__clearSearch()
            # sr = ServiceReference(ret)
            # self.switchView(to_mode=VT_MENU)
            serviceHandler = eServiceCenter.getInstance()
            info = serviceHandler.info(ret)
            print_debug("Service info: ", str(info))
            # sname = info and info.getName(ret) or ""
            # print_debug("Service name", str(sname))
            self.event = info and info.getEvent(ret)
            print_debug("Event: ", str(self.event))
            self.service = ServiceReference(ret)
            # evtname = evt and evt.getEventName()
            # print_debug("Event name", str(evtname))
            # self.eventName = evt and evt.getEventName()
            self.resultlist = []
            self.switchView(to_mode=VT_NONE)
            self.processData()

    def switchGUI(self, to_mode=VT_MENU):
        print_info("Switching GUI", "old mode=" + self.mode + ", new mode=" + to_mode)
        self.mode = to_mode
        if self.mode == VT_MENU:
            self["menu"].show()
            self["details_label"].show()

            self["title_label"].hide()
            self["login_label"].hide()
            self["plot_label"].hide()
            self["nstars"].hide()
            self["rating_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["wallpaper"].hide()
            self["extra_label"].hide()

            self["title"].setText(_("Ambiguous results"))
            if len(self.resultlist) > 0:
                self["details_label"].setText(_("Please select the matching entry"))
            else:
                self["details_label"].setText("")

            self["key_green"].setText("")
            self["key_yellow"].setText(_("Details"))
            self["key_blue"].setText("")
        elif self.mode == VT_DETAILS:
            self["rating_label"].show()
            self["cast_label"].show()
            self["details_label"].show()
            self["plot_label"].show()
            self["login_label"].show()
            self["wallpaper"].show()
            self["title_label"].show()

            if os.path.exists(self.posterpath):
                self["poster"].show()
            else:
                self["poster"].hide()

            self["nstars"].show()

            self["menu"].hide()
            self["extra_label"].hide()

            if len(self.resultlist) > 1:
                self["key_green"].setText(_("Title Menu"))
            else:
                self["key_green"].setText("")
            if self.searchType == MT_MOVIE:
                self["key_yellow"].setText(_("Search TV Serie"))
            else:
                self["key_yellow"].setText(_("Search Movie"))
            if self.detailslink:
                self["key_blue"].setText(_("Descriptions"))
            else:
                self["key_blue"].setText("")
        elif self.mode == VT_EXTRAS:
            self["extra_label"].show()
            self["title_label"].show()

            self["wallpaper"].hide()
            self["login_label"].hide()
            self["details_label"].hide()
            self["plot_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["nstars"].hide()
            self["rating_label"].hide()
            self["menu"].hide()

            if len(self.resultlist) > 1:
                self["key_green"].setText(_("Title Menu"))
            else:
                self["key_green"].setText("")
            self["key_yellow"].setText(_("Details"))
            self["key_blue"].setText("")
        else:
            self["title_label"].hide()
            self["login_label"].hide()
            self["extra_label"].hide()
            self["details_label"].hide()
            self["plot_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["nstars"].hide()
            self["rating_label"].hide()
            self["menu"].hide()
            self["wallpaper"].hide()

            if self.initialize:
                self["key_yellow"].setText("")
                self["title_label"].setText(_("Initializing - please wait ..."))
                self["title_label"].show()
            else:
                if self.searchType == MT_MOVIE:
                    self["key_yellow"].setText(_("Search TV Serie"))
                else:
                    self["key_yellow"].setText(_("Search Movie"))

            self["key_green"].setText('')
            self["key_blue"].setText('')

    def createGUI(self):
        self["title_label"] = Label()
        def setLText(txt):
            print_debug("setLText - Title Label", str(txt))
            if len(txt) > TITLE_MAX_SIZE:
                txt = txt[0:TITLE_MAX_SIZE - 3] + "..."
            Label.setText(self["title_label"], txt)
        self["title_label"].setText = setLText
        self["title"] = StaticText(_("The Filmweb Movie Database"))
        self["poster"] = Pixmap()
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintPoster)

        self["wallpaper"] = mautils.PixLoader(self.removeWallData)

        self["nstars"] = StarsComp()

        self["details_label"] = Label("")
        self["login_label"] = Label("")
        self["plot_label"] = ScrollLabelExt("")
        self["cast_label"] = ActorChoiceList(self.cast_list)

        self["extra_label"] = ScrollLabelExt("")
        self["status_bar"] = Label("")
        self["copyright"] = Label("Powered By Marcin Slowik")
        self["rating_label"] = Label("")
        self["menu"] = MenuChoiceList(self.resultlist)

        self["key_red"] = Button(_("Exit"))
        self["key_green"] = Button()
        self["key_yellow"] = Button()
        self["key_blue"] = Button()

    def __str__(self):
        return "FILMWEB {Session: " + str(self.session) + ", Search Text:" + str(self.searchTitle) + "}"

    def switchView(self, to_mode=VT_MENU):
        print_info("Switching view", "old mode=" + self.mode + ", new mode=" + to_mode)
        if self.mode == to_mode:
            return
        if self.initialize:
            to_mode = self.mode
        else:
            if to_mode == VT_MENU:
                size = len(self.resultlist)
                print_debug("The movies list size", str(size))
                self["title_label"].setText('')
                if size == 0:
                    print_debug('Search type:', str(self.searchType))
                    if self.searchType == MT_MOVIE:
                        self.inputMovieName()
                    else:
                        self.inputSerieName()
                    self.switchGUI(to_mode=VT_NONE)
                    return
                if size == 1:
                    to_mode = VT_DETAILS
                    self.loadDetails(self.resultlist[0][1], self.resultlist[0][0])
            elif to_mode == VT_DETAILS:
                if self.mode == VT_MENU:
                    if self["menu"].getCurrent():
                        idx = self["menu"].getSelectionIndex()
                        self.loadDetails(link=self.resultlist[idx][1], title=self.resultlist[idx][0])
                    else:
                        to_mode = VT_MENU
                elif self.mode == VT_EXTRAS:
                    pass
                else:
                    to_mode = self.mode
            elif to_mode == VT_EXTRAS:
                if self.mode == VT_DETAILS:
                    self.loadDescs()
                else:
                    to_mode = self.mode
        self.switchGUI(to_mode)

    def loadDescs(self):
        if self.detailslink:
            self["status_bar"].setText(_("Loading descriptions ..."))
            self.engine.loadDescriptions(self.detailslink, self.loadDescsCallback)

    def loadDetails(self, link, title):
        print_info("LOAD DETAILS", "link: " + link + ", title: " + title)
        self["status_bar"].setText(_("Seraching details for: %s...") % (title))
        print_debug("Filmweb Details Query ", link)
        self.detailslink = link
        self["poster"].hide()
        self.cast_list = []
        self.engine.queryDetails(link, self.queryDetailsCallback, self.sessionId)

    def loadCastCallback(self, clst):
        if clst:
            self.cast_list = []
            for x in clst:
                self.cast_list.append(self["cast_label"].createEntry(x[0], x[1], x[2]))
            self["cast_label"].l.setList(self.cast_list)

    def loadDescsCallback(self, descres):
        if descres:
            self["extra_label"].setText(descres)
        else:
            self["extra_label"].setText('')
            self["status_bar"].setText(_("Descriptions parsing error"))

    def queryDetailsCallback(self, detailsData):
        self.filmId = None
        self["title_label"].setText('')
        self["cast_label"].l.setList(self.cast_list)
        self["login_label"].setText('')
        self["plot_label"].setText('')
        self["rating_label"].setText('')
        self["nstars"].setValue(0)
        self["details_label"].setText('')
        self["wallpaper"].hide()
        self["poster"].hide()
        if not detailsData:
            self["status_bar"].setText(_("Movie details parsing error"))
        else:
            self.engine.loadPoster(detailsData['poster_url'], self.loadPosterCallback, localfile=self.tmppath)

            self.filmId = detailsData['film_id']

            self.cast_list = []
            clst = detailsData['cast']
            for x in clst:
                self.cast_list.append(self["cast_label"].createEntry(x[0], x[1], x[2]))
            self["cast_label"].l.setList(self.cast_list)

            self.wallpapers = []
            if self.sessionId and self.filmId:
                if detailsData['wallpapers_link']:
                    print_info("Parse wallpapers for link_" + str(detailsData['wallpapers_link']) + ', SID: ' + str(self.sessionId) + ', FID: ' + str(self.filmId))
                    self.engine.searchWallpapers(detailsData['wallpapers_link'], self.searchWallpapersCallback)
                if detailsData['photos_link']:
                    print_info("Parse photos for link_" + str(detailsData['photos_link']) + ', SID: ' + str(self.sessionId) + ', FID: ' + str(self.filmId))
                    self.engine.searchWallpapers(detailsData['photos_link'], self.searchWallpapersCallback)


            self["title_label"].setText(detailsData['title'])
            self.regtitle = detailsData['title']
            title = detailsData['org_title']
            self.orgtitle = title
            if title != '':
                ls = len(self["title_label"].getText())
                if ls < TITLE_MAX_SIZE:
                    self["title_label"].setText(self["title_label"].getText() + " (" + title + ")")

            self.myvote = detailsData['vote_val']
            self["login_label"].setText(detailsData['login'])
            self["plot_label"].setText(detailsData['plot'])
            self["rating_label"].setText(detailsData['rating'])
            self["nstars"].setValue(detailsData['rating_val'])
            textdsp = _("Genre: ") + detailsData['genre'] + "\n" + \
                        _("Country: ") + detailsData['country'] + "\n" + \
                        _("Director: ") + detailsData['director'] + "\n" + \
                        _("Writer: ") + detailsData['writer'] + "\n" + \
                        _("Year: ") + detailsData['year'] + "\n" + \
                        _("Runtime: ") + str(detailsData['runtime']) + " min.\n" + \
                        _("My Vote: ") + str(detailsData['vote']) + "\n"

            promo = detailsData['promo']
            if promo is not None:
                textdsp = textdsp + promo + '% ' + _('to your taste') + ' \n'

            self["details_label"].setText(textdsp)

    def searchWallpapersCallback(self, wallpapers):
        self.wallpapers = wallpapers
        if self.wallpapers and len(self.wallpapers) > 0:
            self.changeWallpaper()

    def rateEntry(self, rating):
        try:
            self.engine.applyRating(rating, self.filmId, self.userToken, self.fetchRateRes)
        except:
            import traceback
            traceback.print_exc()

    def loginPage(self, callback=None, param=None):
        try:
            self.userToken = None
            self.sessionId = None
            self.engine.login(self.user,
                              self.passwd,
                              self.loginCallback,
                              callback,
                              param)
        except:
            import traceback
            traceback.print_exc()

    def loginCallback(self, userToken, sessionId, callback, param):
        print_debug('Login callback - userToken:', userToken + ', SID: ' + sessionId)
        self.userToken = userToken
        self.sessionId = sessionId
        if callback:
            callback(param)
        return None

    def fetchRateRes(self, res_):
        if res_ and res_.startswith('//OK'):
            if self.mode == VT_DETAILS:
                self.loadDetails(self.detailslink, self["title_label"].getText())

    def failureHandler(self, txt):
        if self.has_key('status_bar'):
            self["status_bar"].setText(_("Filmweb Download failed"))

    def queryCallback(self, rlista, typ, data=None):
        self.resultlist = rlista
        print_debug("[queryCallback] search type:", str(typ))
        self.searchType = typ
        lista = []
        for entry in self.resultlist:
            caption = entry[0]
            link = entry[1]
            print_debug("LISTA", "caption: " + str(caption) + ", lnk: " + link)
            lista.append(self["menu"].createEntry(caption))
        if len(lista) == 0:
            self["title_label"].setText(_("Entry not found in Filmweb.pl database"))
        self["menu"].l.setList(lista)
        self.switchView(to_mode='MENU')

    def processData(self, tryOther=True):
        try:
            self.initialize = False
            if os.path.exists(self.posterpath):
                os.remove(self.posterpath)
            self.picload.startDecode(self.posterpath)
            self.initVars()
            self["cast_label"].l.setList(self.cast_list)
            self.resultlist = []

            self.beforeProcessData()
            print_info("Getting data for event: ", str(self.event))
            if self.event or self.searchTitle:
                self.tvsearcher.dataForEvent(self.service, self.event, self.searchType, self.queryDataCallback, tryOther)
            else:
                self["status_bar"].setText(_("Unknown Eventname"))
                self["title_label"].setText(_("Unknown Eventname"))
                self.switchView(to_mode='')
        except:
            import traceback
            traceback.print_exc()

    def beforeProcessData(self):
        if not self.event and not self.searchTitle:
            s = self.session.nav.getCurrentService()
            print_debug("Current Service", str(s))
            ref = self.session.nav.getCurrentlyPlayingServiceReference()
            print_debug("Current Service ref", str(ref))
            self.service = ServiceReference(ref)

            serviceHandler = eServiceCenter.getInstance()
            info = serviceHandler.info(ref)
            print_info("Service info", str(info))
            self.event = info and info.getEvent(ref)
            print_info("Event", str(self.event))
            # self.eventName = evt and evt.getEventName()

    def queryDataCallback(self, service, event, ret, tryOther):
        if event:
            self.searchTitle = event.getEventName()
        elif self.event:
            self.searchTitle = self.event.getEventName()

        if ret:
            self.searchTitle = ret[5]
            self.searchYear = ret[3]
            print_debug("Search data:", "title:%s, year:%s, type:%s" % (self.searchTitle, self.searchYear, self.searchType))
        elif event and tryOther:
            if self.searchType == MT_MOVIE:
                self.searchType = MT_SERIE
            else:
                self.searchType = MT_MOVIE
            self.tvsearcher.dataForEvent(service, event, self.searchType, self.queryDataCallback, False)
            return

        if not self.searchTitle:
            return

        if tryOther and (self.searchTitle.find('odc.') > -1 or self.searchTitle.find('serial') > -1):
            self.searchType = MT_SERIE
        print_debug("Search type", str(self.searchType) + ", try other: " + str(tryOther));
        idx = self.searchTitle.find(' - ')
        if idx > 0:
            self.searchTitle = self.searchTitle[:idx]
        self["status_bar"].setText(_("Query Filmweb: %s...") % (self.searchTitle))
        self.engine.query(self.searchType, self.searchTitle, self.searchYear, tryOther, self.queryCallback)

    def changeWallpaper(self):
        if self.mode != VT_DETAILS:
            return;
        print_debug("Change wallpaper", str(self.wallpaperidx) + ", filmId: " + str(self.filmId))
        if self.filmId is None:
            return
        localfile = self.tmppath + '/wal_' + self.filmId + '.jpg'
        if len(self.wallpapers) > 0:
            indx = self.wallpaperidx
            if self.wallpaperidx < 0:
                self.wallpaperidx = 0
            furl = self.wallpapers[self.wallpaperidx]
            self.wallpaperidx = self.wallpaperidx + 1
            if self.wallpaperidx >= len(self.wallpapers):
                self.wallpaperidx = 0
            if indx == self.wallpaperidx:
                return
            self.engine.loadWallpaper(furl, localfile, self.fetchWallDataOK)
        else:
            self["wallpaper"].hide()

    def fetchWallDataOK(self, txt_, localfile=None):
        if self.has_key("wallpaper") and self.filmId and localfile:
            print_debug("Loading image data", str(localfile))
            self["wallpaper"].updateIcon(localfile)
            if self.mode == VT_DETAILS:
                self["wallpaper"].show()

    def removeWallData(self, filename):
        print_debug("removeWallData - filename:", str(filename))
        if filename:
            if os.path.exists(filename):
                os.remove(filename)

    def loadPosterCallback(self, rpath):
        sc = AVSwitch().getFramebufferScale()
        self.picload.setPara((self["poster"].instance.size().width(),
                              self["poster"].instance.size().height(),
                              sc[0], sc[1], False, 1, "#00000000"))
        self.picload.startDecode(rpath)
        if self.mode == VT_DETAILS:
            self["poster"].show()

    def paintPoster(self, picInfo=None):
        print_debug("Paint poster", str(picInfo))
        ptr = self.picload.getData()
        if ptr != None:
            self["poster"].instance.setPixmap(ptr.__deref__())
            self["poster"].show()

    def inputSerieName(self):
        self.searchType = MT_SERIE
        dlg = self.session.openWithCallback(self.askForName, InputBox,
                                      windowTitle=_("Input the name of serie to search"),
                                       title=_("Enter serie title to search for"),
                                       text=self.searchTitle + " ",
                                       maxSize=55,
                                       type=Input.TEXT)
        dlg["input"].end()

    def configData(self):
        print_debug("configData", "started")
        self.session.openWithCallback(self.configSaved, FilmwebConfig)

    def configSaved(self, val=False):
        print_debug("configSaved", str(val))
        if val:
            self.loginPage()

    def voteMovie(self, res=None):
        if self.sessionId is None or self.userToken is None:
            self.session.open(MessageBox, _('In order to enter vote value you should be logged in'), MessageBox.TYPE_INFO)
        else:
            defa = 0
            if self.myvote > 0:
                defa = self.myvote
            dlg = self.session.openWithCallback(self.rateEntered, ChoiceBox,
                                           title=_("Enter rating value"),
                                           list=RATE_CHOICES,
                                           selection=defa)
            # dlg["input"].end()

    def rateEntered(self, val):
        if val is None:
            return
        else:
            voteVal = val[1].strip()
            isok = False
            if len(voteVal) > 0 and voteVal.isdigit():
                voteNum = int(voteVal)
                if voteNum >= 0 and voteNum < 11:
                    isok = True
                    self.rateEntry(voteNum)
            if not isok:
                self.session.openWithCallback(self.voteMovie, MessageBox, _('You have to enter value in range [0, 10]'), MessageBox.TYPE_ERROR)

    def inputMovieName(self):
        self.searchType = MT_MOVIE
        dlg = self.session.openWithCallback(self.askForName, InputBox,
                                      windowTitle=_("Input the name of movie to search"),
                                       title=_("Enter movie title to search for"),
                                       text=self.searchTitle + " ",
                                       maxSize=55,
                                       type=Input.TEXT)
        dlg["input"].end()

    def askForName(self, word):
        if word is None:
            pass
        else:
            self.__clearSearch()
            self.searchTitle = word.strip()
            self.processData(False)
            # self.session.open(MessageBox,_(word.strip()), MessageBox.TYPE_INFO)







