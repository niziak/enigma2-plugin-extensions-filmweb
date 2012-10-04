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
from __common__ import print_info, print_debug
import time
import datetime
import mautils
import urllib
import os
import sys

MT_MOVIE = 'film'
MT_SERIE = 'serial'

USER_TOKEN = '_artuser_token'
SESSION_KEY = '_artuser_sessionId'
POSTER_PATH = "/tmp/poster.jpg"

PAGE_URL = 'http://www.filmweb.pl'
SEARCH_QUERY_URL = PAGE_URL + "/search/"
LOGIN_QUERY_URL = 'https://ssl.filmweb.pl/j_login'

COOKIES = {}
MAPPING = {}
MAPPING2 = {}

def loadMappings():
    try:
        rpath = os.path.dirname(sys.modules[__name__].__file__)
        print_info('TV Channel Mappings loading', rpath)
        global MAPPING
        global MAPPING2
        path = '%s/resource/services.dat' % (rpath)
        if os.path.exists(path):
            sfile = open(path, "r")
            lines = sfile.readlines()
            for x in lines:
                dt = x.strip().split(',')
                if dt and len(dt) > 2:
                    srv = dt[2]
                    if len(srv.strip()) > 0:
                        MAPPING[dt[1]] = srv                    
                    if len(dt) > 3:
                        srv = dt[3]
                        if len(srv.strip()) > 0:
                            MAPPING2[dt[1]] = srv
    except:
        import traceback
        traceback.print_exc() 
    finally:
        if sfile is not None:
            sfile.close()  

loadMappings()
 
class FilmwebEngine(object):
    def __init__(self, failureHandler=None, statusComponent=None):
        self.inhtml = None
        self.loopx = 0  
        self.resultlist = []       
        self.detailsData = {} 
        self.failureHandler = failureHandler
        self.statusComponent = statusComponent
    
    def login(self, username, password, callback=None, resdata=None):
        print_debug("LoginPage", "started")
        if self.statusComponent:
            self.statusComponent.setText(_('Logging in ...'))
        if COOKIES.has_key(SESSION_KEY):
            COOKIES.pop(SESSION_KEY)
        if COOKIES.has_key(USER_TOKEN):
            COOKIES.pop(USER_TOKEN)  
        data = {'j_username': username, "j_password" : password}
        data = urllib.urlencode(data)
        print_info("LoginPage data", str(data))
        return getPage(LOGIN_QUERY_URL, method='POST', postdata=data, 
                headers={'Content-Type':'application/x-www-form-urlencoded'},
                cookies=COOKIES).addCallback(self.__fetchLoginRes, callback, resdata).addErrback(self.__fetchLoginRes, callback, resdata)        

    def queryDetails(self, link, callback=None, sessionId=None):
        return getPage(link, cookies=COOKIES).addCallback(self.__fetchDetailsOK, link, callback, sessionId).addErrback(self.__fetchFailed) 
        
    def query(self, type, title, year=None, tryOther=False, callback=None, data=None):
        fetchurl = SEARCH_QUERY_URL + type + "?q=" + mautils.quote(title.encode('utf8'))
        if year:
            fetchurl += '&startYear=' + year + '&endYear=' + year
        print_info("Filmweb Query", fetchurl)
        return self.__fetchEntries(fetchurl, type, callback, tryOther, data)

    def searchWallpapers(self, link_, callback):
        if link_:  
            return getPage(link_, cookies=COOKIES).addCallback(self.__fetchWallpaperOK, callback).addErrback(self.__fetchFailed)
        return None      
                
    def loadPoster(self, posterUrl, callback=None, localfile = POSTER_PATH):
        if posterUrl:                                
            print_info("Downloading poster", posterUrl + " to " + localfile)
            return downloadPage(posterUrl, localfile).addCallback(self.__fetchPosterOK, localfile, callback).addErrback(self.__fetchFailed)
        return None
                        
    def loadWallpaper(self, furl, localfile, callback):
        if not furl or not localfile:
            return None
        print_info("Loading wallpaper", 'URL: ' + furl + ', Local File:' + localfile)
        return downloadPage(furl, localfile).addCallback(callback,localfile).addErrback(self.__fetchFailed)

    def loadDescriptions(self, furl, callback):  
        if not furl:
            return None
        print_info("LOAD DESCS - link", furl + "/descs")                  
        return getPage(furl + "/descs", cookies=COOKIES).addCallback(self.__fetchExtraOK, callback).addErrback(self.__fetchFailed)

    def applyRating(self, rating, filmId, userToken, callback):
        if rating and filmId:
            print_debug("rateEntry - user token", str(userToken) + ', rating: ' + str(rating))
            data = '5|0|6|http://2.fwcdn.pl/gwt/newFilmActivity/|CCD826B60450FCB69E9BD856EE06EAB5|filmweb.gwt.filmactivity.client.UserFilmRemoteService|setRate|J|I|1|2|3|4|2|5|6|' + str(filmId) + '|0|' + str(rating) + '|'
            print_debug("POST DATA", data)
            headers = {'Content-Type':'text/x-gwt-rpc; charset=UTF-8',
                       'Host':'www.filmweb.pl',
                       'Origin':'http://www.filmweb.pl',
                       'X-GWT-Module-Base':'http://2.fwcdn.pl/gwt/newFilmActivity/',
                       'X-GWT-Permutation':'7C0EB94ECB5DCB0BABC0AE73531FA849',
                       'X-Artuser-Token': userToken
                       }
            return getPage(PAGE_URL + '/rpc/userFilmRemoteService', method='POST', postdata=data, 
                    headers=headers,
                    cookies=COOKIES).addCallback(callback).addErrback(callback)  
        return None  
        

