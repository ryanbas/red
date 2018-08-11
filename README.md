# red.py

Repository created to play around with the reddit api.

## Requirements
* python 3

## Usage
Create a .secrets/user_agent.txt file to use as your user agent when accessing the api. Optionally, specify --user-agent on the command line.

Run with ./red.py announcements to fetch the newest 100 posts from news and print the top 10 submitters.

Replace announcements with the subreddit of your choosing.

## Detailed Usage

```
usage: red.py [-h] [--log {DEBUG,INFO,WARN,ERROR}] [--cache] [--use-cache]
              [--user-agent USER_AGENT]
              subreddit

Fetch the newest 100 posts from a subreddit and print top 10 submitters

positional arguments:
  subreddit             the subreddit to get new posts from

optional arguments:
  -h, --help            show this help message and exit
  --log {DEBUG,INFO,WARN,ERROR}
                        set the logging level
  --cache               store the response from reddit in a file for later use
  --use-cache           use a previously stored response instead of retrieving
                        posts from reddit
  --user-agent USER_AGENT
                        user agent override
```
