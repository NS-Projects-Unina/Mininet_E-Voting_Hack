#!/usr/bin/env python3
"""
Electronic Voting System - Client
===================================
Command-line client that authenticates with a voter ID and sends a
vote to the voting server.  Supports both HTTP and HTTPS.

Usage:
    python3 voting_client.py --server 10.0.0.1 --port 8080 --voter VOTER001 --candidate "Alice Ferraro"
    python3 voting_client.py --server 10.0.0.1 --port 8080 --results
"""

import sys
import json
import argparse
import requests
import urllib3

# Suppress self-signed cert warnings for HTTPS demo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CANDIDATES = [
    'Alice Ferraro',
    'Marco Rinaldi',
    'Laura Marchetti',
    'Giuseppe Moretti'
]

def build_url(host: str, port: int, path: str, https: bool = False) -> str:
    scheme = 'https' if https else 'http'
    return f'{scheme}://{host}:{port}{path}'


def cast_vote(host, port, voter_id, candidate, https=False):
    """Send a vote to the server and display the result."""
    url = build_url(host, port, '/vote', https)

    payload = {
        'voter_id': voter_id,
        'candidate': candidate
    }

    print(f"\n[*] Sending vote to {url}")
    print(f"    Voter   : {voter_id}")
    print(f"    Candidate: {candidate}")

    try:
        resp = requests.post(url, json=payload, timeout=10,
                             verify=False)  # verify=False for self-signed certs
        data = resp.json()

        if resp.status_code == 200:
            print(f"\n[+] SUCCESS — {data.get('message', '')}")
            print(f"    Hash : {data.get('vote_hash', 'N/A')}")
            print(f"    Time : {data.get('timestamp', 'N/A')}")
        else:
            print(f"\n[-] FAILED ({resp.status_code}) — {data.get('message', '')}")

        return data

    except requests.exceptions.ConnectionError:
        print(f"\n[!] ERROR: Cannot connect to {url}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] ERROR: {e}")
        sys.exit(1)


def get_results(host, port, https=False):
    """Fetch current election results."""
    url = build_url(host, port, '/api/results', https)
    try:
        resp = requests.get(url, timeout=10, verify=False)
        data = resp.json()

        print(f"\n{'=' * 50}")
        print(f"  ELECTION RESULTS  (total: {data['total_votes']} votes)")
        print(f"{'=' * 50}")
        for cand in data.get('candidates', []):
            count = data['results'].get(cand, 0)
            pct = (count / data['total_votes'] * 100) if data['total_votes'] > 0 else 0
            bar = '█' * int(pct / 2)
            print(f"  {cand:20s}  {count:3d}  ({pct:5.1f}%) {bar}")
        print(f"{'=' * 50}\n")
        return data

    except Exception as e:
        print(f"[!] Could not fetch results: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Electronic Voting System — Client')
    parser.add_argument('--server', default='10.0.0.1',
                        help='Voting server IP (default 10.0.0.1)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Voting server port (default 8080)')
    parser.add_argument('--https', action='store_true',
                        help='Use HTTPS')
    parser.add_argument('--voter', help='Voter ID (e.g. VOTER001)')
    parser.add_argument('--candidate', help='Candidate name')
    parser.add_argument('--results', action='store_true',
                        help='Just show current results')
    args = parser.parse_args()

    if args.results:
        get_results(args.server, args.port, args.https)
    elif args.voter and args.candidate:
        cast_vote(args.server, args.port,
                  args.voter, args.candidate, args.https)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
