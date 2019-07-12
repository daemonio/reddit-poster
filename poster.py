#!/usr/bin/env python

# TODO: try/catch stuff

import time
import sys
import praw
import os
import sqlite3
from datetime import datetime

# queue
# waiting
# posted
# skip
# ignored

# skip when we have two posts in the sub and the
# first post is a "best", that means that the second post
# has to wait until the first one is rising.

# ignored is used for "follow" the post just stay there.

# type
# anytime
# best
# follow

# status
# schedule
# subreddit
# title
# url
# tim

# TODO: Constants. Make sure to put this on
# separeted classes/files.
#SLEEP_BETWEEN_POSTS = 120 # 2 min
SLEEP_BETWEEN_POSTS = 10 # 2 min
#SLEEP_LOOP          = 300 # 5 min
SLEEP_LOOP          = 10 # 5 min
POST_FILE           = 'postfile.txt'
PUSHIT_SEARCH       = 'https://api.pushshift.io/reddit/search/submission/'\
                      '?q=&subreddit={0}&fields=title,created_utc,score'\
                      '&after={1}&before={2}'
PRAW_RENEW_AUTH     = 7200 # renew praw auth every 2hr
#TIME_POST_SAME_SUB  = 7200
TIME_POST_SAME_SUB  = 300 

class DB:
    def __init__(self, DB_FILE):
        self.dbfile    = DB_FILE
	self.conn      = sqlite3.connect(self.dbfile)
        self.cursor    = self.conn.cursor() 

    def close(self):
        self.conn.close()

    def execute(self, query, parameters):
        self.cursor.execute(query, parameters)
        self.conn.commit()
        return self.cursor.fetchall()

    def select(self, query, parameters):
        self.cursor.execute(query, parameters)
        return self.cursor.fetchall()

    def select_print(self, query, parameters):
        self.cursor.execute(query, parameters)
        for t in self.cursor.fetchall():
            print t

class POST:
    def __init__(self, status, schedule, subreddit, title, url, tim):
        self.status    = status
        self.schedule  = schedule
        self.subreddit = subreddit
        self.title     = title
        self.url       = url
        self.timestamp = tim

    def get_status(self):
        return self.status

    def get_schedule(self):
        return self.schedule

    def get_title(self):
        return self.title

    def get_url(self):
        return self.url

    def get_timestamp(self):
        return float(self.timestamp)

    def get_subreddit(self):
        return self.subreddit

    def get_seconds(self):
        return self.secs

    def get_hash(self):
        return hash(self.subreddit+self.title+self.url)

    def __str__(self):
        s = 'Status: {0}\nSche.: {1}\nSubreddit: {2}\nTitle: {3}\nURL: {4}\nTime: {5}\n'
        s = s.format(self.status, self.schedule, self.subreddit, self.title, self.url, self.timestamp)
        
        return s

# Our database. Use DB as parent class.
class DBREDDIT(DB):
    def __init__(self, DB_FILE):
        # parent's constructor.
        DB.__init__(self, DB_FILE)
        self.table     = DB_FILE.split('.')[0]
        self.posts     = []
        self.debugflag = True

    def insert(self, p):
        # TODO: remove "reddit" and use query variable
        self.execute("""
        INSERT INTO reddit (status, schedule, subreddit, title, url, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)""", (p.get_status(), p.get_schedule(),
            p.get_subreddit(), p.get_title(), p.get_url(), p.get_timestamp()))
         
    def _debug(self, msg):
        if self.debugflag:
            print '[+] DEBUG: ' + msg

    def show(self):
        #TODO: empty tuple on second parameter?
        self.select_print('select * from '+self.table, tuple())

    def tuple_to_post(self, t):
        return POST(*t)

    def update_field(self, key, field, new_value):
        query = 'update {0} set {1}=? where id=?'.format(self.table, field)
        self.execute(query, (new_value, key))
        pass

    def select_field(self, columns, field, value, notEqual=False):
        if notEqual:
            query = 'select {0} from {1} where {2}<>?'.format(columns, self.table, field)
        else:
            query = 'select {0} from {1} where {2}=?'.format(columns, self.table, field)
        return self.select(query, (value,))

    def exists(self, p):
        for t_ in self.execute('select * from reddit where subreddit=?', (p.get_subreddit(),) ):
            # remove id (first position)
            t = t_[1:]

            q = self.tuple_to_post(t)

            if p.get_hash() == q.get_hash():
                return True

        return False

    def update(self, POSTS_FILE):
        for p in POSTS_FILE:
            if self.exists(p) == False:
                self._debug('Adding ' + p.get_title() + ' to database.')
                self.insert(p)

def to_hour(seconds):
    return round(seconds/(60 * 60))

def reddit_calc_timestamp_best(reddit, subreddit, limit_new=30):
    sub = reddit.subreddit(subreddit)
    current_timestamp = time.time()

    # off by 2 minutes
    best_timestamp = current_timestamp + 2*60

    for submission in sub.new(limit=limit_new):
        score   = submission.score
        seconds = current_timestamp - submission.created_utc

        hour = to_hour(seconds)

        # for posts < 1hr 
        if hour == 0:
            hour = 1

        print submission.title, submission.created_utc, score, to_hour(seconds)

        # submissions are already in order (the most recent first).
        # the first who matches will bring the longest timestamp.
        if hour < 15 and (score/hour) > 88:
            #print 'ACHOU: {0} + {1} + {2}'.format(current_timestamp, (15 - hour)*3600, 2*60)
            best_timestamp = current_timestamp + (15 - hour)*3600 + 2*60

            break

    return best_timestamp

