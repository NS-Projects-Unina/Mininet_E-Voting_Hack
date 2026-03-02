#!/usr/bin/env python3
"""
Automated Voter Simulator
===========================
Simulates multiple voters casting votes in sequence.
Useful for populating the election with realistic data
before running attack demos.

Usage:
    python3 auto_vote.py --server 10.0.0.1
    python3 auto_vote.py --server 10.0.0.1 --distribution random
    python3 auto_vote.py --server 10.0.0.1 --distribution alice
"""

import sys
import time
import random
import argparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CANDIDATES = [
    'Alice Ferraro',
    'Marco Rinaldi',
    'Laura Marchetti',
    'Giuseppe Moretti'
]

VOTERS = {
    'VOTER001': 'Mario Rossi',
    'VOTER002': 'Anna Bianchi',
    'VOTER003': 'Luca Verdi',
    'VOTER004': 'Sara Neri',
    'VOTER005': 'Paolo Gialli',
    'VOTER006': 'Giulia Blu',
    'VOTER007': 'Andrea Viola',
    'VOTER008': 'Elena Rosa',
    'VOTER009': 'Davide Grigio',
    'VOTER010': 'Chiara Marrone',
}

# Pre-defined realistic vote distribution
REALISTIC_VOTES = {
    'VOTER001': 'Alice Ferraro',
    'VOTER002': 'Marco Rinaldi',
    'VOTER003': 'Alice Ferraro',
    'VOTER004': 'Laura Marchetti',
    'VOTER005': 'Alice Ferraro',
    'VOTER006': 'Marco Rinaldi',
    'VOTER007': 'Giuseppe Moretti',
    'VOTER008': 'Alice Ferraro',
    'VOTER009': 'Laura Marchetti',
    'VOTER010': 'Marco Rinaldi',
}


def main():
    parser = argparse.ArgumentParser(description='Automated Voter Simulator')
    parser.add_argument('--server', '-s', default='10.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8080)
    parser.add_argument('--https', action='store_true')
    parser.add_argument('--distribution', '-d', default='realistic',
                        choices=['realistic', 'random', 'alice', 'giuseppe'],
                        help='Vote distribution pattern')
    parser.add_argument('--count', '-n', type=int, default=None,
                        help='Number of voters to simulate (default: all)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between votes (seconds)')
    args = parser.parse_args()

    scheme = 'https' if args.https else 'http'
    base = f'{scheme}://{args.server}:{args.port}'

    voters = list(VOTERS.keys())
    if args.count:
        voters = voters[:args.count]

    print(f"\n[*] Auto-voting for {len(voters)} voters")
    print(f"[*] Server: {base}")
    print(f"[*] Distribution: {args.distribution}\n")

    for vid in voters:
        if args.distribution == 'realistic':
            candidate = REALISTIC_VOTES.get(vid, random.choice(CANDIDATES))
        elif args.distribution == 'random':
            candidate = random.choice(CANDIDATES)
        elif args.distribution == 'alice':
            candidate = 'Alice Ferraro'
        elif args.distribution == 'giuseppe':
            candidate = 'Giuseppe Moretti'
        else:
            candidate = random.choice(CANDIDATES)

        try:
            resp = requests.post(f'{base}/vote',
                                 json={'voter_id': vid, 'candidate': candidate},
                                 timeout=10, verify=False)
            data = resp.json()
            status_icon = '✓' if resp.status_code == 200 else '✗'
            print(f"  {status_icon}  {vid} ({VOTERS[vid]:18s}) → {candidate}")
        except Exception as e:
            print(f"  !  {vid} → ERROR: {e}")

        time.sleep(args.delay)

    # Show final results
    print()
    try:
        resp = requests.get(f'{base}/api/results', timeout=10, verify=False)
        data = resp.json()
        print(f"{'=' * 50}")
        print(f"  FINAL RESULTS  (total: {data['total_votes']})")
        print(f"{'=' * 50}")
        for c in CANDIDATES:
            cnt = data['results'].get(c, 0)
            bar = '█' * (cnt * 3)
            print(f"  {c:20s}  {cnt:2d}  {bar}")
        print(f"{'=' * 50}\n")
    except Exception:
        pass


if __name__ == '__main__':
    main()
