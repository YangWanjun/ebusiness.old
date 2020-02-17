# coding: UTF-8
"""
Created on 2017/04/24

@author: Yang Wanjun
"""
from __future__ import unicode_literals
import datetime
import re
import math

from django.db import models
from django.contrib.humanize.templatetags import humanize
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from eb.models import (
    Member, Config, Company, Subcontractor, Project, ProjectMember, Salesperson, BpMemberOrder, BpLumpOrder
)
from utils.validator import validate_rate
from utils import constants, common


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


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, null=True, editable=False, verbose_name=u"作成日時")
    updated_date = models.DateTimeField(auto_now=True, editable=False, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(blank=True, null=True, editable=False, verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_date = datetime.datetime.now()
        self.save()


class Contract(BaseModel):
    member = models.ForeignKey(Member, editable=False, verbose_name=u"社員")
    company = models.ForeignKey(Company, verbose_name=u"雇用会社")
    contract_no = models.CharField(max_length=20, verbose_name=u"契約番号")
    contract_date = models.DateField(verbose_name=u"契約日", help_text=u"例：2014-01-01")
    member_type = models.IntegerField(choices=constants.CHOICE_MEMBER_TYPE, verbose_name=u"雇用形態")
    is_loan = models.BooleanField(default=False, verbose_name=u"出向")
    employment_date = models.DateField(verbose_name=u"雇用日", help_text=u"例：2014-01-01")
    start_date = models.DateField(verbose_name=u"雇用開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"雇用終了日")
    employment_period_comment = models.TextField(blank=True, null=True, verbose_name=u"雇用期間コメント",
                                                 default=Config.get_employment_period_comment())
    position = models.CharField(max_length=50, blank=True, null=True, verbose_name=u"職位")
    business_address = models.CharField(max_length=255, blank=True, null=True, default=Config.get_business_address(),
                                        verbose_name=u"就業の場所")
    business_type = models.CharField(max_length=2, choices=constants.CHOICE_BUSINESS_TYPE, verbose_name=u"業務の種類")
    business_type_other = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"業務の種類その他")
    business_other = models.TextField(blank=True, null=True, default=Config.get_business_other(),
                                      verbose_name=u"業務その他")
    business_time = models.TextField(blank=True, null=True, default=Config.get_business_time(),
                                     verbose_name=u"就業時間")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    allowance_base = models.IntegerField(verbose_name=u"基本給（税抜）")
    allowance_base_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"基本給メモ")
    allowance_base_tax = models.IntegerField(default=0, verbose_name=u"基本給（税金）")
    allowance_base_other = models.IntegerField(default=0, verbose_name=u"基本給その他")
    allowance_base_other_memo = models.CharField(max_length=255, blank=True, null=True,
                                                 verbose_name=u"基本給その他メモ")
    allowance_work = models.IntegerField(default=0, verbose_name=u"現場手当")
    allowance_work_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"現場手当メモ")
    allowance_director = models.IntegerField(default=0, verbose_name=u"役職手当")
    allowance_director_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"役職手当メモ")
    allowance_position = models.IntegerField(default=0, verbose_name=u"職務手当")
    allowance_position_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"職務手当メモ")
    allowance_diligence = models.IntegerField(default=0, verbose_name=u"精勤手当")
    allowance_diligence_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"精勤手当メモ")
    allowance_region = models.IntegerField(default=0, verbose_name=u"地域手当")
    allowance_region_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"地域手当メモ")
    allowance_security = models.IntegerField(default=0, verbose_name=u"安全手当")
    allowance_security_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"安全手当メモ")
    allowance_qualification = models.IntegerField(default=0, verbose_name=u"資格手当")
    allowance_qualification_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"資格手当メモ")
    allowance_traffic = models.IntegerField(default=0, verbose_name=u"通勤手当")
    allowance_traffic_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"通勤手当メモ")
    allowance_time_min = models.IntegerField(default=160, verbose_name=u"時間下限", help_text=u"足りないなら欠勤となる")
    allowance_time_max = models.IntegerField(default=200, verbose_name=u"時間上限", help_text=u"超えたら残業となる")
    allowance_overtime = models.IntegerField(default=0, verbose_name=u"残業手当")
    allowance_overtime_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"残業手当メモ")
    allowance_absenteeism = models.IntegerField(default=0, verbose_name=u"欠勤控除")
    allowance_absenteeism_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"欠勤手当メモ")
    allowance_other = models.IntegerField(default=0, verbose_name=u"その他手当")
    allowance_other_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"その他手当メモ")
    endowment_insurance = models.CharField(max_length=1, null=True, default='0',
                                           choices=constants.CHOICE_ENDOWMENT_INSURANCE,
                                           verbose_name=u"社会保険加入有無",
                                           help_text=u"0:加入しない、1:加入する")
    allowance_ticket_comment = models.TextField(blank=True, null=True, verbose_name=u"諸手当")
    allowance_date_comment = models.TextField(blank=True, null=True, default=Config.get_allowance_date_comment(),
                                              verbose_name=u"給与締め切り日及び支払日")
    allowance_change_comment = models.TextField(blank=True, null=True, default=Config.get_allowance_change_comment(),
                                                verbose_name=u"昇給及び降給")
    bonus_comment = models.TextField(blank=True, null=True, default=Config.get_bonus_comment(), verbose_name=u"賞与")
    holiday_comment = models.TextField(blank=True, null=True, default=Config.get_holiday_comment(), verbose_name=u"休日")
    paid_vacation_comment = models.TextField(blank=True, null=True, default=Config.get_paid_vacation_comment(),
                                             verbose_name=u"有給休暇")
    non_paid_vacation_comment = models.TextField(blank=True, null=True, default=Config.get_no_paid_vacation_comment(),
                                                 verbose_name=u"無給休暇")
    retire_comment = models.TextField(blank=True, null=True, default=Config.get_retire_comment(),
                                      verbose_name=u"退職に関する項目")
    status = models.CharField(max_length=2, default='01', choices=constants.CHOICE_CONTRACT_STATUS,
                              verbose_name=u"契約状態")
    comment = models.TextField(blank=True, null=True, default=Config.get_contract_comment(), verbose_name=u"備考")
    move_flg = models.BooleanField(default=0, editable=False)
    join_date = models.DateField(blank=True, null=True, verbose_name=u"入社年月日")
    retired_date = models.DateField(blank=True, null=True, verbose_name=u"退職年月日")
    end_date2 = models.DateField(blank=True, null=True, verbose_name=u"雇用終了日")

    class Meta:
        ordering = ['member', 'contract_no']
        verbose_name = verbose_name_plural = u"社員契約"
        db_table = 'eb_contract'

    def __unicode__(self):
        return u"%s(%s)" % (unicode(self.member), self.contract_no)

    def get_cost(self):
        """コストを取得する

        :return:
        """
        cost = self.allowance_base \
               + self.allowance_base_other \
               + self.allowance_work \
               + self.allowance_director \
               + self.allowance_position \
               + self.allowance_diligence \
               + self.allowance_security \
               + self.allowance_qualification \
               + self.allowance_other
        if self.member_type == 1 or self.member_type == 7:
            cost = int((cost * 14) / 12)
        return cost

    def get_next_contract_no(self):
        today = datetime.date.today()
        return "WT%04d%s" % (int(self.member.id_from_api), today.strftime('%Y%m%d'))

    @property
    def is_fixed_cost(self):
        return False

    def get_cost_monthly(self):
        """在職証明書、所得証明書出力時、正社員の場合でも*14/12の必要はない

        :return:
        """
        cost = self.allowance_base \
               + self.allowance_base_other \
               + self.allowance_work \
               + self.allowance_director \
               + self.allowance_position \
               + self.allowance_diligence \
               + self.allowance_security \
               + self.allowance_qualification \
               + self.allowance_other
        return cost

    def get_cost_yearly(self):
        """年収を取得する。

        :return:
        """
        cost = self.allowance_base \
               + self.allowance_base_other \
               + self.allowance_work \
               + self.allowance_director \
               + self.allowance_position \
               + self.allowance_diligence \
               + self.allowance_security \
               + self.allowance_qualification \
               + self.allowance_other
        if self.member_type == 1 or self.member_type == 7:
            return int(cost * 14)
        else:
            return cost * 12

    def get_business_position(self):
        """在職証明書の職務位置に使われる

        :return:
        """
        business_type_name = self.get_business_type_display()
        m = re.search(r'（([^（）]+)）', business_type_name)
        if m and m.groups():
            return m.groups()[0]
        else:
            return business_type_name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.member.contract_set.filter(is_deleted=False).exclude(status='04').count() == 0:
            # 既存の契約が存在しない場合、入社日は契約開始日とする。
            self.join_date = self.start_date
        else:
            # 前の契約が存在する場合、終了日を設定する。
            prev_contracts = self.member.contract_set.filter(
                is_deleted=False,
                start_date__lt=self.start_date
            ).exclude(status='04').order_by('-start_date')
            if prev_contracts.count() > 0:
                prev_contract = prev_contracts[0]
                if prev_contract.retired_date is not None:
                    # 前の契約の退職日はある場合、再び入社日を設定する。
                    self.join_date = self.start_date
                if prev_contract.member_type == 1 and prev_contract.end_date is None:
                    # 前の契約形態は正社員で、かつ雇用終了日は空白の場合。
                    prev_contract.end_date2 = self.start_date + datetime.timedelta(days=-1)
                    prev_contract.save(update_fields=['end_date2'])
        super(Contract, self).save(force_insert, force_update, using, update_fields)
        # from_email, title, body, html = self.get_formatted_batch(context)
        # mail_connection = BatchManage.get_custom_connection()
        # recipient_list = ContractRecipient.get_recipient_list()
        # cc_list = ContractRecipient.get_cc_list()
        # bcc_list = ContractRecipient.get_bcc_list()
        # email = EmailMultiAlternativesWithEncoding(
        #     subject=title,
        #     body=body,
        #     from_email=from_email,
        #     to=recipient_list,
        #     cc=cc_list,
        #     connection=mail_connection
        # )
        # if html:
        #     email.attach_alternative(html, constants.MIME_TYPE_HTML)
        # if attachments:
        #     for filename, content, mimetype in attachments:
        #         email.attach(filename, content, mimetype)
        # email.send()


