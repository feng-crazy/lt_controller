#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 10:47
# @Author  : hedengfeng
# @Site    : 
# @File    : controller.py
# @Software: LT_controller
import asyncio
import multiprocessing
import os

import select
import sys
from socket import *

import time
import signal
import traceback

from ControllerBroadcast import ControllerBroadcast
from ManagerDevice import ManagerDevice
# from basestation.BasesController import BaseController
from basestation.BaseStationServer import BaseStationServer
from eventbus.EventBus import EventBus
from eventbus.EventClient import EventClient
from terminal.LocDataProxy import LocDataProxy
from terminal.TermController import TermController
from utility import message_pb2
from utility.LTCommon import LTEventType
from utility.Mlogging import MLog

from utility.NetWorkInfo import NetWorkInfo

operating_system_type = NetWorkInfo.get_platform()


class MainController(object):
    def __init__(self):
        if operating_system_type != 'Windows':
            self.register_signal()
        self.contorller_exit_flag = False
        self.loc_proxy = None
        self.terminal_ctrl = None
        self.bases_server = None
        self.manager_dev = None
        self.broadcast = None

        # if self.check_ctrller_exit():
        #     sys.exit()

        self.eventbus = EventBus()
        self.main_event_client = EventClient()

        main_loop = asyncio.get_event_loop()
        tasks = [self.system_initialize(), self.main_task_handle(),
                 self.system_timer(), self.delay_system_startup()]
        future = asyncio.wait(tasks)
        main_loop.run_until_complete(future)

        main_loop.close()

    async def system_timer(self):
        """
        发布系统的每一秒的定时事件
        """
        old_time = time.time()
        while True:
            current_time = time.time()
            time_diff = current_time - old_time
            if time_diff >= 1.0:
                event = LTEventType.EVENT_SYSTEM_TIME_1
                event_content = bytes()
                self.main_event_client.publish_event(event, event_content)
                old_time = current_time

            await asyncio.sleep(0.01)

            if self.contorller_exit_flag:
                break
        return

    async def main_task_handle(self):
        """
        主线程的消息客户端事件处理
        """
        # print('main_task_handle: ', threading.get_ident())
        while True:
            if self.main_event_client is not None:
                try:
                    self.main_event_client.handle_event()
                except Exception as err:
                    MLog.mlogger.warn('Exception as err:%s', err)
                    MLog.mlogger.warn(traceback.format_exc())
            await asyncio.sleep(0.01)

            if self.contorller_exit_flag:
                break
        return

    async def system_initialize(self):
        try:
            self.loc_proxy = LocDataProxy()
            # 不要调整初始化顺序
            self.manager_dev = ManagerDevice('ManagerDevice')
            
            self.terminal_ctrl = TermController('TermController')

            self.bases_server = BaseStationServer()

            self.broadcast = ControllerBroadcast()
        except Exception as err:
            MLog.mlogger.warn('Exception as err:%s', err)
            MLog.mlogger.warn(traceback.format_exc())

        # 初始化完成之后循环处理广播
        while True:
            try:
                self.broadcast.handle_broadcast()
            except Exception as err:
                MLog.mlogger.warn('Exception as err:%s', err)
                MLog.mlogger.warn(traceback.format_exc())
            await asyncio.sleep(0.0001)  # 100 us

            if self.contorller_exit_flag:
                break
        return

    async def delay_system_startup(self):
        """系统必须要延迟启动，因为当网络环境没有准备好，就启动会导致阻塞，
        必须要先接收足够多的广播包，网络中的终端都连接之后才启动"""
        await asyncio.sleep(3)  # 延迟3秒启动，让其接收广播包
        event = LTEventType.EVENT_SYSTEM_STARTUP
        event_content = bytes()
        self.main_event_client.publish_event(event, event_content)

    @staticmethod
    def check_ctrller_exit():
        """检查局域网，是否存在其他控制器的广播，如果存在整个程序退出"""
        host = ''
        prot = NetWorkInfo.UDP_BROADCAST_PORT
        buf_size = 1024
        udp_addr = (host, prot)
        recv_udp_sock = socket(AF_INET, SOCK_DGRAM)
        recv_udp_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        recv_udp_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        recv_udp_sock.settimeout(2)  # 2秒内收到广播说明存在，否则不存在
        recv_udp_sock.bind(udp_addr)

        try:
            data, addr = recv_udp_sock.recvfrom(buf_size)
            print('_recv_broadcast:', data, addr)
            msg = message_pb2.ControllerBroadcast()
            msg.ParseFromString(data)
            recv_udp_sock.close()
            MLog.mlogger.warn('The LAN cannot have two controllers at the same time')
            return True  # 检查到局域网已经存在了控制器，这个控制器退出
        except Exception as err:
            return False

    def signal_handler(self, signum, frame):
        print('Received signal: ', signum)
        # traceback.print_stack()

        self.contorller_exit_flag = True

        self.manager_dev.exit()
        self.terminal_ctrl.exit()
        self.bases_server.exit()
        # self.loc_proxy.exit_child_process()
        # self.eventbus.exit_bus()
        # self.broadcast.exit()
        time.sleep(0.5)
        os._exit(0)

    def register_signal(self):
        signal.signal(signal.SIGHUP, self.signal_handler)  # 1
        signal.signal(signal.SIGINT, self.signal_handler)  # 2
        signal.signal(signal.SIGQUIT, self.signal_handler)  # 3
        signal.signal(signal.SIGABRT, self.signal_handler)  # 6
        signal.signal(signal.SIGTERM, self.signal_handler)  # 15
        signal.signal(signal.SIGSEGV, self.signal_handler)  # 11


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main_controller = MainController()
    os._exit(0)










