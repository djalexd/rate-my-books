"""Rate a Dropbox library and get book recommendations from an Obsidian read-list.

rate-my-books rate --path /books --ratings ratings.json   # needs ACCESS_TOKEN (Dropbox)
rate-my-books view --ratings ratings.json                 # library ranked by Goodreads rating
rate-my-books taste                                       # best fits for your overall taste
rate-my-books next                                        # builds on what you read recently
rate-my-books add --title ... --author ... --rating 4     # record a finished book
"""

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from rate_my_books.model import Mode, Params, Pick
from rate_my_books.rating import load_ratings, rate_library, save_ratings
from rate_my_books.readlist import add_entry
from rate_my_books.service import recommend_books
from rate_my_books.settings import Settings, SettingsError
from rate_my_books.viewer import adjusted_rating, ranked


def _print_picks(heading: str, picks: list[Pick]) -> None:
    print(f'\n{heading}')
    if not picks:
        print('  (none)')
    for i, pick in enumerate(picks, 1):
        b = pick.book
        rating = f' - {b.rating:.2f}' if b.rating else ''
        print(f'{i:2d}. {b.title}{f" ({b.author})" if b.author else ""}{rating}')
        if pick.reasons:
            print(f'      {"; ".join(pick.reasons)}')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='rate-my-books', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--env-file',
        type=Path,
        help='read ACCESS_TOKEN and READLIST_DIR from this file (default: .env if present); '
        'values like op://vault/item/field are read from 1Password',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    rate = sub.add_parser('rate', help='look up Goodreads ratings for the books in a Dropbox folder')
    rate.add_argument('--path', required=True, help='Dropbox folder with the books')
    rate.add_argument('--ratings', type=Path, default=Path('ratings.json'), help='where to store the ratings')
    rate.add_argument('--limit', type=int, help='only rate this many books')

    view = sub.add_parser('view', help='print the rated library, best first')
    view.add_argument('--ratings', type=Path, default=Path('ratings.json'))

    for mode in Mode:
        p = sub.add_parser(mode.value, help=f'recommend ({mode.value} mode)')
        p.add_argument(
            '--readlist-dir',
            help='Obsidian directory with one note per read book (or set READLIST_DIR)',
        )
        p.add_argument('--ratings', type=Path, default=Path('ratings.json'), help='output of `rate` for the library')
        p.add_argument('--cache', type=Path, default=Path('.cache/openlibrary.json'))
        p.add_argument('--library-picks', type=int, default=5)
        p.add_argument('--outside-picks', type=int, default=2)
        p.add_argument(
            '--half-life',
            type=float,
            default=Params.half_life_days,
            help='days after which a read counts half as much (next mode)',
        )

    add = sub.add_parser('add', help='record a book you finished in the read-list')
    add.add_argument('--readlist-dir')
    add.add_argument('--title', required=True)
    add.add_argument('--author')
    add.add_argument('--rating', type=float)
    add.add_argument('--date', type=date.fromisoformat, help='YYYY-MM-DD, defaults to today')
    return parser


def _readlist_dir(raw: str | None) -> Path | None:
    if not raw:
        print('No read-list directory: pass --readlist-dir or set READLIST_DIR', file=sys.stderr)
        return None
    directory = Path(raw).expanduser()
    if not directory.is_dir():
        print(f'Read-list directory does not exist: {directory}', file=sys.stderr)
        return None
    return directory


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return _run(args, Settings.load(args.env_file))
    except SettingsError as e:
        print(e, file=sys.stderr)
        return 1


def _run(args: argparse.Namespace, settings: Settings) -> int:
    if args.command == 'rate':
        token = settings.get('ACCESS_TOKEN')
        if not token:
            print('No ACCESS_TOKEN specified: set it in the environment or .env', file=sys.stderr)
            return 1
        books = rate_library(token, args.path, args.limit)
        save_ratings(books, args.ratings)
        print(f'Stored {len(books)} ratings at {args.ratings}')
        return 0

    if args.command == 'view':
        for i, book in enumerate(ranked(load_ratings(args.ratings))):
            print(f'{i:2d}. {book.name} - {adjusted_rating(book):.2f} (from {book.ratings_count})')
        return 0

    readlist_dir = _readlist_dir(args.readlist_dir or settings.get('READLIST_DIR'))
    if readlist_dir is None:
        return 1

    if args.command == 'add':
        print(f'Read-list entry: {add_entry(readlist_dir, args.title, args.author, args.rating, args.date)}')
        return 0

    try:
        result = recommend_books(
            mode=Mode(args.command),
            readlist_dir=readlist_dir,
            ratings_path=args.ratings,
            cache_path=args.cache,
            library_picks=args.library_picks,
            outside_picks=args.outside_picks,
            today=date.today(),
            params=Params(half_life_days=args.half_life),
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print(
        f'{result.reads} books read, {result.library_size} in library '
        f'({result.library_without_subjects} without subject data)'
    )
    _print_picks('From your library', result.library)
    _print_picks('From outside', result.outside)
    return 0


if __name__ == '__main__':
    sys.exit(main())
