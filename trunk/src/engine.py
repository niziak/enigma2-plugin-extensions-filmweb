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

from twisted.web.client import downloadPage, getPage, defer
from __common__ import _
from logger import print_info, print_debug
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
POSTER_IMDB_PATH = "/tmp/poster_imdb.jpg"

SEARCH_IMDB_URL = 'http://www.imdb.com/search/title?'
PAGE_URL = 'http://www.filmweb.pl'
SEARCH_QUERY_URL = PAGE_URL + "/search/"
LOGIN_QUERY_URL = 'https://ssl.filmweb.pl/j_login'

COOKIES = {}
COOKIES_IMDB = {}
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

class ImdbEngine(object):
    def __init__(self, failureHandler=None, statusComponent=None):
        self.inhtml = None
        self.resultlist = []
        self.detailsData = {}
        self.failureHandler = failureHandler
        self.statusComponent = statusComponent

    def login(self, username, password, callback=None, resdata=None):
        print_debug("LoginPage", "started")
        return None

    def query(self, typ, title, year=None, tryOther=False, callback=None, data=None):
        if typ == MT_MOVIE:
            typen = 'feature,tv_movie,mini_series,documentary'
        else:
            typen = 'tv_series'
        tit = urllib.quote(title.encode('utf8'))
        fetchurl = SEARCH_IMDB_URL + 'title=' + tit + '&title_type=' + typen
        if year:
            fetchurl += '&release_date=' + year + '-01-01,' + year + '-12-31'
        print_info("IMDB Query", fetchurl)
        return self.__fetchEntries(fetchurl, type, callback, tryOther, data)

    def queryDetails(self, link, callback=None, sessionId=None):
        headers = {"Accept":"text/html", "Accept-Charset":"utf-8", "Accept-Encoding":"deflate",
           "Accept-Language":"pl-PL,pl;q=0.8,en-US;q=0.6,en;q=0.4", "Connection":"keep-alive",
           "Host":"www.imdb.com",
           "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0.1229.94 Safari/537.4"}
        return getPage(link, cookies=COOKIES_IMDB, headers=headers).addCallback(self.__fetchDetailsOK, link, callback, sessionId).addErrback(self.__fetchFailed)

    def __fetchDetailsOK(self, txt_, link, callback, sessionId):
        print_info("fetch details OK", str(COOKIES_IMDB))
        if self.statusComponent:
            self.statusComponent.setText(_("Movie details loading completed"))
        self.inhtml = mautils.html2utf8(txt_)
        self.detailsData = {}
        if self.inhtml:
            try:
                self.detailsData['login'] = ''
                self.detailsData['plot'] = ''
                self.detailsData['year'] = ''
                self.detailsData['genre'] = ''
                self.detailsData['country'] = ''
                self.detailsData['director'] = ''
                self.detailsData['writer'] = ''
                self.detailsData['promo'] = None
                self.detailsData['runtime'] = ''
                self.detailsData['wallpapers_link'] = None

                self.parseFilmId()
                self.parseTitle()
                self.parseOrgTitle()
                self.parseRating()
                self.parsePoster()
                self.parsePlot()
                self.parseGenere()
                # self.parseDirector()
                # self.parseWriter()
                # self.parseCountry()
                self.parseYear()
                self.parseRuntime()
                self.parseMyVote()
                # self.parsePromoWidget(sessionId)
                # self.parseWallpaper(link)
                self.parseCast()
            except:
                import traceback
                traceback.print_exc()
        else:
            self.detailsData = None
        if (callback):
            return callback(self.detailsData)
        return self.detailsData

    def parseGenere(self):
        print_debug("parseGenere", "started")
        genre = ''
        elem = mautils.between(self.inhtml, '<div class="infobar">', '</div>')
        elements = elem.split('<a href="/genre')
        no_elems = len(elements)
        print_debug("Genre list elements count", str(no_elems))
        if elements != '':
            for element in elements:
                if element.find('tt_ov_inf') > 0:
                    ex = mautils.between(element, '" >', '</a>')
                    genre = genre + ' ' + ex
        print_debug("GENRE: ", str(genre))
        genre = mautils.strip_tags(genre)
        self.detailsData['genre'] = genre

    def parseRuntime(self):
        print_debug("parseRuntime", "started")
        runtime = mautils.between(self.inhtml, '<time itemprop="duration"', '</time>')
        runtime = mautils.after(runtime, '>')
        runtime = mautils.strip_tags(runtime).strip()
        print_debug('Runtime data: ', str(runtime))
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
        if runtime.find('min') > -1:
            str_m = mautils.before(runtime, 'min')
        print_debug("Runtime", "godz: " + str_h + ", min: " + str_m)
        val_runtime = 0
        if str_h:
            val_runtime = 60 * int(float(str_h))
        if str_m:
            val_runtime += int(float(str_m))
        self.detailsData['runtime'] = val_runtime

    def parseFilmId(self):
        print_debug("parseFilmId", "started")
        fid = mautils.between(self.inhtml, '<link rel="canonical" href="http://www.imdb.com/title/', '/" />')
        if fid and len(fid) > 0:
            self.detailsData['film_id'] = fid
        else:
            self.detailsData['film_id'] = None
        print_info("FILM ID", str(self.detailsData['film_id']))

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
        title = mautils.between(self.inhtml, '<span class="title-extra">', '<i>(original title)')
        print_debug("org title first: ", title)
        title = title.strip();
        self.detailsData['org_title'] = title

    def parseYear(self):
        print_debug("parseYear", "started")
        year = mautils.between(self.inhtml, 'tt_ov_inf" >', '</a>')
        year = mautils.strip_tags(year)
        self.detailsData['year'] = str(year)

    def parsePoster(self):
        print_debug("parsePoster", "started")
        self.detailsData['poster_url'] = None
        if self.inhtml.find('<a href="/media/') > -1:
            posterUrl = mautils.between(self.inhtml, '<a href="/media/', 'itemprop="image" />')
            posterUrl = mautils.between(posterUrl, 'src="', '"')
        else:
            posterUrl = ''
        print_debug("Poster URL", posterUrl)
        if posterUrl != '' and posterUrl.find("jpg") > 0:
            if self.statusComponent:
                self.statusComponent.setText(_("Downloading Movie Poster: %s...") % (posterUrl))
            self.detailsData['poster_url'] = posterUrl

    def parseCast(self):
        print_debug("parseCast", "started")
        cast_list = []
        fidx = self.inhtml.find('<table class="cast_list">')
        if fidx > -1:
            cast = mautils.between(self.inhtml, '<table class="cast_list">', '</table>')
            elements = cast.split('<tr class="')
            no_elems = len(elements)
            print_debug("Cast list elements count", str(no_elems))
            cidx = 0
            if elements != '':
                for element in elements:
                    if element == '' or element.find('<td class="primary_photo">') < 0:
                        continue
                    cre = self.__loadCastData(element)
                    cast_list.append((cre[0], cre[1], cidx))
                    cidx += 1
        self.detailsData['cast'] = cast_list

    def parseMyVote(self):
        print_debug("parseMyVote", "started")
        self.detailsData['vote'] = ''
        self.detailsData['vote_val'] = 0

    def parsePlot(self):
        print_debug("parsePlot", "started")
        plot = mautils.between(self.inhtml, '<div class="inline canwrap" itemprop="description">', '</div>')
        plot = plot.replace('  ', ' ')
        plot = mautils.strip_tags(plot).strip()
        print_debug("PLOT", plot)
        self.detailsData['plot'] = plot

    def parseRating(self):
        print_debug("parseRating", "started")
        rating = mautils.between(self.inhtml, '<div class="titlePageSprite star-box-giga-star">', '</div>')
        if rating != '':
            rating = rating.replace(' ', '')
            rating = rating.replace(',', '.')
            rate = float(rating.strip())
            print_debug("RATING", str(rate))
            self.detailsData['rating'] = _("User Rating") + ": " + str(rate) + " / 10"
            ratingstars = int(10 * round(rate, 1))
            self.detailsData['rating_val'] = ratingstars
        else:
            self.detailsData['rating'] = _("no user rating yet")
            self.detailsData['rating_val'] = 0

    def loadPoster(self, posterUrl, callback=None, localfile=POSTER_IMDB_PATH):
        if posterUrl:
            print_info("Downloading poster", posterUrl + " to " + localfile)
            return downloadPage(posterUrl, localfile).addCallback(self.__fetchPosterOK, localfile, callback).addErrback(self.__fetchFailed)
        return None

    def loadWallpaper(self, furl, localfile, callback):
        if not furl or not localfile:
            return None
        print_info("Loading wallpaper", 'URL: ' + furl + ', Local File:' + localfile)
        # return downloadPage(furl, localfile).addCallback(callback, localfile).addErrback(self.__fetchFailed)
        return None

    def loadDescriptions(self, furl, callback):
        if not furl:
            return None
        print_info("LOAD DESCS - link", furl + "/descs")
        # return getPage(furl + "/descs", cookies=COOKIES).addCallback(self.__fetchExtraOK, callback).addErrback(self.__fetchFailed)
        return None

    def loadCast(self, furl, callback):
        if not furl:
            return None
        print_info("LOAD CAST - link", furl + "/cast")
        # return getPage(furl + "/cast", cookies=COOKIES).addCallback(self.__fetchCastOK, callback).addErrback(self.__fetchFailed)
        return None


    def __loadCastData(self, element):
        element = mautils.after(element, '<td class="primary_photo">')
        imge = mautils.between(element, 'loadlate="', '"')
        print_debug("Actor data", "IMG=" + imge)

        element = mautils.between(element, "itemprop='name'>", '</tr>')
        stre = mautils.before(element, '</a>');
        stre = stre.strip()
        if element.find('<td class="character">') > -1:
            element = mautils.between(element, '<td class="character">', '</td>')
            element = mautils.strip_tags(element)
            element = element.strip()
            if len(element) > 0:
                stre = stre + ' jako ' + element

        print_debug("Actor data", "IMG=" + imge + ", DATA=" + stre)
        return (imge, stre)

    def __fetchPosterOK(self, data, localfile, callback=None):
        try:
            print_debug("Fetch Poster OK", str(COOKIES_IMDB))
            # if not self.has_key('status_bar'):
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

    def __fetchEntries(self, fetchurl, typ, callback, tryOther=True, data=None):
        self.resultlist = []
        headers = {"Accept":"text/html", "Accept-Charset":"utf-8", "Accept-Encoding":"deflate",
                   "Accept-Language":"pl-PL,pl;q=0.8,en-US;q=0.6,en;q=0.4", "Connection":"keep-alive",
                   "Host":"www.imdb.com",
                   "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0.1229.94 Safari/537.4"}
        df = getPage(fetchurl, cookies=COOKIES_IMDB, headers=headers).addCallback(self.__fetchOK, callback, tryOther, fetchurl, typ, data).addErrback(self.__fetchFailed)
        print_debug('IMDB query deffered: ', str(df))
        return df

    def __fetchOK(self, txt_, callback, tryOther, fetchurl, typ, data):
        print_debug("Fetch OK", str(COOKIES_IMDB))
        if self.statusComponent:
            self.statusComponent.setText(_("IMDB Download completed"))
        self.inhtml = mautils.html2utf8(txt_)
        if self.inhtml:
            self.__parseEntries(typ)
        if len(self.resultlist) == 0:
            if tryOther:
                if typ == MT_SERIE:
                    typ = MT_MOVIE
                else:
                    typ = MT_SERIE
                return self.__fetchEntries(fetchurl, type, callback, False, data)
        if callback:
            return callback(self.resultlist, type, data)
        return None

    def __fetchFailed(self, txt_):
        print_info("Fetch failed", str(txt_))
        if self.failureHandler:
            self.failureHandler(txt_)

    def __parseEntries(self, typ):
        print_debug("__parseEntries", "started")
        fidx = self.inhtml.find('<table class="results">')
        print_debug("search idx", str(fidx))
        if fidx > -1:
            self.inhtml = mautils.after(self.inhtml, '<table class="results">')
        else:
            self.inhtml = None

        if self.inhtml is None:
            pass
        else:
            # print_debug("---", str(self.inhtml))
            elements = self.inhtml.split('<tr class="')
            number_results = len(elements)
            print_info("Serach results count", str(number_results))
            if elements == '':
                number_results = 0
            else:
                for element in elements:
                    if element == '':
                        continue
                    tt = mautils.after(element, '<td class="title">')
                    link = mautils.between(tt, '<a href="/title/', '">')
                    if (link != ''):
                        print_debug("The movie link", link)
                        title = mautils.after(tt, '<a href="/title/')
                        title = mautils.between(title, '">', '</a>')
                        print_debug("The movie title", title)
                        year = mautils.between(tt, '<span class="year_type">', '</span>')
                        print_debug("The movie year", year)
                        rating = mautils.after(tt, 'data-ga-identifier="advsearch"')
                        rating = mautils.between(rating, 'title="', '- click stars to rate"')
                        cast = mautils.between(tt, 'With:', '</span>')
                        if (cast != ''):
                            cast = mautils.strip_tags(cast)

                        element = title.strip()
                        if year:
                            element += ' ' + year.strip()
                        # if country:
                        #    element += ' - ' + country.strip()
                        basic_data = element
                        element = mautils.strip_tags(element)
                        if rating:
                            element += '\n' + rating.strip()
                        if cast:
                            element += '\n' + cast.strip()
                        print_info("The movie serach title", element)
                        if (rating and rating.find('Users rated this') > -1):
                            rt = mautils.between(rating, 'Users rated this ', '/10')
                        else:
                            rt = '0.0'

                        # (caption, url, basic_caption, title, rating, year, country)
                        self.resultlist.append((element, 'http://www.imdb.com/title/' + link, basic_data, title, rt, year, ''))



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

    def query(self, typ, title, year=None, tryOther=False, callback=None, data=None):
        fetchurl = SEARCH_QUERY_URL + str(typ) + "?q=" + mautils.quote(title.encode('utf8'))
        if year:
            fetchurl += '&startYear=' + year + '&endYear=' + year
        print_info("Filmweb Query", fetchurl)
        return self.__fetchEntries(fetchurl, typ, callback, tryOther, data)

    def searchWallpapers(self, link_, callback):
        if link_:
            return getPage(link_, cookies=COOKIES).addCallback(self.__fetchWallpaperOK, callback).addErrback(self.__fetchFailed)
        return None

    def loadPoster(self, posterUrl, callback=None, localfile=POSTER_PATH):
        if posterUrl:
            print_info("Downloading poster", posterUrl + " to " + localfile)
            return downloadPage(posterUrl, localfile).addCallback(self.__fetchPosterOK, localfile, callback).addErrback(self.__fetchFailed)
        return None

    def loadWallpaper(self, furl, localfile, callback):
        if not furl or not localfile:
            return None
        print_info("Loading wallpaper", 'URL: ' + furl + ', Local File:' + localfile)
        return downloadPage(furl, localfile).addCallback(callback, localfile).addErrback(self.__fetchFailed)

    def loadDescriptions(self, furl, callback):
        if not furl:
            return None
        print_info("LOAD DESCS - link", furl + "/descs")
        return getPage(furl + "/descs", cookies=COOKIES).addCallback(self.__fetchExtraOK, callback).addErrback(self.__fetchFailed)

    def loadCast(self, furl, callback):
        if not furl:
            return None
        print_info("LOAD CAST - link", furl + "/cast")
        return getPage(furl + "/cast", cookies=COOKIES).addCallback(self.__fetchCastOK, callback).addErrback(self.__fetchFailed)

    def applyRating(self, rating, filmId, userToken, callback):
        if rating > -2 and filmId:
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

    def __fetchCastOK(self, txt_, callback):
        try:
            print_debug("fetch cast OK", str(COOKIES))
            if self.statusComponent:
                self.statusComponent.setText(_("Cast loading completed"))
            dhtml = mautils.html2utf8(txt_)
            data = None
            if dhtml:
                data = self.parseCastDetails(dhtml)
            if callback:
                callback(data)
        except:
            import traceback
            traceback.print_exc()

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
                walls = mautils.after(txt_, '<h2 class=inline>tapety</h2>')
                walls = mautils.after(txt_, '<ul class="')
                elements = walls.split('<li>')
                elcount = len(elements)
                print_debug("Wallpapers count", str(elcount))
                if elcount > 0:  # and self.has_key('wallpaper'):
                    furl = None
                    for elem in elements:
                        didx = elem.find('<span class=loggedOnlyLink>')
                        print_debug("Wallpaper idx", str(didx))
                        if didx > -1:
                            furl = mautils.between(elem, '<span class=loggedOnlyLink>', '</span>')
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
            # if not self.has_key('status_bar'):
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
                self.inhtml = mautils.between(self.inhtml[fidx:], 'Wyniki:', '</form>')
                print_debug("Serach data: ", str(self.inhtml))
            else:
                self.inhtml = None
        else:
            self.inhtml = None

        if self.inhtml is None:
            pass
        else:
            elements = self.inhtml.split('<div class=hitDesc>')
            number_results = len(elements)
            print_info("Serach results count", str(number_results))
            if elements == '':
                number_results = 0
            else:
                for element in elements:
                    if element == '':
                        continue
                    if (element.find('class="hdr hdr-medium" href="') < 0):
                        continue
                    element = mautils.after(element, 'class="hdr hdr-medium" href="')
                    link = mautils.before(element, '"')
                    print_debug("The movie link", link)
                    cast = mautils.after(element, '<div class="text">')
                    cast = mautils.between(cast, '"filmInfo inline">', '</dl>')
                    cast = cast.replace('</ul></dd>', '   ')
                    cast = cast.replace('</li><li>', ', ')
                    cast = mautils.strip_tags(cast)
                    cast = cast.replace('\t', '')
                    cast = cast.replace('\n', '')
                    print_debug("The movie cast", cast)
                    rating = mautils.after(element, '<i class=icon-small-voteOn>')
                    rating = mautils.between(rating, '<strong>', '<div class="box box-half">')
                    rating = mautils.strip_tags(rating)
                    rating = rating.replace('\t', '')
                    rating = rating.replace('\n', '')
                    print_debug("The movie rating", rating)
                    # self.links.append('http://www.filmweb.pl' + link)
                    title = mautils.between(element, '">', '</a>')
                    title = mautils.before(title, ' (')
                    title = title.replace('\t', '')
                    title = mautils.strip_tags(title)
                    print_debug("The movie title", title)
                    # element = mautils.after(element, 'class=searchResultDetails')
                    year = mautils.between(element, ' (', ') </a>')
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
                    # element = mautils.convert_entities(element)
                    element = mautils.strip_tags(element)
                    if rating:
                        element += '\n' + rating.strip()
                    if cast:
                        element += '\n' + cast.strip()
                    print_info("The movie serach title", element)
                    # self.titles.append(element)
                    if rating:
                        rt = mautils.before(rating, '/')
                        rt = rt.strip()
                    else:
                        rt = '0.0'
                    # (caption, url, basic_caption, title, rating, year, country)
                    self.resultlist.append((element, PAGE_URL + link, basic_data, title, rt, year, country))

    def parsePlot(self):
        print_debug("parsePlot", "started")
        plot = mautils.between(self.inhtml, 'property="v:summary">', '</p>')
        plot = plot.replace('  ', ' ')
        plot = mautils.strip_tags(plot)
        print_debug("PLOT", plot)
        self.detailsData['plot'] = plot

    def parseYear(self):
        print_debug("parseYear", "started")
        year = mautils.between(self.inhtml, '<span id=filmYear class=halfSize>', '</span>')
        year = mautils.strip_tags(year)
        self.detailsData['year'] = str(year)

    def parseGenere(self):
        print_debug("parseGenere", "started")
        genre = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1:
            genre = mautils.between(self.inhtml, "gatunek:", '<script type=')
        else:
            genre = mautils.between(self.inhtml, "gatunek:", '</tr>')
            genre = mautils.between(genre, '<ul class="inline sep-comma"><li>', '</ul>')
        genre = genre.replace('<li>', ', ')
        print_debug("GENRE: ", str(genre))
        genre = mautils.strip_tags(genre)
        self.detailsData['genre'] = genre

    def parseCountry(self):
        print_debug("parseCountry", "started")
        country = ''
        if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1:
            country = mautils.between(self.inhtml, "kraj:", '</dd>')
            print_debug("SERIAL COUNTRY: ", '--' + str(country) + '--')
            if not country or len(country) == 0:
                country = mautils.between(self.inhtml, "kraje:", '</dd>')
                print_debug("SERIAL COUNTRY-2: ", country)
            country = mautils.after(country, '<dd>')
        else:
            country = mautils.between(self.inhtml, 'produkcja:', '</tr>')
            country = mautils.between(country, '<ul class="inline sep-comma"><li>', '</ul>')
        country = country.replace('<li>', ', ')
        print_debug("COUNTRY: ", str(country))
        country = mautils.strip_tags(country)
        self.detailsData['country'] = country

    def parseWriter(self):
        print_debug("parseWriter", "started")
        writer = mautils.between(self.inhtml, "scenariusz:", '</tr>')
        writer = mautils.between(writer, '<ul class="inline sep-comma"><li>', '</ul>')
        writer = writer.replace('<li>', ', ')
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
            director = mautils.between(director, '<ul class="inline sep-comma"><li>', '</ul>')
            director = director.replace('<li>', ', ')
            # director = mautils.after(director, '</th>')
            print_debug("director after", director)
        director = director.replace("(więcej...)", '')
        director = mautils.strip_tags(director)
        print_debug("director stripped", director)
        self.detailsData['director'] = director

    def parseRating(self):
        print_debug("parseRating", "started")
        rating = mautils.between(self.inhtml, '<span class=filmRate>', '</span>')
        rating = mautils.between(rating, 'property="v:average">', '</')
        if rating != '':
            rating = rating.replace(' ', '')
            rating = rating.replace(',', '.')
            rate = float(rating.strip())
            print_debug("RATING", str(rate))
            self.detailsData['rating'] = _("User Rating") + ": " + str(rate) + " / 10"
            ratingstars = int(10 * round(rate, 1))
            self.detailsData['rating_val'] = ratingstars
        else:
            self.detailsData['rating'] = _("no user rating yet")
            self.detailsData['rating_val'] = 0

    def parseFilmId(self):
        print_debug("parseFilmId", "started")
        fid = mautils.between(self.inhtml, '<div id=filmId>', '</div>')
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
        title = mautils.between(self.inhtml, '<h2 class="text-large caption">', '</h2>')
        print_debug("org title first", title)
        self.detailsData['org_title'] = title

    def parsePromoWidget(self, sessionId):
        print_debug("parsePromoWidget", "started")
        if sessionId is not None:
            idx = self.inhtml.find('<div id="svdRec" style="display: none;">')
            if idx > 0:
                txt = mautils.between(self.inhtml, '<div id="svdRec" style="display: none;">', '</div>')
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
            num = mautils.between(txt, '(', ')')
            if len(num) > 0 and num.isdigit():
                self.detailsData['vote_val'] = int(num)
                self.detailsData['vote'] = txt

    def parseRuntime(self):
        print_debug("parseRuntime", "started")
        # if mautils.between(self.inhtml, '<title>', '</title>').find('Serial TV') > -1:
        runtime = mautils.between(self.inhtml, '<div class=filmTime>', '</div>')
        runtime = mautils.strip_tags(runtime)
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
        idx = self.inhtml.find('<li id=filmMenu-filmWallpapers class=" caption">tapety</li>')
        print_debug('Wallpaper idx', str(idx))
        self.detailsData['wallpapers_link'] = None
        if idx < 0:
            self.detailsData['wallpapers_link'] = link_ + '/wallpapers'

    def parseCast(self):
        print_debug("parseCast", "started")

        cast_list = []
        fidx = self.inhtml.find('<ul class="vertical-list filmCast">')
        if fidx > -1:
            cast = mautils.between(self.inhtml, '<ul class="vertical-list filmCast">', '</ul>')

            elements = cast.split('<li')
            no_elems = len(elements)
            print_debug("Cast list elements count", str(no_elems))
            cidx = 0
            if elements != '':
                for element in elements:
                    if element == '':
                        continue
                    cre = self.__loadCastData(element)
                    cast_list.append((cre[0], cre[1], cidx))
                    cidx += 1
        self.detailsData['cast'] = cast_list

    def __loadCastData(self, element):
        element = mautils.after(element, '>')
        element = mautils.before(element, '<div class="rolePhoto')
        print_debug("Actor", "EL=" + element)
        imge = mautils.between(element, '<img', '>')
        print_debug("Actor data", "IMG=" + imge)
        imge = mautils.between(imge, 'src="', '"')
        stre = element.replace('<div>', _(" as "))
        stre = mautils.strip_tags(stre)
        stre = stre.replace('   ', '')
        stre = stre.replace('  ', ' ')
        print_debug("Actor data", "IMG=" + imge + ", DATA=" + stre)
        return (imge, stre)

    def parseCastDetails(self, dhtml):
        print_debug("parseCastDetails", "started")
        descs = mautils.between(dhtml, '<dt id=role-actors>', '</dd>')
        elements = descs.split('<li')
        cidx = 0
        cast_list = []
        if elements != '':
            for element in elements:
                if element == '':
                    continue
                if cidx > 0:
                    cre = self.__loadCastData(element)
                    cast_list.append((cre[0], cre[1], cidx))
                cidx += 1
        # self.detailsData['cast'] = cast_list
        return cast_list

    def parseDescriptions(self, dhtml):
        print_debug("parseDescriptions", "started")
        descres = ''
        descs = mautils.between(dhtml, '<ul class="sep-hr descriptionsList"', '<script type=')
        elements = descs.split('hoverOpacity"')
        if elements != '':
            for element in elements:
                if element == '':
                    continue
                element = mautils.between(element, '<p class=text>', '</p>')
                element = element.replace('  ', ' ')
                element = mautils.strip_tags(element)
                # print_debug("DESC", str(element))
                descres = descres + element + '\n\n'
        return descres

