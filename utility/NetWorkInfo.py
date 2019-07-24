#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 16:48
# @Author  : hedengfeng
# @Site    : 
# @File    : NetWorkInfo.py
# @Software: LT_controller

import platform
import psutil


class NetWorkInfo(object):
    """
    网络信息类，可以从这里获取mac地址，ip地址，主机名
    """
    UDP_BROADCAST_PORT = 56630
    TERMINAL_PROT = 56631
    MANAGER_PROT = 56632
    LOC_XSUB_PORT = 56633
    LOC_XPUB_PORT = 56634
    BASE_CONTROL_PORT = 56635

    def __init__(self):
        self.hostname = platform.node()

    @classmethod
    def get_mac_addr(cls, card_name):
        """获取MAC地址 card_name:网卡名称"""
        net_all_info = psutil.net_if_addrs()
        for k, v in net_all_info.items():
            if k == card_name:
                for item in v:
                    address = item[1]
                    if '-' in address or ':' in address and len(address) == 17:
                        address = address.replace(':', '-')
                        return address
        return None

    @classmethod
    def get_ip_addr(cls, card_name):
        """获取ip地址 card_name:网卡名称"""
        net_all_info = psutil.net_if_addrs()
        for k, v in net_all_info.items():
            if k == card_name:
                for item in v:
                    if item[0] == 2:
                        ip_addr = item[1]
                        return ip_addr
        return None

    @staticmethod
    def get_all_ip_addr():
        ip_addr_list = []
        net_all_info = psutil.net_if_addrs()
        for k, v in net_all_info.items():
                for item in v:
                    if item[0] == 2:
                        ip_addr_list.append(item[1])
        return ip_addr_list

    @staticmethod
    def judge_ip_network_segment(src_ip_list, dest_ip):
        dest_ip_char_list = dest_ip.split('.')
        for ip_item in src_ip_list:
            src_ip_char_list = ip_item.split('.')
            if src_ip_char_list[0] == dest_ip_char_list[0] and src_ip_char_list[1] == dest_ip_char_list[1] \
                    and src_ip_char_list[2] == dest_ip_char_list[2]:
                return ip_item

        return False

    @classmethod
    def get_host_name(cls):
        """获取主机名"""
        return platform.node()

    @classmethod
    def get_platform(cls):
        """获取操作系统类型"""
        return platform.system()


if __name__ == '__main__':
    mac_addr = NetWorkInfo.get_mac_addr("wlan0")
    print('mac_addr', mac_addr, type(mac_addr))
    ip_addr = NetWorkInfo.get_ip_addr("wlan0")
    print('ip_addr', ip_addr, type(ip_addr))
    hostname = NetWorkInfo.get_host_name()
    print('hostname', hostname, type(hostname))
    system_type = NetWorkInfo.get_platform()
    print('system_type', system_type, type(system_type))

# if __name__ == '__main__':
#     mac_addr = NetWorkInfo.get_mac_addr("wlan0")
#     print(mac_addr)
#     ip_addr = NetWorkInfo.get_ip_addr("wlan0")
#     print(ip_addr)
#     hostname = NetWorkInfo.get_host_name()
#     print(hostname)
