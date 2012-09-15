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
from enigma import gFont, eTimer, ePicLoad, eServiceReference, eServiceCenter, eServiceEvent, eListboxPythonMultiContent, RT_HALIGN_LEFT
import mautils
import gettext
import os
import urllib
#import re
    
from ServiceReference import ServiceReference
from Tools.BoundFunction import boundFunction
#from Tools.LoadPixmap import LoadPixmap
#from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN

from Screens.Screen import Screen
from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.EpgSelection import EPGSelection
#from Screens.InfoBarGenerics import InfoBarEPG
from Screens.ChannelSelection import SimpleChannelSelection

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
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry, ConfigPassword, ConfigText, ConfigSubsection

USER_TOKEN = '_artuser_token'
SESSION_KEY = '_artuser_sessionId'
POSTER_PATH = "/tmp/poster.jpg"
TITLE_MAX_SIZE = 67

MT_MOVIE = 'film'
MT_SERIE = 'serial'

VT_NONE = 'none'
VT_MENU = 'MENU'
VT_DETAILS = 'DETAILS'
VT_EXTRAS = 'EXTRAS'

COOKIES = {}

config.plugins.mfilmweb = ConfigSubsection()
config.plugins.mfilmweb.user = ConfigText(default = "", fixed_size = False)
config.plugins.mfilmweb.password = ConfigPassword(default="",visible_width = 50,fixed_size = False)


def print_info(nfo, data):
    mautils.print_info("FILMWEB", nfo, data)    

def _(txt):
    t = gettext.dgettext("Filmweb", txt)
    if t == txt:
        t = gettext.gettext(txt)
    return t
        
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
        rpath = os.path.realpath("/tmp/actor_img_" + str(idx) + ".jpg")
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
        localfile = "/tmp/actor_img_" + str(index) + ".jpg"
        print_info("Downloading actor img", img_url + " to " + localfile)
        downloadPage(img_url, localfile).addCallback(fetchImgOK, index).addErrback(fetchImgFailed, index)
    #inst.cast_list.append(res)
    #inst["cast_label"].l.setList(inst.cast_list)
    return res

