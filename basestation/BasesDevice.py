#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/17 15:23
# @Author  : hedengfeng
# @Site    : 
# @File    : BasesDevice.py
# @Software: LTController
# @description: 与基站主控板STM32通信的设备类，通过spi
import socket
import traceback

import time
from _multiprocessing import send

from basestation import BasesProtocal
from eventbus.EventTarget import EventTarget
from utility import message_pb2
from utility.LTCommon import LTEventType
from utility.ZipUnzipFile import ZipUnzipFile
from basestation.BasesLog import BasesLog


class BasesDevice(EventTarget):
    """基站设备类"""
    def __init__(self):
        super(BasesDevice, self).__init__(self)
        self.ip_address = None
        self.tcp_socket = None

        self.bases_addr_count_map = {}  # 基站地址计数map
        self.bases_addr_chip_id_map = {}  # 基站地址和芯片idmap
        self.network_connect_flag = False
        self.bases_ctrller_resp_count = 0
        self.subscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)

    def set_address_socket(self, address, client_sock):
        self.ip_address = address
        self.tcp_socket = client_sock
        self.network_connect_flag = True
        self.bases_ctrller_resp_count = 0

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        # print('BaseStation ', 'event_handle', event)
        if event == LTEventType.EVENT_SYSTEM_TIME_1:
            if self.network_connect_flag is False:
                return
            self.scan_bases()
            self.bases_ctrller_resp_count += 1
            if self.bases_ctrller_resp_count >= 6:  # 基站控制五次没有响应视为掉线
                BasesLog.mlogger.warn('基站控制器连续没有响应，判断为掉线')
                self.network_connect_flag = False
                self.tcp_socket.close()
                self.ip_address = None
                event = LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT
                event_content = b''
                self.publish_event(event, event_content)

    def send_cmd(self, cmd):
        # traceback.print_stack()
        if self.network_connect_flag is False:
            BasesLog.mlogger.warn('send_cmd network_connect_flag is False')
            return None
        try:
            print('send_cmd:', cmd)
            send_bytes = self.tcp_socket.sendall(bytes(cmd))
            print('already send_bytes return:',  send_bytes)
        except socket.timeout as err:
            BasesLog.mlogger.warn('sendall nework is timeout{}'.format(err))
        except Exception as err:
            BasesLog.mlogger.warn('sendall nework is Exception{}'.format(err))
            self.network_connect_flag = False
            self.tcp_socket.close()
            self.ip_address = None
            event = LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT
            event_content = b''
            self.publish_event(event, event_content)
            return None
        time.sleep(0.01)  # 10毫秒等待响应
        rep = self.recv_reponse()
        print('send_cmd rep:', rep)
        if rep is None:
            BasesLog.mlogger.warn('send_cmd recv reponse is None')
        return rep

    def recv_reponse(self):
        rep_data = []
        pack_data_list = []
        try:
            recv_data = self.tcp_socket.recv(1024)
            if not recv_data:
                BasesLog.mlogger.warn('tcp_socket recv return err {}'.format(recv_data))
                return None
            rep_data += list(recv_data)
            print('recv_reponse rep_data:', rep_data)
        except socket.timeout as err:
            BasesLog.mlogger.warn('recv nework is timeout{}'.format(err))
        except Exception as err:
            BasesLog.mlogger.warn('tcp_socket recv nework is Exception{}'.format(err))
            self.network_connect_flag = False
            self.tcp_socket.close()
            self.ip_address = None
            event = LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT
            event_content = b''
            self.publish_event(event, event_content)
            return None

        while len(rep_data) > 4:
            if rep_data[0:2] == BasesProtocal.PACK_HEAD:
                pack_len = BasesProtocal.getLengh(rep_data) + BasesProtocal.PACK_FIXED_LENGH
                if pack_len > len(rep_data):
                    BasesLog.mlogger.warn('recv reponse data length is error')
                    break
                pack_data = rep_data[:pack_len]
                if BasesProtocal.judgeCheckSum(pack_data) is True:
                    self.bases_ctrller_resp_count = 0
                    pack_data_list.append(pack_data)
                else:
                    BasesLog.mlogger.warn('recv reponse data check sum is error')

                for i in range(0, pack_len):
                    rep_data.pop(0)
            else:
                rep_data.pop(0)
        if len(pack_data_list) > 0:
            return pack_data_list[-1]
        return None

    def send(self, data):
        self.tcp_socket.sendall(data)

    def recv(self, read_len):
        ret_len = self.tcp_socket.recv(read_len)  # read data
        return ret_len

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
        super(BasesDevice, self).__del__()
        if self.tcp_socket is not None:
            self.tcp_socket.close()

    def scan_bases(self):
        bases_addr_list = self.send_scan_cmd()
        if bases_addr_list is None:
            return

        for list_elem in bases_addr_list:
            if list_elem in self.bases_addr_count_map:
                self.bases_addr_count_map[list_elem] = 0
            else:  # 新的基站连接
                self.handle_new_bases_connect(list_elem)

        # 判断掉线基站
        for key in list(self.bases_addr_count_map.keys()):
            self.bases_addr_count_map[key] += 1
            if self.bases_addr_count_map[key] >= 3:  # 3次没有认定掉线了
                self.handle_bases_disconnect(key)

    def handle_new_bases_connect(self, addres):
        #  根据地址获取新基站的详细信息
        # BasesLog.mlogger.warn('handle_new_bases_connect addres:%d', addres)
        send_data = BasesProtocal.packGetBasesInfo(addres)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            rep_map = BasesProtocal.parseBasesInfo(rep_data)
            if rep_map is False:
                BasesLog.mlogger.warn('parseBasesInfo return false')
                return None
            bases_property = message_pb2.BaseStationProperty()
            bases_property.group = rep_map['group']
            bases_property.address = rep_map['address']
            bases_property.chip_id = rep_map['chip_id']
            bases_property.host_name = rep_map['name']
            bases_property.frequency = 22000
            bases_property.led_status = rep_map['led']
            bases_property.motor_speed = rep_map['motor']
            bases_property.connect_status = True

            BasesLog.mlogger.warn('handle_new_bases_connect bases_property: {}'.format(bases_property))
            #  发送新基站连接事件
            event = LTEventType.EVENT_A_NEW_BASE_STATION_CONNECT
            event_content = bases_property.SerializeToString()
            self.publish_loc_event(event,  event_content)

            self.bases_addr_chip_id_map[addres] = bases_property.chip_id
        else:
            BasesLog.mlogger.warn('BasesDevice handle_new_bases_connect rep_data is None')
            return False

        self.bases_addr_count_map[addres] = 0
        return True

    def handle_bases_disconnect(self, addres):
        if addres in self.bases_addr_count_map:
            del self.bases_addr_count_map[addres]

        if addres in self.bases_addr_chip_id_map:
            chip_id = self.bases_addr_chip_id_map[addres]
            del self.bases_addr_chip_id_map[addres]
            BasesLog.mlogger.warn('handle_bases_disconnect addres:{} id:{}'.format(addres, chip_id))
            #  发送新基站连接事件
            event = LTEventType.EVENT_A_BASE_STATION_DISCONNECT
            event_content = chip_id.encode()
            self.publish_loc_event(event, event_content)

        return True

    def send_scan_cmd(self):
        """
        发送扫描基站命令,扫描只能扫描地址，下位机无法做到扫描基站
        :rtype: 基站地址表达式
        """
        send_data = BasesProtocal.packGetBasesList()
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            address_list = BasesProtocal.parseAddrList(rep_data)
            if address_list is not False:
                return address_list
            else:
                # BasesLog.mlogger.warn('send_scan_cmd rep_data is error:{}'.format(address_list))
                return None
        else:
            BasesLog.mlogger.warn('send_scan_cmd rep_data is None')

        return None

    def handle_bases_addr_change(self, chip_id_str, bases_addr):
        # 旧的地址删除
        old_bases_addr = 0
        for key, chip_id in self.bases_addr_chip_id_map.items():
            if chip_id == chip_id_str:
                old_bases_addr = key
                break

        del self.bases_addr_chip_id_map[old_bases_addr]

        if old_bases_addr in self.bases_addr_count_map:
            del self.bases_addr_count_map[old_bases_addr]

        # 新的地址添加
        self.bases_addr_chip_id_map[bases_addr] = chip_id_str
        self.bases_addr_count_map[bases_addr] = 0

    def set_bases_addr(self, chip_id_str, bases_addr):
        print('set_bases_addr  chip_id_str:', chip_id_str, bases_addr)
        chip_id = self.chip_id_to_int_list(chip_id_str)
        if chip_id is None:
            return False
        send_data = BasesProtocal.packConfigAddr(chip_id, bases_addr)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                # 更换了新的地址有一些数据结构要变
                self.handle_bases_addr_change(chip_id_str, bases_addr)
                return True
            else:
                BasesLog.mlogger.warn('set_bases_addr result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('set_bases_addr rep_data is None')

        return False

    def set_group(self, chip_id_str, group):
        print('set_group  chip_id_str:', chip_id_str, group)
        chip_id = self.chip_id_to_int_list(chip_id_str)
        if chip_id is None:
            return False
        send_data = BasesProtocal.packConfigGroup(chip_id, group)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('set_group result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('set_group rep_data is None')

        return False

    def set_host_name(self, chip_id_str, host_name):
        print('set_host_name  chip_id_str:', chip_id_str, host_name)
        chip_id = self.chip_id_to_int_list(chip_id_str)
        if chip_id is None:
            return False

        hostname = self.hostname_to_int(host_name)
        if hostname is None:
            return False

        send_data = BasesProtocal.packConfigHostname(chip_id, hostname)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('set_bases_led result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('set_bases_led rep_data is None')

        return False

    def set_bases_led(self, chip_id_str, led_status):
        print('set_bases_led  chip_id_str:', chip_id_str, led_status)
        chip_id = self.chip_id_to_int_list(chip_id_str)
        if chip_id is None:
            return False
        send_data = BasesProtocal.packConfigLed(chip_id, led_status)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('set_bases_led result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('set_bases_led rep_data is None')

        return False

    def set_bases_motor(self, chip_id_str, motor_status):
        print('set_bases_motor  chip_id_str:', chip_id_str, motor_status)
        chip_id = self.chip_id_to_int_list(chip_id_str)
        if chip_id is None:
            return False
        send_data = BasesProtocal.packConfigMotor(chip_id, motor_status)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                    return True
            else:
                BasesLog.mlogger.warn('set_bases_motor result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('set_bases_motor rep_data is None')

        return False

    def get_bases_info(self, address):
        send_data = BasesProtocal.packGetBasesInfo(address)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            rep_map = BasesProtocal.parseBasesInfo(rep_data)
            if rep_map is False:
                BasesLog.mlogger.warn('parseBasesInfo return false')
                return None

            bases_property = message_pb2.BaseStationProperty()
            bases_property.group = rep_map['group']
            bases_property.address = rep_map['address']
            bases_property.chip_id = rep_map['chip_id']
            bases_property.host_name = rep_map['name']
            bases_property.frequency = 22000
            bases_property.led_status = rep_map['led']
            bases_property.motor_speed = rep_map['motor']
            return bases_property

        else:
            BasesLog.mlogger.warn('get_bases_info rep_data is None:{}'.format(address))

        return None

    @staticmethod
    def chip_id_to_int_list(chip_id_str):
        """将ID转化成int型的数据"""
        if len(chip_id_str) != 24:
            BasesLog.mlogger.warn('chip_id_to_int_list :len(chip_id_str) != 24')
            return None

        chip_id_list = []

        i = 2
        n = 0
        while i <= len(chip_id_str):
            id_byte = chip_id_str[n:i]
            id_elem = int(id_byte, 16)
            chip_id_list.append(id_elem)
            n = i
            i += 2

        # print('chip_id_to_int_list: ', ['{:02x}'.format(i) for i in chip_id_list])
        return chip_id_list

    @staticmethod
    def hostname_to_int(host_name):
        """将hostname转化成int型数据"""
        if host_name in (None, ''):
            return None

        host_list = list(map(ord, host_name))

        if len(host_list) == 0:
            return None
        elif len(host_list) > 16:
            return None
        return host_list

    def handle_upgrade_request(self, msg):
        """
        升级基站的命令处理
        :param msg: message_pb2.LingTrackUpdateRequest
        """
        msg_parse = message_pb2.LingTrackUpdateRequest()
        msg_parse.ParseFromString(msg)
        print('BasesDevice LingTrackUpdateRequest:', msg_parse.type)
        with open('update.zip', 'w', encoding='utf-8') as f:
            f.write(msg_parse.detail)
        f.close()
        ZipUnzipFile.unzip_file('update.zip', r'./')

        update_address_list = list(msg_parse.bases_address_list)

        with open('update.bin', 'r', encoding='utf-8') as f:
            update_str = f.read()
            if self.send_begin_update_cmd(update_address_list) is False:
                return
            send_len = len(update_str)
            begin_loc = 0
            while True:
                if send_len > 2048:
                    if self.send_update_data(update_str[begin_loc:1024]) is False:
                        break
                else:
                    self.send_update_data(update_str[begin_loc:send_len])
                    # 发送完成退出
                    break
                #  每次发送2048个字节
                send_len = send_len - 2048
                begin_loc = begin_loc + 2048
            if self.send_end_update_cmd() is False:
                return

    def send_begin_update_cmd(self, address_list):
        send_data = BasesProtocal.packBeginUpdate(address_list)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('send_begin_update_cmd result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('send_begin_update_cmd rep_data is None')

        return False

    def send_update_data(self, data):
        send_data = BasesProtocal.packUpdateData(data)
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('send_update_data result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('send_update_data rep_data is None')
        return False

    def send_end_update_cmd(self):
        send_data = BasesProtocal.packEndUpdate()
        rep_data = self.send_cmd(send_data)
        if rep_data is not None:
            result = BasesProtocal.parseRepResult(rep_data)
            if result is True:
                return True
            else:
                BasesLog.mlogger.warn('send_end_update_cmd result is error:{}'.format(result))
        else:
            BasesLog.mlogger.warn('send_end_update_cmd rep_data is None')

        return False


if __name__ == '__main__':
    device = BasesDevice()
    while True:
        device.scan_bases()
        time.sleep(1)




