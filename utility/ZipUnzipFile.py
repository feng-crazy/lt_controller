#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2019/2/1 10:24
# @Author  : hedengfeng
# @Site    : 
# @File    : ZipUnzipFile.py
# @Software: LTController
# @description:

import os
import zipfile


class ZipUnzipFile(object):
    @classmethod
    def get_zip_file(input_path, result):
        """
        对目录进行深度优先遍历
        :param input_path:需要压缩的目录文件
        :param result: 目录列表添加list
        :return:
        """
        files = os.listdir(input_path)
        for file in files:
            if os.path.isdir(input_path + '/' + file):
                ZipUnzipFile.get_zip_file(input_path + '/' + file, result)
            else:
                result.append(input_path + '/' + file)

    @classmethod
    def zip_file_path(input_path, output_path, output_name):
        """
        压缩文件
        :param input_path: 压缩的文件夹路径
        :param output_path: 解压后（输出）的路径
        :param output_name: 压缩包名称
        :return:
        """
        f = zipfile.ZipFile(output_path + '/' + output_name, 'w', zipfile.ZIP_DEFLATED)
        filelists = []
        ZipUnzipFile.get_zip_file(input_path, filelists)
        for file in filelists:
            f.write(file)
        # 调用了close方法才会保证完成压缩
        f.close()
        return output_path + r"/" + output_name

    @classmethod
    def unzip_file(zipfilename, unziptodir):
        """
        解压文件
        :param zipfilename: 要解压的文件路径
        :param unziptodir: 解压后的文件目录
        :return:
        """
        if not os.path.exists(unziptodir):
            os.mkdir(unziptodir, 777)
        zfobj = zipfile.ZipFile(zipfilename)

        for name in zfobj.namelist():
            name = name.replace('\\', '/')
            if name.endswith('/'):
                os.mkdir(os.path.join(unziptodir, name))
            else:
                ext_filename = os.path.join(unziptodir, name)
                ext_dir = os.path.dirname(ext_filename)
                if not os.path.exists(ext_dir):
                    os.mkdir(ext_dir, 777)
                outfile = open(ext_filename, 'wb')
                outfile.write(zfobj.read(name))
                outfile.close()


if __name__ == '__main__':
    ZipUnzipFile.zip_file_path(r"./test", r"./", '123.zip')
    ZipUnzipFile.unzip_file('123.zip', r'./456')