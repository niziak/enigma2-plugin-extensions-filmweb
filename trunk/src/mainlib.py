# -*- coding: UTF-8 -*-

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

from twisted.web.client import downloadPage, getPage
from enigma import gFont, eTimer, ePicLoad, eServiceCenter, eListboxPythonMultiContent, RT_HALIGN_LEFT
from config import FilmwebConfig
from mselection import FilmwebChannelSelection, FilmwebRateChannelSelection
from __common__ import print_info, _
import mautils
import os
import sys
import urllib
#import re
    
#from ServiceReference import ServiceReference
from Tools.BoundFunction import boundFunction
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN

from Screens.Screen import Screen
from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox

from Components.MultiContent import MultiContentEntryText #, MultiContentEntryProgress, MultiContentTemplateColor
from Components.ChoiceList import ChoiceList
from Components.Input import Input
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
#from Components.MenuList import MenuList
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config

USER_TOKEN = '_artuser_token'
SESSION_KEY = '_artuser_sessionId'
POSTER_PATH = "/tmp/poster.jpg"
ACTOR_IMG_PREFIX = "/tmp/actor_img_"
TITLE_MAX_SIZE = 67
WALLPAPER_REFRESH_TIME=15000

MT_MOVIE = 'film'
MT_SERIE = 'serial'

VT_NONE = 'none'
VT_MENU = 'MENU'
VT_DETAILS = 'DETAILS'
VT_EXTRAS = 'EXTRAS'

COOKIES = {} 

actorPicload = {}


def MovieSearchEntryComponent(text = ["--"]):
    res = [ text ]

    if text[0] == "--":
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 800, 65, 0, RT_HALIGN_LEFT, "-"*200))
    else:
        offset = 0
        for x in text.splitlines():
            if offset == 0:            
                color=0x00F0B400
                font=1
            else:
                color=0x00FFFFFF
                font=0                
            res.append(MultiContentEntryText(pos=(0, offset), size=(800, 25), font=font, 
                                             flags=RT_HALIGN_LEFT, text=x, 
                                             color=color, color_sel=color))
            offset = offset + 25        
    return res      
    
def ActorEntryComponent(inst, img_url = "", text = ["--"], index=0):
    res = [ text ]
    
    def paintImage(idx=None, picInfo=None):
        print_info("Paint Actor Image", str(idx))
        ptr = actorPicload[idx].getData()
        if ptr != None:
            #png = ptr.__deref__()
            print_info("RES append", str(res) + " - img: " + str(ptr))
            res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 0, 40, 45, ptr))
            inst.l.invalidate()
        del actorPicload[idx]        
    
    def fetchImgOK(data, idx):
        print_info("fetchImgOK", str(idx))
        rpath = os.path.realpath(ACTOR_IMG_PREFIX + str(idx) + ".jpg")
        if os.path.exists(rpath):
            sc = AVSwitch().getFramebufferScale()
            actorPicload[idx].setPara((40, 45, sc[0], sc[1], False, 1, "#00000000"))
            print_info("Decode Image", rpath)
            actorPicload[idx].startDecode(rpath)
    
    def fetchImgFailed(data,idx):
        pass
    
    if text[0] == "--" or img_url == '' or img_url.find("jpg") < 0:
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 800, 45, 0, RT_HALIGN_LEFT, "-"*200))
    else:
        actorPicload[index] = ePicLoad()
        actorPicload[index].PictureData.get().append(boundFunction(paintImage, index)) 
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 0, 750, 45, 0, RT_HALIGN_LEFT, text[0]))        
        localfile = ACTOR_IMG_PREFIX + str(index) + ".jpg"
        print_info("Downloading actor img", img_url + " to " + localfile)
        downloadPage(img_url, localfile).addCallback(fetchImgOK, index).addErrback(fetchImgFailed, index)
    #inst.cast_list.append(res)
    #inst["cast_label"].l.setList(inst.cast_list)
    return res

                        
