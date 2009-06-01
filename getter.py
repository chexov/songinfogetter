#!/usr/bin/env python
# coding=utf-8

import logging
import sys
import getopt
import glob
import urllib2
import urllib
import re
import os
import fnmatch
from threading import Thread

import eyeD3
from eyeD3.tag import *

cache = dict()
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def usage():
    print "usage: %s [-l|--lyrics] [-a|--artwork] [<file> <file> <dir> <...>]" % sys.argv[0]
    sys.exit(1)

def getUniqueValues(source):
    target = []
    for src in source:
        if src not in target:
            target.append(src)
    return target

def getAmazonArtwork(artist, album, lock=None):

    def _GetResultURL(xmldata):
        url_re = re.compile(r"<DetailPageURL>([^<]+)</DetailPageURL>")
        m = url_re.search(xmldata)
        return m and m.group(1)

    def _SearchAmazon(artist, album):
        data = {
          "Service": "AWSECommerceService",
          "Version": "2005-03-23",
          "Operation": "ItemSearch",
          "ContentType": "text/xml",
          # AWS ID just for this script
          "SubscriptionId": "0XRZB4P7WVZTP0C06Y02",
          "SearchIndex": "Music",
          "ResponseGroup": "Small",
        }
        data["Artist"] = artist
        data["Keywords"] = album

        fd = urllib.urlopen("%s?%s" % ("http://ecs.amazonaws.com/onca/xml", urllib.urlencode(data)))
        return fd.read()

    url = _GetResultURL(_SearchAmazon(artist, album))
    if not url:
        return None
    img_re = re.compile(r'''registerImage\("original_image", "([^"]+)"''')
    prod_data = urllib.urlopen(url).read()
    m = img_re.search(prod_data)
    if not m:
        return None
    img_url = m.group(1)
    i = urllib.urlopen(img_url)

    output = tempfile.mktemp(".jpg")
    o = open(output, "wb")
    o.write(i.read())
    o.close()

    return output 

    
def getWalmartArtwork(artist, album, lock=None):

    print "Getting artwork from Walmart"

    import tempfile
    walmart = { 'albums' : { 'url'   : 'http://www.walmart.com/catalog/search-ng.gsp?',
                             'query' : 'search_query',
                             'args'  : { 'search_constraint': '4104', 'ics' : '5', 'ico': '0' },
                             're' : [ r'<input type="hidden" name="product_id" value="(\d+)">' ] },
                'covers' : { 'url'   : 'http://www.walmart.com/catalog/product.do?',
                             'query' : 'product_id',
                             'args'  : { },
                             're' : 
            [ r'<a href="javascript:photo_opener\(\'(\S+.jpg)&amp;product_id=',
              r'<meta name="Description" content="(.+) at Wal-Mart.*">' ] }
             }


    def searchInWalmart(search_type, keyword):
        s = walmart[search_type]
        args = s['args']
        args[s['query']] = keyword
        url = s['url'] + urllib.urlencode(args)
        file = urllib.urlopen(url)
        #print "url in search:", url
        content = file.read()
        result = []
        for i in s['re']:
            r = re.compile(i, re.M)
            result += r.findall(content)
        return result

    albums = searchInWalmart('albums', artist + " " + album)
    albums = getUniqueValues(albums)
    
    #print "albums ids =", albums
    covers = [searchInWalmart('covers', albumResults) for albumResults in albums]
    #print "covers ids =", covers

    if len(covers) > 0:
        cover = covers[0]
        cover_ulr, name = cover
        i = urllib.urlopen(cover_ulr)
        output = tempfile.mktemp(".jpg")
        o = open(output, "wb")
        o.write(i.read())
        o.close()
        return output 

class DummyRunner(Thread):
    def __init__(self, function, args):
        Thread.__init__(self)
        self.args = args
        self.function = function
        self.result = None
        self.finished = False
    
    def run(self):
        self.result = self.function(*self.args)
        self.finished = True
    
    def is_finished(self):
        return self.finished
    
    def get_result(self):
        return self.result;
    

