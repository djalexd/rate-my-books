import os
import sys
import argparse
import time
import dropbox
import requests
import xml.etree.ElementTree
import json

try:
    access_token = os.environ['ACCESS_TOKEN']
except KeyError:
    print('No ACCESS_TOKEN environment var specified')
    sys.exit(1)

try:
    goodreads_token = os.environ['GOODREADS_APIKEY']
except KeyError:
    print('No GOODREADS_APIKEY environment var defined')
    sys.exit(1)

def get_best_rating(name):
    try:
        r = requests.get('https://www.goodreads.com/search/index.xml', params={'key': goodreads_token, 'q': name}, timeout=5)
    except Exception:
        # just a simple way to reprocess later
        return '-1.0', 0
    root = xml.etree.ElementTree.fromstring(r.content)
    items = root.findall('./search/results/work')
    items_sorted_by_ratings = sorted(items, key=lambda x: int(x.find('ratings_count').text), reverse=True)
    if items_sorted_by_ratings:
        return items_sorted_by_ratings[0].find('average_rating').text, int(items_sorted_by_ratings[0].find('ratings_count').text)
    else:
        return '0.0', 0

parser = argparse.ArgumentParser(description='')
parser.add_argument('--path', help='Specifies the path to locate files in Dropbox')
parser.add_argument('--ratings_path', help='Specified the local path to store/sync ratings with Dropbox file metadata. This is a JSON file')
args = parser.parse_args()
path = args.path
ratings_path = args.ratings_path

ratings_and_books = []

dbx = dropbox.Dropbox(access_token)
valid_books = [book for book in dbx.files_list_folder(path = path).entries if '.mobi' in book.name]
for book in valid_books:
    name = book.name[:-5]
    rating, counts = get_best_rating(name)
    print u'%s - %s' % (name, rating)
    ratings_and_books.append({
        'name': name,
        'path': book.path_display,
        'rating': float(rating),
        'ratings_count': counts
    })
    time.sleep(1)

print json.dumps(ratings_and_books)

print 'Found & rated %d books' % len(valid_books)