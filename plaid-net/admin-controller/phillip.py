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

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ether_types
from ryu.topology import event
from ryu.topology.api import get_switch, get_link, get_all_link, get_all_switch
from ryu.controller import dpset

# import networkx as nx
UP = 1
DOWN = 0

simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/mactable/{dpid}'

link_list = []


class SimpleSwitchRest13(simple_switch_13.SimpleSwitch13):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'dpset': dpset.DPSet
    }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchRest13, self).__init__(*args, **kwargs)
        self.switches = {}
        wsgi = kwargs['wsgi']
        dpset = kwargs['dpset']

        wsgi.register(SimpleSwitchController,
                      {simple_switch_instance_name: self})
        self.topo_shape = TopoStructure()

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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch

        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        # print(in_port)

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        src_dpid = self.find_src_dpid(src)

    # if [src_dpid, dpid] in link_list || [dpid, src_dpid] in link_list:
    # placeholder until I can correctly find dpid:
    # if True:
    #    self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

    #    # learn a mac address to avoid FLOOD next time.
    #    self.mac_to_port[dpid][src] = in_port

    #    if dst in self.mac_to_port[dpid]:
    #        out_port = self.mac_to_port[dpid][dst]
    #    else:
    #        out_port = ofproto.OFPP_FLOOD

    #    actions = [parser.OFPActionOutput(out_port)]

    #    # install a flow to avoid packet_in next time
    #    if out_port != ofproto.OFPP_FLOOD:
    #        match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
    #        # verify if we have a valid buffer_id, if yes avoid to send both
    #        # flow_mod & packet_out
    #        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
    #            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
    #            return
    #        else:
    #            self.add_flow(datapath, 1, match, actions)
    #    data = None
    #    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
    #        data = msg.data

    # else:
    #    # functionally equal to dropping the packet; we're in a dead link
    #    actions = []

    # out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
    # in_port=in_port, actions=actions, data=data)
    # datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no

        ofproto = msg.datapath.ofproto

        if ev.msg.desc.hw_addr == '00:0e:c6:bf:83:cc':
            if reason == ofproto.OFPPR_ADD:
                print("button interface added")
                links = get_link(self)
                print(links)

                for link in links:
                    mod = ev.msg.datapath.ofproto_parser.OFPPortMod(
                        datapath=ev.msg.datapath, port_no=link.src.port_no, hw_addr=link.src.hw_addr,
                        config=0, mask=ofproto.OFPPC_PORT_DOWN
                    )
                    ev.msg.datapath.send_msg(mod)
                    mod = ev.msg.datapath.ofproto_parser.OFPPortMod(
                        datapath=ev.msg.datapath, port_no=link.dst.port_no, hw_addr=link.dst.hw_addr,
                        config=ofproto.OFPPC_PORT_DOWN, mask=ofproto.OFPPC_PORT_DOWN
                    )
                    ev.msg.datapath.send_msg(mod)
            elif reason == ofproto.OFPPR_DELETE:
                print("button interface removed\nlinks:")
                links = get_link(self)
                print(links)

                print("switches:")
                switches = get_switch(self)
                for switch in switches:
                    for port in switch.ports:
                        if port._state != ofproto_v1_3.OFPPS_LIVE:
                            mod = ev.msg.datapath.ofproto_parser.OFPPortMod(
                                datapath=ev.msg.datapath, port_no=port.port_no, hw_addr=port.hw_addr,
                                config=0, mask=(
                                        ofproto.OFPPC_PORT_DOWN |
                                        ofproto.OFPPC_NO_RECV |
                                        ofproto.OFPPC_NO_FWD |
                                        ofproto.OFPPC_NO_PACKET_IN
                                )
                            )
                            ev.msg.datapath.send_msg(mod)
                print(switches)

        else:
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

    @set_ev_cls(dpset.EventPortModify, MAIN_DISPATCHER)
    def port_modify_handler(self, ev):
        dp = ev.dp
        port_attr = ev.port
        dp_str = dpid_lib.dpid_to_str(dp.id)
        self.logger.info("\t ***switch dpid=%s"
                         "\n \t port_no=%d hw_addr=%s name=%s config=0x%08x "
                         "\n \t state=0x%08x curr=0x%08x advertised=0x%08x "
                         "\n \t supported=0x%08x peer=0x%08x curr_speed=%d max_speed=%d" %
                         (dp_str, port_attr.port_no, port_attr.hw_addr,
                          port_attr.name, port_attr.config,
                          port_attr.state, port_attr.curr, port_attr.advertised,
                          port_attr.supported, port_attr.peer, port_attr.curr_speed,
                          port_attr.max_speed))
        if port_attr.state == 1:
            self.topo_shape.print_links("Link Down")
            out = self.topo_shape.link_with_src_port(port_attr.port_no, dp.id)
            print("out" + str(out))
            if out is not None:
                print(self.topo_shape.find_shortest_path(out.src.dpid))
        elif port_attr.state == 0:
            self.topo_shape.topo_raw_links = get_all_link(self)  ### HERE ###
            print("Link count: " + str(len(self.topo_shape.topo_raw_links)))
            self.topo_shape.print_links("Link Up")
            # self.topo_shape.topo_raw_links = get_all_link(self)
            # self.topo_shape.print_links("Link Up")

    def remove_table_flows(self, datapath, table_id, match, instructions):
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(datapath, 0, 0, table_id, ofproto.OFPFC_DELETE, 0, 0, 1,
                                                      ofproto.OFPCML_NO_BUFFER, ofproto.OFPP_ANY, OFPG_ANY, 0, match,
                                                      instructions)
        return flow_mod


