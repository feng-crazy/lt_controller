#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 10:56
# @Author  : hedengfeng
# @Site    : 
# @File    : BasesController.py
# @Software: LT_controller
import copy
import os
import threading
import traceback

from configobj import ConfigObj

from eventbus.MThread import MThread
from utility import message_pb2
from basestation.BaseStation import BaseStation
from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType
from utility.Mlogging import MLog

from basestation.BasesDevice import BasesDevice


class BaseController(MThread, EventTarget):
    """BaseController"""

    def __init__(self, thread_name):
        self.thread_name = thread_name
        self.bases_ctrller_connect_flag = False
        self.device = None

        self.total_config_file_path = 'basestation/basesConfig'
        self.total_config_obj = ConfigObj(self.total_config_file_path, encoding='UTF8')
        self.default_bases_property = None

        self.chip_bases_obj_map = {}  # chip id 和基站对象的一个map
        self.bases_obj_list = []
        self.bases_obj_list_index = 0
        self.active_bases_property_list = []  # type message_pb2.BaseStationProperty list
        self.all_bases_property_list = []  # type message_pb2.BaseStationProperty list
        self.base_config_file_list = []  # 所有的基站列表

        # 该类构造父类必须要最后
        MThread.__init__(self, self, thread_name)

    def _init_all_bases_property_list(self):
        """遍历所有基站配置，初始化到基站属性列表"""
        self.all_bases_property_list.clear()
        rootdir = 'basestation/config'
        self.base_config_file_list = os.listdir('basestation/config')  # 遍历config目录
        for file_name in self.base_config_file_list:
            # file_path = os.path.join(rootdir, file_name)
            file_path = rootdir + '/' + file_name
            config_obj = ConfigObj(file_path, encoding='UTF8')
            bases_property = self.convert_config_to_property(config_obj)
            self.all_bases_property_list.append(bases_property)

        self.convert_all_property_to_config()
        # print('BasesController _init_all_bases_property_list:', self.all_bases_property_list)

    def _init_default_bases_property(self):
        """初始化默认基站属性用于首次连接的基站"""
        bases_property = message_pb2.BaseStationProperty()
        bases_property.chip_id = ''
        bases_property.group = -1
        bases_property.host_name = ''
        bases_property.address = -1
        bases_property.frequency = -1
        bases_property.start_angle = 0
        bases_property.coordinates.x = 0
        bases_property.coordinates.y = 0
        bases_property.coordinates.z = 300
        bases_property.orientation.pitch = 0
        bases_property.orientation.roll = 0
        bases_property.orientation.yaw = 0
        bases_property.led_status = 0
        bases_property.motor_speed = 0
        bases_property.connect_status = False
        bases_property.bs_desc = '0'

        self.default_bases_property = bases_property

    def setup_thread(self):
        """
        子线程初始操作函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        """
        EventTarget.__init__(self, self)  # 该父类的构造必须是要再该线程执行中，最开始执行

        self.event_handle_sleep = 0.01
        self.thread_loop_sleep = 0.5

        self._init_default_bases_property()
        self._init_all_bases_property_list()

        print('setup_thread...........', threading.current_thread(), self.thread_name)
        self.subscribe(LTEventType.EVENT_A_NEW_BASE_STATION_CONNECT, self)
        self.subscribe(LTEventType.EVENT_A_BASE_STATION_DISCONNECT, self)
        self.subscribe(LTEventType.EVENT_UPDATE_BASE_STATION_PRO, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_REMOVE_REQUEST, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_APPEND_REQUEST, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_ACTION_REQUEST, self)
        self.subscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_CONNECT, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT, self)
        self.subscribe(LTEventType.EVENT_BASE_UPGRADE_REQUEST, self)
        self.subscribe(LTEventType.EVENT_BASE_CTRLLER_UPGRADE_REQUEST, self)

        self.device = BasesDevice()

    def thread_task(self):
        """
        线程主循环函数，该函数可以理解为纯虚函数，MThread子类必须要实现
        该函数每0.5秒执行一次，见setup_thread的 self.thread_loop_sleep = 0.5
        """
        if self.bases_ctrller_connect_flag is False:
            return
        if self.bases_obj_list_index < len(self.bases_obj_list):
            self.bases_obj_list[self.bases_obj_list_index].monitor_bases()
            self.bases_obj_list_index += 1

        else:
            self.bases_obj_list_index = 0

    def judge_property_conflict(self, judge_property):
        """返回True表示没有冲突，False表示有冲突"""
        if judge_property.address == -1:  # 如果bs_id为负数那么说明是初始化的值，可以重复
            return True

        for bases_property in self.all_bases_property_list:
            if bases_property.chip_id != judge_property.chip_id:
                if bases_property.address == judge_property.address:
                    event = LTEventType.EVENT_BASES_EXCEPT_STATUS
                    bases_except_status = message_pb2.BasesExceptStatus()
                    bases_except_status.chip_id = judge_property.chip_id
                    bases_except_status.except_detail.append('base station config conflict')
                    event_content = bases_except_status.SerializeToString()
                    self.publish_event(event, event_content)
                    return False

        return True

    def judge_property_repeat(self, judge_property):
        """返回True表示没有重复，False表示有重复"""
        if judge_property.address == -1:  # 如果bs_id为负数那么说明是初始化的值，可以重复
            return True

        for bases_property in self.all_bases_property_list:
            if bases_property.chip_id == judge_property.chip_id \
                    or bases_property.address == judge_property.address:
                event = LTEventType.EVENT_BASES_EXCEPT_STATUS
                bases_except_status = message_pb2.BasesExceptStatus()
                bases_except_status.chip_id = judge_property.chip_id
                bases_except_status.except_detail.append('base station config repeat')
                event_content = bases_except_status.SerializeToString()
                self.publish_event(event, event_content)
                return False

        return True

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        if event == LTEventType.EVENT_A_BASE_STATION_DISCONNECT:
            self.handle_bases_disconnect_event(event_content.decode())

        elif event == LTEventType.EVENT_A_NEW_BASE_STATION_CONNECT:
            self.handle_bases_connect_event(event_content)

        elif event == LTEventType.EVENT_UPDATE_BASE_STATION_PRO:
            self.update_bases_property_list(event_content)

        elif event == LTEventType.EVENT_BASE_STATION_REMOVE_REQUEST:
            self.remove_bases_property_list(event_content)

        elif event == LTEventType.EVENT_BASE_STATION_APPEND_REQUEST:
            self.append_bases_property_list(event_content)

        elif event == LTEventType.EVENT_BASE_STATION_ACTION_REQUEST:
            self.handle_act_request(event_content)

        elif event == LTEventType.EVENT_BASE_STATION_CTRLLER_CONNECT:
            self.bases_ctrller_connect_flag = True
            event = LTEventType.EVENT_BASES_EXCEPT_STATUS
            bases_except_status = message_pb2.BasesExceptStatus()
            bases_except_status.except_detail.append('base station controller connect')
            event_content = bases_except_status.SerializeToString()
            self.publish_event(event, event_content)

        elif event == LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT:
            print('BasesController handle EVENT_BASE_STATION_CTRLLER_DISCONNECT')
            self.bases_ctrller_connect_flag = False
            event = LTEventType.EVENT_BASES_EXCEPT_STATUS
            bases_except_status = message_pb2.BasesExceptStatus()
            bases_except_status.except_detail.append('base station controller disconnect')
            event_content = bases_except_status.SerializeToString()
            self.publish_event(event, event_content)

        elif event == LTEventType.EVENT_SYSTEM_STARTUP:
            event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
            event_content = self.get_all_bases_property_list()
            self.publish_event(event, event_content)

        elif event == LTEventType.EVENT_BASE_UPGRADE_REQUEST:
            self.device.handle_upgrade_request(event_content)

        elif event == LTEventType.EVENT_BASE_CTRLLER_UPGRADE_REQUEST:
            pass

    def set_address_socket(self, address, client_sock):
        # self.ip_address = address
        # self.tcp_socket = client_sock
        self.device.set_address_socket(address, client_sock)
        self.start()

    def convert_config_to_property(self, config_obj):
        """
        将终端的配置转化为message_pb2.BaseStationProperty
        :param config_obj:必须为单基站基站配置的config
        :return:message_pb2.BaseStationProperty
        """
        bases_property = message_pb2.BaseStationProperty()
        bases_property.chip_id = config_obj['CHIP_ID']
        bases_property.host_name = config_obj['HOST_NAME']

        bases_property.group = int(config_obj['BS_GROUP'])
        bases_property.frequency = int(config_obj['BS_FREQS'])
        bases_property.address = int(config_obj['BS_ADDRS'])
        bases_property.start_angle = float(config_obj['BS_START_ANGLES'])
        bases_property.led_status = int(config_obj['LED_STATUS'])
        bases_property.motor_speed = float(config_obj['MOTOR_SPEED'])
        location = config_obj['BS_LOCATIONS']
        bases_property.coordinates.x = float(location[0])
        bases_property.coordinates.y = float(location[1])
        bases_property.coordinates.z = float(location[2])
        orientation = config_obj['BS_ORIENTATIONS']
        bases_property.orientation.pitch = float(orientation[0])
        bases_property.orientation.roll = float(orientation[1])
        bases_property.orientation.yaw = float(orientation[2])
        bases_property.connect_status = False
        if 'BS_INFO' in config_obj:
            bases_property.bs_desc = config_obj['BS_INFO']
        else:
            bases_property.bs_desc = '0'

        return bases_property

    def convert_all_property_to_config(self):
        """将属性列表中的内容转化到配置文件中"""
        print('BasesController convert_all_property_to_config')
        group = []
        bs_freqs = []
        bs_addrs = []
        bs_locations = []
        bs_start_angles = []
        bs_orientations = []
        bs_desc = []
        for i in range(0, len(self.all_bases_property_list)):
            if self.all_bases_property_list[i].group != -1 and \
                    self.all_bases_property_list[i].frequency != -1 and \
                    self.all_bases_property_list[i].address != -1:
                group.append(str(self.all_bases_property_list[i].group))
                bs_freqs.append(str(self.all_bases_property_list[i].frequency))
                bs_addrs.append(str(self.all_bases_property_list[i].address))
                bs_start_angles.append(str(self.all_bases_property_list[i].start_angle))
                bs_locations.extend([self.all_bases_property_list[i].coordinates.x,
                                     self.all_bases_property_list[i].coordinates.y,
                                     self.all_bases_property_list[i].coordinates.z])
                bs_orientations.extend([self.all_bases_property_list[i].orientation.pitch,
                                        self.all_bases_property_list[i].orientation.roll,
                                        self.all_bases_property_list[i].orientation.yaw])
                bs_desc.append(str(self.all_bases_property_list[i].bs_desc))

        self.total_config_obj['BS_GROUP'] = group
        self.total_config_obj['BS_FREQS'] = bs_freqs
        self.total_config_obj['BS_ADDRS'] = bs_addrs
        self.total_config_obj['BS_LOCATIONS'] = bs_locations
        self.total_config_obj['BS_START_ANGLES'] = bs_start_angles
        self.total_config_obj['BS_ORIENTATIONS'] = bs_orientations
        self.total_config_obj['BS_INFO'] = bs_desc
        self.total_config_obj.write()
        self.total_config_obj.reload()

        event = LTEventType.EVENT_BASE_STATION_CONFIG_UPDATE
        event_content = bytes()
        self.publish_event(event, event_content)

    def create_old_basestation(self, new_bases_property):
        """
        判断该终端连上过，存在配置文件，使用该配置文件创建一个终端，分配终端属性
        :param chip_id:
        """
        chip_id = new_bases_property.chip_id
        # 找到其基站配置
        print('BasesController create_old_basestation chip_id:', chip_id)
        bases_property = self.find_base_property_in_all(chip_id)
        bases_property.connect_status = True
        # 创建终端对象
        bases = BaseStation(self.device, bases_property)
        self.chip_bases_obj_map[chip_id] = bases
        self.bases_obj_list.append(bases)
        self.active_bases_property_list.append(bases_property)  # 列表添加一个终端属性

    def create_new_basestation(self, new_bases_property):
        """
        使用终端的默认属性创建一个第一次连上的终端
        :param chip_id:
        """
        # 判断新连上的基站是否与以前有冲突，有的话删掉原来的
        for list_elem in self.all_bases_property_list:
            if list_elem.chip_id != new_bases_property.chip_id:
                if list_elem.address == new_bases_property.address:
                    self.all_bases_property_list.remove(list_elem)
                    config_file = 'basestation/config/' + list_elem.chip_id
                    os.remove(config_file)
                    self.base_config_file_list.remove(list_elem.chip_id)

        chip_id = new_bases_property.chip_id
        print('BasesController create_new_basestation chip_id:', chip_id)
        # bases_config_file_name = 'basestation/config/' + chip_id
        bases_property = copy.deepcopy(self.default_bases_property)
        bases_property.chip_id = chip_id
        bases_property.group = new_bases_property.group
        bases_property.address = new_bases_property.address
        bases_property.host_name = new_bases_property.host_name
        bases_property.frequency = new_bases_property.frequency
        bases_property.led_status = new_bases_property.led_status
        bases_property.motor_speed = new_bases_property.motor_speed
        bases_property.connect_status = True
        bases_property.bs_desc = '0'

        bases = BaseStation(self.device, bases_property)
        self.chip_bases_obj_map[chip_id] = bases
        self.bases_obj_list.append(bases)
        self.active_bases_property_list.append(bases_property)  # 列表添加一个终端属性
        self.all_bases_property_list.append(bases_property)
        self.base_config_file_list.append(chip_id)
        self.convert_all_property_to_config()

    def handle_bases_disconnect_event(self, chip_id):
        """
        处理一个基站断开连接事件
        :param chip_id:
        """
        print('handle_bases_disconnect_event:', chip_id)
        if chip_id in self.chip_bases_obj_map:
            bases_obj = self.chip_bases_obj_map[chip_id]
            if bases_obj in self.bases_obj_list:
                self.bases_obj_list.remove(bases_obj)
            del self.chip_bases_obj_map[chip_id]
            base_property = self.find_base_property_in_active(chip_id)
            self.active_bases_property_list.remove(base_property)

            bases_property = self.find_base_property_in_all(chip_id)
            bases_property.connect_status = False

            event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
            event_content = self.get_all_bases_property_list()
            self.publish_event(event, event_content)
        else:
            MLog.mlogger.warn('handle_bases_disconnect_event chip_id:{} is not in map'.format(chip_id))

    def handle_bases_connect_event(self, bases_info):
        """
        处理一个基站连接事件
        :param chip_id:
        """
        bases_property = message_pb2.BaseStationProperty()
        bases_property.ParseFromString(bases_info)

        chip_id = bases_property.chip_id
        if chip_id not in self.chip_bases_obj_map:
            if chip_id in self.base_config_file_list:
                self.create_old_basestation(bases_property)  #
            else:
                self.create_new_basestation(bases_property)

            event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
            event_content = self.get_all_bases_property_list()
            self.publish_event(event, event_content)
        else:
            MLog.mlogger.warn('handle_bases_connect_event chip_id:{} is in map'.format(chip_id))

    def find_base_property_in_all(self, chip_id):
        """
        根据chip_id在all_bases_property_list中找到bases_property
        :rtype: bases_property
        """
        for bases_property in self.all_bases_property_list:
            if bases_property.chip_id == chip_id:
                return bases_property

        MLog.mlogger.warn('find_base_property_in_all chip_id:{} no find'.format(chip_id))
        return False

    def find_base_property_in_active(self, chip_id):
        """
        根据chip_id在active_bases_property_list中找到bases_property
        :rtype: bases_property
        """
        for bases_property in self.active_bases_property_list:
            if bases_property.chip_id == chip_id:
                return bases_property

    def get_active_bases_property_list(self):
        """
        :return message_pb2.BaseStationPropertyResponse msg string
        """
        print('ManagerDevice get_active_bases_property_list')
        msg_pack = message_pb2.BaseStationPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_pack.base_station_list.extend(self.active_bases_property_list)
        # print('BasesController get_active_bases_property_list BaseStationPropertyResponse:')
        msg_serialize = msg_pack.SerializeToString()
        return msg_serialize

    def get_all_bases_property_list(self):
        """
        :return message_pb2.BaseStationPropertyResponse msg string
        """
        print('BasesController get_all_bases_property_list')
        msg_pack = message_pb2.BaseStationPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        msg_pack.base_station_list.extend(self.all_bases_property_list)
        # print('get_all_bases_property_list BaseStationPropertyResponse:')
        msg_serialize = msg_pack.SerializeToString()
        return msg_serialize

    def get_property_in_all_bases_list(self, msg_parse):
        """
        :return message_pb2.BaseStationPropertyResponse msg string
        """
        print('ManagerDevice get_all_bases_property_list')
        msg_pack = message_pb2.BaseStationPropertyResponse()
        msg_pack.status.code = message_pb2.ResponseStatus.OK
        if not msg_parse.base_station_list:
            msg_pack.base_station_list.extend(self.all_bases_property_list)
        else:
            property_list = []
            for i, req_bases in enumerate(msg_parse.base_station_list):
                for j, bases in enumerate(self.all_bases_property_list):
                    if req_bases.chip_id == bases.chip_id:
                        property_list.append(bases)
                        break
            msg_pack.base_station_list.extend(property_list)

        print('get_all_bases_property_list BaseStationPropertyResponse:')
        msg_str = msg_pack.SerializeToString()
        return msg_str

    def update_bases_property_list(self, msg):
        """
        更新msg_parse里面对应的终端属性
        :return message_pb2.BaseStationPropertyResponse msg string
        :param msg: message_pb2.BaseStationPropertyRequest
        """
        print('BasesController update_bases_property_list')
        msg_parse = message_pb2.BaseStationPropertyRequest()
        msg_parse.ParseFromString(msg)

        unhandle_bases = []
        conflict_bases = []
        update_success_flag = True
        for i, update_bases in enumerate(msg_parse.base_station_list):
            handle_flag = False
            for j, bases in enumerate(self.all_bases_property_list):
                if update_bases.chip_id == bases.chip_id:
                    if self.judge_property_conflict(update_bases):
                        if update_bases.chip_id in self.chip_bases_obj_map:
                            # update_bases.connect_status = 1
                            # 由基站对象来处理属性更改
                            ret = self.chip_bases_obj_map[update_bases.chip_id].update_property(update_bases)
                            active_list_index = self.active_bases_property_list.index(bases)
                            self.active_bases_property_list[active_list_index] = update_bases
                            if not ret:
                                update_success_flag = False
                                conflict_bases.append(update_bases)
                        else:  # 写入配置到文件
                            self.write_unactive_bases_config(update_bases)

                        self.all_bases_property_list[j] = update_bases
                    else:
                        update_success_flag = False
                        conflict_bases.append(update_bases)

                    handle_flag = True
                    break

            if handle_flag is False:
                unhandle_bases.append(update_bases)

        self.convert_all_property_to_config()

        event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
        event_content = self.get_all_bases_property_list()
        self.publish_event(event, event_content)

        if not update_success_flag:
            MLog.mlogger.info('update_bases_property_list conflict_bases:%s', conflict_bases)
        if len(unhandle_bases) > 0:
            MLog.mlogger.info('update_bases_property_list unhandle_bases:%s', unhandle_bases)

    def append_bases_property_list(self, msg):
        print('BasesController append_bases_property_list')
        msg_parse = message_pb2.BaseStationPropertyRequest()
        msg_parse.ParseFromString(msg)

        # 判断基站是否冲突
        for i, update_bases in enumerate(msg_parse.base_station_list):
            if self.judge_property_repeat(update_bases):
                self.all_bases_property_list.append(update_bases)
                self.write_unactive_bases_config(update_bases)
                self.base_config_file_list.append(update_bases.chip_id)

        self.convert_all_property_to_config()

        event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
        event_content = self.get_all_bases_property_list()
        self.publish_event(event, event_content)

    def remove_bases_property_list(self, msg):
        """
        更新msg_parse里面对应的终端属性
        :return message_pb2.BaseStationPropertyResponse msg string
        :param msg: message_pb2.BaseStationPropertyRequest
        """
        print('BasesController remove_bases_property_list')
        msg_parse = message_pb2.BaseStationPropertyRequest()
        msg_parse.ParseFromString(msg)

        unhandle_bases = []
        for i, req_bases in enumerate(msg_parse.base_station_list):
            req_bases = msg_parse.base_station_list[i]
            handle_flag = False
            for bases in self.all_bases_property_list.copy():
                if req_bases.chip_id == bases.chip_id \
                        and bases.connect_status is False:
                    self.all_bases_property_list.remove(bases)
                    config_file = 'basestation/config/' + bases.chip_id
                    os.remove(config_file)
                    self.base_config_file_list.remove(bases.chip_id)
                    handle_flag = True
                    break

            if handle_flag is False:
                unhandle_bases.append(req_bases)

        self.convert_all_property_to_config()

        event = LTEventType.EVENT_ALL_BASES_LIST_UPDATE
        event_content = self.get_all_bases_property_list()
        self.publish_event(event, event_content)

        if len(unhandle_bases) > 0:
            MLog.mlogger.info('remove_bases_property_list unhandle_bases:%s', unhandle_bases)

    def handle_act_request(self, msg):
        """
        预留的基站命令动作的处理
        :return message_pb2.BaseStationActionResponse msg string
        :param msg: message_pb2.BaseStationActionRequest
        """
        msg_parse = message_pb2.BaseStationActionRequest()
        msg_parse.ParseFromString(msg)
        act_command = msg_parse.command
        print('BasesController handle_act_request act_command:', act_command)
        # todo: 执行command命令

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_A_NEW_BASE_STATION_CONNECT, self)
        self.unsubscribe(LTEventType.EVENT_A_BASE_STATION_DISCONNECT, self)
        self.unsubscribe(LTEventType.EVENT_UPDATE_BASE_STATION_PRO, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_REMOVE_REQUEST, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_APPEND_REQUEST, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_ACTION_REQUEST, self)
        self.unsubscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_CONNECT, self)
        self.unsubscribe(LTEventType.EVENT_BASE_UPGRADE_REQUEST, self)
        self.unsubscribe(LTEventType.EVENT_BASE_CTRLLER_UPGRADE_REQUEST, self)
        super(BaseController, self).__del__()

    def write_unactive_bases_config(self, update_bases):
        print('BasesController write_unactive_bases_config:', update_bases)
        try:
            file_path = 'basestation/config/' + update_bases.chip_id
            single_config_obj = ConfigObj(file_path, encoding='UTF8')
            single_config_obj['CHIP_ID'] = update_bases.chip_id
            single_config_obj['HOST_NAME'] = update_bases.host_name
            single_config_obj['BS_GROUP'] = update_bases.group
            single_config_obj['BS_FREQS'] = update_bases.frequency
            single_config_obj['BS_ADDRS'] = update_bases.address
            single_config_obj['BS_START_ANGLES'] = update_bases.start_angle

            single_config_obj['BS_LOCATIONS'] = [update_bases.coordinates.x, update_bases.coordinates.y,
                                                 update_bases.coordinates.z]
            single_config_obj['BS_ORIENTATIONS'] = [update_bases.orientation.pitch, update_bases.orientation.roll,
                                                    update_bases.orientation.yaw]

            single_config_obj['LED_STATUS'] = update_bases.led_status
            single_config_obj['MOTOR_SPEED'] = update_bases.motor_speed
            single_config_obj['BS_INFO'] = update_bases.bs_desc
            single_config_obj.write()
            single_config_obj.write()
        except Exception as err:
            MLog.mlogger.warn('BaseStation write_unactive_bases_config Exception err :%s:', err)
            MLog.mlogger.warn(traceback.format_exc())