class ContractRecipient(BaseModel):
    recipient_type = models.CharField(max_length=2, default='01', choices=constants.CHOICE_RECIPIENT_TYPE,
                                      verbose_name=u"送信種類")
    member = models.ForeignKey(Member, blank=True, null=True, verbose_name=u"送信先の社員")
    email = models.EmailField(blank=True, null=True, verbose_name=u"メールアドレス")

    class Meta:
        verbose_name = verbose_name_plural = u"契約変更の受信者"
        db_table = 'eb_contractrecipient'

    def __unicode__(self):
        if self.member:
            return unicode(self.member)
        else:
            return self.email

    @classmethod
    def get_recipient_list(cls):
        return ContractRecipient.objects.public_filter(recipient_type='01')

    @classmethod
    def get_cc_list(cls):
        return ContractRecipient.objects.public_filter(recipient_type='02')

    @classmethod
    def get_bcc_list(cls):
        return ContractRecipient.objects.public_filter(recipient_type='03')


class BpContract(BaseModel):
    contract_type = models.CharField(max_length=2, default='02', choices=constants.CHOICE_BP_CONTRACT_TYPE, verbose_name=u"契約形態")
    member = models.ForeignKey(Member, verbose_name=u"社員")
    company = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"雇用会社")
    member_type = models.IntegerField(default=4, editable=False, choices=constants.CHOICE_MEMBER_TYPE,
                                      verbose_name=u"雇用形態")
    start_date = models.DateField(verbose_name=u"雇用開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"雇用終了日")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    is_fixed_cost = models.BooleanField(default=False, verbose_name=u"固定")
    is_show_formula = models.BooleanField(default=True, verbose_name=u"計算式",
                                          help_text=u"注文書に超過単価と不足単価の計算式を表示するか")
    allowance_base = models.IntegerField(verbose_name=u"基本給")
    allowance_base_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"基本給メモ")
    allowance_time_min = models.DecimalField(default=160, max_digits=5, decimal_places=2, verbose_name=u"時間下限",
                                             help_text=u"足りないなら欠勤となる")
    allowance_time_max = models.DecimalField(default=200, max_digits=5, decimal_places=2, verbose_name=u"時間上限",
                                             help_text=u"超えたら残業となる")
    allowance_time_memo = models.CharField(max_length=255, blank=True, null=True,
                                           default=u"※基準時間：160～200/月", verbose_name=u"基準時間メモ")
    calculate_type = models.CharField(default='99', max_length=2, choices=constants.CHOICE_CALCULATE_TYPE,
                                      verbose_name=u"計算種類")
    business_days = models.IntegerField(blank=True, null=True, verbose_name=u"営業日数")
    calculate_time_min = models.DecimalField(blank=True, null=True, default=160, max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用下限", help_text=u"欠勤手当を算出ために使われます。")
    calculate_time_max = models.DecimalField(blank=True, null=True, default=200, max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用上限", help_text=u"残業手当を算出ために使われます。")
    allowance_overtime = models.IntegerField(default=0, verbose_name=u"残業手当")
    allowance_overtime_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"残業手当メモ")
    allowance_absenteeism = models.IntegerField(default=0, verbose_name=u"欠勤手当")
    allowance_absenteeism_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"欠勤手当メモ")
    allowance_other = models.IntegerField(default=0, verbose_name=u"その他手当")
    allowance_other_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"その他手当メモ")
    status = models.CharField(max_length=2, default='01', choices=constants.CHOICE_CONTRACT_STATUS,
                              verbose_name=u"契約状態")
    comment = models.TextField(blank=True, null=True,  verbose_name=u"備考")

    class Meta:
        ordering = ['company', 'member', '-start_date']
        verbose_name = verbose_name_plural = u"ＢＰ契約"
        db_table = 'eb_bp_contract'

    def __unicode__(self):
        return u"%s(%s)" % (unicode(self.member), self.start_date)

    def get_cost(self):
        """コストを取得する

        :return:
        """
        if self.is_hourly_pay:
            cost = self.allowance_base
        else:
            cost = self.allowance_base + self.allowance_other
        return cost

    @property
    def endowment_insurance(self):
        """他者技術者の場合、保険なし

        :return:
        """
        return '0'

    def get_allowance_time_min_now(self):
        return self.get_allowance_time_min(datetime.date.today().year, datetime.date.today().month)

    def get_allowance_absenteeism_memo_now(self):
        return self.get_allowance_absenteeism_memo(datetime.date.today().year, datetime.date.today().month)

    def get_allowance_time_min(self, year, month):
        if self.is_hourly_pay or self.is_fixed_cost:
            return 0
        elif self.calculate_type == '01':
            return 160
        elif self.calculate_type == '02':
            return len(common.get_business_days(year, month)) * 8
        elif self.calculate_type == '03':
            return len(common.get_business_days(year, month)) * 7.9
        elif self.calculate_type == '04':
            return len(common.get_business_days(year, month)) * 7.75
        else:
            return self.allowance_time_min

    def get_allowance_time_memo(self, year, month):
        allowance_time_min = self.get_allowance_time_min(year, month)
        float_part, int_part = math.modf(self.allowance_time_max)
        if float_part == 0.0:
            allowance_time_max = int(int_part)
        else:
            allowance_time_max = self.allowance_time_max
        if self.is_hourly_pay or self.is_fixed_cost:
            allowance_time_memo = ''
        elif self.calculate_type in ('01', '02', '03', '04'):
            allowance_time_memo = u"※基準時間：%s～%sh/月" % (allowance_time_min, allowance_time_max)
        else:
            if self.allowance_time_memo:
                allowance_time_memo = self.allowance_time_memo
            else:
                allowance_time_memo = u"※基準時間：%s～%sh/月" % (allowance_time_min, allowance_time_max)
        # 営業日数 × ８または営業日数 × ７.９の説明
        if self.calculate_type in ('02', '03', '04'):
            hours = 8
            if self.calculate_type == '02':
                hours = 8
            elif self.calculate_type == '03':
                hours = 7.9
            elif self.calculate_type == '04':
                hours = 7.75
            allowance_time_memo += "   （%s＝%s月の営業日数(%s)×%s）" % (
                allowance_time_min, month, len(common.get_business_days(year, month)), hours
            )
        return allowance_time_memo

    def get_calculate_type_comment(self):
        if self.calculate_type in ('02', '03'):
            return "精算方式：変動基準時間方式"
        else:
            return ""

    def get_allowance_absenteeism(self, year, month):
        if self.is_hourly_pay or self.is_fixed_cost:
            allowance_absenteeism = 0
        elif self.calculate_type in ('01', '02', '03', '04'):
            allowance_time_min = self.get_allowance_time_min(year, month)
            allowance_absenteeism = int(int(self.allowance_base) / allowance_time_min)
            allowance_absenteeism -= allowance_absenteeism % 10
        else:
            allowance_absenteeism = self.allowance_absenteeism
        return allowance_absenteeism

    def get_allowance_absenteeism_memo(self, year, month):
        if self.is_hourly_pay or self.is_fixed_cost:
            allowance_absenteeism_memo = ''
        elif self.calculate_type == '01':
            allowance_absenteeism_memo = self.allowance_absenteeism_memo
        elif self.calculate_type in ('02', '03', '04'):
            allowance_time_min = self.get_allowance_time_min(year, month)
            allowance_absenteeism = self.get_allowance_absenteeism(year, month)
            if self.is_show_formula:
                allowance_absenteeism_memo = u"不足単価：¥%s/%sh=¥%s/h" % (
                    humanize.intcomma(self.allowance_base), allowance_time_min, humanize.intcomma(allowance_absenteeism)
                )
            else:
                allowance_absenteeism_memo = u"不足単価：¥%s/h" % humanize.intcomma(allowance_absenteeism)
        else:
            allowance_absenteeism_memo = self.allowance_absenteeism_memo
        return allowance_absenteeism_memo


