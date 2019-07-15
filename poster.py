#!/usr/bin/env python

# TODO: try/catch stuff

import time
import sys
import praw
import os
import sqlite3
import re
from shutil import copyfile
from datetime import datetime

# for colored print's
from colorama import Fore, Back, Style

# TODO: Constants. Make sure to put this on
# separeted classes/files.
SLEEP_BETWEEN_POSTS = 120 # 2 min
SLEEP_LOOP          = 300 # 5 min
POST_FILE           = 'postfile.txt'
PRAW_RENEW_AUTH     = 7200 # renew praw auth every 2hr
TIME_POST_SAME_SUB  = 300 
DRY_RUN_BEST_TIME   = 120  # only when using --dry-run

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
    def __init__(self, DB_FILE, table):
        # parent's constructor.
        DB.__init__(self, DB_FILE)
        self.table     = table
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

class Print():
    def __init__(self):
        pass

    def info(self, msg):
        print Fore.MAGENTA + msg + Style.RESET_ALL

    def alert(self, msg):
        print Fore.RED + msg + Style.RESET_ALL

    def event(self, msg):
        print Fore.YELLOW + msg + Style.RESET_ALL

    def show(self, msg):
        print Fore.GREEN + msg + Style.RESET_ALL

def to_hour(seconds):
    return round(seconds/(60 * 60))

def to_seconds(n, suffix):
    if suffix == 's':
        return float(n)
    if suffix == 'm':
        return float(n)*60
    if suffix == 'h':
        return float(n)*60*60
    if suffix == 'd':
        return float(n)*60*60*24

    #TODO: error
    assert 0!=0, 'wrong suffix'

def reddit_calc_timestamp_best(reddit, subreddit, limit_new=30):
    sub = reddit.subreddit(subreddit)
    current_timestamp = time.time()

    # off by 2 minutes
    best_timestamp = current_timestamp #+ 2*60

    for submission in sub.new(limit=limit_new):
        score   = submission.score
        seconds = current_timestamp - submission.created_utc

        hour = to_hour(seconds)

        # for posts < 1hr 
        if hour == 0:
            hour = 1

        #print submission.title, submission.created_utc, score, to_hour(seconds)

        # submissions are already in order (the most recent first).
        # the first who matches will bring the longest timestamp.
        # TODO: using 88 instead of 100.
        if hour < 15 and (score/hour) > 88:
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

def countdown(MyPrint, msg, sleep):
    for i in range(sleep):
        MyPrint.show('{0} {1}/{2}'.format(msg, i, sleep))
        time.sleep(1)

def show_info(MyPrint, RDB):
    q_i = RDB.select_field('id', 'status', 'queue')
    w_i = RDB.select_field('id', 'status', 'waiting')
    p_i = RDB.select_field('id', 'status', 'posted')

    MyPrint.info('[+] Info: Queue: {0} | Waiting: {1} | Posted: {2}'.format(
            len(q_i), len(w_i), len(p_i)))
    MyPrint.info('[+] Next Auth renew: {0}'.format(datetime.fromtimestamp(time.time() + PRAW_RENEW_AUTH)))

    t_i = RDB.select('select subreddit,timestamp from reddit where status=? order by timestamp', ('waiting',))

    for s in t_i:
        MyPrint.event('[+] Schedule @ {0} : {1}'.format(s[0], datetime.fromtimestamp(s[1])))

#
# MAIN
#

# Just to color stuff around.
MyPrint = Print()
DRY_RUN = False

# --dry-run: for testing. NOTHING will be posted to reddit.
if len(sys.argv) > 1:
    if sys.argv[1] == '--dry-run':
        DRY_RUN = True

    MyPrint.alert('[+] Dry run mode. Nothing will be altered or posted.')

# Database should be the name of the sqlite3 file.
DATABASE_NAME='reddit.db'

# in case of a dry run create a dumb database
if DRY_RUN:
    DATABASE_NAME='redditdryrun.db'
    copyfile('reddit.db', DATABASE_NAME)
    MyPrint.alert('[+] Using Dry run database: ' + DATABASE_NAME)

