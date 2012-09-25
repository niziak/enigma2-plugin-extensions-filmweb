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

from __common__ import print_info, _

from Screens.Screen import Screen

from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry, ConfigPassword, ConfigText, ConfigSubsection

config.plugins.mfilmweb = ConfigSubsection()
config.plugins.mfilmweb.user = ConfigText(default = "", fixed_size = False)
config.plugins.mfilmweb.password = ConfigPassword(default="",visible_width = 50,fixed_size = False)
config.plugins.mfilmweb.selserv = ConfigText(default = "", fixed_size = False)

class FilmwebConfig(Screen, ConfigListScreen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skinName = ["Setup" ]
        self.setup_title = _("Filmweb Config")
        
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
        {
            "cancel": self.keyCancel,
            "ok": self.keySave,
            "red": self.keyCancel,
            "green": self.keySave,
        }, -2)
        self.list = []
        self.list.append(getConfigListEntry(_("User Name"), config.plugins.mfilmweb.user))
        self.list.append(getConfigListEntry(_("Password"), config.plugins.mfilmweb.password))
        self["config"].list = self.list
        self["config"].l.setList(self.list)   
        
        self.onLayoutFinish.append(self.layoutFinished)  
        
    def layoutFinished(self):
        self.setTitle(self.setup_title)
        
    def keySave(self):            
        config.plugins.mfilmweb.save()
        configfile.save()
        self.close(True)

    def keyCancel(self):        
        self.close(False)