class BpLumpContract(BaseModel):
    contract_type = models.CharField(max_length=2, default='04', editable=False, verbose_name=u"契約形態")
    company = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"雇用会社")
    start_date = models.DateField(verbose_name=u"契約開始日")
    end_date = models.DateField(verbose_name=u"契約終了日")
    delivery_date = models.DateField(blank=False, null=True, verbose_name=u"納品日")
    project = models.ForeignKey(Project, blank=False, null=True, verbose_name=u"関連案件")
    # project_name = models.CharField(max_length=50, verbose_name=u"件名")
    is_hourly_pay = models.BooleanField(default=False, editable=False, verbose_name=u"時給")
    allowance_base = models.IntegerField(verbose_name=u"契約金額")
    allowance_base_tax = models.IntegerField(default=0, verbose_name=u"消費税")
    allowance_base_total = models.IntegerField(default=0, verbose_name=u"合計額")
    allowance_time_min = models.DecimalField(default=160, max_digits=5, decimal_places=2, verbose_name=u"時間下限",
                                             editable=False, help_text=u"足りないなら欠勤となる")
    allowance_time_max = models.DecimalField(default=200, max_digits=5, decimal_places=2, verbose_name=u"時間上限",
                                             editable=False, help_text=u"超えたら残業となる")
    project_content = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"作業内容")
    workload = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"作業量")
    project_result = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"納入成果品")
    status = models.CharField(max_length=2, default='01', choices=constants.CHOICE_CONTRACT_STATUS,
                              verbose_name=u"契約状態")
    comment = models.CharField(blank=True, null=True, max_length=255,  verbose_name=u"備考")

    class Meta:
        ordering = ['company', '-start_date']
        verbose_name = verbose_name_plural = u"ＢＰ一括契約"
        db_table = 'eb_bp_lump_contract'

    def __unicode__(self):
        return unicode(self.project)

    def get_cost(self):
        """コストを取得する

        :return:
        """
        cost = self.allowance_base
        return cost


