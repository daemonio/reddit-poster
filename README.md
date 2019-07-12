# reddit-poster
Python scripts to schedule posting in reddit. It includes a simple heuristic to schedule the best time to post.

# How to use

1) Run `poster.py` and wait. The scripts watches the file `postfile.txt` for new posts.
2) Add your posts to `postfile.txt` using this sintaxe:

    subreddit_name~title of the post~link of the post~schedule

symbol "\~" is the field separator and "schedule" can be:

    best    : heuristic to decide the best time to post.
    anytime : post as soon as possible
    follow  : post after the the post above in the file

Example:

    dankmemes~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~best
    pics~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~follow
    dank_memes~The real firework~https://i.redd.it/k9bzcs5gou931.jpg~anytime

First post is "best" so it will be post when it's the time to do so (see below). Second
Second post will be delayed to be posted after the first one. This is what follow means.
The third post will be posted when the main loop hit it, that is, as soon as possible.

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

The calculation is simple. Being "score" the amount of upvotes, IF the division `score/created_utc`
is above 100 which means 100 upvotes per hour, the minimum rate for being considered a
"highly upvoted" post THEN schedule the post to `(15 - created_utc)` hours from now. The best
time to post is to wait a "highly upvoted" post to get at least 15 hours old. Of course ff there
is no "highly upvoted" at the moment just post right away.

# Database 'reddit.db'

The DB is a file under sqlite3 format. Its schema is simple, just type:

    sqlite3 reddit.db '.schema'

To learn more about sqlite3 on python to search it up in duckduckgo.
