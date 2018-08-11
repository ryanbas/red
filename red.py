#!/usr/bin/env python3

import argparse
import json
import urllib.request, urllib.error, urllib.parse
import collections
import logging
import sys
import codecs

user_agent = [('User-Agent', 'python:com.github.ryanbas.messin.around:v0.0.1 (by /u/ryanbas)')]

def saveToFile(filename, idx, jsonStr):
  f = open(filename + str(idx) + '.json', 'w')
  f.write(jsonStr)

def getPostsFromUrl(subreddit, after = ''):
  opener = urllib.request.build_opener()
  opener.addheaders = user_agent
  post_url = 'https://www.reddit.com/r/{}/new.json?limit=100'

  return decode_http_response(opener.open(post_url.format(subreddit) + '&after=' + after))

def getUserInfo(username):
  opener = urllib.request.build_opener()
  opener.addheaders = user_agent
  
  return decode_http_response(opener.open(user_url.format(username)))

def decode_http_response(response):
  logging.info(response.info())
  return codecs.getreader('UTF-8')(response)

def getPostsFromFile(filename, idx = ''):
  f = open(filename + str(idx) + '.json')
  return f.read()

def setup_logging(args):
  log_level = getattr(logging, args.log_level, None)
  logging.basicConfig(level = log_level)

parser = argparse.ArgumentParser(description = "Read stuff from reddit")
parser.add_argument('subreddit', metavar = 'S', help = 'the subreddit to get new posts from')
parser.add_argument('--log', dest = 'log_level', default = 'WARN', required = False, type = str.upper, choices = ['DEBUG', 'INFO', 'WARN', 'ERROR'])
args = parser.parse_args(sys.argv[1:])
setup_logging(args)

subreddit = args.subreddit
user_url = 'https://www.reddit.com/u/{}/about.json'

posts_stream = getPostsFromUrl(subreddit)
data = json.load(posts_stream)

data_children = data['data']['children']
authors = collections.Counter([postdata['data']['author'] for postdata in data_children])
print('Total posts: ' + str(len(data_children)))
for author in authors.most_common(10):
  print(str(author[0]) + ": " + str(author[1]))
