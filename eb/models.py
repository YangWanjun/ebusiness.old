# coding: UTF-8
"""
Created on 2015/08/20

@author: Yang Wanjun
"""
import datetime
import re
import os
import urllib2
import logging
import traceback
import mimetypes
import math
import uuid

from email import encoders
from email.header import Header
from xml.etree import ElementTree

from django.db import models, connection
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.validators import RegexValidator
from django.db.models import Max, Min, Q, Sum, Prefetch, Subquery, OuterRef
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.encoding import smart_str
from django.template import Context, Template
from django.core.mail import EmailMultiAlternatives, get_connection, SafeMIMEText
from django.core.mail.message import MIMEBase
from django.conf import settings
from django.core.validators import validate_comma_separated_integer_list
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

# from django.contrib.contenttypes.models import ContentType
# from django.contrib.contenttypes.fields import GenericForeignKey

from utils import common, constants
from utils.errors import CustomException


class AbstractCompany(models.Model):
    name = models.CharField(blank=False, null=False, unique=True, max_length=30, verbose_name=u"会社名")
    japanese_spell = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"フリカナ")
    president = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"代表者名")
    found_date = models.DateField(blank=True, null=True, verbose_name=u"設立年月日")
    capital = models.BigIntegerField(blank=True, null=True, verbose_name=u"資本金")
    post_code = models.CharField(blank=True, null=True, max_length=7, verbose_name=u"郵便番号")
    address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"住所１")
    address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"住所２")
    tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"電話番号")
    fax = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"ファックス")

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name


class AbstractMember(models.Model):
    employee_id = models.CharField(blank=False, null=False, unique=True, max_length=30, verbose_name=u"社員ID")
    first_name = models.CharField(blank=False, null=False, max_length=30, verbose_name=u"姓")
    last_name = models.CharField(blank=False, null=False, max_length=30, verbose_name=u"名")
    first_name_ja = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"姓(フリカナ)")
    last_name_ja = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"名(フリカナ)")
    first_name_en = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"姓(ローマ字)",
                                     help_text=u"先頭文字は大文字にしてください（例：Zhang）")
    last_name_en = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"名(ローマ字)",
                                    help_text=u"漢字ごとに先頭文字は大文字にしてください（例：XiaoWang）")
    sex = models.CharField(blank=True, null=True, max_length=1, choices=constants.CHOICE_SEX, verbose_name=u"性別")
    country = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"国籍・地域")
    birthday = models.DateField(blank=True, null=True, verbose_name=u"生年月日")
    graduate_date = models.DateField(blank=True, null=True, verbose_name=u"卒業年月日")
    join_date = models.DateField(blank=True, null=True, default=timezone.now, verbose_name=u"入社年月日")
    email = models.EmailField(blank=True, null=True, verbose_name=u"会社メールアドレス")
    private_email = models.EmailField(blank=True, null=True, verbose_name=u"個人メールアドレス")
    post_code = models.CharField(blank=True, null=True, max_length=7, verbose_name=u"郵便番号",
                                 help_text=u"数値だけを入力してください、例：1230034")
    address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"住所１")
    address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"住所２")
    lat = models.CharField(blank=True, null=True, max_length=25, verbose_name=u"緯度")
    lng = models.CharField(blank=True, null=True, max_length=25, verbose_name=u"経度")
    coordinate_update_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"座標更新日時")
    nearest_station = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"最寄駅")
    years_in_japan = models.IntegerField(blank=True, null=True, verbose_name=u"在日年数")
    phone = models.CharField(blank=True, null=True, max_length=11, verbose_name=u"電話番号",
                             help_text=u"数値だけを入力してください、例：08012345678")
    is_married = models.CharField(blank=True, null=True, max_length=1,
                                  choices=constants.CHOICE_MARRIED, verbose_name=u"婚姻状況")
    company = models.ForeignKey('Company', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"会社")
    japanese_description = models.TextField(blank=True, null=True, verbose_name=u"日本語能力の説明")
    certificate = models.TextField(blank=True, null=True, verbose_name=u"資格の説明")
    skill_description = models.TextField(blank=True, null=True, verbose_name=u"得意")
    comment = models.TextField(blank=True, null=True, verbose_name=u"備考")
    notify_type = models.IntegerField(default=1, choices=constants.CHOICE_NOTIFY_TYPE, verbose_name=u"通知種類",
                                      help_text=u"メール通知時に利用する。EBのメールアドレスを設定すると、"
                                                u"通知のメールはEBのアドレスに送信する")
    is_retired = models.BooleanField(blank=False, null=False, default=False, verbose_name=u"退職")
    retired_date = models.DateField(blank=True, null=True, verbose_name=u"退職年月日")
    id_from_api = models.CharField(blank=True, null=True, unique=True, max_length=30,
                                   verbose_name=u"社員ID", help_text=u"データを導入するために、API側のID")
    eboa_user_id = models.CharField(blank=True, null=True, max_length=14, unique=True)
    created_date = models.DateTimeField(null=True, auto_now_add=True, editable=False, verbose_name=u"作成日時")
    updated_date = models.DateTimeField(null=True, auto_now=True, editable=False, verbose_name=u"更新日時")

    class Meta:
        abstract = True

    def get_notify_mail_list(self):
        if self.notify_type == 1:
            if self.email:
                return [self.email]
        elif self.notify_type == 2:
            if self.private_email:
                return [self.private_email]
        elif self.notify_type == 3:
            if self.email and self.private_email:
                return [self.email, self.private_email]
            elif self.email:
                return [self.email]
            elif self.private_email:
                return [self.private_email]
        return []


class PublicManager(models.Manager):

    # use_for_related_fields = True

    def __init__(self, *args, **kwargs):
        super(PublicManager, self).__init__()
        self.args = args
        self.kwargs = kwargs

    def get_queryset(self):
        return super(PublicManager, self).get_queryset().filter(is_deleted=False)

    def public_all(self):
        return self.get_queryset().filter(*self.args, **self.kwargs)

    def public_filter(self, *args, **kwargs):
        return self.public_all().filter(*args, **kwargs)


