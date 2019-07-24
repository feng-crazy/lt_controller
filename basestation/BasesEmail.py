#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/7/17 15:25
# @Author  : hedengfeng
# @Site    : 
# @File    : BasesEmail.py
# @Software: LTController
# @description: 定时的发送基站信息邮件的类
import datetime
import smtplib
import sys
import traceback
from email.mime.text import MIMEText
from email.header import Header

from basestation import BasesLog
from eventbus.EventTarget import EventTarget
from utility.LTCommon import LTEventType


class BasesEmail(EventTarget):

    def __init__(self):
        super(BasesEmail, self).__init__(self)

        self.sender = 'hedengfeng@lingtrack.com'  # 'qiaozhiyong@lingtrack.com'
        self.password = 'hdf654321'  #

        # receiver
        self.receiver = ['894220128@qq.com', '42704329@qq.com']

        # server
        self.smtp_server = 'smtp.qq.com'  # 'smtp.exmail.qq.com'
        self.port = 25

        self.time_count = 0

        self.subscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)

    def send_email(self, data):
        message = MIMEText(data, 'plain', 'utf-8')  # MIMEText(data,'plain','utf-8')
        message['From'] = self.sender  # Header(sender,'utf-8') # Header('raspberrypi','utf-8')
        message['To'] = ','.join(self.receiver)

        subject = 'BaseStation Info'
        message['Subject'] = Header(subject, 'utf-8')

        try:

            smtp = smtplib.SMTP()

            smtp.connect(self.smtp_server, self.port)

            smtp.login(self.sender, self.password)  # username

            smtp.sendmail(self.sender, self.receiver, message.as_string())
            smtp.quit()
        except smtplib.SMTPException:
            traceback.print_stack()

    def event_handle(self, event, event_content):
        """
        事件处理函数，该函数可以理解为纯虚函数，EventTarget子类必须要实现
        """
        # print('BaseStation ', 'event_handle', event)
        if event == LTEventType.EVENT_SYSTEM_TIME_1:
            self.time_count += 1
            if self.time_count >= 3600:
                self.time_count = 0
                with open(BasesLog.LOG_FILE, 'r', encoding='utf-8') as f:
                    send_data = f.read()
                    self.send_email(send_data)

    def __del__(self):
        self.unsubscribe(LTEventType.EVENT_SYSTEM_TIME_1, self)
        super(BasesEmail, self).__del__()


if __name__ == '__main__':
    base_mail = BasesEmail()