############################################# LOCAL METHODS ###############################


    def __fetchExtraOK(self, txt_, callback):
        try:
            print_debug("fetch extra OK", str(COOKIES))
            if self.statusComponent:
                self.statusComponent.setText(_("Descriptions loading completed"))
            dhtml = mautils.html2utf8(txt_)
            data = None
            if dhtml:
                data = self.parseDescriptions(dhtml)
            if callback:
                callback(data)
        except:
            import traceback
            traceback.print_exc()            
            
    def __fetchWallpaperOK(self, txt_, callback):
        print_debug("fetchWallpaperOK ...")
        try:
            wallpapers = []
            print_debug("fetch wallpaper OK", str(COOKIES))
            if self.statusComponent:
                self.statusComponent.setText(_("Wallpaper loading completed"))
            if txt_ and len(txt_) > 0:
                walls = mautils.after(txt_, '<ul class=filmWallapersList')
                elements = walls.split('filmWallapersItem')
                elcount = len(elements)
                print_debug("Wallpapers count", str(elcount))                
                if elcount > 0: # and self.has_key('wallpaper'):
                    furl = None
                    for elem in elements:
                        didx = elem.find('<span class=newLinkLoggedOnly>')
                        print_debug("Wallpaper idx", str(didx))
                        if didx > -1:                            
                            furl = mautils.between(elem, '<span class=newLinkLoggedOnly>', '</span>')
                            print_debug("URL", furl)
                            wallpapers.append(furl)
            if callback:
                callback(wallpapers)
        except:
            import traceback
            traceback.print_exc()
                    
    def __fetchPosterOK(self, data, localfile, callback=None):
        try:
            print_debug("Fetch Poster OK", str(COOKIES)) 
            #if not self.has_key('status_bar'):
            #    return
            if self.statusComponent:
                self.statusComponent.setText(_("Poster downloading finished"))
            rpath = os.path.realpath(localfile)
            print_debug("Poster local real path", rpath)
            if os.path.exists(rpath):
                if callback:
                    return callback(rpath)
                else:
                    return rpath
            return None
        except:
            import traceback
            traceback.print_exc()
                
    def __fetchLoginRes(self, res_, callback, data):
        try:
            print_debug("RESULT COOKIE", str(COOKIES))
            if COOKIES.has_key(SESSION_KEY):
                sessionId = COOKIES[SESSION_KEY]            
            else:
                sessionId = None
            if COOKIES.has_key(USER_TOKEN):
                userToken = COOKIES[USER_TOKEN]            
            else:
                userToken = None     
            if self.statusComponent:
                self.statusComponent.setText(_('Login done'))   
            print_info('Login data', str(userToken) + ', SID: ' + str(sessionId))
            if callback:
                callback(userToken, sessionId, data)
        except:
            import traceback
            traceback.print_exc()             
            
    def __fetchDetailsOK(self, txt_, link, callback, sessionId):
        print_info("fetch details OK", str(COOKIES))
        if self.statusComponent:
            self.statusComponent.setText(_("Movie details loading completed"))
        self.inhtml = mautils.html2utf8(txt_)   
        self.detailsData = {}
        if self.inhtml:
            try:
                self.parseLogin()
                self.parseFilmId()                          
                self.parseTitle()  
                self.parseOrgTitle() 
                self.parseRating()
                self.parsePoster()                
                self.parsePlot()                            
                self.parseGenere()
                self.parseDirector()
                self.parseWriter()
                self.parseCountry()
                self.parseYear()
                self.parseRuntime()   
                self.parseMyVote()
                self.parsePromoWidget(sessionId)                
                self.parseWallpaper(link)                      
                self.parseCast()
            except:
                import traceback
                traceback.print_exc()
        else:
            self.detailsData = None
        if (callback):
            return callback(self.detailsData)
        return self.detailsData
            
    def __fetchEntries(self, fetchurl, type, callback, tryOther=True, data=None):
        self.resultlist = []
        return getPage(fetchurl, cookies=COOKIES).addCallback(self.__fetchOK, callback, tryOther, fetchurl, type, data).addErrback(self.__fetchFailed) 
        
    def __fetchOK(self, txt_, callback, tryOther, fetchurl, type, data):        
        print_debug("Fetch OK", str(COOKIES))                
        if self.statusComponent:
            self.statusComponent.setText(_("Filmweb Download completed"))
        self.inhtml = mautils.html2utf8(txt_)
        if self.inhtml:
            if self.inhtml.find('Automatyczne przekierowanie') > -1:
                df = None
                if self.loopx == 0:
                    self.loopx = 1
                    df = self.__fetchEntries(fetchurl, type, callback, tryOther, data)
                else:
                    self.loopx = 0
                return df
            self.__parseEntries(type)
        if len(self.resultlist) == 0:
            if tryOther:
                if type == MT_SERIE:
                    type = MT_MOVIE
                else:
                    type = MT_SERIE
                return self.__fetchEntries(fetchurl, type, callback, False, data)
        if callback:
            return callback(self.resultlist, type, data)            
        return None
        
    def __fetchFailed(self, txt_):
        print_info("Fetch failed", str(txt_))
        if self.failureHandler:
            self.failureHandler(txt_)

    def __parseEntries(self, type):     
        print_debug("__parseEntries", "started")   
        if type == MT_MOVIE:
            ttx = 'Filmy ('
        else:
            ttx = 'Seriale ('
        fidx = self.inhtml.find(ttx)
        print_debug("search idx", str(fidx))  
        if fidx > -1:
            counts = mautils.between(self.inhtml, ttx, ')')
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
            number_results = len(elements)
            print_info("Serach results count", str(number_results))
            if elements == '':
                number_results = 0
            else:
                for element in elements:
                    if element == '':
                        continue
                    element = mautils.after(element, 'searchResultTitle href="')
                    link = mautils.before(element, '"')
                    print_debug("The movie link", link)
                    cast = mautils.after(element, 'class=searchHitCast')                    
                    cast =  mautils.between(cast, '>', '</div>')                    
                    cast = mautils.strip_tags(cast)
                    cast = cast.replace('\t', '')
                    cast = cast.replace('\n', '')
                    print_debug("The movie cast", cast)
                    rating = mautils.after(element, 'class=searchResultRating')                    
                    rating =  mautils.between(rating, '>', '</div>')                    
                    rating = mautils.strip_tags(rating)
                    rating = rating.replace('\t', '')
                    rating = rating.replace('\n', '')
                    print_debug("The movie rating", rating)                    
                    #self.links.append('http://www.filmweb.pl' + link)                    
                    title = mautils.between(element, '">', '</a>')
                    title = title.replace('\t', '')
                    title = mautils.strip_tags(title)
                    print_debug("The movie title", title)
                    element = mautils.after(element, 'class=searchResultDetails')
                    year = mautils.between(element, '>', '|')
                    year = year.replace(" ", '')
                    year = mautils.strip_tags(year)
                    print_debug("The movie year", year)
                    country = ''
                    country_idx = element.find('countryIds')
                    if country_idx != -1:
                        country = mautils.between(element[country_idx:], '">', '</a>')
                    print_debug("The movie country", country)
                    element = title.strip()
                    if year:
                        element += ' (' + year.strip() + ')'
                    if country:
                        element += ' - ' + country.strip()    
                    basic_data = element                
                    #element = mautils.convert_entities(element)
                    element = mautils.strip_tags(element)
                    if rating:
                        element += '\n' + rating.strip()
                    if cast:
                        element += '\n' + cast.strip()
                    print_info("The movie serach title", element)
                    #self.titles.append(element)
                    rt = rating.split()
                    self.resultlist.append((element, PAGE_URL + link, basic_data, title, rt[0], year, country))
        
    def parsePlot(self):
        print_debug("parsePlot", "started")
        plot = mautils.between(self.inhtml, '<span class=filmDescrBg property="v:summary">', '</span>')
        plot = plot.replace('  ', ' ')
        plot = mautils.strip_tags(plot)
        print_debug("PLOT", plot)
        self.detailsData['plot'] = plot        
        
    def parseYear(self):
        print_debug("parseYear", "started")
        year = mautils.between(self.inhtml, '<span id=filmYear class=filmYear>', '</span>')
        year = mautils.strip_tags(year)
        self.detailsData['year'] = str(year)
        
    def parseGenere(self):
        print_debug("parseGenere", "started")
        genre = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            genre = mautils.between(self.inhtml, "gatunek:", '</strong>')
        else:  
            genre = mautils.between(self.inhtml, "gatunek:", '</tr>')
        genre = mautils.strip_tags(genre)
        self.detailsData['genre'] = genre
                            
    def parseCountry(self):
        print_debug("parseCountry", "started")
        country = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            country = mautils.between(self.inhtml, "kraj:", '</dd>')
            country = mautils.after(country, '<dd>')
        else:  
            country = mautils.between(self.inhtml, 'produkcja:', '</tr>')
        country = mautils.strip_tags(country)
        self.detailsData['country'] = country
    
    def parseWriter(self):
        print_debug("parseWriter", "started")
        writer = mautils.between(self.inhtml, "scenariusz:", '</tr>')
        writer = mautils.after(writer, '</th>')
        writer = writer.replace("(więcej...)", '')
        writer = mautils.strip_tags(writer)
        self.detailsData['writer'] = writer
        
    def parseDirector(self):
        print_debug("parseDirector", "started")
        director = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            if self.inhtml.find("Twórcy:") > -1: 
                director = mautils.between(self.inhtml, "Twórcy:", '</dd>')
            else:  
                director = mautils.between(self.inhtml, "Twórca:", '</dd>')
            director = mautils.after(director, '<dd>')
        else: 
            director = mautils.between(self.inhtml, "reżyseria:", '</tr>')
            print_debug("director to parse", director)
            director = mautils.after(director, '</th>')
            print_debug("director after", director)
        director = director.replace("(więcej...)", '')
        director = mautils.strip_tags(director)
        print_debug("director stripped", director)
        self.detailsData['director'] = director
        
    def parseRating(self):
        print_debug("parseRating", "started")
        rating = mautils.between(self.inhtml, '<div class=rates>', '</div>')
        rating = mautils.between(rating, '<span property="v:average">', '</span>')
        if rating != '':
            rating = rating.replace(' ', '')
            rating = rating.replace(',', '.')
            rate = float(rating.strip())
            print_debug("RATING", str(rate))
            self.detailsData['rating'] = _("User Rating") + ": " + str(rate) + " / 10"            
            ratingstars = int(10*round(rate,1))
            self.detailsData['rating_val'] = ratingstars
        else:
            self.detailsData['rating'] = _("no user rating yet")
            self.detailsData['rating_val'] = 0
            
    def parseFilmId(self):
        print_debug("parseFilmId", "started")
        fid = mautils.between(self.inhtml, '<div id=filmId style="display:none;">', '</div>') 
        if fid and len(fid) > 0:
            self.detailsData['film_id'] = fid
        else:
            self.detailsData['film_id'] = None
        print_info("FILM ID", str(self.detailsData['film_id']))
        
    def parseLogin(self):
        print_debug("parseLogin", "started")
        idx = self.inhtml.find('userName')
        print_debug("Login user idx", str(idx))
        if idx > -1:
            lg = mautils.between(self.inhtml, 'userName">', '</a>')
            self.detailsData['login'] = lg            
        else:
            self.detailsData['login'] = ''
        
    def parseTitle(self):
        print_debug("parseTitle", "started")
        title = mautils.between(self.inhtml, '<title>', '</title>')
        print_debug("title first", title)
        if title.find('(') > -1:
            title = mautils.before(title, '(')
        if title.find('/') > -1:
            title = mautils.before(title, '/')   
        print_debug("title last", title)             
        self.detailsData['title'] = title
        
    def parseOrgTitle(self):
        print_debug("parseOrgTitle", "started")
        title = mautils.between(self.inhtml, '<h2 class=origTitle>', '</h2>')
        print_debug("org title first", title)          
        self.detailsData['org_title'] = title
    
    def parsePromoWidget(self, sessionId):
        print_debug("parsePromoWidget", "started")
        if sessionId is not None:
            idx = self.inhtml.find('<div id="svdRec" style="display:none">')
            if idx > 0:
                txt = mautils.between(self.inhtml, '<div id="svdRec" style="display:none">', '</div>')
                self.detailsData['promo'] = txt
                return
        self.detailsData['promo'] = None
        
    def parseMyVote(self):
        print_debug("parseMyVote", "started")
        idx = self.inhtml.find('gwt-currentVoteLabel')
        self.detailsData['vote'] = ''
        self.detailsData['vote_val'] = 0
        if idx > 0:
            txt = mautils.between(self.inhtml, 'gwt-currentVoteLabel>', '</span>')
            print_debug("My VOTE", txt)
            num = mautils.between(txt, '(',')')
            if len(num) > 0 and num.isdigit():                
                self.detailsData['vote_val'] = int(num)
                self.detailsData['vote'] = txt
    
    def parseRuntime(self):
        print_debug("parseRuntime", "started")
        #if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
        runtime = mautils.between(self.inhtml, 'filmTime="', '";')
        print_debug('Runtime data', str(runtime))
        runtime = runtime.replace(' ', '')        
        if not runtime:
            self.detailsData['runtime'] = ''
            return
        print_debug("Runtime parsed", runtime)
        str_m = ''
        str_h = ''
        if runtime.find('godz.') > -1:
            str_h = mautils.before(runtime, 'godz.')
            runtime = mautils.after(runtime, 'godz.')
        if runtime.find('min.') > -1:
            str_m = mautils.before(runtime, 'min.')
        print_debug("Runtime", "godz: " + str_h + ", min: " + str_m)
        val_runtime = 0
        if str_h:
            val_runtime = 60 * int(float(str_h))
        if str_m:
            val_runtime += int(float(str_m))
        self.detailsData['runtime'] = val_runtime
        
    def parsePoster(self):
        print_debug("parsePoster", "started")   
        self.detailsData['poster_url'] = None
        if self.inhtml.find('<div class=posterLightbox>') > -1:
            posterUrl = mautils.between(self.inhtml, '<div class=posterLightbox>', '</div>')
            posterUrl = mautils.between(posterUrl, 'href="', '" ')
        else:
            posterUrl = ''
        print_debug("Poster URL", posterUrl)  
        if posterUrl != '' and posterUrl.find("jpg") > 0:
            if self.statusComponent:
                self.statusComponent.setText(_("Downloading Movie Poster: %s...") % (posterUrl))
            self.detailsData['poster_url'] = posterUrl
        
    def parseWallpaper(self, link_=None):
        print_debug("parseWallpaper", "started")
        idx = self.inhtml.find('<li id="filmMenu-filmWallpapers" class=" caption">tapety</li>')
        print_debug('Wallpaper idx', str(idx))
        self.detailsData['wallpapers_link'] = None
        if idx < 0:
            self.detailsData['wallpapers_link'] = link_ + '/wallpapers'                
            
    def parseCast(self):
        print_debug("parseCast", "started")  
        
        cast_list = []
        fidx = self.inhtml.find('<div class="castListWrapper cl">')
        if fidx > -1:
            cast = mautils.between(self.inhtml[fidx:], '<ul class=list>', '</ul>')
            
            elements = cast.split('<li')
            no_elems = len(elements)
            print_debug("Cast list elements count", str(no_elems))
            cidx = 0
            if elements != '':
                for element in elements:
                    if element == '':
                        continue
                    element = mautils.after(element, '>')
                    print_debug("Actor", "EL=" + element)
                    imge = mautils.between(element, '<img', '>')
                    print_debug("Actor data", "IMG=" + imge)
                    imge = mautils.between(imge, 'src="', '"')
                    stre = element.replace('<div>', _(" as "))
                    stre = mautils.strip_tags(stre)
                    stre = stre.replace('   ', '')
                    stre = stre.replace('  ', ' ')
                    print_debug("Actor data", "IMG=" + imge + ", DATA=" + stre)  
                    cast_list.append((imge, stre, cidx))                                        
                    cidx += 1                        
        self.detailsData['cast'] = cast_list
    
    def parseDescriptions(self, dhtml):
        print_debug("parseDescriptions", "started")
        descres = ''
        descs = mautils.between(dhtml, '<ul class=descriptionsList', '<script type=')
        elements = descs.split('<li class=')
        if elements != '':
            for element in elements:
                if element == '':
                    continue
                element = mautils.between(element, '<p>', '</p>')
                element = element.replace('  ', ' ')
                element = mautils.strip_tags(element)
                #print_debug("DESC", str(element))
                descres = descres + element + '\n\n'
        return descres
             
