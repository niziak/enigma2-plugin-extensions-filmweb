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

from twisted.web.client import downloadPage
from __common__ import _
from logger import print_info, print_debug
import os
import sys

from config import config

from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Components.AVSwitch import AVSwitch
from Components.ScrollLabel import ScrollLabel
from enigma import gFont, ePicLoad, eListboxPythonMultiContent, RT_HALIGN_LEFT
from Components.Pixmap import Pixmap
from Components.ChoiceList import ChoiceList
from Components.MultiContent import MultiContentEntryText
from Components.ProgressBar import ProgressBar

ACTOR_IMG_PREFIX = "/actor_img_"

actorPicload = {}

class PixLoader(Pixmap):
    def __init__(self, callback=None):
        Pixmap.__init__(self)
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintMe)
        self.callback = callback
        self.filename = None

    def onShow(self):
        Pixmap.onShow(self)
        sc = AVSwitch().getFramebufferScale()
        self.picload.setPara((self.instance.size().width(), self.instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))

    def paintMe(self, picInfo=None):
        ptr = self.picload.getData()
        if ptr != None:
            self.instance.setPixmap(ptr.__deref__())
        if self.callback is not None:
            self.callback(self.filename)

    def updateIcon(self, filename):
        self.filename = filename
        self.picload.startDecode(filename)


class DefaultScreen(Screen):
    def __init__(self, session, temat):
        mf = sys.modules[__name__].__file__
        self.ppath = os.path.dirname(mf)
        print_debug('Plugin path', self.ppath)
        fn = resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/menu/BlackHoleEpgBackup.png')
        if (os.path.exists(fn)):
            skin = "%s/resource/%s_skin_bh.xml" % (self.ppath, temat)
        else:
            skin = "%s/resource/%s_skin_df.xml" % (self.ppath, temat)
        f = open(skin, "r")
        self.skin = f.read()
        f.close()

        Screen.__init__(self, session)
        print_debug("Screen init")


def MovieSearchEntryComponent(text=["--"]):
    res = [ text ]

    if text[0] == "--":
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 800, 65, 0, RT_HALIGN_LEFT, "-"*200))
    else:
        offset = 0
        for x in text.splitlines():
            if offset == 0:
                color = 0x00F0B400
                font = 1
            else:
                color = 0x00FFFFFF
                font = 0
            res.append(MultiContentEntryText(pos=(0, offset), size=(800, 25), font=font,
                                             flags=RT_HALIGN_LEFT, text=x,
                                             color=color, color_sel=color))
            offset = offset + 25
    return res

def ActorEntryComponent(inst, img_url="", text=["--"], index=0, ext='jpg'):
    res = [ text ]

    if len(img_url) > 4:
        ex = img_url[-4:]
        # print_debug("--- EXT", ex)
        if ex[0] == '.':
            ext = ex[1:]

    def paintImage(idx=None, picInfo=None):
        print_info("Paint Actor Image", str(idx))
        ptr = actorPicload[idx].getData()
        if ptr != None:
            print_debug("RES append", str(res) + " - img: " + str(ptr))
            res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 0, 40, 45, ptr))
            inst.l.invalidate()
        del actorPicload[idx]

    def fetchImgOK(data, idx):
        print_debug("fetchImgOK", str(idx))
        # print_debug("IMAGE EXT", ext)
        tmppath = config.plugins.mfilmweb.tmpPath.getValue()
        rpath = os.path.realpath(tmppath + ACTOR_IMG_PREFIX + str(idx) + "." + ext)
        if os.path.exists(rpath):
            sc = AVSwitch().getFramebufferScale()
            actorPicload[idx].setPara((40, 45, sc[0], sc[1], False, 1, "#00000000"))
            print_debug("Decode Image", rpath)
            actorPicload[idx].startDecode(rpath)

    def fetchImgFailed(data, idx):
        pass

    print_debug("IMAGE EXT", ext)
    if text[0] == "--" or img_url == '' or img_url.find(ext) < 0:
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 800, 45, 0, RT_HALIGN_LEFT, "-"*200))
    else:
        actorPicload[index] = ePicLoad()
        actorPicload[index].PictureData.get().append(boundFunction(paintImage, index))
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 0, 750, 45, 0, RT_HALIGN_LEFT, text[0]))
        tmppath = config.plugins.mfilmweb.tmpPath.getValue()
        localfile = tmppath + ACTOR_IMG_PREFIX + str(index) + "." + ext
        print_debug("Downloading actor img", img_url + " to " + localfile)
        downloadPage(img_url, localfile).addCallback(fetchImgOK, index).addErrback(fetchImgFailed, index)
    return res

