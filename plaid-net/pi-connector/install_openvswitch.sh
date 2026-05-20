#!/bin/bash

wget https://www.openvswitch.org/releases/openvswitch-2.12.0.tar.gz
tar -xvzf openvswitch-2.12.0.tar.gz
cd openvswitch-2.12.0

apt install python-simplejson python-qt4 libssl-dev python-twisted-conch automake autoconf gcc uml-utilities libtool build-essential pkg-config -y

./configure
make -j4
make -j4 install

touch /usr/local/etc/ovs-vswitchd.conf
mkdir -p /usr/local/etc/openvswitch
ovsdb-tool create /usr/local/etc/openvswitch/conf.db vswitchd/vswitch.ovsschema
mkdir -p /usr/local/var/run/openvswitch
