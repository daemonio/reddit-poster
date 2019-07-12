# reddit-poster
Python scripts to schedule posting in reddit. It includes a simple heuristic to schedule the best time to post.

# How to use

1) Run `poster.py` and wait. The scripts watches the file `postfile.txt` for new posts.
2) Add your posts to `postsfile.txt` using this sintaxe:

    subreddit_name~title of the post~link of the post~schedule

symbol "\~" is the field separator and "schedule" can be:

    best    : heuristic to decide the best time to post.
    anytime : post as soon as possible
    follow  : post after the the post above in the file

Example:

    sub1~title_1~gfycat_1~best
    sub2~title_2~gfycat_2~follow
    sub3~title_3~gfycat_3~anytime

"title\_1" will be post to "sub1" when it is the best time to do so. Second
post will be delayed to be post after "title\_1" since we're using "follow"
schedule. "title\_3" will be post as soon as poosible to "sub3".

# How "best" schedule work

The heuristic was created by observation. Most subs can only have a highly
upvoted post in a timeframe of 15 hours. That is, when a post is being
highly upvoted, new posts will not grow as much because of the algorithm.

Let's say r/pics have a post with 10k upvotes in 4 hours. If you post something
new it will rarely grow but if you post the same thing after 15 hours, the
post will get more karma -- or be the new "highly upvoted" post of the time.

So the WORST time to post to a sub, if one wants as karma as possible, is
to post when a "highly upvoted" post is growing between its post time (also called created\_utc time)
and 15 hours.

In other words, the BEST time to post is to wait a "highly upvoted" post to get 15
hours old. Again, this is a heuristic so of course it can fail sometimes.

The calculation is simple, IF `score/created\_utc` is above 100 which means 100 upvotes
per hour, the minimum rate for being considered a "highly upvoted" post THEN schedule the
post to (15 - created\_utc) hours from now.