class Config(models.Model):
    group = models.CharField(max_length=50, blank=False, null=True, verbose_name=u"グループ")
    name = models.CharField(max_length=50, unique=True, verbose_name=u"設定名")
    value = models.CharField(max_length=2000, verbose_name=u"設定値")
    description = models.TextField(blank=True, null=True, verbose_name=u"説明")

    class Meta:
        ordering = ['group', 'name']
        verbose_name = verbose_name_plural = u"設定"
        db_table = 'mst_config'

    def __unicode__(self):
        return self.name

    @classmethod
    def get(cls, config_name, default_value=None, group_name=None):
        """システム設定を取得する。

        DBから値を取得する。

        :param config_name: 設定名
        :param default_value: デフォルト値
        :param group_name: グループ名
        :return:
        """
        try:
            c = Config.objects.get(name=config_name)
            return c.value
        except ObjectDoesNotExist:
            if default_value is not None:
                c = Config(group=group_name, name=config_name, value=default_value)
                c.save()
            return default_value

    @classmethod
    def get_employment_period_comment(cls):
        """社員の雇用期間コメントを取得する。

        :return:
        """
        default = u"（期間満了の１ヶ月前までに双方にいずれからも別段の意志表示がないときは、" \
                  u"同一条件をもってさらに３ヶ月継続するものとし、その後も同じとする。） "
        return Config.get(constants.CONFIG_EMPLOYMENT_PERIOD_COMMENT, default,
                          group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_business_address(cls):
        """就業の場所

        :return:
        """
        default = u"就業の場所（当社社内および雇用者が指定した場所）"
        return Config.get(constants.CONFIG_BUSINESS_ADDRESS, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_business_time(cls):
        default = u"始業および終業時刻　午前　9時30分　～　午後　6時30分\n" \
                  u"休憩時間　　　　　　　正午～午後1時\n" \
                  u"就業時間の変更　　前記にかかわらず業務の都合または就業場所変更により\n" \
                  u"　　　　　　　　　　　　　始業および終業時刻の変更を行うことがある。\n" \
                  u"所定労働時間を越える労働の有無　有"
        return Config.get(constants.CONFIG_BUSINESS_TIME, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_business_other(cls):
        default = u"就業の場所および業務の種類は、業務の都合により変更することがある。\n" \
                  u"出向、転勤、配置転換等の業務命令が発令されることがある。"
        return Config.get(constants.CONFIG_BUSINESS_OTHER, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_allowance_date_comment(cls):
        """給与締め切り日及び支払日のコメントを取得する。

        :return:
        """
        default = u"1、締切日および支払日：毎月末日〆、翌月末日払\n" \
                  u"2、支払時の控除：所得税、雇用保険"
        return Config.get(constants.CONFIG_ALLOWANCE_DATE_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_allowance_change_comment(cls):
        """昇給及び降給のコメントを取得する。

        :return:
        """
        default = u"会社の業績および社員個人の業績その他の状況を勘案し、昇給または降給を行うことがある。"
        return Config.get(constants.CONFIG_ALLOWANCE_CHANGE_COMMENT, default,
                          group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_bonus_comment(cls):
        default = u"賞与支給要件を満たした者に対し、賞与が年2回、計2ヵ月分。\n" \
                  u"ただし会社業績、本人業績、勤怠状況および将来への期待度により、変更の可能性がある。"
        return Config.get(constants.CONFIG_BONUS_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_holiday_comment(cls):
        default = u"週休2日制（土・日・祝祭日休み）"
        return Config.get(constants.CONFIG_HOLIDAY_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_paid_vacation_comment(cls):
        default = u"年次有給休暇：労働基準法の定めによる。"
        return Config.get(constants.CONFIG_PAID_VACATION_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_no_paid_vacation_comment(cls):
        default = u"産前産後、育児・介護休業、生理休暇、その他就業規則に定めがあるときは当該休暇。"
        return Config.get(constants.CONFIG_NO_PAID_VACATION_COMMENT, default,
                          group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_retire_comment(cls):
        default = u"1、就業期間中、業務能力が著しく劣り、又は業務実績が著しく不良のとき、" \
                  u"会社の業務命令が従わないとき、減給、降職又は諭旨解雇とする。\n" \
                  u"2、自己都合退職の際は退職する30日前までに届け出ること。\n" \
                  u"3、解雇の事由および手続きは、就業規則の定めるところによる。"
        return Config.get(constants.CONFIG_RETIRE_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_contract_comment(cls):
        default = u"上記以外の雇用条件については、就業規則の定めることによる。"
        return Config.get(constants.CONFIG_CONTRACT_COMMENT, default, group_name=constants.CONFIG_GROUP_CONTRACT)

    @classmethod
    def get_bp_order_delivery_properties(cls):
        """ＢＰ注文書の納入物件

        :return:
        """
        return Config.get(constants.CONFIG_BP_ORDER_DELIVERY_PROPERTIES, '', group_name=constants.CONFIG_GROUP_BP_ORDER)

    @classmethod
    def get_bp_order_payment_condition(cls):
        """ＢＰ注文書の支払条件

        :return:
        """
        return Config.get(constants.CONFIG_BP_ORDER_PAYMENT_CONDITION, '', group_name=constants.CONFIG_GROUP_BP_ORDER)

    @classmethod
    def get_bp_order_contract_items(cls):
        """ＢＰ注文書の契約条項

        :return:
        """
        return Config.get(constants.CONFIG_BP_ORDER_CONTRACT_ITEMS, '', group_name=constants.CONFIG_GROUP_BP_ORDER)

    @classmethod
    def get_default_expenses_category(cls):
        """出勤情報アップロード時、客先立替金を精算リストに追加するために、既定の分類を取得する

        :return:
        """
        expenses_id = Config.get(constants.CONFIG_DEFAULT_EXPENSES_ID)
        if expenses_id:
            try:
                expenses = ExpensesCategory.objects.get(pk=expenses_id)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                expenses = None
            return expenses
        else:
            return None

    @classmethod
    def get_firebase_serverkey(cls):
        return Config.get(constants.CONFIG_FIREBASE_SERVERKEY, '', group_name=constants.CONFIG_GROUP_SYSTEM)

    @classmethod
    def get_gcm_url(cls):
        return Config.get(constants.CONFIG_GCM_URL, 'https://fcm.googleapis.com/fcm/send',
                          group_name=constants.CONFIG_GROUP_SYSTEM)

    @classmethod
    def get_bp_attendance_type(cls):
        return Config.get(constants.CONFIG_BP_ATTENDANCE_TYPE, '2', group_name=constants.CONFIG_GROUP_SYSTEM)

    @classmethod
    def get_year_list_start(cls):
        return Config.get(constants.CONFIG_YEAR_LIST_START, '2015', group_name=constants.CONFIG_GROUP_SYSTEM)

    @classmethod
    def get_year_list_end(cls):
        return Config.get(constants.CONFIG_YEAR_LIST_END, '2025', group_name=constants.CONFIG_GROUP_SYSTEM)

    @classmethod
    def get_domain_name(cls):
        return Config.get(constants.CONFIG_DOMAIN_NAME, '', group_name=constants.CONFIG_GROUP_SYSTEM)


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, auto_now=False, null=True, editable=False,
                                        verbose_name=u"作成日時")
    updated_date = models.DateTimeField(auto_now=True, null=True, editable=False, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class Company(AbstractCompany):
    payment_month = models.CharField(blank=True, null=True, max_length=1, default='1',
                                     choices=constants.CHOICE_PAYMENT_MONTH, verbose_name=u"支払いサイト",)
    payment_day = models.CharField(blank=True, null=True, max_length=2, default='99',
                                   choices=constants.CHOICE_PAYMENT_DAY, verbose_name=u"支払日")
    tax_rate = models.DecimalField(default=0.1, max_digits=3, decimal_places=2, choices=constants.CHOICE_TAX_RATE,
                                   verbose_name=u"税率")
    decimal_type = models.CharField(max_length=1, default='0', choices=constants.CHOICE_DECIMAL_TYPE,
                                    verbose_name=u"小数の処理区分")
    quotation_file = models.FileField(blank=True, null=True, upload_to="./quotation",
                                      verbose_name=u"見積書テンプレート")
    request_file = models.FileField(blank=True, null=True, upload_to="./request", verbose_name=u"請求書テンプレート")
    request_lump_file = models.FileField(blank=True, null=True, upload_to="./request",
                                         verbose_name=u"請求書テンプレート(一括)")
    pay_notify_file = models.FileField(blank=True, null=True, upload_to="./request",
                                       verbose_name=u"支払通知書テンプレート")
    order_file = models.FileField(blank=True, null=True, upload_to="./eb_order", verbose_name=u"註文書テンプレート",
                                  help_text=u"協力会社への註文書。")
    dispatch_file = models.FileField(blank=True, null=True, upload_to="./attachment", verbose_name=u"派遣社員一覧")
    created_dt = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        verbose_name = verbose_name_plural = u"会社"
        permissions = (
            ('view_member_status_list', u"社員稼働状況リスト"),
            ('view_batch', u"バッチ参照"),
            ('execute_batch', u"バッチ実行"),
        )

    @staticmethod
    def get_projects(status=0):
        """ステータスによって、該当する全ての案件を取得する。

        :param status:
        :return:
        """
        if status == 0:
            return Project.objects.public_all()
        else:
            return Project.objects.public_filter(status=status)

    def get_proposal_projects(self):
        """提案中の案件を取得する。

        Arguments：
          なし

        Returns：
          案件のリスト

        Raises：
          なし
        """
        return self.get_projects(1)

    def get_examination_projects(self):
        """予算審査中の案件を取得する。

        Arguments：
          なし

        Returns：
          案件のリスト

        Raises：
          なし
        """
        return self.get_projects(2)

    def get_confirmed_projects(self):
        """予算確定の案件を取得する。

        Arguments：
          なし

        Returns：
          案件のリスト

        Raises：
          なし
        """
        return self.get_projects(3)

    def get_working_projects(self):
        """実施中の案件を取得する。

        Arguments：
          なし

        Returns：
          案件のリスト

        Raises：
          なし
        """
        return self.get_projects(4)

    def get_finished_projects(self):
        """終了の案件を取得する。

        Arguments：
          なし

        Returns：
          案件のリスト

        Raises：
          なし
        """
        return self.get_projects(5)

    def get_pay_date(self, date=datetime.date.today()):
        """支払い期限日を取得する。

        :param date:
        :return:
        """
        months = int(self.payment_month) if self.payment_month else 1
        pay_month = common.add_months(date, months)
        if self.payment_day == '99' or not self.payment_day:
            return common.get_last_day_by_month(pay_month)
        else:
            pay_day = int(self.payment_day)
            last_day = common.get_last_day_by_month(pay_month)
            if last_day.day < pay_day:
                return last_day
            return datetime.date(pay_month.year, pay_month.month, pay_day)


class Bank(BaseModel):
    code = models.CharField(
        max_length=4, primary_key=True, validators=(RegexValidator(regex=r'[0-9]{4}'),), verbose_name=u"金融機関コード"
    )
    name = models.CharField(max_length=30, verbose_name=u"金融機関名称")
    kana = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=u"金融機関カナ",
        help_text=u"半角カナ文字及び英数字等、左詰め残りスペースとする。"
    )

    class Meta:
        ordering = ['code']
        verbose_name = u"金融機関"
        verbose_name_plural = u"金融機関一覧"

    def __unicode__(self):
        return self.name


class BankInfo(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, verbose_name=u"会社")
    bank = models.ForeignKey(Bank, blank=False, null=True, on_delete=models.PROTECT, verbose_name=u"銀行")
    bank_name = models.CharField(blank=False, null=False, max_length=20, verbose_name=u"銀行名称")
    branch_no = models.CharField(blank=False, null=False, max_length=3, verbose_name=u"支店番号")
    branch_name = models.CharField(blank=False, null=False, max_length=20, verbose_name=u"支店名称")
    branch_kana = models.CharField(max_length=40, blank=True, null=True, verbose_name=u"支店カナ",)
    account_type = models.CharField(blank=False, null=False, max_length=1, choices=constants.CHOICE_ACCOUNT_TYPE,
                                    verbose_name=u"預金種類")
    account_number = models.CharField(blank=False, null=False, max_length=7, verbose_name=u"口座番号")
    account_holder = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義")

    class Meta:
        unique_together = ('branch_no', 'account_number')
        verbose_name = verbose_name_plural = u"銀行口座"

    def __unicode__(self):
        return self.bank_name


class Subcontractor(AbstractCompany):
    employee_count = models.IntegerField(blank=True, null=True, verbose_name=u"従業員数")
    sale_amount = models.BigIntegerField(blank=True, null=True, verbose_name=u"売上高")
    payment_month = models.CharField(blank=True, null=True, max_length=1, default='1',
                                     choices=constants.CHOICE_PAYMENT_MONTH, verbose_name=u"支払いサイト")
    payment_day = models.CharField(blank=True, null=True, max_length=2, choices=constants.CHOICE_PAYMENT_DAY,
                                   default='99', verbose_name=u"支払日")
    middleman = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"連絡窓口担当者")
    comment = models.TextField(blank=True, null=True, verbose_name=u"備考")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False)

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"協力会社"
        permissions = (
            ('view_subcontractor', u'協力会社参照'),
        )

    def get_start_date(self):
        """
        協力社員のアサイン情報の一番古い日付を取得する。
        :return:
        """
        members = self.member_set.all()
        min_start_date = ProjectMember.objects.public_filter(member__in=members).aggregate(Min('start_date'))
        start_date = min_start_date.get('start_date__min')
        return start_date if start_date else datetime.date.today()

    def get_end_date(self):
        """
        協力社員のアサイン情報の一番最後日付を取得する。
        :return:
        """
        members = self.member_set.all()
        max_end_date = ProjectMember.objects.public_filter(member__in=members).aggregate(Max('end_date'))
        end_date = max_end_date.get('end_date__max')
        return end_date if end_date else datetime.date.today()

    def get_members_by_month(self, date):
        """
        指定月の協力社員情報を取得する
        :param date: 指定月
        :return:
        """
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(first_day)
        # members = self.member_set.filter(
        #     projectmember__start_date__lte=last_day,
        #     projectmember__end_date__gte=first_day
        # ).distinct()
        members = Member.objects.filter(
            Q(bpcontract__end_date__gte=first_day) | Q(bpcontract__end_date__isnull=True),
            bpcontract__start_date__lte=last_day,
            projectmember__start_date__lte=last_day,
            projectmember__end_date__gte=first_day,
            projectmember__is_deleted=False,
            bpcontract__company_id=self.pk,
        )
        return members

    def get_year_month_order_finished(self):
        """
        月単位の註文情報を取得する。
        :return:
        """
        ret_value = []
        for year, month in common.get_year_month_list(self.get_start_date(), self.get_end_date()):
            first_day = datetime.date(int(year), int(month), 1)
            subcontractor_order = None
            members = self.get_members_by_month(first_day)
            bp_members = BpMemberOrderInfo.objects.public_filter(member__in=members, year=year, month=month)
            if members.count() > 0 and members.count() == bp_members.count():
                is_finished = True
            else:
                is_finished = False
            ret_value.append((year, month, subcontractor_order, is_finished))
        return ret_value

    def get_request_sections(self, year, month):
        """協力会社の請求書は事業部単位で作成されているので、指定年月の各部署を取得する
        
        :param year: 
        :param month: 
        :return: 
        """
        first_day = datetime.date(int(year), int(month), 10)
        members = self.get_members_by_month(first_day)
        organizations = []
        ret_list = []
        for member in members:
            section = member.get_section(first_day)
            if section:
                division = section.get_root_section()
                if division not in organizations:
                    try:
                        subcontractor_request = SubcontractorRequest.objects.get(
                            subcontractor=self,
                            section=division,
                            year=year,
                            month=month
                        )
                    except (ObjectDoesNotExist, MultipleObjectsReturned):
                        subcontractor_request = None
                    organizations.append(division)
                    ret_list.append((division, subcontractor_request))
        # 一括請求書
        for department in self.get_lump_departments(first_day):
            division = department.get_root_section()
            if division and division.pk not in [org.pk for org, r in ret_list]:
                try:
                    subcontractor_request = SubcontractorRequest.objects.get(
                        subcontractor=self,
                        section=division,
                        year=year,
                        month=month
                    )
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    subcontractor_request = None
                organizations.append(division)
                ret_list.append((division, subcontractor_request))
        return ret_list

    def get_lump_departments(self, date):
        """一括案件の部署別リストを取得する。

        支払通知書と請求書を作成時一括案件も作成できるように。

        :param date:
        :return:
        """
        lump_contracts = self.get_lump_contracts(date.year, date.month)
        departments = lump_contracts.values('project__department').distinct()
        return Section.objects.public_filter(pk__in=departments)

    def get_lump_contracts(self, year, month):
        first_day = common.get_first_day_from_ym('%04d%02d' % (int(year), int(month)))
        last_day = common.get_last_day_by_month(first_day)
        lump_contracts = self.bplumpcontract_set.filter(
            start_date__lte=last_day,
            end_date__gte=first_day,
        ).exclude(status='04')
        return lump_contracts

    def get_members_by_month_and_section(self, year, month, section):
        """協力会社の請求書を作成時に、部署単位でメンバーを取得し、作成する。
        
        :param year: 
        :param month: 
        :param section: 
        :return: 
        """
        first_day = datetime.date(int(year), int(month), 20)
        members = self.get_members_by_month(first_day)
        section_pk_list = [s.pk for s in section.get_children()]
        section_pk_list.append(section.pk)
        ret_list = []
        for member in members:
            section = member.get_section(first_day)
            if section and section.pk in section_pk_list:
                ret_list.append(member)
        return ret_list

    def get_subcontractor_request(self, year, month, organization):
        """指定年月と事業部の請求書を取得する、存在しない場合は新規作成する。
        
        :param year: 
        :param month: 
        :param organization: 
        :return: 
        """
        organizations = organization.get_children()
        organizations.append(organization)
        request_list = SubcontractorRequest.objects.filter(
            subcontractor=self, year=year, month=month, section__in=organizations
        )
        if request_list.count() == 0:
            # 指定年月と事業部の請求書がない場合、請求番号を発行する。
            max_request_no = SubcontractorRequest.objects.filter(year=year, month=month).aggregate(Max('request_no'))
            request_no = max_request_no.get('request_no__max')
            if request_no and re.match(r"^([0-9]{7}|[0-9]{7}-[0-9]{3})$", request_no):
                no = request_no[4:7]
                no = "%03d" % (int(no) + 1,)
            else:
                no = "001"
            next_request = "%s%s%s" % (year[2:], month, no)
            next_pay_notify_no = "WT%s%s%s" % (year[2:], month, no)
            subcontractor_request = SubcontractorRequest(
                subcontractor=self, section=organization, year=year, month=month, request_no=next_request,
                pay_notify_no=next_pay_notify_no,
            )
            return subcontractor_request
        else:
            # 存在する場合、そのまま使う、再発行はしません。
            return request_list[0]

    def get_pay_notify_mail_list(self):
        """支払通知書と請求書をメール送信時、の宛先リストとＣＣリストを取得する。

        :return:
        """
        queryset = SubcontractorRequestRecipient.objects.public_filter(subcontractor=self)
        recipient_list = []
        cc_list = []
        for request_recipient in queryset.filter(is_cc=False):
            recipient_list.append(request_recipient.subcontractor_member.email)
        for request_cc in queryset.filter(is_cc=True):
            cc_list.append(request_cc.subcontractor_member.email)
        # EBのＣＣリストを取得する
        mail_group = MailGroup.get_subcontractor_pay_notify()
        cc_list.extend(mail_group.get_cc_list())
        return recipient_list, cc_list

    def get_member_order_mail_list(self):
        """支払通知書と請求書をメール送信時、の宛先リストとＣＣリストを取得する。

        :return:
        """
        queryset = SubcontractorOrderRecipient.objects.public_filter(subcontractor=self)
        recipient_list = []
        cc_list = []
        for request_recipient in queryset.filter(is_cc=False):
            recipient_list.append(request_recipient.subcontractor_member.email)
        for request_cc in queryset.filter(is_cc=True):
            cc_list.append(request_cc.subcontractor_member.email)
        # EBのＣＣリストを取得する
        mail_group = MailGroup.get_member_order()
        cc_list.extend(mail_group.get_cc_list())
        return recipient_list, cc_list

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()

    def get_pay_date(self, date=datetime.date.today()):
        """支払い期限日を取得する。

        :param date:
        :return:
        """
        months = int(self.payment_month) if self.payment_month else 1
        pay_month = common.add_months(date, months)
        if self.payment_day == '99' or not self.payment_day:
            return common.get_last_day_by_month(pay_month)
        else:
            pay_day = int(self.payment_day)
            last_day = common.get_last_day_by_month(pay_month)
            if last_day.day < pay_day:
                return last_day
            return datetime.date(pay_month.year, pay_month.month, pay_day)

class SubcontractorBankInfo(BaseModel):
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"協力会社")
    bank = models.ForeignKey(Bank, blank=False, null=True, on_delete=models.PROTECT, verbose_name=u"銀行")
    bank_code = models.CharField(blank=False, null=True, editable=False, max_length=4, verbose_name=u"銀行コード")
    bank_name = models.CharField(blank=False, null=False, editable=False, max_length=20, verbose_name=u"銀行名称")
    branch_kana = models.CharField(max_length=40, blank=True, null=True, verbose_name=u"支店カナ",)
    branch_no = models.CharField(blank=False, null=False, max_length=7, verbose_name=u"支店番号")
    branch_name = models.CharField(blank=False, null=False, max_length=20, verbose_name=u"支店名称")
    account_type = models.CharField(blank=False, null=False, max_length=1, choices=constants.CHOICE_ACCOUNT_TYPE,
                                    verbose_name=u"預金種類")
    account_number = models.CharField(blank=False, null=False, max_length=7, verbose_name=u"口座番号")
    account_holder = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義")

    class Meta:
        verbose_name = verbose_name_plural = u"協力会社銀行口座"

    def __unicode__(self):
        return self.bank_name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.bank_code = self.bank.code
        self.bank_name = self.bank.name
        super(SubcontractorBankInfo, self).save(force_insert, force_update, using, update_fields)


class SubcontractorMember(BaseModel):
    name = models.CharField(max_length=30, verbose_name=u"名前")
    email = models.EmailField(blank=False, null=True, verbose_name=u"メールアドレス")
    phone = models.CharField(blank=True, null=True, max_length=11, verbose_name=u"電話番号")
    member_type = models.CharField(max_length=2, choices=constants.CHOICE_CLIENT_MEMBER_TYPE, verbose_name=u"役割担当")
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"所属会社")

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"協力会社社員"

    def __unicode__(self):
        return "%s - %s" % (self.subcontractor.name, self.name)

    def delete(self, using=None, keep_parents=False):
        super(BaseModel, self).delete(using, keep_parents)


class SubcontractorRequestRecipient(BaseModel):
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"所属会社")
    subcontractor_member = models.ForeignKey(SubcontractorMember, on_delete=models.PROTECT, verbose_name=u"所属会社社員")
    is_cc = models.BooleanField(default=False, verbose_name=u"ＣＣに入れて送信")

    class Meta:
        ordering = ['subcontractor', 'subcontractor_member']
        verbose_name = u"支払通知書の宛先"
        verbose_name_plural = u"支払通知書の宛先一覧"

    def __unicode__(self):
        return unicode(self.subcontractor_member)

    def delete(self, using=None, keep_parents=False):
        super(BaseModel, self).delete(using, keep_parents)


class SubcontractorOrderRecipient(BaseModel):
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"所属会社")
    subcontractor_member = models.ForeignKey(SubcontractorMember, on_delete=models.PROTECT, verbose_name=u"所属会社社員")
    is_cc = models.BooleanField(default=False, verbose_name=u"ＣＣに入れて送信")

    class Meta:
        ordering = ['subcontractor', 'subcontractor_member']
        unique_together = ('subcontractor', 'subcontractor_member')
        verbose_name = u"ＢＰ注文書の宛先"
        verbose_name_plural = u"ＢＰ注文書の宛先一覧"

    def __unicode__(self):
        return unicode(self.subcontractor_member)

    def delete(self, using=None, keep_parents=False):
        super(BaseModel, self).delete(using, keep_parents)


class MailTemplate(BaseModel):
    mail_title = models.CharField(max_length=100, unique=True, verbose_name=u"送信メールのタイトル")
    mail_body = models.TextField(blank=True, null=True, verbose_name=u"メール本文(Plain Text)")
    mail_html = models.TextField(blank=True, null=True, verbose_name=u"メール本文(HTML)")
    pass_title = models.CharField(
        max_length=50, blank=True, null=True, editable=False, verbose_name=u"パスワード通知メールの題名",
        help_text=u'設定してない場合は「送信メールのタイトル」を使う。'
    )
    pass_body = models.TextField(blank=True, null=True, verbose_name=u"パスワードお知らせ本文(Plain Text)")
    attachment1 = models.FileField(blank=True, null=True, upload_to="./attachment", verbose_name=u"添付ファイル１",
                                   help_text=u"メール送信時の添付ファイルその１。")
    attachment2 = models.FileField(blank=True, null=True, upload_to="./attachment", verbose_name=u"添付ファイル２",
                                   help_text=u"メール送信時の添付ファイルその２。")
    attachment3 = models.FileField(blank=True, null=True, upload_to="./attachment", verbose_name=u"添付ファイル３",
                                   help_text=u"メール送信時の添付ファイルその３。")
    description = models.TextField(blank=True, null=True, verbose_name=u"説明")

    class Meta:
        ordering = ['mail_title']
        verbose_name = verbose_name_plural = u"メールテンプレート"

    def __unicode__(self):
        return self.mail_title


class MailGroup(BaseModel):
    code = models.CharField(
        max_length=4, choices=constants.CHOICE_MAIL_GROUP, default='0000', editable=False, verbose_name=u"コード"
    )
    name = models.CharField(max_length=30, blank=False, null=True, verbose_name=u"名称")
    title = models.CharField(max_length=50, blank=False, null=True, verbose_name=u"タイトル")
    mail_sender = models.EmailField(blank=True, null=True, verbose_name=u"メール差出人")
    sender_display_name = models.CharField(max_length=50, blank=True, null=True, editable=False, verbose_name=u"差出人表示名")
    mail_template = models.ForeignKey(MailTemplate, blank=True, null=True, on_delete=models.PROTECT,
                                      verbose_name=u"メールテンプレート")
    footer = models.ForeignKey(
        MailTemplate, blank=True, null=True, on_delete=models.PROTECT, related_name='tail_group_set',
        verbose_name=u"フッター", editable=False
    )

    class Meta:
        ordering = ['title']
        verbose_name = verbose_name_plural = u"メールグループ"

    def __unicode__(self):
        return self.name

    def get_mail_title(self, **kwargs):
        if self.mail_template and self.mail_template.mail_title:
            return self.mail_template.mail_title.replace('{{', '{').replace('}}', '}').format(**kwargs)
        else:
            return None

    def get_mail_body(self, **kwargs):
        if self.mail_template:
            mail_body = self.mail_template.mail_body or self.mail_template.mail_html
            t = Template(mail_body)
            ctx = Context(kwargs)
            body = t.render(ctx)
            return body
        else:
            return None

    def get_pass_body(self, **kwargs):
        if self.mail_template and self.mail_template.pass_body:
            pass_body = self.mail_template.pass_body
            t = Template(pass_body)
            ctx = Context(kwargs)
            body = t.render(ctx)
            return body
        else:
            return None

    def get_cc_list(self):
        carbon_copies = self.mailcclist_set.public_all()
        cc_list = []
        for cc in carbon_copies:
            if cc.member and cc.member.email:
                cc_list.append(cc.member.email)
            if cc.email:
                cc_list.append(cc.email)
        return cc_list

    @classmethod
    def get_subcontractor_pay_notify(cls):
        try:
            return MailGroup.objects.get(name=constants.MAIL_GROUP_SUBCONTRACTOR_PAY_NOTIFY)
        except ObjectDoesNotExist:
            mail_group = MailGroup(name=constants.MAIL_GROUP_SUBCONTRACTOR_PAY_NOTIFY)
            mail_group.save()
            return mail_group

    @classmethod
    def get_member_order(cls):
        try:
            return MailGroup.objects.get(name=constants.MAIL_GROUP_MEMBER_ORDER)
        except ObjectDoesNotExist:
            mail_group = MailGroup(name=constants.MAIL_GROUP_MEMBER_ORDER)
            mail_group.save()
            return mail_group


class MailCcList(BaseModel):
    group = models.ForeignKey(MailGroup, on_delete=models.PROTECT, verbose_name=u"メールグループ")
    member = models.ForeignKey('Member', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"ＣＣ先の社員")
    email = models.EmailField(blank=True, null=True, verbose_name=u"メールアドレス")
    is_bcc = models.BooleanField(default=False, editable=False, verbose_name=u"ＢＣＣ")

    class Meta:
        ordering = ['group']
        verbose_name = verbose_name_plural = u"メールＣＣリスト"

    def __unicode__(self):
        if self.member:
            return unicode(self.member)
        else:
            return self.email or ''


class Section(BaseModel):
    name = models.CharField(blank=False, null=False, max_length=30, verbose_name=u"部署名")
    description = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"概要")
    is_on_sales = models.BooleanField(default=False, verbose_name=u"営業対象")
    is_active = models.BooleanField(default=False, verbose_name=u"社員に表示")
    parent = models.ForeignKey("self", related_name='children', blank=True, null=True, on_delete=models.PROTECT,
                               verbose_name=u"親組織")
    org_type = models.CharField(blank=False, null=False, max_length=2, choices=constants.CHOICE_ORG_TYPE,
                                verbose_name=u"組織類別")
    company = models.ForeignKey(Company, blank=False, null=False, on_delete=models.PROTECT, verbose_name=u"会社")

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"部署"
        permissions = (
            ('view_section', u'部署参照'),
        )

    def __unicode__(self):
        return self.name

    def get_attendance_amount(self, ym):
        """対象年月の出勤売上を取得する。

        :param ym: 対象年月
        :return:
        """
        amount = MemberAttendance.objects.public_filter(year=ym[:4], month=ym[4:],
                                                        project_member__member__section=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def get_expenses_amount(self, ym):
        amount = MemberExpenses.objects.public_filter(year=ym[:4], month=ym[4:],
                                                      project_member__member__section=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def get_cost_amount(self, ym):
        pass

    def get_chief(self):
        """部門長、課長を取得する

        :return:
        """
        query_set = Member.objects.public_filter(
            positionship__section=self,
            positionship__position__in=[3, 3.1, 4, 6],
            positionship__is_deleted=False,
        )
        return query_set

    def get_chief2(self):
        """担当部長、担当課長を取得する

        :return:
        """
        query_set = Member.objects.public_filter(
            positionship__section=self,
            positionship__position__in=[5, 7],
            positionship__is_deleted=False,
        )
        return query_set

    def get_attendance_statistician(self):
        """勤務情報の統計者を取得する。

        :return:
        """
        query_set = Member.objects.public_filter(positionship__section=self,
                                                 positionship__position=11)
        return query_set

    def get_child_section(self):
        return self.children.filter(is_on_sales=True)

    def get_children(self):
        children = []
        for org in self.children.filter(is_deleted=False):
            children.append(org)
            children.extend(list(org.get_children()))
        return children

    def get_root_section(self):
        """事業部を取得する。
        
        :return: 
        """
        if self.parent:
            return self.parent.get_root_section()
        else:
            return self

    def get_members_period(self):
        """当該部署に所属メンバーを取得する、子部署も含む。

        :return:
        """
        today = timezone.now().date()
        all_children = self.get_children()
        org_pk_list = [org.pk for org in all_children]
        org_pk_list.append(self.pk)
        projectmember_set = ProjectMember.objects.filter(start_date__lte=today,
                                                         end_date__gte=today)
        org_period_list = MemberSectionPeriod.objects.filter(
            Q(division__in=org_pk_list) |
            Q(section__in=org_pk_list) |
            Q(subsection__in=org_pk_list),
            Q(end_date__gte=today) | Q(end_date__isnull=True),
            start_date__lte=today,
            member__is_retired=False,
            member__is_deleted=False
        ).select_related('member').prefetch_related(
            Prefetch('member__projectmember_set', queryset=projectmember_set, to_attr='current_projectmember_set'),
        )
        return org_period_list


class SalesOffReason(BaseModel):
    name = models.CharField(blank=False, null=False, max_length=50, verbose_name=u"理由")

    class Meta:
        verbose_name = verbose_name_plural = u"営業対象外理由"
        db_table = 'mst_salesofreason'

    def __unicode__(self):
        return self.name


class Salesperson(AbstractMember):
    employee_id = models.CharField(null=True, max_length=30, verbose_name=u"社員ID")
    first_name = models.CharField(null=True, max_length=30, verbose_name=u"姓")
    last_name = models.CharField(null=True, max_length=30, verbose_name=u"名")
    member = models.OneToOneField('Member', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u'社員')
    name = models.CharField(max_length=30, null=True, verbose_name=u"名前")
    email = models.EmailField(blank=False, null=True, verbose_name=u"メールアドレス")
    section = models.ForeignKey('Section', blank=False, null=True, on_delete=models.PROTECT, verbose_name=u"部署")
    member_type = models.IntegerField(default=5, choices=constants.CHOICE_SALESPERSON_TYPE, verbose_name=u"社員区分")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")
    user = models.OneToOneField(User, blank=True, null=True)

    objects = PublicManager(is_deleted=False, is_retired=False, section__is_deleted=False)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = verbose_name_plural = u"営業員"

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

    def get_on_sales_members(self):
        """該当営業員の営業対象のメンバーを取得する

        :return: MemberのQueryset
        """
        today = datetime.date.today()
        members = get_on_sales_members().filter((Q(membersalespersonperiod__start_date__lte=today) &
                                                 Q(membersalespersonperiod__end_date__isnull=True)) |
                                                (Q(membersalespersonperiod__start_date__lte=today) &
                                                 Q(membersalespersonperiod__end_date__gte=today)),
                                                membersalespersonperiod__is_deleted=False,
                                                membersalespersonperiod__salesperson=self)
        return members

    def get_off_sales_members(self):
        """該当営業員の営業対象のメンバーを取得する

        :return: MemberのQueryset
        """
        today = datetime.date.today()
        members = get_off_sales_members().filter((Q(membersalespersonperiod__start_date__lte=today) &
                                                  Q(membersalespersonperiod__end_date__isnull=True)) |
                                                 (Q(membersalespersonperiod__start_date__lte=today) &
                                                  Q(membersalespersonperiod__end_date__gte=today)),
                                                 membersalespersonperiod__is_deleted=False,
                                                 membersalespersonperiod__salesperson=self)
        return members

    def get_working_members(self):
        """現在稼働中のメンバーを取得する

        :return: MemberのQueryset
        """
        today = datetime.date.today()
        members = get_working_members().filter((Q(membersalespersonperiod__start_date__lte=today) &
                                                Q(membersalespersonperiod__end_date__isnull=True)) |
                                               (Q(membersalespersonperiod__start_date__lte=today) &
                                                Q(membersalespersonperiod__end_date__gte=today)),
                                               membersalespersonperiod__is_deleted=False,
                                               membersalespersonperiod__salesperson=self)
        return members

    def get_waiting_members(self):
        """現在待機中のメンバーを取得する

        :return: MemberのQueryset
        """
        today = datetime.date.today()
        members = get_waiting_members().filter((Q(membersalespersonperiod__start_date__lte=today) &
                                                Q(membersalespersonperiod__end_date__isnull=True)) |
                                               (Q(membersalespersonperiod__start_date__lte=today) &
                                                Q(membersalespersonperiod__end_date__gte=today)),
                                               membersalespersonperiod__is_deleted=False,
                                               membersalespersonperiod__salesperson=self)
        return members

    def get_release_current_month(self):
        """今月にリリースするメンバーを取得する

        :return: ProjectMemberのQueryset
        """
        today = datetime.date.today()
        project_members = get_release_current_month()
        query_set = project_members.filter((Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__isnull=True)) |
                                           (Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__gte=today)),
                                           member__membersalespersonperiod__is_deleted=False,
                                           member__membersalespersonperiod__salesperson=self)
        return query_set

    def get_release_next_month(self):
        """来月にリリースするメンバーを取得する

        :return: ProjectMemberのQueryset
        """
        today = datetime.date.today()
        project_members = get_release_next_month()
        query_set = project_members.filter((Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__isnull=True)) |
                                           (Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__gte=today)),
                                           member__membersalespersonperiod__is_deleted=False,
                                           member__membersalespersonperiod__salesperson=self)
        return query_set

    def get_release_next_2_month(self):
        """再来月にリリースするメンバーを取得する

        :return: ProjectMemberのQueryset
        """
        today = datetime.date.today()
        project_members = get_release_next_2_month()
        query_set = project_members.filter((Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__isnull=True)) |
                                           (Q(member__membersalespersonperiod__start_date__lte=today) &
                                            Q(member__membersalespersonperiod__end_date__gte=today)),
                                           member__membersalespersonperiod__is_deleted=False,
                                           member__membersalespersonperiod__salesperson=self)
        return query_set

    def get_warning_projects(self):
        if self.pk == 36:
            return Salesperson.objects.get(pk=16).get_warning_projects()
        today = datetime.date.today()
        query_set = self.project_set.filter(status=4).extra(select={
            'num_working': "select count(*) "
                           "  from eb_projectmember pm "
                           " where pm.project_id = eb_project.id "
                           "   and pm.start_date <= '%s' "
                           "   and pm.end_date >= '%s' " % (today, today)
        })
        return query_set

    def get_under_salesperson(self):
        """部下の営業員を取得する、部下がない場合自分を返す。
        """
        if self.member_type == 0 and self.section:
            return self.section.salesperson_set.public_all()
        else:
            return [self]

    def get_attendance_amount(self, ym):
        """対象年月の出勤売上を取得する。

        :param ym: 対象年月
        :return:
        """
        amount = MemberAttendance.objects.public_filter(year=ym[:4], month=ym[4:],
                                                        project_member__member__salesperson=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def get_expenses_amount(self, ym):
        amount = MemberExpenses.objects.public_filter(year=ym[:4], month=ym[4:],
                                                      project_member__member__salesperson=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.name = u"%s %s" % (self.first_name, self.last_name)
        super(Salesperson, self).save(force_insert, force_update, using, update_fields)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class Member(AbstractMember):
    user = models.OneToOneField(User, blank=True, null=True)
    common_first_name = models.CharField(
        blank=True, null=True, max_length=30, verbose_name=u"通称名（姓）"
    )
    common_last_name = models.CharField(
        blank=True, null=True, max_length=30, verbose_name=u"通称名（名）"
    )
    common_first_name_ja = models.CharField(
        blank=True, null=True, max_length=30, verbose_name=u"通称名（姓）(カナ)"
    )
    common_last_name_ja = models.CharField(
        blank=True, null=True, max_length=30, verbose_name=u"通称名（名）(カナ)"
    )
    oa_user_id = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"ＯＡのユーザーＩＤ")
    member_type = models.IntegerField(default=0, choices=constants.CHOICE_MEMBER_TYPE, verbose_name=u"社員区分")
    section = models.ForeignKey('Section', blank=True, null=True, verbose_name=u"部署", on_delete=models.PROTECT,
                                help_text=u"開発メンバーなど営業必要な方はしたの「社員の部署期間」のほうで設定してください、"
                                          u"ここで設定できるのは管理部、総務部などの営業対象外のかたです。")
    ranking = models.CharField(blank=True, null=True, max_length=2, choices=constants.CHOICE_MEMBER_RANK,
                               verbose_name=u"ランク")
    is_individual_pay = models.BooleanField(default=False, verbose_name=u"個別精算")
    subcontractor = models.ForeignKey(Subcontractor, blank=True, null=True, on_delete=models.PROTECT,
                                      verbose_name=u"協力会社")
    is_on_sales = models.BooleanField(blank=False, null=False, default=True, verbose_name=u"営業対象")
    is_unofficial = models.BooleanField(default=False, verbose_name=u"内定")
    sales_off_reason = models.ForeignKey(SalesOffReason, blank=True, null=True, on_delete=models.PROTECT,
                                         verbose_name=u"営業対象外理由")
    cost = models.IntegerField(null=False, default=0, verbose_name=u"コスト")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")
    id_number = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"在留カード番号")
    id_card_expired_date = models.DateField(blank=True, null=True, verbose_name=u"在留カード期限")
    visa_start_date = models.DateField(blank=True, null=True, verbose_name=u"ビザ有効期限（開始）")
    visa_expire_date = models.DateField(blank=True, null=True, verbose_name=u"ビザ有効期限（終了）")
    passport_number = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"パスポート番号")
    passport_expired_dt = models.DateField(blank=True, null=True, verbose_name=u"パスポート有効期限")
    residence_type = models.CharField(blank=True, null=True, max_length=20, choices=constants.CHOICE_RESIDENCE_TYPE, verbose_name=u"在留種類")
    pay_bank = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行名")
    pay_bank_code = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行コード")
    pay_branch = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行支店名")
    pay_branch_code = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行支店コード")
    pay_owner = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義")
    pay_owner_kana = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義（カナ）")
    pay_account = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座番号")
    avatar_url = models.CharField(blank=True, null=True, max_length=500, verbose_name=u"自分の写真")
    personal_number = models.CharField(max_length=12, blank=True, null=True, verbose_name=u"個人番号")
    basic_pension_no = models.CharField(max_length=10, blank=True, null=True, verbose_name=u"基礎年金番号")
    employment_insurance_no = models.CharField(max_length=11, blank=True, null=True, verbose_name=u"雇用保険証被保険者番号")
    emergency_post_code = models.CharField(
        blank=True, null=True, max_length=7, verbose_name=u"緊急連絡先郵便番号",
        help_text=u"数値だけを入力してください、例：1230034"
    )
    emergency_address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"緊急連絡先住所１")
    emergency_address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"緊急連絡先住所２")
    emergency_name = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"緊急連絡先氏名")
    emergency_phone = models.CharField(blank=True, null=True, max_length=11, verbose_name=u"緊急連絡先電話番号")
    emergency_relationship = models.CharField(blank=True, null=True, max_length=10, verbose_name=u"緊急連絡先との関係")

    objects = PublicManager(is_deleted=False, is_retired=False)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = verbose_name_plural = u"社員"
        permissions = (
            ('view_member', u'社員参照'),
            ('view_member_cost', u"社員コスト参照"),
            ('view_bp_cost', u"ＢＰコスト参照"),
        )

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

    def is_deletable(self):
        # get all the related object
        for rel in self._meta.get_fields():
            try:
                # check if there is a relationship with at least one related object
                related = rel.related_model.objects.filter(**{rel.field.name: self})
                if related.exists():
                    # if there is return a Tuple of flag = False the related_model object
                    return False, related
            except AttributeError:  # an attribute error for field occurs when checking for AutoField
                pass  # just pass as we dont need to check for AutoField
        return True, None

    def get_resume_name(self):
        """履歴書の氏名を取得する。

        :return: 名(ローマ字)が定義すれば、その頭文字を取得し、姓と一緒に返す。
        """
        if self.last_name_en:
            if isinstance(self.last_name_en, unicode):
                lst = re.findall(r"[A-Z]", self.last_name_en)
            else:
                lst = re.findall(r"[A-Z]", str(self.last_name_en))
            last_name = "".join(lst)
        else:
            last_name = self.last_name
        return u"%s %s" % (self.first_name, last_name)

    def get_age(self):
        birthday = self.birthday
        if birthday:
            today = datetime.date.today()
            years = today.year - birthday.year
            if today.month < birthday.month:
                years -= 1
            elif today.month == birthday.month:
                if today.day <= birthday.day:
                    years -= 1
            return years
        else:
            return None

    def get_section(self, date=None):
        """部署を取得する。

        :param date:
        :return:
        """
        if not date:
            first_day = last_day = datetime.date.today()
        else:
            first_day = common.get_first_day_by_month(date)
            last_day = common.get_last_day_by_month(date)
        results = self.membersectionperiod_set.filter((Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
                                                      (Q(start_date__lte=last_day) & Q(end_date__gte=first_day)))
        if results.count() > 0:
            return results[0].subsection or results[0].section or results[0].division
        return self.section

    def get_salesperson(self, date=None):
        """営業員を取得する。

        :param date:
        :return:
        """
        if not date:
            date = datetime.date.today()
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(date)
        results = self.membersalespersonperiod_set.filter(
            (Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
            (Q(start_date__lte=last_day) & Q(end_date__gte=first_day)),
            is_deleted=False
        ).first()
        if results:
            return results.salesperson
        else:
            return None

    def get_current_project_member(self):
        """現在実施中の案件アサイン情報を取得する
        """
        now = datetime.datetime.now()
        queryset = self.projectmember_set.public_filter(end_date__gte=now, start_date__lte=now,
                                                        status=2, is_deleted=False)
        return queryset.first()

    def get_current_end_project_member(self):
        """今月リリースのアサイン情報を取得する。

        :return:
        """
        first_day = common.get_first_day_current_month()
        last_day = common.get_last_day_by_month(first_day)
        project_members = self.projectmember_set.public_filter(end_date__gte=first_day,
                                                               end_date__lte=last_day,
                                                               status=2,
                                                               is_deleted=False)
        return project_members[0] if project_members.count() > 0 else None

    def get_next_start_project_member(self):
        """来月からのアサイン情報を取得する。

        :return:
        """
        next_month = common.add_months(datetime.date.today(), 1)
        first_day = common.get_first_day_by_month(next_month)
        last_day = common.get_last_day_by_month(first_day)
        project_members = self.projectmember_set.public_filter(start_date__gte=first_day,
                                                               start_date__lte=last_day,
                                                               status=2,
                                                               is_deleted=False)
        return project_members[0] if project_members.count() > 0 else None

    def get_project_end_date(self):
        # 稼働状態を取得する（待機・稼働中）
        if self.pk == 787:
            pass
        now = datetime.datetime.now()
        projects = self.projectmember_set.public_filter(end_date__gte=now, start_date__lte=now,
                                                        status=2, is_deleted=False)
        if projects.count() > 0:
            return projects[0].end_date
        else:
            return None

    def get_business_status(self):
        """営業状態を取得する

        planning_countとlast_end_dateはget_sales_membersにより取得されている

        :return:
        """
        next_2_month = common.add_months(datetime.date.today(), 2)
        if hasattr(self, 'planning_count'):
            if self.planning_count > 0:
                return u"営業中"
            if self.last_end_date and self.last_end_date >= next_2_month:
                return u"-"
            else:
                return u"未提案"
        else:
            return u"-"

    def get_skill_list(self):
        query_set = Member.objects.raw(u"SELECT DISTINCT S.*"
                                       u"  FROM eb_member M"
                                       u"  JOIN eb_projectmember PM ON M.ID = PM.MEMBER_ID"
                                       u"  JOIN eb_project P ON P.ID = PM.PROJECT_ID"
                                       u"  JOIN eb_projectskill PS ON PS.PROJECT_ID = P.ID"
                                       u"  JOIN mst_skill S ON S.ID = PS.SKILL_ID"
                                       u" WHERE M.EMPLOYEE_ID = %s"
                                       u"   AND PM.END_DATE <= %s", [self.employee_id, datetime.date.today()])
        return list(query_set)

    def get_recommended_projects(self):
        skill_list = self.get_skill_list()
        skill_id_list = [str(skill.pk) for skill in skill_list]
        if not skill_id_list:
            return []
        query_set = Member.objects.raw(u"SELECT DISTINCT P.*"
                                       u"  FROM eb_member M"
                                       u"  JOIN eb_projectmember PM ON M.ID = PM.MEMBER_ID"
                                       u"  JOIN eb_project P ON P.ID = PM.PROJECT_ID"
                                       u"  JOIN eb_projectskill PS ON PS.PROJECT_ID = P.ID"
                                       u"  JOIN mst_skill S ON S.ID = PS.SKILL_ID"
                                       u" WHERE S.ID IN (%s)"
                                       u"   AND P.STATUS <= 3" % (",".join(skill_id_list),))
        return [project.pk for project in query_set]

    def get_project_role_list(self):
        """かつてのプロジェクト中の役割担当を取得する。。

        Arguments：
          なし

        Returns：
          役割担当のリスト

        Raises：
          なし
        """
        project_member_list = self.projectmember_set.public_all()
        role_list = []
        for project_member in project_member_list:
            role = project_member.get_role_display().split(u"：")[0]
            if role not in role_list:
                role_list.append(role)
        return role_list

    def get_position_ship(self, is_min=False):
        """該当メンバーの職位を取得する

        :param is_min:
        :return:
        """
        if is_min:
            positions = self.positionship_set.public_filter(is_part_time=False).order_by('-position')
        else:
            positions = self.positionship_set.public_filter(is_part_time=False)
        if positions.count() > 0:
            return positions[0]
        else:
            return None

    def set_coordinate(self):
        if self.address1 and not self.lat and not self.lng:
            address = self.address1
            if self.address2:
                address += self.address2
            try:
                response = urllib2.urlopen("http://www.geocoding.jp/api/?q={0}".format(address.encode("utf8")))
                xml = response.read()
                tree = ElementTree.XML(xml)
                lat = tree.find(".//coordinate/lat")
                lng = tree.find(".//coordinate/lng")
                if lat is not None and lng is not None:
                    self.lat = lat.text
                    self.lng = lng.text
                    self.save()
                    return True
                else:
                    return False
            except Exception as e:
                logger = logging.getLogger(constants.LOG_EB_SALES)
                logger.error(e.message)
                logger.error(traceback.format_exc())
                return False
        return False

    def get_bp_member_info(self, date):
        """
        他者技術者の場合、注文の詳細情報を取得する。
        :param date 対象年月
        :return:
        """
        members = self.bpmemberorderinfo_set.filter(year=str(date.year), month="%02d" % (date.month,))
        if members.count() > 0:
            return members[0]
        else:
            return None

    def get_project_by_month(self, year, month):
        ym = '%s%02d' % (year, int(month))
        first_day = common.get_first_day_from_ym(ym)
        last_day = common.get_last_day_by_month(first_day)
        project_member_set = self.projectmember_set.public_filter(start_date__lte=last_day, 
                                                                  end_date__gte=first_day,
                                                                  is_deleted=False)
        if project_member_set.count() > 0:
            return project_member_set[0].project
        else:
            return None

    def get_cost(self, date):
        """コストを取得する

        :return:
        """
        contract = self.get_contract(date)
        if contract:
            return contract.get_cost()
        else:
            return 0

    def get_latest_contract(self):
        """最新の契約情報を取得する

        :return:
        """
        today = datetime.date.today()
        return self.get_contract(today)

    def get_current_contract(self):
        return self.get_contract(datetime.date.today())

    def get_contract(self, date):
        """指定日付の契約情報を取得する。

        契約情報のビューから取得する。

        :param date 対象年月
        :return:
        """
        contract = None
        last_day = common.get_last_day_by_month(date)
        contract_list = self.contract_set.filter(
            employment_date__lte=last_day
        ).exclude(status='04').order_by('-employment_date', '-contract_no')
        bp_contract_list = self.bpcontract_set.filter(
            start_date__lte=last_day,
            is_deleted=False,
        ).order_by('-start_date')
        if bp_contract_list.count() > 0:
            contract = bp_contract_list[0]
        else:
            if contract_list.count() > 0:
                contract = contract_list[0]
        return contract

    def is_belong_to(self, user, date):
        if user.is_superuser:
            return True
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(date)
        if user.has_perm('eb.edit_price'):
            return True
        elif hasattr(user, 'member'):
            with connection.cursor() as cursor:
                cursor.execute("select distinct boss.id boss_id"
                               "     , ps.position"
                               "  from eb_positionship ps"
                               "  join eb_membersectionperiod msp on (   msp.section_id = ps.section_id "
                               "                                      or msp.division_id = ps.section_id"
                               "                                      or msp.subsection_id = ps.section_id)"
                               "  join eb_member m on m.id = msp.member_id"
                               "  join eb_member boss on boss.id = ps.member_id"
                               " where m.is_deleted = 0"
                               "   and ps.is_deleted = 0"
                               "   and msp.is_deleted = 0"
                               "   and msp.start_date <= %s"
                               "   and (msp.end_date >= %s or msp.end_date is null)"
                               "   and ps.position in (3, 3.1, 4, 5, 6, 7)"
                               "   and m.id = %s"
                               "   and boss.id = %s", [last_day, first_day, self.pk, user.member.pk])
                records = cursor.fetchall()
            if len(records) > 0:
                return True
            else:
                return False
        elif hasattr(user, 'salesperson'):
            # 営業員ログインの場合
            with connection.cursor() as cursor:
                cursor.execute("select count(*)"
                               "  from eb_member m"
                               "  join eb_membersalespersonperiod msp on msp.member_id = m.id"
                               "								     and msp.start_date <= %s"
                               "								     and (msp.end_date >= %s or msp.end_date is null)"
                               "								     and msp.is_deleted = 0"
                               "  join eb_salesperson s on s.id = %s"
                               "                       and s.is_deleted = 0"
                               "  left join eb_membersectionperiod msp2 on msp2.member_id = m.id"
                               "									   and msp2.start_date <= %s"
                               "									   and (msp2.end_date >= %s or msp2.end_date is null)"
                               "									   and msp2.is_deleted = 0"
                               " where m.is_deleted = 0"
                               "   and m.id = %s"
                               "   and (   msp2.division_id = s.section_id"
                               "        or msp2.section_id = s.section_id"
                               "        or msp2.subsection_id = s.section_id"
                               "	   )", [last_day, first_day, user.salesperson.pk, last_day, first_day, self.pk])
                records = cursor.fetchall()
            if records[0][0] > 0:
                return True
            elif user.pk == 7:
                return True
            else:
                return False
        else:
            return False

    @classmethod
    def get_max_api_id(cls):
        with connection.cursor() as cursor:
            cursor.execute('select max(id_from_api) from eb_member')
            records = cursor.fetchall()
        if len(records) > 0 and records[0][0]:
            return "%04d" % (int(records[0][0]) + 1)
        else:
            return "0001"

    @cached_property
    def get_health_insurance(self):
        today = datetime.date.today()
        try:
            member = VMemberInsurance.objects.get(member=self, year=today.strftime('%Y'), month=today.strftime('%m'))
            decimal_part, int_part = math.modf(member.health_insurance)
            if decimal_part > 0.5:
                return int(int_part) + 1
            else:
                return int(int_part)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return 0

    @cached_property
    def traffic_cost(self):
        date = datetime.date.today()
        queryset = MemberAttendance.objects.public_filter(
            project_member__in=self.projectmember_set.filter(status=2, is_deleted=False),
        )
        attendance = queryset.filter(year=date.strftime('%Y'), month=date.strftime('%m')).first()
        if attendance:
            cost = attendance.traffic_cost
        else:
            date = common.add_months(date, -1)
            attendance = queryset.filter(year=date.strftime('%Y'), month=date.strftime('%m')).first()
            cost = attendance.traffic_cost if attendance else 0
        return cost or 0

    @cached_property
    def employment_insurance(self):
        date = datetime.date.today()
        queryset = MemberAttendance.objects.public_filter(
            project_member__in=self.projectmember_set.filter(status=2, is_deleted=False),
        )
        attendance = queryset.filter(year=date.strftime('%Y'), month=date.strftime('%m')).first()
        if attendance:
            cost = attendance.get_employment_insurance()
        else:
            date = common.add_months(date, -1)
            attendance = queryset.filter(year=date.strftime('%Y'), month=date.strftime('%m')).first()
            cost = attendance.get_employment_insurance() if attendance else 0
        return cost or 0

    def get_sales_off_reason(self):
        today = datetime.date.today()
        queryset = MemberSalesOffPeriod.objects.filter(
            (Q(start_date__lte=today) & Q(end_date__isnull=True)) |
            (Q(start_date__lte=today) & Q(end_date__gte=today)),
            member=self,
        )
        sales_off_period = queryset.first()
        return sales_off_period.sales_off_reason if sales_off_period else None

    def get_all_cost(self):
        today = datetime.date.today()
        return self.get_cost(today) + self.get_health_insurance + self.traffic_cost + self.employment_insurance

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class VMemberInsurance(models.Model):
    ym = models.CharField(max_length=6)
    year = models.CharField(max_length=4)
    month = models.CharField(max_length=2)
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=50)
    birthday = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    salary = models.IntegerField(blank=True, null=True)
    health_insurance = models.DecimalField(max_digits=10, decimal_places=1)

    class Meta:
        managed = False
        verbose_name = verbose_name_plural = "被保険者保険料"
        db_table = 'v_member_insurance'

    def __unicode__(self):
        return unicode(self.member)


class MemberSectionPeriod(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員名")
    division = models.ForeignKey(Section, on_delete=models.PROTECT, blank=True, null=True,
                                 related_name='memberdivisionperiod_set',
                                 verbose_name=u"事業部")
    section = models.ForeignKey(Section, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"部署")
    subsection = models.ForeignKey(Section, blank=True, null=True, on_delete=models.PROTECT,
                                   related_name='membersubsectionperiod_set',
                                   verbose_name=u"課・グループ")
    start_date = models.DateField(verbose_name=u"開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日")

    class Meta:
        ordering = ['start_date']
        verbose_name = verbose_name_plural = u"社員の部署期間"

    def __unicode__(self):
        f = u"%s - %s(%s〜%s)"
        if self.division:
            organization = unicode(self.division)
        elif self.section:
            organization = unicode(self.section)
        else:
            organization = unicode(self.subsection)
        return f % (self.member.__unicode__(), organization, self.start_date, self.end_date)


class MemberSalespersonPeriod(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員名")
    salesperson = models.ForeignKey(Salesperson, on_delete=models.PROTECT, verbose_name=u"営業員")
    start_date = models.DateField(verbose_name=u"開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日")

    class Meta:
        ordering = ['start_date']
        verbose_name = verbose_name_plural = u"社員の営業員期間"

    def __unicode__(self):
        f = u"%s - %s(%s〜%s)"
        return f % (self.member.__unicode__(), self.salesperson.__unicode__(), self.start_date, self.end_date)


class MemberSalesOffPeriod(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員名")
    sales_off_reason = models.ForeignKey(SalesOffReason, on_delete=models.PROTECT, verbose_name=u"営業対象外理由")
    start_date = models.DateField(verbose_name=u"開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日")

    class Meta:
        ordering = ['start_date']
        verbose_name = verbose_name_plural = u"社員の営業対象外期間"

    def __unicode__(self):
        f = u"%s - %s(%s〜%s)"
        return f % (unicode(self.member), unicode(self.sales_off_reason), self.start_date, self.end_date)


class PositionShip(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員名")
    position = models.DecimalField(
        blank=True, null=True, max_digits=4, decimal_places=1, choices=constants.CHOICE_POSITION, verbose_name=u"職位"
    )
    section = models.ForeignKey(Section, on_delete=models.PROTECT, verbose_name=u"所属")
    is_part_time = models.BooleanField(default=False, verbose_name=u"兼任")

    class Meta:
        ordering = ['position']
        verbose_name = verbose_name_plural = u"職位"

    def __unicode__(self):
        return "%s - %s %s" % (self.get_position_display(), self.member.first_name, self.member.last_name)


class Client(AbstractCompany):
    employee_count = models.IntegerField(blank=True, null=True, verbose_name=u"従業員数")
    sale_amount = models.BigIntegerField(blank=True, null=True, verbose_name=u"売上高")
    undertaker = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"担当者")
    undertaker_mail = models.EmailField(blank=True, null=True, verbose_name=u"担当者メール")
    payment_month = models.CharField(blank=True, null=True, max_length=1, default='1',
                                     choices=constants.CHOICE_PAYMENT_MONTH, verbose_name=u"支払いサイト")
    payment_day = models.CharField(blank=True, null=True, max_length=2, default='99',
                                   choices=constants.CHOICE_PAYMENT_DAY, verbose_name=u"支払日")
    tax_rate = models.DecimalField(default=0.08, max_digits=3, decimal_places=2, choices=constants.CHOICE_TAX_RATE,
                                   verbose_name=u"税率")
    decimal_type = models.CharField(max_length=1, default='0', choices=constants.CHOICE_DECIMAL_TYPE,
                                    verbose_name=u"小数の処理区分")
    remark = models.TextField(blank=True, null=True, verbose_name=u"評価")
    comment = models.TextField(blank=True, null=True, verbose_name=u"備考")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"営業担当")
    quotation_file = models.FileField(blank=True, null=True, upload_to="./quotation",
                                      verbose_name=u"見積書テンプレート")
    request_file = models.FileField(blank=True, null=True, upload_to="./request", verbose_name=u"請求書テンプレート",
                                    help_text=u"如果该项目为空，则使用WT自己的模板。")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False)

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"取引先"

    def get_pay_date(self, date=datetime.date.today()):
        """支払い期限日を取得する。

        :param date:
        :return:
        """
        months = int(self.payment_month) if self.payment_month else 1
        pay_month = common.add_months(date, months)
        if self.payment_day == '99' or not self.payment_day:
            return common.get_last_day_by_month(pay_month)
        else:
            pay_day = int(self.payment_day)
            last_day = common.get_last_day_by_month(pay_month)
            if last_day.day < pay_day:
                return last_day
            return datetime.date(pay_month.year, pay_month.month, pay_day)

    def get_attendance_amount(self, ym):
        """対象年月の出勤売上を取得する。

        :param ym: 対象年月
        :return:
        """
        amount = MemberAttendance.objects.public_filter(year=ym[:4], month=ym[4:],
                                                        project_member__project__client=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def get_expenses_amount(self, ym):
        amount = MemberExpenses.objects.public_filter(year=ym[:4], month=ym[4:],
                                                      project_member__project__client=self)\
            .aggregate(amount=Sum('price'))
        return amount.get('amount', 0) if amount.get('amount', 0) else 0

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class ClientMember(BaseModel):
    name = models.CharField(max_length=30, verbose_name=u"名前")
    email = models.EmailField(blank=True, null=True, verbose_name=u"メールアドレス")
    phone = models.CharField(blank=True, null=True, max_length=11, verbose_name=u"電話番号")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name=u"所属会社")

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"お客様"

    def __unicode__(self):
        return "%s - %s" % (self.client.name, self.name)


class Skill(BaseModel):
    name = models.CharField(blank=False, null=False, unique=True, max_length=30, verbose_name=u"名称")

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"スキル"
        db_table = 'mst_skill'

    def __unicode__(self):
        return self.name


class Holiday(BaseModel):
    date = models.DateField(unique=True, verbose_name=u"日付")
    comment = models.CharField(max_length=100, verbose_name=u"説明")

    class Meta:
        ordering = ['date']
        verbose_name = verbose_name_plural = u"休日"
        db_table = 'mst_holiday'


class OS(BaseModel):
    name = models.CharField(max_length=15, unique=True, verbose_name=u"名称")

    class Meta:
        ordering = ['name']
        verbose_name = verbose_name_plural = u"機種／OS"
        db_table = 'mst_os'

    def __unicode__(self):
        return self.name


class Project(BaseModel):
    name = models.CharField(blank=False, null=False, max_length=50, verbose_name=u"案件名称")
    description = models.TextField(blank=True, null=True, verbose_name=u"案件概要")
    business_type = models.CharField(blank=False, null=True, max_length=2,
                                     choices=constants.CHOICE_PROJECT_BUSINESS_TYPE,
                                     verbose_name=u"事業分類",
                                     help_text=u"必ず入力してください、質問があったら 沈さん にお問い合わせください。")
    skills = models.ManyToManyField(Skill, through='ProjectSkill', blank=True, verbose_name=u"スキル要求")
    os = models.ManyToManyField(OS, blank=True, verbose_name=u"機種／OS")
    start_date = models.DateField(blank=True, null=True, verbose_name=u"開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日",
                                help_text=u"もし設定した終了日は一番最後の案件メンバーの終了日より以前の日付だったら、"
                                          u"自動的に最後のメンバーの終了日に設定する。")
    address = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"作業場所")
    nearest_station = models.CharField(blank=False, null=True, max_length=15, verbose_name=u"最寄駅",
                                       help_text=u"必ず入力してください、沈さんの要求により追加しました。")
    status = models.IntegerField(choices=constants.CHOICE_PROJECT_STATUS, verbose_name=u"ステータス")
    attendance_type = models.CharField(max_length=1, default='1', choices=constants.CHOICE_ATTENDANCE_TYPE,
                                       verbose_name=u"出勤の計算区分")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=160, verbose_name=u"基準時間",
                                    help_text=u"该项目仅仅是作为项目中各人员时间的默认设置，计算时不会使用该值。")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=180, verbose_name=u"最大時間",
                                    help_text=u"该项目仅仅是作为项目中各人员时间的默认设置，计算时不会使用该值。")
    is_lump = models.BooleanField(default=False, verbose_name=u"一括フラグ")
    lump_amount = models.BigIntegerField(default=0, blank=True, null=True, verbose_name=u"一括金額")
    lump_comment = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"一括の備考",
                                    help_text=u"该项目会作为请求书中備考栏中的值。")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給",
                                        help_text=u"选中后将会无视人员的单价与增减等信息，计算请求时会将总时间乘以时薪。")
    is_reserve = models.BooleanField(default=False, verbose_name=u"待機案件フラグ",
                                     help_text=u"バーチャル案件です、コストなどを算出ために非稼働メンバーを"
                                               u"この案件にアサインすればいい。")
    client = models.ForeignKey(Client, null=True, on_delete=models.PROTECT, verbose_name=u"関連会社")
    boss = models.ForeignKey(ClientMember, blank=False, null=True, related_name="boss_set", on_delete=models.PROTECT,
                             verbose_name=u"案件責任者")
    middleman = models.ForeignKey(ClientMember, blank=True, null=True, on_delete=models.PROTECT,
                                  related_name="middleman_set", verbose_name=u"案件連絡者")
    salesperson = models.ForeignKey(Salesperson, blank=False, null=True, on_delete=models.PROTECT, verbose_name=u"営業員")
    department = models.ForeignKey(Section, blank=False, null=True, verbose_name=u"所属部署", on_delete=models.PROTECT,
                                   help_text=u"一括案件で、メンバーアサインしていない場合を設定する。")
    members = models.ManyToManyField(Member, through='ProjectMember', blank=True)

    objects = PublicManager(is_deleted=False, client__is_deleted=False)

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'client')
        verbose_name = verbose_name_plural = u"案件"
        permissions = (
            ('view_project', u'案件参照'),
        )

    def __unicode__(self):
        return self.name

    def get_project_members(self):
        """案件の現在アサイン中のメンバーを取得する。

        :return:
        """
        today = datetime.date.today()
        return self.projectmember_set.public_filter(start_date__lte=today,
                                                    end_date__gte=today)

    def get_recommended_members(self):
        # 如果案件为提案状态则自动推荐待机中的人员及即将待机的人
        members = []

        if self.status != 1:
            return members

        dict_skills = {}
        for skill in self.skills.public_all():
            dict_skills[skill.name] = self.get_members_by_skill_name(skill.name)

        return dict_skills

    def get_members_by_skill_name(self, name):
        members = []
        if not name:
            return members

        next_2_month = common.add_months(datetime.date.today(), 2)
        last_day_a_month_later = datetime.date(next_2_month.year, next_2_month.month, 1)
        query_set = Member.objects.raw(u"SELECT DISTINCT m.* "
                                       u"  FROM eb_member m "
                                       u"  JOIN eb_projectmember pm ON m.ID = pm.MEMBER_ID "
                                       u"  JOIN eb_projectskill ps ON ps.PROJECT_ID = pm.PROJECT_ID"
                                       u"  JOIN mst_skill s ON s.ID = ps.SKILL_ID"
                                       u" WHERE s.NAME = %s"
                                       u"   AND pm.END_DATE < %s"
                                       u"   AND pm.STATUS <> 1"
                                       u"   AND NOT EXISTS (SELECT 1 "
                                       u"                     FROM eb_projectmember pm2"
                                       u"                    WHERE pm2.START_DATE >= %s"
                                       u"                      AND pm2.MEMBER_ID = m.ID"
                                       u"                      AND pm2.PROJECT_ID = %s"
                                       u"                      AND pm2.STATUS = 1)", [name,
                                                                                      last_day_a_month_later,
                                                                                      datetime.date.today(),
                                                                                      self.pk]
                                       )
        members = list(query_set)
        return members

    def get_project_members_by_month(self, date=None, ym=None):
        if date:
            first_day = datetime.date(date.year, date.month, 1)
        elif ym:
            first_day = common.get_first_day_from_ym(ym)
        else:
            date = datetime.date.today()
            first_day = datetime.date(date.year, date.month, 1)
        last_day = common.get_last_day_by_month(first_day)
        return self.projectmember_set.public_filter(start_date__lte=last_day,
                                                    end_date__gte=first_day,
                                                    is_deleted=False).exclude(status='1')

    def get_first_project_member(self):
        """営業企画書を出すとき、1つ目に表示するメンバー。

        Arguments：
          なし

        Returns：
          Member のインスタンス

        Raises：
          なし
        """
        now = datetime.date.today()
        first_day = datetime.date(now.year, now.month, 1)
        last_day = common.get_last_day_by_month(now)
        project_members = self.projectmember_set.public_filter(start_date__lte=last_day, end_date__gte=first_day,
                                                               role=7, is_deleted=False)
        if project_members.count() == 0:
            project_members = self.projectmember_set.public_filter(start_date__lte=last_day, end_date__gte=first_day,
                                                                   role=6, is_deleted=False)
        if project_members.count() == 0:
            project_members = self.projectmember_set.public_filter(start_date__lte=last_day, end_date__gte=first_day,
                                                                   is_deleted=False)
        if project_members.count() > 0:
            return project_members[0]
        else:
            return None

    def get_working_project_members(self):
        now = datetime.date.today()
        first_day = datetime.date(now.year, now.month, 1)
        last_day = common.get_last_day_by_month(now)
        return self.projectmember_set.public_filter(start_date__lte=last_day, end_date__gte=first_day,
                                                    is_deleted=False)

    def get_expenses(self, year, month, project_members):
        """指定年月の清算リストを取得する。

        :param year:
        :param month:
        :param project_members:
        :return:
        """
        return MemberExpenses.objects.public_filter(project_member__project=self,
                                                    year=str(year),
                                                    month=str(month),
                                                    project_member__in=project_members).order_by('category__name')

    def get_order_by_month(self, year, month):
        """指定年月の注文履歴を取得する。

        :param year:
        :param month:
        :return:
        """
        ym = year + month
        first_day = common.get_first_day_from_ym(ym)
        last_day = common.get_last_day_by_month(first_day)
        return self.clientorder_set.public_filter(start_date__lte=last_day, end_date__gte=first_day, is_deleted=False)

    def get_year_month_order_finished(self):
        """案件の月単位の註文書を取得する。

        Arguments：
          なし

        Returns：
          (対象年, 対処月, ClientOrder, 注文書数)

        Raises：
          なし
        """
        ret_value = []
        for year, month in common.get_year_month_list(self.start_date, self.end_date):
            client_orders = self.get_order_by_month(year, month)
            if client_orders:
                cnt = client_orders.count()
                project_members_month = self.get_project_members_by_month(ym=year + month)
                old_project_request = self.get_project_request(year, month)
                for client_order in client_orders:
                    project_request = self.get_project_request(year, month, client_order)
                    if project_request and not project_request.pk:
                        project_request = old_project_request
                    if project_request and not project_request.pk:
                        project_request = None
                    ret_value.append((year, month, client_order, cnt, project_members_month, project_request))
            else:
                ret_value.append((year, month, None, 0, None, None))
        return ret_value

    def get_year_month_attendance_finished(self):
        """案件の月単位の勤怠入力状況を取得する。

        Arguments：
          なし

        Returns：
          (対象年月, True / False)

        Raises：
          なし
        """
        ret_value = []
        for year, month in common.get_year_month_list(self.start_date, self.end_date):
            first_day = datetime.date(int(year), int(month), 1)
            last_day = common.get_last_day_by_month(first_day)
            project_members = self.get_project_members_by_month(first_day)
            if project_members.count() == 0:
                ret_value.append((year + month, False))
            else:
                query_set = ProjectMember.objects.raw(u"select pm.* "
                                                      u"  from eb_projectmember pm"
                                                      u" where not exists (select 1 "
                                                      u"                     from eb_memberattendance ma"
                                                      u"				    where pm.id = ma.project_member_id"
                                                      u"                      and ma.year = %s"
                                                      u"                      and ma.month = %s"
                                                      u"					  and ma.is_deleted = 0)"
                                                      u"   and pm.end_date >= %s"
                                                      u"   and pm.start_date <= %s"
                                                      u"   and pm.project_id = %s"
                                                      u"   and pm.is_deleted = 0",
                                                      [year, month, first_day, last_day, self.pk])
                project_members = list(query_set)
                ret_value.append((year + month, False if len(project_members) > 0 else True))
        return ret_value

    def get_project_request(self, str_year, str_month, client_order=None):
        """請求番号を取得する。

        :param str_year:
        :param str_month:
        :param client_order:
        :return:
        """
        if self.projectrequest_set.filter(year=str_year, month=str_month, client_order=client_order).count() == 0:
            # 指定年月の請求番号がない場合、請求番号を発行する。
            max_request_no = ProjectRequest.objects.filter(year=str_year, month=str_month).aggregate(Max('request_no'))
            request_no = max_request_no.get('request_no__max')
            if request_no and re.match(r"^([0-9]{7}|[0-9]{7}-[0-9]{3})$", request_no):
                no = request_no[4:7]
                no = "%03d" % (int(no) + 1,)
                next_request = "%s%s%s" % (str_year[2:], str_month, no)
            else:
                next_request = "%s%s%s" % (str_year[2:], str_month, "001")
            project_request = ProjectRequest(project=self, client_order=client_order,
                                             year=str_year, month=str_month, request_no=next_request)
            return project_request
        else:
            # 存在する場合、そのまま使う、再発行はしません。
            project_request = self.projectrequest_set.filter(year=str_year, month=str_month,
                                                             client_order=client_order)[0]
            return project_request

    def can_end_project(self):
        """案件が終了できるかどうかを判断する。

        案件メンバーの一人でも終了日は本日以降でしたら、終了はできません。

        :return:
        """
        today = datetime.date.today()
        project_members = self.projectmember_set.all()
        for project_member in project_members:
            if project_member.end_date >= today:
                return False
        return True

    @property
    def all_price_lump(self):
        """一括案件の税込売上を取得する。

        :return:
        """
        return self.lump_amount + self.lump_amount * self.client.tax_rate

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


