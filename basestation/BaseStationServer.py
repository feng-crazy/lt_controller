#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/12/24 10:27
# @Author  : hedengfeng
# @Site    : 
# @File    : BaseStationServer.py
# @Software: LTController
# @description:
import threading
import socket

from basestation.BasesLog import BasesLog
from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType
from utility.NetWorkInfo import NetWorkInfo

from basestation.BasesController import BaseController


class BaseStationServer(EventTarget):
    def __init__(self):
        """"""
        super(BaseStationServer, self).__init__(self)

        self.base_ctrl = BaseController('BaseController')

        self.thread = threading.Thread(target=self.server_run, args=(), name='BaseStationServer')
        self.thread.setDaemon(True)

        self.bases_ctrller_connect_flag = False

        self.subscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.subscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT, self)

    def event_handle(self, event, event_content):
        if event == LTEventType.EVENT_SYSTEM_STARTUP:
            self.thread.start()
        elif event == LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT:
            print('BaseStationServer handle EVENT_BASE_STATION_CTRLLER_DISCONNECT')
            self.bases_ctrller_connect_flag = False
            self.base_ctrl.stop()

    def server_run(self):
        """"""
        print('********************************************************************')
        try:
            bind_ip = ''
            bind_port = NetWorkInfo.BASE_CONTROL_PORT

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((bind_ip, bind_port))
            server.listen(5)
            print('Listening on {}:{}'.format(bind_ip, bind_port))
            while True:
                client_sock, client_addr = server.accept()

                self.connnect_handler(client_addr, client_sock)
        except Exception as e:
            BasesLog.mlogger.warn('BaseStationServer Exception err {}'.format(e))

    def connnect_handler(self, address, client_sock):
        """new实例BasesController"""
        print('Got connection from {}'.format(address))
        if self.bases_ctrller_connect_flag is True:
            print('目前只支持连接一个基站控制器。。。。')
            client_sock.close()
            return

        client_sock.settimeout(5)
        self.base_ctrl.set_address_socket(address, client_sock)
        self.bases_ctrller_connect_flag = True

        event = LTEventType.EVENT_BASE_STATION_CTRLLER_CONNECT
        event_content = b''
        self.publish_event(event, event_content)

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_SYSTEM_STARTUP, self)
        self.unsubscribe(LTEventType.EVENT_BASE_STATION_CTRLLER_DISCONNECT, self)
        super(BaseStationServer, self).__del__()

# if __name__ == '__main__':
#     echo_server(('', 20000))

