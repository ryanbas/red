# red.py

Repository created to play around with the reddit api.

## Requirements
* python 3
* praw (install using pip3 install praw)

## Usage
* Update the .secrets/praw.sample.json file and save to .secrets/praw.json with your own api client id and secret. See https://www.reddit.com/prefs/apps/ and register a script to get an id and secret of your own
* Alternatively, use a praw.ini file and set these values in the [DEFAULT] section
* Create a .secrets/user_agent.txt file to use as your user agent when accessing the api. Optionally, specify --user-agent on the command line

Run with ./red.py announcements to fetch the newest 100 posts from announcements and print the top 10 submitters.

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