class ImdbRateEngine(object):
    def __init__(self):
        pass

    def query(self, title, year, typ):
        if typ == MT_MOVIE:
            typen = 'feature,tv_movie,mini_series,documentary'
        else:
            typen = 'tv_series'
        fetchurl = SEARCH_IMDB_URL + 'title=' + urllib.quote(title.encode('utf8')) + '&title_type=' + typen
        if year:
            fetchurl += '&release_date=' + year + '-01-01,' + year + '-12-31'
        print_info("IMDB Query", fetchurl)
        headers = {"Accept":"text/html", "Accept-Charset":"utf-8", "Accept-Encoding":"deflate",
                   "Accept-Language":"pl-PL,pl;q=0.8,en-US;q=0.6,en;q=0.4", "Connection":"keep-alive",
                   "Host":"www.imdb.com",
                   "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0.1229.94 Safari/537.4"}
        df = getPage(fetchurl, cookies=COOKIES_IMDB, headers=headers).addCallback(self.__fetchImdbOK).addErrback(self.__fetchFailed)
        print_debug('IMDB query deffered: ', str(df))
        return df

    def __fetchImdbOK(self, res):
        # print_debug('Fetch IMDB OK: ', str(res))
        # inhtml = mautils.html2utf8(res, 'utf-8')
        inhtml = mautils.between(res, '<table class="results">', '<div class="leftright">')
        # print_debug('Fetch IMDB html: ', str(inhtml))

        elements = inhtml.split('<td class="number">')
        num = len(elements)
        print_debug('IMDB Number of elements: ', str(num))
        for element in elements:
            # print_debug('ELEMENT: ', str(element))
            ttle = mautils.between(element, '<a href="/title/', '/" title="')
            idx = element.find('<span class="rating-rating"><span class="value">')
            if idx > -1:
                rating = mautils.between(element, '<span class="rating-rating"><span class="value">', '</span>')
                print_debug('Rating: ', str(rating))
                return (rating, ttle)
        return None

    def __fetchFailed(self, res):
        print_debug('Fetch IMDB ERROR: ', str(res))

