#!/usr/bin/env python3
# topology.py — Custom Linear Topology for Path Tracing

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink
    )

    info("*** Adding Controller\n")
    net.addController('c0', controller=RemoteController,
                       ip='127.0.0.1', port=6633)

    info("*** Adding Hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')

    info("*** Adding Switches\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    info("*** Adding Links\n")
    net.addLink(h1, s1)
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s3, h2)

    info("*** Starting Network\n")
    net.start()

    info("*** Network is ready!\n")
    info("*** Hosts: h1=10.0.0.1, h2=10.0.0.2\n")
    info("*** Opening Mininet CLI — type 'pingall' to test\n")

    CLI(net)

    info("*** Stopping Network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
