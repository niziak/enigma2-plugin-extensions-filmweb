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

import os
import re
import string
try:
    import htmlentitydefs
    from urllib import quote_plus
    iteritems = lambda d: d.iteritems()
except ImportError as ie:
    from html import entities as htmlentitydefs
    from urllib.parse import quote_plus
    iteritems = lambda d: d.items()
    
def getPluginPath():
    return os.path.dirname(os.path.realpath(__file__))
  
def quote(txt):
    return quote_plus(txt) 

def castInt(x):
    if x is None:
        return None;
    try:
        return int(x)
    except:
        return None; 

def strip_tags(text):
    if text is None:
        return None
    process = 1
    while process:
        process = 0
        start = text.find("<")
        if start >= 0:
            stop = text[start:].find(">")
            if stop >= 0:
                text = text[:start] + text[start+stop+1:]
                process = 1
    return text

def between(text,key1,key2):
    p1 = string.find(text,key1)
    if p1 == -1:
        return ""
    else:
        p1 = p1+len(key1)
    p2 = string.find(text[p1:],key2)
    if p2 == -1:
        return ""
    else:
        p2 = p1+p2
    return text[p1:p2]
    
def after(text,key):
    p1 = string.find(text,key)
    return text[p1+len(key):]

def before(text,key):
    p1 = string.find(text,key)
    return text[:p1]

def print_info(prefix, nfo, data):
    print "[" + prefix + "] " + nfo + ": " + data
    
def getKey(val, repo):
    for key, value in iteritems(repo):    
        if value == val: 
            return key
    return None

def html2utf8(in_html, code='utf8'):
    entitydict = {}

    entities = re.finditer('&([^#][A-Za-z]{1,5}?);', in_html)
    for x in entities:
        key = x.group(0)
        if key not in entitydict:
            elem = x.group(1)
            entitydict[key] = htmlentitydefs.name2codepoint[elem]
            print_info("MAUTILS", "Dictionary-1", str(key) + "->" + str(elem) + "->" + str(entitydict[key]))

    entities = re.finditer('&#x([0-9A-Fa-f]{2,2}?);', in_html)
    for x in entities:
        key = x.group(0)
        if key not in entitydict:
            entitydict[key] = "%d" % int(key[3:5], 16)
            print_info("MAUTILS","Dictionary-2", str(key) + "->" + str(int(key[3:5], 16)) + "->" + str(entitydict[key]))

    entities = re.finditer('&#(\d{1,5}?);', in_html)
    for x in entities:
        key = x.group(0)
        if key not in entitydict:
            entitydict[key] = x.group(1)
            print_info("MAUTILS","Dictionary-3", str(key) + "->" + str(entitydict[key]))

    for key, codepoint in iteritems(entitydict):
        utfchar = unichr(int(codepoint)).encode(code, 'ignore')
        print_info("MAUTILS","KEY-CODEPOINT-UTF", str(key) + "->" + str(codepoint) + "->" + utfchar)            
        in_html = in_html.replace(key, utfchar)
        
    #print_info("MAUTILS","result", in_html)
    return in_html.decode(code).encode('utf8')
    
    
    