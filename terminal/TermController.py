#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 10:50
# @Author  : hedengfeng
# @Site    : 
# @File    : termContorller.py
# @Software: LT_controller
import csv
import os
import shutil
import threading
import time
import traceback

import zmq
from configobj import ConfigObj

from utility import message_pb2
from utility.Mlogging import MLog
from utility.NetWorkInfo import NetWorkInfo
from eventbus.EventBus import EventBus
from eventbus.MThread import MThread
from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType

from terminal.Terminal import Terminal


class TermController(MThread, EventTarget):
    """
    TermDataHandle 终端接收controller数据处理类
    """

    def __init__(self, thread_name):
        self.thread_name = thread_name

        self.context = EventBus.CONTEXT
        self._socket_rep = None
        self._rep_socket_addr_port = "tcp://*:" + str(NetWorkInfo.TERMINAL_PROT)

        self.term_property_list = []  # type message_pb2.TerminalProperty list
        self.mac_term_obj_map = {}  # Mac地址和终端对象的一个map

        self.default_config_file_path = 'terminal/termConfig'
        self.default_config_obj = ConfigObj(self.default_config_file_path, encoding='UTF8')
        self.default_term_property = None

        self.term_config_file_list = []  # 配置文件和终端识别，只以MAC为唯一标识,有配置文件终端MAC地址列表

        self.bases_config_file_path = 'basestation/basesConfig'

        self._init_default_term_property()
        self._init_term_config_file_list()
        # 该类构造父类必须要最后
        MThread.__init__(self, self, thread_name)

    def _init_term_config_file_list(self):
        """有一些终端保存在配置文件中了，启动需要进行初始化操作,遍历config目录"""
        self.term_config_file_list = os.listdir('terminal/config')

    def _init_default_term_property(self):
        """初始化默认终端属性和termConfig文件保持一致"""
        term_property = message_pb2.TerminalProperty()
        term_property.ip_addr = ''
        term_property.mac_addr = ''
        term_property.host_name = ''
        sensor = term_property.sensor_list.add()
        sensor.index = 0
        sensor.active = 1
        sensor.height = 2
        sensor.coordinates.x = 0
        sensor.coordinates.y = 0
        sensor.coordinates.y = 0
        term_property.report_ip_addr.extend(['127.0.0.1'])
        term_property.report_tcp_port.extend([6000])
        term_property.raw_output_flag = 0
        term_property.odom_parameters = ""
        term_property.odom_input_option = 0
        term_property.optic_data_input_dev = 0
        term_property.loc_data_output_dev = 0
        term_property.loc_data_output_protocol = 0

        self.default_term_property = term_property

    def rep_request(self, msg):
        """响应请求"""
        # print('TermController rep_request:', msg)
        try:
            self._socket_rep.send_multipart(msg)
            return True
        except zmq.error.Again as err:
            MLog.mlogger.warn('TermController rep_request Exception: ', err)
            MLog.mlogger.warn(traceback.format_exc())
            return False
        # print('-----------------------------------rep_request send end')

    def recv_request(self):
        """
        接收manager请求,接收的数据分为三个部分，1、终端的MAC地址标识，2、msg的类型字符，3、msg的内容
        """
        data = self._socket_rep.recv_multipart()
        # print('recv term request: ', data)
        mac_addr = data[0].decode()
        try:
            if mac_addr in self.mac_term_obj_map:
                self.mac_term_obj_map[mac_addr].terminal_request_handle(data[1], data[2])  # 找到对应的终端处理
            else:  # 不支持的终端请求，通知终端没有收到广播包响应
                print(" mac_addr not in self.mac_term_obj_map:", mac_addr)

                rep_msg = message_pb2.TerminalHeartbeatResponse()
                rep_msg.sequence = -1
                rep_msg.status.code = message_pb2.ResponseStatus.TERMINAL_NOTFOUND
                rep_data = rep_msg.SerializeToString()
                self.rep_request([b'TerminalHeartbeatResponse', rep_data])
        except Exception as err:
            MLog.mlogger.warn('Exception as err:%s', err)
            self.rep_request(data)

    def thread_task(self):
        """
        线程主循环函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        """
        # print('TerController thread_task recv_request')
        if len(self.mac_term_obj_map) != 0:
            while self._socket_rep.poll(20):
                self.recv_request()

        # time.sleep(0.001)

    def setup_thread(self):
        """
        子线程初始操作函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        """
        EventTarget.__init__(self, self)  # 该父类的构造必须是要再该线程执行中，最开始执行

        print('setup_thread...........', threading.current_thread(), self.thread_name)

        self.event_handle_sleep = 0
        self.thread_loop_sleep = 0

        self._socket_rep = self.context.socket(zmq.REP)
        self._socket_rep.setsockopt(zmq.LINGER, 0)
        self._socket_rep.setsockopt(zmq.SNDTIMEO, 2000)
        self._socket_rep.bind(self._rep_socket_addr_port)

        event = LTEventType.EVENT_TERMINAL_LIST_UPDATE
        event_content = self.get_term_property_list()
        self.publish_event(event, event_content)

        self.subscribe(LTEventType.EVENT_RECV_TERM_CAST_REP, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE, self)
        self.subscribe(LTEventType.EVENT_A_TERMINAL_DISCONNECT, self)
        self.subscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.subscribe(LTEventType.EVENT_UPDATE_TERMINAL_PRO, self)
        self.subscribe(LTEventType.EVENT_TERM_ACTION_REQUEST, self)
        self.subscribe(LTEventType.EVENT_TERM_UPGRADE_REQUEST, self)

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        # print('TermConftorller event handle:', event, event_content)
        if event == LTEventType.EVENT_RECV_TERM_CAST_REP:
            # print('TermController event handle:', event, event_content)
            self.handle_recv_cast_event(event_content)

        elif event == LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE:
            self.handle_bases_config_update()

        elif event == LTEventType.EVENT_A_TERMINAL_DISCONNECT:
            self.handle_term_disconnect_event(event_content)

        elif event == LTEventType.EVENT_SYSTEM_STARTUP:
            self.start()

        elif event == LTEventType.EVENT_UPDATE_TERMINAL_PRO:
            self.update_term_property_list(event_content)

        elif event == LTEventType.EVENT_TERM_ACTION_REQUEST:
            self.handle_act_request(event_content)

        elif event == LTEventType.EVENT_TERM_UPGRADE_REQUEST:
            self.handle_upgrade_request(event_content)

    def handle_term_disconnect_event(self, event_content):
        """
        处理某一个终端断开连接事件
        """
        mac_addr = event_content.decode()
        print('handle_term_disconnect_event:%s' % mac_addr)
        for term_property in self.term_property_list:
            if term_property.mac_addr == mac_addr:
                self.term_property_list.remove(term_property)
                break
        # print('handle_term_disconnect_event term_property_list: ', self.term_property_list)
        if mac_addr in self.mac_term_obj_map:
            del self.mac_term_obj_map[mac_addr]

        # print('handle_term_disconnect_event mac_term_obj_map: ', self.mac_term_obj_map)
        event = LTEventType.EVENT_TERMINAL_LIST_UPDATE
        event_content = self.get_term_property_list()
        self.publish_event(event, event_content)

        self.write_ip_list_to_csv()

    def handle_recv_cast_event(self, event_content):
        """
        处理收到终端广播响应事件
        :param event_content:
        """
        msg = message_pb2.BroadcastResponse()
        msg.ParseFromString(event_content)
        ip_addr = msg.ip_addr
        mac_addr = msg.mac_addr
        host_name = msg.host_name

        # print('handle_recv_cast_event : ', ip_addr, mac_addr, host_name)
        if mac_addr not in self.mac_term_obj_map:  # 构建MAC地址和对应终端的MAP
            file_name = self.find_term_config(mac_addr)
            if not file_name:  # 找不到该终端的配置文件
                self.create_new_terminal(ip_addr, mac_addr, host_name)
            else:
                self.create_old_terminal(ip_addr, mac_addr, host_name, file_name)

            # 因为 每次连接上 终端都会发送配置上来，到那时在发送list更新事件
            # event = LTEventType.EVENT_TERMINAL_LIST_UPDATE
            # event_content = self.get_term_property_list()
            # self.publish_event(event, event_content)
            # self.write_ip_list_to_csv()

    def write_ip_list_to_csv(self):
        csv_file = open("terminal/current_ip_list.csv", "w", newline='')
        writer = csv.writer(csv_file)

        # 写入的内容都是以列表的形式传入函数
        for term_property in self.term_property_list:
            writer.writerow([term_property.ip_addr])
        csv_file.close()

    def handle_bases_config_update(self):
        """
        处理基站配置更新事件
        """
        print('TermConftorller handle_bases_config_update :')
        try:
            bases_config_obj = ConfigObj(self.bases_config_file_path, encoding='UTF8')
            self.default_config_obj['BS_GROUP'] = bases_config_obj['BS_GROUP']
            self.default_config_obj['BS_FREQS'] = bases_config_obj['BS_FREQS']
            self.default_config_obj['BS_ADDRS'] = bases_config_obj['BS_ADDRS']
            self.default_config_obj['BS_LOCATIONS'] = bases_config_obj['BS_LOCATIONS']
            self.default_config_obj['BS_START_ANGLES'] = bases_config_obj['BS_START_ANGLES']
            self.default_config_obj['BS_ORIENTATIONS'] = bases_config_obj['BS_ORIENTATIONS']
            self.default_config_obj['BS_INFO'] = bases_config_obj['BS_INFO']
            self.default_config_obj.write()
            self.default_config_obj.reload()
        except KeyError as err:
            MLog.mlogger.warn('TermController handle_bases_config_update err :%s', err)
            MLog.mlogger.warn(traceback.format_exc())

    def find_term_config(self, mac_addr):
        """
        :param mac_addr:  MAC addr str
        :return: find file succes return file name ,else return ''
        """
        # print('find_term_config:', self.term_config_file_list)
        for file_name in self.term_config_file_list:
            if mac_addr == file_name:
                return file_name
        return ''

    def copy_cur_base_config(self, config_obj):
        try:
            config_obj['BS_GROUP'] = self.default_config_obj['BS_GROUP']
            config_obj['BS_FREQS'] = self.default_config_obj['BS_FREQS']
            config_obj['BS_ADDRS'] = self.default_config_obj['BS_ADDRS']
            config_obj['BS_LOCATIONS'] = self.default_config_obj['BS_LOCATIONS']
            config_obj['BS_START_ANGLES'] = self.default_config_obj['BS_START_ANGLES']
            config_obj['BS_ORIENTATIONS'] = self.default_config_obj['BS_ORIENTATIONS']
            config_obj['BS_INFO'] = self.default_config_obj['BS_INFO']
            config_obj.write()
            config_obj.reload()
        except KeyError as err:
            MLog.mlogger.warn('TermController copy_cur_base_config err:%s ', err)
            MLog.mlogger.warn(traceback.format_exc())

    def convert_config_to_property(self, config_obj, ip_addr, mac_addr, host_name):
        """
        将终端的配置转化为message_pb2.TerminalProperty
        :param config_obj:
        :param ip_addr:
        :param mac_addr:
        :param host_name:
        :return:
        """
        try:
            term_property = message_pb2.TerminalProperty()
            term_property.ip_addr = ip_addr
            term_property.mac_addr = mac_addr
            term_property.host_name = host_name

            channel_list = config_obj['SENSOR_CHANNELS']
            offset_list = config_obj['SENSOR_OFFSETS']
            report_ip_addr_list = config_obj['REMOTE_MONITOR_ADDR']
            report_tcp_port_list = config_obj['REMOTE_MONITOR_PORT']
            recv_height = config_obj['RECEIVER_HEIGHT']

            if type(channel_list) == list:
                for i in range(0, len(channel_list)):
                    sensor = term_property.sensor_list.add()
                    sensor.index = i
                    sensor.active = int(channel_list[i])
                    sensor.height = float(recv_height)
                    sensor.coordinates.x = float(offset_list[3*i])
                    sensor.coordinates.y = float(offset_list[3*i + 1])
                    sensor.coordinates.z = float(offset_list[3*i + 2])
            else:
                sensor = term_property.sensor_list.add()
                sensor.index = 0
                sensor.active = int(channel_list)
                sensor.height = float(recv_height)
                sensor.coordinates.x = float(offset_list[0])
                sensor.coordinates.y = float(offset_list[1])
                sensor.coordinates.z = float(offset_list[2])

            if type(report_ip_addr_list) == list:
                for report_ip_addr in report_ip_addr_list:
                    term_property.report_ip_addr.extend([report_ip_addr])
            else:
                term_property.report_ip_addr.extend([report_ip_addr_list])

            if type(report_tcp_port_list) == list:
                for report_tcp_port in report_tcp_port_list:
                    term_property.report_tcp_port.extend([int(report_tcp_port)])
            else:
                term_property.report_tcp_port.extend([int(report_tcp_port_list)])

            if 'RAW_OUTPUT_FLAG' in config_obj:
                term_property.raw_output_flag = int(config_obj['RAW_OUTPUT_FLAG'])
            else:
                term_property.raw_output_flag = 0

            if 'ODOM_PARAMETERS' in config_obj:
                term_property.odom_parameters = config_obj['ODOM_PARAMETERS']
            else:
                term_property.odom_parameters = ''

            if 'ODOM_INPUT_OPTION' in config_obj:
                term_property.odom_input_option = int(config_obj['ODOM_INPUT_OPTION'])
            else:
                term_property.odom_input_option = 0

            if 'OPTIC_DATA_INPUT_DEV' in config_obj:
                term_property.optic_data_input_dev = int(config_obj['OPTIC_DATA_INPUT_DEV'])
            else:
                term_property.optic_data_input_dev = 0

            if 'LOC_DATA_OUTPUT_DEV' in config_obj:
                term_property.loc_data_output_dev = int(config_obj['LOC_DATA_OUTPUT_DEV'])
            else:
                term_property.loc_data_output_dev = 0

            if 'LOC_DATA_OUTPUT_PROTOCOL' in config_obj:
                term_property.loc_data_output_protocol = int(config_obj['LOC_DATA_OUTPUT_PROTOCOL'])
            else:
                term_property.loc_data_output_protocol = 0

            return term_property

        except Exception as err:
            MLog.mlogger.warn('TermController convert_config_to_property Exception err:%s ', err)
            MLog.mlogger.warn(traceback.format_exc())

    def create_old_terminal(self, ip_addr, mac_addr, host_name, file_name):
        """
        判断该终端连上过，存在配置文件，使用该配置文件创建一个终端，分配终端属性
        :param file_name:
        :param ip_addr:
        :param mac_addr:
        :param host_name:
        """
        # 如果文件名字变化，需要重命名
        file_name = 'terminal/config/' + file_name
        # 拷贝当前最新的基站配置
        config_obj = ConfigObj(file_name, encoding='UTF8')
        self.copy_cur_base_config(config_obj)
        # 转化配置到终端属性
        term_property = self.convert_config_to_property(config_obj, ip_addr, mac_addr, host_name)
        # 创建终端对象
        term = Terminal(self, term_property)
        self.mac_term_obj_map[mac_addr] = term
        self.term_property_list.append(term_property)  # 列表添加一个终端属性
        print('TermController create_old_terminal:', host_name, mac_addr)

    def create_new_terminal(self, ip_addr, mac_addr, host_name):
        """
        使用终端的默认属性创建一个第一次连上的终端
        :param ip_addr:
        :param mac_addr:
        :param host_name:
        """
        # 将默认配置文件拷贝到新建的终端
        term_config_file_name = 'terminal/config/' + mac_addr
        shutil.copyfile(self.default_config_file_path, term_config_file_name)
        term_property = message_pb2.TerminalProperty()  # 新连接上来的终端 使用默认的终端属性
        term_property.ip_addr = ip_addr
        term_property.mac_addr = mac_addr
        term_property.host_name = host_name
        term_property.sensor_list.extend(self.default_term_property.sensor_list)
        term_property.report_ip_addr.extend(self.default_term_property.report_ip_addr)
        term_property.report_tcp_port.extend(self.default_term_property.report_tcp_port)
        term_property.raw_output_flag = self.default_term_property.raw_output_flag
        term_property.odom_parameters = self.default_term_property.odom_parameters
        term_property.odom_input_option = self.default_term_property.odom_input_option
        term_property.optic_data_input_dev = self.default_term_property.optic_data_input_dev
        term_property.loc_data_output_dev = self.default_term_property.loc_data_output_dev
        term_property.loc_data_output_protocol = self.default_term_property.loc_data_output_protocol
        term = Terminal(self, term_property)
        self.mac_term_obj_map[mac_addr] = term
        self.term_property_list.append(term_property)  # 列表添加一个终端属性
        self.term_config_file_list.append(mac_addr)
        print('TermController create_new_terminal:', host_name, mac_addr)

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_RECV_TERM_CAST_REP, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE, self)
        self.unsubscribe(LTEventType.EVENT_A_TERMINAL_DISCONNECT, self)
        self.unsubscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.unsubscribe(LTEventType.EVENT_UPDATE_TERMINAL_PRO, self)
        self.unsubscribe(LTEventType.EVENT_TERM_ACTION_REQUEST, self)
        self.unsubscribe(LTEventType.EVENT_TERM_UPGRADE_REQUEST, self)
        super(TermController, self).__del__()

    def get_term_property_list(self):
        """
        获取指定的终端属性，如果term_property_list为空，获取全部
        :return message_pb2.TerminalPropertyResponse msg string
        """
        msg_pack = message_pb2.TerminalPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_pack.terminal_list.extend(self.term_property_list)
        # print('....TermContorller get_term_property_list:', msg_pack)
        msg_str = msg_pack.SerializeToString()
        # print('TermController TerminalPropertyResponse get_term_property_list :')
        return msg_str

    def get_term_property(self, msg_parse):
        """
        获取指定的终端属性，如果term_property_list为空，获取全部
        :return message_pb2.TerminalPropertyResponse msg string
        """
        msg_pack = message_pb2.TerminalPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        if not msg_parse.terminal_list:
            msg_pack.terminal_list.extend(self.term_property_list)
        else:
            property_list = []
            for i, req_term in enumerate(msg_parse.terminal_list):
                for j, term in enumerate(self.term_property_list):
                    if req_term.mac_addr == term.mac_addr:
                        property_list.append(term)
                        break

            msg_pack.terminal_list.extend(property_list)
        msg_str = msg_pack.SerializeToString()
        # print('TermController TerminalPropertyResponse get_term_property_list :')
        return msg_str

    def update_term_property_list(self, msg):
        """
        更新msg_parse里面对应的终端属性
        :return message_pb2.TerminalPropertyResponse msg string
        :param msg: message_pb2.TerminalPropertyRequest
        """
        msg_parse = message_pb2.TerminalPropertyRequest()
        msg_parse.ParseFromString(msg)
        # print('TermController TerminalPropertyRequest update :', msg_parse)

        for i, req_term in enumerate(msg_parse.terminal_list):
            list_exist_flag = False
            for j, term in enumerate(self.term_property_list):
                if req_term.mac_addr == term.mac_addr:
                    self.term_property_list[j] = req_term
                    # 判断终端属性是否一致，如果一致就不更新
                    self.mac_term_obj_map[req_term.mac_addr].update_property(req_term)  # 由终端对象来处理属性更改
                    list_exist_flag = True
                    break
            if list_exist_flag is False:
                if req_term.mac_addr in self.term_config_file_list:
                    #  没有对应的终端对象直接，直接写入文件中
                    self.write_property_to_config(req_term)

        event = LTEventType.EVENT_TERMINAL_LIST_UPDATE
        event_content = self.get_term_property_list()
        self.publish_event(event, event_content)

    def handle_upgrade_request(self, msg):
        msg_parse = message_pb2.LingTrackUpdateRequest()
        msg_parse.ParseFromString(msg)
        print('TermController LingTrackUpdateRequest :', msg_parse)

        for mac_addr in msg_parse.term_mac_addr_list:
            if mac_addr in self.mac_term_obj_map:
                self.mac_term_obj_map[mac_addr].upgrade_msg_handle(msg_parse)  # 由终端对象来处理act动作请求

    def handle_act_request(self, msg):
        """
        更新msg_parse里面对应的终端属性
        :return message_pb2.TerminalActionResponse msg string
        :param msg: message_pb2.TerminalActionRequest
        """
        msg_parse = message_pb2.TerminalActionRequest()
        msg_parse.ParseFromString(msg)
        print('TermController TerminalActionRequest :', msg_parse)

        unhandle_term = []
        for i, req_term in enumerate(msg_parse.terminal_list):
            handle_flag = False
            for j, term in enumerate(self.term_property_list):
                if req_term.mac_addr == term.mac_addr:
                    self.mac_term_obj_map[req_term.mac_addr].act_msg_handle(msg_parse)  # 由终端对象来处理act动作请求
                    handle_flag = True
                    break

            if handle_flag is False:
                unhandle_term.append(req_term)
                print('handle_act_request unhandle_term:', req_term)

            i += 1

        # msg_pack = message_pb2.TerminalActionResponse()
        # msg_pack.sequence = msg_parse.sequence
        # if len(unhandle_term) == 0:
        #     msg_pack.status.code = message_pb2.ResponseStatus.OK
        # else:
        #     msg_pack.status.code = message_pb2.ResponseStatus.TERMINAL_NOTFOUND
        #     msg_pack.status.detail = 'controller not exist the terminal'
        #     msg_pack.terminal_list.extend(unhandle_term)
        # msg_str = msg_pack.SerializeToString()
        # return msg_str

    def write_property_to_config(self, term_property):
        try:
            config_file_name = 'terminal/config/' + term_property.mac_addr  # mac addr 是唯一标识，也是该终端配置文件的文件名
            config_obj = ConfigObj(config_file_name, encoding='UTF8')

            channel_str = []
            offset_str = []
            height = ''
            for sensor in term_property.sensor_list:
                channel_str.append(str(sensor.active))
                offset_str.extend([sensor.coordinates.x, sensor.coordinates.y, sensor.coordinates.z])
                height = str(sensor.height)

            config_obj['RECEIVER_HEIGHT'] = height
            if len(channel_str) == 1:
                config_obj['SENSOR_CHANNELS'] = channel_str[0]
            else:
                config_obj['SENSOR_CHANNELS'] = channel_str
            config_obj['SENSOR_OFFSETS'] = offset_str

            # report_ip_addr = '127.0.0.1'
            # if term_property.HasField('report_ip_addr'):
            report_ip_addr = term_property.report_ip_addr[0]
            config_obj['REMOTE_MONITOR_ADDR'] = report_ip_addr

            # report_tcp_port = 6000
            # if term_property.HasField('report_tcp_port'):
            report_tcp_port = term_property.report_tcp_port[0]
            config_obj['REMOTE_MONITOR_PORT'] = report_tcp_port
            config_obj['RAW_OUTPUT_FLAG'] = term_property.raw_output_flag
            config_obj['TERM_NAME'] = term_property.host_name
            config_obj['ODOM_PARAMETERS'] = term_property.odom_parameters

            config_obj['ODOM_INPUT_OPTION'] = term_property.odom_input_option
            config_obj['OPTIC_DATA_INPUT_DEV'] = term_property.optic_data_input_dev
            config_obj['LOC_DATA_OUTPUT_DEV'] = term_property.loc_data_output_dev
            config_obj['LOC_DATA_OUTPUT_PROTOCOL'] = term_property.loc_data_output_protocol
            config_obj.write()
            config_obj.reload()
        except KeyError as err:
            MLog.mlogger.warn('Terminal update_property err:%s ', err)
            MLog.mlogger.warn(traceback.format_exc())




