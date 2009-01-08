#!/usr/bin/env python
# coding=utf-8


import sys
import getopt
import glob
import urllib2
import urllib

import eyeD3
from eyeD3.tag import *


def usage():
    print "usage: %s [-l|--lyrics] [-a|--artwork] [file|-d dirname]" % sys.argv[0]
    sys.exit(1)

if len(sys.argv) < 3:
    usage()


def getUniqueValues(source):
    target = []
    for src in source:
        if src not in target:
            target.append(src)
    return target
    
def getWalmartArtwork(artist, album):
    import urllib
    import re
    import os
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
        print "cover saved to tmp file", output
        return output 

def fillAlbumCover(filename):
    if not isMp3File(filename):
        print filename, "is not a mp3 file"
        usage()

    mp3 = Mp3AudioFile(filename)

    artist = mp3.getTag().getArtist()
    album = mp3.getTag().getAlbum()

    if album == "":
        print "there are no album title in tags, sorry"
        exit
    elif artist == "":
        print "there are no artist name in tags, sorry"
        exit

    cover = getWalmartArtwork(artist, album)

    mp3.getTag().addImage(0x03, cover)
    mp3.getTag().update()

    os.remove(cover)

    print "cover image added"

def fillTrackLyrics(filename):
    if not isMp3File(filename):
        print filename, "is not a mp3 file"
        usage()
        
    mp3 = Mp3AudioFile(filename)
    mp3Tags = mp3.getTag()
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
        lyrics = urllib2.urlopen(u).read()
        lyrics = lyrics.decode("utf-8")
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
    return __getFilesRecursive(dirname, [])

def __getFilesRecursive(dirname, files):
    if os.path.isdir(dirname):
        for f in glob.glob(os.path.join(dirname, '*.mp3')):
            print f
            fl = os.path.join(dirname, f);
            files.append(fl)
        dirList=os.listdir(dirname)
        for fname in dirList:
            fl = os.path.join(dirname, fname)
            if os.path.isdir(fl):
                files.extend(__getFilesRecursive(fl, files))

        return files

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ald:", ["lyrics", "artwork"])
    except getopt.GetoptError, e:
        print e
        usage()
    
    files=[]
    lyrics = False
    artwork = False
    for opt, value in opts:
        if opt == "-d":
            files.extend(getFilesRecursive(value.encode("utf-8")))
        elif opt in ("-l", "--lyrics"):
            lyrics = True
        elif opt in ("-a", "--artwork"):
            artwork = True

    if len(args) > 0:
        files.extend(args)

    for f in files:
        print "============================"
        print f
        if lyrics:
            fillTrackLyrics(f)
        if artwork:
            fillAlbumCover(f)

    print "bye"
