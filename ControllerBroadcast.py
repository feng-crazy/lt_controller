#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 10:55
# @Author  : hedengfeng
# @Site    : 
# @File    : ControllerBroadcast.py
# @Software: LT_controller
import select
import time
from socket import *

from utility import message_pb2
# from eventbus.EventBus import EventBus
# from eventbus.EventClient import EventClient
from utility.LTCommon import LTEventType
from utility.NetWorkInfo import NetWorkInfo
from utility.Mlogging import MLog
from eventbus.EventTarget import EventTarget

operating_system_type = NetWorkInfo.get_platform()

global_local_ip_addr = None  # 该值并不可靠
# 程序要等到网络连接上，获取到id地址之后才开始

if operating_system_type == 'Windows':
    global_local_ip_addr = NetWorkInfo.get_ip_addr('以太网')
    if global_local_ip_addr is None:
        global_local_ip_addr = NetWorkInfo.get_ip_addr('WLAN')
elif operating_system_type == 'Linux':
    global_local_ip_addr = NetWorkInfo.get_ip_addr('wlan0')  # 优先使用无线
    if global_local_ip_addr is None:
        global_local_ip_addr = NetWorkInfo.get_ip_addr('eth0')

if global_local_ip_addr is None:
    global_local_ip_addr = '127.0.0.1'

print("global_local_ip_addr:", global_local_ip_addr)


class ControllerBroadcast(EventTarget):
    """控制器广播类"""
    PORT = NetWorkInfo.UDP_BROADCAST_PORT
    BUFSIZE = 512
    BROADCASE_DEST = ('<broadcast>', PORT)

    def __init__(self):
        super(ControllerBroadcast, self).__init__(self)

        self._udp_sock = socket(AF_INET, SOCK_DGRAM)
        # self._udp_sock.bind(ControllerBroadcast.ADDR)
        self._udp_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

        self.ip_addr = global_local_ip_addr
        self.terminal_port = NetWorkInfo.TERMINAL_PROT
        self.manager_port = NetWorkInfo.MANAGER_PROT
        self.loc_xsub_port = NetWorkInfo.LOC_XSUB_PORT
        self.loc_xpub_port = NetWorkInfo.LOC_XPUB_PORT
        self.__timeout = 10
        self.send_cast_str = None

        self._init_send_cast_str()

        self.subscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        # print('ControllerBroadcast ', 'event_handle', event)
        if event == LTEventType.EVENT_SYSTEM_TIME_1:
            # print('send Broadcast: time:', time.time())
            self._send_broadcast()

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
        super(ControllerBroadcast, self).__del__()

    def _init_send_cast_str(self):
        # 使用protobuf封装发送数据
        msg = message_pb2.ControllerBroadcast()
        msg.ip_addr = self.ip_addr
        msg.terminal_port = self.terminal_port
        msg.manager_port = self.manager_port
        msg.loc_xsub_port = self.loc_xsub_port
        msg.loc_xpub_port = self.loc_xpub_port
        # print('send msg: ', msg)
        self.send_cast_str = msg.SerializeToString()

    def _send_broadcast(self):
        """每秒发送广播"""
        self._udp_sock.sendto(self.send_cast_str, ControllerBroadcast.BROADCASE_DEST)

    def _recv_broadcase_rep(self):
        # 接收广播响应
        data, rep_addr = self._udp_sock.recvfrom(ControllerBroadcast.BUFSIZE)
        # print('_recv_broadcase_rep data: ', data, 'rep_addr: ', rep_addr)
        if not data:
            return None
        # 判断是终端响应还是manager响应
        msg_parse = message_pb2.BroadcastResponse()
        msg_parse.ParseFromString(data)
        # print(" BroadcastResponse: ", msg_parse)

        # 判断返回ip地址和响应的ip地址是否是同一个
        if msg_parse.ip_addr != rep_addr[0]:
            # MLog.mlogger.warn('rep ip addr error: %s, %s', msg_parse.ip_addr, rep_addr[0])
            if msg_parse.ip_addr == "0.0.0.0":
                msg_parse.ip_addr = rep_addr[0]
            else:
                return

        if msg_parse.ip_addr == '127.0.0.1':
            MLog.mlogger.warn('rep termnal ip addr error: %s', msg_parse.ip_addr)
            return

        msg = msg_parse.SerializeToString()
        # print('_recv_broadcase_rep msg: ', msg)

        if msg_parse.type == message_pb2.BroadcastResponse.TERMINAL_TYPE:  # 终端响应给终端控制器
            # print("publish_event(LTEventType.EVENT_RECV_TERM_CAST_REP) : ", msg_parse)
            event = LTEventType.EVENT_RECV_TERM_CAST_REP
            event_content = msg
            self.publish_event(event, event_content)
        elif msg_parse.type == message_pb2.BroadcastResponse.MANAGER_TYPE:  # Manager响应给主控
            # print("publish_event(LTEventType.EVENT_RECV_MANAGER_CAST_REP)")
            event = LTEventType.EVENT_RECV_MANAGER_CAST_REP
            event_content = msg
            self.publish_event(event, event_content)

    def handle_broadcast(self):
        readable, writeable, exceptional = select.select([self._udp_sock], [self._udp_sock], [self._udp_sock], self.__timeout)
        # print(readable, writeable, exceptional, time.time())
        if not (readable or writeable or exceptional):
            return
        for self._udp_sock in readable:
            self._recv_broadcase_rep()

        for self._udp_sock in exceptional:
            MLog.mlogger.error("Client:%s  Error." % str(self._udp_sock))


# def main_task_handle(event_client):
#     if event_client is not None:
#         event_client.handle_event()
#     s = sched.scheduler(time.time, time.sleep)  # scheduler的两个参数用法复杂,可以不做任何更改
#     s.enter(1, 1, main_task_handle, (event_client,))
#     s.run()
#
#
# if __name__ == '__main__':
#     eventbus = EventBus()
#     main_event_client = EventClient()
#     main_task_handle(main_event_client)
#     broadcast = ControllerBroadcast()
#     broadcast.handle_broadcast()
