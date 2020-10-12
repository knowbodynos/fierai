import argparse
import inspect
from typing import Optional

from . import run


def create_base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Come on down to Flavortown.')
    return parser


def create_download_subparser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser('download', description='Download a YouTube playlist.')
    parser.add_argument('playlist_url', help='YouTube playlist URL to download.')
    parser.add_argument('--audio', '-a', dest='audio', action='store_true',
                        help='Download audio')
    parser.add_argument('--subtitles', '-s', dest='subtitles', action='store_true',
                        help='Download subtitles')
    return parser


def create_scrape_subparser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser('scrape', description='Scrape YouTube playlists.')
    parser.add_argument('query', help='YouTube query.')
    parser.add_argument('--max-results', '-m', dest='max_results', type=int, default=100,
                        help='Maximum number of playlist')
    parser.add_argument('--audio', '-a', dest='audio', action='store_true',
                        help='Scrape audio')
    parser.add_argument('--subtitles', '-s', dest='subtitles', action='store_true',
                        help='Scrape subtitles')
    return parser


def create_chunk_subparser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser('chunk', description='Chunk audio and subtitle files.')
    parser.add_argument('audio_file', help="Path to audio file")
    parser.add_argument('subtitles_file', help="Path to subtitles file")
    parser.add_argument('--split-time', '-s', dest='split_time', type=float, default=3.,
                        help="Duration of silence to split on (in seconds). [Default: 3]")
    return parser


def create_corpus_subparser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser('corpus', description='Create corpus from subtitles.')
    parser.add_argument('--subs-dir', '-d', dest='subtitles_dir', default='.',
                        help='Directory of parsed subtitles. [Default: \'.\']')
    parser.add_argument('--train-frac', '-t', dest='train_frac', type=float, default=0.9,
                        help='Fraction of data to use for training. [Default: 0.9]')
    parser.add_argument('--valid-frac', '-v', dest='valid_frac', type=float, default=None,
                        help='Fraction of data to use for validation. [Default: None]')
    parser.add_argument('--random-seed', '-r', dest='random_seed', type=int, default=42,
                        help='Random seed. [Default: 42]')
    parser.add_argument('--split-time', '-s', dest='split_time', type=float, default=3.,
                        help="Duration of silence to split on (in seconds). [Default: 3]")
    return parser


def cli(args: Optional[argparse.Namespace] = None) -> None:
    if args is None:
        parser = create_base_parser()
        subparsers = parser.add_subparsers(dest='subcommand')
        create_download_subparser(subparsers)
        create_scrape_subparser(subparsers)
        create_chunk_subparser(subparsers)
        create_corpus_subparser(subparsers)
        args = parser.parse_args()

    func = getattr(run, f'run_{args.subcommand}')

    arg_dict = vars(args)
    arg_names = inspect.signature(func).parameters

    missing = set(arg_names) - set(arg_dict.keys())
    if missing:
        raise RuntimeError(f"Missing arguments: {missing}")
    chunk_args = {name: arg_dict[name] for name in arg_names}

    func(**chunk_args)


if __name__ == '__main__':
    cli()
