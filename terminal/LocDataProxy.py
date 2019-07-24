#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/2 13:56
# @Author  : hedengfeng
# @Site    : 
# @File    : LocDataProxy.py
# @Software: LT_controller
import sys

from utility.NetWorkInfo import NetWorkInfo

import zmq
from multiprocessing import Process
import os


class LocDataProxy(object):
    """控制器转发终端位置数据"""

    def __init__(self):
        # print('Parent process %s.' % os.getpid())
        self.xsubsocket = None
        self.xpubsocket = None
        self.p = Process(target=self._create_loc_process, args=())
        # print('Child process will start.')
        self.p.start()
        # print('LocDataProxy end.')

    def _create_loc_process(self):
        print('create_loc_process')
        self.context = zmq.Context()
        self.xsubsocket = self.context.socket(zmq.XSUB)
        self.xsubsocket_addr = "tcp://*:" + str(NetWorkInfo.LOC_XSUB_PORT)
        self.xsubsocket.bind(self.xsubsocket_addr)

        self.xpubsocket = self.context.socket(zmq.XPUB)
        self.xpubsocket.setsockopt(zmq.XPUB_VERBOSE, 1)
        self.xpubsocket_addr = "tcp://*:" + str(NetWorkInfo.LOC_XPUB_PORT)
        self.xpubsocket.bind(self.xpubsocket_addr)
        try:
            zmq.proxy(self.xpubsocket, self.xsubsocket)
        except Exception as err:
            print('zmq.proxy err:', err)
            self.xsubsocket.close()
            self.xpubsocket.close()
            self.context.term()

    def exit_child_process(self):
        # self.xsubsocket.close()
        # self.xpubsocket.close()
        # self.context.term()
        self.p.terminate()
        # self.p.join()

    # def __del__(self):
    #     self.exit_child_process()


if __name__ == '__main__':
    loc_proxy = LocDataProxy()