class Filmweb(Screen):
    def __init__(self, session, eventName):
        mf = sys.modules[__name__].__file__
        self.ppath = os.path.dirname(mf)
        print_info('Plugin path', self.ppath)
        fn = resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/buttons/red25.png')
        if (os.path.exists(fn)):
            skin = "%s/resource/filmweb_skin_bh.xml" % (self.ppath)
        else:
            skin = "%s/resource/filmweb_skin_df.xml" % (self.ppath)
        f = open(skin, "r")
        self.skin = f.read()
        f.close()
        
        Screen.__init__(self, session)
        print_info("Filmweb Screen - event", eventName)

        self.session = session
        self.eventName = eventName
        self.mode = ''
        self.searchType = MT_MOVIE        
        self.detailDir = 0
        self.resultlist = []          
        self.loopx = 0      
        self.initialize = True
        self.sessionId = None
        self.userToken = None
        
        self.onLayoutFinish.append(self.__layoutFinished)
        
        self.initVars()
        self.createGUI()
        self.initActions()
        self.switchView(to_mode=VT_NONE)
        
        self.wallpapertimer = eTimer()
        self.wallpapertimer.callback.append(self.changeWallpaper)
        self.wallpapertimer.start(WALLPAPER_REFRESH_TIME)
                        
        if config.plugins.mfilmweb.user.getText() == '':
            self.getData()
        else:
            self.loginPage(self.getData)
    
    event_quoted = property(lambda self: mautils.quote(self.eventName.encode('utf8')))
        
    def __layoutFinished(self):
        try:
            pixmap_path = "%s/resource/starsbar_filled.png" % (self.ppath)
            print_info('STARS instance', str(self["stars"].instance))
            self["stars"].instance.setPixmap(LoadPixmap(cached=True, path=pixmap_path))                
                  
            pixmap_path = "%s/resource/starsbar_empty.png" % (self.ppath)
            print_info('STARS BG instance', str(self["stars_bg"].instance))
            self["stars_bg"].instance.setPixmap(LoadPixmap(cached=True, path=pixmap_path))
        except:            
            import traceback
            traceback.print_exc() 
            
    def initVars(self):
        self.descs = None
        self.filmId = None
        self.cast_list = []
        self.wallpapers = []
        self.wallpaperidx = -1
        self.myvote = -1
        self.detailslink = None
            
    def initActions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "InfobarMovieListActions", "MovieSelectionActions", "DirectionActions"], {
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
            "movieList": self.showEPGList
        }, -1)
        
    # ---- ACTIONS ----  
    def showEPGListCallback(self, res=None):
        print_info('showEPGListCallback', str(res))
        
    def showEPGList(self):
        self.session.openWithCallback(self.showEPGListCallback, FilmwebRateChannelSelection) 
              
        '''
        from enigma import  eEPGCache, eServiceReference
        from Screens.ChannelSelection import service_types_tv
        from Components.Sources.ServiceList import ServiceList
        
        bouquetlist = ServiceList(eServiceReference(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'), validate_commands=False).getServicesAsList()
        for bouquetitem in bouquetlist:
            print_info('-- EPG --', 'bouquet: ' + str(bouquetitem))
            serviceHandler = eServiceCenter.getInstance()
            list = serviceHandler.list(eServiceReference(str(bouquetitem[0])))
            services = list and list.getContent('S')
            print_info('-- EPG --', 'SERV: ' + str(services))
            channels = list and list.getContent("SN", True)
            print_info('-- EPG --', 'CHNLS: ' + str(channels))
            
            search = ['IBDCTSERNX']
            if services: # It's a Bouquet
                search.extend([(service, 0, -1) for service in services])
            
            print_info('-- EPG --', 'SEARCH: ' + str(search))
            events = eEPGCache.getInstance().lookupEvent(search)
            for eventinfo in events:
                #0 eventID | 4 eventname | 5 short descr | 6 long descr | 7 serviceref | 8 channelname
                print_info('-- EPG --', 'evt: ' + str(eventinfo))
        '''    
        #idbouquet = '%s ORDER BY name'%(service_types_tv)
        #epgcache = eEPGCache.getInstance()
        #serviceHandler = eServiceCenter.getInstance()
        #services = serviceHandler.list(eServiceReference(idbouquet))
        #print_info('-- EPG --', 'services: ' + str(services))
        #channels = services and services.getContent("SN", True)
        #for channel in channels:
            #print_info('-- EPG --', 'channel: ' + str(channel))
            #if not int(channel[0].split(":")[1]) & 64:
                #chan = {}
                #chan['ref'] = channel[0]
                #chan['name'] = channel[1]
                #print_info('-- EPG --', 'chan: ' + str(chan))
                #nowevent = epgcache.lookupEvent(['TBDCIX', (channel[0], 0, -1)])
                #print_info('-- EPG --', 'now evt: ' + str(nowevent))
                
    
    def moveLeft(self):
        if self.mode == VT_DETAILS:
            self.detailDir = 0
                            
    def moveRight(self):
        if self.mode == VT_DETAILS:
            self.detailDir = 1
            
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
            if self.searchType == MT_MOVIE:
                self.searchType = MT_SERIE
            else:
                self.searchType = MT_MOVIE
            self.switchView(to_mode=VT_NONE)
            self.getData(False)
        else:
            self.switchView(to_mode=VT_DETAILS)
              
    def showMenu(self):
        if self.mode == VT_NONE:
            return
        self.switchView(to_mode=VT_MENU)
          
    def showExtras(self):
        if self.mode == VT_DETAILS and self.descs:
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
            list = lista,
        )

    def menuCallback(self, ret = None):
        v = ret and ret[1]()
        print_info("Context menu selected value", str(v))
        return v
        
        
    def channelSelection(self):      
        print_info("Channel selection")  
        self.session.openWithCallback(
            self.serachSelectedChannel,
            FilmwebChannelSelection
        )
                    
    def serachSelectedChannel(self, ret = None):
        print_info("Serach Selected Channel", str(ret)) 
        if ret:
            #sr = ServiceReference(ret)            
            #self.switchView(to_mode=VT_MENU)  
            serviceHandler = eServiceCenter.getInstance()  
            info = serviceHandler.info(ret)               
            print_info("Service info", str(info)) 
            #sname = info and info.getName(ret) or ""  
            #print_info("Service name", str(sname))  
            evt = info and info.getEvent(ret) 
            print_info("Event", str(evt))  
            #evtname = evt and evt.getEventName()
            #print_info("Event name", str(evtname))  
            self.eventName = evt and evt.getEventName()           
            self.resultlist = []
            self.switchView(to_mode=VT_NONE)            
            self.getData()
            
    def switchView(self, to_mode=VT_MENU):
        print_info("Switching view", "old mode=" + self.mode + ", new mode=" + to_mode)
        if self.mode == to_mode:
            return
        if self.initialize:
            to_mode = self.mode
        else:
            if to_mode == VT_MENU:
                size = len(self.resultlist)
                print_info("The movies list size", str(size))
                self["title_label"].setText('')
                if size == 0:
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
        if self.descs:
            print_info("LOAD DESCS", "link: " + self.descs)
            self["status_bar"].setText(_("Loading descriptions ..."))
            getPage(self.descs, cookies=COOKIES).addCallback(self.fetchExtraOK).addErrback(self.fetchFailed)
    
    def loadDetails(self, link, title):
        print_info("LOAD DETAILS", "link: " + link + ", title: " + title)
        self["status_bar"].setText(_("Seraching details for: %s...") % (title))
        print_info("Filmweb Details Query ", link)        
        self.descs = link + "/descs"
        self.detailslink = link
                        
        getPage(link, cookies=COOKIES).addCallback(self.fetchDetailsOK).addErrback(self.fetchFailed) 
        
    def rateEntry(self, rating):
        try:
            if rating and self.filmId:
                print_info("rateEntry - user token", str(self.userToken) + ', rating: ' + str(rating))
                data = '5|0|6|http://2.fwcdn.pl/gwt/newFilmActivity/|CCD826B60450FCB69E9BD856EE06EAB5|filmweb.gwt.filmactivity.client.UserFilmRemoteService|setRate|J|I|1|2|3|4|2|5|6|' + str(self.filmId) + '|0|' + str(rating) + '|'
                print_info("POST DATA", data)
                headers = {'Content-Type':'text/x-gwt-rpc; charset=UTF-8',
                           'Host':'www.filmweb.pl',
                           'Origin':'http://www.filmweb.pl',
                           'X-GWT-Module-Base':'http://2.fwcdn.pl/gwt/newFilmActivity/',
                           'X-GWT-Permutation':'7C0EB94ECB5DCB0BABC0AE73531FA849',
                           'X-Artuser-Token':self.userToken
                           }
                getPage('http://www.filmweb.pl/rpc/userFilmRemoteService', method='POST', postdata=data, 
                        headers=headers,
                        cookies=COOKIES).addCallback(self.fetchRateRes).addErrback(self.fetchRateRes)
        except:            
            import traceback
            traceback.print_exc() 
                
    def loginPage(self, callback=None):
        try:
            print_info("LoginPage", "started")
            self["status_bar"].setText(_('Logging in ...'))
            self.sessionId = None 
            self.userToken = None
            if COOKIES.has_key(SESSION_KEY):
                COOKIES.pop(SESSION_KEY)
            if COOKIES.has_key(USER_TOKEN):
                COOKIES.pop(USER_TOKEN)  
            data = {'j_username': config.plugins.mfilmweb.user.getText(), "j_password" : config.plugins.mfilmweb.password.getText()}
            data = urllib.urlencode(data)
            getPage('https://ssl.filmweb.pl/j_login', method='POST', postdata=data, 
                    headers={'Content-Type':'application/x-www-form-urlencoded'},
                    cookies=COOKIES).addCallback(self.fetchLoginRes, callback).addErrback(self.fetchLoginRes, callback)
            print_info("LoginPage data", str(data))
        except:            
            import traceback
            traceback.print_exc() 
        
    def fetchRateRes(self, res_):
        print_info("RESULT COOKIE", str(COOKIES) + ", res: " + str(res_))
        if res_ and res_.startswith('//OK'):
            #self.session.open(MessageBox,_('Your vote has been registered'), MessageBox.TYPE_INFO)
            if self.mode == VT_DETAILS:
                self.loadDetails(self.detailslink, self["title_label"].getText())          
        
    def fetchLoginRes(self, res_, callback):
        print_info("RESULT COOKIE", str(COOKIES))
        if COOKIES.has_key(SESSION_KEY):
            self.sessionId = COOKIES[SESSION_KEY]            
        else:
            self.sessionId = None
        if COOKIES.has_key(USER_TOKEN):
            self.userToken = COOKIES[USER_TOKEN]            
        else:
            self.userToken = None     
        self["status_bar"].setText(_('Login done'))   
        print_info('Login data', str(self.userToken) + ', SID: ' + str(self.sessionId))
        if callback:
            callback()
            
    def switchGUI(self, to_mode=VT_MENU):
        print_info("Switching GUI", "old mode=" + self.mode + ", new mode=" + to_mode)
        self.mode = to_mode
        if self.mode == VT_MENU:
            self["menu"].show()
            self["details_label"].show()            
            
            self["title_label"].hide()
            self["login_label"].hide()
            self["plot_label"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
            self["rating_label"].hide()
            if self.has_key('cast_scroll'):
                self["cast_scroll"].hide()
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
            if self.has_key('cast_scroll'):
                self["cast_scroll"].show()
            self["cast_label"].show()
            self["details_label"].show()
            self["plot_label"].show()
            self["login_label"].show()
            self["wallpaper"].show()
            self["title_label"].show()
            
            if os.path.exists(POSTER_PATH):
                self["poster"].show()
            else:
                self["poster"].hide()
            
            self["stars_bg"].show()
            self["stars"].show()
            
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
            if self.descs:
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
            if self.has_key('cast_scroll'):
                self["cast_scroll"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
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
            if self.has_key('cast_scroll'):
                self["cast_scroll"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
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
            print_info("setLText - Title Label", str(txt))
            if len(txt) > TITLE_MAX_SIZE:
                txt = txt[0:TITLE_MAX_SIZE - 3] + "..."
            Label.setText(self["title_label"], txt)
        self["title_label"].setText = setLText        
        self["title"] = StaticText(_("The Filmweb Movie Database"))        
        self["poster"] = Pixmap()
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintPoster)
        
        self["wallpaper"] = mautils.PixLoader(self.removeWallData)
           
        self["stars"] = ProgressBar()                
        self["stars_bg"] = Pixmap()      
          
        self["details_label"] = Label("")
        self["login_label"] = Label("")        
        self["plot_label"] = ScrollLabel("")
        self["cast_label"] = ChoiceList(self.cast_list)        
        self["cast_label"].l.setItemHeight(50)
        self["extra_label"] = ScrollLabel("")
        self["status_bar"] = Label("")
        self["rating_label"] = Label("")        
        self["menu"] = ChoiceList(self.resultlist)
        self["menu"].l.setItemHeight(70)
        self["menu"].l.setFont(0, gFont("Regular", 16))
        self["menu"].l.setFont(1, gFont("Regular", 20))        
        
        self["key_red"] = Button(_("Exit"))
        self["key_green"] = Button()
        self["key_yellow"] = Button()
        self["key_blue"] = Button()
        
    def __str__(self):
        return "FILMWEB {Session: " + str(self.session) + ", EventName:" + str(self.eventName) + "}"
                     
    def getData(self, tryOther=True):
        try:
            self.initialize = False
            if os.path.exists(POSTER_PATH):
                os.remove(POSTER_PATH)     
            self.picload.startDecode(POSTER_PATH)
            self.initVars()
            self["cast_label"].l.setList(self.cast_list)
            self.resultlist = []
            print_info("Getting data for event", str(self.eventName))
            if not self.eventName or len(self.eventName.strip()) == 0:
                s = self.session.nav.getCurrentService()
                print_info("Current Service", str(s))
                ref = self.session.nav.getCurrentlyPlayingServiceReference()
                print_info("Current Service ref", str(ref))
                
                serviceHandler = eServiceCenter.getInstance()  
                info = serviceHandler.info(ref)               
                print_info("Service info", str(info))              
                evt = info and info.getEvent(ref) 
                print_info("Event", str(evt))               
                self.eventName = evt and evt.getEventName()  
            print_info("Getting data for event with name", str(self.eventName))
            if self.eventName:
                idx = self.eventName.find(' -')
                if idx > 0:
                    self.eventName = self.eventName[:idx]
                if tryOther and self.eventName.find('odc.') > 0:
                    self.searchType = MT_SERIE
                self["status_bar"].setText(_("Query Filmweb: %s...") % (self.eventName))
                #localfile = "/tmp/filmweb_query.html"        
                fetchurl = "http://www.filmweb.pl/search/" + self.searchType + "?q=" + self.event_quoted
                #print_info("Filmweb Query " + fetchurl + " to ", localfile)
                print_info("Filmweb Query ", fetchurl)
                getPage(fetchurl, cookies=COOKIES).addCallback(self.fetchOK, tryOther).addErrback(self.fetchFailed)            
            else:
                self["status_bar"].setText(_("Unknown Eventname"))
                self["title_label"].setText(_("Unknown Eventname"))
                self.switchView(to_mode='')
        except:
            import traceback
            traceback.print_exc()
            
    def fetchWallpaperOK(self, txt_):
        print_info("fetchWallpaperOK ...")
        try:
            if not self.filmId:
                return
            self["wallpaper"].hide()
            print_info("fetch wallpaper OK", str(COOKIES))
            self["status_bar"].setText(_("Wallpaper loading completed"))
            if txt_ and len(txt_) > 0:
                walls = mautils.after(txt_, '<ul class=filmWallapersList')
                elements = walls.split('filmWallapersItem')
                elcount = len(elements)
                print_info("Wallpapers count", str(elcount))                
                if elcount > 0 and self.has_key('wallpaper'):
                    furl = None
                    for elem in elements:
                        #print_info("ELEM", elem)
                        didx = elem.find('<span class=newLinkLoggedOnly>')
                        print_info("Wallpaper idx", str(didx))
                        if didx > -1:                            
                            furl = mautils.between(elem, '<span class=newLinkLoggedOnly>', '</span>')
                            print_info("URL", furl)
                            self.wallpapers.append(furl)
                    self.changeWallpaper()                       
        except:
            import traceback
            traceback.print_exc()
    
    def changeWallpaper(self):
        if self.mode != VT_DETAILS:
            return;
        print_info("Change wallpaper", str(self.wallpaperidx) + ", filmId: " + str(self.filmId))
        if self.filmId is None:
            return
        localfile = '/tmp/' + self.filmId + '.jpg'
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
            print_info("Loading wallpaper", 'URL: ' + furl + ', Local File:' + localfile)
            downloadPage(furl, localfile).addCallback(self.fetchWallDataOK,localfile).addErrback(self.fetchFailed)
        else:
            self["wallpaper"].hide()
                        
    def fetchWallDataOK(self, txt_, localfile=None):
        if self.has_key("wallpaper") and self.filmId and localfile:
            print_info("Loading image data", str(localfile))
            self["wallpaper"].updateIcon(localfile)
            if self.mode == VT_DETAILS:  
                self["wallpaper"].show()          
        
    def removeWallData(self, filename):
        print_info("removeWallData - filename:", str(filename))
        if filename:
            if os.path.exists(filename):
                os.remove(filename)
                
    def fetchExtraOK(self, txt_):
        print_info("fetch extra OK", str(COOKIES))
        self["status_bar"].setText(_("Descriptions loading completed"))
        dhtml = mautils.html2utf8(txt_)
        if dhtml:
            self.parseDescriptions(dhtml)
        else:
            self["status_bar"].setText(_("Descriptions parsing error"))
        
    def fetchDetailsOK(self, txt_):
        print_info("fetch details OK", str(COOKIES))
        self["status_bar"].setText(_("Movie details loading completed"))
        self.inhtml = mautils.html2utf8(txt_)   
        if self.inhtml:
            try:
                self.parseLogin()
                self.parseFilmId()
                self.parseWallpaper(self.detailslink)                
                self.parseTitle()  
                ls = len(self["title_label"].getText())
                if ls < TITLE_MAX_SIZE:
                    self.parseOrgTitle() 
                self.parseRating()
                self.parsePoster()
                self.parseCast()
                self.parsePlot()            
                
                self.parseDetails()
            except:
                import traceback
                traceback.print_exc()
        else:
            self["status_bar"].setText(_("Movie details parsing error"))
        
    def fetchOK(self, txt_, tryOther=True):        
        print_info("Fetch OK", str(COOKIES))                
        self["status_bar"].setText(_("Filmweb Download completed"))
        self.inhtml = mautils.html2utf8(txt_)
        if self.inhtml:
            if self.inhtml.find('Automatyczne przekierowanie') > -1:
                if self.loopx == 0:
                    self.loopx = 1
                    self.getData()
                else:
                    self.loopx = 0
                return;
            self.search()
        lista = []
        for entry in self.resultlist:            
            caption = entry[0]
            link = entry[1]
            print_info("LISTA", "caption: " + str(caption) + ", lnk: " + link)
            lista.append(MovieSearchEntryComponent(text = caption))
        if len(lista) == 0:
            if tryOther:
                if self.searchType == MT_SERIE:
                    self.searchType = MT_MOVIE
                else:
                    self.searchType = MT_SERIE
                self.getData(False)
                return
            else:
                self["title_label"].setText(_("Entry not found in Filmweb.pl database"))
        self["menu"].l.setList(lista)
        #self["menu"].l.setList(self.resultlist)  
        self.switchView(to_mode='MENU')
                
    def fetchPosterOK(self, data):
        print_info("Fetch Poster OK", str(COOKIES)) 
        if not self.has_key('status_bar'):
            return
        self["status_bar"].setText(_("Poster downloading finished"))
        rpath = os.path.realpath(POSTER_PATH)
        print_info("Poster local real path", rpath)
        if os.path.exists(rpath):
            sc = AVSwitch().getFramebufferScale()
            self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
            self.picload.startDecode(rpath)
            if self.mode == VT_DETAILS:
                self["poster"].show()
    
    def fetchFailed(self, txt_):
        print_info("Fetch failed", str(txt_))
        if self.has_key('status_bar'):
            self["status_bar"].setText(_("Filmweb Download failed"))
        
    def paintPoster(self, picInfo=None):
        print_info("Paint poster", str(picInfo))
        ptr = self.picload.getData()
        if ptr != None:
            self["poster"].instance.setPixmap(ptr.__deref__())
            self["poster"].show()
            
    def parsePoster(self):
        self["poster"].hide()
        print_info("parsePoster", "started")   
        if self.inhtml.find('<div class=posterLightbox>') > -1:
            posterUrl = mautils.between(self.inhtml, '<div class=posterLightbox>', '</div>')
            posterUrl = mautils.between(posterUrl, 'href="', '" ')
        else:
            posterUrl = ''
        print_info("Poster URL", posterUrl)  
        if posterUrl != '' and posterUrl.find("jpg") > 0:
            #pname = mautils.before(posterUrl, "jpg")
            self["status_bar"].setText(_("Downloading Movie Poster: %s...") % (posterUrl))
            localfile = POSTER_PATH
            print_info("Downloading poster", posterUrl + " to " + localfile)
            downloadPage(posterUrl, localfile).addCallback(self.fetchPosterOK).addErrback(self.fetchFailed)            
            
    def parseDescriptions(self, dhtml):
        print_info("parseDescriptions", "started")
        descres = ''
        descs = mautils.between(dhtml, '<ul class=descriptionsList', '<script type=')
        #print_info("DESCS", str(descs))
        elements = descs.split('<li class=')
        if elements != '':
            for element in elements:
                if element == '':
                    continue
                element = mautils.between(element, '<p>', '</p>')
                element = element.replace('  ', ' ')
                element = mautils.strip_tags(element)
                #print_info("DESC", str(element))
                descres = descres + element + '\n\n'
        self["extra_label"].setText(descres)
        
    def parsePlot(self):
        print_info("parsePlot", "started")
        plot = mautils.between(self.inhtml, '<span class=filmDescrBg property="v:summary">', '</span>')
        plot = plot.replace('  ', ' ')
        plot = mautils.strip_tags(plot)
        print_info("PLOT", plot)
        self["plot_label"].setText(plot)
        
    def parseYear(self):
        print_info("parseYear", "started")
        year = mautils.between(self.inhtml, '<span id=filmYear class=filmYear>', '</span>')
        year = mautils.strip_tags(year)
        return year
        
    def parseGenere(self):
        print_info("parseGenere", "started")
        genre = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            genre = mautils.between(self.inhtml, "gatunek:", '</strong>')
        else:  
            genre = mautils.between(self.inhtml, "gatunek:", '</tr>')
        genre = mautils.strip_tags(genre)
        return genre
            
    def parseCast(self):
        print_info("parseCast", "started")  
        
        self.cast_list = []
        fidx = self.inhtml.find('<div class="castListWrapper cl">')
        if fidx > -1:
            #cast = mautils.between(self.inhtml, '<div class="castListWrapper cl">', '<div class="additional-info comBox">')
            cast = mautils.between(self.inhtml[fidx:], '<ul class=list>', '</ul>')
            
            elements = cast.split('<li')
            no_elems = len(elements)
            print_info("Cast list elements count", str(no_elems))
            cidx = 0
            if elements != '':
                for element in elements:
                    if element == '':
                        continue
                    element = mautils.after(element, '>')
                    print_info("Actor", "EL=" + element)
                    imge = mautils.between(element, '<img', '>')
                    print_info("Actor data", "IMG=" + imge)
                    imge = mautils.between(imge, 'src="', '"')
                    stre = element.replace('<div>', _(" as "))
                    stre = mautils.strip_tags(stre)
                    stre = stre.replace('   ', '')
                    stre = stre.replace('  ', ' ')
                    print_info("Actor data", "IMG=" + imge + ", DATA=" + stre)  
                    self.cast_list.append(ActorEntryComponent(self["cast_label"], img_url = imge, text = [stre], index=cidx))
                    cidx += 1            
            self["cast_label"].l.setList(self.cast_list)
                    
    def parseCountry(self):
        print_info("parseCountry", "started")
        country = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            country = mautils.between(self.inhtml, "kraj:", '</dd>')
            country = mautils.after(country, '<dd>')
        else:  
            country = mautils.between(self.inhtml, 'produkcja:', '</tr>')
        country = mautils.strip_tags(country)
        return country
    
    def parseWriter(self):
        print_info("parseWriter", "started")
        writer = mautils.between(self.inhtml, "scenariusz:", '</tr>')
        writer = mautils.after(writer, '</th>')
        writer = writer.replace("(więcej...)", '')
        writer = mautils.strip_tags(writer)
        return writer
        
    def parseDirector(self):
        print_info("parseDirector", "started")
        director = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            if self.inhtml.find("Twórcy:") > -1: 
                director = mautils.between(self.inhtml, "Twórcy:", '</dd>')
            else:  
                director = mautils.between(self.inhtml, "Twórca:", '</dd>')
            director = mautils.after(director, '<dd>')
        else: 
            director = mautils.between(self.inhtml, "reżyseria:", '</tr>')
            print_info("director to parse", director)
            director = mautils.after(director, '</th>')
            print_info("director after", director)
        director = director.replace("(więcej...)", '')
        director = mautils.strip_tags(director)
        print_info("director stripped", director)
        return director
        
    def parseRating(self):
        print_info("parseRating", "started")
        rating = mautils.between(self.inhtml, '<div class=rates>', '</div>')
        rating = mautils.between(rating, '<span property="v:average">', '</span>')
        if rating != '':
            rating = rating.replace(' ', '')
            rating = rating.replace(',', '.')
            rate = float(rating.strip())
            print_info("RATING", str(rate))
            self["rating_label"].setText(_("User Rating") + ": " + str(rate) + " / 10")
            ratingstars = int(10*round(rate,1))
            self["stars"].setValue(ratingstars)
        else:
            self["rating_label"].setText(_("no user rating yet"))
            self["stars"].setValue(0)
            
    def parseWallpaper(self, link_=None):
        print_info("parseWallpaper", "started")
        idx = self.inhtml.find('<li id="filmMenu-filmWallpapers" class=" caption">tapety</li>')
        print_info('Wallpaper idx', str(idx))
        if idx < 0:
            # only for logged users
            print_info("Parse wallpapers for link_" + str(link_) + ', SID: ' + str(self.sessionId) + ', FID: ' + str(self.filmId))
            if link_ and self.sessionId and self.filmId:  
                getPage(link_ + '/wallpapers', cookies=COOKIES).addCallback(self.fetchWallpaperOK).addErrback(self.fetchFailed)      
                
    def parseFilmId(self):
        print_info("parseFilmId", "started")
        fid = mautils.between(self.inhtml, '<div id=filmId style="display:none;">', '</div>') 
        if fid and len(fid) > 0:
            self.filmId = fid
        else:
            self.filmId = None
        print_info("FILM ID", str(self.filmId))
        
    def parseLogin(self):
        print_info("parseLogin", "started")
        idx = self.inhtml.find('userName')
        print_info("Login user idx", str(idx))
        if idx > -1:
            lg = mautils.between(self.inhtml, 'userName">', '</a>')            
            self["login_label"].setText(_("User") + ": " + lg)
        else:
            self["login_label"].setText("")
        
    def parseTitle(self):
        print_info("parseTitle", "started")
        title = mautils.between(self.inhtml, '<title>', '</title>')
        print_info("title first", title)
        if title.find('(') > -1:
            title = mautils.before(title, '(')
        if title.find('/') > -1:
            title = mautils.before(title, '/')   
        print_info("title last", title)     
        self["title_label"].setText(title)
        
    def parseOrgTitle(self):
        print_info("parseOrgTitle", "started")
        title = mautils.between(self.inhtml, '<h2 class=origTitle>', '</h2>')
        print_info("org title first", title)  
        if title != '':
            self["title_label"].setText(self["title_label"].getText() + " (" + title + ")")
    
    def parsePromoWidget(self):
        print_info("parsePromoWidget", "started")
        if self.sessionId is not None:
            idx = self.inhtml.find('<div id="svdRec" style="display:none">')
            if idx > 0:
                txt = mautils.between(self.inhtml, '<div id="svdRec" style="display:none">', '</div>')
                return txt
        return None
        
    def parseMyVote(self):
        print_info("parseMyVote", "started")
        idx = self.inhtml.find('gwt-currentVoteLabel')
        if idx > 0:
            txt = mautils.between(self.inhtml, 'gwt-currentVoteLabel>', '</span>')
            print_info("My VOTE", txt)
            num = mautils.between(txt, '(',')')
            if len(num) > 0 and num.isdigit():
                self.myvote = int(num)
                return txt 
        return ''
    
    def parseRuntime(self):
        print_info("parseRuntime", "started")
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            runtime = mautils.between(self.inhtml, "czas trwania:", '</strong>')
            runtime = mautils.after(runtime, '<strong>')
        else:  
            runtime = mautils.between(self.inhtml, 'var filmTime="', '";')
            #runtime = mautils.after(runtime, '<td>')
            #runtime = mautils.before(runtime, '</td>')
        runtime = runtime.replace(' ', '')        
        if not runtime:
            return
        print_info("Runtime parsed", runtime)
        str_m = ''
        str_h = ''
        if runtime.find('godz.') > -1:
            str_h = mautils.before(runtime, 'godz.')
            runtime = mautils.after(runtime, 'godz.')
        if runtime.find('min.') > -1:
            str_m = mautils.before(runtime, 'min.')
        print_info("Runtime", "godz: " + str_h + ", min: " + str_m)
        val_runtime = 0
        if str_h:
            val_runtime = 60 * int(float(str_h))
        if str_m:
            val_runtime += int(float(str_m))
        return val_runtime
        
    def parseDetails(self):
        genere = self.parseGenere()
        print_info("Movie Genere", genere)
        director = self.parseDirector()
        print_info("Movie Director", director)
        writer = self.parseWriter()
        print_info("Movie Writer", writer)
        country = self.parseCountry()
        print_info("Movie Country", country)
        year = self.parseYear()
        print_info("Movie Year", str(year))
        rtm = self.parseRuntime()   
        print_info("Movie Runtime", str(rtm))
        vote = self.parseMyVote()
        print_info("My Vote", str(vote))
        promo = self.parsePromoWidget()
        
        textdsp = _("Genre: ") + genere + "\n" + \
        _("Country: ") +  country + "\n" + \
        _("Director: ") + director + "\n" + \
        _("Writer: ") + writer + "\n" + \
        _("Year: ") + year + "\n" + \
        _("Runtime: ") + str(rtm) + " min.\n" + \
        _("My Vote: ") + str(vote) + "\n"
        
        if promo is not None:
            textdsp = textdsp + promo + '% ' + _('to your taste') + ' \n'
            
        self["details_label"].setText(textdsp)                     

    def inputSerieName(self):
        self.searchType = MT_SERIE
        dlg = self.session.openWithCallback(self.askForName, InputBox, 
                                      windowTitle = _("Input the name of serie to search"),
                                       title=_("Enter serie title to search for"), 
                                       text=self.eventName + " ", 
                                       maxSize=55, 
                                       type=Input.TEXT)
        dlg["input"].end()
        
    def configData(self):
        print_info("configData", "started")
        self.session.openWithCallback(self.configSaved, FilmwebConfig)
        
    def configSaved(self, val=False):
        print_info("configSaved", str(val))
        if val:
            self.loginPage()
    
    def voteMovie(self, res=None):
        if self.sessionId is None or self.userToken is None:
            self.session.open(MessageBox,_('In order to enter vote value you should be logged in'), MessageBox.TYPE_INFO)
        else:
            defa = '0 '
            if self.myvote > 0:
                defa = str(self.myvote) + ' '
            dlg = self.session.openWithCallback(self.rateEntered, InputBox, 
                                          windowTitle = _("Rating input"),
                                           title=_("Enter rating value"), 
                                           text=defa, 
                                           maxSize=55, 
                                           type=Input.NUMBER)
            dlg["input"].end()
        
    def rateEntered(self, val):
        if val is None:
            pass 
        else:
            voteVal = val.strip()
            isok = False
            if len(voteVal) > 0 and voteVal.isdigit():
                voteNum = int(voteVal) 
                if voteNum >= 0 and voteNum < 11:
                    isok = True
                    self.rateEntry(voteNum)
            if not isok:
                self.session.openWithCallback(self.voteMovie,MessageBox,_('You have to enter value in range [0, 10]'), MessageBox.TYPE_ERROR)
                        
    def inputMovieName(self):
        self.searchType = MT_MOVIE
        dlg = self.session.openWithCallback(self.askForName, InputBox, 
                                      windowTitle = _("Input the name of movie to search"),
                                       title=_("Enter movie title to search for"), 
                                       text=self.eventName + " ", 
                                       maxSize=55, 
                                       type=Input.TEXT)
        dlg["input"].end()
            
    def askForName(self, word): 
        if word is None:
            pass 
        else:
            self.eventName = word.strip()
            self.getData(False)
            #self.session.open(MessageBox,_(word.strip()), MessageBox.TYPE_INFO)
                               
    def search(self):     
        print_info("search", "started")   
        
        #output = open('/tmp/test.html', 'w')
        #f = self.inhtml.splitlines()
        #for line in f:
        #    output.write(line.rstrip() + '\n') 

        if self.searchType == MT_MOVIE:
            ttx = 'Filmy ('
        else:
            ttx = 'Seriale ('
        fidx = self.inhtml.find(ttx)
        print_info("search idx", str(fidx))  
        if fidx > -1:
            counts = mautils.between(self.inhtml, ttx, ')')
            #print_info("Movie count string", counts)
            count = mautils.castInt(counts.strip())
            print_info("Movie/Serie count", str(count))
            if count > 0:
                self.inhtml = mautils.between(self.inhtml[fidx:], '<ul id=searchFixCheck>', '</ul>')
            else:
                self.inhtml = None
        else:
            self.inhtml = None
            
        if self.inhtml is None:
            pass
        else:
            elements = self.inhtml.split('<li class=searchResult>')
            self.number_results = len(elements)
            print_info("Serach results count", str(self.number_results))
            if elements == '':
                self.number_results = 0
            else:
                for element in elements:
                    if element == '':
                        continue
                    element = mautils.after(element, 'searchResultTitle href="')
                    link = mautils.before(element, '"')
                    print_info("The movie link", link)
                    cast = mautils.after(element, 'class=searchHitCast')                    
                    cast =  mautils.between(cast, '>', '</div>')                    
                    cast = mautils.strip_tags(cast)
                    cast = cast.replace('\t', '')
                    cast = cast.replace('\n', '')
                    print_info("The movie cast", cast)
                    rating = mautils.after(element, 'class=searchResultRating')                    
                    rating =  mautils.between(rating, '>', '</div>')                    
                    rating = mautils.strip_tags(rating)
                    rating = rating.replace('\t', '')
                    rating = rating.replace('\n', '')
                    print_info("The movie rating", rating)                    
                    #self.links.append('http://www.filmweb.pl' + link)                    
                    title = mautils.between(element, '">', '</a>')
                    title = title.replace('\t', '')
                    print_info("The movie title", title)
                    element = mautils.after(element, 'class=searchResultDetails')
                    year = mautils.between(element, '>', '|')
                    year = year.replace(" ", '')
                    year = mautils.strip_tags(year)
                    print_info("The movie year", year)
                    country = ''
                    country_idx = element.find('countryIds')
                    if country_idx != -1:
                        country = mautils.between(element[country_idx:], '">', '</a>')
                    print_info("The movie country", country)
                    element = title.strip()
                    if year:
                        element += ' (' + year.strip() + ')'
                    if country:
                        element += ' - ' + country.strip()                    
                    #element = mautils.convert_entities(element)
                    element = mautils.strip_tags(element)
                    if rating:
                        element += '\n' + rating.strip()
                    if cast:
                        element += '\n' + cast.strip()
                    print_info("The movie serach title", element)
                    #self.titles.append(element)
                    self.resultlist.append((element,'http://www.filmweb.pl' + link))