def get_client_order_path(instance, filename):
    return u"./client_order/{0}/{1}{2}_{3}".format(instance.project.client.name,
                                                   instance.start_date.year, instance.start_date.month,
                                                   filename)


class ClientOrder(BaseModel):
    projects = models.ManyToManyField(Project, verbose_name=u"案件")
    name = models.CharField(max_length=50, verbose_name=u"注文書名称")
    start_date = models.DateField(default=timezone.now, verbose_name=u"開始日")
    end_date = models.DateField(default=timezone.now, verbose_name=u"終了日")
    order_no = models.CharField(max_length=20, verbose_name=u"注文番号")
    order_date = models.DateField(blank=False, null=True, verbose_name=u"注文日")
    contract_type = models.CharField(max_length=2, blank=False, null=True,
                                     choices=constants.CHOICE_CLIENT_CONTRACT_TYPE, verbose_name=u"契約形態")
    bank_info = models.ForeignKey(BankInfo, blank=False, null=True, on_delete=models.PROTECT, verbose_name=u"振込先口座")
    order_file = models.FileField(blank=True, null=True, upload_to=get_client_order_path, verbose_name=u"注文書")
    member_comma_list = models.CharField(max_length=255, blank=True, null=True, editable=False,
                                         verbose_name=u"メンバー主キーのリスト",
                                         validators=[validate_comma_separated_integer_list])

    class Meta:
        ordering = ['name', 'start_date', 'end_date']
        verbose_name = verbose_name_plural = u"お客様注文書"

    def __unicode__(self):
        return self.name


