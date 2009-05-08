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
    print "usage: %s TEXT_FILE MP3_FILE" % sys.argv[0]
    sys.exit(1)

def fillTrackWithText(filename, text_filename):
    if not isMp3File(filename):
        print filename, "is not a mp3 file"
        usage()
    
    mp3 = Mp3AudioFile(filename)
    mp3Tags = mp3.getTag()
    mp3Tags.setVersion(eyeD3.ID3_V2_4)
    mp3Tags.setTextEncoding(eyeD3.UTF_8_ENCODING)
    
    print "Reading txt file"
    f = open(text_filename)
    
    text = "".join(f.readlines())
    
    if text:
        print "Ok. Updating file...",
        mp3Tags.addLyrics(text)
        mp3Tags.update()
        print "file updated."
    else:
        print "No text, sorry"


if __name__ == "__main__":

    if len(sys.argv) != 3:
        usage()
    try:
        fillTrackWithText(sys.argv[2], sys.argv[1])
    except Exception, e:
        log.error("Error occured during procession %s: %s", sys.argv[2], e)
        import traceback
        traceback.print_tb(sys.exc_info()[2])
    print "Bye"

