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

def parse_args(args):
  parent_parser = argparse.ArgumentParser(add_help=False)
  parent_parser.add_argument('--action', dest = 'action', default = 'top_posters', type = str, choices = ['top_posters', 'stream'], help = 'function of red to use')
  parent_parser.add_argument('--log', dest = 'log_level', default = 'INFO', type = str.upper, choices = ['DEBUG', 'INFO', 'WARN', 'ERROR'], help = 'set the logging level')
  parent_parser.add_argument('--user-agent', dest = 'user_agent', help = 'user agent override')

  parser = argparse.ArgumentParser(description = 'Fetch the newest 100 posts from subreddit(s) and print top 10 submitters', parents=[parent_parser])
  parser.add_argument('subreddit_list', metavar = 'subreddit_list', nargs = '+', help = 'the subreddit(s) to get new posts from')
  parser.add_argument('--cache', dest = 'cache_response', action = 'store_true', default = False, help = 'store the response from reddit in a file for later use')
  parser.add_argument('--use-cache', dest = 'use_cache', action = 'store_true', default = False, help = 'use a previously stored response instead of retrieving posts from reddit')
  parser.add_argument('--topn', dest = 'topn', metavar = 'n', default = 10, type = int, help = 'top n submitters to show')
  parser.add_argument('--fetch', dest = 'fetch', metavar = 'n', default = 100, type = int, help = 'fetch n posts (max 100)')

  return parser.parse_args(args)

def get_user_agent(args):
  if args.user_agent:
    return args.user_agent
  elif not args.use_cache:
    try:
      user_agent_path = './.secrets/user_agent.txt'
      with open(user_agent_path) as f:
        return f.readline().replace('\n', '')
    except FileNotFoundError:
      logging.error('No ./secrets/user_agent.txt found. Put an agent string in there or specify --user-agent')

  return None

def get_praw_secret(args):
  if not args.use_cache:
    try:
      praw_secret_path = './.secrets/praw.json'
      with open(praw_secret_path) as f:
        praw_secret = json.load(f)
        if logging.getLogger('root').isEnabledFor(logging.INFO):
          for key, val in praw_secret.items():
            if key == 'password' or key == 'client_secret': val = '******'
            logging.debug('%s: %s', key, val)
        return praw_secret
    except FileNotFoundError:
        logging.error('No ./secrets/praw.json found. See ./secrets/praw.sample.json for example')

  return None

def build_reddit_client(user_agent, secret):
  logging.debug('Using User-Agent: %s', user_agent)
  reddit_client = praw.Reddit(site_name = 'DEFAULT', user_agent = user_agent, **secret)

  return reddit_client

def save_to_file(filename, json_str):
  pathlib.Path('cached').mkdir(parents = True, exist_ok = True)
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path, 'w') as f:
    f.write(json_str)

def fetch_newest_posts_from_subreddits(subreddit_list, fetch_count, reddit_client):
  post_url = '/r/{}/new?limit={}'
  return reddit_client.request('GET', post_url.format('+'.join(subreddit_list), fetch_count))

def get_posts_from_file(filename):
  file_path = 'cached/{}.json'.format(filename)
  with open(file_path) as f:
    return f.read()

def top_posters(args, reddit_client, subreddit_list, fetch_count, topn):
  if args.use_cache:
    try:
      filename = '-'.join(subreddit_list)
      logging.info('Using cached posts from ./cached/{}.json'.format(filename))
      response = json.loads(get_posts_from_file(filename))
    except FileNotFoundError:
      logging.error('Cached file ./cached/{}.json'.format(filename) + 'does not exist')
      logging.error('Use --cache parameter instead to retrieve posts from {}'.format(filename))
      exit()
  else:
    response = fetch_newest_posts_from_subreddits(subreddit_list, fetch_count, reddit_client)
    if args.cache_response:
      filename = '-'.join(subreddit_list)
      logging.info('Saving posts to ./cached/{}.json'.format(filename))
      save_to_file(filename, json.dumps(response))

  posts = response['data']['children']
  subreddit_posts = collections.Counter([post['data']['subreddit'] for post in posts])
  authors = collections.Counter([post['data']['author'] + '|' + post['data']['subreddit'] for post in posts])
  for subreddit_post in subreddit_posts.most_common():
    logging.info('{}: {}'.format(subreddit_post[0], subreddit_post[1]))

  logging.info('Total posts: {}'.format(len(posts)))
  logging.info('Users with most submissions across {}'.format(', '.join(subreddit_list)))

  for author in authors.most_common(topn):
    logging.info('{}: {}'.format(author[0], author[1]))

def stream(args, reddit_client, subreddit_list):
  logging.info('Will stream {}'.format(', '.join(subreddit_list)))

def main(argv):
  try:
    args = parse_args(argv[1:])

    setup_logging(args)

    if not args.use_cache:
      user_agent = get_user_agent(args)
      praw_secret = get_praw_secret(args)
      reddit_client = build_reddit_client(user_agent, praw_secret)
    else:
      reddit_client = None

    if args.action == 'top_posters':
      top_posters(args, reddit_client, args.subreddit_list, min(args.fetch, 100), args.topn)
    elif args.action == 'stream':
      stream(args, reddit_client, args.subreddit_list)
  except Exception as e:
    logging.exception(e)

if __name__ == '__main__':
    main(sys.argv)