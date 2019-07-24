#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/3 15:14
# @Author  : hedengfeng
# @Site    : 
# @File    : BaseStation.py
# @Software: LT_controller
# @description: 每一个485总线上基站的实例对象，提供设置该基站的接口方法
import traceback

from configobj import ConfigObj

from basestation.BasesLog import BasesLog
# from eventbus.EventTarget import EventTarget
from utility import message_pb2
# from utility.LTCommon import LTEventType
from utility.Mlogging import MLog


# class BaseStation(EventTarget):
class BaseStation(object):
    """
    BaseStation
    """

    def __init__(self, device, bases_property):
        # super(BaseStation, self).__init__(self)
        # print('BaseStation __init__:', bases_property)
        self.device = device
        self.property = bases_property

        self.chip_id = bases_property.chip_id
        self.host_name = bases_property.host_name
        self.group = bases_property.group
        self.address = bases_property.address
        self.frequency = bases_property.frequency
        self.start_angle = bases_property.start_angle
        self.coordinates = [bases_property.coordinates.x, bases_property.coordinates.y, bases_property.coordinates.z]
        self.orientation = [bases_property.orientation.pitch, bases_property.orientation.roll,
                            bases_property.orientation.yaw]
        self.led_status = bases_property.led_status
        self.motor_speed = bases_property.motor_speed
        self.bs_desc = bases_property.bs_desc

        self.config_file_path = 'basestation/config/' + self.chip_id
        self.config_obj = ConfigObj(self.config_file_path, encoding='UTF8')

        self.property_convert_config()

        # self.subscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)

    def _init_set_basestation(self):
        # 保证基站连上的时候，与控制器保存的配置一致
        self.set_group(self.group)
        self.set_bases_addr(self.address)
        self.set_led_status(self.led_status)
        self.set_host_name(self.host_name)
        self.set_bases_motor(self.motor_speed)

    # def event_handle(self, event, event_content):
    #     """
    #     事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
    #     """
    #     # print('BaseStation ', 'event_handle', event)
    #     if event == LTEventType.EVENT_SYSTEM_TIME_1:
    #         self.monitor_bases()

    def monitor_bases(self):
        """监视基站运行"""
        # BasesLog.mlogger.warn('BaseStation monitor_bases:{}'.format(self.chip_id))
        # print('BaseStation monitor_bases:{}'.format(self.chip_id))
        if self.device is not None:
            bases_property = self.device.get_bases_info(self.chip_id)  # 监视基站配置不变
            if bases_property is None:
                BasesLog.mlogger.warn('BaseStation monitor_bases return None: {}'.format(self.chip_id))
                return False
            if self.host_name != bases_property.host_name:
                self.set_host_name(self.host_name)

            if self.group != bases_property.group:
                self.set_group(self.group)

            if self.address != bases_property.address:
                self.set_bases_addr(self.address)

            if self.led_status != bases_property.led_status:
                print('monitor_bases:', self.host_name, self.led_status, bases_property.led_status)
                self.set_led_status(self.led_status)

            if self.motor_speed != bases_property.motor_speed:
                self.set_bases_motor(self.motor_speed)

        return True

    def property_convert_config(self):
        print('BaseStation property_convert_config:')
        try:
            self.config_obj['CHIP_ID'] = self.chip_id
            self.config_obj['HOST_NAME'] = self.host_name
            self.config_obj['BS_GROUP'] = self.group
            self.config_obj['BS_FREQS'] = self.frequency
            self.config_obj['BS_ADDRS'] = self.address
            self.config_obj['BS_START_ANGLES'] = self.start_angle

            self.config_obj['BS_LOCATIONS'] = self.coordinates
            self.config_obj['BS_ORIENTATIONS'] = self.orientation

            self.config_obj['LED_STATUS'] = self.led_status
            self.config_obj['MOTOR_SPEED'] = self.motor_speed
            self.config_obj['BS_INFO'] = self.bs_desc
            self.config_obj.write()
            self.config_obj.write()
        except KeyError as err:
            MLog.mlogger.warn('BaseStation property_convert_config KeyError %s:', err)
            MLog.mlogger.warn(traceback.format_exc())

    def update_property(self, bases_property):
        """
        更新属性,属性变化则设置到基站上去
        :param bases_property: message_pb2.BaseStationProperty
        """
        print('BaseStation update_property bases_property:', self.chip_id)
        if self.chip_id != bases_property.chip_id:
            return False
        self.property = bases_property
        # print('BaseStation update_property property:', self.property)
        if self.host_name != bases_property.host_name:
            self.set_host_name(bases_property.host_name)
            self.host_name = bases_property.host_name

        if self.address != bases_property.address:
            self.set_bases_addr(bases_property.address)
            self.address = bases_property.address

        if self.group != bases_property.group:
            self.set_group(bases_property.group)
            self.group = bases_property.group

        if self.led_status != bases_property.led_status:
            self.set_led_status(bases_property.led_status)
            self.led_status = bases_property.led_status

        if self.motor_speed != bases_property.motor_speed:
            self.set_bases_motor(bases_property.motor_speed)
            self.motor_speed = bases_property.motor_speed

        self.frequency = bases_property.frequency
        self.start_angle = bases_property.start_angle

        self.coordinates = [bases_property.coordinates.x, bases_property.coordinates.y,
                            bases_property.coordinates.z]
        self.orientation = [bases_property.orientation.pitch, bases_property.orientation.roll,
                            bases_property.orientation.yaw]

        self.bs_desc = bases_property.bs_desc

        # print('BaseStation update_property property_convert_config:')
        self.property_convert_config()
        return True

    def set_host_name(self, host_name):
        BasesLog.mlogger.warn('BaseStation set_host_name:{},{}'.format(self.chip_id, host_name))
        if self.device is not None:
            ret = self.device.set_host_name(self.chip_id, host_name)
            if ret is False:
                BasesLog.mlogger.warn('BaseStation set_host_name failure {},{}'.format(self.host_name, host_name))

    def set_group(self, group):
        BasesLog.mlogger.warn('BaseStation set_group:{},{}'.format(self.host_name, group))
        if self.device is not None:
            ret = self.device.set_group(self.chip_id, group)
            if ret is False:
                BasesLog.mlogger.warn('BaseStation set_group failure {},{}'.
                                      format(self.host_name, group))

    def set_bases_addr(self, address):
        BasesLog.mlogger.warn('BaseStation set_bases_addr:{},{}'.format(self.host_name, address))
        if self.device is not None:
            ret = self.device.set_bases_addr(self.chip_id, address)
            if ret is False:
                BasesLog.mlogger.warn('BaseStation set_bases_addr failure {},{}'.
                                      format(self.host_name, address))

    def set_led_status(self, led_status):
        print('BaseStation set_led_status:{},{}'.format(self.host_name, led_status))
        if self.device is not None:
            ret = self.device.set_bases_led(self.chip_id, led_status)
            if ret is False:
                BasesLog.mlogger.warn('BaseStation set_led_status failure {},{}'.format(self.host_name, led_status))

    def set_bases_motor(self, motor_speed):
        print('BaseStation set_bases_motor:{},{}'.format(self.host_name, motor_speed))
        if self.device is not None:
            motor_status = int(motor_speed)
            if motor_status > 0:
                motor_status = 1
            else:
                motor_status = 0
            ret = self.device.set_bases_motor(self.chip_id, motor_status)
            if ret is False:
                BasesLog.mlogger.warn('BaseStation set_bases_motor failure {},{}'.format(self.host_name, motor_speed))

    # def cancel_subscribe(self):
    #     self.unsubscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
    #
    # def __del__(self):
    #     print('BaseStation __del__...........', self, self.chip_id)
    #     super(BaseStation, self).__del__()

