import os
import sys
import argparse
import dropbox

try:
    access_token = os.environ['ACCESS_TOKEN']
except KeyError:
    print('No ACCESS_TOKEN environment var specified')
    sys.exit(1)

parser = argparse.ArgumentParser(description='')
parser.add_argument('--path', help='Specifies the path to locate files in Dropbox')
args = parser.parse_args()
path = args.path

dbx = dropbox.Dropbox(access_token)
valid_books = [book for book in dbx.files_list_folder(path = path).entries if '.mobi' in book.name]
for book in valid_books:
    print book.name
print 'Found %d books' % len(valid_books)