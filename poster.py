#!/usr/bin/env python3

# TODO: try/catch stuff
# TODO: python 3

import time
import sys
import praw
import os
import sqlite3
import re
import optparse
from shutil import copyfile
from datetime import datetime

# for colored print's
from colorama import Fore, Back, Style

# TODO: Constants. Make sure to put this on
# classes or files.
SLEEP_BETWEEN_POSTS = 120 # 2 min
SLEEP_LOOP          = 300 # 5 min
POST_FILE           = 'postfile.txt'
PRAW_RENEW_AUTH     = 7200 # renew praw auth every 2hr
TIME_POST_SAME_SUB  = 7200 # used when two or more "best" posts.
DRY_RUN_BEST_TIME   = 120  # used when using --dry-run
BOT_NAME            = 'mybot' # modify this
BEST_POST_AGE       = 13 #the age of the post when using "best"

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
            print (t)

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
            print ('[+] DEBUG: ' + msg)

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
        print (Fore.MAGENTA + msg + Style.RESET_ALL)

    def warn(self, msg):
        print (Fore.MAGENTA, Back.WHITE + msg + Style.RESET_ALL)

    def alert(self, msg):
        print (Fore.WHITE, Back.RED + msg + Style.RESET_ALL)

    def event(self, msg):
        print (Fore.YELLOW, Back.WHITE + msg + Style.RESET_ALL)

    def show(self, msg):
        print (Fore.GREEN + msg + Style.RESET_ALL)

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

def reddit_get_posts(reddit, new_or_search, subreddit, search, limit_new=10):
    sub = reddit.subreddit(subreddit)
    current_timestamp = time.time()

    SUB_LIST = []
    SUBMISSION_LIST = []

    if new_or_search == True:
        SUBMISSION_LIST = sub.new(limit=limit_new)
    else:
        SUBMISSION_LIST = sub.search(search, limit=limit_new)

    limit_p = int(limit_new)
    #for submission in sub.new(limit=limit_new):
    for submission in SUBMISSION_LIST:
        t = current_timestamp - submission.created_utc
        (d1, d2) = to_date_ago(t)

        title  = submission.title.encode('utf-8')
        score  = submission.score
        author = submission.author
        url    = submission.url

        print ('Title: {0}\nUrl: {1}\nScore: {2}\nAuthor: {3}\nPosted: {4} {5} ago\n\n'.format(
                title, url, score, author, d1, d2))

        # TODO: In my tests the "limit" parameter of PRAW API did not work.
        limit_p -= 1
        if limit_p == 0:
            break

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

        if hour < BEST_POST_AGE and (score/hour) > 88:
            best_timestamp = current_timestamp + (BEST_POST_AGE - hour)*3600 + 2*60

            break

    return best_timestamp

def reddit_submit(reddit, _subreddit, _title, _url):
    sub = reddit.subreddit(_subreddit)
    print (sub.submit(title=_title, url=_url))

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

    # SKIP info
    t_i = RDB.select('select subreddit,title,timestamp from reddit where status=? order by timestamp', ('skip',))
    for s in t_i:
        MyPrint.warn('[+] SKIP to WAITING {0} "{1}" in {2}'.format(
            s[0], s[1], datetime.fromtimestamp(s[2])))

    # NEXT post
    t_i = RDB.select('select subreddit,title,timestamp from reddit where status=? order by timestamp', ('waiting',))
    for s in t_i:
        MyPrint.warn('[+] NEXT post to {0} "{1}" @ {2}'.format(
            s[0], s[1], datetime.fromtimestamp(s[2])))

def praw_login(BOT_NAME):
    reddit = praw.Reddit(BOT_NAME, user_agent='reddit-poster script')
    MyPrint.event('[+] PRAW: connect as: ' + str(reddit.user.me()))

    return reddit

#
# MAIN
#