def fillAlbumCover(filename):
    if not isMp3File(filename):
        print filename, "is not a mp3 file"
        usage()
    
    mp3 = Mp3AudioFile(filename)
    
    artist = mp3.getTag().getArtist()
    album = mp3.getTag().getAlbum()
    
    if album == "":
        print "there are no album title in tags, sorry"
        return None
    elif artist == "":
        print "there are no artist name in tags, sorry"
        return None
    
    # Checking if cache has cached cover_file,
    # if not than getting cover from artwork providers
    cover_file = None
    
    if cache.has_key((artist, album)):
        print "Cover retrieved from cache"
        cover_file = cache.get((artist, album))
    else:
        print "Getting artwork from Amazon for '%s' - '%s' " % (mp3.getTag().getArtist(),  mp3.getTag().getTitle())
        amazonRnr = DummyRunner(getAmazonArtwork, (artist.encode("utf-8"), album.encode("utf-8")))
        amazonRnr.start()
        
        timeout = 60
        start_time = time.time();
        while (time.time() - start_time) < timeout and not amazonRnr.is_finished():  #and not walmartRnr.get_result())\
            pass
        
        if amazonRnr.get_result():
            cover_file = amazonRnr.get_result()
            print "Cover downloaded from Amazon"
            cache[(artist, album)] = cover_file
            print "Cover added to cache"
            
        #     walmartRnr.reject()
        # elif walmartRnr.get_result():
        #     cover_file = walmartRnr.get_result()
        #     print "Cover downloaded from Walmart"
        #     amazonRnr.reject()
        
        if not cover_file and amazonRnr.is_finished():
            print "No cover found"
            return None
        elif not cover_file:
            print "%dsec timeout during getting covers, skipping" % timeout
            return None
    
    mp3.getTag().addImage(0x03, cover_file)
    mp3.getTag().update()
    print "Cover inserted into mp3"



def clean_cache():
    for f in cache.values():
        os.remove(f)
    print "Cache cleaned"

def fillTrackLyrics(filename):
    if not isMp3File(filename):
        print filename, "is not a mp3 file"
        usage()
    
    mp3 = Mp3AudioFile(filename)
    mp3Tags = mp3.getTag()
    mp3Tags.setVersion(eyeD3.ID3_V2_4)
    mp3Tags.setTextEncoding(eyeD3.UTF_8_ENCODING)
    print "Getting lyrics from lyricwiki.org for '%s' - '%s'" % (mp3.getTag().getArtist(),  mp3.getTag().getTitle())
    query = {'func': 'getSong',
             'artist': mp3Tags.getArtist().encode("utf-8"),
             'song': mp3Tags.getTitle().encode("utf-8"),
             'fmt': 'text',
             }
    u = 'http://lyricwiki.org/api.php?' + urllib.urlencode(query)
    lyrics = None
    try:
        log.debug("Opening URL `%s`" % u)
        lyrics = urllib2.urlopen(u).read()
        lyrics = lyrics.decode("utf-8")
        # lyricswiki.org respod with HTTP 200 even if lyrics are not found, but body is 'Not found'
        if lyrics == 'Not found':
            lyrics = None
    except:
        print "Error while opening %s: %s" % (u, sys.exc_info())
        return None
    
    if lyrics:
        print "Lyrics found. Updating file...",
        mp3Tags.addLyrics(lyrics)
        mp3Tags.update()
        print "file updated."
    else:
        print "Lyrics are not found"


def getFilesRecursive(dirname):
    if not os.path.isdir(dirname):
        print dirname, "is not a directory"
        usage()
    
    mp3_files = []
    for path, dirs, files in os.walk(os.path.abspath(dirname)):
        for filename in fnmatch.filter(files, "*.mp3"):
            mp3_files.append(os.path.join(path, filename))

    return mp3_files

if __name__ == "__main__":

    if len(sys.argv) < 3:
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ald:", ["lyrics", "artwork"])
    except getopt.GetoptError, e:
        print e
        usage()
    
    files=[]
    items=[]
    lyrics = False
    artwork = False
    for opt, value in opts:
        if opt in ("-l", "--lyrics"):
            lyrics = True
        elif opt in ("-a", "--artwork"):
            artwork = True

    if len(args) == 1 and args[0] == '-':
        for __stdinline in sys.stdin.readlines():
            items.append(__stdinline.rstrip())
            print items
    elif len(args) > 0:
        items.extend(args)

    # If args have dirs, will go recursive on that dir tree
    for __item in items:
        if os.path.isdir(__item):
            files.extend(getFilesRecursive(__item))
        else:
            files.append(__item)

    print "Total files:", len(files)
    for f in files:
        print "============================"
        print "Working with %s" % f
        try:
            if lyrics:
                fillTrackLyrics(f)
            if artwork:
                fillAlbumCover(f)
        except Exception, e:
            log.error("Error occured during procession %s: %s", f, e)
            import traceback
            traceback.print_tb(sys.exc_info()[2])
            continue
    clean_cache()
    print "Bye"