class TelemagEngine(object):
    def __init__(self):
        pass
    
    def query(self, ref, typ, dz):       
        ch = self.__getChannel(ref)
        print_debug('channel', ch)
        if not ch:
            return None
        tp = self.__getType(typ)
        fetchurl = 'http://www.telemagazyn.pl/%s/%s/%s,3,1,dz,go,cpr.html' % (ch, tp, dz)
        return getPage(fetchurl).addCallback(self.__fetchOK,(ref,typ,dz)).addErrback(self.__fetchFailed)
    
    def __fetchOK(self, res, tup):
        result = []
        service = tup[0]
        typ = tup[1]
        dzien = tup[2]
        lastnum = 0
        inhtml = mautils.html2utf8(res, 'ISO8859-2')
        idx = inhtml.find('id="lista-programow"')
        if idx > -1:
            inhtml = inhtml[idx:]
            elements = inhtml.split('<td class="lewy')
            for element in elements:
                num = mautils.before(element, '<div class="m1"')                
                if not num or len(num) == 0:
                    continue
                num = num.strip()
                idxm = num.find('<span>')
                if idxm < 0:
                    continue 
                else:
                    numv = mautils.between(num, '<span>', '</span>')
                    if numv.isdigit():
                        num = int(numv)
                    else:
                        continue
                prog =  mautils.between(element, '<td>', '</td>')
                #print_debug('PROG', str(prog))
                ds = None
                hr = mautils.between(prog, '<div class="m1', '<div')
                #print_debug('HR', str(hr))
                ds = mautils.between(prog, '<div class="opisProgramu">', '</div>')
                #print_debug('DS', str(ds))
                if not ds or len(ds) == 0:
                    ds = None
                if not hr and len(hr) == 0:
                    hr = None    
                if hr and ds:         
                    row = []       
                    idxp = hr.find("<p")
                    #print_debug('HRP idx', str(idxp))
                    if idxp > -1:
                        hr = hr[idxp:]
                        hr = mautils.strip_tags(hr)
                        hr = hr.strip('"')
                        hr = hr.strip()
                        tm = time.strptime(dzien + hr,'%Y%m%d%H:%M')
                        sec = time.mktime(tm)
                        if num < lastnum:
                            sec += 86400
                        row.append(sec)
                        print_debug('Godzina', str(hr) + ', sec: ' + str(sec))
                                                
                    idxp = ds.find("<p")
                    #print_debug('DSP idx', str(idxp))
                    if idxp > -1:
                        dsa = ds[idxp:]
                        dsa = mautils.strip_tags(dsa)
                        dsa = dsa.strip()
                        print_debug('Opis', str(dsa))
                        row.append(dsa)
                        
                        dsa = ds[:idxp]
                        dsa = mautils.strip_tags(dsa)
                        dsa = dsa.strip()
                        print_debug('Tytuł', str(dsa))
                        row.append(dsa)
                        
                    # duration value - always None
                    row.append(None)
                    
                    if len(row) == 4:
                        row.append(service)
                        row.append(typ)
                        result.append(row)
                lastnum = num            
        ''' ROW to (begin, opis, tytul, service, typ)'''
        #print_debug('ROW', str(result))            
        return result
    
    def __fetchFailed(self, res):
        pass
    
    def __getChannel(self, ref):              
        x = ref.getServiceName()
        #print_debug('xx', x +', map: '+ str(MAPPING))
        return MAPPING.get(x)
        
    def __getType(self, typ):
        return 'film'
    