class ProjectRequest(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, verbose_name=u"案件")
    client_order = models.ForeignKey(ClientOrder, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"注文書")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    request_no = models.CharField(max_length=7, unique=True, verbose_name=u"請求番号")
    request_name = models.CharField(max_length=50, blank=True, null=True, verbose_name=u"請求名称")
    cost = models.IntegerField(default=0, verbose_name=u"コスト")
    amount = models.IntegerField(default=0, verbose_name=u"請求金額（税込）")
    turnover_amount = models.IntegerField(default=0, verbose_name=u"売上金額（基本単価＋残業料）（税抜き）")
    tax_amount = models.IntegerField(default=0, verbose_name=u"税金")
    expenses_amount = models.IntegerField(default=0, verbose_name=u"精算金額")
    filename = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"請求書ファイル名")
    created_user = models.ForeignKey(User, related_name='created_requests', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"作成者")
    created_date = models.DateTimeField(null=True, auto_now_add=True, editable=False, verbose_name=u"作成日時")
    updated_user = models.ForeignKey(User, related_name='updated_requests', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"更新者")
    updated_date = models.DateTimeField(null=True, auto_now=True, editable=False, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        ordering = ['-request_no']
        unique_together = ('project', 'client_order', 'year', 'month')
        verbose_name = verbose_name_plural = u"案件請求情報"
        permissions = (
            ('generate_request', u"請求書作成"),
            ('view_turnover', u"売上情報参照")
        )

    def __unicode__(self):
        return u"%s-%s" % (self.request_no, self.project.name)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, other_data=None):
        super(ProjectRequest, self).save(force_insert, force_update, using, update_fields)
        # 請求書作成時、請求に関する全ての情報を履歴として保存する。
        if other_data:
            data = other_data
            # 既存のデータを全部消す。
            if hasattr(self, "projectrequestheading"):
                self.projectrequestheading.delete()
            self.projectrequestdetail_set.all().delete()
            bank = data['EXTRA']['BANK']
            date = datetime.datetime(int(self.year), int(self.month), 1, tzinfo=common.get_tz_utc())
            date = common.get_last_day_by_month(date)
            heading = ProjectRequestHeading(project_request=self,
                                            is_lump=self.project.is_lump,
                                            lump_amount=self.project.lump_amount,
                                            lump_comment=self.project.lump_comment,
                                            is_hourly_pay=self.project.is_hourly_pay,
                                            client=self.project.client,
                                            client_post_code=data['DETAIL']['CLIENT_POST_CODE'],
                                            client_address=data['DETAIL']['CLIENT_ADDRESS'],
                                            client_tel=data['DETAIL']['CLIENT_TEL'],
                                            client_name=data['DETAIL']['CLIENT_COMPANY_NAME'],
                                            tax_rate=self.project.client.tax_rate,
                                            decimal_type=self.project.client.decimal_type,
                                            work_period_start=data['EXTRA']['WORK_PERIOD_START'],
                                            work_period_end=data['EXTRA']['WORK_PERIOD_END'],
                                            remit_date=data['EXTRA']['REMIT_DATE'],
                                            publish_date=data['EXTRA']['PUBLISH_DATE'],
                                            company_post_code=data['DETAIL']['POST_CODE'],
                                            company_address=data['DETAIL']['ADDRESS'],
                                            company_name=data['DETAIL']['COMPANY_NAME'],
                                            company_tel=data['DETAIL']['TEL'],
                                            company_master=data['DETAIL']['MASTER'],
                                            bank=data['EXTRA']['BANK'],
                                            bank_name=bank.bank_name,
                                            branch_no=bank.branch_no,
                                            branch_name=bank.branch_name,
                                            account_type=bank.account_type,
                                            account_number=bank.account_number,
                                            account_holder=bank.account_holder)
            heading.save()
            for i, item in enumerate(data['MEMBERS']):
                project_member = item["EXTRA_PROJECT_MEMBER"]
                ym = data['EXTRA']['YM']
                total_hours = item['ITEM_WORK_HOURS'] if item['ITEM_WORK_HOURS'] else 0
                expenses_price = project_member.get_expenses_amount(ym[:4], int(ym[4:]))
                try:
                    member_attendance = MemberAttendance.objects.get(
                        project_member=project_member, year=self.year, month=self.month
                    )
                    with connection.cursor() as cursor:
                        cursor.callproc('sp_project_member_cost', [
                            project_member.member.pk,
                            project_member.pk,
                            self.year,
                            self.month,
                            len(common.get_business_days(self.year, self.month)),
                            member_attendance.total_hours_bp or member_attendance.total_hours,
                            member_attendance.allowance or 0,
                            member_attendance.night_days or 0,
                            member_attendance.traffic_cost or 0,
                            expenses_price,
                        ])
                        dict_cost = common.dictfetchall(cursor)[0]
                except Exception as ex:
                    dict_cost = dict()
                member_section = project_member.member.get_section(date)
                if not member_section:
                    raise CustomException(u'{}は{}年{}月の部署が設定されていません。'.format(
                        project_member.member, self.year, self.month)
                    )
                detail = ProjectRequestDetail(project_request=self,
                                              project_member=project_member,
                                              year=self.year,
                                              month=self.month,
                                              member_section=member_section,
                                              member_type=project_member.member.member_type,
                                              salesperson=project_member.member.get_salesperson(date),
                                              subcontractor=project_member.member.subcontractor,
                                              salary=dict_cost.get('salary', 0) or 0,
                                              cost=dict_cost.get('cost', 0) or 0,
                                              no=str(i + 1),
                                              hourly_pay=project_member.hourly_pay if project_member.hourly_pay else 0,
                                              basic_price=project_member.price,
                                              min_hours=project_member.min_hours,
                                              max_hours=project_member.max_hours,
                                              total_hours=total_hours,
                                              extra_hours=item['ITEM_EXTRA_HOURS']if item['ITEM_EXTRA_HOURS'] else 0,
                                              rate=item['ITEM_RATE'],
                                              plus_per_hour=project_member.plus_per_hour,
                                              minus_per_hour=project_member.minus_per_hour,
                                              total_price=item['ITEM_AMOUNT_TOTAL'],
                                              expenses_price=expenses_price,
                                              comment=item['ITEM_COMMENT'])
                detail.save()


class ProjectRequestHeading(models.Model):
    project_request = models.OneToOneField(ProjectRequest, verbose_name=u"請求書")
    is_lump = models.BooleanField(default=False, verbose_name=u"一括フラグ")
    lump_amount = models.BigIntegerField(default=0, blank=True, null=True, verbose_name=u"一括金額")
    lump_comment = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"一括の備考")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    client = models.ForeignKey(Client, null=True, on_delete=models.PROTECT, verbose_name=u"関連会社")
    client_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"お客様郵便番号")
    client_address = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"お客様住所１")
    client_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様電話番号")
    client_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"お客様会社名")
    tax_rate = models.DecimalField(blank=True, null=True, max_digits=3, decimal_places=2, verbose_name=u"税率")
    decimal_type = models.CharField(blank=True, null=True, max_length=1, choices=constants.CHOICE_DECIMAL_TYPE,
                                    verbose_name=u"小数の処理区分")
    work_period_start = models.DateField(blank=True, null=True, verbose_name=u"作業期間＿開始")
    work_period_end = models.DateField(blank=True, null=True, verbose_name=u"作業期間＿終了")
    remit_date = models.DateField(blank=True, null=True, verbose_name=u"お支払い期限")
    publish_date = models.DateField(blank=True, null=True, verbose_name=u"発行日")
    company_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"本社郵便番号")
    company_address = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所")
    company_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"会社名")
    company_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様電話番号")
    company_master = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"代表取締役")
    bank = models.ForeignKey(BankInfo, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"口座")
    bank_name = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行名称")
    branch_no = models.CharField(blank=True, null=True, max_length=3, verbose_name=u"支店番号")
    branch_name = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"支店名称")
    account_type = models.CharField(blank=True, null=True, max_length=1, choices=constants.CHOICE_ACCOUNT_TYPE,
                                    verbose_name=u"預金種類")
    account_number = models.CharField(blank=True, null=True, max_length=7, verbose_name=u"口座番号")
    account_holder = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義")
    created_dt = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        ordering = ['-project_request__request_no']
        verbose_name = verbose_name_plural = u"案件請求見出し"

    def __unicode__(self):
        return unicode(self.project_request)


