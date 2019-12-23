# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import os
import mimetypes
import datetime
import traceback
import sys
import random
import string
import subprocess
import shutil
import zipfile
import io

from email import encoders
from email.header import Header

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection, SafeMIMEText
from django.core.mail.message import MIMEBase
from django.db import connection
from django.utils.encoding import smart_str

from utils.errors import CustomException
from utils import constants, common


logger = common.get_sales_logger()


class EbMail(object):

    def __init__(self, sender=None, recipient_list=None, cc_list=None, attachment_list=None, is_encrypt=True,
                 mail_title=None, mail_body=None, pass_body=None, addressee=None, zip_file_name=None):
        self.addressee = addressee
        self.sender = sender
        self.recipient_list = EbMail.str_to_list(recipient_list)
        self.cc_list = EbMail.str_to_list(cc_list)
        self.attachment_list = attachment_list
        self.is_encrypt = is_encrypt
        self.mail_title = mail_title
        self.mail_body = mail_body
        self.password = None
        self.pass_body = pass_body
        self.temp_files = []
        self.zip_file_name = zip_file_name

    def check_recipient(self):
        if not self.recipient_list:
            raise CustomException("宛先はありません。")

    def check_attachment(self):
        if self.attachment_list:
            for attachment in self.attachment_list:
                if not os.path.exists(attachment):
                    raise CustomException("ファイル「%s」が見つかりません。" % attachment)

    def check_mail_title(self):
        if not self.mail_title:
            raise CustomException("メールの題名を設定してください。")

    @classmethod
    def get_mail_connection(cls):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select value from mst_config where name = %s "
                    " union all "
                    "select value from mst_config where name = %s "
                    " union all "
                    "select value from mst_config where name = %s "
                    " union all "
                    "select value from mst_config where name = %s ",
                    [constants.CONFIG_ADMIN_EMAIL_SMTP_HOST, constants.CONFIG_ADMIN_EMAIL_SMTP_PORT,
                     constants.CONFIG_ADMIN_EMAIL_ADDRESS, constants.CONFIG_ADMIN_EMAIL_PASSWORD]
                )
                host, port, username, password = cursor.fetchall()
            backend = get_connection()
            backend.host = str(host[0])
            backend.port = int(port[0])
            backend.username = str(username[0])
            backend.password = str(password[0])
            return backend
        except Exception as ex:
            logger.error(unicode(ex))
            logger.error(traceback.format_exc())
            raise CustomException(unicode(ex))

    @classmethod
    def str_to_list(cls, s):
        if isinstance(s, basestring):
            return [i.strip() for i in s.split(',') if i]
        else:
            return s

    def zip_attachments(self):
        if self.attachment_list:
            if sys.platform in ("linux", "linux2"):
                # tempフォルダー配下の一時フォルダーを取得する
                temp_path = os.path.join(common.get_temp_path(), datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
                if not os.path.exists(temp_path):
                    os.mkdir(temp_path)
                    self.temp_files.append(temp_path)
                temp_zip = os.path.join(common.get_temp_path(), datetime.datetime.now().strftime('%Y%m%d%H%M%S%f.zip'))
                self.temp_files.append(temp_zip)
                file_list = []
                for attachment_file in self.attachment_list:
                    if '注文書' in attachment_file:
                        new_path = os.path.join(temp_path, os.path.basename('注文書.pdf'))
                    elif '注文請書' in attachment_file:
                        new_path = os.path.join(temp_path, os.path.basename('注文請書.pdf'))
                    else:
                        new_path = os.path.join(temp_path, os.path.basename(attachment_file))
                    file_list.append(new_path)
                    self.temp_files.append(new_path)
                    shutil.copy(attachment_file, new_path)
                password = self.generate_password()
                # tempフォルダー配下すべてのファイル名をUTF8からShift-JISに変換する
                subprocess.call(["convmv", "-r", "-f", "utf8", '-t', 'sjis', '--notest', temp_path.rstrip('/') + '/'])
                # 一時フォルダーを圧縮する
                command = "zip --password {0} -j {1} {2}/*".format(password, temp_zip, temp_path.rstrip('/'))
                print(command)
                subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                bytes = open(temp_zip, 'rb', ).read()
                return bytes
            else:
                buff = io.BytesIO()
                in_memory_zip = zipfile.ZipFile(buff, mode='w')
                for attachment_file in self.attachment_list:
                    if attachment_file.is_bytes():
                        in_memory_zip.writestr(attachment_file.filename, attachment_file.content)
                    else:
                        in_memory_zip.write(attachment_file.filename, attachment_file.path)
                in_memory_zip.close()
                return buff.getvalue()
        else:
            return None

    def escape(self, name):
        """Shift_JISのダメ文字対策

        2バイト目に「5C」のコードが使われている文字は、次のようなものがあります。
        ―ソЫⅨ噂浬欺圭構蚕十申曾箪貼能表暴予禄兔喀媾彌拿杤歃濬畚秉綵臀藹觸軆鐔饅鷭偆砡

        :param name:
        :return:
        """
        chars = u"ソЫⅨ噂浬欺圭構蚕十申曾箪貼能表暴予禄兔喀媾彌拿杤歃濬畚秉綵臀藹觸軆鐔饅鷭偆砡"
        s = name
        for c in chars:
            if c in s:
                s = s.replace(c, u"＿")
        return s

    def generate_password(self, length=8):
        self.password = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
        return self.password

    def send_email(self):
        try:
            self.check_recipient()
            self.check_attachment()
            self.check_mail_title()

            mail_connection = self.get_mail_connection()
            if not self.sender:
                self.sender = mail_connection.username

            email = EmailMultiAlternativesWithEncoding(
                subject=self.mail_title,
                body=self.mail_body,
                from_email=self.sender,
                to=self.recipient_list,
                cc=self.cc_list,
                connection=mail_connection
            )
            attachments = self.zip_attachments()
            if attachments:
                email.attach('%s.zip' % self.zip_file_name, attachments, constants.MIME_TYPE_ZIP)
            email.send()
            # パスワードを送信する。
            self.send_password(mail_connection)
            log_format = u"題名: %s; TO: %s; CC: %s; 送信完了。"
            logger.info(log_format % (self.mail_title, ','.join(self.recipient_list), ','.join(self.cc_list)))
        except subprocess.CalledProcessError as e:
            logger.error(e.output)
        finally:
            # 一時ファイルを削除
            for path in self.temp_files:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)

    def send_password(self, conn):
        if self.attachment_list and self.is_encrypt:
            # TODO: パスワードの送信もメールテンプレートに管理する。
            try:
                body = self.pass_body.format(password=self.password)
            except Exception:
                body = "PW: %s" % self.password
            email = EmailMultiAlternativesWithEncoding(
                subject=self.mail_title,
                body=body,
                from_email=self.sender,
                to=self.recipient_list,
                cc=self.cc_list,
                connection=conn
            )
            email.send()
            logger.info("%sのパスワードは送信しました。" % self.mail_title)


class EmailMultiAlternativesWithEncoding(EmailMultiAlternatives):
    def _create_attachment(self, filename, content, mimetype=None):
        """
        Converts the filename, content, mimetype triple into a MIME attachment
        object. Use self.encoding when handling text attachments.
        """
        if mimetype is None:
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype is None:
                mimetype = constants.MIME_TYPE_EXCEL
        basetype, subtype = mimetype.split('/', 1)
        if basetype == 'text':
            encoding = self.encoding or settings.DEFAULT_CHARSET
            attachment = SafeMIMEText(smart_str(content, settings.DEFAULT_CHARSET), subtype, encoding)
        else:
            # Encode non-text attachments with base64.
            attachment = MIMEBase(basetype, subtype)
            attachment.set_payload(content)
            encoders.encode_base64(attachment)
        if filename:
            try:
                filename = filename.encode('ascii')
            except UnicodeEncodeError:
                filename = Header(filename, 'utf-8').encode()
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        return attachment