class FilmwebTvEngine(object):
    def __init__(self):
        pass
    
    def query(self, ref, typ, dz):
        ch = self.__getChannel(ref)
        print_debug('channel', ch)
        if not ch:
            return None
        tms = time.strptime(dz,"%Y%m%d")
        local = time.localtime(time.time())
        now =time.strptime(time.strftime("%Y%m%d", local),"%Y%m%d")
        #now = time.localtime(time.time())
        tt = time.mktime(tms) - time.mktime(now) 
        d = datetime.timedelta(seconds=tt)
        
        if local[3] < 6:
            tx = time.localtime(time.mktime(tms) - 6 * 60 * 60)
            dz = time.strftime("%Y%m%d", tx)
        
        params ={}
        params['day'] = str(d.days)
        getdata = urllib.urlencode(params)        
        fetchurl = 'http://www.filmweb.pl/guide/%s?%s' % (ch, getdata)
        print_info('URL', str(fetchurl))
        return getPage(fetchurl, method='GET', cookies=COOKIES, headers={'Referer':'http://www.filmweb.pl/guide', 'X-Requested-With':'XMLHttpRequest'}).addCallback(self.__fetchOK,(ref,typ,dz)).addErrback(self.__fetchFailed)
    
    def __fetchOK(self, res, tup):        
        result = []
        service = tup[0]
        typ = tup[1]
        dzien = tup[2]
        
        lastsec = time.mktime(time.strptime(dzien + '05:59','%Y%m%d%H:%M'))
        off = 0
        
        inhtml = mautils.html2utf8(res)
        #inhtml = mautils.between(inhtml, '<div class="channel first">', '<div class="channel">')
        #print_debug('++++++++++++ page', str(inhtml))
        inhtml = mautils.after(inhtml,'brak programów dla wybranych filtrów')
        inhtml = mautils.after(inhtml, '<div class=toScroll>') 
        #print_debug('+++++------- page', str(inhtml))
        #print_debug('------------------')
        
        elements = inhtml.split('<div class="singleProg seance seance_film')
        skip = True
        for element in elements:
            if skip:
                skip = False
                continue
            row = []
            #print_debug('----------- page', str(element))
            if element.find('<span class="hour">') < 0:
                continue
            hr = mautils.between(element, '<span class="hour">', '</span>')
            #print_debug('--', hr)
            hr = mautils.strip_tags(hr)
            hr = hr.strip()
            #print_debug('--', hr)
            tm = time.strptime(dzien + hr,'%Y%m%d%H:%M')
            sec = time.mktime(tm) + off * 86400 
            if sec < lastsec:
                off += 1
                sec += 86400
            lastsec = sec
            row.append(sec)
            print_debug('Godzina', str(hr) + ', sec: ' + str(sec))
            
            duration = None
            hr = mautils.between(element, '<span class="duration">', '</span>')
            hr = hr and hr.strip()
            if hr and len(hr) > 0:                
                print_debug('Czas Trwania', str(hr))
                if hr.isdigit():
                    duration = int(hr)            
            
            hr = mautils.between(element, '<p>', '</p>')
            print_debug('HR', str(hr))
            if hr.find('title=') > -1:
                hrt = mautils.between(hr, 'title="', '"')
                hrt = hrt.strip(')')
                print_debug('Opis', str(hrt))
                row.append(hrt)
                
                hrt = mautils.between(hr, '">', '</a>')
                print_debug('Tytuł', str(hrt))
                row.append(hrt)
            else:
                if hr.find('<br>') > -1:
                    hrt = mautils.after(hr, '<br>')
                    hrt = mautils.strip_tags(hrt)
                    print_debug('Opis', str(hrt))
                    row.append(hrt)
                    
                    hrt = mautils.before(hr, '<br>')
                    hrt = mautils.strip_tags(hrt)
                    print_debug('Tytuł', str(hrt))
                    row.append(hrt)

            row.append(duration)
                                
            if len(row) == 4:
                row.append(service)
                row.append(typ)
                result.append(row)             
        return result
           
    def __fetchFailed(self, res):
        print_info('----> FAILED', str(res))
    
    def __getChannel(self, ref):              
        x = ref.getServiceName()
        #print_debug('xx', x +', map: '+ str(MAPPING))
        return MAPPING2.get(x)
     
    
        