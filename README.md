# reddit-poster
Python script to schedule a post in reddit. It includes a simple heuristic to schedule the best time to post.

# What to install

`pip` any of these bad boys if any is missing:

    import praw
    import sqlite3
    from colorama import Fore, Back, Style

# Praw config

I put my PRAW configuration in `~/.config/praw.ini`. Here's a example of the file:

    [mybot]
    client_id=
    client_secret=
    password=
    username=

Fill the missing values with your own configuration. Don't forget to set the `BOT_NAME`
in `poster.py` and in `search.py` (for this example `BOT_NAME='mybot'`)

# How to use

1) Run `./poster.py` and wait. The scripts watches the file `postfile.txt` for new posts.
This script will run infinitely. Hit `ctrl+c` whenever you like, just make sure that there's
no pending posts.

2) Add your posts to `postfile.txt` using this syntaxe:

    subreddit_name\~title of the post\~link of the post\~schedule

symbol "\~" is the field separator and "schedule" can be:

    best     : heuristic to decide the best time to post.
    anytime  : post as soon as possible
    follow   : post after some post -- the one above it in the `postfile.txt`.
    +t[smhd] : traditional scheduling. Post after "t" time have passed.

Example of `postfile.txt`:

    dankmemes~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~best
    pics~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~follow
    dank_memes~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~anytime
    funny~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~+5h

First post is "best" so it will be posted when it's the best time to do so (see below).
Second post will be delayed to be posted after the first one. This is what "follow" means.
The third post will be posted when the main loop hits it, that is, as soon as possible.
Finally the last post will be submitted after 5 hours from current time.

Let's say the first post will be schedule 4 hours from here. The posting sequence will
be: third post immediately, first post after 4 hours, second post after 4h and 2 minutes and
the last post after 5h. Basically: 3 -> 1 -> 2 -> 4.

Obs: There's a delay of 2 minutes between posts. This is to avoid "spam" errors from PRAW.

# Dry run

Pass the --dry-run option to tell the script to not update anything or post anything. This option
is for testing purposes.

    ./poster.py --dry-run

Nothing will be modified or posted to reddit except the creation of a database named
`redditdryrun.db`. You can also use "fake" subreddit names here to test the script like
"sub1", "sub2", etc.

# More on Schedules

To schedule a post you have 4 options: best, follow, anytime, +t[smhd]. "Best" is explained below.
"Follow" submit a post after the post above it. "Anytime" is the same as immediately.

"+t[smhd]" is the traditional time scheduling. If you put +1h the post will be submitted after
one hour from current time. Suffixes are 's', 'm', 'h', 'd' for seconds, minutes, hours and
days, repectively.

# How "best" schedule work

The heuristic was created by observation. Most subs can only have a highly
upvoted post in a timeframe of 15 hours. That is, when a post is being
highly upvoted, new posts will not grow as much because of the algorithm.

Let's say r/pics have a post with 10k upvotes in 4 hours. If you post something
new it will rarely grow but if you post the same thing after 11 hours, the
post will get more karma -- or be the new "highly upvoted" post.

So the WORST time to post to a sub, if one wants more karma as possible, is
to post when a "highly upvoted" post is growing between its post time (also called created\_utc time)
and 15 hours.

In other words, the BEST time to post is to wait a "highly upvoted" post to be at least 15
hours old. Again, this is a heuristic so of course it can fail sometimes.

The calculation is simple. Being "score" the amount of upvotes, IF `created_utc` [1] is below 15 hours AND
the division `score/created_utc` is above 100 [2], which means 100 upvotes per hour -- the minimum rate for
being considered a "highly upvoted" THEN schedule the post to `(15 - created_utc)` hours from now.

The best time to post is to wait a "highly upvoted" post to get at least 15 hours old. Of course if there
is no "highly upvoted" at the moment the script will just post immediately. Also, if your post is competing
with new posts, any of these new posts can grow bigger than yours. This can't be avoided -- except to delay
the posting time even more, which the script doesn't do.

[1] : In reality `created_utc` is in seconds, but as an example consider it as time in hours.

[2] : This value can vary between subs. The 100 value is kinda low so it can produce many "false-postives",
that is, posts that seem to be highly upvoted but they're not. If the sub averages 5k or lower upvotes
for the most upvoted post in a day, the 100 value works great. Big subs that averages 20k or more, this
value must be changed accordingly.

# Options

    --dry-run                 : Execute script as a test. No post will be submitted to reddit.
    --quit-run                : Quit script when everything is submitted.
    --command-after=COMMAND   : Command to execute (only once) when everything is submitted.
                                Useful for "reboot".
    --subredit=SUBREDDIT      : Set the subreddit that the options will operate.
    --get-best                : Print the "best" time to post in --subreddit.
    --get-new  N              : Get the first N new posts of the --subreddit.
    --search=SEARCH           : Term to search in --subreddit.

Example:

    ./poster.py --subreddit natureismetal --search 'honey+badger+snake'
# Database 'reddit.db'

The DB is a file under sqlite3 format. Its schema is simple, just type:

    sqlite3 reddit.db '.schema'

To learn more about using sqlite3 in python just search it up in duckduckgo.

# search.py

This the reddit search engine in a script form. I use it before posting to avoid reposts.

    ./search.py natureismetal 'honey+badger+snake'
