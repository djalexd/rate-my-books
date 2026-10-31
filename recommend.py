"""Book recommendations from your read-list (an Obsidian directory) and your Dropbox library.

  python recommend.py taste              # best fits for your overall taste
  python recommend.py next               # builds on what you read recently
  python recommend.py add --title ... --author ... --rating 4
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import List

from recommender.model import NEXT, TASTE, Params, Pick
from recommender.readlist import add_entry
from recommender.service import recommend_books


def _print_picks(heading: str, picks: List[Pick]) -> None:
    print(f'\n{heading}')
    if not picks:
        print('  (none)')
    for i, pick in enumerate(picks, 1):
        b = pick.book
        rating = f' - {b.rating:.2f}' if b.rating else ''
        print(f'{i:2d}. {b.title}{f" ({b.author})" if b.author else ""}{rating}')
        if pick.reasons:
            print(f'      {"; ".join(pick.reasons)}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--readlist-dir', default=os.environ.get('READLIST_DIR'),
                        help='Obsidian directory with one note per read book (or set READLIST_DIR)')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in (TASTE, NEXT):
        p = sub.add_parser(name)
        p.add_argument('--ratings', type=Path, default=Path('ratings.json'), help='rate.py output for the library')
        p.add_argument('--cache', type=Path, default=Path('.cache/openlibrary.json'))
        p.add_argument('--library-picks', type=int, default=5)
        p.add_argument('--outside-picks', type=int, default=2)
        p.add_argument('--half-life', type=float, default=Params.half_life_days,
                       help='days after which a read counts half as much (next mode)')
    add = sub.add_parser('add', help='record a book you finished in the read-list')
    add.add_argument('--title', required=True)
    add.add_argument('--author')
    add.add_argument('--rating', type=float)
    add.add_argument('--date', type=date.fromisoformat, help='YYYY-MM-DD, defaults to today')
    args = parser.parse_args()

    if not args.readlist_dir:
        print('No read-list directory: pass --readlist-dir or set READLIST_DIR', file=sys.stderr)
        return 1
    readlist_dir = Path(args.readlist_dir).expanduser()
    if not readlist_dir.is_dir():
        print(f'Read-list directory does not exist: {readlist_dir}', file=sys.stderr)
        return 1

    if args.command == 'add':
        print(f'Read-list entry: {add_entry(readlist_dir, args.title, args.author, args.rating, args.date)}')
        return 0

    try:
        result = recommend_books(
            mode=args.command, readlist_dir=readlist_dir, ratings_path=args.ratings, cache_path=args.cache,
            library_picks=args.library_picks, outside_picks=args.outside_picks, today=date.today(),
            params=Params(half_life_days=args.half_life),
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print(f'{result.reads} books read, {result.library_size} in library '
          f'({result.library_without_subjects} without subject data)')
    _print_picks('From your library', result.library)
    _print_picks('From outside', result.outside)
    return 0


if __name__ == '__main__':
    sys.exit(main())