class Scroller(object):
    def __init__(self, component=None):
        self.scroller = None
        self.component = component
        self.pixpath = resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/scroll.png')
        if (os.path.exists(self.pixpath)):
            self.scroller = Pixmap()
        if self.component:
            self.component.onVisibilityChange.append(self.__visChanged)
        else:
            self.onVisibilityChange.append(self.__visChanged)

    def __visChanged(self, flag):
        if self.scroller:
            if flag:
                self.scroller.show()
            else:
                self.scroller.hide()

    def createScroller(self, parent):
        if self.scroller:
            self.scroller.GUIcreate(parent)

    def deleteScroller(self):
        if self.scroller:
            self.scroller.GUIdelete()

    def applyScroller(self, desktop, parent):
        res = True
        if self.scroller:
            attrmap = {}
            attribs = self.component and self.component.skinAttributes or self.skinAttributes
            for (attrib, value) in attribs:
                try:
                    print_debug('ATTRIB', attrib + ": " + str(value))
                    attrmap[attrib] = value
                except:
                    import traceback
                    traceback.print_exc()

            self.scroller.skinAttributes = []

            self.scroller.skinAttributes.append(('pixmap', self.pixpath))
            self.scroller.skinAttributes.append(('alphatest', 'blend'))
            self.scroller.skinAttributes.append(('transparent', '1'))
            zp = attrmap['zPosition']
            if zp:
                zpn = int(zp) + 1
                self.scroller.skinAttributes.append(('zPosition', str(zpn)))
            res = self.scroller.applySkin(desktop, parent)

            px, py = self.component and self.component.getPosition() or self.getPosition()
            pt = self.component and self.component.instance.size() or self.instance.size()
            self.scroller.setPosition(px + pt.width() - 22, py - 2)
            self.scroller.resize(22, pt.height() + 2)
        return res

class ChoiceListExt(ChoiceList, Scroller):
    def __init__(self, lista):
        ChoiceList.__init__(self, lista)
        Scroller.__init__(self)

    def GUIcreate(self, parent):
        ChoiceList.GUIcreate(self, parent)
        self.createScroller(parent)

    def GUIdelete(self):
        self.deleteScroller()
        ChoiceList.GUIdelete(self)

    def applySkin(self, desktop, parent):
        ret = ChoiceList.applySkin(self, desktop, parent)
        rets = self.applyScroller(desktop, parent)
        return ret and rets

class MenuChoiceList(ChoiceListExt):
    def __init__(self, lista):
        ChoiceListExt.__init__(self, lista)

    def GUIcreate(self, parent):
        ChoiceListExt.GUIcreate(self, parent)
        self.l.setItemHeight(70)
        self.l.setFont(0, gFont("Regular", 16))
        self.l.setFont(1, gFont("Regular", 20))

    def createEntry(self, caption):
        return MovieSearchEntryComponent(text=caption)

class ActorChoiceList(ChoiceListExt):
    def __init__(self, lista):
        ChoiceListExt.__init__(self, lista)

    def GUIcreate(self, parent):
        ChoiceListExt.GUIcreate(self, parent)
        self.l.setItemHeight(50)

    def createEntry(self, imge, stre, cidx, ext='jpg'):
        print_debug('---createEntry---', imge)
        return ActorEntryComponent(self, img_url=imge, text=[stre], index=cidx, ext=ext)