class FilmwebChannelSelection(SimpleChannelSelection):
    def __init__(self, session):
        SimpleChannelSelection.__init__(self, session, _("Channel Selection"))
        self.skinName = "SimpleChannelSelection"

        self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
            { "showEPGList": self.processSelected }
        )

    def processSelected(self):
        ref = self.getCurrentSelection()
        print_info("Channel selected", str(ref) + ", flags: " + str(ref.flags))
        # flagDirectory = isDirectory|mustDescent|canDescent
        if (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
            # when directory go to descent
            self.enterPath(ref)
        elif not (ref.flags & eServiceReference.isMarker):
            # open the event selection screen and handle on close event
            self.session.openWithCallback(
                self.onClosed,
                FilmwebEPGSelection,
                ref,
                openPlugin = False
            )

    def onClosed(self, ret = None):
        print_info("EPG Closed", str(ret)) 
        if ret:
            self.close(ret)
    
class FilmwebEPGSelection(EPGSelection):
    def __init__(self, session, ref, openPlugin = True):
        EPGSelection.__init__(self, session, ref)
        self.skinName = "EPGSelection"
        self["key_red"].setText(_("Lookup"))
        self.openPlugin = openPlugin

    def infoKeyPressed(self):
        print_info("Info Key pressed", "")
        self.lookup()
        
    def zapTo(self):
        self.lookup()
        
    #def onSelectionChanged(self):
    #    cur = self["list"].getCurrent()
    #    evt = cur[0]
    #    print_info("Selection Changed Event", str(evt))        
    
    def lookup(self):
        cur = self["list"].getCurrent()
        evt = cur[0]
        sref = cur[1]        
        print_info("Lookup EVT", str(evt))
        print_info("Lookup SREF", str(sref)) 
        if not evt: 
            return
        
        # when openPlugin is TRUE - open filmweb data window
        # otherwise only return the selected event name           
        if self.openPlugin:
            print_info("EVT short desc", str(evt.getShortDescription()))
            print_info("EVT ext desc", str(evt.getExtendedDescription()))
            print_info("EVT ptr", str(evt.getPtrString()))
            self.session.open(Filmweb, evt.getEventName())
        else:
            self.close(evt.getEventName())              
        
class FilmwebConfig(Screen, ConfigListScreen):
    skin = """<screen position="center,center" size="700,340" title="Filmweb Plugin Configuration">
        <widget name="config" position="10,30" size="680,230" scrollbarMode="showOnDemand" transparent="1"/>
        
        <ePixmap pixmap="skin_default/buttons/red.png" position="140,270" size="140,40" alphatest="on" />
        <ePixmap pixmap="skin_default/buttons/green.png" position="420,270" size="140,40"  alphatest="on" zPosition="1" />
        
        <widget name="key_red" position="140,270" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />        
        <widget name="key_green" position="420,270" zPosition="2" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
    </screen>"""
    
    def __init__(self, session):
        self.skin = FilmwebConfig.skin
        self.session = session
        Screen.__init__(self, session)
        
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        
        self["actions"] = ActionMap(["WizardActions", "ColorActions"],
        {
            "red": self.keyCancel,
            "back": self.keyCancel,
            "green": self.keySave,
        }, -2)
        self.list = []
        self.list.append(getConfigListEntry(_("User Name"), config.plugins.mfilmweb.user))
        self.list.append(getConfigListEntry(_("Password"), config.plugins.mfilmweb.password))
        self["config"].list = self.list
        self["config"].l.setList(self.list)     
        
    def keySave(self):            
        config.plugins.mfilmweb.save()
        configfile.save()
        self.close()

    def keyCancel(self):        
        self.close()
                
class Filmweb(Screen):
    skin = """<screen name="FilmwebData" position="90,105" size="1100,560" title="Filmweb.pl" >
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red25.png" position="20,505" size="250,40" alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green25.png" position="290,505" size="250,40" alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow25.png" position="560,505" size="250,40"  alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue25.png" position="830,505" size="250,40"  alphatest="on" />
            <widget name="key_red" position="20,508" size="250,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_green" position="290,508" size="250,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_yellow" position="560,508" size="250,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_blue" position="830,508" size="250,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="title_label" position="10,0" size="850,30" zPosition="5" valign="center" font="Regular;22" foregroundColor="#f0b400" transparent="1"/>
            <widget name="details_label" position="170,40" size="900,228" zPosition="5" font="Regular;19"  transparent="1"/>
            <widget name="plot_label" position="550,250" size="535,240" zPosition="5" font="Regular;18" transparent="1"/>
            <widget name="cast_label" position="10,250" size="535,240" zPosition="5" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="extra_label" position="10,30" size="1070,470" zPosition="5" font="Regular;18" transparent="1"/>
            <widget name="rating_label" position="870,56" size="210,25" zPosition="5" halign="center" font="Regular;18" foregroundColor="#f0b400" transparent="1"/>
            <widget name="login_label" position="870,5" size="210,20" zPosition="5" halign="center" font="Regular;18" foregroundColor="#58bcff" transparent="1"/>
            <widget name="status_bar" position="10,545" size="1070,20" zPosition="2" font="Regular;16" foregroundColor="#cccccc" transparent="1"/>
            <widget name="poster" position="20,26" size="140,216" zPosition="5" alphatest="blend" />
            <widget name="wallpaper" position="870,81" size="210,170" zPosition="0" alphatest="on" />
            <widget name="menu" position="10,80" size="1070,400" zPosition="5" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="stars_bg" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/starsbar_empty.png" position="870,35" zPosition="2" size="210,21" transparent="1" alphatest="on" />
            <widget name="stars" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/starsbar_filled.png" position="870,35" zPosition="5" size="210,21" transparent="1" />
        </screen>"""
              
    def __init__(self, session, eventName):
        Screen.__init__(self, session)
        print_info("Filmweb Screen - event", eventName)

        self.session = session
        self.eventName = eventName
        self.mode = ''
        self.searchType = MT_MOVIE
        self.descs = None
        self.sessionId = None
        self.userToken = None
        self.filmId = None
        self.detailDir = 0
        self.resultlist = []  
        self.cast_list = []
        self.loopx = 0      
        self.initialize = True
        self.wallpapers = []
        self.wallpaperidx = 0
                
        self.createGUI()
        self.initActions()
        self.switchView(to_mode=VT_NONE)
        
        self.wallpapertimer = eTimer()
        self.wallpapertimer.callback.append(self.changeWallpaper)
        self.wallpapertimer.start(10000)
            
        if config.plugins.mfilmweb.user.getText() == '':
            self.getData()
        else:
            self.loginPage(self.getData)
    
    event_quoted = property(lambda self: mautils.quote(self.eventName.encode('utf8')))
        
    def initActions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MovieSelectionActions", "DirectionActions"], {
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
            "showEventInfo": self.showDetails
        }, -1)
        
    # ---- ACTIONS ----  
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
        if self.sessionId and self.userToken:
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
        print_info("Channel selection", "exec")  
        self.session.openWithCallback(
            self.serachSelectedChannel,
            FilmwebChannelSelection
        )
                    
    def serachSelectedChannel(self, ret = None):
        print_info("Serach Selected Channel", str(ret)) 
        if ret:
            sr = ServiceReference(ret)            
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
                        
        getPage(link, cookies=COOKIES).addCallback(self.fetchDetailsOK, link).addErrback(self.fetchFailed) 
        
    def rateEntry(self, rating):
        try:
            print_info("rateEntry - user token", str(self.userToken) + ', rating: ' + str(rating))
            data = '5|0|6|http://2.fwcdn.pl/gwt/newFilmActivity/|CCD826B60450FCB69E9BD856EE06EAB5|filmweb.gwt.filmactivity.client.UserFilmRemoteService|setRate|J|I|1|2|3|4|2|5|6|599540|0|' + str(rating) + '|'
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
            if COOKIES.has_key(SESSION_KEY):
                COOKIES.pop(SESSION_KEY)
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
            self.session.open(MessageBox,_('Your vote has been registered'), MessageBox.TYPE_INFO)            
        
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
        if callback:
            callback()
            
    def switchGUI(self, to_mode=VT_MENU):
        print_info("Switching GUI", "old mode=" + self.mode + ", new mode=" + to_mode)
        self.mode = to_mode
        if self.mode == VT_MENU:
            self["menu"].show()
            self["details_label"].show()            
            
            self["login_label"].hide()
            self["plot_label"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
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
            
            self["wallpaper"].hide()            
            self["login_label"].hide()
            self["details_label"].hide()
            self["plot_label"].hide()
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
        
        #self["stars"].instance.setPixmap(LoadPixmap(cached=True, path=mautils.getPluginPath() + '/resource/starsbar_filled.png'))        
        #path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Filmweb/resource/starsbar_filled.png')
        #print_info("Current Path", str(path))
        
        self["stars_bg"] = Pixmap()      
        #self["stars_bg"].instance.setPixmap(LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Filmweb/resource/starsbar_empty.png')))  
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
            self.cast_list = []
            self.wallpapers = []
            self.wallpaperidx = 0
            self.descs = None
            self.filmId = None
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
        try:
            if not self.filmId:
                return
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
        print_info("Change wallpaper", str(self.wallpaperidx) + ", filmId: " + str(self.filmId))
        if self.filmId is None:
            return
        localfile = '/tmp/' + self.filmId + '.jpg'
        if len(self.wallpapers) > 0:               
            furl = self.wallpapers[self.wallpaperidx]               
            self.wallpaperidx = self.wallpaperidx + 1
            if self.wallpaperidx >= len(self.wallpapers):
                self.wallpaperidx = 0              
            print_info("Loading wallpaper", 'URL: ' + furl + ', Local File:' + localfile)
            downloadPage(furl, localfile).addCallback(self.fetchWallDataOK,localfile).addErrback(self.fetchFailed)
                        
    def fetchWallDataOK(self, txt_, localfile=None):
        if self.has_key("wallpaper") and self.filmId and localfile:
            print_info("Loading image data", str(localfile))
            self["wallpaper"].updateIcon(localfile)            
        
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
        
    def fetchDetailsOK(self, txt_, link_=None):
        print_info("fetch details OK", str(COOKIES))
        self["status_bar"].setText(_("Movie details loading completed"))
        self.inhtml = mautils.html2utf8(txt_)   
        if self.inhtml:
            try:
                self.parseLogin()
                self.parseFilmId()
                self.parseWallpaper(link_)                
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
        descs = mautils.between(dhtml, '<ul class=descriptionsList', '</ul>')
        elements = descs.split('<li class=desc')
        if elements != '':
            for element in elements:
                if element == '':
                    continue
                element = mautils.between(element, '<p>', '</p>')
                element = element.replace('  ', ' ')
                element = mautils.strip_tags(element)
                #print_info("DESC", str(element))
                descres = element + '\n\n'
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
        idx = self.inhtml.find('<li id="filmMenu-filmWallpapers" class=" caption">tapety</li>')
        if idx < 0:
            # only for logged users
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
        
        self["details_label"].setText(_("Genre: ") + genere + "\n" + 
                                      _("Country: ") +  country + "\n" + 
                                      _("Director: ") + director + "\n" + 
                                      _("Writer: ") + writer + "\n" +
                                      _("Year: ") + year + "\n" + 
                                      _("Runtime: ") + str(rtm) + " min.\n"                                           
                                      )                     

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
        
    def configSaved(self):
        print_info("configSaved", "started")
        self.loginPage()
    
    def voteMovie(self, res=None):
        if self.sessionId is None or self.userToken is None:
            self.session.open(MessageBox,_('In order to enter vote value you should be logged in'), MessageBox.TYPE_INFO)
        else:
            dlg = self.session.openWithCallback(self.rateEntered, InputBox, 
                                          windowTitle = _("Rating input"),
                                           title=_("Enter rating value"), 
                                           text="5 ", 
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
                if voteNum > 0 and voteNum < 11:
                    isok = True
                    self.rateEntry(voteNum)
            if not isok:
                self.session.openWithCallback(self.voteMovie,MessageBox,_('You have to enter value in range [1, 10]'), MessageBox.TYPE_ERROR)
                        
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

