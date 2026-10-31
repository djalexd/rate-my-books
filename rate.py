import os
import sys
import argparse
import time
import dropbox
import json
from recommender.goodreads import get_best_rating

try:
    access_token = os.environ['ACCESS_TOKEN']
except KeyError:
    print('No ACCESS_TOKEN environment var specified')
    sys.exit(1)

parser = argparse.ArgumentParser(description='')
parser.add_argument('--path', help='Specifies the path to locate files in Dropbox')
parser.add_argument('--ratings_path', help='Specified the local path to store/sync ratings with Dropbox file metadata. This is a JSON file')
parser.add_argument('--limit', type=int, help='Limit the number of books to rate')
args = parser.parse_args()
path = args.path
ratings_path = args.ratings_path
limit = args.limit

ratings_and_books = []
dbx = dropbox.Dropbox(access_token)

def list_dropbox_folder(path, cursor=None, first=True):
    if first:
        response = dbx.files_list_folder(path = path)
        return response.entries + list_dropbox_folder(path, cursor=response.cursor, first=False)
    else:
        if cursor:
            response = dbx.files_list_folder_continue(cursor)
            if len(response.entries):
                return response.entries + list_dropbox_folder(path, cursor=response.cursor, first=False)
            else:
                return response.entries
        else:
            return []

valid_books = [book for book in list_dropbox_folder(path = path) if '.mobi' in book.name]
if limit and limit > 0:
    print('Limiting to %d out of %d books' % (limit, len(valid_books)))
    valid_books = valid_books[:limit]
else:
    print(f'Checking ratings for {len(valid_books)} books')
for book in valid_books:
    name = book.name[:-5]
    rating, counts = get_best_rating(name)
    print('%s - %s' % (name, rating))
    ratings_and_books.append({
        'name': name,
        'path': book.path_display,
        'rating': rating,
        'ratings_count': counts
    })
    time.sleep(1)

print(json.dumps(ratings_and_books))

print(f'Found & rated {len(valid_books)} books')

if ratings_path:
    with open(ratings_path, 'w') as fd:
        fd.write(json.dumps(ratings_and_books))
        print(f'Stored {len(ratings_and_books)} ratings at {ratings_path}')