class TelemagEngine(object):
    def __init__(self):
        pass

    def query(self, ref, typ, dz):
        ch = self.__getChannel(ref)
        print_debug('Fetching using TELEMAGAZYN-ENGINE - channel', ch)
        if not ch:
            return None
        tp = self.__getType(typ)
        fetchurl = 'http://www.telemagazyn.pl/%s/%s/%s,3,1,dz,go,cpr.html' % (ch, tp, dz)
        return getPage(fetchurl).addCallback(self.__fetchOK, (ref, typ, dz)).addErrback(self.__fetchFailed)

    def __fetchOK(self, res, tup):
        print_debug('-- FETCH OK for: ', str(tup[0] and tup[0].getServiceName() or '') + ', day: ' + str(tup[2]))
        result = []
        service = tup[0]
        typ = tup[1]
        dzien = tup[2]
        lastnum = 0
        print_debug('TELEMAGAZYN - Convert result to UTF8 - ', str(service and service.getServiceName() or ''))
        inhtml = mautils.html2utf8(res, 'ISO8859-2')
        idx = inhtml.find('id="lista-programow"')
        if idx > -1:
            inhtml = inhtml[idx:]
            elements = inhtml.split('<td class="lewy')
            print_debug('Elements count: ' + str(elements and len(elements) or 0))
            if elements and len(elements) == 0:
                print_debug('ELEMS 0 - res: ', str(res))
            offset = 0
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
                prog = mautils.between(element, '<td>', '</td>')
                # print_debug('PROG', str(prog))
                ds = None
                hr = mautils.between(prog, '<div class="m1', '<div')
                entryId = mautils.between(hr, 'id="chmurka-', '">')
                # print_debug('HR', str(hr))
                ds = mautils.between(prog, '<div class="opisProgramu">', '</div>')
                # print_debug('DS', str(ds))
                if not ds or len(ds) == 0:
                    ds = None
                if not hr and len(hr) == 0:
                    hr = None
                if hr and ds:
                    row = []
                    idxp = hr.find("<p")
                    # print_debug('HRP idx', str(idxp))
                    if idxp > -1:
                        hr = hr[idxp:]
                        hr = mautils.strip_tags(hr)
                        hr = hr.strip('"')
                        hr = hr.strip()
                        tm = time.strptime(dzien + hr, '%Y%m%d%H:%M')
                        sec = time.mktime(tm)
                        if num < lastnum:
                            offset = 86400
                        sec += offset
                        row.append(sec)
                        print_debug('Godzina', str(hr) + ', sec: ' + str(sec))

                    idxp = ds.find("<p")
                    # print_debug('DSP idx', str(idxp))
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
                    # self.__searchDetails(entryId, row)
                    row.append(None)

                    print_debug('- ROW LENGTH: ', str(len(row)))
                    if len(row) == 4:
                        row.append(service)
                        row.append(typ)
                        result.append(row)
                lastnum = num
        ''' ROW to (begin, opis, tytul, service, typ)'''
        # print_debug('ROW', str(result))
        print_debug('-- RESULT FOR: ', str(tup[0] and tup[0].getServiceName() or '') + ', day: ' + str(tup[2]) + ', res: ' + str(result))
        return result

    @defer.inlineCallbacks
    def __searchDetails(self, entryId, row):
        print_debug('Search details for entry:', str(entryId))
        duration = None
        if entryId:
            durl = "http://www.telemagazyn.pl/ajax/chmurka_programu/%s.html" % (entryId)
            ddf = getPage(durl).addCallback(self.__fetchDetailsOK).addErrback(self.__fetchFailed)
            duration = yield ddf
        print_debug('DURATION:', str(duration))
        row.append(duration)

    def __fetchDetailsOK(self, res):
        if res:
            prog = mautils.between(res, '<span>Czas:</span>', 'min.')
            if prog:
                prog = mautils.strip_tags(prog)
                prog = prog.strip()
                if prog.isdigit():
                    return int(prog)
        return None

    def __fetchFailed(self, res):
        pass

    def __getChannel(self, ref):
        x = ref.getServiceName()
        # print_debug('xx', x +', map: '+ str(MAPPING))
        return MAPPING.get(x)

    def __getType(self, typ):
        return 'film'

