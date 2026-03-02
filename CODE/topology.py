#!/usr/bin/env python3
"""
Mininet Topology — Electronic Voting System
=============================================
Creates a realistic network with:
  - 1 Election server            (h1 / 10.0.0.1)
  - 4 Voter hosts                (h2‑h5 / 10.0.0.2‑5)
  - 1 Attacker                   (h6 / 10.0.0.6)
  - 1 Switch

Optionally starts the voting server automatically on h1.

Usage (must be root):
    sudo python3 topology.py
    sudo python3 topology.py --autostart   # auto-launch server on h1
"""

import os
import sys
import argparse

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info


class VotingNetworkTopo(Topo):
    """
    Topology:

        h1 (Election Server)  ─┐
        h2 (Voter 1)           ─┤
        h3 (Voter 2)           ─┼── s1 (switch)
        h4 (Voter 3)           ─┤
        h5 (Voter 4)           ─┤
        h6 (Attacker)          ─┘
    """

    def build(self):
        # --- Switch ---
        switch = self.addSwitch('s1')

        # --- Hosts ---
        server   = self.addHost('h1', ip='10.0.0.1/24')
        voter1   = self.addHost('h2', ip='10.0.0.2/24')
        voter2   = self.addHost('h3', ip='10.0.0.3/24')
        voter3   = self.addHost('h4', ip='10.0.0.4/24')
        voter4   = self.addHost('h5', ip='10.0.0.5/24')
        attacker = self.addHost('h6', ip='10.0.0.6/24')

        # --- Links (10 Mbps, 5 ms delay — realistic LAN) ---
        for host in [server, voter1, voter2, voter3, voter4, attacker]:
            self.addLink(host, switch, bw=10, delay='5ms')


def run(autostart: bool = False):
    """Build the network, optionally launch the server, then drop to CLI."""
    setLogLevel('info')

    topo = VotingNetworkTopo()
    net  = Mininet(topo=topo, switch=OVSBridge, link=TCLink,
                   controller=None)
    net.start()

    info('\n')
    info('*' * 60 + '\n')
    info('*               ELECTRONIC VOTING SYSTEM               *\n')
    info('*' * 60 + '\n')
    info('*  h1  = Election Server   (10.0.0.1)                  *\n')
    info('*  h2  = Voter 1           (10.0.0.2)                  *\n')
    info('*  h3  = Voter 2           (10.0.0.3)                  *\n')
    info('*  h4  = Voter 3           (10.0.0.4)                  *\n')
    info('*  h5  = Voter 4           (10.0.0.5)                  *\n')
    info('*  h6  = Attacker          (10.0.0.6)                  *\n')
    info('*' * 60 + '\n\n')

    project_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(project_dir, 'server', 'voting_server.py')

    if autostart:
        h1 = net.get('h1')
        info('[*] Starting voting server on h1 …\n')
        h1.cmd(f'python3 {server_script} &')
        info('[+] Server running on http://10.0.0.1:8080\n\n')

    CLI(net)
    net.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Electronic Voting System — Mininet topology')
    parser.add_argument('--autostart', action='store_true',
                        help='Automatically start the voting server on h1')
    args = parser.parse_args()
    run(autostart=args.autostart)
