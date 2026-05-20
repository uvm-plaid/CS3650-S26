import json

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
from ryu.lib import dpid as dpid_lib
from ryu.ofproto import ether
from ryu.lib.packet import arp

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ether_types
from ryu.topology import event
from ryu.topology.api import get_switch, get_link, get_all_link, get_all_switch
from ryu.controller import dpset

from Graph import DirectedGraph
from Node import KeyedNode

simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/mactable/{dpid}'

link_list = []


class SwitchNode(KeyedNode):
    def __init__(self, dpid, switch):
        super().__init__(dpid)
        self.switch = switch

    def __str__(self):
        return self.switch.dp.address[0]


class SimpleSwitchRest13(simple_switch_13.SimpleSwitch13):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
    }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchRest13, self).__init__(*args, **kwargs)
        self.switches = {}
        wsgi = kwargs['wsgi']

        wsgi.register(SimpleSwitchController,
                      {simple_switch_instance_name: self})

        self.graph = DirectedGraph()
        self.forwarding_tables = []
        self.mac_to_port = {}

        self.ip_to_mac = {
            "169.254.20.158": "b8:27:eb:17:0d:96",
            "169.254.173.130": "b8:27:eb:7f:7c:ea",
            "169.254.240.121": "b8:27:eb:81:61:47"
        }
        self.link_to_port = {
            (1, "169.254.20.158"): 2,
            (9, "169.254.173.130"): 16,
            (8, "169.254.240.121"): 2
        }

    def update_topology(self):
        self.graph = DirectedGraph()

        switch_list = get_switch(self)
        for switch in switch_list:
            self.graph.add_node(SwitchNode(switch.dp.id, switch))

        links_list = get_link(self)
        for link in links_list:
            self.graph.add_edge(link.src.dpid, link.dst.dpid)
        print(self.graph)
        print(len(links_list))
        print("test")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp, target_hw_addr, target_ip_addr):
        # see http://osrg.github.io/ryu-book/en/html/packet_lib.html
        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=target_hw_addr))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=target_hw_addr,
                                 src_ip=target_ip_addr,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        self._send_packet(datapath, port, pkt)

    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("To dpid {0} packet-out {1}".format(datapath.id, pkt))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        # print("#############################################")
        datapath = msg.datapath
        dpid = datapath.id
        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data)
        # self.logger.info("packet-in: %s" % (pkt,))

        eth = pkt.get_protocols(ethernet.ethernet)[0]

        pkt_eth = pkt.get_protocol(ethernet.ethernet)
        if pkt_eth:
            dst_mac = pkt_eth.dst
            eth_type = pkt_eth.ethertype

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            print("datapath id: " + str(dpid))
            print("port: " + str(port))
            print("pkt_eth.dst: " + str(pkt_eth.dst))
            print("pkt_eth.src: " + str(pkt_eth.src))
            print("pkt_arp: " + str(pkt_arp))
            print("pkt_arp:src_ip: " + str(pkt_arp.src_ip))
            print("pkt_arp:dst_ip: " + str(pkt_arp.dst_ip))
            print("pkt_arp:src_mac: " + str(pkt_arp.src_mac))
            print("pkt_arp:dst_mac: " + str(pkt_arp.dst_mac))

            # Destination and source ip address
            d_ip = pkt_arp.dst_ip
            s_ip = pkt_arp.src_ip

            # Destination and source mac address (HW address)
            d_mac = pkt_arp.dst_mac
            s_mac = pkt_arp.src_mac

            in_port = msg.match['in_port']
            dst_addr = self.ip_to_mac[d_ip]

            self._handle_arp(datapath=datapath,
                             port=in_port,
                             pkt_ethernet=pkt.get_protocols(ethernet.ethernet)[0],
                             pkt_arp=pkt_arp,
                             target_hw_addr=dst_addr,
                             target_ip_addr=d_ip)
        else:
            print("OTHER")
            print(pkt)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        super(SimpleSwitchRest13, self).switch_features_handler(ev)
        datapath = ev.msg.datapath
        self.switches[datapath.id] = datapath
        self.mac_to_port.setdefault(datapath.id, {})

    def set_mac_to_port(self, dpid, entry):
        mac_table = self.mac_to_port.setdefault(dpid, {})
        datapath = self.switches.get(dpid)

        entry_port = entry['port']
        entry_mac = entry['mac']

        if datapath is not None:
            parser = datapath.ofproto_parser
            if entry_port not in mac_table.values():

                for mac, port in mac_table.items():
                    # from known device to new device
                    actions = [parser.OFPActionOutput(entry_port)]
                    match = parser.OFPMatch(in_port=port, eth_dst=entry_mac)
                    self.add_flow(datapath, 1, match, actions)

                    # from new device to known device
                    actions = [parser.OFPActionOutput(port)]
                    match = parser.OFPMatch(in_port=entry_port, eth_dst=mac)
                    self.add_flow(datapath, 1, match, actions)

                mac_table.update({entry_mac: entry_port})
        return mac_table

    def find_src_dpid(self, src_addr):
        switch_list = get_all_switch(self)
        for switch in switch_list:
            port_list = switch.ports
            for port in port_list:
                if src_addr == port.hw_addr:
                    print(port.hw_addr, port.dpid)
                    return (port.hw_addr, port.dpid)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no

        ofproto = msg.datapath.ofproto

        print("links:")
        links = get_link(self)
        print(links)

        print("switches:")
        switches = get_switch(self)
        print(switches)
        print(" [", end='')
        for switch in switches:
            print(switch.dp.id, end='')
            print(",", end='')
        print("]")

    def remove_table_flows(self, datapath, table_id, match, instructions):
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(datapath, 0, 0, table_id,
                                                      ofproto.OFPFC_DELETE, 0, 0, 1, ofproto.OFPCML_NO_BUFFER,
                                                      ofproto.OFPP_ANY,
                                                      ofproto.OFPG_ANY, 0, match, instructions)
        return flow_mod