class FilmwebTvEngine(object):
    def __init__(self):
        pass

    def query(self, ref, typ, dz):
        ch = self.__getChannel(ref)
        print_debug('Fetching using FILMWEB-ENGINE - channel', ch)
        if not ch:
            return None
        tms = time.strptime(dz, "%Y%m%d")
        local = time.localtime(time.time())
        now = time.strptime(time.strftime("%Y%m%d", local), "%Y%m%d")
        # now = time.localtime(time.time())
        tt = time.mktime(tms) - time.mktime(now)
        d = datetime.timedelta(seconds=tt)

        if local[3] < 6:
            tx = time.localtime(time.mktime(tms) - 6 * 60 * 60)
            dz = time.strftime("%Y%m%d", tx)

        params = {}
        params['day'] = str(d.days)
        getdata = urllib.urlencode(params)
        fetchurl = 'http://www.filmweb.pl/guide/%s?%s' % (ch, getdata)
        print_info('URL', str(fetchurl))
        return getPage(fetchurl, method='GET', cookies=COOKIES, headers={'Referer':'http://www.filmweb.pl/guide', 'X-Requested-With':'XMLHttpRequest'}).addCallback(self.__fetchOK, (ref, typ, dz)).addErrback(self.__fetchFailed)

    def __fetchOK(self, res, tup):
        print_debug('-- FETCH OK for: ', str(tup[0] and tup[0].getServiceName() or '') + ', day: ' + str(tup[2]))
        result = []
        service = tup[0]
        typ = tup[1]
        dzien = tup[2]

        lastsec = time.mktime(time.strptime(dzien + '05:59', '%Y%m%d%H:%M'))
        off = 0

        print_debug('FILMWEBTV - Convert result to UTF8 - ', str(service and service.getServiceName() or ''))
        inhtml = mautils.html2utf8(res)
        # inhtml = mautils.between(inhtml, '<div class="channel first">', '<div class="channel">')
        # print_debug('++++++++++++ page', str(inhtml))
        inhtml = mautils.after(inhtml, 'brak programów dla wybranych filtrów')
        inhtml = mautils.after(inhtml, '<div class=toScroll>')
        # print_debug('+++++------- page', str(inhtml))
        # print_debug('------------------')

        elements = inhtml.split('<div class="singleProg seance seance_film')
        skip = True
        print_debug('Elements count: ' + str(elements and len(elements) or 0))
        if elements and len(elements) == 0:
            print_debug('ELEMS 0 - res: ', str(res))
        for element in elements:
            if skip:
                skip = False
                continue
            row = []
            # print_debug('----------- page', str(element))
            if element.find('<span class="hour">') < 0 and element.find('<span class=hour>') < 0:
                print_debug('ELEM hour not found - res: ', str(res))
                continue
            if element.find('<span class="hour">') > 0:
                hr = mautils.between(element, '<span class="hour">', '</span>')
            else:
                hr = mautils.between(element, '<span class=hour>', '</span>')
            # print_debug('--', hr)
            hr = mautils.strip_tags(hr)
            hr = hr.strip()
            # print_debug('--', hr)
            tm = time.strptime(dzien + hr, '%Y%m%d%H:%M')
            sec = time.mktime(tm) + off * 86400
            if sec < lastsec:
                off += 1
                sec += 86400
            lastsec = sec
            row.append(sec)
            print_debug('Godzina', str(hr) + ', sec: ' + str(sec))

            duration = None
            # print_debug('elem: ', str(element))
            hr = mautils.between(element, '<span class="duration">', '</span>')
            hr = hr and hr.strip()
            if not hr or len(hr) == 0:
                hr = mautils.between(element, '<span class=duration>', '</span>')
                hr = hr and hr.strip()
            if hr and len(hr) > 0:
                print_debug('Czas Trwania: ', str(hr))
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

            print_debug('- ROW LENGTH: ', str(len(row)))
            if len(row) == 4:
                row.append(service)
                row.append(typ)
                result.append(row)
        print_debug('-- RESULT FOR: ', str(tup[0] and tup[0].getServiceName() or '') + ', day: ' + str(tup[2]) + ', res: ' + str(result))
        return result

    def __fetchFailed(self, res):
        print_info('----> FAILED', str(res))

    def __getChannel(self, ref):
        x = ref.getServiceName()
        # print_debug('xx', x +', map: '+ str(MAPPING))
        return MAPPING2.get(x)