class ProjectRequestDetail(models.Model):
    project_request = models.ForeignKey(ProjectRequest, on_delete=models.PROTECT, verbose_name=u"請求書")
    project_member = models.ForeignKey('ProjectMember', on_delete=models.PROTECT, verbose_name=u"メンバー")
    year = models.CharField(blank=True, null=True, max_length=4, verbose_name=u"対象年")
    month = models.CharField(blank=True, null=True, max_length=2, verbose_name=u"対象月")
    member_section = models.ForeignKey(Section, verbose_name=u"部署")
    member_type = models.IntegerField(default=0, choices=constants.CHOICE_MEMBER_TYPE, verbose_name=u"社員区分")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"営業員")
    subcontractor = models.ForeignKey(Subcontractor, blank=True, null=True, on_delete=models.PROTECT,
                                      verbose_name=u"協力会社")
    salary = models.IntegerField(default=0, verbose_name=u"給料")
    cost = models.IntegerField(default=0, verbose_name=u"コスト")
    no = models.IntegerField(verbose_name=u"番号")
    hourly_pay = models.IntegerField(default=0, verbose_name=u"時給")
    basic_price = models.IntegerField(default=0, verbose_name=u"単価")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"基準時間")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"最大時間")
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"合計時間")
    extra_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"残業時間")
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=1, verbose_name=u"率")
    plus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"増（円）")
    minus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"減（円）")
    total_price = models.IntegerField(default=0, verbose_name=u"売上（基本単価＋残業料）（税抜き）")
    expenses_price = models.IntegerField(default=0, verbose_name=u"精算金額")
    expect_price = models.IntegerField(blank=True, null=True, verbose_name=u"請求金額")
    comment = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"備考")
    created_dt = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        ordering = ['-project_request__request_no', 'no']
        unique_together = ('project_request', 'no')
        verbose_name = verbose_name_plural = u"案件請求明細"

    def __unicode__(self):
        f = u"%s %s%sの請求明細"
        return f % (self.project_member,
                    self.project_request.get_year_display(),
                    self.project_request.get_month_display())

    def get_tax_price(self):
        """税金を計算する。
        """
        if not hasattr(self.project_request, 'projectrequestheading'):
            return 0

        tax_rate = self.project_request.projectrequestheading.tax_rate
        # decimal_type = self.project_request.projectrequestheading.decimal_type
        if tax_rate is None:
            return 0
        # if decimal_type == '0':
        #     # 四捨五入
        #     return int(round(self.total_price * tax_rate))
        # else:
        #     # 切り捨て
        #     return int(self.total_price * tax_rate)
        return round(self.total_price * tax_rate, 1)

    def get_all_price(self):
        """合計を計算する（税込、精算含む）
        """
        return int(self.total_price) + self.get_tax_price() + int(self.expenses_price)


class ProjectActivity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, verbose_name=u"案件")
    name = models.CharField(max_length=30, verbose_name=u"活動名称")
    open_date = models.DateTimeField(default=timezone.now, verbose_name=u"開催日時")
    address = models.CharField(max_length=255, verbose_name=u"活動場所")
    content = models.TextField(verbose_name=u"活動内容")
    client_members = models.ManyToManyField(ClientMember, blank=True, verbose_name=u"参加しているお客様")
    members = models.ManyToManyField(Member, blank=True, verbose_name=u"参加している社員")
    salesperson = models.ManyToManyField(Salesperson, blank=True, verbose_name=u"参加している営業員")
    created_date = models.DateTimeField(auto_now_add=True, editable=False)
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False, project__is_deleted=False)

    class Meta:
        ordering = ['project', 'open_date']
        verbose_name = verbose_name_plural = u"案件活動"

    def __unicode__(self):
        return "%s - %s" % (self.project.name, self.name)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class ProjectSkill(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, verbose_name=u"案件")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, verbose_name=u"スキル")
    period = models.IntegerField(blank=True, null=True, choices=constants.CHOICE_SKILL_TIME, verbose_name=u"経験年数")
    description = models.TextField(blank=True, null=True, verbose_name=u"備考")

    class Meta:
        verbose_name = verbose_name_plural = u"案件のスキル要求"

    def __unicode__(self):
        return "%s - %s" % (self.project.name, self.skill.name)


class ProjectStage(BaseModel):
    name = models.CharField(max_length=15, unique=True, verbose_name=u"作業工程名称")

    class Meta:
        verbose_name = verbose_name_plural = u"作業工程"
        db_table = 'mst_project_stage'

    def __unicode__(self):
        return self.name


class ProjectMember(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, verbose_name=u'案件名称')
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"名前")
    start_date = models.DateField(blank=False, null=True, verbose_name=u"開始日")
    end_date = models.DateField(blank=False, null=True, verbose_name=u"終了日")
    price = models.IntegerField(default=0, verbose_name=u"単価")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=160, verbose_name=u"基準時間")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=180, verbose_name=u"最大時間")
    plus_per_hour = models.IntegerField(default=0, verbose_name=u"増（円）")
    minus_per_hour = models.IntegerField(default=0, verbose_name=u"減（円）")
    hourly_pay = models.IntegerField(blank=True, null=True, verbose_name=u"時給")
    status = models.IntegerField(null=False, default=1,
                                 choices=constants.CHOICE_PROJECT_MEMBER_STATUS, verbose_name=u"ステータス")
    role = models.CharField(default="PG", max_length=2, choices=constants.CHOICE_PROJECT_ROLE, verbose_name=u"作業区分")
    stages = models.ManyToManyField(ProjectStage, blank=True, verbose_name=u"作業工程")
    contract_type = models.CharField(max_length=2, blank=True, null=True, choices=constants.CHOICE_CLIENT_CONTRACT_TYPE,
                                     verbose_name=u"契約形態")

    objects = PublicManager(is_deleted=False, project__is_deleted=False, member__is_deleted=False)

    class Meta:
        verbose_name = verbose_name_plural = u"案件メンバー"
        permissions = (
            ('edit_price', u'単価設定'),
        )

    def __unicode__(self):
        return self.member.__unicode__()

    def is_in_rd(self):
        if self.stages.public_filter(name=u"要件定義").count() > 0:
            return True
        else:
            return False

    def is_in_sa(self):
        if self.stages.public_filter(name=u"調査分析").count() > 0:
            return True
        else:
            return False

    def is_in_bd(self):
        if self.stages.public_filter(name=u"基本設計").count() > 0:
            return True
        else:
            return False

    def is_in_dd(self):
        if self.stages.public_filter(name=u"詳細設計").count() > 0:
            return True
        else:
            return False

    def is_in_pg(self):
        if self.stages.public_filter(name=u"開発製造").count() > 0:
            return True
        else:
            return False

    def is_in_pt(self):
        if self.stages.public_filter(name=u"単体試験").count() > 0:
            return True
        else:
            return False

    def is_in_it(self):
        if self.stages.public_filter(name=u"結合試験").count() > 0:
            return True
        else:
            return False

    def is_in_st(self):
        if self.stages.public_filter(name=u"総合試験").count() > 0:
            return True
        else:
            return False

    def is_in_maintain(self):
        if self.stages.public_filter(name=u"保守運用").count() > 0:
            return True
        else:
            return False

    def is_in_support(self):
        if self.stages.public_filter(name=u"サポート").count() > 0:
            return True
        else:
            return False

    def is_in_past(self):
        if self.end_date < datetime.date.today():
            return True
        else:
            return False

    def get_attendance(self, year, month):
        """指定された年月によって、該当するメンバーの勤怠情報を取得する。

        :param year: 対象年
        :param month: 対象月
        :return: MemberAttendanceのインスタンス、または None
        """
        try:
            return self.memberattendance_set.get(year=str(year), month="%02d" % (int(month),), is_deleted=False)
        except ObjectDoesNotExist:
            return None

    def get_attendance_amount(self, year, month):
        """メンバーの売上を取得する。

        :param year: 対象年
        :param month: 対象月
        :return:
        """
        attendance = self.get_attendance(year, month)
        if attendance:
            return attendance.price
        else:
            return 0

    def get_expenses_amount(self, year, month):
        """メンバーの清算を取得する。

        :param year:
        :param month:
        :return:
        """
        expense = self.memberexpenses_set.public_filter(year=str(year),
                                                        month="%02d" % int(month),
                                                        is_deleted=False).aggregate(price=Sum('price'))
        return expense.get('price') if expense.get('price') else 0

    def get_cost_amount(self, year, month):
        cost = self.member.cost
        attendance = self.get_attendance(year, month)
        if attendance:
            return cost + int(attendance.extra_hours * 2000)
        else:
            return cost

    def get_attendance_dict(self, year, month):
        """指定された年月の出勤情報を取得する。

        :param year: 対象年
        :param month: 対象月
        :return:
        """
        attendance = self.get_attendance(year, month)
        d = dict()
        # 勤務時間
        d['ITEM_WORK_HOURS'] = attendance.total_hours if attendance else u""

        if self.project.is_hourly_pay:
            # 基本金額
            d['ITEM_AMOUNT_BASIC'] = 0
            # 残業時間
            d['ITEM_EXTRA_HOURS'] = 0
            # 率
            d['ITEM_RATE'] = 1
            # 減（円）
            d['ITEM_MINUS_PER_HOUR'] = 0
            # 増（円）
            d['ITEM_PLUS_PER_HOUR'] = 0
            # 基本金額＋残業金額
            d['ITEM_AMOUNT_TOTAL'] = attendance.price * attendance.total_hours if attendance else 0
        else:
            # 基本金額
            d['ITEM_AMOUNT_BASIC'] = self.price if attendance else u""
            # 残業時間
            d['ITEM_EXTRA_HOURS'] = attendance.extra_hours if attendance else u""
            # 率
            d['ITEM_RATE'] = attendance.rate if attendance and attendance.rate else 1
            # 減（円）
            if self.minus_per_hour is None:
                d['ITEM_MINUS_PER_HOUR'] = (self.price / self.min_hours) if attendance else u""
            else:
                d['ITEM_MINUS_PER_HOUR'] = self.minus_per_hour
            # 増（円）
            if self.plus_per_hour is None:
                d['ITEM_PLUS_PER_HOUR'] = (self.price / self.max_hours) if attendance else u""
            else:
                d['ITEM_PLUS_PER_HOUR'] = self.plus_per_hour

            if attendance and attendance.extra_hours > 0:
                d['ITEM_AMOUNT_EXTRA'] = attendance.extra_hours * d['ITEM_PLUS_PER_HOUR']
                d['ITEM_PLUS_PER_HOUR2'] = d['ITEM_PLUS_PER_HOUR']
                d['ITEM_MINUS_PER_HOUR2'] = u""
            elif attendance and attendance.extra_hours < 0:
                d['ITEM_AMOUNT_EXTRA'] = attendance.extra_hours * d['ITEM_MINUS_PER_HOUR']
                d['ITEM_PLUS_PER_HOUR2'] = u""
                d['ITEM_MINUS_PER_HOUR2'] = d['ITEM_MINUS_PER_HOUR']
            else:
                d['ITEM_AMOUNT_EXTRA'] = 0
                d['ITEM_PLUS_PER_HOUR2'] = u""
                d['ITEM_MINUS_PER_HOUR2'] = u""
            # 基本金額＋残業金額
            d['ITEM_AMOUNT_TOTAL'] = attendance.price if attendance else self.price
        # 備考
        d['ITEM_COMMENT'] = attendance.comment if attendance and attendance.comment else u""
        d['ITEM_OTHER'] = u""

        return d

    def get_bp_member_orders(self):
        if not self.start_date or not self.end_date:
            return [(None, None, None)]
        orders = []
        max_months = self.end_date.year * 12 + self.end_date.month
        min_months = self.start_date.year * 12 + self.start_date.month
        today = datetime.date.today()
        next_month = common.add_months(today, 1)
        max_date = next_month \
            if self.end_date and next_month.strftime('%Y%m') <= self.end_date.strftime('%Y%m') else today
        for i in range(max_months - min_months, -1, -1):
            date = common.add_months(self.start_date, i)
            if (max_date.year * 12 + max_date.month) < (date.year * 12 + date.month):
                # 来月以降だったら、表示する必要ないので、スキップする。
                continue
            try:
                order = BpMemberOrder.objects.annotate(
                    ym_start=Concat('year', 'month', output_field=models.CharField()),
                    ym_end=Concat('end_year', 'end_month', output_field=models.CharField()),
                ).get(project_member=self, ym_start__lte='%04d%02d' % (date.year, date.month),
                      ym_end__gte='%04d%02d' % (date.year, date.month))
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                order = None
            days = common.get_business_days(date.year, date.month)
            orders.append((date.year, date.month, len(days), order,
                           date.strftime('%Y%m') < common.add_months(today, -2).strftime('%Y%m')))
        return orders

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class SubcontractorRequest(models.Model):
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"協力会社")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, verbose_name=u"部署")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    request_no = models.CharField(max_length=7, unique=True, verbose_name=u"請求番号")
    request_name = models.CharField(max_length=50, blank=True, null=True, verbose_name=u"請求名称")
    pay_notify_no = models.CharField(max_length=9, unique=True, null=True, verbose_name=u"支払通知書番号")
    amount = models.IntegerField(default=0, verbose_name=u"請求金額（税込）")
    turnover_amount = models.IntegerField(default=0, verbose_name=u"売上金額（基本単価＋残業料）（税抜き）")
    tax_amount = models.IntegerField(default=0, verbose_name=u"税金")
    expenses_amount = models.IntegerField(default=0, verbose_name=u"精算金額")
    filename = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"請求書ファイル名")
    filename_pdf = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"請求書ＰＤＦ名")
    pay_notify_filename = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"支払通知書ファイル名")
    pay_notify_filename_pdf = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"支払通知書ＰＤＦ名")
    is_sent = models.BooleanField(default=False, verbose_name=u"送信")
    created_user = models.ForeignKey(User, related_name='created_subcontractor_requests', null=True,
                                     on_delete=models.PROTECT, editable=False, verbose_name=u"作成者")
    created_date = models.DateTimeField(null=True, auto_now_add=True, editable=False, verbose_name=u"作成日時")
    updated_user = models.ForeignKey(User, related_name='updated_subcontractor_requests', null=True,
                                     on_delete=models.PROTECT, editable=False, verbose_name=u"更新者")
    updated_date = models.DateTimeField(null=True, auto_now=True, editable=False, verbose_name=u"更新日時")

    class Meta:
        ordering = ['-request_no']
        unique_together = ('subcontractor', 'section', 'year', 'month')
        verbose_name = verbose_name_plural = u"協力会社請求情報"

    def __unicode__(self):
        return u"%s-%s" % (self.request_no, unicode(self.subcontractor))

    def get_absolute_request_path(self):
        """作成された請求書エクセルの絶対パスを取得する。

        :return:
        """
        return os.path.join(common.get_subcontractor_request_root_path(), self.year + self.month, self.filename)

    def get_absolute_request_pdf_path(self):
        """作成された請求書ＰＤＦの絶対パスを取得する。

        :return:
        """
        if self.filename_pdf is None:
            raise CustomException(u"ＢＰ請求書のＰＤＦは作成されていません。")
        return os.path.join(common.get_subcontractor_request_root_path(), self.year + self.month, self.filename_pdf)

    def get_absolute_pay_notify_path(self):
        """作成された支払通知書エクセルの絶対パスを取得する。

        :return:
        """
        return os.path.join(
            common.get_subcontractor_pay_notify_root_path(), self.year + self.month, self.pay_notify_filename
        )

    def get_absolute_pay_notify_pdf_path(self):
        """作成された支払通知書ＰＤＦの絶対パスを取得する。

        :return:
        """
        if self.filename_pdf is None:
            raise CustomException(u"支払通知書のＰＤＦは作成されていません。")
        return os.path.join(
            common.get_subcontractor_pay_notify_root_path(), self.year + self.month, self.pay_notify_filename_pdf
        )

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, other_data=None, mail_data=None):
        super(SubcontractorRequest, self).save(force_insert, force_update, using, update_fields)
        # メールの送信履歴
        if update_fields and len(update_fields) == 1 and 'is_sent' in update_fields \
                and mail_data and 'user' in mail_data:
            change_messages = []
            if mail_data.get('sender', None):
                change_messages.append(u'FROM:%s' % mail_data['sender'])
            if mail_data.get('recipient_list', None):
                change_messages.append(u'TO:%s' % mail_data['recipient_list'])
            if mail_data.get('cc_list', None):
                change_messages.append(u'CC:%s' % mail_data['cc_list'])
            if mail_data.get('attachment_list', None):
                change_messages.append(
                    u'添付ファイル:%s' % ','.join([os.path.basename(p) for p in mail_data['attachment_list']])
                )
            if mail_data.get('mail_title', None):
                change_messages.append(u'題名:%s' % mail_data['mail_title'])
            if mail_data.get('mail_body', None):
                change_messages.append(u'==========内容==========\n%s' % mail_data['mail_body'])
            LogEntry.objects.log_action(mail_data['user'].id,
                                        ContentType.objects.get_for_model(self).pk,
                                        self.pk,
                                        unicode(self),
                                        CHANGE,
                                        "\n".join(change_messages))
        # 請求書作成時、請求に関する全ての情報を履歴として保存する。
        if other_data:
            data = other_data
            # 既存のデータを全部消す。
            if hasattr(self, "subcontractorrequestheading"):
                self.subcontractorrequestheading.delete()
            self.subcontractorrequestdetail_set.all().delete()
            bank = data['EXTRA']['BANK']
            date = datetime.datetime(int(self.year), int(self.month), 1, tzinfo=common.get_tz_utc())
            date = common.get_last_day_by_month(date)
            company = data['EXTRA']['COMPANY']
            heading = SubcontractorRequestHeading(
                subcontractor_request=self,
                is_lump=False,
                lump_amount=0,
                lump_comment=0,
                is_hourly_pay=False,
                client=company,
                client_post_code=data['DETAIL']['CLIENT_POST_CODE'],
                client_address=data['DETAIL']['CLIENT_ADDRESS'],
                client_tel=data['DETAIL']['CLIENT_TEL'],
                client_fax=data['DETAIL']['CLIENT_FAX'],
                client_name=data['DETAIL']['CLIENT_COMPANY_NAME'],
                tax_rate=company.tax_rate,
                decimal_type=company.decimal_type,
                work_period_start=data['EXTRA']['WORK_PERIOD_START'],
                work_period_end=data['EXTRA']['WORK_PERIOD_END'],
                remit_date=data['EXTRA']['REMIT_DATE'],
                publish_date=data['EXTRA']['PUBLISH_DATE'],
                created_date=data['DETAIL']['CREATE_DATE'],
                company_post_code=data['DETAIL']['POST_CODE'],
                company_address=data['DETAIL']['ADDRESS'],
                company_name=data['DETAIL']['COMPANY_NAME'],
                company_tel=data['DETAIL']['TEL'],
                company_master=data['DETAIL']['MASTER'],
                bank=data['EXTRA']['BANK'],
                bank_name=bank.bank_name if bank else '',
                branch_no=bank.branch_no if bank else '',
                branch_name=bank.branch_name if bank else '',
                account_type=bank.account_type if bank else '',
                account_number=bank.account_number if bank else '',
                account_holder=bank.account_holder if bank else ''
            )
            heading.save()
            for i, item in enumerate(data['MEMBERS']):
                project_member = item.get('EXTRA_PROJECT_MEMBER', None)
                contract = project_member.member.get_contract(date) if project_member else None
                lump_contract = item.get('EXTRA_LUMP_CONTRACT', None)
                detail = SubcontractorRequestDetail(subcontractor_request=self)
                detail.bp_member_order = item['BP_MEMBER_ORDER']
                detail.project_member = project_member
                detail.member_type = 4
                if project_member:
                    detail.member_section = project_member.member.get_section(date)
                    detail.salesperson = project_member.member.get_salesperson(date)
                elif lump_contract:
                    detail.project = lump_contract.project
                    detail.member_section = lump_contract.project.department
                    detail.salesperson = lump_contract.project.salesperson
                detail.subcontractor = self.subcontractor
                detail.cost = 0
                detail.no = str(i + 1)
                if contract:
                    detail.hourly_pay = contract.allowance_base if contract.is_hourly_pay else 0
                    detail.basic_price = contract.allowance_base
                    detail.min_hours = item['ITEM_MIN_HOURS']
                    detail.max_hours = item['ITEM_MAX_HOURS']
                detail.total_hours = item['ITEM_WORK_HOURS'] if item['ITEM_WORK_HOURS'] else 0
                detail.extra_hours = item['ITEM_EXTRA_HOURS'] if item['ITEM_EXTRA_HOURS'] else 0
                detail.rate = item['ITEM_RATE']
                detail.plus_per_hour = item['ITEM_PLUS_PER_HOUR']
                detail.minus_per_hour = item['ITEM_MINUS_PER_HOUR']
                detail.plus_amount = item['ITEM_PLUS_AMOUNT']
                detail.minus_amount = item['ITEM_MINUS_AMOUNT']
                detail.total_price = item['ITEM_AMOUNT_TOTAL']
                detail.expenses_price = item['ITEM_EXPENSES_TOTAL']
                detail.comment = item['ITEM_COMMENT']
                # detail = SubcontractorRequestDetail(
                #     subcontractor_request=self,
                #     project_member=project_member,
                #     member_section=project_member.member.get_section(date),
                #     member_type=4,
                #     salesperson=project_member.member.get_salesperson(date),
                #     subcontractor=contract.company,
                #     cost=0,
                #     no=str(i + 1),
                #     hourly_pay=contract.allowance_base if contract.is_hourly_pay else 0,
                #     basic_price=contract.allowance_base,
                #     min_hours=contract.allowance_time_min,
                #     max_hours=contract.allowance_time_max,
                #     total_hours=item['ITEM_WORK_HOURS'] if item['ITEM_WORK_HOURS'] else 0,
                #     extra_hours=item['ITEM_EXTRA_HOURS'] if item['ITEM_EXTRA_HOURS'] else 0,
                #     rate=item['ITEM_RATE'],
                #     plus_per_hour=contract.allowance_overtime,
                #     minus_per_hour=contract.allowance_absenteeism,
                #     total_price=item['ITEM_AMOUNT_TOTAL'],
                #     expenses_price=project_member.get_expenses_amount(ym[:4], int(ym[4:])),
                #     comment=item['ITEM_COMMENT']
                # )
                detail.save()


