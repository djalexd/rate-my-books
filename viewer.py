import os
import sys
import argparse
import json

parser = argparse.ArgumentParser(description='')
parser.add_argument('--ratings_path', help='Specified the local path to store/sync ratings with Dropbox file metadata. This is a JSON file')
args = parser.parse_args()
ratings_path = args.ratings_path

with open(args.ratings_path, 'r') as fd:
    rated_books = json.load(fd)

    sorted_books = sorted(rated_books, key=lambda b: b['rating'], reverse=True)
    for book in [b for b in sorted_books if b['rating'] > 0.0 and b['ratings_count'] > 100]:
        print '%s - %s (from %s)' % (book['name'], book['rating'], book['ratings_count']) 