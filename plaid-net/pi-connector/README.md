### pi_connector.py

Deploys a specified bash script on each of the Pis in the network. The specific Pis are specified in the ips.txt file. The execute.sh script is sent to each of the Pis in ips.txt and executed.

### local_ips.txt
Lists all of the IPs of the Pis in the network. The SDN controller’s IP is the .0 address, the switches each have their own number, and the hosts are 101, 102, and 103 for hosts 1, 2, and 3.

### install_openvswitch.sh 

Download OVS and install it from source. There are a few strange aspects to this instillation that this script automates.

### init_ovs.sh 

Initializes OVS on a switch for the first time. OVS is started, and all of the ethernet interfaces are added as ports and refreshed. OpenFlow13 is set as the protocol, and the fail mode is set to secure to ensure only commands send to the switch via OpenFlow are enacted (as opposed to automatically determining where packets should go). Additionally, the controller is set to the IP of the SDN controller Pi.

### start_ovs.sh

Starts OVS on a switch. The ovs database is started, and the ethernet interfaces are refreshed. Additionally, any current flow set in the switch’s database is deleted so that the switch will only respond to new commands sent via OpenFlow. `stop_ovs.sh` finds the running OVS process and kills it.

### start_flask.sh 

Starts the flask app for the switch. Currently, this app’s only purpose is to light up the Pi’s indicator lights. Though, this app could used for other purposes as well, for anything that is unable to be communciated via OpenFlow. `stop_flask.sh` finds the running flask process and kills it.