class SubcontractorRequestHeading(models.Model):
    subcontractor_request = models.OneToOneField(SubcontractorRequest, verbose_name=u"請求書")
    is_lump = models.BooleanField(default=False, verbose_name=u"一括フラグ")
    lump_amount = models.BigIntegerField(default=0, blank=True, null=True, verbose_name=u"一括金額")
    lump_comment = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"一括の備考")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    client = models.ForeignKey(Company, null=True, on_delete=models.PROTECT, verbose_name=u"関連会社")
    client_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"お客様郵便番号")
    client_address = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"お客様住所１")
    client_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様電話番号")
    client_fax = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様ファックス")
    client_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"お客様会社名")
    tax_rate = models.DecimalField(blank=True, null=True, max_digits=3, decimal_places=2, verbose_name=u"税率")
    decimal_type = models.CharField(blank=True, null=True, max_length=1, choices=constants.CHOICE_DECIMAL_TYPE,
                                    verbose_name=u"小数の処理区分")
    work_period_start = models.DateField(blank=True, null=True, verbose_name=u"作業期間＿開始")
    work_period_end = models.DateField(blank=True, null=True, verbose_name=u"作業期間＿終了")
    remit_date = models.DateField(blank=True, null=True, verbose_name=u"お支払い期限")
    publish_date = models.DateField(blank=True, null=True, verbose_name=u"発行日")
    created_date = models.DateField(blank=True, null=True, verbose_name=u"作成日")
    company_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"本社郵便番号")
    company_address = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所")
    company_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"会社名")
    company_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様電話番号")
    company_master = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"代表取締役")
    bank = models.ForeignKey(SubcontractorBankInfo, blank=True, null=True, on_delete=models.PROTECT,
                             verbose_name=u"口座")
    bank_name = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"銀行名称")
    branch_no = models.CharField(blank=True, null=True, max_length=7, verbose_name=u"支店番号")
    branch_name = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"支店名称")
    account_type = models.CharField(blank=True, null=True, max_length=1, choices=constants.CHOICE_ACCOUNT_TYPE,
                                    verbose_name=u"預金種類")
    account_number = models.CharField(blank=True, null=True, max_length=7, verbose_name=u"口座番号")
    account_holder = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"口座名義")

    class Meta:
        ordering = ['-subcontractor_request__request_no']
        verbose_name = verbose_name_plural = u"協力会社請求見出し"


class SubcontractorRequestDetail(models.Model):
    subcontractor_request = models.ForeignKey(SubcontractorRequest, on_delete=models.PROTECT, verbose_name=u"請求書")
    bp_member_order = models.ForeignKey('BpMemberOrder', null=True, on_delete=models.PROTECT, verbose_name=u"ＢＰ注文書")
    project_member = models.ForeignKey('ProjectMember', null=True, on_delete=models.PROTECT, verbose_name=u"メンバー")
    project = models.ForeignKey(Project, null=True, on_delete=models.PROTECT, verbose_name=u"一括案件")
    member_section = models.ForeignKey(Section, verbose_name=u"部署")
    member_type = models.IntegerField(default=4, choices=constants.CHOICE_MEMBER_TYPE, verbose_name=u"社員区分")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, on_delete=models.PROTECT,
                                    verbose_name=u"営業員")
    subcontractor = models.ForeignKey(Subcontractor, blank=True, null=True, on_delete=models.PROTECT,
                                      verbose_name=u"協力会社")
    salary = models.IntegerField(default=0, verbose_name=u"給料")
    cost = models.IntegerField(default=0, verbose_name=u"コスト")
    no = models.IntegerField(verbose_name=u"番号")
    hourly_pay = models.IntegerField(default=0, verbose_name=u"時給")
    basic_price = models.IntegerField(default=0, verbose_name=u"単価")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"基準時間")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"最大時間")
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"合計時間")
    extra_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"残業時間")
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=1, verbose_name=u"率")
    plus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"増（円）")
    minus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"減（円）")
    plus_amount = models.IntegerField(default=0, editable=False, verbose_name=u"超過金額")
    minus_amount = models.IntegerField(default=0, editable=False, verbose_name=u"控除金額")
    total_price = models.IntegerField(default=0, verbose_name=u"売上（基本単価＋残業料）（税抜き）")
    expenses_price = models.IntegerField(default=0, verbose_name=u"精算金額")
    comment = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"備考")

    class Meta:
        ordering = ['-subcontractor_request__request_no', 'no']
        unique_together = ('subcontractor_request', 'no')
        verbose_name = verbose_name_plural = u"協力会社請求明細"

    def __unicode__(self):
        f = u"%s %s%sの請求明細"
        return f % (self.project_member,
                    self.subcontractor_request.get_year_display(),
                    self.subcontractor_request.get_month_display())

    def get_tax_price(self):
        """税金を計算する。
        """
        if not hasattr(self.subcontractor_request, 'subcontractorrequestheading'):
            return 0

        tax_rate = self.subcontractor_request.subcontractorrequestheading.tax_rate
        # decimal_type = self.project_request.subcontractorrequestheading.decimal_type
        if tax_rate is None:
            return 0
        # if decimal_type == '0':
        #     # 四捨五入
        #     return int(round(self.total_price * tax_rate))
        # else:
        #     # 切り捨て
        #     return int(self.total_price * tax_rate)
        return round(self.total_price * tax_rate, 1)

    def get_all_price(self):
        """合計を計算する（税込、精算含む）
        """
        return int(self.total_price) + self.get_tax_price() + int(self.expenses_price)


class ExpensesCategory(BaseModel):
    name = models.CharField(max_length=50, unique=True, verbose_name=u"名称")

    class Meta:
        verbose_name = verbose_name_plural = u"精算分類"
        db_table = 'mst_expenses_category'

    def __unicode__(self):
        return self.name


class EmployeeExpenses(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    advance_amount = models.IntegerField(default=0, verbose_name=u"管理職立替金額")

    class Meta:
        unique_together = ('member', 'year', 'month')
        verbose_name = verbose_name_plural = u"社員精算リスト"

    def __unicode__(self):
        return u"%s %s %s" % (self.member, self.get_year_display(), self.get_month_display())


class SubcontractorMemberExpenses(BaseModel):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.PROTECT, verbose_name=u"要員")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    category = models.ForeignKey(ExpensesCategory, on_delete=models.PROTECT, verbose_name=u"分類")
    price = models.IntegerField(default=0, verbose_name=u"金額")

    objects = PublicManager(is_deleted=False, project_member__is_deleted=False, category__is_deleted=False)

    class Meta:
        ordering = ['project_member', 'year', 'month']
        verbose_name = verbose_name_plural = u"協力会社精算リスト"

    def __unicode__(self):
        return u"%s %s %s" % (self.project_member, self.get_year_display(), self.get_month_display())


class MemberExpenses(BaseModel):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.PROTECT, verbose_name=u"要員")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    category = models.ForeignKey(ExpensesCategory, on_delete=models.PROTECT, verbose_name=u"分類")
    price = models.IntegerField(default=0, verbose_name=u"金額")

    objects = PublicManager(is_deleted=False, project_member__is_deleted=False, category__is_deleted=False)

    class Meta:
        ordering = ['project_member', 'year', 'month']
        verbose_name = verbose_name_plural = u"取引先精算リスト"

    def __unicode__(self):
        return u"%s %s %s" % (self.project_member, self.get_year_display(), self.get_month_display())


class MemberAttendance(BaseModel):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.PROTECT, verbose_name=u"メンバー")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=1, verbose_name=u"率")
    salary = models.IntegerField(default=0, editable=False, verbose_name=u"給料")
    cost = models.IntegerField(default=0, editable=False, verbose_name=u"コスト",
                               help_text=u"交通費、残業、保険など含む")
    basic_price = models.IntegerField(default=0, editable=False, verbose_name=u"単価")
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=u"合計時間")
    total_hours_bp = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=u"ＢＰ作業時間")
    extra_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=u"残業時間")
    total_days = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"勤務日数")
    night_days = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"深夜日数")
    advances_paid = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"立替金")
    advances_paid_client = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"客先立替金")
    traffic_cost = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"勤務交通費",
                                       help_text=u"今月に勤務交通費がない場合、先月のを使用する。")
    allowance = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"手当",
                                    help_text=u"今月に手当がない場合、先月のを使用する。")
    expenses = models.IntegerField(blank=True, null=True, editable=False, verbose_name=u"経費")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False, verbose_name=u"基準時間")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False, verbose_name=u"最大時間")
    plus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"増（円）")
    minus_per_hour = models.IntegerField(default=0, editable=False, verbose_name=u"減（円）")
    price = models.IntegerField(default=0, verbose_name=u"価格")
    expect_price = models.IntegerField(blank=True, null=True, verbose_name=u"請求金額")
    comment = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"備考")
    # 経費（原価ではない、営業コストとする）
    expenses_conference = models.IntegerField(default=0, verbose_name=u"会議費")
    expenses_entertainment = models.IntegerField(default=0, verbose_name=u"交際費")
    expenses_travel = models.IntegerField(default=0, verbose_name=u"旅費交通費")
    expenses_communication = models.IntegerField(default=0, verbose_name=u"通信費")
    expenses_tax_dues = models.IntegerField(default=0, verbose_name=u"租税公課")
    expenses_expendables = models.IntegerField(default=0, verbose_name=u"消耗品")

    objects = PublicManager(is_deleted=False, project_member__is_deleted=False)

    class Meta:
        ordering = ['project_member', 'year', 'month']
        unique_together = ('project_member', 'year', 'month')
        verbose_name = verbose_name_plural = u"勤務時間"
        permissions = (
            ('input_attendance', u'勤怠入力'),
        )

    def __unicode__(self):
        return u"%s %s %s" % (self.project_member, self.get_year_display(), self.get_month_display())

    def get_night_allowance(self):
        """深夜手当を取得する

        :return:
        """
        contract = self.get_contract()
        if self.night_days and self.night_days > 0:
            if contract and contract.member_type in (1, 2):
                return int(self.night_days) * 3000
            else:
                return 0
        else:
            return 0

    def get_contract(self):
        date = datetime.datetime(int(self.year), int(self.month), 1, tzinfo=common.get_tz_utc())
        return self.project_member.member.get_contract(date)

    def get_total_hours_cost(self):
        """コスト算出時、社内は30分ごとに計算されている。

        規定としては30分ですが、システム設定では変更できます。

        :return:
        """
        attendance_type = Config.get_bp_attendance_type()
        total_hours = self.total_hours_bp if self.total_hours_bp else self.total_hours
        return common.get_attendance_total_hours(total_hours, attendance_type)

    def get_cost(self):
        """コストを取得する

        :return:
        """
        contract = self.get_contract()
        if contract:
            if contract.is_hourly_pay:
                return int(contract.get_cost() * self.get_total_hours_cost() + contract.allowance_other)
            else:
                return contract.get_cost()
        return 0

    @classmethod
    def get_bonus(cls):
        """ボーナスを取得する。

        正社員の場合はボーナスある。

        :return:
        """
        return 0

    def get_overtime(self, contract=None):
        if contract is None:
            contract = self.get_contract()
        if contract:
            total_hours = self.get_total_hours_cost()
            if contract.allowance_time_min <= total_hours <= contract.allowance_time_max:
                return 0
            elif contract.is_fixed_cost or contract.is_hourly_pay:
                return 0
            elif self.project_member.project.is_reserve:
                # 待機案件の場合、残業と欠勤を計算する必要がない。
                return 0
            elif total_hours > contract.allowance_time_max:
                overtime = total_hours - float(contract.allowance_time_max)
                return overtime
            else:
                absenteeism = total_hours - float(contract.allowance_time_min)
                return absenteeism
        else:
            return 0

    def get_overtime_cost(self, allowance_time_min=None):
        """残業／控除の金額を取得する

        :return:
        """
        contract = self.get_contract()
        if contract:
            if contract.is_fixed_cost:
                return 0
            if allowance_time_min is None:
                allowance_time_min = contract.allowance_time_min
            total_hours = self.get_total_hours_cost()
            if allowance_time_min <= total_hours <= contract.allowance_time_max:
                return 0
            elif self.project_member.project.is_reserve:
                # 待機案件の場合、残業と欠勤を計算する必要がない。
                return 0
            elif total_hours > contract.allowance_time_max:
                overtime = total_hours - float(contract.allowance_time_max)
                return int(overtime * contract.allowance_overtime)
            else:
                absenteeism = round(total_hours - float(allowance_time_min), 2)
                return int(absenteeism * contract.allowance_absenteeism)
        else:
            return 0

    def get_employment_insurance(self):
        """雇用保険を取得する

        :return:
        """
        if self.project_member.member.member_type in (1, 2):
            # 正社員、契約社員の場合
            cost = float(self.get_cost())
            bonus = float(self.get_bonus())
            allowance = float(self.allowance) if self.allowance else 0
            night_allowance = float(self.get_night_allowance())
            overtime_cost = self.get_overtime_cost()
            traffic_cost = float(self.traffic_cost) if self.traffic_cost else 0
            return int((cost + bonus + allowance + night_allowance + overtime_cost + traffic_cost) * 0.01)
        else:
            return 0

    def get_health_insurance(self):
        """健康保険を取得する

        :return:
        """
        contract = self.get_contract()
        if contract and hasattr(contract, 'endowment_insurance') \
                and contract.endowment_insurance == "1" and contract.member_type != 4:
            # 契約情報保険加入した場合
            cost = float(self.get_cost())
            bonus = float(self.get_bonus())
            allowance = float(self.allowance) if self.allowance else 0
            night_allowance = float(self.get_night_allowance())
            overtime_cost = self.get_overtime_cost()
            traffic_cost = float(self.traffic_cost) if self.traffic_cost else 0
            return int((cost + bonus + allowance + night_allowance + overtime_cost + traffic_cost) * 0.14)
        else:
            return 0

    def get_all_cost(self):
        """原価合計を取得する

        原価合計 = 月給 + 手当 + 深夜手当 + 残業／控除 + 交通費 + 経費 + 雇用／労災 + 健康／厚生

        :return:
        """
        return sum((self.get_cost(),
                    int(self.allowance) if self.allowance else 0,
                    self.get_night_allowance(),
                    self.get_overtime_cost(),
                    int(self.traffic_cost) if self.traffic_cost else 0,
                    int(self.expenses) if self.expenses else 0,
                    self.get_employment_insurance(),
                    self.get_health_insurance()))

    def get_profits(self):
        """利益を取得する

        税抜きの売上 - 原価合計

        :return:
        """
        request_detail = self.get_project_request_detail()
        if request_detail:
            total_price = request_detail.total_price
            return total_price - self.get_all_cost()
        elif self.project_member.project.is_lump:
            return self.project_member.project.lump_amount - self.get_all_cost()
        elif self.project_member.project.is_reserve:
            return 0 - self.get_all_cost()
        else:
            return None

    def get_prev_attendance(self):
        """先月の出勤情報を取得する。

        :return:
        """
        prev_month = common.add_months(datetime.date(int(self.year), int(self.month), 1), -1)
        try:
            member_attendance = MemberAttendance.objects.get(project_member=self.project_member,
                                                             year="%04d" % prev_month.year,
                                                             month="%02d" % prev_month.month)
            return member_attendance
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            return None

    def get_prev_traffic_cost(self):
        """先月の勤務交通費を取得する。

        :return:
        """
        attendance = self.get_prev_attendance()
        return attendance.traffic_cost if attendance else None

    def get_prev_allowance(self):
        """先月の手当を取得する。

        :return:
        """
        attendance = self.get_prev_attendance()
        return attendance.allowance if attendance else None

    def get_project_request_detail(self):
        """メンバーの出勤情報によて、案件の請求情報を取得する。

        :return: ProjectRequestDetailのQueryset
        """
        try:
            return ProjectRequestDetail.objects.get(project_member=self.project_member,
                                                    project_request__year=self.year,
                                                    project_request__month=self.month)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            return None

    def get_lump_project_request(self):
        """一括案件の請求情報を取得する

        経営データ統計表の売上を表示するために使われている。

        :return:
        """
        if self.project_member.project.is_lump:
            try:
                project_request = ProjectRequest.objects.get(
                    project=self.project_member.project,
                    year=self.year,
                    month=self.month
                )
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                project_request = None
            return project_request
        else:
            return None

    def get_bp_expenses_amount(self):
        expense = SubcontractorMemberExpenses.objects.public_filter(project_member=self.project_member,
                                                                    year=self.year,
                                                                    month=self.month,
                                                                    is_deleted=False).aggregate(price=Sum('price'))
        return expense.get('price') if expense.get('price') else 0

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.pk is None:
            self.basic_price = self.project_member.price
            self.min_hours = self.project_member.min_hours
            self.max_hours = self.project_member.max_hours
            self.plus_per_hour = self.project_member.plus_per_hour
            self.minus_per_hour = self.project_member.minus_per_hour
        super(MemberAttendance, self).save(force_insert, force_update, using, update_fields)


class BpLumpOrder(BaseModel):
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"協力会社")
    contract = models.OneToOneField('contract.BpLumpContract', on_delete=models.PROTECT, verbose_name=u"契約")
    order_no = models.CharField(max_length=14, unique=True, verbose_name=u"注文番号")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    amount = models.IntegerField(default=0, verbose_name=u"契約金額")
    tax_amount = models.IntegerField(default=0, verbose_name=u"消費税")
    total_amount = models.IntegerField(default=0, verbose_name=u"合計額")
    filename = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文書ファイル名")
    filename_request = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文請書")
    is_sent = models.BooleanField(default=False, verbose_name=u"送信")
    created_user = models.ForeignKey(User, related_name='created_lump_orders', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"作成者")
    updated_user = models.ForeignKey(User, related_name='updated_lump_orders', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"更新者")

    class Meta:
        verbose_name = verbose_name_plural = u"ＢＰ一括註文書"

    def __unicode__(self):
        return u"%s(%s)" % (unicode(self.subcontractor), self.order_no)

    @classmethod
    def get_next_bp_order(cls, contract, user, publish_date=None):
        salesperson = None
        if publish_date is None:
            publish_date = datetime.date.today()
        elif isinstance(publish_date, basestring):
            publish_date = datetime.datetime.strptime(publish_date, '%Y/%m/%d').date()
        if hasattr(user, 'salesperson'):
            salesperson = user.salesperson
        elif hasattr(user, 'member'):
            salesperson = user.member
        lump_order = BpLumpOrder(
            subcontractor=contract.company,
            contract=contract,
            order_no=BpLumpOrder.get_next_order_no(salesperson, publish_date),
            year='%04d' % publish_date.year,
            month='%02d' % publish_date.month,
            amount=contract.allowance_base,
            tax_amount=contract.allowance_base_tax,
            total_amount=contract.allowance_base_total,
        )
        return lump_order

    @classmethod
    def get_next_order_no(cls, member, publish_date=None):
        """注文番号を取得する。

        :param member:
        :param publish_date:
        :return:
        """
        prefix = '-'
        date = publish_date if publish_date else datetime.date.today()
        if member and member.first_name_en:
            prefix = member.first_name_en[0].upper()

        order_no = "WT{0:04d}{1:02d}{2:02d}{3}".format(date.year, date.month, date.day, prefix)
        max_order_no = BpLumpOrder.objects.public_filter(order_no__startswith=order_no) \
            .aggregate(Max('order_no'))
        max_order_no = max_order_no.get('order_no__max')
        if max_order_no:
            index = int(max_order_no[-2:]) + 1
        else:
            index = 1
        return "{0}{1:02d}".format(order_no, index)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, data=None, is_request=False):
        super(BpLumpOrder, self).save(force_insert, force_update, using, update_fields)
        # 注文書作成時、注文に関する全ての情報を履歴として保存する。
        if data:
            # 既存のデータを全部消す。
            if hasattr(self, 'bplumporderheading'):
                self.bplumporderheading.delete()
            heading = BpLumpOrderHeading(bp_order=self,
                                         publish_date=data['DETAIL'].get('PUBLISH_DATE', None),
                                         subcontractor_name=data['DETAIL'].get('SUBCONTRACTOR_NAME', None),
                                         subcontractor_post_code=data['DETAIL'].get('SUBCONTRACTOR_POST_CODE', None),
                                         subcontractor_address1=data['DETAIL'].get('SUBCONTRACTOR_ADDRESS1', None),
                                         subcontractor_address2=data['DETAIL'].get('SUBCONTRACTOR_ADDRESS2', None),
                                         subcontractor_tel=data['DETAIL'].get('SUBCONTRACTOR_TEL', None),
                                         subcontractor_fax=data['DETAIL'].get('SUBCONTRACTOR_FAX', None),
                                         company_address1=data['DETAIL'].get('ADDRESS1', None),
                                         company_address2=data['DETAIL'].get('ADDRESS2', None),
                                         company_name=data['DETAIL'].get('COMPANY_NAME', None),
                                         company_tel=data['DETAIL'].get('TEL', None),
                                         company_fax=data['DETAIL'].get('FAX', None),
                                         project_name=data['DETAIL'].get('PROJECT_NAME', None),
                                         start_date=data['DETAIL'].get('START_DATE', None),
                                         end_date=data['DETAIL'].get('END_DATE', None),
                                         delivery_date=data['DETAIL'].get('DELIVERY_DATE', None),
                                         project_content=data['DETAIL'].get('PROJECT_CONTENT', None),
                                         workload=data['DETAIL'].get('WORKLOAD', None),
                                         project_result=data['DETAIL'].get('PROJECT_RESULT', None),
                                         allowance_base=data['DETAIL'].get('ALLOWANCE_BASE', None),
                                         allowance_base_tax=data['DETAIL'].get('ALLOWANCE_BASE_TAX', None),
                                         allowance_base_total=data['DETAIL'].get('ALLOWANCE_BASE_TOTAL', None),
                                         comment=data['DETAIL'].get('COMMENT', None),
                                         )
            heading.save()


class BpLumpOrderHeading(models.Model):
    bp_order = models.OneToOneField(BpLumpOrder, verbose_name=u"ＢＰ注文書")
    publish_date = models.CharField(max_length=200, verbose_name=u"発行年月日")
    subcontractor_name = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"下請け会社名")
    subcontractor_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"協力会社郵便番号")
    subcontractor_address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"協力会社住所１")
    subcontractor_address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"協力会社住所２")
    subcontractor_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"協力会社電話番号")
    subcontractor_fax = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"協力会社ファックス")
    company_address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所１")
    company_address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所２")
    company_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"会社名")
    company_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"会社電話番号")
    company_fax = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"会社ファックス")
    project_name = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"業務名称")
    start_date = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"作業開始日")
    end_date = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"作業終了日")
    delivery_date = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"納品日")
    project_content = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"作業内容")
    workload = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"作業量")
    project_result = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"納入成果品")
    allowance_base = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"契約金額")
    allowance_base_tax = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"消費税")
    allowance_base_total = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"合計額")
    comment = models.TextField(blank=True, null=True, verbose_name=u"備考")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        verbose_name = verbose_name_plural = u"ＢＰ一括註文書見出し"

    def __unicode__(self):
        return unicode(self.bp_order)


