#!/usr/bin/env python3
"""
Electronic Voting System - Server
==================================
Flask-based voting server that handles vote collection, storage, 
result display and vote integrity verification via HMAC.

Supports both HTTP (vulnerable) and HTTPS (secure) modes to 
demonstrate the impact of encryption on vote security.

Usage:
    python3 voting_server.py                    # HTTP mode (default)
    python3 voting_server.py --https            # HTTPS mode
    python3 voting_server.py --port 9090        # Custom port
"""

import os
import sys
import json
import hashlib
import hmac
import ssl
import sqlite3
import argparse
from datetime import datetime
from flask import Flask, request, jsonify, redirect, url_for, session, abort
from flask_cors import CORS


# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = os.urandom(32)
CORS(app)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE = os.path.join(BASE_DIR, 'votes.db')

CANDIDATES = [
    'Alice Ferraro',
    'Marco Rinaldi',
    'Laura Marchetti',
    'Giuseppe Moretti'
]

# HMAC key used to guarantee vote integrity (shared secret)
HMAC_SECRET = b'e-voting-integrity-key-ns-2026'

# Valid voter credentials  {token: full_name}
# In a real system these would come from a secure identity provider.
VALID_VOTERS = {
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


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Return a fresh DB connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id    TEXT    UNIQUE NOT NULL,
            voter_name  TEXT    NOT NULL,
            candidate   TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL,
            client_ip   TEXT,
            vote_hash   TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            details     TEXT,
            timestamp   TEXT NOT NULL,
            source_ip   TEXT
        )
    ''')
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------
def compute_vote_hash(voter_id: str, candidate: str, timestamp: str) -> str:
    """Compute an HMAC-SHA256 over the vote payload for integrity."""
    message = f"{voter_id}:{candidate}:{timestamp}"
    return hmac.new(HMAC_SECRET, message.encode(), hashlib.sha256).hexdigest()


def log_event(event_type: str, details: str, source_ip: str = ''):
    """Append an entry to the audit log."""
    conn = get_db()
    conn.execute(
        'INSERT INTO audit_log (event_type, details, timestamp, source_ip) '
        'VALUES (?, ?, ?, ?)',
        (event_type, details, datetime.now().isoformat(), source_ip)
    )
    conn.commit()
    conn.close()


# ===================================================================== #
#                             ROUTES                                     #
# ===================================================================== #

@app.route('/')
def index():
    """API info."""
    return jsonify({
        'service': 'Electronic Voting System',
        'endpoints': [
            'POST /vote',
            'GET /api/results',
            'GET /api/votes',
            'GET /api/audit',
            'POST /api/verify',
            'POST /admin/reset'
        ],
        'candidates': CANDIDATES
    })


@app.route('/vote', methods=['POST'])
def cast_vote():
    """
    Accept a vote via POST.
    Expects 'voter_id' and 'candidate' in form data or JSON body.
    """
    # --- Parse input ---
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    voter_id  = data.get('voter_id', '').strip()
    candidate = data.get('candidate', '').strip()
    client_ip = request.remote_addr

    # --- Validate voter ---
    if voter_id not in VALID_VOTERS:
        log_event('INVALID_VOTER', f'Rejected voter ID: {voter_id}', client_ip)
        return jsonify({'status': 'error', 'message': 'Invalid voter ID.'}), 403

    # --- Validate candidate ---
    if candidate not in CANDIDATES:
        log_event('INVALID_CANDIDATE', f'Invalid candidate: {candidate}', client_ip)
        return jsonify({'status': 'error', 'message': 'Invalid candidate.'}), 400

    # --- Check double-voting ---
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM votes WHERE voter_id = ?', (voter_id,)
    ).fetchone()
    if existing:
        conn.close()
        log_event('DOUBLE_VOTE', f'{voter_id} tried to vote again', client_ip)
        return jsonify({'status': 'error', 'message': 'This voter ID has already been used.'}), 409

    # --- Record vote ---
    timestamp  = datetime.now().isoformat()
    vote_hash  = compute_vote_hash(voter_id, candidate, timestamp)
    voter_name = VALID_VOTERS[voter_id]

    conn.execute(
        'INSERT INTO votes '
        '(voter_id, voter_name, candidate, timestamp, client_ip, vote_hash) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (voter_id, voter_name, candidate, timestamp, client_ip, vote_hash)
    )
    conn.commit()
    conn.close()

    log_event('VOTE_CAST', f'{voter_id} -> {candidate}', client_ip)

    return jsonify({
        'status': 'success',
        'message': f'Vote recorded for {candidate}',
        'vote_hash': vote_hash,
        'timestamp': timestamp
    })


# ------------------------------------------------------------------ #
# Results & admin endpoints
# ------------------------------------------------------------------ #

@app.route('/api/results')
def api_results():
    """JSON results — consumed by the results page and by the client."""
    conn = get_db()
    counts = {}
    for cand in CANDIDATES:
        row = conn.execute(
            'SELECT COUNT(*) AS cnt FROM votes WHERE candidate = ?', (cand,)
        ).fetchone()
        counts[cand] = row['cnt']

    total = conn.execute('SELECT COUNT(*) AS cnt FROM votes').fetchone()['cnt']
    conn.close()

    return jsonify({
        'results': counts,
        'total_votes': total,
        'candidates': CANDIDATES,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/votes')
def api_votes():
    """Detailed vote list (admin)."""
    conn = get_db()
    rows = conn.execute(
        'SELECT voter_id, voter_name, candidate, timestamp, client_ip, vote_hash '
        'FROM votes ORDER BY timestamp'
    ).fetchall()
    conn.close()
    return jsonify({'votes': [dict(r) for r in rows]})


@app.route('/api/audit')
def api_audit():
    """Audit-log dump (admin)."""
    conn = get_db()
    rows = conn.execute(
        'SELECT event_type, details, timestamp, source_ip '
        'FROM audit_log ORDER BY timestamp DESC LIMIT 200'
    ).fetchall()
    conn.close()
    return jsonify({'events': [dict(r) for r in rows]})


@app.route('/api/verify', methods=['POST'])
def verify_vote():
    """Verify vote integrity via HMAC comparison."""
    data = request.get_json()
    voter_id = data.get('voter_id', '')

    conn = get_db()
    row = conn.execute(
        'SELECT candidate, timestamp, vote_hash FROM votes WHERE voter_id = ?',
        (voter_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'status': 'error', 'message': 'Vote not found'}), 404

    expected = compute_vote_hash(voter_id, row['candidate'], row['timestamp'])
    is_valid = hmac.compare_digest(row['vote_hash'], expected)

    return jsonify({
        'voter_id': voter_id,
        'candidate': row['candidate'],
        'integrity': 'VALID' if is_valid else 'TAMPERED',
        'stored_hash': row['vote_hash'],
        'expected_hash': expected
    })


@app.route('/admin/reset', methods=['POST'])
def reset_election():
    """Delete every vote and start fresh."""
    conn = get_db()
    conn.execute('DELETE FROM votes')
    conn.commit()
    conn.close()
    log_event('ELECTION_RESET', 'All votes deleted', request.remote_addr)
    return jsonify({'status': 'success', 'message': 'Election reset.'})


# ===================================================================== #
#                            ENTRY POINT                                 #
# ===================================================================== #

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Electronic Voting System — Server')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Bind address (default 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Listen port (default 8080)')
    parser.add_argument('--https', action='store_true',
                        help='Enable HTTPS with self-signed certificate')
    parser.add_argument('--cert', default=os.path.join(BASE_DIR, 'certs', 'server.crt'),
                        help='Path to SSL certificate')
    parser.add_argument('--key', default=os.path.join(BASE_DIR, 'certs', 'server.key'),
                        help='Path to SSL private key')
    args = parser.parse_args()

    init_db()
    log_event('SERVER_START',
              f'Binding {args.host}:{args.port}  HTTPS={args.https}')

    proto = 'HTTPS' if args.https else 'HTTP'
    print(f"\n{'=' * 60}")
    print(f"  ELECTRONIC VOTING SYSTEM  —  {proto}")
    print(f"  Listening on {args.host}:{args.port}")
    print(f"  Candidates : {', '.join(CANDIDATES)}")
    print(f"  Voters     : {len(VALID_VOTERS)} registered")
    print(f"{'=' * 60}\n")

    if args.https:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(args.cert, args.key)
        app.run(host=args.host, port=args.port,
                ssl_context=ctx, debug=False)
    else:
        app.run(host=args.host, port=args.port, debug=False)
