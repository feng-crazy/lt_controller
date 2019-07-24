#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/2 14:51
# @Author  : hedengfeng
# @Site    : 
# @File    : ManagerDevice.py
# @Software: LT_controller
# @description: 与LTManager设备连接通信的类
import subprocess
import threading
import time
import traceback

import zmq

from utility import message_pb2
from utility.Mlogging import MLog
from utility.NetWorkInfo import NetWorkInfo
from eventbus.EventBus import EventBus
from eventbus.MThread import MThread
from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType
from utility.ZipUnzipFile import ZipUnzipFile


class ManagerDevice(MThread, EventTarget):
    """
    ManagerDevice 与LTManager设备连接通信的类
    """

    def __init__(self, thread_name):
        self.thread_name = thread_name

        self.context = EventBus.CONTEXT
        self._socket_rep = None
        self._rep_socket_addr_port = "tcp://*:" + str(NetWorkInfo.MANAGER_PROT)

        self.term_list_update_event = False
        self.term_property_list_serialize = b''
        self.base_list_update_event = False
        # self.active_bases_list_serialize = b''
        self.all_bases_list_serialize = b''

        self.term_except_status_list = []
        self.bases_except_status_list = []

        self.req_handle_map = {b'TerminalPropertyRequest': self._handle_term_pro,
                               b'TerminalActionRequest': self._handle_term_act,
                               b'BaseStationPropertyRequest': self._handle_bs_pro,
                               b'BaseStationActionRequest': self._handle_bs_act,
                               b'GuiHeartbeatRequest': self._handle_heartbeat,
                               b'LingTrackUpdateRequest': self._handle_update_request}

        self.mac_manager_addr_map = {}

        # 该类构造父类必须要最后
        MThread.__init__(self, self, thread_name)

    def thread_task(self):
        """
        线程主循环函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        """
        while self._socket_rep.poll(20):
            self.recv_request()

    def recv_request(self):
        """
        接收manager请求
        """
        msg = self._socket_rep.recv_multipart()
        # print('manager recv_request: ', msg)
        if msg[0] in self.req_handle_map:
            self.req_handle_map[msg[0]](msg[1])
        else:
            self.rep_request([b'Not Recognized title', msg[1]])

    def rep_request(self, msg):
        """响应manager请求"""
        # print('ManagerDevice rep_request:', msg)
        try:
            self._socket_rep.send_multipart(msg)
        except zmq.error.Again as err:
            MLog.mlogger.warn('ManagerDevice rep_request Exception: ', err)
            MLog.mlogger.warn(traceback.format_exc())

    def setup_thread(self):
        """
        子线程初始操作函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        """
        EventTarget.__init__(self, self)  # 该父类的构造必须是要再该线程执行中，最开始执行

        print('setup_thread...........', threading.current_thread(), self.thread_name)

        self.event_handle_sleep = 0.01
        self.thread_loop_sleep = 0

        self._socket_rep = self.context.socket(zmq.REP)
        self._socket_rep.setsockopt(zmq.LINGER, 0)
        self._socket_rep.setsockopt(zmq.SNDTIMEO, 5000)
        self._socket_rep.bind(self._rep_socket_addr_port)

        self.subscribe(LTEventType.EVENT_RECV_MANAGER_CAST_REP, self)
        self.subscribe(LTEventType.EVENT_TERMINAL_LIST_UPDATE, self)
        # self.subscribe(LTEventType.EVENT_ACTIVE_BASES_LIST_UPDATE, self)
        self.subscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        self.subscribe(LTEventType.EVENT_TERMINAL_EXCEPT_STATUS, self)
        self.subscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.subscribe(LTEventType.EVENT_BASES_EXCEPT_STATUS, self)

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        # print('manager event handle:', event, event_content)
        if event == LTEventType.EVENT_RECV_MANAGER_CAST_REP:
            # print('EVENT_RECV_MANAGER_CAST_REP event handle:', event, event_content)
            msg = message_pb2.BroadcastResponse()
            msg.ParseFromString(event_content)
            ip_addr = msg.ip_addr
            mac_addr = msg.mac_addr
            host_name = msg.host_name
            if mac_addr not in self.mac_manager_addr_map:
                manager_object = ManageTerminal(self, ip_addr, mac_addr, host_name)
                self.mac_manager_addr_map[mac_addr] = manager_object

        elif event == LTEventType.EVENT_TERMINAL_LIST_UPDATE:
            # print('manager event handle:', event, event_content)
            self.term_list_update_event = True
            self.term_property_list_serialize = event_content

        elif event == LTEventType.EVENT_ALL_BASES_LIST_UPDATE:
            # print('manager event handle:', event, event_content)
            self.base_list_update_event = True
            self.all_bases_list_serialize = event_content

        elif event == LTEventType.EVENT_TERMINAL_EXCEPT_STATUS:
            print('manager event handle:', event, event_content)
            term_except_status = message_pb2.TerminalExceptStatus()
            term_except_status.ParseFromString(event_content)
            self.term_except_status_list.append(term_except_status)

        elif event == LTEventType.EVENT_BASES_EXCEPT_STATUS:
            print('manager event handle:', event, event_content)
            bases_except_status = message_pb2.BasesExceptStatus()
            bases_except_status.ParseFromString(event_content)
            self.bases_except_status_list.append(bases_except_status)

        elif event == LTEventType.EVENT_SYSTEM_STARTUP:
            self.term_list_update_event = False
            self.base_list_update_event = False
            self.start()

    def _handle_term_pro(self, msg):
        """处理 TerminalPropertyRequest 消息"""
        msg_parse = message_pb2.TerminalPropertyRequest()
        msg_parse.ParseFromString(msg)
        # print('ManagerDevice TerminalPropertyRequest:', msg_parse)

        msg_str = b''
        if msg_parse.type == message_pb2.TerminalPropertyRequest.GET:
            msg_str = self.term_property_list_serialize

        if msg_parse.type == message_pb2.TerminalPropertyRequest.UPDATE:
            event = LTEventType.EVENT_UPDATE_TERMINAL_PRO
            event_content = msg
            self.publish_event(event, event_content)

            msg_pack = message_pb2.TerminalPropertyResponse()
            msg_pack.status.code = message_pb2.ResponseStatus.OK
            msg_str = msg_pack.SerializeToString()

        # print('ManagerDevice TerminalPropertyResponse:', msg_str)
        self.rep_request([b'TerminalPropertyResponse', msg_str])

    def _handle_term_act(self, msg):
        """处理终端的动作请求TerminalActionRequest"""
        msg_parse = message_pb2.TerminalActionRequest()
        msg_parse.ParseFromString(msg)
        print('ManagerDevice TerminalActionRequest:', msg_parse)

        event = LTEventType.EVENT_TERM_ACTION_REQUEST
        event_content = msg
        self.publish_event(event, event_content)

        msg_pack = message_pb2.TerminalActionResponse()
        msg_pack.sequence = msg_parse.sequence
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_str = msg_pack.SerializeToString()

        self.rep_request([b'TerminalActionResponse', msg_str])

    def _handle_update_request(self, msg):
        """处理终端的动作请求TerminalActionRequest"""
        msg_parse = message_pb2.LingTrackUpdateRequest()
        msg_parse.ParseFromString(msg)
        print('ManagerDevice LingTrackUpdateRequest:', msg_parse.type)

        msg_pack = message_pb2.LingTrackUpdateResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_str = msg_pack.SerializeToString()

        self.rep_request([b'LingTrackUpdateResponse', msg_str])

        if msg_parse.type == message_pb2.LingTrackUpdateRequest.UpdateType.TERMINAL_TYPE:
            event = LTEventType.EVENT_TERM_UPGRADE_REQUEST
            event_content = msg
            self.publish_event(event, event_content)

        if msg_parse.type == message_pb2.LingTrackUpdateRequest.UpdateType.BASES_TYPE:
            event = LTEventType.EVENT_BASE_UPGRADE_REQUEST
            event_content = msg
            self.publish_event(event, event_content)

        if msg_parse.type == message_pb2.LingTrackUpdateRequest.UpdateType.BASES_CTRLLER_TYPE:
            event = LTEventType.EVENT_BASE_CTRLLER_UPGRADE_REQUEST
            event_content = msg
            self.publish_event(event, event_content)

        if msg_parse.type == message_pb2.LingTrackUpdateRequest.UpdateType.MAIN_CTRLLER_TYPE:
            # 解压内容
            with open('update.zip', 'w', encoding='utf-8') as f:
                f.write(msg_parse.detail)
            f.close()
            ZipUnzipFile.unzip_file('update.zip', r'./')

            # 重启系统
            time.sleep(1)
            subprocess.Popen('sudo reboot', shell=True)

    def _handle_heartbeat(self, msg):
        """处理gui的心跳请求GuiHeartbeatRequest"""
        msg_parse = message_pb2.GuiHeartbeatRequest()
        msg_parse.ParseFromString(msg)
        # print('_handle_heartbeat:', msg_parse)
        mac_addr = msg_parse.mac_addr
        if mac_addr in self.mac_manager_addr_map:
            self.mac_manager_addr_map[mac_addr].handle_heartbeat(msg_parse)
            return

        msg_pack = message_pb2.GuiHeartbeatResponse()
        msg_pack.sequence = msg_parse.sequence
        msg_pack.status.code = message_pb2.ResponseStatus.OK

        if self.term_list_update_event:
            print('ManagerDevice _handle_heartbeat term_list_update_event:', self.term_list_update_event)
            msg_pack.event.event = message_pb2.UpdateEvent.TERMINAL_LIST_UPDATE
            self.term_list_update_event = False
        elif self.base_list_update_event:
            print('ManagerDevice _handle_heartbeat base_list_update_event:', self.base_list_update_event)
            msg_pack.event.event = message_pb2.UpdateEvent.BASE_STATION_LIST_UPDATE
            self.base_list_update_event = False

        if self.term_except_status_list:
            print('ManagerDevice _handle_heartbeat term_except_status_list:', self.term_except_status_list)
            msg_pack.term_except_status.extend(self.term_except_status_list)
            self.term_except_status_list.clear()

        if self.bases_except_status_list:
            print('ManagerDevice _handle_heartbeat bases_except_status_list:', self.bases_except_status_list)
            msg_pack.bases_except_status.extend(self.bases_except_status_list)
            self.bases_except_status_list.clear()

        msg_str = msg_pack.SerializeToString()
        self.rep_request([b'GuiHeartbeatResponse', msg_str])

    def _handle_bs_pro(self, msg):
        """处理基站的属性请求BaseStationPropertyRequest"""
        msg_parse = message_pb2.BaseStationPropertyRequest()
        msg_parse.ParseFromString(msg)
        print('ManagerDevice BaseStationPropertyRequest:', msg_parse)

        msg_pack = message_pb2.BaseStationPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_str = msg_pack.SerializeToString()

        if msg_parse.type == message_pb2.BaseStationPropertyRequest.UPDATE:
            event = LTEventType.EVENT_UPDATE_BASE_STATION_PRO
            event_content = msg
            self.publish_event(event, event_content)

        if msg_parse.type == message_pb2.BaseStationPropertyRequest.GET_ALL:
            msg_str = self.all_bases_list_serialize
            # msg_print = message_pb2.BaseStationPropertyResponse()
            # msg_print.ParseFromString(msg_str)
            # print('GET_ALL msg_send:', msg_print)

        if msg_parse.type == message_pb2.BaseStationPropertyRequest.APPEND:
            event = LTEventType.EVENT_BASE_STATION_APPEND_REQUEST
            event_content = msg
            self.publish_event(event, event_content)

        if msg_parse.type == message_pb2.BaseStationPropertyRequest.REMOVE:
            event = LTEventType.EVENT_BASE_STATION_REMOVE_REQUEST
            event_content = msg
            self.publish_event(event, event_content)

        self.rep_request([b'BaseStationPropertyResponse', msg_str])

    def _handle_bs_act(self, msg):
        """处理基站的动作请求BaseStationActionRequest"""
        msg_parse = message_pb2.BaseStationActionRequest()
        msg_parse.ParseFromString(msg)
        print('ManagerDevice BaseStationActionRequest:', msg_parse)

        act_command = msg_parse.command
        print('BasesController handle_act_request act_command:', act_command)
        # todo: 执行command命令 这个模式需要立即直接的返回，所以要在这里执行

        msg_pack = message_pb2.BaseStationActionResponse()
        msg_pack.sequence = msg_parse.sequence

        msg_pack.status.code = message_pb2.ResponseStatus.OK

        msg_pack.bs_info = ''  # todo:命令执行返回信息
        print('handle_act_request BaseStationActionResponse:', msg_pack)
        msg_str = msg_pack.SerializeToString()

        self.rep_request([b'BaseStationActionResponse', msg_str])

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_RECV_MANAGER_CAST_REP, self)
        self.unsubscribe(LTEventType.EVENT_TERMINAL_LIST_UPDATE, self)
        # self.unsubscribe(LTEventType.EVENT_ACTIVE_BASES_LIST_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_TERMINAL_EXCEPT_STATUS, self)
        self.unsubscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.unsubscribe(LTEventType.EVENT_BASES_EXCEPT_STATUS, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_CONNECT, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT, self)
        super(ManagerDevice, self).__del__()


