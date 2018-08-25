#!/usr/bin/env python3

import argparse
import json
import collections
import logging
import sys
import pathlib
import praw

def setup_logging(args):
  log_level = getattr(logging, args.log_level, None)
  logging.basicConfig(level = log_level)

parser = argparse.ArgumentParser(description = "Fetch the newest 100 posts from a subreddit and print top 10 submitters")
parser.add_argument('subreddit', metavar = 'subreddit', nargs = '+', help = 'the subreddit to get new posts from')
parser.add_argument('--log', dest = 'log_level', default = 'ERROR', type = str.upper, choices = ['DEBUG', 'INFO', 'WARN', 'ERROR'], help = 'set the logging level')
parser.add_argument('--cache', dest = 'cache_response', action = 'store_true', default = False, help = 'store the response from reddit in a file for later use')
parser.add_argument('--use-cache', dest = 'use_cache', action = 'store_true', default = False, help = 'use a previously stored response instead of retrieving posts from reddit')
parser.add_argument('--user-agent', dest = 'user_agent', help = 'user agent override')
parser.add_argument('--top', dest = 'top', metavar = 'n', default = 10, type = int, help = 'top n submitters to show')
parser.add_argument('--fetch', dest = 'fetch', metavar = 'n', default = 100, type = int, help = 'fetch n posts (max 100)')
args = parser.parse_args(sys.argv[1:])
setup_logging(args)

if args.user_agent:
  user_agent_str = args.user_agent
elif not args.use_cache:
  try:
    user_agent_path = './.secrets/user_agent.txt'
    with open(user_agent_path) as f:
      user_agent_str = f.readline().replace('\n', '')
  except FileNotFoundError:
    print('No ./secrets/user_agent.txt found. Put an agent string in there or specify --user-agent')
    exit()
  try:
    praw_secret_path = './.secrets/praw.json'
    with open(praw_secret_path) as f:
      praw_secret = json.load(f)
      if logging.getLogger('root').isEnabledFor(logging.INFO):
        for key, val in praw_secret.items():
          if key == 'password' or key == 'client_secret': val = '******'
          logging.info('%s: %s', key, val)
  except FileNotFoundError:
      print('No ./secrets/praw.json found. See ./secrets/praw.sample.json for example')
      exit()

def save_to_file(filename, json_str):
  pathlib.Path('cached').mkdir(parents = True, exist_ok = True)
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path, 'w') as f:
    f.write(json_str)

def fetch_newest_posts_from_subreddit(subreddit, fetch_count, reddit_client):
  post_url = '/r/{}/new?limit={}'
  return reddit_client.request('GET', post_url.format('+'.join(subreddit), fetch_count))

def get_posts_from_file(filename):
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path) as f:
    return f.read()

subreddit = args.subreddit
fetch_count = min(args.fetch, 100)

if args.use_cache:
  try:
    response = json.loads(get_posts_from_file(subreddit))
    print('Using cached posts from ./cached/{}.json'.format(subreddit))
  except FileNotFoundError:
    print('Cached file', './cached/{}.json'.format(subreddit), 'does not exist')
    print('Use --cache parameter instead to retrieve posts from', subreddit)
    exit()
else:
  logging.info('using User-Agent: %s', user_agent_str)

  print('Fetching newest', fetch_count, 'posts from', ', '.join(subreddit))
  reddit_client = praw.Reddit(site_name = "DEFAULT", user_agent = user_agent_str, **praw_secret)
  response = fetch_newest_posts_from_subreddit(subreddit, fetch_count, reddit_client)
  if args.cache_response:
    print('Saving posts to ./cached/{}.json'.format(subreddit))
    save_to_file(subreddit, json.dumps(json_str))

try:
  posts = response['data']['children']
  subreddit_posts = collections.Counter([post['data']['subreddit'] for post in posts])
  authors = collections.Counter([post['data']['author'] + '|' + post['data']['subreddit'] for post in posts])
  for subreddit_post in subreddit_posts.most_common():
    print("{}: {}".format(subreddit_post[0], subreddit_post[1]))
  print('Total posts:', len(posts))

  print()
  print('Users with most submissions across', ', '.join(subreddit))

  for author in authors.most_common(args.top):
    print("{}: {}".format(author[0], author[1]))
except Exception as e:
  logging.error(e)
