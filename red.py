#!/usr/bin/env python3

from collections import defaultdict
from enum import Enum, auto
from itertools import groupby

import argparse
import collections
import json
import logging
import pathlib
import pickle
import praw
import sys
import time

class PostTag(Enum):
  SELF_TO_USER = auto()
  USER_TO_USER = auto()
  NORMAL_POST_ON_OVER_18 = auto()
  ON_OVER_18 = auto()
  OVER_18 = auto()
  ON_NORMAL = auto()
  UNKNOWN = auto()

class SimpleSubmission:
  def tag_submission(self, subreddit, submission):
    tags = []
    subreddit_split = self.subreddit.split('_', maxsplit = 1)

    if self.subreddit == self.author:
      tags.append(PostTag.SELF_TO_USER)

    if subreddit_split[0] == 'u':
      if subreddit_split[1] == self.author:
        tags.append(PostTag.SELF_TO_USER)
      else:
        tags.append(PostTag.USER_TO_USER)

    if subreddit.over18:
      tags.append(PostTag.ON_OVER_18)
    else:
      tags.append(PostTag.ON_NORMAL)

    if submission.over_18:
      tags.append(PostTag.OVER_18)
    else:
      if subreddit.over18:
        tags.append(PostTag.NORMAL_POST_ON_OVER_18)

    if len(tags) == 0:
      tags.append(PostTag.UNKNOWN)

    return tags

  def __init__(self, redditor, subreddit, submission):
    self.author = '[deleted]' if redditor is None else redditor.name
    self.subreddit = subreddit.display_name
    self.title = submission.title
    self.reddit_url = 'https://reddit.com{}'.format(submission.permalink)
    self.target_url = submission.url
    self.submission_tags = self.tag_submission(subreddit, submission)

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
    submissions = [SimpleSubmission(submission.author, submission.subreddit, submission) for submission in response]
    if args.cache_response:
      save_submissions_to_file(subreddit_list, submissions)

  subreddit_counter = collections.Counter([submission.subreddit for submission in submissions])
  for subreddit in subreddit_counter.most_common():
    print('{}: {}'.format(subreddit[0], subreddit[1]))
  print('Total posts: {}'.format(len(submissions)))

  authors = collections.Counter([submission.author + '|' + submission.subreddit for submission in submissions])
  print('Users with most submissions across {}'.format(', '.join(subreddit_list)))
  for author in authors.most_common(topn):
    print('{}: {}'.format(author[0], author[1]))


def all_tags_match(post_tags, search_tags):
  return all(tag in post_tags for tag in search_tags)

def all_tags_match_exact(post_tags, search_tags):
  return len(search_tags) == len(post_tags) and all_tags_match(post_tags, search_tags)

def is_interesting(post_tags):
  UNKNOWN = [PostTag.UNKNOWN]
  NORMAL_POST = [PostTag.ON_NORMAL]
  OVER_18 = [PostTag.ON_OVER_18, PostTag.OVER_18]

  if all_tags_match_exact(post_tags, UNKNOWN):
    return False
  if all_tags_match_exact(post_tags, NORMAL_POST):
    return False
  if all_tags_match(post_tags, OVER_18):
    return False

  return True

def stream(args, reddit_client, subreddit_list):
  logging.info('Will stream {} for {} seconds'.format(', '.join(subreddit_list), args.stream_time))

  stream = reddit_client.subreddit('+'.join(subreddit_list)).stream.submissions()
  start = time.time()
  submission_summary = defaultdict(list)
  for submission in stream:
    s = SimpleSubmission(submission.author, submission.subreddit, submission)

    summary_key = '-'.join([str(t.value) for t in s.submission_tags])
    summary = submission_summary[summary_key]
    summary.append(s)
    submission_summary[summary_key] = summary

    now = time.time()
    if now - start > args.stream_time:
      break

  total = 0
  skipped_num = 0
  skipped_tags = []
  keys = sorted(submission_summary.keys())
  for key in keys:
    submissions = submission_summary[key]
    num_submissions = len(submissions)
    post_tags = [PostTag(int(x)) for x in key.split('-')]
    post_tags_display = '/'.join([pt.name for pt in post_tags])

    if is_interesting(post_tags):
      print()
      print('{}: {}'.format(post_tags_display, num_submissions))
      for groups in groupby(submissions, lambda s: s.subreddit):
        print(groups[0])
        for submission in groups[1]:
          print('\t{}: {}\n\t{}'.format(submission.author, submission.title, submission.reddit_url))
    else:
      skipped_tags.append('{}: {}'.format(post_tags_display, num_submissions))
      skipped_num = skipped_num + num_submissions

    total = total + num_submissions

  print()
  print('Skipped: {}'.format(skipped_num))
  for skipped in skipped_tags:
    print('\t{}'.format(skipped))
  print('Total  : {}'.format(total))


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