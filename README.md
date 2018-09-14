# rate-my-books
A very simple python script that loads books from a Dropbox location and figures out their rating

## usage
Before starting the script, you'll need the following:
* Create a Dropbox app, thus obtaining an api token
* Create a GoodReads account & app, thus obtaining an api token
* install dependencies `pip install -r requirements.txt [--user]`

Execute the `rate.py` script to extract books & ratings:
`ACCESS_TOKEN=<dropbox token> GOODREADS_APIKEY=<goodreads apikey> python rate.py --path <path_in_dropbox>`

Script goes over each book found (file with `.mobi` extension) and fetches the rating. It outputs each
book on a single line, but at the end it outputs a json that can be read using `viewer.py`

Execute the `viewer.py` script:
* removes some entries (no rating, too few ratings)
* can easily be extended to perform additional filtering
