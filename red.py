#!/usr/bin/env python3

import argparse
import json
import urllib.request, urllib.error, urllib.parse
import collections
import logging
import sys
import codecs
import pathlib

def setup_logging(args):
  log_level = getattr(logging, args.log_level, None)
  logging.basicConfig(level = log_level)

parser = argparse.ArgumentParser(description = "Get the newest 100 posts from a subreddit and print top 10 submitters")
parser.add_argument('subreddit', metavar = 'subreddit', help = 'the subreddit to get new posts from')
parser.add_argument('--log', dest = 'log_level', default = 'ERROR', type = str.upper, choices = ['DEBUG', 'INFO', 'WARN', 'ERROR'], help = 'set the logging level')
parser.add_argument('--cache', dest = 'cache_response', action = 'store_true', default = False, help = 'store the response from reddit in a file for later use')
parser.add_argument('--use-cache', dest = 'use_cache', action = 'store_true', default = False, help = 'use a previously stored response instead of retrieving posts from reddit')
parser.add_argument('--user-agent', dest = 'user_agent', help = 'user agent override')
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


def save_to_file(filename, json_str):
  pathlib.Path('cached').mkdir(parents = True, exist_ok = True) 
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path, 'w') as f:
    f.write(json_str)

def fetch_newest_posts_from_subreddit(subreddit, user_agent, after = ''):
  opener = urllib.request.build_opener()
  opener.addheaders = user_agent
  post_url = 'https://www.reddit.com/r/{}/new.json?limit=100'

  return decode_http_response(opener.open(post_url.format(subreddit) + '&after=' + after))

def decode_http_response(response):
  logging.debug(response.info())
  return codecs.getreader('UTF-8')(response)

def get_posts_from_file(filename):
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path) as f:
    return f.read()


subreddit = args.subreddit

if args.use_cache:
  try:
    json_str = get_posts_from_file(subreddit)
    print('Using cached posts from ./cached/{}.json'.format(subreddit))
  except FileNotFoundError:
    print('Cached file', './cached/{}.json'.format(subreddit), 'does not exist')
    print('Use --cache parameter instead to retrieve posts from', subreddit)
    exit()
else:
  logging.info('using User-Agent: %s', user_agent_str)
  user_agent = [('User-Agent', user_agent_str)]

  print('Fetching newest 100 posts from', subreddit, 'subreddit'.format(subreddit))
  posts_stream = fetch_newest_posts_from_subreddit(subreddit, user_agent)
  json_str = posts_stream.read()
  if args.cache_response:
    print('Saving posts to ./cached/{}.json'.format(subreddit))
    save_to_file(subreddit, json_str)

try:

  data = json.loads(json_str)

  data_children = data['data']['children']
  authors = collections.Counter([postdata['data']['author'] for postdata in data_children])
  print('Total posts: ' + str(len(data_children)))

  header = 'Users with most submissions in {}'.format(subreddit)
  print()
  print(header)
  print(''.join(['-' for x in header]))

  for author in authors.most_common(10):
    print(str(author[0]) + ": " + str(author[1]))
except Exception as e:
  logging.warn(e)
