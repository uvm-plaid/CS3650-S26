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
from collections import deque
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ether_types, tcp, icmp, dhcp, ipv4
from ryu.topology import event
from ryu.topology.switches import Switches
from ryu.topology.api import get_switch, get_link, get_all_link, get_all_switch
from ryu.controller import dpset
import requests
import time
from typing import Any
from Graph import DirectedGraph
from Node import KeyedNode

simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/mactable/{dpid}'
MAX_HOPS = 1000
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
        'topology': Switches
    }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchRest13, self).__init__(*args, **kwargs)
        kwargs.pop('topology', None)
        self.switches = {}
        wsgi = kwargs['wsgi']
        self.topology_api_app = self
        wsgi.register(SimpleSwitchController, {
            simple_switch_instance_name: self
        })

        self.graph = DirectedGraph()
        self.forwarding_tables = []
        self.forwarding_profiles = {}

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

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp, target_hw_addr, target_ip_addr):
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
        datapath = msg.datapath
        dpid = datapath.id
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]

        pkt_eth = pkt.get_protocol(ethernet.ethernet)
        if pkt_eth:
            dst_mac = pkt_eth.dst
            eth_type = pkt_eth.ethertype

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)

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

            d_ip = pkt_arp.dst_ip
            s_ip = pkt_arp.src_ip
            d_mac = pkt_arp.dst_mac
            s_mac = pkt_arp.src_mac

            in_port = msg.match['in_port']

            if d_ip not in self.ip_to_mac:   # ADDED GUARD
                return
            dst_addr = self.ip_to_mac[d_ip]

            self._handle_arp(datapath=datapath,
                             port=in_port,
                             pkt_ethernet=pkt.get_protocols(ethernet.ethernet)[0],
                             pkt_arp=pkt_arp,
                             target_hw_addr=dst_addr,
                             target_ip_addr=d_ip)
            return

        pkt_icmp = pkt.get_protocol(icmp.icmp)
        pkt_dhcp = pkt.get_protocol(dhcp.dhcp)
        if pkt_icmp:
            print("OTHER")
            print(pkt)
            for entry in self.forwarding_tables:
                switch_id = entry['switch_id']
                dst_ip = entry['dst_ip']
                out_port = entry['out_port']

                if dpid == switch_id and dst_ip == pkt_ipv4.dst:
                    match = parser.OFPMatch(ipv4_dst=dst_ip, eth_type=ether.ETH_TYPE_IP)
                    actions = [parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 1, match, actions)

                    requests.get("http://192.168.4." + str(dpid) + ":1142/green_light_on")
                    time.sleep(0.5)
                    requests.get("http://192.168.4." + str(dpid) + ":1142/green_light_off")

                    print("MATCH:")
                    print(match)

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
                    actions = [parser.OFPActionOutput(entry_port)]
                    match = parser.OFPMatch(in_port=port, eth_dst=entry_mac)
                    self.add_flow(datapath, 1, match, actions)

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

    @route('get_topology', '/get_topology', methods=['GET'])
    def retrieve_links(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        link_list = get_link(simple_switch)
        connected = []

        for link in link_list:
            connected.append([link.src.dpid, link.dst.dpid, link.src.port_no])

        for link in simple_switch.link_to_port:
            connected.append([link[0], link[1], simple_switch.link_to_port[link]])
            connected.append([link[1], link[0], -1])

        self.simple_switch_app.update_topology()

        return Response(content_type='application/json',
                        body=json.dumps({"connected": connected}))

    @route('get_topology_named', '/get_topology/{topology}', methods=['GET'])
    def retrieve_links_named(self, req, topology=None, **kwargs):
        filepath = f"./topologies/{topology}.json"
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return Response(content_type='application/json',
                            body=json.dumps({"connected": data["connected"]}))
        except FileNotFoundError:
            return Response(status=404)
        except Exception as e:
            return Response(status=500)

    @route('configlinks', '/configlinks', methods=['PUT'])
    def configure_links(self, req, **kwargs):
        try:
            json_in = req.json if req.body else {}
            print(json_in)
        except ValueError:
            raise Response(status=400)
        try:
            config_list = json_in['connected']
        except Exception as e:
            return Response(status=500)

        self.red_off(None)
        self.green_off(None)

        # Extract only switch-to-switch pairs (ignore host entries)
        config_pairs = [
            [entry[0], entry[1]]
            for entry in config_list
            if isinstance(entry[0], int) and isinstance(entry[1], int)
        ]

        simple_switch = self.simple_switch_app
        link_list = get_link(simple_switch)
        queue = []
        original_links = [(link.src.dpid, link.dst.dpid) for link in link_list]
        down_links = []

        for link in link_list:
            src = link.src.dpid
            dst = link.dst.dpid
            print(f"link src dpid={src} port={link.src.port_no} hw_addr={link.src.hw_addr}")
            print(f"link dst dpid={dst} port={link.dst.port_no} hw_addr={link.dst.hw_addr}")

            if ([src, dst] not in config_pairs) and ([dst, src] not in config_pairs):
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
                down_links.append((src, dst))

        original_links = set(original_links)
        down_links = set(down_links)
        up_links = original_links - down_links
        for link in up_links:
            requests.get("http://192.168.4." + str(link[0]) + ":1142/red_light_on")
            requests.get("http://192.168.4." + str(link[1]) + ":1142/red_light_on")

        for message in queue:
            message[1].send_msg(message[0])

        return Response(status=200)

    @route('reset_topology', '/reset_topology', methods=['GET'])
    def reset_links(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        switch_list = get_switch(simple_switch)
        for switch in switch_list:
            parser = switch.dp.ofproto_parser
            empty_match = parser.OFPMatch()
            flow_mod = simple_switch.remove_table_flows(switch.dp, 0, empty_match, [])
            switch.dp.send_msg(flow_mod)

            port_list = switch.ports
            for port in port_list:
                ofproto = switch.dp.ofproto
                mod = parser.OFPPortMod(datapath=switch.dp, port_no=port.port_no,
                                        hw_addr=port.hw_addr, config=0,
                                        mask=(ofproto.OFPPC_PORT_DOWN | ofproto.OFPPC_NO_RECV |
                                              ofproto.OFPPC_NO_FWD | ofproto.OFPPC_NO_PACKET_IN))
                switch.dp.send_msg(mod)
        print("PORT DOWN:")
        print(ofproto.OFPPC_PORT_DOWN)

    @route('reset_flow', '/reset_flow', methods=['GET'])
    def reset_flow(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        switch_list = get_switch(simple_switch)
        for switch in switch_list:
            parser = switch.dp.ofproto_parser
            port_list = switch.ports
            for port in port_list:
                ofproto = switch.dp.ofproto
                mod = parser.OFPPortMod(datapath=switch.dp, port_no=port.port_no,
                                        hw_addr=port.hw_addr, config=0,
                                        mask=(ofproto.OFPPC_PORT_DOWN | ofproto.OFPPC_NO_RECV |
                                              ofproto.OFPPC_NO_FWD | ofproto.OFPPC_NO_PACKET_IN))
                switch.dp.send_msg(mod)
        print("PORT DOWN:")
        print(ofproto.OFPPC_PORT_DOWN)

    def fetch_topology(self, url: str) -> dict[str, Any]:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    
    def parse_topology(self, raw: dict[str, Any],) -> tuple[dict[int, dict[int, int]], dict[str, int]]:
        topology: dict[int, dict[int, int]] = {}
        host_map: dict[str, int] = {}

        for link in raw.get("connected", []):
            if len(link) != 3:
                raise ValueError(f"Malformed link (expected 3 elements): {link}")

            src, dst, out_port = link

            src_is_host = isinstance(src, str)
            dst_is_host = isinstance(dst, str)

            if src_is_host and not dst_is_host:
                # ["169.254.20.158", 9, -1]  →  host attached to switch 9
                host_map[src] = int(dst)

            elif not src_is_host and not dst_is_host:
                # [5, 3, 1]  →  switch 5 reaches switch 3 via out-port 1
                src_id  = int(src)
                dst_id  = int(dst)
                port    = int(out_port)
                topology.setdefault(src_id, {})[port] = dst_id

            # switch → host links are intentionally skipped:
            # path tracing stops as soon as the destination switch is reached.

        return topology, host_map
    
    def build_lookup(self, table: dict) -> dict[tuple[int, str], int]:
        return {
            (e["switch_id"], e["dst_ip"]): e["out_port"]
            for e in table["table_entries"]
        }


    def trace_path(self,
        src_switch: int,
        dst_ip: str,
        lookup: dict[tuple[int, str], int],
        topology: dict[int, dict[int, int]],
        dst_switch: int,
    ):
        current = src_switch
        visited: set[int] = set()
        hops = 0

        while True:
            if current == dst_switch:
                return hops

            if current in visited or hops >= MAX_HOPS:
                return None           # loop or runaway path

            visited.add(current)

            out_port = lookup.get((current, dst_ip))
            if out_port is None:
                return None           # no matching rule — packet dropped

            next_switch = topology.get(current, {}).get(out_port)
            if next_switch is None:
                return None           # port leads nowhere — misconfigured topology

            hops += 1
            current = next_switch
    def bfs_shortest_hops(self,
        src_switch: int,
        dst_switch: int,
        topology: dict[int, dict[int, int]],
    ):
        if src_switch == dst_switch:
            return 0

        visited = {src_switch}
        queue   = deque([(src_switch, 0)])

        while queue:
            current, hops = queue.popleft()

            for next_switch in topology.get(current, {}).values():
                if next_switch == dst_switch:
                    return hops + 1
                if next_switch not in visited:
                    visited.add(next_switch)
                    queue.append((next_switch, hops + 1))

        return None
    
    def compute_hop_counts(self,
        submitted_table: dict[str, Any],
        topology_url: str,
    ) -> list[dict[str, Any]]:
        raw_topology       = self.fetch_topology(topology_url)
        topology, host_map = self.parse_topology(raw_topology)
        submitted_lookup   = self.build_lookup(submitted_table)

        dst_ips = {e["dst_ip"] for e in submitted_table["table_entries"]}
        all_ips = set(host_map.keys())

        results: list[dict[str, Any]] = []

        for src_ip in all_ips:
            for dst_ip in dst_ips:
                if src_ip == dst_ip:
                    continue

                src_switch = host_map.get(src_ip)
                dst_switch = host_map.get(dst_ip)

                if src_switch is None or dst_switch is None:
                    continue

                results.append({
                    "src_ip":         src_ip,
                    "dst_ip":         dst_ip,
                    "correct_hops":   self.bfs_shortest_hops(src_switch, dst_switch, topology),
                    "submitted_hops": self.trace_path(src_switch, dst_ip, submitted_lookup, topology, dst_switch),
                })

        return results
    
    @route('set_tables', '/set_tables', methods=['POST'])
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
        simple_switch.forwarding_tables = table_entries
        response = self.compute_hop_counts(json_in, topology_url = f"http://127.0.0.1:2222/get_topology")
        response = {"error": None, "hops": response}
        Response(content_type='application/json', body=json.dumps(response))



    @route('set_tables_named', '/set_tables/{topology}', methods=['POST'])
    def set_tables_named(self, req, topology=None, **kwargs):
        simple_switch = self.simple_switch_app
        try:
            json_in = json.loads(req.body) if req.body else {}
        except ValueError:
            raise Response(status=400)
        try:
            table_entries = json_in['table_entries']
        except Exception as e:
            return Response(status=500)

        simple_switch.forwarding_profiles[topology] = table_entries
        simple_switch.forwarding_tables = table_entries

        # Snapshot current live topology alongside the forwarding profile
        link_list = get_link(simple_switch)
        connected = []
        for link in link_list:
            connected.append([link.src.dpid, link.dst.dpid, link.src.port_no])
        for link in simple_switch.link_to_port:
            connected.append([link[0], link[1], simple_switch.link_to_port[link]])
            connected.append([link[1], link[0], -1])

        response = self.compute_hop_counts(json_in, topology_url = f"http://127.0.0.1:2222/get_topology/{topology}")
        response = {"error": None, "hops": response}
        return Response(content_type='application/json', body=json.dumps(response))

    @route('red_on', '/red_on', methods=['GET'])
    def red_on(self, req, **kwargs):
        for i in range(1, 12):
            switch_ip = "http://192.168.4." + str(i) + ":1142"
            requests.get(switch_ip + "/red_light_on")

    @route('red_off', '/red_off', methods=['GET'])
    def red_off(self, req, **kwargs):
        for i in range(1, 12):
            switch_ip = "http://192.168.4." + str(i) + ":1142"
            requests.get(switch_ip + "/red_light_off")

    @route('green_on', '/green_on', methods=['GET'])
    def green_on(self, req, **kwargs):
        for i in range(1, 12):
            switch_ip = "http://192.168.4." + str(i) + ":1142"
            requests.get(switch_ip + "/green_light_on")

    @route('green_off', '/green_off', methods=['GET'])
    def green_off(self, req, **kwargs):
        for i in range(1, 12):
            switch_ip = "http://192.168.4." + str(i) + ":1142"
            requests.get(switch_ip + "/green_light_off")