def reddit_submit(reddit, _subreddit, _title, _url):
    sub = reddit.subreddit(_subreddit)
    print sub.submit(title=_title, url=_url)

def read_post_file(filename):
    POSTS_LIST = []

    with open(filename,'r') as fd:
        for line in fd:
            line = line.rstrip('\n')

            subreddit, title, url, schedule = line.split('~')
            p = POST('queue', schedule, subreddit, title, url, 0)

            POSTS_LIST.append(p)

    return POSTS_LIST

def countdown(msg, sleep):
    for i in range(sleep):
        print '{0} {1}/{2}'.format(msg, i, sleep)
        time.sleep(1)

def show_info(RDB):
    q_i = RDB.select_field('id', 'status', 'queue')
    w_i = RDB.select_field('id', 'status', 'waiting')
    p_i = RDB.select_field('id', 'status', 'posted')

    print '[+] Info: Queue: {0} | Waiting: {1} | Posted: {2}'.format(
            len(q_i), len(w_i), len(p_i))

    t_i = RDB.select('select subreddit,timestamp from reddit where status=? order by timestamp', ('waiting',))

    for s in t_i:
        print '[+] Schedule @ {0} : {1}'.format(s[0], datetime.fromtimestamp(s[1]))
    #r_i = t_i[0][1]
    #if r_i != None:
    #    print '[+] Next post is scheduled to: ', datetime.fromtimestamp(r_i), '@', t_i[0][0]
    #else:
    #    print '[+] NO post being scheduled right now.'

    print '[+] Next Auth renew: ', datetime.fromtimestamp(time.time() + PRAW_RENEW_AUTH)


#
# MAIN
#

# data base file should be created beforehand.
RDB = DBREDDIT('reddit.db')
# Your bot description in ~/.config/praw.ini
BOT_NAME='alface'

# Praw obj. Will be initialized in the main loop.
reddit = None

# used to check if postfile.txt was modified.
OLDMTIME = 0
POSTS_LIST = []

# inc every time.
praw_renew_time = 0

while True:
    praw_renew_time = praw_renew_time % PRAW_RENEW_AUTH

    if praw_renew_time == 0:
        reddit = praw.Reddit(BOT_NAME, user_agent='script powered by u/yorian_dates')
        print '[+] PRAW: connect as: ', reddit.user.me()

    if OLDMTIME != os.path.getmtime(POST_FILE):
        POSTS_LIST = read_post_file(POST_FILE)
        OLDMTIME = os.path.getmtime(POST_FILE)

        RDB.update(POSTS_LIST)

    show_info(RDB)

    # All posts that weren't posted yet (status not equal to posted)
    available_posts = RDB.select_field('*', 'status', 'posted', notEqual=True)
    for t in available_posts:
        (key, status, schedule, subreddit, title, url, timestamp) = t

        actual_timestamp = time.time()

        if status == 'queue':
            # Don't de-queue if there are 'waiting' posts
            # of the same subreddit. The first post should
            # be made in order to post the second, and go on.
            is_to_update = True
            for u in RDB.select_field('status,schedule', 'subreddit', subreddit):
                if u[0] == 'waiting':
                    is_to_update = False
                    break
            if is_to_update:
                RDB.update_field(key, 'status', 'waiting')
                new_timestamp = actual_timestamp

                if schedule == 'best':
                    print 'Updating timestamp'
                    #new_timestamp = reddit_calc_timestamp_best(reddit, subreddit, limit_new=30)
                    new_timestamp = time.time() + 60*2
                    #new_timestamp = time.time() + SLEEP_BETWEEN_POSTS

                    # If we're posting in the subreddit we have to "wait" at least 2h when using
                    # "best" since the previous best can be rising and gaining upvotes.
                    query = 'select MAX(timestamp) from reddit where subreddit=? and status=?'
                    r_query = RDB.select(query, (subreddit, 'posted'))
                    t_timestamp = r_query[0][0] # None or the last timestamp of this particular subreddit.

                    if t_timestamp != None and (actual_timestamp - t_timestamp) < TIME_POST_SAME_SUB:
                        new_timestamp += TIME_POST_SAME_SUB
                        print '[+] Skipping until: ', TIME_POST_SAME_SUB
                        RDB.update_field(key, 'status', 'skip')
                elif schedule == 'follow':
                    # TODO: follow as first post should act like anytime
                    RDB.update_field(key, 'status', 'ignored')

                RDB.update_field(key, 'timestamp', new_timestamp)
            else:
                print 'No update. A post for r/'+subreddit+' is already scheduled.'
        elif status == 'waiting' and actual_timestamp > timestamp:
            print 'Posted.'
            #reddit_submit(reddit, subreddit, title, url)
            RDB.update_field(key, 'status', 'posted')

            query_follow = 'select status,schedule from reddit where id=?'
            t_follow = RDB.select(query_follow, (key+1,))

            if len(t_follow) > 0:
                t_status, t_schedule = t_follow[0]

                if t_status == 'ignored' and t_schedule == 'follow':
                    # Just make sure that the follow post has
                    # timestamp less than the above post.
                    RDB.update_field(key+1, 'status', 'waiting')
                    RDB.update_field(key+1, 'timestamp', timestamp)

            countdown('Sleep time between posting. Waiting...', SLEEP_BETWEEN_POSTS)
        elif status == 'skip' and actual_timestamp > timestamp:
            # Time to wake up and be back to queue.
            RDB.update_field(key, 'status', 'queue')

    countdown('Loop waiting...', SLEEP_LOOP)
    praw_renew_time += SLEEP_LOOP
    RDB.show()
