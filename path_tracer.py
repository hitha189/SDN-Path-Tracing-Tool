#!/usr/bin/env python3
# path_tracer.py — Ryu Controller with Path Tracing Logic

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, icmp
from ryu.lib import mac
import time

class PathTracer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PathTracer, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.flow_paths = {}
        self.logger.info("=== PATH TRACER CONTROLLER STARTED ===")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.install_flow(datapath, priority=0, match=match, actions=actions)
        self.logger.info(f"Switch s{datapath.id} connected to controller")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        dst_mac = eth.dst
        src_mac = eth.src
        switch_id = datapath.id

        self.mac_to_port.setdefault(switch_id, {})
        self.mac_to_port[switch_id][src_mac] = in_port

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            key = (src_ip, dst_ip)

            if key not in self.flow_paths:
                self.flow_paths[key] = []

            if switch_id not in self.flow_paths[key]:
                self.flow_paths[key].append(switch_id)
                self.logger.info(
                    f"  [PATH] Packet {src_ip} → {dst_ip} "
                    f"passed through Switch s{switch_id}"
                )

            if len(self.flow_paths[key]) >= 3:
                self.print_path(src_ip, dst_ip)

        if dst_mac in self.mac_to_port.get(switch_id, {}):
            out_port = self.mac_to_port[switch_id][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self.install_flow(datapath, priority=1, match=match, actions=actions)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        )
        datapath.send_msg(out)

    def install_flow(self, datapath, priority, match, actions,
                     idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )
        datapath.send_msg(mod)

    def print_path(self, src_ip, dst_ip):
        key = (src_ip, dst_ip)
        if key in self.flow_paths:
            switches = self.flow_paths[key]
            switch_str = " → ".join([f"s{s}" for s in sorted(switches)])
            self.logger.info("=" * 50)
            self.logger.info(f"  TRACED PATH:")
            self.logger.info(f"  {src_ip} → {switch_str} → {dst_ip}")
            self.logger.info("=" * 50)