class BpMemberOrder(BaseModel):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.PROTECT, verbose_name=u"案件メンバー")
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"協力会社")
    order_no = models.CharField(max_length=14, unique=True, verbose_name=u"注文番号")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"開始年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"開始月")
    end_year = models.CharField(max_length=4, blank=False, null=True,
                                choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"終了年")
    end_month = models.CharField(max_length=2, blank=False, null=True, verbose_name=u"終了月")
    business_days = models.IntegerField(default=0, verbose_name=u"営業日数")
    filename = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文書ファイル名")
    filename_pdf = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文書ＰＤＦ名")
    filename_request = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文請書")
    filename_request_pdf = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"注文請書ＰＤＦ")
    is_sent = models.BooleanField(default=False, verbose_name=u"送信")
    created_user = models.ForeignKey(User, related_name='created_orders', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"作成者")
    updated_user = models.ForeignKey(User, related_name='updated_orders', null=True, on_delete=models.PROTECT,
                                     editable=False, verbose_name=u"更新者")

    class Meta:
        unique_together = ('project_member', 'year', 'month')
        verbose_name = verbose_name_plural = u"ＢＰ註文書"

    def __unicode__(self):
        return u"%s(%s)" % (unicode(self.project_member.member), self.order_no)

    @classmethod
    def get_next_bp_order(cls, subcontractor, project_member, year, month,
                          publish_date=None, end_year=None, end_month=None):
        """指定メンバー、年月によって、注文情報を取得する。

        :param subcontractor:
        :param project_member:
        :param year:
        :param month:
        :param publish_date:
        :param end_year:
        :param end_month:
        :return:
        """
        try:
            order = BpMemberOrder.objects.annotate(
                ym_start=Concat('year', 'month', output_field=models.CharField()),
                ym_end=Concat('end_year', 'end_month', output_field=models.CharField()),
            ).get(project_member=project_member,
                  ym_start__lte='%04d%02d' % (int(year), int(month)),
                  ym_end__gte='%04d%02d' % (int(year), int(month)))
        except ObjectDoesNotExist:
            if not end_year or not end_month:
                end_year = year
                end_month = month
            salesperson = project_member.member.get_salesperson(datetime.date(int(year), int(month), 20))
            order = BpMemberOrder(project_member=project_member,
                                  subcontractor=subcontractor,
                                  order_no=BpMemberOrder.get_next_order_no(salesperson, year, month, publish_date),
                                  year=year,
                                  month="%02d" % int(month),
                                  end_year='%04d' % int(end_year),
                                  end_month='%02d' % int(end_month))
        return order

    @classmethod
    def get_next_order_no(cls, member, year=None, month=None, publish_date=None):
        """注文番号を取得する。

        :param member ログインしているユーザ
        :param year:
        :param month
        :param publish_date:
        """
        prefix = '-'
        date = datetime.date.today()
        if year and month:
            date = common.get_bp_order_publish_date(year, month, publish_date)
        if member and member.first_name_en:
            prefix = member.first_name_en[0].upper()

        order_no = "WT{0:04d}{1:02d}{2:02d}{3}".format(date.year, date.month, date.day, prefix)
        max_order_no = BpMemberOrder.objects.public_filter(order_no__startswith=order_no)\
            .aggregate(Max('order_no'))
        max_order_no = max_order_no.get('order_no__max')
        if max_order_no:
            index = int(max_order_no[-2:]) + 1
        else:
            index = 1
        return "{0}{1:02d}".format(order_no, index)

    def get_order_path(self):
        if self.filename:
            return os.path.join(settings.GENERATED_FILES_ROOT, "partner_order", '%s%s' % (self.year, self.month), self.filename_pdf)
        else:
            return None

    def get_order_request_path(self):
        if self.filename_request:
            return os.path.join(settings.GENERATED_FILES_ROOT, "partner_order", '%s%s' % (self.year, self.month), self.filename_request_pdf)
        else:
            return None

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, data=None, is_request=False):
        super(BpMemberOrder, self).save(force_insert, force_update, using, update_fields)
        # 注文書作成時、注文に関する全ての情報を履歴として保存する。
        if data:
            # 既存のデータを全部消す。
            if hasattr(self, 'bpmemberorderheading'):
                self.bpmemberorderheading.delete()
            heading = BpMemberOrderHeading(bp_order=self,
                                           publish_date=data['DETAIL'].get('PUBLISH_DATE', None),
                                           subcontractor_name=data['DETAIL'].get('SUBCONTRACTOR_NAME', None),
                                           subcontractor_post_code=data['DETAIL'].get('SUBCONTRACTOR_POST_CODE', None),
                                           subcontractor_address1=data['DETAIL'].get('SUBCONTRACTOR_ADDRESS1', None),
                                           subcontractor_address2=data['DETAIL'].get('SUBCONTRACTOR_ADDRESS2', None),
                                           subcontractor_tel=data['DETAIL'].get('SUBCONTRACTOR_TEL', None),
                                           subcontractor_fax=data['DETAIL'].get('SUBCONTRACTOR_FAX', None),
                                           company_address1=data['DETAIL'].get('ADDRESS1', None),
                                           company_address2=data['DETAIL'].get('ADDRESS2', None),
                                           company_name=data['DETAIL'].get('COMPANY_NAME', None),
                                           company_tel=data['DETAIL'].get('TEL', None),
                                           company_fax=data['DETAIL'].get('FAX', None),
                                           project_name=data['DETAIL'].get('PROJECT_NAME', None),
                                           start_date=data['DETAIL'].get('START_DATE', None),
                                           end_date=data['DETAIL'].get('END_DATE', None),
                                           master=data['DETAIL'].get('MASTER', None),
                                           middleman=data['DETAIL'].get('MIDDLEMAN', None),
                                           subcontractor_master=data['DETAIL'].get('SUBCONTRACTOR_MASTER', None),
                                           subcontractor_middleman=data['DETAIL'].get('SUBCONTRACTOR_MIDDLEMAN', None),
                                           member_name=data['DETAIL'].get('MEMBER_NAME', None),
                                           location=data['DETAIL'].get('LOCATION', None),
                                           is_hourly_pay=data['DETAIL'].get('IS_HOURLY_PAY', False),
                                           is_fixed_cost=data['DETAIL'].get('IS_FIXED_COST', False),
                                           is_show_formula=data['DETAIL'].get('IS_SHOW_FORMULA', False),
                                           calculate_type_comment=data['DETAIL'].get('CALCULATE_TYPE_COMMENT', None),
                                           allowance_base=data['DETAIL'].get('ALLOWANCE_BASE', None),
                                           allowance_base_memo=data['DETAIL'].get('ALLOWANCE_BASE_MEMO', None),
                                           allowance_time_min=data['DETAIL'].get('ALLOWANCE_TIME_MIN', None),
                                           allowance_time_max=data['DETAIL'].get('ALLOWANCE_TIME_MAX', None),
                                           allowance_time_memo=data['DETAIL'].get('ALLOWANCE_TIME_MEMO', None),
                                           allowance_overtime=data['DETAIL'].get('ALLOWANCE_OVERTIME', None),
                                           allowance_overtime_memo=data['DETAIL'].get('ALLOWANCE_OVERTIME_MEMO', None),
                                           allowance_absenteeism=data['DETAIL'].get('ALLOWANCE_ABSENTEEISM', None),
                                           allowance_absenteeism_memo=data['DETAIL'].get('ALLOWANCE_ABSENTEEISM_MEMO',
                                                                                         None),
                                           allowance_other=data['DETAIL'].get('ALLOWANCE_OTHER', None),
                                           allowance_other_memo=data['DETAIL'].get('ALLOWANCE_OTHER_MEMO', None),
                                           comment=data['DETAIL'].get('COMMENT', None),
                                           delivery_properties_comment=data['DETAIL'].get('DELIVERY_PROPERTIES', None),
                                           payment_condition_comments=data['DETAIL'].get('PAYMENT_CONDITION', None),
                                           contract_items_comments=data['DETAIL'].get('CONTRACT_ITEMS', None),
                                           )
            heading.save()


class BpMemberOrderHeading(models.Model):
    bp_order = models.OneToOneField(BpMemberOrder, verbose_name=u"ＢＰ注文書")
    publish_date = models.CharField(max_length=200, verbose_name=u"発行年月日")
    subcontractor_name = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"下請け会社名")
    subcontractor_post_code = models.CharField(blank=True, null=True, max_length=8, verbose_name=u"協力会社郵便番号")
    subcontractor_address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"協力会社住所１")
    subcontractor_address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"協力会社住所２")
    subcontractor_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"協力会社電話番号")
    subcontractor_fax = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"協力会社ファックス")
    company_address1 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所１")
    company_address2 = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"本社住所２")
    company_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"会社名")
    company_tel = models.CharField(blank=True, null=True, max_length=15, verbose_name=u"お客様電話番号")
    company_fax = models.CharField(blank=True, null=True, max_length=15, verbose_name="会社ファックス")
    project_name = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"業務名称")
    start_date = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"作業開始日")
    end_date = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"作業終了日")
    master = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"委託業務責任者（甲）")
    middleman = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"連絡窓口担当者（甲）")
    subcontractor_master = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"委託業務責任者（乙）")
    subcontractor_middleman = models.CharField(blank=True, null=True, max_length=30,
                                               verbose_name=u"連絡窓口担当者（乙）")
    member_name = models.CharField(blank=True, null=True, max_length=30, verbose_name=u"作業責任者")
    location = models.CharField(blank=True, null=True, max_length=200, verbose_name=u"作業場所")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    is_fixed_cost = models.BooleanField(default=False, verbose_name=u"固定")
    is_show_formula = models.BooleanField(default=True, verbose_name=u"計算式")
    calculate_type_comment = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"変動基準時間方式の説明")
    allowance_base = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"基本給")
    allowance_base_memo = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"基本給メモ")
    allowance_time_min = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"時間下限")
    allowance_time_max = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"時間上限")
    allowance_time_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"基準時間メモ")
    allowance_overtime = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"残業手当")
    allowance_overtime_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"残業手当メモ")
    allowance_absenteeism = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"欠勤手当")
    allowance_absenteeism_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"欠勤手当メモ")
    allowance_other = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"その他手当")
    allowance_other_memo = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"その他手当メモ")
    comment = models.TextField(blank=True, null=True, verbose_name=u"備考")
    delivery_properties_comment = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"納入物件")
    payment_condition_comments = models.TextField(blank=True, null=True, verbose_name=u"支払条件")
    contract_items_comments = models.TextField(blank=True, null=True, verbose_name=u"契約条項")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        verbose_name = verbose_name_plural = u"ＢＰ註文書見出し"

    def __unicode__(self):
        return unicode(self.bp_order)


class BpMemberOrderInfo(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"協力社員")
    year = models.CharField(max_length=4, default=str(datetime.date.today().year),
                            choices=constants.CHOICE_ATTENDANCE_YEAR, verbose_name=u"対象年")
    month = models.CharField(max_length=2, choices=constants.CHOICE_ATTENDANCE_MONTH, verbose_name=u"対象月")
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=160, verbose_name=u"基準時間")
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, default=180, verbose_name=u"最大時間")
    plus_per_hour = models.IntegerField(default=0, verbose_name=u"増（円）")
    minus_per_hour = models.IntegerField(default=0, verbose_name=u"減（円）")
    cost = models.IntegerField(null=False, default=0, verbose_name=u"コスト")
    comment = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"備考")

    class Meta:
        ordering = ['member', 'year', 'month']
        unique_together = ('member', 'year', 'month')
        verbose_name = verbose_name_plural = u"協力社員の注文情報"

    def __unicode__(self):
        return u"%s_%s(%s/%s)" % (unicode(self.member), unicode(self.member.subcontractor), self.year, self.month)


class Degree(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"社員")
    start_date = models.DateField(verbose_name=u"入学日")
    end_date = models.DateField(verbose_name=u"卒業日")
    description = models.CharField(blank=True, null=True, max_length=255, verbose_name=u"学校名称/学部/専門/学位")

    class Meta:
        verbose_name = verbose_name_plural = u"学歴"


class HistoryProject(BaseModel):
    name = models.CharField(max_length=50, verbose_name=u"案件名称")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=u"名前")
    location = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"作業場所")
    description = models.TextField(blank=True, null=True, verbose_name=u"案件概要")
    start_date = models.DateField(blank=True, null=True, verbose_name=u"開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日")
    os = models.ManyToManyField(OS, blank=True, verbose_name=u"機種／OS")
    skill = models.ManyToManyField(Skill, blank=True, verbose_name=u"スキル要求")
    role = models.CharField(default="PG", max_length=2, choices=constants.CHOICE_PROJECT_ROLE, verbose_name=u"作業区分")
    stages = models.ManyToManyField(ProjectStage, blank=True, verbose_name=u"作業工程")

    class Meta:
        ordering = ['-start_date']
        verbose_name = verbose_name_plural = u"以前やっていた案件"

    def __unicode__(self):
        return "%s - %s %s" % (self.name, self.member.first_name, self.member.last_name)

    def is_in_rd(self):
        if self.stages.public_filter(name=u"要件定義").count() > 0:
            return True
        else:
            return False

    def is_in_sa(self):
        if self.stages.public_filter(name=u"調査分析").count() > 0:
            return True
        else:
            return False

    def is_in_bd(self):
        if self.stages.public_filter(name=u"基本設計").count() > 0:
            return True
        else:
            return False

    def is_in_dd(self):
        if self.stages.public_filter(name=u"詳細設計").count() > 0:
            return True
        else:
            return False

    def is_in_pg(self):
        if self.stages.public_filter(name=u"開発製造").count() > 0:
            return True
        else:
            return False

    def is_in_pt(self):
        if self.stages.public_filter(name=u"単体試験").count() > 0:
            return True
        else:
            return False

    def is_in_it(self):
        if self.stages.public_filter(name=u"結合試験").count() > 0:
            return True
        else:
            return False

    def is_in_st(self):
        if self.stages.public_filter(name=u"総合試験").count() > 0:
            return True
        else:
            return False

    def is_in_maintain(self):
        if self.stages.public_filter(name=u"保守運用").count() > 0:
            return True
        else:
            return False

    def is_in_support(self):
        if self.stages.public_filter(name=u"サポート").count() > 0:
            return True
        else:
            return False


class Issue(BaseModel):
    title = models.CharField(max_length=30, verbose_name=u"タイトル")
    level = models.PositiveSmallIntegerField(choices=constants.CHOICE_ISSUE_LEVEL, default=1, verbose_name=u"優先度")
    content = models.TextField(verbose_name=u"内容")
    created_user = models.ForeignKey(User, related_name='created_issue_set', editable=False,
                                     on_delete=models.PROTECT, verbose_name=u"作成者")
    present_user = models.ForeignKey(User, blank=False, null=True, related_name='present_issue_set',
                                     on_delete=models.PROTECT,
                                     verbose_name=u"提出者")
    observer = models.ManyToManyField(User, blank=True, verbose_name=u"観察者",
                                      help_text=u"ここで選択されたユーザーに対して、"
                                                u"課題に変更があったら自動的メールを送信します。")
    status = models.CharField(max_length=1, default=1, choices=constants.CHOICE_ISSUE_STATUS,
                              verbose_name=u"ステータス")
    limit_date = models.DateField(blank=True, null=True, verbose_name=u"期限日")
    resolve_user = models.ForeignKey(User, related_name='resolve_issue_set', blank=False, null=True,
                                     on_delete=models.PROTECT,
                                     verbose_name=u"担当者")
    planned_end_date = models.DateField(blank=True, null=True, verbose_name=u"予定完了日")
    really_end_date = models.DateField(blank=True, null=True, verbose_name=u"実際完了日")
    solution = models.TextField(blank=True, null=True, verbose_name=u"対応方法")

    class Meta:
        ordering = ['-id']
        verbose_name = verbose_name_plural = u"課題管理表"

    def __unicode__(self):
        return self.title

    def get_mail_title(self):
        return u"【営業支援システム】[課題管理] #%d: %s - %s" % (self.pk, self.title, self.get_status_display())

    def get_mail_body(self, updated_user):
        """課題のメール本文を取得する。

        :param updated_user:
        :return:
        """
        mail_body = Config.get(constants.CONFIG_ISSUE_MAIL_BODY)
        if mail_body:
            t = Template(mail_body)
            context = {'issue': self,
                       'updated_user': updated_user,
                       'domain': Config.get(constants.CONFIG_DOMAIN_NAME),
                       }
            ctx = Context(context)
            return t.render(ctx)
        else:
            return None

    def get_cc_list(self):
        # システム管理者を取得する
        users = User.objects.filter(is_superuser=True, is_active=True)
        mail_list = [user.email for user in users if user.email]
        # 担当者をメールリストに追加
        if self.resolve_user and self.resolve_user.email not in mail_list:
            mail_list.append(self.resolve_user.email)
        for observer in self.observer.all():
            if observer.email not in mail_list:
                mail_list.append(observer.email)
        return mail_list

    def send_mail(self, updated_user):
        # メール送信
        html = self.get_mail_body(updated_user)
        if not html:
            # メール本文が設定されてないなら、送信を行わずに処理を終了する。
            return
        attachments = []
        from_email = Config.get(constants.CONFIG_ADMIN_EMAIL_ADDRESS)
        recipient_list = [updated_user.email]
        cc_list = self.get_cc_list()
        mail_connection = BatchManage.get_custom_connection()
        email = EmailMultiAlternativesWithEncoding(
            subject=self.get_mail_title(),
            body="",
            from_email=from_email,
            to=recipient_list,
            cc=cc_list,
            connection=mail_connection
        )
        if html:
            email.attach_alternative(html, constants.MIME_TYPE_HTML)
        if attachments:
            for filename, content, mimetype in attachments:
                email.attach(filename, content, mimetype)
        email.send()


class History(BaseModel):
    start_datetime = models.DateTimeField(default=timezone.now, verbose_name=u"開始日時")
    end_datetime = models.DateTimeField(default=timezone.now, verbose_name=u"終了日時")
    location = models.CharField(max_length=2, choices=constants.CHOICE_DEV_LOCATION, verbose_name=u"作業場所")
    description = models.TextField(verbose_name=u"詳細")

    class Meta:
        ordering = ['-start_datetime']
        verbose_name = verbose_name_plural = u"開発履歴"

    def get_hours(self):
        td = self.end_datetime - self.start_datetime
        hours = td.seconds / 3600.0
        return round(hours, 1)


class BatchManage(BaseModel):
    name = models.CharField(max_length=50, unique=True, verbose_name=u"バッチＩＤ")
    title = models.CharField(max_length=50, verbose_name=u"バッチタイトル")
    cron_tab = models.CharField(blank=True, null=True, max_length=100, verbose_name=u"バッチの実行タイミング")
    is_active = models.BooleanField(default=True, verbose_name=u"有効フラグ")
    mail_template = models.ForeignKey(MailTemplate, blank=True, null=True, verbose_name=u"メールテンプレート")
    is_send_to_boss = models.BooleanField(default=True, verbose_name=u"上司に送る")
    is_send_to_self = models.BooleanField(default=True, verbose_name=u"自分に送る")
    description = models.TextField(blank=True, null=True, verbose_name=u"説明")

    class Meta:
        verbose_name = verbose_name_plural = u"バッチ管理"

    def __unicode__(self):
        return self.title

    def get_logger(self):
        return logging.getLogger('eb.management.commands.%s' % (self.name,))

    @classmethod
    def get_log_entry_user(cls, username='batch'):
        """ログエントリーにログを記録するにはログインユーザが必要

        :return:
        """
        try:
            user = User.objects.get(username=username)
            return user
        except ObjectDoesNotExist:
            try:
                user = User.objects.get(username='admin')
                return user
            except ObjectDoesNotExist:
                return None

    def get_formatted_batch(self, context):
        """フォーマット後のバッチを返す

        メールタイトルに日付追加とか、メール本文にパラメーターなどを設定する。

        :param context:
        :return:
        """
        if self.mail_template:
            today = datetime.datetime.now()
            # FROM
            from_email = Config.get(constants.CONFIG_ADMIN_EMAIL_ADDRESS)
            title = self.mail_template.mail_title + today.strftime(u"_%y%m%d")
            # BODY
            t = Template(self.mail_template.mail_body)
            ctx = Context(context)
            body = t.render(ctx)
            # HTML
            t = Template(self.mail_template.mail_html)
            ctx = Context(context)
            html = t.render(ctx)
        else:
            from_email = title = body = html = ""

        return from_email, title, body, html

    def get_cc_list(self):
        batch_carbon_copies = self.batchcarboncopy_set.public_all()
        cc_list = []
        for cc in batch_carbon_copies:
            if cc.member and cc.member.email:
                cc_list.append(cc.member.email)
            if cc.salesperson and cc.salesperson.email:
                cc_list.append(cc.salesperson.email)
            if cc.email:
                cc_list.append(cc.email)
        return cc_list

    def send_notify_mail(self, context, recipient_list, attachments=None, no_cc=False):
        logger = self.get_logger()
        if not recipient_list:
            logger.warning(u"宛先が空白になっている。")
            return False
        from_email, title, body, html = self.get_formatted_batch(context)
        mail_connection = BatchManage.get_custom_connection()
        cc_list = [] if no_cc else self.get_cc_list()
        email = EmailMultiAlternativesWithEncoding(
            subject=title,
            body=body,
            from_email=from_email,
            to=recipient_list,
            cc=cc_list,
            connection=mail_connection
        )
        if html:
            email.attach_alternative(html, constants.MIME_TYPE_HTML)
        if attachments:
            for filename, content, mimetype in attachments:
                email.attach(filename, content, mimetype)
        email.send()
        log_format = u"題名: %s; FROM: %s; TO: %s; CC: %s; 送信完了。"
        logger.info(log_format % (title, from_email, ','.join(recipient_list), ','.join(cc_list)))

    @staticmethod
    def get_custom_connection():
        host = Config.get(constants.CONFIG_ADMIN_EMAIL_SMTP_HOST, default_value='smtp.e-business.co.jp')
        port = Config.get(constants.CONFIG_ADMIN_EMAIL_SMTP_PORT, default_value=587)
        username = Config.get(constants.CONFIG_ADMIN_EMAIL_ADDRESS)
        password = Config.get(constants.CONFIG_ADMIN_EMAIL_PASSWORD)
        backend = get_connection()
        backend.host = str(host)
        backend.port = int(port)
        backend.username = str(username)
        backend.password = str(password)
        return backend


class BatchCarbonCopy(BaseModel):
    batch = models.ForeignKey(BatchManage, on_delete=models.PROTECT, verbose_name=u"バッチ名")
    member = models.ForeignKey(Member, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"ＣＣ先の社員")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, on_delete=models.PROTECT,
                                    verbose_name=u"ＣＣ先の営業員")
    email = models.EmailField(blank=True, null=True, verbose_name=u"メールアドレス")

    class Meta:
        ordering = ['batch']
        verbose_name = verbose_name_plural = u"バッチ送信時のＣＣリスト"

    def __unicode__(self):
        if self.member:
            return self.member.__unicode__()
        elif self.salesperson:
            return self.salesperson.__unicode__()
        else:
            return self.email


class PushNotification(BaseModel):
    user = models.ForeignKey(User, verbose_name=u"ユーザー")
    registration_id = models.CharField(max_length=1000, verbose_name=u"デバイスの登録ＩＤ")
    key_auth = models.CharField(max_length=100)
    key_p256dh = models.CharField(max_length=256)
    title = models.CharField(blank=True, null=True, max_length=100)
    message = models.CharField(blank=True, null=True, max_length=256)

    class Meta:
        ordering = ['user']
        verbose_name = verbose_name_plural = u"プッシュ通知"