# Dealing with options
parser = optparse.OptionParser()
parser.add_option('--dry-run', action="store_true", default=False,
        help='Execute script as a test. No post will be submitted to reddit.')
parser.add_option('--quit-after', action="store_true", default=False,
        help='Quit the script when everything is submitted.')
parser.add_option('--command-after', action="store", dest="command",
        help='Command to execute (only once) when everything is submitted.')
parser.add_option('--subreddit', action="store", dest="subreddit",
        help='Set the subreddit that the options will operate.')
parser.add_option('--best', action="store_true", default=False,
        help='Print the "best" time to post in --subreddit.')
parser.add_option('--new', action="store", dest='new',
        help='Get the first N new posts of the --subreddit.')
parser.add_option('--search', action="store", dest='search',
        help='Terms to search in --subreddit.')

(options, values) = parser.parse_args()

OPT_DRY_RUN=options.dry_run
OPT_QUIT=options.quit_after
OPT_CMD_AFTER=options.command
OPT_SUBREDDIT=options.subreddit
OPT_BEST=options.best
OPT_SEARCH=options.search
OPT_NEW=options.new

# Validating parameters.
if (OPT_SUBREDDIT == None) and (OPT_BEST or OPT_NEW != None or OPT_SEARCH != None):
    print ('[+] Error: When using --best or --new or --search, ')
    print ('--subreddit must be used.')

    sys.exit()

# Just to color stuff around.
MyPrint = Print()

# --dry-run: for testing. NOTHING will be posted to reddit.
if OPT_DRY_RUN:
        MyPrint.alert('[+] Dry run mode. Nothing will be altered or posted.')

# Treating options.
# --best
if OPT_BEST:
    reddit = praw_login(BOT_NAME)

    new_timestamp = reddit_calc_timestamp_best(
            reddit, OPT_SUBREDDIT, limit_new=30)

    MyPrint.warn('[+] BEST time to post in {0} : {1}'.format(
        OPT_SUBREDDIT, datetime.fromtimestamp(new_timestamp)))

    sys.exit()

# --new and --search
if OPT_NEW != None or OPT_SEARCH != None:
    reddit = praw_login(BOT_NAME)

    new_or_search = (OPT_NEW != None)

    MyPrint.warn('[+] Getting {0} new posts of : {1}'.format(
        OPT_NEW, OPT_SUBREDDIT))

    if OPT_SEARCH:
        LIMIT_POSTS = 30
    else:
        LIMIT_POSTS = int(OPT_NEW)

    reddit_get_posts(reddit, new_or_search, OPT_SUBREDDIT, OPT_SEARCH, limit_new=LIMIT_POSTS)

    sys.exit()

# Database should be the name of the sqlite3 file.
DATABASE_NAME='reddit.db'

# in case of a dry run create a dumb database
if OPT_DRY_RUN:
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
if OPT_DRY_RUN:
    SLEEP_BETWEEN_POSTS = 10
    SLEEP_LOOP          = 10
    TIME_POST_SAME_SUB  = 120 

