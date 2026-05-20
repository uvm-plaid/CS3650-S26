#!/bin/bash

chmod +x /home/pi/start_ovs.sh
/home/pi/start_ovs.sh

ovs-vsctl add-br br0
ovs-vsctl add-port br0 eth0
ovs-vsctl add-port br0 eth1
ovs-vsctl add-port br0 eth2
ovs-vsctl add-port br0 eth3

ip addr flush eth0
ip addr flush eth1
ip addr flush eth2
ip addr flush eth3

ovs-vsctl set bridge br0 protocols=OpenFlow13
ovs-vsctl set-fail-mode br0 secure

ovs-vsctl set-controller br0 tcp:192.168.4.0:6633