class ViewContract(models.Model):
    contract_no = models.CharField(db_column='contract_no', max_length=20, verbose_name=u"契約番号")
    contract_date = models.DateField(db_column='contract_date', verbose_name=u"契約日", help_text=u"例：2014-01-01")
    member_type = models.IntegerField(db_column='member_type', choices=constants.CHOICE_MEMBER_TYPE,
                                      verbose_name=u"雇用形態")
    employment_date = models.DateField(db_column='employment_date', verbose_name=u"雇用日", help_text=u"例：2014-01-01")
    start_date = models.DateField(db_column='start_date', verbose_name=u"雇用開始日")
    end_date = models.DateField(db_column='end_date', blank=True, null=True, verbose_name=u"雇用終了日")
    employment_period_comment = models.TextField(db_column='employment_period_comment', blank=True, null=True,
                                                 verbose_name=u"雇用期間コメント",
                                                 default=Config.get_employment_period_comment())
    position = models.CharField(db_column='position', max_length=50, blank=True, null=True, verbose_name=u"職位")
    business_address = models.CharField(db_column='business_address', max_length=255, blank=True, null=True,
                                        default=Config.get_business_address(),
                                        verbose_name=u"就業の場所")
    business_type = models.CharField(db_column='business_type', max_length=2, choices=constants.CHOICE_BUSINESS_TYPE,
                                     verbose_name=u"業務の種類")
    business_type_other = models.CharField(db_column='business_type_other', blank=True, null=True, max_length=50,
                                           verbose_name=u"業務の種類その他")
    business_other = models.TextField(db_column='business_other', blank=True, null=True,
                                      default=Config.get_business_other(),
                                      verbose_name=u"業務その他")
    business_time = models.TextField(db_column='business_time', blank=True, null=True,
                                     default=Config.get_business_time(),
                                     verbose_name=u"就業時間")
    is_hourly_pay = models.BooleanField(db_column='is_hourly_pay', default=False, verbose_name=u"時給")
    is_fixed_cost = models.BooleanField(db_column='is_fixed_cost', default=False, verbose_name=u"固定")
    is_show_formula = models.BooleanField(db_column='is_show_formula', default=True, verbose_name=u"計算式",
                                          help_text=u"注文書に超過単価と不足単価の計算式を表示するか")
    allowance_base = models.IntegerField(db_column='allowance_base', verbose_name=u"基本給")
    allowance_base_memo = models.CharField(db_column='allowance_base_memo', max_length=255, blank=True, null=True,
                                           verbose_name=u"基本給メモ")
    allowance_base_tax = models.IntegerField(default=0, verbose_name=u"基本給（税金）")
    allowance_base_other = models.IntegerField(db_column='allowance_base_other', default=0, verbose_name=u"基本給その他")
    allowance_base_other_memo = models.CharField(db_column='allowance_base_other_memo', max_length=255, blank=True,
                                                 null=True,
                                                 verbose_name=u"基本給その他メモ")
    allowance_work = models.IntegerField(db_column='allowance_work', default=0, verbose_name=u"現場手当")
    allowance_work_memo = models.CharField(db_column='allowance_work_memo', max_length=255, blank=True, null=True,
                                           verbose_name=u"現場手当メモ")
    allowance_director = models.IntegerField(db_column='allowance_director', default=0, verbose_name=u"役職手当")
    allowance_director_memo = models.CharField(db_column='allowance_director_memo', max_length=255, blank=True,
                                               null=True, verbose_name=u"役職手当メモ")
    allowance_position = models.IntegerField(db_column='allowance_position', default=0, verbose_name=u"職務手当")
    allowance_position_memo = models.CharField(db_column='allowance_position_memo', max_length=255, blank=True,
                                               null=True, verbose_name=u"職務手当メモ")
    allowance_diligence = models.IntegerField(db_column='allowance_diligence', default=0, verbose_name=u"精勤手当")
    allowance_diligence_memo = models.CharField(db_column='allowance_diligence_memo', max_length=255, blank=True,
                                                null=True, verbose_name=u"精勤手当メモ")
    allowance_region = models.IntegerField(default=0, verbose_name=u"地域手当")
    allowance_region_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"地域手当メモ")
    allowance_security = models.IntegerField(db_column='allowance_security', default=0, verbose_name=u"安全手当")
    allowance_security_memo = models.CharField(db_column='allowance_security_memo', max_length=255, blank=True,
                                               null=True, verbose_name=u"安全手当メモ")
    allowance_qualification = models.IntegerField(db_column='allowance_qualification', default=0, verbose_name=u"資格手当")
    allowance_qualification_memo = models.CharField(db_column='allowance_qualification_memo', max_length=255,
                                                    blank=True, null=True, verbose_name=u"資格手当メモ")
    allowance_traffic = models.IntegerField(db_column='allowance_traffic', default=0, verbose_name=u"通勤手当")
    allowance_traffic_memo = models.CharField(db_column='allowance_traffic_memo', max_length=255, blank=True, null=True,
                                              verbose_name=u"通勤手当メモ")
    allowance_time_min = models.IntegerField(db_column='allowance_time_min', default=160, verbose_name=u"時間下限",
                                             help_text=u"足りないなら欠勤となる")
    allowance_time_max = models.IntegerField(db_column='allowance_time_max', default=200, verbose_name=u"時間上限",
                                             help_text=u"超えたら残業となる")
    allowance_time_memo = models.CharField(db_column='allowance_time_memo', max_length=255, blank=True, null=True,
                                           default=u"※基準時間：160～200/月", verbose_name=u"基準時間メモ")
    calculate_type = models.CharField(db_column='calculate_type', default='99', max_length=2,
                                      choices=constants.CHOICE_CALCULATE_TYPE,
                                      verbose_name=u"計算種類")
    calculate_time_min = models.DecimalField(db_column='calculate_time_min', blank=True, null=True, default=160,
                                             max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用下限", help_text=u"欠勤手当を算出ために使われます。")
    calculate_time_max = models.DecimalField(db_column='calculate_time_max', blank=True, null=True, default=200,
                                             max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用上限", help_text=u"残業手当を算出ために使われます。")
    allowance_overtime = models.IntegerField(db_column='allowance_overtime', default=0, verbose_name=u"残業手当")
    allowance_overtime_memo = models.CharField(db_column='allowance_overtime_memo', max_length=255, blank=True,
                                               null=True, verbose_name=u"残業手当メモ")
    allowance_absenteeism = models.IntegerField(db_column='allowance_absenteeism', default=0, verbose_name=u"欠勤控除")
    allowance_absenteeism_memo = models.CharField(db_column='allowance_absenteeism_memo', max_length=255, blank=True,
                                                  null=True, verbose_name=u"欠勤手当メモ")
    allowance_other = models.IntegerField(db_column='allowance_other', default=0, verbose_name=u"その他手当")
    allowance_other_memo = models.CharField(db_column='allowance_other_memo', max_length=255, blank=True, null=True,
                                            verbose_name=u"その他手当メモ")
    endowment_insurance = models.CharField(db_column='endowment_insurance', max_length=1, null=True, default='0',
                                           choices=constants.CHOICE_ENDOWMENT_INSURANCE,
                                           verbose_name=u"社会保険加入有無",
                                           help_text=u"0:加入しない、1:加入する")
    allowance_ticket_comment = models.TextField(db_column='allowance_ticket_comment', blank=True, null=True,
                                                verbose_name=u"諸手当")
    allowance_date_comment = models.TextField(db_column='allowance_date_comment', blank=True, null=True,
                                              default=Config.get_allowance_date_comment(),
                                              verbose_name=u"給与締め切り日及び支払日")
    allowance_change_comment = models.TextField(db_column='allowance_change_comment', blank=True, null=True,
                                                default=Config.get_allowance_change_comment(),
                                                verbose_name=u"昇給及び降給")
    bonus_comment = models.TextField(db_column='bonus_comment', blank=True, null=True,
                                     default=Config.get_bonus_comment(), verbose_name=u"賞与")
    holiday_comment = models.TextField(db_column='holiday_comment', blank=True, null=True,
                                       default=Config.get_holiday_comment(), verbose_name=u"休日")
    paid_vacation_comment = models.TextField(db_column='paid_vacation_comment', blank=True, null=True,
                                             default=Config.get_paid_vacation_comment(),
                                             verbose_name=u"有給休暇")
    non_paid_vacation_comment = models.TextField(db_column='non_paid_vacation_comment', blank=True, null=True,
                                                 default=Config.get_no_paid_vacation_comment(),
                                                 verbose_name=u"無給休暇")
    retire_comment = models.TextField(db_column='retire_comment', blank=True, null=True,
                                      default=Config.get_retire_comment(),
                                      verbose_name=u"退職に関する項目")
    status = models.CharField(db_column='status', max_length=2, default='01', choices=constants.CHOICE_CONTRACT_STATUS,
                              verbose_name=u"契約状態")
    comment = models.TextField(db_column='comment', blank=True, null=True, default=Config.get_contract_comment(),
                               verbose_name=u"備考")
    member = models.ForeignKey(Member, db_column='member_id', editable=False, verbose_name=u"社員")
    content_type = models.ForeignKey(ContentType, db_column='content_type_id', on_delete=models.PROTECT)
    company_id = models.PositiveIntegerField(db_column='company_id')
    content_object = GenericForeignKey('content_type', 'company_id')
    is_loan = models.BooleanField(db_column='is_loan', default=False, verbose_name=u"出向")
    move_flg = models.BooleanField(db_column='move_flg', default=0, editable=False)
    is_old = models.BooleanField(db_column='is_old', default=False, verbose_name=u"上書きされた契約")
    join_date = models.DateField(db_column='join_date', blank=True, null=True, verbose_name=u"入社年月日")
    retired_date = models.DateField(db_column='retired_date', blank=True, null=True, verbose_name=u"退職年月日")
    cost = models.IntegerField(db_column='cost', verbose_name=u"基本給", help_text=u"コスト")
    created_date = models.DateTimeField(db_column='created_date', null=True, editable=False, verbose_name=u"作成日時")
    updated_date = models.DateTimeField(db_column='updated_date', editable=False, verbose_name=u"更新日時")
    is_deleted = models.BooleanField(db_column='is_deleted', default=False, editable=False, verbose_name=u"削除フラグ")
    deleted_date = models.DateTimeField(db_column='deleted_date', blank=True, null=True, editable=False,
                                        verbose_name=u"削除年月日")

    objects = PublicManager(is_deleted=False)

    class Meta:
        managed = False
        db_table = 'v_contract'
        ordering = ['member', 'contract_no', 'start_date']
        verbose_name = verbose_name_plural = u"社員契約情報"
        default_permissions = ()

    def __unicode__(self):
        return unicode(self.member)

    def get_business_position(self):
        """在職証明書の職務位置に使われる

        :return:
        """
        business_type_name = self.get_business_type_display()
        m = re.search(r'（([^（）]+)）', business_type_name)
        if m and m.groups():
            return m.groups()[0]
        else:
            return business_type_name

    def get_cost_monthly(self):
        """在職証明書、所得証明書出力時、正社員の場合でも*14/12の必要はない

        :return:
        """
        cost = self.allowance_base \
               + self.allowance_base_other \
               + self.allowance_work \
               + self.allowance_director \
               + self.allowance_position \
               + self.allowance_diligence \
               + self.allowance_security \
               + self.allowance_qualification \
               + self.allowance_other
        return cost

    def get_cost_yearly(self):
        """年収を取得する。

        :return:
        """
        cost = self.allowance_base \
               + self.allowance_base_other \
               + self.allowance_work \
               + self.allowance_director \
               + self.allowance_position \
               + self.allowance_diligence \
               + self.allowance_security \
               + self.allowance_qualification \
               + self.allowance_other
        if self.member_type == 1 or self.member_type == 7 :
            return int(cost * 14)
        else:
            return cost * 12


class ViewLatestBpContract(models.Model):
    contract_type = models.CharField(max_length=2, default='03', choices=constants.CHOICE_BP_CONTRACT_TYPE, verbose_name=u"契約形態")
    member = models.ForeignKey(Member, verbose_name=u"社員")
    company = models.ForeignKey(Subcontractor, on_delete=models.PROTECT, verbose_name=u"雇用会社")
    member_type = models.IntegerField(default=4, editable=False, choices=constants.CHOICE_MEMBER_TYPE,
                                      verbose_name=u"雇用形態")
    start_date = models.DateField(verbose_name=u"雇用開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"雇用終了日")
    is_hourly_pay = models.BooleanField(default=False, verbose_name=u"時給")
    is_fixed_cost = models.BooleanField(default=False, verbose_name=u"固定")
    is_show_formula = models.BooleanField(default=True, verbose_name=u"計算式",
                                          help_text=u"注文書に超過単価と不足単価の計算式を表示するか")
    allowance_base = models.IntegerField(verbose_name=u"基本給")
    allowance_base_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"基本給メモ")
    allowance_time_min = models.DecimalField(default=160, max_digits=5, decimal_places=2, verbose_name=u"時間下限",
                                             help_text=u"足りないなら欠勤となる")
    allowance_time_max = models.DecimalField(default=200, max_digits=5, decimal_places=2, verbose_name=u"時間上限",
                                             help_text=u"超えたら残業となる")
    allowance_time_memo = models.CharField(max_length=255, blank=True, null=True,
                                           default=u"※基準時間：160～200/月", verbose_name=u"基準時間メモ")
    calculate_type = models.CharField(default='99', max_length=2, choices=constants.CHOICE_CALCULATE_TYPE,
                                      verbose_name=u"計算種類")
    business_days = models.IntegerField(blank=True, null=True, verbose_name=u"営業日数")
    calculate_time_min = models.DecimalField(blank=True, null=True, default=160, max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用下限", help_text=u"欠勤手当を算出ために使われます。")
    calculate_time_max = models.DecimalField(blank=True, null=True, default=200, max_digits=5, decimal_places=2,
                                             verbose_name=u"計算用上限", help_text=u"残業手当を算出ために使われます。")
    allowance_overtime = models.IntegerField(default=0, verbose_name=u"残業手当")
    allowance_overtime_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"残業手当メモ")
    allowance_absenteeism = models.IntegerField(default=0, verbose_name=u"欠勤手当")
    allowance_absenteeism_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"欠勤手当メモ")
    allowance_other = models.IntegerField(default=0, verbose_name=u"その他手当")
    allowance_other_memo = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"その他手当メモ")
    status = models.CharField(max_length=2, default='01', choices=constants.CHOICE_CONTRACT_STATUS,
                              verbose_name=u"契約状態")
    comment = models.TextField(blank=True, null=True,  verbose_name=u"備考")
    is_retired = models.BooleanField(blank=False, null=False, default=False, verbose_name=u"退職")
    project = models.ForeignKey(Project, blank=True, null=True, verbose_name=u"案件")
    projectmember = models.ForeignKey(ProjectMember, blank=True, null=True, verbose_name=u"案件メンバー")
    salesperson = models.ForeignKey(Salesperson, blank=True, null=True, verbose_name=u"営業員")
    current_bp_order = models.ForeignKey(BpMemberOrder, related_name='current_bp_order_set', blank=True, null=True,
                                         verbose_name=u"今月注文書")
    next_bp_order = models.ForeignKey(BpMemberOrder, related_name='next_bp_order_set', blank=True, null=True,
                                      verbose_name=u"来月注文書")
    lump_order = models.ForeignKey(BpLumpOrder, blank=True, null=True, verbose_name=u"一括注文書")

    class Meta:
        managed = False
        db_table = 'v_latest_bp_contract'
        default_permissions = ()

    def __unicode__(self):
        return unicode(self.member)

    def get_cost(self):
        """コストを取得する

        :return:
        """
        cost = self.allowance_base + self.allowance_other
        return cost

    def get_bp_contract(self):
        if not self.lump_order:
            return BpContract.objects.get(pk=self.pk)
        return None


