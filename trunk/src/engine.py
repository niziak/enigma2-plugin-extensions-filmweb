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
from __common__ import print_info
import mautils
import urllib
import os

MT_MOVIE = 'film'
MT_SERIE = 'serial'

USER_TOKEN = '_artuser_token'
SESSION_KEY = '_artuser_sessionId'
POSTER_PATH = "/tmp/poster.jpg"

PAGE_URL = 'http://www.filmweb.pl'
SEARCH_QUERY_URL = PAGE_URL + "/search/"
LOGIN_QUERY_URL = 'https://ssl.filmweb.pl/j_login'

COOKIES = {} 

class FilmwebEngine(object):
    def __init__(self, failureHandler=None, statusComponent=None):
        self.inhtml = None
        self.loopx = 0  
        self.resultlist = []       
        self.detailsData = {} 
        self.failureHandler = failureHandler
        self.statusComponent = statusComponent
    
    def login(self, username, password, callback=None, resdata=None):
        print_info("LoginPage", "started")
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
        
    def loadPoster(self, posterUrl, callback):
        if posterUrl:                    
            localfile = POSTER_PATH
            print_info("Downloading poster", posterUrl + " to " + localfile)
            return downloadPage(posterUrl, localfile).addCallback(self.__fetchPosterOK, callback).addErrback(self.__fetchFailed)
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
            print_info("rateEntry - user token", str(userToken) + ', rating: ' + str(rating))
            data = '5|0|6|http://2.fwcdn.pl/gwt/newFilmActivity/|CCD826B60450FCB69E9BD856EE06EAB5|filmweb.gwt.filmactivity.client.UserFilmRemoteService|setRate|J|I|1|2|3|4|2|5|6|' + str(filmId) + '|0|' + str(rating) + '|'
            print_info("POST DATA", data)
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
            print_info("fetch extra OK", str(COOKIES))
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
        print_info("fetchWallpaperOK ...")
        try:
            wallpapers = []
            print_info("fetch wallpaper OK", str(COOKIES))
            if self.statusComponent:
                self.statusComponent.setText(_("Wallpaper loading completed"))
            if txt_ and len(txt_) > 0:
                walls = mautils.after(txt_, '<ul class=filmWallapersList')
                elements = walls.split('filmWallapersItem')
                elcount = len(elements)
                print_info("Wallpapers count", str(elcount))                
                if elcount > 0: # and self.has_key('wallpaper'):
                    furl = None
                    for elem in elements:
                        didx = elem.find('<span class=newLinkLoggedOnly>')
                        print_info("Wallpaper idx", str(didx))
                        if didx > -1:                            
                            furl = mautils.between(elem, '<span class=newLinkLoggedOnly>', '</span>')
                            print_info("URL", furl)
                            wallpapers.append(furl)
            if callback:
                callback(wallpapers)
        except:
            import traceback
            traceback.print_exc()
                    
    def __fetchPosterOK(self, data, callback):
        try:
            print_info("Fetch Poster OK", str(COOKIES)) 
            #if not self.has_key('status_bar'):
            #    return
            if self.statusComponent:
                self.statusComponent.setText(_("Poster downloading finished"))
            rpath = os.path.realpath(POSTER_PATH)
            print_info("Poster local real path", rpath)
            if callback and os.path.exists(rpath):
                callback(rpath)
        except:
            import traceback
            traceback.print_exc()
                
    def __fetchLoginRes(self, res_, callback, data):
        try:
            print_info("RESULT COOKIE", str(COOKIES))
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
            callback(self.detailsData)
            
    def __fetchEntries(self, fetchurl, type, callback, tryOther=True, data=None):
        self.resultlist = []
        return getPage(fetchurl, cookies=COOKIES).addCallback(self.__fetchOK, callback, tryOther, fetchurl, type, data).addErrback(self.__fetchFailed) 
        
    def __fetchOK(self, txt_, callback, tryOther, fetchurl, type, data):        
        print_info("Fetch OK", str(COOKIES))                
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
        print_info("__parseEntries", "started")   
        if type == MT_MOVIE:
            ttx = 'Filmy ('
        else:
            ttx = 'Seriale ('
        fidx = self.inhtml.find(ttx)
        print_info("search idx", str(fidx))  
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
                    basic_data = element                
                    #element = mautils.convert_entities(element)
                    element = mautils.strip_tags(element)
                    if rating:
                        element += '\n' + rating.strip()
                    if cast:
                        element += '\n' + cast.strip()
                    print_info("The movie serach title", element)
                    #self.titles.append(element)
                    self.resultlist.append((element, PAGE_URL + link, basic_data, title, rating, year, country))
        
    def parsePlot(self):
        print_info("parsePlot", "started")
        plot = mautils.between(self.inhtml, '<span class=filmDescrBg property="v:summary">', '</span>')
        plot = plot.replace('  ', ' ')
        plot = mautils.strip_tags(plot)
        print_info("PLOT", plot)
        self.detailsData['plot'] = plot        
        
    def parseYear(self):
        print_info("parseYear", "started")
        year = mautils.between(self.inhtml, '<span id=filmYear class=filmYear>', '</span>')
        year = mautils.strip_tags(year)
        self.detailsData['year'] = str(year)
        
    def parseGenere(self):
        print_info("parseGenere", "started")
        genre = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            genre = mautils.between(self.inhtml, "gatunek:", '</strong>')
        else:  
            genre = mautils.between(self.inhtml, "gatunek:", '</tr>')
        genre = mautils.strip_tags(genre)
        self.detailsData['genre'] = genre
                            
    def parseCountry(self):
        print_info("parseCountry", "started")
        country = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
            country = mautils.between(self.inhtml, "kraj:", '</dd>')
            country = mautils.after(country, '<dd>')
        else:  
            country = mautils.between(self.inhtml, 'produkcja:', '</tr>')
        country = mautils.strip_tags(country)
        self.detailsData['country'] = country
    
    def parseWriter(self):
        print_info("parseWriter", "started")
        writer = mautils.between(self.inhtml, "scenariusz:", '</tr>')
        writer = mautils.after(writer, '</th>')
        writer = writer.replace("(więcej...)", '')
        writer = mautils.strip_tags(writer)
        self.detailsData['writer'] = writer
        
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
        self.detailsData['director'] = director
        
    def parseRating(self):
        print_info("parseRating", "started")
        rating = mautils.between(self.inhtml, '<div class=rates>', '</div>')
        rating = mautils.between(rating, '<span property="v:average">', '</span>')
        if rating != '':
            rating = rating.replace(' ', '')
            rating = rating.replace(',', '.')
            rate = float(rating.strip())
            print_info("RATING", str(rate))
            self.detailsData['rating'] = _("User Rating") + ": " + str(rate) + " / 10"            
            ratingstars = int(10*round(rate,1))
            self.detailsData['rating_val'] = ratingstars
        else:
            self.detailsData['rating'] = _("no user rating yet")
            self.detailsData['rating_val'] = 0
            
    def parseFilmId(self):
        print_info("parseFilmId", "started")
        fid = mautils.between(self.inhtml, '<div id=filmId style="display:none;">', '</div>') 
        if fid and len(fid) > 0:
            self.detailsData['film_id'] = fid
        else:
            self.detailsData['film_id'] = None
        print_info("FILM ID", str(self.detailsData['film_id']))
        
    def parseLogin(self):
        print_info("parseLogin", "started")
        idx = self.inhtml.find('userName')
        print_info("Login user idx", str(idx))
        if idx > -1:
            lg = mautils.between(self.inhtml, 'userName">', '</a>')
            self.detailsData['login'] = lg            
        else:
            self.detailsData['login'] = ''
        
    def parseTitle(self):
        print_info("parseTitle", "started")
        title = mautils.between(self.inhtml, '<title>', '</title>')
        print_info("title first", title)
        if title.find('(') > -1:
            title = mautils.before(title, '(')
        if title.find('/') > -1:
            title = mautils.before(title, '/')   
        print_info("title last", title)             
        self.detailsData['title'] = title
        
    def parseOrgTitle(self):
        print_info("parseOrgTitle", "started")
        title = mautils.between(self.inhtml, '<h2 class=origTitle>', '</h2>')
        print_info("org title first", title)          
        self.detailsData['org_title'] = title
    
    def parsePromoWidget(self, sessionId):
        print_info("parsePromoWidget", "started")
        if sessionId is not None:
            idx = self.inhtml.find('<div id="svdRec" style="display:none">')
            if idx > 0:
                txt = mautils.between(self.inhtml, '<div id="svdRec" style="display:none">', '</div>')
                self.detailsData['promo'] = txt
                return
        self.detailsData['promo'] = None
        
    def parseMyVote(self):
        print_info("parseMyVote", "started")
        idx = self.inhtml.find('gwt-currentVoteLabel')
        self.detailsData['vote'] = ''
        self.detailsData['vote_val'] = 0
        if idx > 0:
            txt = mautils.between(self.inhtml, 'gwt-currentVoteLabel>', '</span>')
            print_info("My VOTE", txt)
            num = mautils.between(txt, '(',')')
            if len(num) > 0 and num.isdigit():                
                self.detailsData['vote_val'] = int(num)
                self.detailsData['vote'] = txt
    
    def parseRuntime(self):
        print_info("parseRuntime", "started")
        #if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1: 
        runtime = mautils.between(self.inhtml, 'filmTime="', '";')
        print_info('Runtime data', str(runtime))
        runtime = runtime.replace(' ', '')        
        if not runtime:
            self.detailsData['runtime'] = ''
            return
        print_info("Runtime parsed", runtime)
        str_m = ''
        str_h = ''
        if runtime.find('godz.') > -1:
            str_h = mautils.before(runtime, 'godz.')
            runtime = mautils.after(runtime, 'godz.')
        if runtime.find('min.') > -1:
            str_m = mautils.before(runtime, 'min.')
        print_info("Runtime", "godz: " + str_h + ", min: " + str_m)
        val_runtime = 0
        if str_h:
            val_runtime = 60 * int(float(str_h))
        if str_m:
            val_runtime += int(float(str_m))
        self.detailsData['runtime'] = val_runtime
        
    def parsePoster(self):
        print_info("parsePoster", "started")   
        self.detailsData['poster_url'] = None
        if self.inhtml.find('<div class=posterLightbox>') > -1:
            posterUrl = mautils.between(self.inhtml, '<div class=posterLightbox>', '</div>')
            posterUrl = mautils.between(posterUrl, 'href="', '" ')
        else:
            posterUrl = ''
        print_info("Poster URL", posterUrl)  
        if posterUrl != '' and posterUrl.find("jpg") > 0:
            if self.statusComponent:
                self.statusComponent.setText(_("Downloading Movie Poster: %s...") % (posterUrl))
            self.detailsData['poster_url'] = posterUrl
        
    def parseWallpaper(self, link_=None):
        print_info("parseWallpaper", "started")
        idx = self.inhtml.find('<li id="filmMenu-filmWallpapers" class=" caption">tapety</li>')
        print_info('Wallpaper idx', str(idx))
        self.detailsData['wallpapers_link'] = None
        if idx < 0:
            self.detailsData['wallpapers_link'] = link_ + '/wallpapers'                
            
    def parseCast(self):
        print_info("parseCast", "started")  
        
        cast_list = []
        fidx = self.inhtml.find('<div class="castListWrapper cl">')
        if fidx > -1:
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
                    cast_list.append((imge, stre, cidx))                                        
                    cidx += 1                        
        self.detailsData['cast'] = cast_list
    
    def parseDescriptions(self, dhtml):
        print_info("parseDescriptions", "started")
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
                #print_info("DESC", str(element))
                descres = descres + element + '\n\n'
        return descres
             
        
        