class ManageTerminal(EventTarget):
    def __init__(self, manager_dev, ip_addr, mac_addr, host_name):
        print('ManageTerminal init:', ip_addr, mac_addr, host_name)
        super(ManageTerminal, self).__init__(self)
        self.manager_dev = manager_dev
        self.ip_addr = ip_addr
        self.mac_addr = mac_addr
        self.host_name = host_name
        self.term_list_update_event = False
        self.term_property_list_serialize = b''
        self.base_list_update_event = False
        # self.active_bases_list_serialize = b''
        self.all_bases_list_serialize = b''

        self.term_except_status_list = []
        self.bases_except_status_list = []

        self.subscribe(LTEventType.EVENT_TERMINAL_LIST_UPDATE, self)
        # self.subscribe(LTEventType.EVENT_ACTIVE_BASES_LIST_UPDATE, self)
        self.subscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        self.subscribe(LTEventType.EVENT_TERMINAL_EXCEPT_STATUS, self)
        self.subscribe(LTEventType.EVENT_BASES_EXCEPT_STATUS, self)

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        if event == LTEventType.EVENT_TERMINAL_LIST_UPDATE:
            # print('manager event handle:', event, event_content)
            self.term_list_update_event = True
            self.term_property_list_serialize = event_content

        elif event == LTEventType.EVENT_ALL_BASES_LIST_UPDATE:
            # print('manager event handle:', event, event_content)
            self.base_list_update_event = True
            self.all_bases_list_serialize = event_content

        elif event == LTEventType.EVENT_TERMINAL_EXCEPT_STATUS:
            print('manager event handle:', event, event_content)
            term_except_status = message_pb2.TerminalExceptStatus()
            term_except_status.ParseFromString(event_content)
            self.term_except_status_list.append(term_except_status)

        elif event == LTEventType.EVENT_BASES_EXCEPT_STATUS:
            print('manager event handle:', event, event_content)
            bases_except_status = message_pb2.BasesExceptStatus()
            bases_except_status.ParseFromString(event_content)
            self.bases_except_status_list.append(bases_except_status)

    def handle_heartbeat(self, msg_parse):
        """处理gui的心跳请求GuiHeartbeatRequest"""
        # print('handle_heartbeat:', self.mac_addr)
        msg_pack = message_pb2.GuiHeartbeatResponse()
        msg_pack.sequence = msg_parse.sequence
        msg_pack.status.code = message_pb2.ResponseStatus.OK

        if self.term_list_update_event:
            print('ManageTerminal _handle_heartbeat term_list_update_event:', self.term_list_update_event)
            msg_pack.event.event = message_pb2.UpdateEvent.TERMINAL_LIST_UPDATE
            self.term_list_update_event = False
        elif self.base_list_update_event:
            print('ManageTerminal _handle_heartbeat base_list_update_event:', self.base_list_update_event)
            msg_pack.event.event = message_pb2.UpdateEvent.BASE_STATION_LIST_UPDATE
            self.base_list_update_event = False

        if self.term_except_status_list:
            print('ManageTerminal _handle_heartbeat term_except_status_list:', self.term_except_status_list)
            msg_pack.term_except_status.extend(self.term_except_status_list)
            self.term_except_status_list.clear()

        if self.bases_except_status_list:
            print('ManageTerminal _handle_heartbeat bases_except_status_list:', self.bases_except_status_list)
            msg_pack.bases_except_status.extend(self.bases_except_status_list)
            self.bases_except_status_list.clear()

        msg_str = msg_pack.SerializeToString()
        self.manager_dev.rep_request([b'GuiHeartbeatResponse', msg_str])

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_TERMINAL_LIST_UPDATE, self)
        # self.unsubscribe(LTEventType.EVENT_ACTIVE_BASES_LIST_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_TERMINAL_EXCEPT_STATUS, self)
        self.unsubscribe(LTEventType.EVENT_BASES_EXCEPT_STATUS, self)
        super(ManageTerminal, self).__del__()

