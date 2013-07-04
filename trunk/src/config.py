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

from __common__ import _
from logger import print_info, print_debug

from Screens.Screen import Screen

from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigBoolean, ConfigInteger, ConfigDirectory, ConfigPassword, ConfigText, ConfigSubsection

config.plugins.mfilmweb = ConfigSubsection()
config.plugins.mfilmweb.user = ConfigText(default="", fixed_size=False)
config.plugins.mfilmweb.password = ConfigPassword(default="", visible_width=50, fixed_size=False)
config.plugins.mfilmweb.imdbUser = ConfigText(default="test", fixed_size=False)
config.plugins.mfilmweb.imdbPassword = ConfigPassword(default="test", visible_width=50, fixed_size=False)
config.plugins.mfilmweb.selserv = ConfigText(default="", fixed_size=False)
config.plugins.mfilmweb.tmpPath = ConfigText(default="/tmp/filmweb", fixed_size=False)
config.plugins.mfilmweb.logs = ConfigSelection([('debug', _('Debug Level')), ('info', _('Info Level')), ('error', _('Error Level'))], default='debug')
config.plugins.mfilmweb.guideDays = ConfigInteger(default=1, limits=(1, 4))
config.plugins.mfilmweb.sort = ConfigInteger(default=0)
config.plugins.mfilmweb.sortOrder = ConfigBoolean()
config.plugins.mfilmweb.imdbData = ConfigYesNo(default=False)
config.plugins.mfilmweb.showNotifications = ConfigYesNo(default=True)
config.plugins.mfilmweb.engine = ConfigSelection([('FILMWEB', _('Filmweb Engine')), ('IMDB', _('IMDB Engine'))], default='FILMWEB')

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
        # self.list.append(getConfigListEntry(_("IMDB User Name"), config.plugins.mfilmweb.imdbUser))
        # self.list.append(getConfigListEntry(_("IMDB Password"), config.plugins.mfilmweb.imdbPassword))
        self.list.append(getConfigListEntry(_("Temporary Folder"), config.plugins.mfilmweb.tmpPath))
        self.list.append(getConfigListEntry(_("Logging Level"), config.plugins.mfilmweb.logs))
        self.list.append(getConfigListEntry(_("Select Engine"), config.plugins.mfilmweb.engine))
        self.list.append(getConfigListEntry(_("Number of days in movie guide search"), config.plugins.mfilmweb.guideDays))
        self.list.append(getConfigListEntry(_("Get IMDB data for Movie Guide entries"), config.plugins.mfilmweb.imdbData))
        self.list.append(getConfigListEntry(_("Show -Want to See- Notifications"), config.plugins.mfilmweb.showNotifications))
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
