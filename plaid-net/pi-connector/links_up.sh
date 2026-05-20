#!/bin/bash

echo "$HOSTNAME"

ovs-ofctl del-flows br0 -O OpenFlow13

ovs-ofctl mod-port br0 eth0 receive -O OpenFlow13
ovs-ofctl mod-port br0 eth1 receive -O OpenFlow13
ovs-ofctl mod-port br0 eth2 receive -O OpenFlow13
ovs-ofctl mod-port br0 eth3 receive -O OpenFlow13

ovs-ofctl mod-port br0 eth0 forward -O OpenFlow13
ovs-ofctl mod-port br0 eth1 forward -O OpenFlow13
ovs-ofctl mod-port br0 eth2 forward -O OpenFlow13
ovs-ofctl mod-port br0 eth3 forward -O OpenFlow13

ovs-ofctl mod-port br0 eth0 down -O OpenFlow13
ovs-ofctl mod-port br0 eth1 down -O OpenFlow13
ovs-ofctl mod-port br0 eth2 down -O OpenFlow13
ovs-ofctl mod-port br0 eth3 down -O OpenFlow13

ovs-ofctl mod-port br0 eth0 up -O OpenFlow13
ovs-ofctl mod-port br0 eth1 up -O OpenFlow13
ovs-ofctl mod-port br0 eth2 up -O OpenFlow13
ovs-ofctl mod-port br0 eth3 up -O OpenFlow13
