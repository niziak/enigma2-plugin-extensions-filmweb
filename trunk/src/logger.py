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

import __common__ as cmn
from Components.config import config

APP_PREFIX = "[FILMWEB]"

def print_error(nfo, data=None):
    val = config.plugins.mfilmweb.logs.value
    if val == 'error' or val == 'info' or val == 'debug':
        cmn.print_info_(APP_PREFIX, 'ERROR', nfo, data)

def print_debug(nfo, data=None):
    val = config.plugins.mfilmweb.logs.value
    if val == 'debug':
        cmn.print_info_(APP_PREFIX, 'DEBUG', nfo, data)

def print_info(nfo, data=None):
    val = config.plugins.mfilmweb.logs.value
    if val == 'info' or val == 'debug':
        cmn.print_info_(APP_PREFIX, 'INFO', nfo, data)



