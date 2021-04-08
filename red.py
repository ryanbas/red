#!/usr/bin/env python3

import argparse
import collections
import json
import logging
import pathlib
import pickle
import praw
import sys
import time

class SimpleSubmission:
  def __init__(self, redditor, subreddit):
    self.author = '[deleted]' if redditor is None else redditor.name
    self.subreddit = subreddit.display_name

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
  parser.add_argument('--stream-time', dest = 'stream_time', metavar = 'n', default = 5, type = int, help = 'stream posts for n seconds')

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
      logging.error('No ./.secrets/user_agent.txt found. Put an agent string in there or specify --user-agent')

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
        logging.warning('No ./secrets/praw.json found. See ./secrets/praw.sample.json for example')

  return None

def create_reddit_client(user_agent, secret):
  logging.debug('Using User-Agent: %s', user_agent)
  if secret == None:
    return praw.Reddit(site_name = 'DEFAULT', user_agent = user_agent)
  else:
    return praw.Reddit(site_name = 'DEFAULT', user_agent = user_agent, **secret)

def gen_file_path(subreddit_list):
  filename = '-'.join(sorted(subreddit_list))
  return 'cached/{}.pickle'.format(filename)

def save_submissions_to_file(subreddit_list, submissions):
  pathlib.Path('cached').mkdir(parents = True, exist_ok = True)
  file_path = gen_file_path(subreddit_list)
  logging.info('Saving posts to {}'.format(file_path))
  with open(file_path, 'wb') as f:
    f.write(pickle.dumps(submissions))

def read_submissions_from_file(subreddit_list):
  try:
    file_path = gen_file_path(subreddit_list)
    logging.info('Using cached posts from {}'.format(file_path))
    with open(file_path, 'rb') as f:
      return pickle.loads(f.read())
  except FileNotFoundError:
    logging.error('Cached file {} does not exist'.format(file_path))
    logging.error('Use --cache parameter instead to retrieve posts from {}'.format(', '.join(subreddit_list)))

  return []

def fetch_newest_posts_from_subreddits(reddit_client, subreddit_list, fetch_count):
  subreddit = reddit_client.subreddit('+'.join(subreddit_list))
  return subreddit.new(limit = fetch_count)

def top_posters(args, reddit_client, subreddit_list, fetch_count, topn):
  if args.use_cache:
    submissions = read_submissions_from_file(subreddit_list)
  else:
    response = fetch_newest_posts_from_subreddits(reddit_client, subreddit_list, fetch_count)
    submissions = [SimpleSubmission(submission.author, submission.subreddit) for submission in response]
    if args.cache_response:
      save_submissions_to_file(subreddit_list, submissions)

  subreddit_counter = collections.Counter([submission.subreddit for submission in submissions])
  for subreddit in subreddit_counter.most_common():
    logging.info('{}: {}'.format(subreddit[0], subreddit[1]))
  logging.info('Total posts: {}'.format(len(submissions)))

  authors = collections.Counter([submission.author + '|' + submission.subreddit for submission in submissions])
  logging.info('Users with most submissions across {}'.format(', '.join(subreddit_list)))
  for author in authors.most_common(topn):
    logging.info('{}: {}'.format(author[0], author[1]))

def stream(args, reddit_client, subreddit_list):
  logging.info('Will stream {} for {} seconds'.format(', '.join(subreddit_list), args.stream_time))

  stream = reddit_client.subreddit('+'.join(subreddit_list)).stream.submissions()
  start = time.time()
  for submission in stream:
    s = SimpleSubmission(submission.author, submission.subreddit)
    if not submission.over_18:
      reddit_url = 'https://reddit.com{}'.format(submission.permalink)
      print('{} on {}: {} \n\t{}\n\t{}\n'.format(s.author, s.subreddit, submission.title, reddit_url, submission.url))
    now = time.time()
    if now - start > args.stream_time:
      break


def main(argv):
  try:
    args = parse_args(argv[1:])

    setup_logging(args)

    if not args.use_cache:
      user_agent = get_user_agent(args)
      praw_secret = get_praw_secret(args)
      reddit_client = create_reddit_client(user_agent, praw_secret)
    else:
      reddit_client = None

    if args.action == 'top_posters':
      top_posters(args, reddit_client, args.subreddit_list, args.fetch, args.topn)
    elif args.action == 'stream':
      stream(args, reddit_client, args.subreddit_list)
  except Exception as e:
    logging.exception(e)

if __name__ == '__main__':
    main(sys.argv)