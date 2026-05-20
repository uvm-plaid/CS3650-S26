#!/bin/bash

echo "$HOSTNAME"

ovs-vsctl set bridge br0 other_config:datapath-id=$1
ovs-ofctl show br0 -O OpenFlow13
