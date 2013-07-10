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

from enigma import eListboxPythonMultiContent

def MultiContentEntryProgressPixmap(pos=(0, 0), size=(0, 0), percent=None, pixmap=None, borderWidth=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None):
    return (eListboxPythonMultiContent.TYPE_PROGRESS_PIXMAP, pos[0], pos[1], size[0], size[1], percent, pixmap, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected)