class ScrollLabelExt(ScrollLabel, Scroller):
    def __init__(self, text=""):
        ScrollLabel.__init__(self, text)
        Scroller.__init__(self)

    def GUIcreate(self, parent):
        ScrollLabel.GUIcreate(self, parent)
        self.createScroller(parent)

    def GUIdelete(self):
        self.deleteScroller()
        ScrollLabel.GUIdelete(self)

    def applySkin(self, desktop, parent):
        ret = ScrollLabel.applySkin(self, desktop, parent)
        rets = self.applyScroller(desktop, parent)
        return ret and rets

class MPixmap(Pixmap):
    def __init__(self):
        Pixmap.__init__(self)
        mf = sys.modules[__name__].__file__
        self.ppath = os.path.dirname(mf)

    def applySkin(self, desktop, parent):
        attrmap = {}
        pixmap_path = None
        for (attrib, value) in self.skinAttributes:
            attrmap[attrib] = value

        if attrmap.has_key('pixmap'):
            pxm = attrmap['pixmap']
            pixmap_path = "%s%s" % (self.ppath, pxm)
            idx = 0;
            for (attrib, value) in self.skinAttributes:
                if attrib == 'pixmap':
                    self.skinAttributes.pop(idx)
                    break;
                idx += 1;
            self.skinAttributes.append(('pixmap', pixmap_path))
        return Pixmap.applySkin(self, desktop, parent)

class StarsComp(ProgressBar):
    def __init__(self):
        ProgressBar.__init__(self)
        self.bg = Pixmap()
        mf = sys.modules[__name__].__file__
        self.ppath = os.path.dirname(mf)
        self.onVisibilityChange.append(self.__visChanged)

    def __visChanged(self, flag):
        if flag:
            self.bg.show()
        else:
            self.bg.hide()

    def setPosition(self, x, y):
        ProgressBar.setPosition(self, x, y)
        self.bg.setPosition(x, y)

    def setZPosition(self, z):
        ProgressBar.setZPosition(self, z)
        self.bg.setZPosition(z - 1)

    def resize(self, x, y=None):
        self.bg.resize(x, y)
        ProgressBar.resize(self, x, y)

    def move(self, x, y=None):
        self.bg.move(x, y)
        ProgressBar.move(self, x, y)

    def destroy(self):
        self.bg.destroy()
        ProgressBar.destroy(self)

    def applySkin(self, desktop, parent):
        attrmap = {}
        idx = 0
        pixmap_path = None
        for (attrib, value) in self.skinAttributes:
            try:
                print_debug('ATTRIB - stars', attrib + ": " + str(value))
                attrmap[attrib] = value
                if attrib == 'pixmap_bg':
                    pixmap_path = "%s%s" % (self.ppath, value)
                    self.skinAttributes.pop(idx)
            except:
                import traceback
                traceback.print_exc()
            idx += 1

        self.bg.skinAttributes = []
        if pixmap_path:
            self.bg.skinAttributes.append(('pixmap', pixmap_path))
        if attrmap.has_key('transparent'):
            self.bg.skinAttributes.append(('transparent', attrmap['transparent']))
        self.bg.skinAttributes.append(('position', attrmap['position']))
        self.bg.skinAttributes.append(('size', attrmap['size']))
        self.bg.skinAttributes.append(('alphatest', 'on'))

        if attrmap.has_key('zPosition'):
            zp = attrmap['zPosition']
            zpn = int(zp) - 1
            self.bg.skinAttributes.append(('zPosition', str(zpn)))
        ret = self.bg.applySkin(desktop, parent)

        if attrmap.has_key('pixmap'):
            pxm = attrmap['pixmap']
            pixmap_path = "%s%s" % (self.ppath, pxm)
            idx = 0;
            for (attrib, value) in self.skinAttributes:
                if attrib == 'pixmap':
                    self.skinAttributes.pop(idx)
                    break;
                idx += 1;
            self.skinAttributes.append(('pixmap', pixmap_path))
        rets = ProgressBar.applySkin(self, desktop, parent)
        return rets and ret

    def GUIcreate(self, parent):
        ProgressBar.GUIcreate(self, parent)
        self.bg.GUIcreate(parent)

    def GUIdelete(self):
        self.bg.GUIdelete()
        ProgressBar.GUIdelete(self)




