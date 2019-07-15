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

    best    : heuristic to decide the best time to post.
    anytime : post as soon as possible
    follow  : post after some post -- the one above it in the `postfile.txt`.
    +t[smh] : tradicional schedule. Post after "t" time has passed.

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

# More on Schedules

To schedule a post you have 5 options: best, follow, anytime, +t. "Best" is explained below.
"Follow" submita a post after the post above it. "Anytime" is the same as "immediately"

"+t" is the tradicional time schedule. If you put +1h the post will be submitted after
one hour from current time. Suffixes are 's', 'h', 'd' for seconds, hours and days repectively.

# How "best" schedule work

The heuristic was created by observation. Most subs can only have a highly
upvoted post in a timeframe of 15 hours. That is, when a post is being
highly upvoted, new posts will not grow as much because of the algorithm.

Let's say r/pics have a post with 10k upvotes in 4 hours. If you post something
new it will rarely grow but if you post the same thing after 11 hours, the
post will get more karma -- or be the new "highly upvoted" post.

So the WORST time to post to a sub, if one wants as karma as possible, is
to post when a "highly upvoted" post is growing between its post time (also called created\_utc time)
and 15 hours.

In other words, the BEST time to post is to wait a "highly upvoted" post to get at least 15
hours old. Again, this is a heuristic so of course it can fail sometimes.

The calculation is simple. Being "score" the amount of upvotes, IF `created_utc`\* is below 15 hours AND
the division `score/created_utc` is above 100, which means 100 upvotes per hour -- the minimum rate for
being considered a "highly upvoted" THEN schedule the post to `(15 - created_utc)` hours from now.

The best time to post is to wait a "highly upvoted" post to get at least 15 hours old. Of course if there
is no "highly upvoted" at the moment the script will just post immediately. Also, if your post is competing
with new posts, any of these new posts can grow bigger than yours. This can't be avoided -- except to delay
the posting time even more, which the script doesn't do.

\* : In reality `created_utc` is in seconds, but as an example consider it as time in hours.

# Database 'reddit.db'

The DB is a file under sqlite3 format. Its schema is simple, just type:

    sqlite3 reddit.db '.schema'

To learn more about using sqlite3 in python just search it up in duckduckgo.

# search.py

This the reddit search engine in a script form. I use it before posting to avoid reposts.

    ./search.py natureismetal 'honey+badger+snake'