# data base file should be created beforehand.
# Second parameter is the table name.
RDB = DBREDDIT(DATABASE_NAME, 'reddit')

# Your bot description in ~/.config/praw.ini
BOT_NAME='mybot'

# Praw obj. Will be initialized in the main loop.
reddit = None

# used to check if postfile.txt was modified.
OLDMTIME = 0
POSTS_LIST = []

# inc every time.
praw_renew_time = 0

# Decrease time for test purposes.
if DRY_RUN:
    SLEEP_BETWEEN_POSTS = 10
    SLEEP_LOOP          = 10
    TIME_POST_SAME_SUB  = 120 

while True:
    praw_renew_time = praw_renew_time % PRAW_RENEW_AUTH

    if praw_renew_time == 0:
        reddit = praw.Reddit(BOT_NAME, user_agent='reddit-poster script')
        MyPrint.event('[+] PRAW: connect as: ' + str(reddit.user.me()))

    if OLDMTIME != os.path.getmtime(POST_FILE):
        POSTS_LIST = read_post_file(POST_FILE)
        OLDMTIME = os.path.getmtime(POST_FILE)

        RDB.update(POSTS_LIST)

    show_info(MyPrint, RDB)

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
                    if DRY_RUN:
                        # set any timestamp on dry run.
                        new_timestamp = time.time() + DRY_RUN_BEST_TIME
                    else:
                        new_timestamp = reddit_calc_timestamp_best(reddit, subreddit, limit_new=30)

                    # If we're posting in the subreddit we have to "wait" at least 2h when using
                    # "best" since the previous best can be rising and gaining upvotes.
                    query = 'select MAX(timestamp) from reddit where subreddit=? and status=?'
                    r_query = RDB.select(query, (subreddit, 'posted'))
                    t_timestamp = r_query[0][0] # None or the last timestamp of this particular subreddit.

                    if t_timestamp != None and (actual_timestamp - t_timestamp) < TIME_POST_SAME_SUB:
                        new_timestamp += TIME_POST_SAME_SUB
                        MyPrint.alert('[+] Skipping until: ' + str(TIME_POST_SAME_SUB))
                        RDB.update_field(key, 'status', 'skip')
                elif schedule == 'follow':
                    # TODO: follow as first post should act like anytime
                    RDB.update_field(key, 'status', 'ignored')
                elif schedule[0] == '+':
                    regexres = re.search('^\+([0-9]+)([smhd])$', schedule)
                    time_seconds = to_seconds(regexres.group(1), regexres.group(2))

                    new_timestamp = actual_timestamp + time_seconds

                RDB.update_field(key, 'timestamp', new_timestamp)
            else:
                MyPrint.alert('No update. A post for r/'+subreddit+' is already scheduled.')
        elif status == 'waiting' and actual_timestamp > timestamp:
            MyPrint.alert('[+] Posted in {0} : {1}'.format(subreddit, title))
            if DRY_RUN == False:
                reddit_submit(reddit, subreddit, title, url)
                pass

            RDB.update_field(key, 'status', 'posted')

            query_follow = 'select status,schedule from reddit where id=?'

            # Loop to treat multiple "follows".
            key_next = key + 1
            while True:
                t_follow = RDB.select(query_follow, (key_next,))

                if len(t_follow) > 0:
                    t_status, t_schedule = t_follow[0]

                    if t_status == 'ignored' and t_schedule == 'follow':
                        # Just make sure that the follow post has
                        # timestamp less than the above post.
                        RDB.update_field(key_next, 'status', 'waiting')
                        RDB.update_field(key_next, 'timestamp', timestamp)
                    else:
                        break
                else:
                    break

                key_next += 1

            countdown(MyPrint, 'Sleep time between posting. Waiting...', SLEEP_BETWEEN_POSTS)
        elif status == 'skip' and actual_timestamp > timestamp:
            # Time to wake up and be back to queue.
            RDB.update_field(key, 'status', 'queue')

    countdown(MyPrint, 'Loop waiting...', SLEEP_LOOP)
    praw_renew_time += SLEEP_LOOP
    RDB.show()
