import os
import json
from argparse import ArgumentParser
from proxy.async_proxy import Proxy


def get_parser():
    """Parse arguments from command line"""
    parser = ArgumentParser(description='async proxy')
    parser.add_argument(
        '-H', '--host', default='localhost',
        help='Host to listen [default: %(default)s]')
    parser.add_argument(
        '-p', '--port', type=int, default=30303,
        help='Port to listen [default: %(default)d]')
    parser.add_argument(
        '-a', '--auth', action="store_true",
        help='Enable authorization [default: disabled]')
    parser.add_argument(
        '-b', '--banlist', default="banlist.json",
        help='name of JSON file with baned hosts list [default: %(default)s]')
    parser.add_argument(
        '-t', '--tokens', default="tokens.json",
        help='name of JSON file with tokens list [default: %(default)s]')

    return parser


def main():
    """Enter point of program"""
    parser = get_parser()
    args = parser.parse_args()

    if not (1 <= args.port <= 65535):
        parser.error('port must be 1-65535')

    ban_list_filename = args.banlist if args.banlist else args.banlist.default
    token_list_filename = args.tokens if args.tokens else args.tokens.default
    baned_hosts = []
    tokens = []

    if os.path.exists(ban_list_filename):
        with open(ban_list_filename, 'r') as f:
            baned_hosts = json.loads(f.read())["banlist"]

    if os.path.exists(token_list_filename):
        with open(token_list_filename, 'r') as f:
            tokens = set(json.loads(f.read())["tokens"])

    proxy = Proxy(
        args.host,
        args.port,
        with_auth=args.auth,
        banned_hosts=baned_hosts,
        tokens=tokens)
    proxy.start_proxy()


if __name__ == '__main__':
    main()
