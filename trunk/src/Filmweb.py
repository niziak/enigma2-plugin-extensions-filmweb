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
from enigma import gFont, eTimer, ePicLoad, eServiceReference, eServiceEvent, eListboxPythonMultiContent, RT_HALIGN_LEFT
import mautils
import gettext
from os import path
#import re
    
from Tools.BoundFunction import boundFunction
from Tools.LoadPixmap import LoadPixmap
#from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN

from Screens.Screen import Screen
from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
#from Screens.MessageBox import MessageBox
from Screens.EpgSelection import EPGSelection
#from Screens.InfoBarGenerics import InfoBarEPG
from Screens.ChannelSelection import SimpleChannelSelection

from Components.MultiContent import MultiContentEntryText, MultiContentEntryProgress, MultiContentTemplateColor
from Components.ChoiceList import ChoiceList
from Components.Input import Input
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.ActionMap import ActionMap

TITLE_MAX_SIZE = 67

VT_NONE = 'none'
VT_MENU = 'MENU'
VT_DETAILS = 'DETAILS'
VT_EXTRAS = 'EXTRAS'

COOKIES = {}

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
        rpath = path.realpath("/tmp/actor_img_" + str(idx) + ".jpg")
        if path.exists(rpath):
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
        
class Filmweb(Screen):
    skin = """<screen name="FilmwebData" position="90,105" size="1100,560" title="Filmweb.pl" >
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red25.png" position="20,505" size="250,40" alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green25.png" position="290,505" size="250,40" alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow25.png" position="560,505" size="250,40"  alphatest="on" />
            <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue25.png" position="830,505" size="250,40"  alphatest="on" />
            <widget name="key_red" position="65,508" size="160,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_green" position="344,508" size="160,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_yellow" position="610,508" size="160,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="key_blue" position="848,508" size="160,40" zPosition="2" font="Regular;24" valign="center" halign="center" backgroundColor="transpBlack" transparent="1" />
            <widget name="title_label" position="10,0" size="850,30" valign="center" font="Regular;22" foregroundColor="#f0b400" transparent="1"/>
            <widget name="details_label" position="170,40" size="900,228" font="Regular;19"  transparent="1"/>
            <widget name="plot_label" position="550,250" size="535,240" font="Regular;18" transparent="1"/>
            <widget name="cast_label" position="10,250" size="535,240" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="extra_label" position="10,30" size="1070,450" font="Regular;18" transparent="1"/>
            <widget name="rating_label" position="870,28" size="210,25" halign="center" font="Regular;18" foregroundColor="#f0b400" transparent="1"/>
            <widget name="status_bar" position="10,545" size="1070,20" font="Regular;16" foregroundColor="#cccccc" transparent="1"/>
            <widget name="poster" position="20,26" size="140,216" alphatest="on" />
            <widget name="menu" position="10,80" size="1070,400" zPosition="3" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="stars_bg" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/starsbar_empty.png" position="870,5" zPosition="0" size="210,21" transparent="1" alphatest="on" />
            <widget name="stars" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/starsbar_filled.png" position="870,5" size="210,21" transparent="1" />
        </screen>"""
              
    def __init__(self, session, eventName):
        Screen.__init__(self, session)
        print_info("Filmweb Screen - event", eventName)

        self.session = session
        self.eventName = eventName
        self.mode = ''
        self.detailDir = 0
        self.resultlist = []  
        self.cast_list = []
        self.loopx = 0      
                
        self.createGUI()
        self.initActions()
        self.switchView(to_mode=VT_NONE)
        self.getData()
    
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
        self.switchView(to_mode=VT_DETAILS)  
    def showMenu(self):
        self.switchView(to_mode=VT_MENU)  
    def showExtras(self):
        self.switchView(to_mode=VT_EXTRAS)        
    def contextMenuPressed(self):
        self.session.openWithCallback(
            self.menuCallback,
            ChoiceBox,
            list = [
                    (_("Enter movie title"), self.inputMovieName),
                    (_("Select from EPG"), self.channelSelection),
            ],
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
            #self.switchView(to_mode=VT_MENU)
            self.eventName = ret.getName()
            self.resultlist = []
            self.switchView(to_mode=VT_NONE)
            self.getData()
            
    def switchView(self, to_mode=VT_MENU):
        print_info("Switching view", "old mode=" + self.mode + ", new mode=" + to_mode)
        if self.mode == to_mode:
            return
        if to_mode == VT_MENU:
            size = len(self.resultlist)
            print_info("The movies list size", str(size))
            self["title_label"].setText('')
            if size == 0:
                self.inputMovieName()
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
        self.switchGUI(to_mode)
        
    def loadDetails(self, link, title):
        print_info("LOAD DETAILS", "link: " + link + ", title: " + title)
        self["status_bar"].setText(_("Seraching details for: %s...") % (title))
        print_info("Filmweb Details Query ", link)
                
        getPage(link, cookies=COOKIES).addCallback(self.fetchDetailsOK).addErrback(self.fetchFailed) 
                
    def switchGUI(self, to_mode=VT_MENU):
        self.mode = to_mode
        if self.mode == VT_MENU:
            self["menu"].show()
            self["details_label"].show()            
            
            self["plot_label"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
            self["rating_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["extra_label"].hide()
            
            self["title"].setText(_("Ambiguous results"))
            self["details_label"].setText(_("Please select the matching entry"))
            
            self["key_green"].setText("")
            self["key_yellow"].setText(_("Details"))
            self["key_blue"].setText("")
        elif self.mode == VT_DETAILS:
            self["rating_label"].show()
            self["cast_label"].show()
            self["details_label"].show()
            self["plot_label"].show()
            self["poster"].show()
            self["stars_bg"].show()
            self["stars"].show()
            
            self["menu"].hide()
            self["extra_label"].hide()
            
            self["key_green"].setText(_("Title Menu"))
            self["key_yellow"].setText("")
            self["key_blue"].setText("")
        elif self.mode == VT_EXTRAS:
            self["extra_label"].show()
            
            self["details_label"].hide()
            self["plot_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
            self["rating_label"].hide()
            self["menu"].hide()
            
            self["key_green"].setText("")
            self["key_yellow"].setText("")
            self["key_blue"].setText("")
        else:
            self["extra_label"].hide()            
            self["details_label"].hide()
            self["plot_label"].hide()
            self["cast_label"].hide()
            self["poster"].hide()
            self["stars"].hide()
            self["stars_bg"].hide()
            self["rating_label"].hide()
            self["menu"].hide()
            
            self["key_green"].setText('')
            self["key_yellow"].setText('')
            self["key_blue"].setText('')

    def createGUI(self):
        self["title_label"] = Label()
        def setLText(txt):
            print_info("setLText - Title Label", str(txt))
            if len(txt) > TITLE_MAX_SIZE:
                txt = txt[0:TITLE_MAX_SIZE - 3] + "..."
            Label.setText(self["title_label"], txt)
        self["title_label"].setText = setLText
        self["title"] = StaticText('')        
        self["title"].text = (_("The Filmweb Movie Database"))        
        self["poster"] = Pixmap()
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintPoster)
        self["stars"] = ProgressBar()        
        
        #self["stars"].instance.setPixmap(LoadPixmap(cached=True, path=mautils.getPluginPath() + '/resource/starsbar_filled.png'))        
        #path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Filmweb/resource/starsbar_filled.png')
        #print_info("Current Path", str(path))
        
        self["stars_bg"] = Pixmap()      
        #self["stars_bg"].instance.setPixmap(LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Filmweb/resource/starsbar_empty.png')))  
        self["details_label"] = Label("")
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
        
    def getData(self):
        self.resultlist = []
        if not self.eventName or len(self.eventName.strip()) == 0:
            s = self.session.nav.getCurrentService()
            info = s and s.info()
            print_info("Current Service Info", str(info))
            event = info and info.getEvent(0) 
            print_info("Current Event", str(event))
            if event:
                self.eventName = event.getEventName()
            if len(str(self.eventName).strip()) == 0:
                event = info and info.getEvent(1)
                print_info("Next Event", str(event))
                if event:
                    self.eventName = event.getEventName()
        print_info("Getting data for event with name", self.eventName)
        if self.eventName:
            self["status_bar"].setText(_("Query Filmweb: %s...") % (self.eventName))
            #localfile = "/tmp/filmweb_query.html"            
            fetchurl = "http://www.filmweb.pl/search/film?q=" + self.event_quoted
            #print_info("Filmweb Query " + fetchurl + " to ", localfile)
            print_info("Filmweb Query ", fetchurl)
            getPage(fetchurl, cookies=COOKIES).addCallback(self.fetchOK).addErrback(self.fetchFailed)            
        else:
            self["status_bar"].setText(_("Unknown Eventname"))
            self["title_label"].setText(_("Unknown Eventname"))
            self.switchView(to_mode='')

    def fetchDetailsOK(self, txt_):
        print_info("fetch details OK", str(COOKIES))
        self["status_bar"].setText(_("Movie details loading completed"))
        self.inhtml = mautils.html2utf8(txt_)   
        if self.inhtml:
            self.parseTitle()  
            ls = len(self["title_label"].getText())
            if ls < TITLE_MAX_SIZE:
                self.parseOrgTitle() 
            self.parseRating()
            self.parsePoster()
            self.parseCast()
            self.parsePlot()            
            
            self.parseDetails()
        else:
            self["status_bar"].setText(_("Movie details parsing error"))
        
    def fetchOK(self, txt_):        
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
        self["menu"].l.setList(lista)
        #self["menu"].l.setList(self.resultlist)  
        self.switchView(to_mode='MENU')
                
    def fetchPosterOK(self, data):
        print_info("Fetch Poster OK", str(COOKIES)) 
        self["status_bar"].setText(_("Poster downloading finished"))
        rpath = path.realpath("/tmp/poster.jpg")
        print_info("Poster local real path", rpath)
        if path.exists(rpath):
            sc = AVSwitch().getFramebufferScale()
            self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
            self.picload.startDecode(rpath)
    
    def fetchFailed(self, txt_):
        print_info("Fetch failed", str(txt_))
        self["status_bar"].setText(_("Filmweb Download failed"))
        
    def paintPoster(self, picInfo=None):
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
            localfile = "/tmp/poster.jpg"
            print_info("Downloading poster", posterUrl + " to " + localfile)
            downloadPage(posterUrl, localfile).addCallback(self.fetchPosterOK).addErrback(self.fetchFailed)            
            
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
            runtime = mautils.between(self.inhtml, "czas trwania:", '</tr>')
            runtime = mautils.after(runtime, '<td>')
            runtime = mautils.before(runtime, '</td>')
        runtime = runtime.replace(' ', '')
        if not runtime:
            return
        str_m = ''
        str_h = ''
        if runtime.find('godz.') > -1:
            str_h = mautils.before(runtime, 'godz.')
            runtime = mautils.after(runtime, 'godz.')
        if runtime.find('min.') > -1:
            str_m = mautils.before(runtime, 'min.')
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
        rt = self.parseRuntime()   
        print_info("Movie Runtime", str(rt))
        
        self["details_label"].setText(_("Genre: ") + genere + "\n" + 
                                      _("Country: ") +  country + "\n" + 
                                      _("Director: ") + director + "\n" + 
                                      _("Writer: ") + writer + "\n" +
                                      _("Year: ") + year + "\n" + 
                                      _("Runtime: ") + str(rt) + " min.\n"                                           
                                      )                     

    def inputMovieName(self):
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
            self.getData()
            #self.session.open(MessageBox,_(word.strip()), MessageBox.TYPE_INFO)
                               
    def search(self):     
        print_info("search", "started")   
        
        #output = open('/tmp/test.html', 'w')
        #f = self.inhtml.splitlines()
        #for line in f:
        #    output.write(line.rstrip() + '\n') 

        fidx = self.inhtml.find('Filmy (')
        print_info("search idx", str(fidx))  
        if fidx > -1:
            counts = mautils.between(self.inhtml, 'Filmy (', ')')
            #print_info("Movie count string", counts)
            count = mautils.castInt(counts.strip())
            print_info("Movie count", str(count))
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

