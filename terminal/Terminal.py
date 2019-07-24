#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/2 16:13
# @Author  : hedengfeng
# @Site    : 
# @File    : Terminal.py
# @Software: Terminal
# @description: 终端类
import traceback

from configobj import ConfigObj
from utility import message_pb2

from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType
from utility.Mlogging import MLog


class Terminal(EventTarget):
    """
    Terminal
    """

    def __init__(self, ctrller, term_property):
        # print('Terminal.__init__', self)
        super(Terminal, self).__init__(self)

        self.ctrller = ctrller
        self.mac_addr = term_property.mac_addr
        self.ip_addr = term_property.ip_addr
        self.host_name = term_property.host_name
        self.sensor_list = term_property.sensor_list  # 所有传感器
        self.report_ip_addr = term_property.report_ip_addr  # 利用stream_socket类型，使用传统tcp连接汇报位置给远程主机
        self.report_tcp_port = term_property.report_tcp_port  # 远程主机端口
        self.raw_output_flag = term_property.raw_output_flag
        self.odom_parameters = term_property.odom_parameters
        self.odom_input_option = term_property.odom_input_option
        self.optic_data_input_dev = term_property.optic_data_input_dev
        self.loc_data_output_dev = term_property.loc_data_output_dev
        self.loc_data_output_protocol = term_property.loc_data_output_protocol

        self.config_file_name = 'terminal/config/' + self.mac_addr  # mac addr 是唯一标识，也是该终端配置文件的文件名
        self.config_obj = ConfigObj(self.config_file_name, encoding='UTF8')
        self.bases_config_file_path = 'basestation/basesConfig'

        self.config_file_update = ''
        self.action_request_from_gui = None  # type:message_pb2.TerminalActionRequest

        self.term_upgrade_request = None

        self.connect_timeout_cnt = 0  # 6秒没有连上，视为终端已经断开连接
        # self.all_bases_list_serialize = b''

        self.req_handle_map = {b'TerminalPropertyRequest': self._handle_term_update_req,
                               # b'BaseStationPropertyRequest': self._handle_bs_list_req,
                               b'TerminalHeartbeatRequest': self.heartbeat_msg_handle}

        self.subscribe(LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE, self)
        self.subscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
        # self.subscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        # self.subscribe(LTEventType.EVENT_TERM_UPGRADE_REQUEST, self)

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        if event == LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE:
            print('Terminal ', 'event_handle', event)
            self.handle_bases_config_update()

        elif event == LTEventType.EVENT_SYSTEM_TIME_1:
            self.connect_timeout_cnt += 1
            if self.connect_timeout_cnt > 60:  # 15秒说明终端断开连接，发送终端断开连接消息
                self.terminal_disconnect()

        # elif event == LTEventType.EVENT_ALL_BASES_LIST_UPDATE:
        #     self.all_bases_list_serialize = event_content

    def handle_bases_config_update(self):
        """
        处理基站配置更新事件
        """
        print('Terminal handle_bases_config_update', self.mac_addr)
        try:
            bases_config_obj = ConfigObj(self.bases_config_file_path, encoding='UTF8')
            self.config_obj['BS_GROUP'] = bases_config_obj['BS_GROUP']
            self.config_obj['BS_FREQS'] = bases_config_obj['BS_FREQS']
            self.config_obj['BS_ADDRS'] = bases_config_obj['BS_ADDRS']
            self.config_obj['BS_LOCATIONS'] = bases_config_obj['BS_LOCATIONS']
            self.config_obj['BS_START_ANGLES'] = bases_config_obj['BS_START_ANGLES']
            self.config_obj['BS_ORIENTATIONS'] = bases_config_obj['BS_ORIENTATIONS']
            self.config_obj['BS_INFO'] = bases_config_obj['BS_INFO']
            self.config_obj.write()
            self.config_obj.reload()
        except KeyError as err:
            MLog.mlogger.warn('Terminal handle_bases_config_update err:%s', err)
            MLog.mlogger.warn(traceback.format_exc())

        with open(self.config_file_name, 'r', encoding='utf-8') as f:
            self.config_file_update = f.read()

    def terminal_request_handle(self, msg, msg_content):
        if msg in self.req_handle_map:
            self.req_handle_map[msg](msg_content)
        else:
            self.ctrller.rep_request([b'Not Recognized title', msg])

    def heartbeat_msg_handle(self, msg_content):
        """
        msg处理函数，
        """
        self.connect_timeout_cnt = 0  # 连接超时计数清理
        req_msg = message_pb2.TerminalHeartbeatRequest()
        req_msg.ParseFromString(msg_content)

        if req_msg.sequence == 0:  # 说明第一次连上，需要将配置发送到终端
            with open(self.config_file_name, 'r', encoding='utf-8') as f:
                self.config_file_update = f.read()

        if not req_msg.ok_status:
            except_status = req_msg.except_status_detail
            print('Terminal heartbeat_msg_handle except_status:', except_status, self.mac_addr)
            event = LTEventType.EVENT_TERMINAL_EXCEPT_STATUS
            event_content = except_status.SerializeToString()
            self.publish_event(event, event_content)

        self.reponse_heartbeat_msg(req_msg)

    def reponse_heartbeat_msg(self, req_msg):
        rep_msg = message_pb2.TerminalHeartbeatResponse()
        rep_msg.sequence = req_msg.sequence
        rep_msg.status.code = message_pb2.ResponseStatus.OK
        if self.config_file_update:
            print('Terminal reponse_heartbeat_msg config_file_update:', self.mac_addr)
            rep_msg.event.event = message_pb2.UpdateEvent.CONFIG_UPDATE
            rep_msg.event.detail = self.config_file_update

        if self.action_request_from_gui is not None:
            print('Terminal reponse_heartbeat_msg action_request_from_gui:', self.action_request_from_gui,
                  self.mac_addr)
            rep_msg.action_request_from_gui.CopyFrom(self.action_request_from_gui)

        if self.term_upgrade_request is not None:
            print('Terminal reponse_heartbeat_msg term_upgrade_request:')
            rep_msg.update_request.CopyFrom(self.term_upgrade_request)

        # print('terminal reponse_heartbeat_msg:', rep_msg)
        rep_data = rep_msg.SerializeToString()
        # print('reponse_heartbeat_msg :', rep_msg)
        ret = self.ctrller.rep_request([b'TerminalHeartbeatResponse', rep_data])
        if ret is True:
            self.config_file_update = ''
            self.action_request_from_gui = None
            self.term_upgrade_request = None

    # def _handle_bs_list_req(self, msg):
    #     """处理基站的属性请求BaseStationPropertyRequest"""
    #     msg_parse = message_pb2.BaseStationPropertyRequest()
    #     msg_parse.ParseFromString(msg)
    #     print('Terminal BaseStationPropertyRequest:', msg_parse)
    #
    #     if msg_parse.type == message_pb2.BaseStationPropertyRequest.GET_ALL:
    #         msg_str = self.all_bases_list_serialize
    #         ret = self.ctrller.rep_request([b'BaseStationPropertyResponse', msg_str])
    #         if ret is True:
    #             self.all_bases_list_serialize = b''

    def _handle_term_update_req(self, msg_content):
        # print('Terminal _handle_term_update_req:')
        self.connect_timeout_cnt = 0
        msg_parse = message_pb2.TerminalPropertyRequest()
        msg_parse.ParseFromString(msg_content)

        if msg_parse.type == message_pb2.TerminalPropertyRequest.UPDATE:
            self.ctrller.update_term_property_list(msg_content)
        else:
            print("_handle_term_update_req is not Update")

        msg_pack = message_pb2.TerminalPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_str = msg_pack.SerializeToString()

        # print('ManagerDevice TerminalPropertyResponse:', msg_str)
        self.ctrller.rep_request([b'TerminalPropertyResponse', msg_str])

    def update_property(self, term_property):
        """
        更新终端属性,到配置文件
        :param term_property: message_pb2.TerminalProperty
        """
        print('Terminal update_property TerminalProperty:', self.mac_addr)
        try:
            if self.judge_terminal_equal(term_property) is True:
                return False
            self.ip_addr = term_property.ip_addr
            self.host_name = term_property.host_name
            self.sensor_list = term_property.sensor_list
            self.report_ip_addr = term_property.report_ip_addr
            self.report_tcp_port = term_property.report_tcp_port
            self.raw_output_flag = term_property.raw_output_flag
            self.odom_parameters = term_property.odom_parameters
            self.odom_input_option = term_property.odom_input_option
            self.optic_data_input_dev = term_property.optic_data_input_dev
            self.loc_data_output_dev = term_property.loc_data_output_dev
            self.loc_data_output_protocol = term_property.loc_data_output_protocol

            channel_str = []
            offset_str = []
            height = ''
            for sensor in term_property.sensor_list:
                channel_str.append(str(sensor.active))
                offset_str.extend([sensor.coordinates.x, sensor.coordinates.y, sensor.coordinates.z])
                height = str(sensor.height)

            self.config_obj['RECEIVER_HEIGHT'] = height
            if len(channel_str) == 1:
                self.config_obj['SENSOR_CHANNELS'] = channel_str[0]
            else:
                self.config_obj['SENSOR_CHANNELS'] = channel_str
            self.config_obj['SENSOR_OFFSETS'] = offset_str

            # report_ip_addr = '127.0.0.1'
            # if term_property.HasField('report_ip_addr'):
            report_ip_addr = term_property.report_ip_addr[0]
            self.config_obj['REMOTE_MONITOR_ADDR'] = report_ip_addr

            # report_tcp_port = 6000
            # if term_property.HasField('report_tcp_port'):
            report_tcp_port = term_property.report_tcp_port[0]
            self.config_obj['REMOTE_MONITOR_PORT'] = report_tcp_port
            self.config_obj['RAW_OUTPUT_FLAG'] = self.raw_output_flag
            self.config_obj['TERM_NAME'] = self.host_name
            self.config_obj['ODOM_PARAMETERS'] = self.odom_parameters
            self.config_obj['ODOM_INPUT_OPTION'] = self.odom_input_option
            self.config_obj['OPTIC_DATA_INPUT_DEV'] = self.optic_data_input_dev
            self.config_obj['LOC_DATA_OUTPUT_DEV'] = self.loc_data_output_dev
            self.config_obj['LOC_DATA_OUTPUT_PROTOCOL'] = self.loc_data_output_protocol
            # print('write TERM_NAME :', term_property.host_name)
            self.config_obj.write()
            self.config_obj.reload()
        except KeyError as err:
            MLog.mlogger.warn('Terminal update_property err:%s ', err)
            MLog.mlogger.warn(traceback.format_exc())

        with open(self.config_file_name, 'r', encoding='utf-8') as f:
            self.config_file_update = f.read()
            # print('Terminal update_property:',  self.config_file_update, self.mac_addr)

    def judge_terminal_equal(self, term_property):
        if self.host_name != term_property.host_name:
            print("judge_terminal_equal host_name", self.host_name)
            return False

        if len(self.sensor_list) != len(term_property.sensor_list):
            print("judge_terminal_equal len(self.sensor_list)", self.sensor_list)
            return False
        if self.judge_sensor_equal(term_property.sensor_list) is not True:
            return False

        if self.report_ip_addr[0] != term_property.report_ip_addr[0]:
            print("judge_terminal_equal report_ip_addr", self.report_ip_addr)
            return False
        if self.report_tcp_port[0] != term_property.report_tcp_port[0]:
            print("judge_terminal_equal report_tcp_port", self.report_tcp_port)
            return False
        if self.raw_output_flag != term_property.raw_output_flag:
            print("judge_terminal_equal raw_output_flag", self.raw_output_flag)
            return False
        if self.odom_parameters != term_property.odom_parameters:
            print("judge_terminal_equal odom_parameters", self.odom_parameters)
            return False
        if self.odom_input_option != term_property.odom_input_option:
            print("judge_terminal_equal odom_input_option", self.odom_input_option)
            return False
        if self.optic_data_input_dev != term_property.optic_data_input_dev:
            print("judge_terminal_equal optic_data_input_dev", self.optic_data_input_dev)
            return False
        if self.loc_data_output_dev != term_property.loc_data_output_dev:
            print("judge_terminal_equal loc_data_output_dev", self.loc_data_output_dev)
            return False
        if self.loc_data_output_protocol != term_property.loc_data_output_protocol:
            print("judge_terminal_equal loc_data_output_protocol", self.loc_data_output_protocol)
            return False
        # print("judge_terminal_equal is True", self.host_name)
        return True

    def judge_sensor_equal(self, sensor_list):
        for i in range(0, len(sensor_list)):
            if self.sensor_list[i].index != sensor_list[i].index:
                print("judge_terminal_equal sensor_list[i].index", self.sensor_list[i].index)
                return False
            if self.sensor_list[i].active != sensor_list[i].active:
                print("judge_terminal_equal sensor_list[i].active", self.sensor_list[i].active)
                return False
            if self.sensor_list[i].height != sensor_list[i].height:
                print("judge_terminal_equal sensor_list[i].height", self.sensor_list[i].height)
                return False
            if self.sensor_list[i].coordinates.x != sensor_list[i].coordinates.x:
                print("judge_terminal_equal sensor_list[i].coordinates.x", self.sensor_list[i].coordinates.x)
                return False
            if self.sensor_list[i].coordinates.y != sensor_list[i].coordinates.y:
                print("judge_terminal_equal sensor_list[i].coordinates.y", self.sensor_list[i].coordinates.y)
                return False
            if self.sensor_list[i].coordinates.z != sensor_list[i].coordinates.z:
                print("judge_terminal_equal sensor_list[i].coordinates.z", self.sensor_list[i].coordinates.z)
                return False
        return True

    def act_msg_handle(self, msg_parse):
        """
        将TerminalActionRequest赋值在终端心跳包响应中发送到终端
        :param msg_parse:message_pb2.TerminalActionRequest
        """
        print('Terminal act_msg_handle TerminalActionRequest', msg_parse, self.mac_addr)
        self.action_request_from_gui = msg_parse

    def upgrade_msg_handle(self, msg_parse):
        """
        将LingTrackUpdateRequest赋值在终端心跳包响应中发送到终端
        :param msg_parse:message_pb2.LingTrackUpdateRequest
        """
        print('Terminal upgrade_msg_handle LingTrackUpdateRequest')
        self.term_upgrade_request = msg_parse

    def cancel_subscribe(self):
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
        # self.unsubscribe(LTEventType.EVENT_ALL_BASES_LIST_UPDATE, self)
        # self.unsubscribe(LTEventType.EVENT_TERM_UPGRADE_REQUEST, self)

    def __del__(self):
        print('Terminal __del__...........', self)
        super(Terminal, self).__del__()

    def terminal_disconnect(self):
        self.connect_timeout_cnt = 0
        event = LTEventType.EVENT_A_TERMINAL_DISCONNECT
        event_content = self.mac_addr.encode()
        self.publish_event(event, event_content)
        print('Terminal publish_event EVENT_A_TERMINAL_DISCONNECT')
        self.cancel_subscribe()  # 需要移除注册，这个类才能自动注销
