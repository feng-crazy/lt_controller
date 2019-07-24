#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/8/8 14:42
# @Author  : hedengfeng
# @Site    : 
# @File    : py
# @Software: LTController
# @description: spi数据的解析和封包功能


PACK_HEAD1 = 0xf1
PACK_HEAD2 = 0xf2
PACK_HEAD = [PACK_HEAD1, PACK_HEAD2]

CMD_GET_BASES_LIST = 0xc2  # 获取当前基站列表
CMD_GET_BASES_INFO = 0xc3  # 获取一个基站详细信息
CMD_CONFIG_ADDR = 0xc4  # 配置基站地址
CMD_CONFIG_GROUP = 0xc5  # 配置某一个基站组号
CMD_CONFIG_LED = 0xc6  # 配置某一个基站led
CMD_CONFIG_MOTOR = 0xc7  # 配置某一个基站电机
CMD_CONFIG_NAME = 0xc8  # 配置某一个基站名称

CMD_BEGIN_UPDATE = 0xca  # 开始升级命令
CMD_END_UPDATE = 0xcb  # 结束升级命令
CMD_UPDATEING = 0xcc  # 基站升级命令

PACK_FIXED_LENGH = 6  # 包的固定长度  除去数据段的长度


def judgeCheckSum(data):
    check_sum = (data[-2] << 8) + data[-1]
    calc_check_sum = 0
    for i in range(0, len(data) - 2):
        calc_check_sum += data[i]
    calc_check_sum = calc_check_sum & 0xffff
    if check_sum != calc_check_sum:
        print('judgeCheckSum is error:', check_sum, calc_check_sum)
        print('judgeCheckSum is error:', ['{:02x}'.format(i) for i in data])
        return False
    return True


def fillCheckSum(data):
    calc_check_sum = 0
    for i in range(0, len(data)):
        calc_check_sum += data[i]

    high_bytes = (calc_check_sum >> 8) & 0xFF
    low_bytes = calc_check_sum & 0xFF
    data.append(high_bytes)
    data.append(low_bytes)


def getLengh(data):
    return data[3]


def getPackType(data):
    return data[2]


def getDataSegment(data):
    data_len = data[3]
    data_end = 4 + data_len
    if data_len > 0:
        return data[4:data_end]
    else:
        return None


def packGetBasesList():
    pack_data = []
    data_len = 0
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_GET_BASES_LIST)
    pack_data.append(data_len)
    fillCheckSum(pack_data)
    return pack_data


def packGetBasesInfo(bases_addr):
    pack_data = []
    data_len = 1
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_GET_BASES_INFO)
    pack_data.append(data_len)
    pack_data.append(bases_addr)
    fillCheckSum(pack_data)
    return pack_data


def packConfigAddr(chip_id, bases_addr):
    """
    :param: chip_id 12字节的基站chip_id list
    :param: bases_addr 基站地址
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = 13  # len(chip_id) + 1
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_CONFIG_ADDR)
    pack_data.append(data_len)
    pack_data.extend(chip_id)
    pack_data.append(bases_addr)
    fillCheckSum(pack_data)
    return pack_data


def packConfigGroup(chip_id, group):
    """
    :param: chip_id 12字节的基站chip_id list
    :param: group 基站组号
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = 13  # len(chip_id) + 1
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_CONFIG_GROUP)
    pack_data.append(data_len)
    pack_data.extend(chip_id)
    pack_data.append(group)
    fillCheckSum(pack_data)
    return pack_data


def packConfigLed(chip_id, led_status):
    """
    :param: chip_id 12字节的基站chip_id
    :param: led_status led状态
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = 13  # len(chip_id) + 1
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_CONFIG_LED)
    pack_data.append(data_len)
    pack_data.extend(chip_id)
    pack_data.append(led_status)
    fillCheckSum(pack_data)
    return pack_data


def packConfigMotor(chip_id, motor_status):
    """
    :param: chip_id 12字节的基站chip_id
    :param: motor_status motor
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = 13  # len(chip_id) + 1
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_CONFIG_MOTOR)
    pack_data.append(data_len)
    pack_data.extend(chip_id)
    pack_data.append(motor_status)
    fillCheckSum(pack_data)
    return pack_data


def packConfigHostname(chip_id, hostname):
    """
    :param: chip_id 12字节的基站chip_id
    :param: hostname 基站名字
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = len(chip_id) + len(hostname)
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_CONFIG_NAME)
    pack_data.append(data_len)
    pack_data.extend(chip_id)
    pack_data.extend(hostname)
    fillCheckSum(pack_data)
    return pack_data


def packBeginUpdate(addr_list):
    """
    :param: 开始升级基站的list
    :rtype: 命令的数据包
    """
    pack_data = []
    data_len = len(addr_list)
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_BEGIN_UPDATE)
    pack_data.append(data_len)
    pack_data.extend(addr_list)
    fillCheckSum(pack_data)
    return pack_data


def packEndUpdate():
    """
    :rtype: 结束升级的数据包
    """
    pack_data = []
    data_len = 0
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_END_UPDATE)
    pack_data.append(data_len)
    fillCheckSum(pack_data)
    return pack_data


def packUpdateData(data):
    """
    :rtype: 升级的数据包
    """
    pack_data = []
    data_len = len(data)
    pack_data.append(PACK_HEAD1)
    pack_data.append(PACK_HEAD2)
    pack_data.append(CMD_UPDATEING)
    pack_data.append(data_len)
    pack_data.extend(data)
    fillCheckSum(pack_data)
    return pack_data


def parseAddrList(data):
    """
    :data: list
    :rtype: list
    """
    pack_type = getPackType(data)
    if pack_type != CMD_GET_BASES_LIST:
        return False
    data_segment = getDataSegment(data)
    if data_segment is None:
        return False
    return data_segment


def parseBasesInfo(data):
    """
    :data: list
    :rtype: dict
    """
    info_map = {}
    chip_id = ''
    pack_type = getPackType(data)
    if pack_type != CMD_GET_BASES_INFO:
        return False
    data_segment = getDataSegment(data)
    if data_segment is None:
        return False

    info_map['group'] = data_segment[0]
    info_map['address'] = data_segment[1]
    chip_id_list = data_segment[2:14]
    for elem in chip_id_list:
        chip_id += '{:02x}'.format(elem)
    info_map['chip_id'] = chip_id
    info_map['led'] = data_segment[15]
    info_map['motor'] = data_segment[16]
    name_list = data_segment[17:]
    name_bytes = bytes(name_list)
    info_map['name'] = name_bytes.decode()
    return info_map


def parseRepResult(data):
    """
    :rtype: bool
    """
    data_segment = getDataSegment(data)
    if data_segment is None:
        return False
    if data_segment[0] == 0:
        return False
    else:
        return True
