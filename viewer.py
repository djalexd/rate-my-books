import os
import sys
import argparse
import json
import math

parser = argparse.ArgumentParser(description='')
parser.add_argument('--ratings_path', help='Specified the local path to store/sync ratings with Dropbox file metadata. This is a JSON file')
args = parser.parse_args()
ratings_path = args.ratings_path

with open(args.ratings_path, 'r') as fd:
    rated_books = json.load(fd)

    def adjust_rating(book_json): 
        if 'ratings_count' in book_json and book_json['ratings_count'] > 0:
            return 0.7 * book_json['rating'] + 0.3 * math.log(book_json['ratings_count'], 10)
        else:
            return book_json['rating']
    
    sorted_books = sorted(rated_books, key=adjust_rating, reverse=True)
    for index, book in enumerate([b for b in sorted_books if b['rating'] > 0.0]):
        print '%2d. %s - %.2f (from %s)' % (index, book['name'], adjust_rating(book), book['ratings_count']) 