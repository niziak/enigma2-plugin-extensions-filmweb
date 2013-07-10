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

from Components.Converter.StringList import StringList
from Components.Converter.TemplatedMultiContent import TemplatedMultiContent

class ExTMultiContent(TemplatedMultiContent):
    def __init__(self, args):
        StringList.__init__(self, args)
        from enigma import gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_VALIGN_BOTTOM, RT_WRAP
        from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend, MultiContentTemplateColor, MultiContentEntryProgress
        from Components.Converter.MultiContentEntryProgressPixmap import MultiContentEntryProgressPixmap
        l = locals()
        del l["self"]
        del l["args"]

        self.active_style = None
        self.template = eval(args, {}, l)

        if not "template" in self.template:
            self.template["template"] = self.template["templates"]["default"][1]
            self.template["itemHeight"] = self.template["template"][0]

        print 'TEMPLATE: %s' % (str(self.template))


