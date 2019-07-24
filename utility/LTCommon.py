#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/6/22 14:10
# @Author  : hedengfeng
# @Site    : 
# @File    : LTCommon.py
# @Software: LT_controller


class LTEventType(object):
    """
    系统事件类型定义
    """
    EVENT_SYSTEM_STARTUP = 'system startup event'  # 系统启动事件
    EVENT_SYSTEM_TIME_1 = 'once per second'  # 系统每秒一次的定时事件

    EVENT_RECV_TERM_CAST_REP = 'recv term cast rep'  # 收到终端广播的响应
    EVENT_RECV_MANAGER_CAST_REP = 'recv manager cast rep'  # 收到Manager的广播响应
    EVENT_TERMINAL_LIST_UPDATE = 'terminal list update'  # 发现并连上新的终端,或者终端断开连接，更新终端列表
    # EVENT_ACTIVE_BASES_LIST_UPDATE = 'active base station list update'  # 发现并连上新的基站，或者基站断开连接，更新基站列表
    EVENT_ALL_BASES_LIST_UPDATE = 'all base station list update'  # 所有的基站配置列表更新
    EVENT_BASE_STATION_CONFIG_UPDATE = 'base station config update'  # 基站配置更新
    EVENT_A_TERMINAL_DISCONNECT = 'a terminal disconnect'  # 某一个终端断开连接事件，事件内容为终端的MAC地址

    EVENT_BASE_STATION_CTRLLER_DISCONNECT = 'base station controller disconnect'  # 基站控制器断开连接
    EVENT_BASE_STATION_CTRLLER_CONNECT = 'base station controller connect'  # 基站控制器连接
    EVENT_A_BASE_STATION_DISCONNECT = 'a base station disconnect'  # 一个基站断开连接
    EVENT_A_NEW_BASE_STATION_CONNECT = 'a new base station connect'  # 一个新的基站连接上
    EVENT_TERMINAL_EXCEPT_STATUS = 'terminal except status'  # 某一个终端异常状态事件

    # 以下是终端terminal.py的事件
    EVENT_FIND_CONTROLLER = 'find controller'  # 用于终端上接收到了控制器的广播包，发现了控制器的事件,用于在终端的消息，控制器不用
    EVENT_NETWORK_DISCONNECT = 'network disconnect'  # 用于网络连接断开了的事件,用于在终端的消息，控制器不用
    EVENT_NETWORK_CONNECTED = 'network connected'  # 用于网络连接上的事件,用于在终端的消息，控制器不用
    EVENT_RESTART_TERMIANL_BIN = 'restart terminal bin'  # 重启终端LT执行文件事件,用于在终端的消息，控制器不用
    EVENT_RESTART_TERMIANL_SYSTEM = 'restart terminal system'  # 重启终端系统,用于在终端的消息，控制器不用
    EVENT_UPDATE_TERMINAL_BIN = 'update terminal bin file'  # 更新终端的bin文件 用于在终端的消息，控制器不用
    EVENT_SENSOR_HOT_PLUG = 'sensor hot plug'  # 传感器热插拔事件
    EVENT_CONFIG_FILE_ERROR = 'config file error'  # 配置文件错误
    EVENT_START_CALIBRATION = 'start calibaration'  # 终端进入标定状态
    EVENT_STOP_CALIBRATION = 'stop calibaration'  # 终端退出标定状态
    EVENT_RUNTIME_CHECK = 'runtime check'  # 运行时检测事件
    EVENT_RUNTIME_CHECK_FINISH = 'runtime check finish'  # 运行时检测完成事件
    EVENT_UPDATE_TERMINAL_PRO = 'update terminal property'  # 更新终端属性事件
    EVENT_TERM_ACTION_REQUEST = 'terminal action request'  # 终端动作请求事件
    EVENT_TERM_UPGRADE_REQUEST = 'terminal update request'  # 终端更新请求事件

    # 以下是基站请求事件
    EVENT_UPDATE_BASE_STATION_PRO = 'update base station property'  # 更新基站属性事件
    EVENT_BASE_STATION_ACTION_REQUEST = 'base station action request'  # 基站动作请求事件
    EVENT_BASE_STATION_REMOVE_REQUEST = 'base station remove request'  # 基站移除请求事件
    EVENT_BASE_STATION_APPEND_REQUEST = 'base station append request'  # 基站添加请求事件
    EVENT_BASES_EXCEPT_STATUS = 'base station config conflict'  # 基站冲突事件
    EVENT_BASE_UPGRADE_REQUEST = 'base station update request'  # 基站更新请求事件
    EVENT_BASE_CTRLLER_UPGRADE_REQUEST = 'base station controller update request'  # 基站控制器更新请求事件