class TopoStructure():
    def __init__(self, *args, **kwargs):
        self.topo_raw_switches = []
        self.topo_raw_links = []
        self.topo_links = []

        # self.net = nx.DiGraph()

    def print_links(self, func_str=None):
        # Convert the raw link to list so that it is printed easily
        print(" \t" + str(func_str) + ": Current Links:")
        for l in self.topo_raw_links:
            print(" \t\t" + str(l))

    def print_switches(self, func_str=None):
        print(" \t" + str(func_str) + ": Current Switches:")
        for s in self.topo_raw_switches:
            print(" \t\t" + str(s))

    def switches_count(self):
        return len(self.topo_raw_switches)

    def convert_raw_links_to_list(self):
        # Build a  list with all the links [((srcNode,port), (dstNode, port))].
        # The list is easier for printing.
        self.lock.acquire()
        self.topo_links = [((link.src.dpid, link.src.port_no),
                            (link.dst.dpid, link.dst.port_no))
                           for link in self.topo_raw_links]
        self.lock.release()

    def convert_raw_switch_to_list(self):
        # Build a list with all the switches ([switches])
        self.lock.acquire()
        self.topo_switches = [(switch.dp.id, UP) for switch in self.topo_raw_switches]
        self.lock.release()

    """
    Adds the link to list of raw links
    """

    def bring_up_link(self, link):
        self.topo_raw_links.append(link)

    """
    Check if a link with specific nodes exists.
    """

    def check_link(self, sdpid, sport, ddpid, dport):
        for i, link in self.topo_raw_links:
            if ((sdpid, sport), (ddpid, dport)) == (
            (link.src.dpid, link.src.port_no), (link.dst.dpid, link.dst.port_no)):
                return True
        return False

    """
    Finds the shortest path from source s to destination d.
    Both s and d are switches.
    """

    def find_shortest_path(self, s):
        s_count = self.switches_count()
        s_temp = s
        visited = []
        shortest_path = {}

        while s_count != len(visited):
            print(visited)
            visited.append(s_temp)
            print(visited)
            print("s_temp 1: " + str(s_temp))
            for l in self.find_links_with_src(s_temp):
                print("\t" + str(l))
                if l.dst.dpid not in visited:
                    print("\t\tDPID dst: " + str(l.dst.dpid))
                    if l.src.dpid in shortest_path:
                        shortest_path[l.dst.dpid] += 1
                        print("\t\t\tdpid found. Count: " + str(shortest_path[l.dst.dpid]))
                    else:
                        print("\t\t\tdpid not found.")
                        shortest_path[l.dst.dpid] = 0
            print("shortest_path: " + str(shortest_path))
            min_val = min(shortest_path.itervalues())
            t = [k for k, v in shortest_path.iteritems() if v == min_val]
            s_temp = t[0]
            print("s_temp 2: " + str(s_temp) + "\n")
        return shortest_path

    """
    Finds the dpids of destinations where the links' source is s_dpid
    """

    def find_dst_with_src(self, s_dpid):
        d = []
        for l in self.topo_raw_links:
            if l.src.dpid == s_dpid:
                d.append(l.dst.dpid)
        return d

    """
    Finds the list of link objects where links' src dpid is s_dpid
    """

    def find_links_with_src(self, s_dpid):
        d_links = []
        for l in self.topo_raw_links:
            if l.src.dpid == s_dpid:
                d_links.append(l)
        return d_links

    """
    Returns a link object that has in_dpid and in_port as either source or destination dpid and port.
    """

    def link_with_src_dst_port(self, in_port, in_dpid):
        for l in self.topo_raw_links:
            if (l.src.dpid == in_dpid and l.src.port_no == in_port) or (
                    l.dst.dpid == in_dpid and l.src.port_no == in_port):
                return l
        return None

    """
    Returns a link object that has in_dpid and in_port as either source dpid and port.
    """

    def link_with_src_port(self, in_port, in_dpid):
        for l in self.topo_raw_links:
            if (l.src.dpid == in_dpid and l.src.port_no == in_port) or (
                    l.dst.dpid == in_dpid and l.src.port_no == in_port):
                return l
        return None


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

    @route('configlinks', '/configlinks', methods=['PUT'])
    def configure_links(self, req, **kwargs):

        global link_list
        try:
            json_in = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        try:
            link_list = json_in['connected']
            print(link_list)
            return Response(content_type='application/text', body="Accepted\n")
        except Exception as e:
            return Response(status=500)

    @route('configlinks', '/configlinks', methods=['GET'])
    def retrieve_links(self, req, **kwargs):

        body = '{"connected": ' + str(link_list) + '}'
        return Response(content_type='application/json', body=body)

    @route('resetlinks', '/resetlinks', methods=['GET'])
    def retrieve_links(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        switch_list = get_switch(simple_switch)
        for switch in switch_list:
            empty_match = ofproto_parser.OFPMatch()
            flow_mod = simple_switch.remove_table_flows(switch.dp, 0, empty_match, [])
            swith.dp.send_msg(flow_mod)
        print(get_link(simple_switch))

        '''
        iterate over switches
        delete all the flow
        bring up all the interfaces
        dump the links (get_links)
        '''