class ViewRelease(models.Model):
    member = models.ForeignKey(Member, verbose_name=u"社員")
    project_member = models.ForeignKey(ProjectMember, db_column='projectmember_id', verbose_name=u"案件メンバー")
    release_ym = models.CharField(max_length=6, verbose_name=u"リリース月")
    division = models.ForeignKey(Section, blank=True, null=True, related_name='division_set', verbose_name=u"事業部")
    section = models.ForeignKey(Section, blank=True, null=True, related_name='section_set', verbose_name=u"部署")
    subsection = models.ForeignKey(Section, blank=True, null=True, related_name='subsection_set', verbose_name=u"課")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, verbose_name=u"営業員")
    project = models.ForeignKey(Project, verbose_name=u"案件")
    member_type = models.IntegerField(choices=constants.CHOICE_MEMBER_TYPE, blank=True, null=True, verbose_name=u"社員区分")
    subcontractor = models.ForeignKey(Subcontractor, blank=True, null=True, verbose_name=u"協力会社")

    class Meta:
        managed = False
        db_table = 'v_release_list'
        verbose_name = verbose_name_plural = u"リリース状況"
        default_permissions = ()

    def __unicode__(self):
        return unicode(self.member)


class ViewSalespersonStatus(models.Model):
    salesperson = models.ForeignKey(Salesperson, verbose_name=u"営業員")
    salesperson_name = models.CharField(max_length=30, verbose_name=u"営業員")
    all_member_count = models.IntegerField(verbose_name=u"担当社員数")
    sales_off_count = models.IntegerField(verbose_name=u"営業対象外員数")
    working_member_count = models.IntegerField(verbose_name=u"稼働中社員数")
    waiting_member_count = models.IntegerField(verbose_name=u"待機中社員数")
    release_count = models.IntegerField(verbose_name=u"今月リリース数")
    release_next_count = models.IntegerField(verbose_name=u"来月リリース数")
    release_next2_count = models.IntegerField(verbose_name=u"再来月リリース数")

    class Meta:
        managed = False
        db_table = 'v_salesperson_status'
        ordering = ['salesperson_name']
        verbose_name = verbose_name_plural = u"営業員担当状況"
        default_permissions = ()

    def __unicode__(self):
        return self.salesperson_name


class ViewStatusMonthly(models.Model):
    ym = models.CharField(max_length=6, primary_key=True, verbose_name=u"対象年月")
    year = models.CharField(max_length=4, verbose_name=u"対象年")
    month = models.CharField(max_length=2, verbose_name=u"対象月")
    all_member_count = models.IntegerField(verbose_name=u"担当社員数")
    sales_on_count = models.IntegerField(verbose_name=u"営業対象内社員数")
    sales_off_count = models.IntegerField(verbose_name=u"営業対象外社員数")
    working_member_count = models.IntegerField(verbose_name=u"稼働中社員数")
    waiting_member_count = models.IntegerField(verbose_name=u"待機中社員数")
    bp_member_count = models.IntegerField(verbose_name=u"ＢＰ社員数")
    bp_sales_on_count = models.IntegerField(verbose_name=u"ＢＰ営業対象内社員数")
    bp_sales_off_count = models.IntegerField(verbose_name=u"ＢＰ営業対象外社員数")
    bp_working_member_count = models.IntegerField(verbose_name=u"ＢＰ稼働中社員数")
    bp_waiting_member_count = models.IntegerField(verbose_name=u"ＢＰ待機中社員数")

    class Meta:
        managed = False
        db_table = 'v_status_monthly'
        ordering = ['ym']
        verbose_name = verbose_name_plural = u"月別稼働状況"
        default_permissions = ()

    def __unicode__(self):
        return self.ym


class VMemberWithoutContract(models.Model):
    member = models.ForeignKey(Member)
    employee_id = models.CharField(max_length=30, verbose_name=u"社員ID")
    name = models.CharField(max_length=30, verbose_name=u"名前")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, verbose_name=u"営業員")

    class Meta:
        managed = False
        db_table = 'v_member_without_contract'
        ordering = ['salesperson']
        verbose_name = verbose_name_plural = u"契約未作成"
        default_permissions = ()

    def __unicode__(self):
        return unicode(self.member)


class VClientRequest(models.Model):
    client = models.ForeignKey(Client, verbose_name=u"取引先")
    client_name = models.CharField(max_length=50, verbose_name=u"取引先名")
    year = models.CharField(max_length=4, verbose_name=u"対象年")
    month = models.CharField(max_length=2, verbose_name=u"対象月")
    limit_date = models.DateField(verbose_name=u"お支払い期限")
    amount = models.IntegerField(default=0, verbose_name=u"請求金額（税込）")
    turnover_amount = models.IntegerField(default=0, verbose_name=u"売上金額（基本単価＋残業料）（税抜き）")
    tax_amount = models.IntegerField(default=0, verbose_name=u"税金")
    expenses_amount = models.IntegerField(default=0, verbose_name=u"精算金額")

    class Meta:
        managed = False
        db_table = 'v_client_request'
        ordering = ['client', 'year', 'month']
        verbose_name = verbose_name_plural = u"取引先月別請求"
        default_permissions = ()

    def __unicode__(self):
        return self.client_name


class VBpRequest(models.Model):
    subcontractor = models.ForeignKey(Subcontractor, verbose_name=u"協力会社")
    subcontractor_name = models.CharField(max_length=50, verbose_name=u"協力会社名")
    year = models.CharField(max_length=4, verbose_name=u"対象年")
    month = models.CharField(max_length=2, verbose_name=u"対象月")
    limit_date = models.DateField(verbose_name=u"お支払い期限")
    amount = models.IntegerField(default=0, verbose_name=u"請求金額（税込）")
    turnover_amount = models.IntegerField(default=0, verbose_name=u"売上金額（基本単価＋残業料）（税抜き）")
    tax_amount = models.IntegerField(default=0, verbose_name=u"税金")
    expenses_amount = models.IntegerField(default=0, verbose_name=u"精算金額")

    class Meta:
        managed = False
        db_table = 'v_bp_request'
        ordering = ['subcontractor', 'year', 'month']
        verbose_name = verbose_name_plural = u"協力会社月別請求"
        default_permissions = ()

    def __unicode__(self):
        return self.subcontractor_name


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


# class ViewOrganizationTurnover(models.Model):
#     member_id = models.IntegerField(db_column='member_id', blank=True, null=True, verbose_name=u"社員")
#     employee_id = models.CharField(db_column='employee_id', blank=True, null=True, max_length=30, verbose_name=u"社員ID")
#     first_name = models.CharField(db_column='first_name', blank=True, null=True, max_length=30, verbose_name=u"姓")
#     last_name = models.CharField(db_column='last_name', blank=True, null=True, max_length=30, verbose_name=u"名")
#     membersectionperiod_id = models.IntegerField(db_column='membersectionperiod_id', blank=True, null=True, verbose_name=u"部署期間")
#     division_id = models.IntegerField(db_column='division_id', blank=True, null=True, verbose_name=u"事業部")
#     division_name = models.CharField(db_column='division_name', blank=True, null=True, max_length=30, verbose_name=u"事業部名")
#     section_id = models.IntegerField(db_column='section_id', blank=True, null=True, verbose_name=u"部署")
#     section_name = models.CharField(db_column='section_name', blank=True, null=True, max_length=30, verbose_name=u"部署名")
#     subsection_id = models.IntegerField(db_column='subsection_id', blank=True, null=True, verbose_name=u"課")
#     subsection_name = models.CharField(db_column='subsection_name', blank=True, null=True, max_length=30, verbose_name=u"課名")
#     projectmember_id = models.IntegerField(db_column='projectmember_id', blank=True, null=True, verbose_name=u"案件メンバー")
#     project_id = models.IntegerField(db_column='project_id', blank=True, null=True, verbose_name=u"案件")
#     project_name = models.CharField(db_column='project_name', blank=True, null=True, max_length=50, verbose_name=u"案件名称")
#     is_reserve = models.BooleanField(db_column='is_reserve', default=False, verbose_name=u"待機案件フラグ")
#     is_lump = models.BooleanField(db_column='is_lump', default=False, verbose_name=u"一括フラグ")
#     client_id = models.IntegerField(db_column='client_id', blank=True, null=True, verbose_name=u"取引先")
#     client_name = models.CharField(db_column='client_name', blank=True, null=True, max_length=30, verbose_name=u"取引先名")
#     company_name = models.CharField(db_column='company_name', blank=True, null=True, max_length=30, verbose_name=u"会社名")
#     endowment_insurance = models.CharField(db_column='endowment_insurance', max_length=1, blank=True, null=True, default='0',
#                                            choices=constants.CHOICE_ENDOWMENT_INSURANCE,
#                                            verbose_name=u"社会保険加入有無")
#     member_type = models.IntegerField(db_column='member_type', blank=True, null=True, choices=constants.CHOICE_MEMBER_TYPE,verbose_name=u"雇用形態コード")
#     member_type_name = models.CharField(db_column='member_type_name', blank=True, null=True, max_length=30, verbose_name=u"雇用形態")
#     is_loan = models.BooleanField(db_column='is_loan', default=False, verbose_name=u"出向")
#     projectrequestdetail_id = models.IntegerField(db_column='projectrequestdetail_id', blank=True, null=True, verbose_name=u"請求ＩＤ")
#     prev_traffic_cost = models.IntegerField(db_column='prev_traffic_cost', default=0, verbose_name=u"先月勤務交通費")
#     prev_allowance = models.IntegerField(db_column='prev_allowance', default=0, verbose_name=u"先月手当")
#     memberattendance_id = models.IntegerField(db_column='memberattendance_id', blank=True, null=True, verbose_name=u"出勤情報")
#     total_hours = models.DecimalField(db_column='total_hours', default=0, max_digits=5, decimal_places=2, verbose_name=u"合計時間")
#     total_days = models.IntegerField(db_column='total_days', default=0, verbose_name=u"勤務日数")
#     night_days = models.IntegerField(db_column='night_days', default=0, verbose_name=u"深夜日数")
#     advances_paid_client = models.IntegerField(db_column='advances_paid_client', default=0, verbose_name=u"客先立替金")
#     advances_paid = models.IntegerField(db_column='advances_paid', default=0, verbose_name=u"立替金")
#     traffic_cost = models.IntegerField(db_column='traffic_cost', default=0, verbose_name=u"勤務交通費")
#     all_price = models.IntegerField(db_column='all_price', default=0, verbose_name=u"売上（税込）")
#     total_price = models.IntegerField(db_column='total_price', default=0, verbose_name=u"売上（税抜）")
#     expenses_price = models.IntegerField(db_column='expenses_price', default=0, verbose_name=u"売上（経費）")
#     salary = models.IntegerField(db_column='salary', default=0, verbose_name=u"月給")
#     allowance = models.IntegerField(db_column='allowance', default=0, verbose_name=u"手当")
#     night_allowance = models.IntegerField(db_column='night_allowance', default=0, verbose_name=u"深夜手当")
#     overtime_cost = models.IntegerField(db_column='overtime_cost', default=0, verbose_name=u"残業／控除")
#     expenses = models.IntegerField(db_column='expenses', default=0, verbose_name=u"経費")
#     employment_insurance = models.IntegerField(db_column='employment_insurance', default=0, verbose_name=u"雇用／労災")
#     health_insurance = models.IntegerField(db_column='health_insurance', default=0, verbose_name=u"健康／厚生")
#
#     class Meta:
#         managed = False
#         db_table = 'v_organization_turnover'
#         verbose_name = verbose_name_plural = u"売上情報明細"
#         default_permissions = ()
#
#     def __unicode__(self):
#         return unicode(self.member) if self.member else unicode(self.project)


def get_all_members(date=None):
    if date is None or date.strftime('%Y%m') == datetime.date.today().strftime('%Y%m'):
        first_day = last_day = datetime.date.today()
    else:
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(date)
    query_set = Member.objects.filter(
        Q(join_date__isnull=True) | Q(join_date__lte=last_day),
        Q(membersectionperiod__division__is_on_sales=True) |
        Q(membersectionperiod__section__is_on_sales=True) |
        Q(membersectionperiod__subsection__is_on_sales=True),
        membersectionperiod__is_deleted=False
    ).annotate(
        sales_off_period_pk=Subquery(
            MemberSalesOffPeriod.objects.filter(
                (Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
                (Q(start_date__lte=last_day) & Q(end_date__gte=first_day)),
                member=OuterRef('pk')
            ).values('pk'),
            output_field=models.IntegerField()
        )
    ).distinct()
    # 現在所属の部署を取得
    section_set = MemberSectionPeriod.objects.filter((Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
                                                     (Q(start_date__lte=last_day) & Q(end_date__gte=first_day)))
    # 現在所属の営業員を取得
    salesperson_set = MemberSalespersonPeriod.objects.filter((Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
                                                             (Q(start_date__lte=last_day) & Q(end_date__gte=first_day)))
    salesoff_set = MemberSalesOffPeriod.objects.filter(
        (Q(start_date__lte=last_day) & Q(end_date__isnull=True)) |
        (Q(start_date__lte=last_day) & Q(end_date__gte=first_day))
    )
    return query_set.prefetch_related(
        Prefetch('membersectionperiod_set', queryset=section_set, to_attr='current_section_period'),
        Prefetch('membersalespersonperiod_set', queryset=salesperson_set, to_attr='current_salesperson_period'),
        Prefetch('membersalesoffperiod_set', queryset=salesoff_set, to_attr='current_salesoff_period'),
    ).extra(select={
        'last_end_date': "select max(pm.end_date) "
                         "  from eb_projectmember pm "
                         "  join eb_project p on p.id = pm.project_id"
                         " where pm.member_id = eb_member.id "
                         "   and pm.is_deleted = 0 "
                         "   and pm.status = 2"
                         "   and p.is_reserve = 0",
        'is_working': "select count(1)"
                      "  from eb_projectmember pm"
                      "  join eb_project p on p.id = pm.project_id"
                      " where pm.member_id = eb_member.id"
                      "   and pm.status = 2"
                      "   and pm.is_deleted = 0"
                      "   and pm.start_date <= '%s'"
                      "   and pm.end_date >= '%s'"
                      "   and p.is_reserve = 0" % (last_day, first_day),
        'planning_count': "select count(*) "
                          "  from eb_projectmember pm "
                          " where pm.member_id = eb_member.id "
                          "   and pm.is_deleted = 0 "
                          "   and pm.status = 1",
    })


def get_sales_members(date=None):
    """現在の営業対象のメンバーを取得する。

    加入日は現在以前、かつ所属部署は営業対象部署になっている

    :return: MemberのQueryset
    """
    if date is None:
        date = datetime.date.today()
    first_day = common.get_first_day_by_month(date)
    return get_all_members(date).filter(Q(is_retired=False) | (Q(is_retired=True) & Q(retired_date__gt=first_day)))


def get_on_sales_members(date=None):
    """現在の営業対象のメンバーを取得する。

    加入日は現在以前、かつ所属部署は営業対象部署、かつ該当社員は営業対象中になっている

    :return: MemberのQueryset
    """
    if date is None:
        date = datetime.date.today()
    query_set = get_sales_members(date).filter(
        Q(membersalesoffperiod__isnull=True) |
        Q(membersalesoffperiod__end_date__lt=date) |
        (Q(membersalesoffperiod__start_date__gt=date) & Q(membersalesoffperiod__is_deleted=False))
    ).distinct()
    return query_set


def get_off_sales_members(date=None):
    """現在の営業対象外のメンバーを取得する。

    加入日は現在以前、かつ所属部署は営業対象部署、かつ該当社員は営業対象外になっている

    :return: MemberのQueryset
    """
    query_set = get_sales_members(date).filter(sales_off_period_pk__isnull=False)
    return query_set


def get_working_members(date=None):
    """指定日付の稼働中のメンバーを取得する

    日付は指定してない場合は本日とする。

    :param date: 対象年月
    :return: MemberのQueryset
    """
    if not date or date.strftime('%Y%m') == datetime.date.today().strftime('%Y%m'):
        first_day = last_day = datetime.date.today()
    else:
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(date)
    members = get_on_sales_members(date).filter(projectmember__start_date__lte=last_day,
                                                projectmember__end_date__gte=first_day,
                                                projectmember__is_deleted=False,
                                                projectmember__status=2,
                                                projectmember__project__is_reserve=False).distinct()
    return members


def get_waiting_members(date=None):
    """現在待機中のメンバーを取得する

    :param date: 対象年月
    :return: MemberのQueryset
    """
    working_members = get_working_members(date)
    return get_on_sales_members(date).exclude(pk__in=working_members)


def get_project_members_by_month(date):
    """指定月の案件メンバー全部取得する。

    案件メンバーのステータスは「作業確定(2)」、該当する案件のステータスは「実施中(4)」

    :param date 指定月
    :return: ProjectMemberのQueryset
    """
    first_day = common.get_first_day_by_month(date)
    # today = datetime.date.today()
    next_2_month = common.add_months(first_day, 2)
    # if date.year == today.year and date.month == today.month:
    #     first_day = today
    last_day = common.get_last_day_by_month(date)
    query_set = ProjectMember.objects.public_filter(end_date__gte=first_day,
                                                    start_date__lte=last_day,
                                                    project__status__in=[4, 5],
                                                    project__is_reserve=False,
                                                    status=2)
    return query_set.extra(select={
        'section_name': "select name "
                        "  from eb_section s "
                        " inner join eb_membersectionperiod msp on s.id = msp.section_id "
                        " where ((msp.start_date <= '{0}' and msp.end_date is null) "
                        "     or (msp.start_date <= '{0}' and msp.end_date >= '{0}')) "
                        "   and msp.member_id = eb_projectmember.member_id "
                        "   and msp.is_deleted = 0".format(date),
        'salesperson_name': "select concat(first_name, last_name) "
                            "  from eb_salesperson s "
                            " inner join eb_membersalespersonperiod msp on s.id = msp.salesperson_id "
                            " where ((msp.start_date <= '{0}' and msp.end_date is null) "
                            "     or (msp.start_date <= '{0}' and msp.end_date >= '{0}')) "
                            "   and msp.member_id = eb_projectmember.member_id "
                            "   and msp.is_deleted = 0".format(date),
        'business_status': "select case"
                           "           when (select count(*) "
                           "                   from eb_projectmember pm2 "
                           "                  where pm2.member_id = eb_projectmember.member_id "
                           "                    and pm2.is_deleted = 0"
                           "                    and pm2.status = 1"
                           "                ) > 0 then '営業中'"
                           "           when (select count(*) "
                           "                   from eb_projectmember pm3 "
                           "                  where pm3.member_id = eb_projectmember.member_id "
                           "                    and pm3.is_deleted = 0 "
                           "                    and pm3.status = 2 "
                           "                    and pm3.end_date >= '%s' "
                           "                ) > 0 then '-' "
                           "           else '未提案' "
                           "       end " % next_2_month,
    }).distinct()


def get_release_members_by_month(date, p=None):
    """指定年月にリリースするメンバーを取得する。

    :param date 指定月
    :param p: 画面からの絞り込み条件
    :return: ProjectMemberのQueryset
    """
    # 次の月はまだ稼働中の案件メンバーは除外する。
    working_member_next_date = get_working_members(date=common.add_months(date, 1))
    project_members = get_project_members_by_month(date).filter(
        Q(member__membersectionperiod__division__is_on_sales=True) |
        Q(member__membersectionperiod__section__is_on_sales=True) |
        Q(member__membersectionperiod__subsection__is_on_sales=True),
        member__membersectionperiod__is_deleted=False,
        member__is_on_sales=True,
    ).exclude(member__in=working_member_next_date)
    if p:
        project_members = project_members.filter(**p)
    return project_members.order_by('member__first_name', 'member__last_name')


def get_release_current_month():
    """今月にリリースするメンバーを取得する

    :return: ProjectMemberのQueryset
    """
    return get_release_members_by_month(datetime.date.today())


def get_release_next_month():
    """来月にリリースするメンバーを取得する

    :return: ProjectMemberのQueryset
    """
    next_month = common.add_months(datetime.date.today(), 1)
    return get_release_members_by_month(next_month)


def get_release_next_2_month():
    """再来月にリリースするメンバーを取得する

    :return: ProjectMemberのQueryset
    """
    next_2_month = common.add_months(datetime.date.today(), 2)
    return get_release_members_by_month(next_2_month)


def get_attachment_id():
    return '{time}_{uuid}'.format(
        time=timezone.now().strftime('%Y%m%d%H%M%S'),
        uuid=uuid.uuid4(),
    )


def get_attachment_path(self, filename):
    name, ext = os.path.splitext(filename)
    now = datetime.datetime.now()
    path = os.path.join(now.strftime('%Y'), now.strftime('%m'))
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, self.uuid, ext)


class Attachment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    uuid = models.CharField(max_length=55, default=get_attachment_id, unique=True, verbose_name=u"ファイルの唯一ＩＤ")
    name = models.CharField(max_length=100, verbose_name=u"帳票名称")
    path = models.FileField(upload_to=get_attachment_path)
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=u"作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除日時")

    class Meta:
        db_table = 'mst_attachment'
        default_permissions = ()
        verbose_name = u"ファイル"
        verbose_name_plural = u"ファイル一覧"


class EMailLogEntry(models.Model):
    action_time = models.DateTimeField(_('action time'), default=timezone.now, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('user'))
    sender = models.EmailField(verbose_name=u"差出人")
    recipient = models.CharField(max_length=1000, verbose_name=u"宛先")
    cc = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u"ＣＣ")
    bcc = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u"ＢＣＣ")
    title = models.CharField(max_length=50, verbose_name=u"件名")
    body = models.TextField(verbose_name=u"メール本文")
    attachment = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"添付ファイル名")

    class Meta:
        db_table = 'eb_email_log'
        default_permissions = ()
        ordering = ['-action_time']
        verbose_name = verbose_name_plural = u"メール送信履歴"


class PartnerCostMonthly(models.Model):
    subcontractor = models.ForeignKey(
        Subcontractor, db_column='partner_id', on_delete=models.PROTECT, verbose_name=u"協力会社"
    )
    name = models.CharField(blank=False, null=False, db_column='partner_name', max_length=30, verbose_name=u"会社名")
    ym = models.CharField(max_length=6, verbose_name=u"対象年月")
    year = models.CharField(max_length=4, verbose_name=u"対象年")
    month = models.CharField(max_length=2, verbose_name=u"対象月")
    turnover_amount = models.IntegerField(default=0, verbose_name=u"売上金額（基本単価＋残業料）（税抜き）")
    tax_amount = models.IntegerField(default=0, verbose_name=u"税金")
    expenses_amount = models.IntegerField(default=0, verbose_name=u"精算金額")
    amount = models.IntegerField(default=0, verbose_name=u"請求金額（税込）")

    class Meta:
        managed = False
        db_table = 'v_partner_cost_monthly'
        default_permissions = ()
        verbose_name = verbose_name_plural = u"協力会社の年間売上"

    def __unicode__(self):
        return self.name
