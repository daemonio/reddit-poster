# reddit-poster
Python scripts to schedule posting in reddit. It includes a simple heuristic to schedule the best time to post.

# How to use

1) Run `poster.py` and wait. The scripts watches the file `postfile.txt` for new posts.
2) Add your posts to `postsfile.txt` using this sintaxe:

    subreddit\_name\~title of the post\~link of the post\~schedule

symbol "\~" is the field separator and "schedule" can be:

    best    : heuristic to decide the best time to post.
    anytime : post as soon as possible
    follow  : post after the the post above in the file

Example:

    sub1\~title\_1\~gfycat\_1\~best
    sub2\~title\_2\~gfycat\_2\~follow
    sub3\~title\_3\~gfycat\_3\~anytime