class InsuranceLevelPeriod(BaseModel):
    title = models.CharField(max_length=100, verbose_name=u"名称")
    location = models.CharField(max_length=10, verbose_name=u"区域")
    start_date = models.DateField(verbose_name="開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name=u"終了日")
    rate1 = models.FloatField(verbose_name="介護保険第２号被保険者でない保険率", validators=[validate_rate])
    rate2 = models.FloatField(verbose_name="介護保険第２号被保険者保険率", validators=[validate_rate])
    rate3 = models.FloatField(verbose_name="厚生年金保険率", validators=[validate_rate])

    class Meta:
        ordering = ['title']
        verbose_name = verbose_name_plural = "社会保険等級期間"
        db_table = 'eb_insurance_level_period'

    def __unicode__(self):
        return self.title


class InsuranceLevelDetail(BaseModel):
    period = models.ForeignKey(InsuranceLevelPeriod, verbose_name=u"保険レベル期間")
    level1 = models.IntegerField(verbose_name="健康月額等級")
    level2 = models.IntegerField(blank=True, null=True, verbose_name="厚生月額等級")
    salary = models.IntegerField(verbose_name="月額")
    amount1_total = models.DecimalField(max_digits=8, decimal_places=1, verbose_name=u"全額１")
    amount1_half = models.DecimalField(max_digits=8, decimal_places=1, verbose_name=u"折半額１")
    amount2_total = models.DecimalField(max_digits=8, decimal_places=1, verbose_name=u"全額２")
    amount2_half = models.DecimalField(max_digits=8, decimal_places=1, verbose_name=u"折半額２")
    amount3_total = models.DecimalField(max_digits=8, decimal_places=1, blank=True, null=True, verbose_name=u"全額３")
    amount3_half = models.DecimalField(max_digits=8, decimal_places=1, blank=True, null=True, verbose_name=u"折半額３")

    class Meta:
        ordering = ['period', 'level1']
        unique_together = ('period', 'level1')
        verbose_name = verbose_name_plural = "社会保険等級詳細"
        db_table = 'eb_insurance_level_detail'

    def __unicode__(self):
        if self.level2:
            return '%s - %02d(%02d)' % (unicode(self.period), self.level1, self.level2)
        else:
            return '%s - %02d' % (unicode(self.period), self.level1)


class MemberInsuranceLevel(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name="社員")
    start_date = models.DateField(verbose_name="開始日")
    end_date = models.DateField(blank=True, null=True, verbose_name="終了日")
    salary = models.IntegerField(verbose_name="決定後の標準報酬月額（健保）")

    class Meta:
        ordering = ['member', 'start_date']
        unique_together = ('member', 'start_date')
        verbose_name = verbose_name_plural = "被保険者標準報酬"
        db_table = 'eb_member_insurance_level'

    def __unicode__(self):
        return self.salary


class ViewMemberInsurance(models.Model):
    member = models.ForeignKey(Member, verbose_name=u"社員")
    name = models.CharField(max_length=30, verbose_name="名前")
    contract = models.ForeignKey(Contract, verbose_name="契約")
    member_insurance_level = models.ForeignKey(MemberInsuranceLevel, blank=True, null=True, verbose_name="被保険者標準報酬")
    salary = models.IntegerField(blank=True, null=True, verbose_name="標準報酬月額")

    class Meta:
        managed = False
        verbose_name = verbose_name_plural = "被保険者標準報酬"
        db_table = 'v_member_insurance_level'

    def __unicode__(self):
        return unicode(self.member)


class ContractNew(models.Model):
    # 会社情報
    company_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, related_name='company_contract_set', verbose_name="契約会社"
    )
    company_object_id = models.PositiveIntegerField(verbose_name="契約会社ID")
    company_content_object = GenericForeignKey('company_content_type', 'company_object_id')
    # 契約対象（社員、案件）
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # 契約共通情報
    contract_no = models.CharField(max_length=20, verbose_name="契約番号")
    contract_date = models.DateField(verbose_name="契約日")
    start_date = models.DateField(verbose_name="契約開始日")
    end_date = models.DateField(default='9999-12-31', verbose_name="契約終了日")
    # 社員契約に関する情報
    member_type = models.CharField(
        max_length=1, blank=True, null=True, choices=constants.CHOICE_MEMBER_TYPE, verbose_name="雇用形態",
    )
    insurance = models.CharField(
        max_length=1, blank=True, null=True, default='0',
        choices=constants.CHOICE_INSURANCE,
        verbose_name="社会保険加入有無",
        help_text="0:加入しない、1:加入する"
    )
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name="削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name="削除日時")

    class Meta:
        db_table = 'eb_contract_new'
        default_permissions = ()
        verbose_name = "契約"
        verbose_name_plural = "契約一覧"


