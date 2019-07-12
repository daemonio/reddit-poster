#!/usr/bin/env python
#qui jul 11 10:40:20 -03 2019

import time
import sys
import praw
import os

def to_date_ago(seconds):
    if seconds < 60:
        return (seconds, 'seconds')
    
    minutes = round(seconds/60)
    if minutes < 60:
        return (minutes, 'minutes')
    
    hour = round(minutes/60)
    if hour < 24:
        return (hour, 'hours')
    
    day = round(hour/24)
    if day < 30:
        return (day, 'days')
    
    month = round(day/30)
    if month < 12:
        return (month, 'months')

    year = round(month/12)
    
    return (year, 'years')

#
# MAIN
#

try:
    sub_name = sys.argv[1]
    term     = sys.argv[2]
except:
    print '[use] ' + sys.argv[0] + ' <sub name> <search term>'
    sys.exit(0)

BOT_NAME = 'alface'
reddit = praw.Reddit(BOT_NAME, user_agent='script powered by u/yorian_dates')
print '[+] PRAW: connect as: ', reddit.user.me()

sub = reddit.subreddit(sub_name)
current_timestamp = time.time()
for i in sub.search(term, limit=30):
    t = current_timestamp - i.created_utc
    (d1, d2) = to_date_ago(t)

    title  = i.title.encode('utf-8')
    score  = i.score
    author = i.author

    print 'Title: {0}\nScore: {1}\nAuthor: {2}\nPosted: {3} {4} ago\n\n'.format(
            title, score, author, d1, d2)
