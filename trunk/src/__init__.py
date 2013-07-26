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

from enigma import getDesktop, addFont
from skin import loadSkin, loadSingleSkinData

import os
import sys

def findSkin(skinPath):
    try:
        import skin
        for entry in reversed(skin.dom_skins):
            if entry[0].startswith(skinPath):
                return  entry[1]
    except Exception:
        try:
            import skin
            for key in reversed(skin.dom_screens.keys()):
                if skin.dom_screens[key][1].startswith(skinPath):
                    return skin.dom_screens[key][0]
        except Exception:
            import traceback
            traceback.print_exc()

    return None

try:
    mf = sys.modules[__name__].__file__
    ppath = os.path.dirname(mf)
    print 'Plugin path: ' + ppath
    skin = "/usr/lib/enigma2/python/Plugins/Extensions/Filmweb/resource/skin/skin.xml"
    loadSkin(skin)
    mpath = os.path.dirname(skin) + "/"
    skind = findSkin(mpath)
    if not skind:
        import xml.etree.cElementTree
        skind = xml.etree.cElementTree.parse(skin).getroot()
    loadSingleSkinData(getDesktop(0), skind, mpath)
except:
    import traceback
    traceback.print_exc()