class SimpleSwitchController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    @route('simpleswitch', url, methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def list_mac_table(self, req, **kwargs):

        simple_switch = self.simple_switch_app
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])

        if dpid not in simple_switch.mac_to_port:
            return Response(status=404)

        mac_table = simple_switch.mac_to_port.get(dpid, {})
        body = json.dumps(mac_table)
        return Response(content_type='application/json', body=body)

    @route('simpleswitch', url, methods=['PUT'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def put_mac_table(self, req, **kwargs):

        simple_switch = self.simple_switch_app
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        if dpid not in simple_switch.mac_to_port:
            return Response(status=404)

        try:
            mac_table = simple_switch.set_mac_to_port(dpid, new_entry)
            body = json.dumps(mac_table)
            return Response(content_type='application/json', body=body)
        except Exception as e:
            return Response(status=500)

    '''
    Return link list in our json format
    '''
    @route('get_topology', '/get_topology', methods=['GET'])
    def retrieve_links(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        # return link list in our json format
        link_list = get_link(simple_switch)
        connected = []
        for link in link_list:
            connected.append([
                link.src.dpid,
                link.dst.dpid,
                link.dst.port_no
            ])

        for link in simple_switch.link_to_port:
            connected.append([
                link[0],
                link[1],
                simple_switch.link_to_port[link]
            ])
            connected.append([
                link[1],
                link[0],
                -1
            ])

        self.simple_switch_app.update_topology()

        return Response(content_type='application/json',
                        body=json.dumps({
                            "connected": connected
                        }))

    '''
    1. retrieve configuration json via PUT
    2. iterate over links:
       if link not in "connected" array put down both ports
    '''
    @route('configlinks', '/configlinks', methods=['PUT'])
    def configure_links(self, req, **kwargs):
        try:
            json_in = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        try:
            config_list = json_in['connected']
        except Exception as e:
            return Response(status=500)

        simple_switch = self.simple_switch_app
        link_list = get_link(simple_switch)
        queue = []
        for link in link_list:
            src = link.src.dpid
            dst = link.dst.dpid
            if ([src, dst] not in config_list) and ([dst, src] not in config_list):
                parser = get_switch(simple_switch, src)[0].dp.ofproto_parser
                ofproto = get_switch(simple_switch, src)[0].dp.ofproto
                mod1 = parser.OFPPortMod(datapath=get_switch(simple_switch, src)[0].dp,
                                         port_no=link.src.port_no, hw_addr=link.src.hw_addr,
                                         config=(ofproto.OFPPC_NO_RECV | ofproto.OFPPC_NO_FWD),
                                         mask=(ofproto.OFPPC_NO_FWD | ofproto.OFPPC_NO_RECV))
                queue.append([mod1, get_switch(simple_switch, src)[0].dp])
                mod2 = parser.OFPPortMod(datapath=get_switch(simple_switch, dst)[0].dp,
                                         port_no=link.dst.port_no, hw_addr=link.dst.hw_addr,
                                         config=(ofproto.OFPPC_NO_RECV | ofproto.OFPPC_NO_FWD),
                                         mask=(ofproto.OFPPC_NO_FWD | ofproto.OFPPC_NO_RECV))
                queue.append([mod2, get_switch(simple_switch, dst)[0].dp])

        # We use a message queue to avoid changing the length
        # of link_list in our loop by turning off links.
        for message in queue:
            message[1].send_msg(message[0])

    '''
    Iterate over switches, delete all the flow, bring up all the interfaces
    '''
    @route('reset_topology', '/reset_topology', methods=['GET'])
    def reset_links(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        switch_list = get_switch(simple_switch)
        for switch in switch_list:
            parser = switch.dp.ofproto_parser
            # Removing flow via method:
            # https://sourceforge.net/p/ryu/mailman/message/32333352/
            empty_match = parser.OFPMatch()
            # remove_table_flows() is in our main controller class
            flow_mod = simple_switch.remove_table_flows(switch.dp, 0, empty_match, [])
            switch.dp.send_msg(flow_mod)

            port_list = switch.ports
            for port in port_list:
                ofproto = switch.dp.ofproto
                mod = parser.OFPPortMod(datapath=switch.dp, port_no=port.port_no,
                                        hw_addr=port.hw_addr, config=0,
                                        mask=(ofproto.OFPPC_PORT_DOWN | ofproto.OFPPC_NO_RECV |
                                              ofproto.OFPPC_NO_FWD | ofproto.OFPPC_NO_PACKET_IN)
                                        )
                switch.dp.send_msg(mod)
        print("PORT DOWN:")
        print(ofproto.OFPPC_PORT_DOWN)

    @route('set_tables', '/set_tables', methods=['PUT'])
    def set_tables(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        try:
            json_in = json.loads(req.body) if req.body else {}
        except ValueError:
            raise Response(status=400)

        try:
            table_entries = json_in['table_entries']
        except Exception as e:
            return Response(status=500)

        for entry in table_entries:
            switch_id = entry['switch_id']
            src_ip = entry['src_ip']
            dst_ip = entry['dst_ip']
            out_port = entry['out_port']
            datapath = get_switch(simple_switch, switch_id)[0]
            if datapath is not None:
                parser = datapath.dp.ofproto_parser
                ofproto = datapath.dp.ofproto
                match = parser.OFPMatch(ipv4_src=src_ip, ipv4_dst=dst_ip, eth_type=ether.ETH_TYPE_IP)
                actions = [parser.OFPActionOutput(out_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                flow_mod = parser.OFPFlowMod(datapath=datapath.dp, priority=1,
                                             match=match, instructions=inst,
                                             command=ofproto.OFPFC_ADD)
                print("Set Table for switch: " + str(datapath.dp.id))
                datapath.dp.send_msg(flow_mod)
            else:
                print("DATAPATH IS NONE")