while True:
    praw_renew_time = praw_renew_time % PRAW_RENEW_AUTH

    if praw_renew_time == 0:
        reddit = praw_login(BOT_NAME)

    if OLDMTIME != os.path.getmtime(POST_FILE):
        POSTS_LIST = read_post_file(POST_FILE)
        OLDMTIME = os.path.getmtime(POST_FILE)

        RDB.update(POSTS_LIST)

    show_info(MyPrint, RDB)

    FLAG_LOOP_WAIT = True

    # All posts that weren't posted yet (status not equal to posted)
    available_posts = RDB.select_field('*', 'status', 'posted', notEqual=True)
    
    # Execute the --command-after when everypost is "posted"
    if OPT_CMD_AFTER != None and len(available_posts) == 0:
        os.system(OPT_CMD_AFTER)
        # Execute only once.
        OPT_CMD_AFTER = None

    if OPT_QUIT and len(available_posts) == 0:
        MyPrint.alert('[+] Quitting...')
        sys.exit(0)

    for t in available_posts:
        (key, status, schedule, subreddit, title, url, timestamp) = t

        actual_timestamp = time.time()

        if status == 'queue':
            # This value can be modified in the if/elif chain and will
            # be updated after.
            new_timestamp = actual_timestamp

            # "best" schedule
            if schedule == 'best':
                if OPT_DRY_RUN:
                    new_timestamp = time.time() + DRY_RUN_BEST_TIME
                else:
                    new_timestamp = reddit_calc_timestamp_best(reddit, subreddit, limit_new=30)

                # A "best" post must be at least 2h older than the most recent post for
                # that sub.
                query = 'select MAX(timestamp) from reddit where subreddit=? and status!=?'
                query_r = RDB.select(query, (subreddit, 'queue'))
                t_timestamp = query_r[0][0]
                
                if t_timestamp != None and (actual_timestamp - t_timestamp) < TIME_POST_SAME_SUB:
                    new_timestamp += TIME_POST_SAME_SUB
                    MyPrint.event('[+] Delaying schedule post {0} for {1}.'.format(title, subreddit))
                    RDB.update_field(key, 'status', 'skip')
                else:
                    RDB.update_field(key, 'status', 'waiting')
            # "follow" schedule
            elif schedule == 'follow':
                # "follow" as first post should act like anytime.
                if key == 1:
                    MyPrint.event('[+] "Follow" post changed to "anytime": "{0}"'.format(title))
                    RDB.update_field(key, 'status', 'anytime')
                else:
                    RDB.update_field(key, 'status', 'ignored')
            # "+t[smhd]" schedule
            elif schedule[0] == '+':
                regexres = re.search('^\+([0-9]+)([smhd])$', schedule)
                time_seconds = to_seconds(regexres.group(1), regexres.group(2))

                #new_timestamp = actual_timestamp + time_seconds
                new_timestamp += time_seconds

                RDB.update_field(key, 'status', 'waiting')
            # "anytime" schedule
            elif schedule == "anytime":
                RDB.update_field(key, 'status', 'waiting')
                #MyPrint.alert('[+] No update. A post for r/'+subreddit+' is already scheduled.')

            # Update timestamp for a queue post.
            RDB.update_field(key, 'timestamp', new_timestamp)
        elif status == 'waiting' and actual_timestamp > timestamp:
            MyPrint.alert('[+] Posted in {0} : "{1}"'.format(subreddit, title))
            if OPT_DRY_RUN == False:
                reddit_submit(reddit, subreddit, title, url)
                pass

            RDB.update_field(key, 'status', 'posted')

            # Wake up "follow" posts
            query = 'select status,schedule from reddit where id=?'
            key_next = key + 1
            while True:
                t_follow = RDB.select(query, (key_next,))

                if len(t_follow) > 0:
                    t_status, t_schedule = t_follow[0]

                    if t_status == 'ignored' and t_schedule == 'follow':
                        # Just make sure that the follow post has
                        # timestamp less than the above post.
                        RDB.update_field(key_next, 'status', 'waiting')
                        RDB.update_field(key_next, 'timestamp', timestamp)

                        # Don't need to "wait" the main loop.
                        FLAG_LOOP_WAIT = False
                    else:
                        break
                else:
                    break

                key_next += 1

            countdown(MyPrint, '[+] Sleep time between posting. Waiting...', SLEEP_BETWEEN_POSTS)
        elif status == 'skip' and actual_timestamp > timestamp:
            # Time to wake up and be back to queue.
            MyPrint.event('[+] SKIP post status changed to QUEUE. {0} in {1}'.format(title, subreddit))
            RDB.update_field(key, 'status', 'queue')

    if FLAG_LOOP_WAIT:
        countdown(MyPrint, 'Loop waiting...', SLEEP_LOOP)
        praw_renew_time += SLEEP_LOOP
    RDB.show()
