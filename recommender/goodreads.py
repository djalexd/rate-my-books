"""Goodreads search-page scraping, shared by rate.py."""
import logging
import re
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

HEADERS = {
    'Accept': 'text/html',
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
}
_RATING_PATTERN = re.compile(r"(\d+\.\d+)\s+avg rating\s+—\s+([\d,]+)\s+ratings")


def extract_rating_and_count(text: str) -> Tuple[Optional[float], Optional[int]]:
    match = _RATING_PATTERN.search(text)
    if not match:
        return None, None
    return float(match.group(1)), int(match.group(2).replace(',', ''))


def get_best_rating(name: str) -> Tuple[float, int]:
    """Rating and rating count of the first Goodreads search hit.

    Returns (-1.0, 0) when the request fails (so it can be retried later) and
    (0.0, 0) when nothing usable was found.
    """
    try:
        r = requests.get('https://www.goodreads.com/search', params={'q': name}, headers=HEADERS, timeout=5)
    except requests.RequestException as e:
        logging.error(f'Error fetching data from goodreads: {e}')
        return -1.0, 0
    soup = BeautifulSoup(r.text, 'html.parser')
    titles = soup.find_all('a', class_='bookTitle')
    ratings = soup.find_all('span', class_='minirating')
    if not titles or not ratings:
        return 0.0, 0
    rating, count = extract_rating_and_count(ratings[0].get_text(strip=True))
    if rating is None or count is None:
        return 0.0, 0
    return rating, count