class ContractComment(models.Model):
    contract = models.ForeignKey(ContractNew, on_delete=models.PROTECT, verbose_name="契約情報")
    code = models.CharField(max_length=5, choices=constants.CHOICE_CONTRACT_COMMENT, verbose_name="コメントコード")
    name = models.CharField(max_length=50, verbose_name="コメント名称")
    content = models.CharField(max_length=2000, verbose_name="内容")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name="削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name="削除日時")

    class Meta:
        db_table = 'eb_contract_comment'
        default_permissions = ()
        verbose_name = "契約コメント"
        verbose_name_plural = "契約コメント一覧"


class ContractAllowance(models.Model):
    contract = models.ForeignKey(ContractNew, on_delete=models.PROTECT, verbose_name="契約情報")
    code = models.CharField(max_length=5, choices=constants.CHOICE_CONTRACT_ALLOWANCE, verbose_name="手当コード")
    name = models.CharField(max_length=50, verbose_name="手当名称")
    amount = models.PositiveIntegerField(verbose_name="金額")
    unit = models.CharField(max_length=2, default='01', choices=constants.CHOICE_ALLOWANCE_UNIT, verbose_name="単位")
    comment = models.CharField(max_length=255, verbose_name="コメント")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_dt = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name="削除フラグ")
    deleted_dt = models.DateTimeField(blank=True, null=True, editable=False, verbose_name="削除日時")

    class Meta:
        db_table = 'eb_contract_allowance'
        default_permissions = ()
        verbose_name = "契約手当"
        verbose_name_plural = "契約手当一覧"
