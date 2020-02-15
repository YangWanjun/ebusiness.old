# coding: UTF-8
"""
Created on 2017/04/24

@author: Yang Wanjun
"""
import datetime
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from . import models
from eb import models as sales_models
from utils import common


class BaseForm(forms.ModelForm):
    pass


class MemberForm(BaseForm):
    class Meta:
        model = models.Member
        fields = '__all__'

    birthday = forms.DateField(widget=AdminDateWidget, label=u"生年月日")
    join_date = forms.DateField(widget=AdminDateWidget, label=u"入社年月日")
    retired_date = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 80px;'}),
                                   label=u"退職年月日",
                                   required=False)
    post_code = forms.CharField(max_length=7,
                                widget=forms.TextInput(
                                    attrs={'onKeyUp': "AjaxZip3.zip2addr(this,'','address1','address1');"}),
                                label=u"郵便番号",
                                help_text=u"数値だけを入力してください、例：1230034",
                                required=False)

    id_card_expired_date = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 80px;'}), label=u"在留カード期限",
                                           required=False)
    visa_start_date = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 80px;'}), label=u"ビザ有効期限（開始）",
                                      required=False)
    visa_expire_date = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 80px;'}), label=u"ビザ有効期限（終了）",
                                       required=False)
    passport_expired_dt = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 80px;'}), label=u"パスポート有効期限",
                                          required=False)

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.fields['id_from_api'].widget.attrs.update({'readonly': 'readonly'})
        # for name in ('birthday', 'join_date', 'retired_date'):
        #     self.files[name].widget = AdminDateWidget()

    def clean(self):
        cleaned_data = super(MemberForm, self).clean()
        is_retired = cleaned_data.get('is_retired', False)
        retired_date = cleaned_data.get('retired_date', False)
        is_unofficial = cleaned_data.get('is_unofficial', False)
        if self.instance.pk and is_unofficial and models.Contract.objects.filter(member=self.instance).count() > 0:
            self.add_error('is_unofficial', u"既に採用済みです。")
        if self.instance and not self.instance.pk:
            cleaned_data["id_from_api"] = models.Member.get_max_api_id()
        if is_retired and not retired_date:
            self.add_error('retired_date', u"退職年月日を入力してください。")
        return cleaned_data


class ContractMemberForm(BaseForm):
    class Meta:
        model = models.Member
        fields = ('employee_id', 'first_name', 'last_name', 'member_type', 'subcontractor', 'is_on_sales', 'is_retired')

    def __init__(self, *args, **kwargs):
        super(ContractMemberForm, self).__init__(*args, **kwargs)
        for key in self.fields.keys():
            self.fields[key].widget.attrs.update({'readonly': 'readonly'})


class ContractForm(BaseForm):
    class Meta:
        model = models.Contract
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ContractForm, self).__init__(*args, **kwargs)
        self.fields['contract_no'].widget.attrs.update({'readonly': 'readonly'})
        self.fields['allowance_base'].widget.attrs.update({
            'onchange': 'set_allowance_base_memo("%s", "%s")' % (
                'id_allowance_base',
                'id_allowance_base_memo'
            )
        })
        self.fields['allowance_time_max'].widget.attrs.update({
            'onchange': 'set_allowance_overtime_memo("%s", "%s", "%s")' % ('id_allowance_time_max',
                                                                           'id_allowance_overtime',
                                                                           'id_allowance_overtime_memo')
        })
        self.fields['allowance_overtime'].widget.attrs.update({
            'onchange': 'set_allowance_overtime_memo("%s", "%s", "%s")' % ('id_allowance_time_max',
                                                                           'id_allowance_overtime',
                                                                           'id_allowance_overtime_memo')
        })
        self.fields['allowance_time_min'].widget.attrs.update({
            'onchange': 'set_allowance_absenteeism_memo("%s", "%s", "%s")' % ('id_allowance_time_min',
                                                                              'id_allowance_absenteeism',
                                                                              'id_allowance_absenteeism_memo')
        })
        self.fields['allowance_absenteeism'].widget.attrs.update({
            'onchange': 'set_allowance_absenteeism_memo("%s", "%s", "%s")' % ('id_allowance_time_min',
                                                                              'id_allowance_absenteeism',
                                                                              'id_allowance_absenteeism_memo')
        })
        self.fields['endowment_insurance'].widget.attrs.update({
            'onchange': 'change_endowment_insurance(this, "id_allowance_date_comment")'
        })

    contract_date = forms.DateField(widget=AdminDateWidget, label=u"契約日")
    employment_date = forms.DateField(widget=AdminDateWidget, label=u"雇用日")
    start_date = forms.DateField(widget=AdminDateWidget, label=u"雇用開始日")
    end_date = forms.DateField(widget=AdminDateWidget, label=u"雇用終了日", required=False)
    retired_date = forms.DateField(widget=AdminDateWidget(attrs={'style': 'width: 100px;'}), label=u"退職年月日", required=False)

    def clean(self):
        cleaned_data = super(ContractForm, self).clean()
        member_type = cleaned_data.get('member_type', None)
        # start_date = cleaned_data.get('start_date', None)
        end_date = cleaned_data.get('end_date', None)
        if member_type == 1 and end_date is not None:
            self.add_error('end_date', u"正社員の場合雇用終了日は入れないでください。")
        # elif member_type == 2 and end_date is None:
        #     self.add_error('end_date', u"契約社員の場合雇用終了日は入力してください。")


class BpContractForm(BaseForm):
    class Meta:
        model = models.BpContract
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(BpContractForm, self).__init__(*args, **kwargs)
        # 開始日を変更時、営業日数も変更する
        self.fields['start_date'].widget.attrs.update({
            'onblur': 'change_start_date(this, "allowance_base", '
                      '"calculate_time_min", "calculate_time_max", '
                      '"allowance_absenteeism", "allowance_overtime",'
                      ' "calculate_type", "business_days")'
        })
        self.fields['is_hourly_pay'].widget.attrs.update({
            'onchange': 'change_hourly_pay_display(this, "allowance_base")'
        })
        self.fields['is_fixed_cost'].widget.attrs.update({
            'onchange': 'change_fixed_cost_display(this, "allowance_base")'
        })
        self.fields['is_show_formula'].widget.attrs.update({
            'onchange': 'change_formula_display(this, "allowance_base", '
                        '"calculate_time_min", "calculate_time_max", '
                        '"allowance_absenteeism", "allowance_overtime")'
        })
        self.fields['allowance_base'].widget.attrs.update({
            'onchange': 'calculate_plus_minus(this, "allowance_base", '
                        '"calculate_time_min", "calculate_time_max", '
                        '"allowance_absenteeism", "allowance_overtime")'
        })
        # 基準時間　下限
        self.fields['allowance_time_min'].widget.attrs.update({
            'onchange': 'change_allowance_time_min(this, "allowance_time_max", '
                        '"allowance_time_memo")'
        })
        # 基準時間　上限
        self.fields['allowance_time_max'].widget.attrs.update({
            'onchange': 'change_allowance_time_max(this, "allowance_time_min", '
                        '"allowance_time_memo")'
        })
        # 計算用下限
        self.fields['calculate_time_min'].widget.attrs.update({
            'onchange': 'calculate_minus_from_min_hour(this, "allowance_base", '
                        '"calculate_time_min", "calculate_time_max", '
                        '"allowance_absenteeism", "allowance_overtime")'
        })
        # 計算用上限
        self.fields['calculate_time_max'].widget.attrs.update({
            'onchange': 'calculate_plus_from_max_hour(this, "allowance_base", '
                        '"calculate_time_min", "calculate_time_max", '
                        '"allowance_absenteeism", "allowance_overtime")'
        })
        # 残業手当
        self.fields['allowance_overtime'].widget.attrs.update({
            'onchange': 'change_allowance_overtime(this, "allowance_base", '
                        '"calculate_time_max", '
                        '"allowance_overtime_memo")'
        })
        # 欠勤手当
        self.fields['allowance_absenteeism'].widget.attrs.update({
            'onchange': 'change_allowance_absenteeism(this, "allowance_base", '
                        '"calculate_time_min", '
                        '"allowance_absenteeism_memo")'
        })
        # 計算種類
        self.fields['calculate_type'].widget.attrs.update({
            'onchange': 'change_calculate_type(this, "allowance_base", '
                        '"allowance_time_min", "allowance_time_max", '
                        '"allowance_absenteeism", "allowance_overtime", "calculate_type", "business_days")'
        })
        # 営業日数
        self.fields['business_days'].widget.attrs.update({
            'onchange': 'change_business_days(this, "allowance_base", '
                        '"allowance_time_min", "allowance_time_max", '
                        '"allowance_absenteeism", "allowance_overtime", "calculate_type")'
        })

        for name in ('allowance_overtime_memo', 'allowance_absenteeism_memo'):
            self.fields[name].widget.attrs.update({'readonly': 'readonly'})

    def clean(self):
        cleaned_data = super(BpContractForm, self).clean()
        member = cleaned_data.get('member', None)
        company = cleaned_data.get('company', None)
        start_date = cleaned_data.get('start_date', None)
        end_date = cleaned_data.get('end_date', None)
        if end_date and start_date > end_date:
            self.add_error('end_date', u"終了日は開始日の前になっている、開始日の以降に設定してください。")
        if not company and member and self.instance:
            self.instance.company = member.subcontractor
        # 契約期間が重複されているかどうかをチェック
        dates = [(start_date, end_date)]
        queryset = models.BpContract.objects.public_filter(member=member).exclude(pk=self.instance.pk)
        for contract in queryset:
            dates.append((contract.start_date, contract.end_date))
        if len(dates) > 1:
            dates.sort(key=lambda date: date[0])
            for i, period in enumerate(dates):
                start_date, end_date = period
                if common.is_cross_date(dates, start_date, i):
                    self.add_error('start_date', u"契約期間の開始日が重複している。")
                if end_date and common.is_cross_date(dates, end_date, i):
                    self.add_error('end_date', u"契約期間の終了日が重複している。")


class BpContractLumpForm(BaseForm):
    class Meta:
        model = models.BpLumpContract
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(BpContractLumpForm, self).__init__(*args, **kwargs)
        self.fields['allowance_base'].widget.attrs.update({
            'onchange': 'calculate_tax_amount(this, "allowance_base_tax", "allowance_base_total")'
        })
        self.fields['comment'] = forms.CharField(widget=forms.Textarea(attrs={'style': 'width: 610px;'}),
                                                 required=False, label=u"備考")


class InsuranceLevelPeriodForm(BaseForm):
    class Meta:
        model = models.InsuranceLevelPeriod
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(InsuranceLevelPeriodForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'style': 'width: 500px;'})

    def clean(self):
        cleaned_data = super(InsuranceLevelPeriodForm, self).clean()
        start_date = cleaned_data.get('start_date', None)
        end_date = cleaned_data.get('end_date', None)
        if end_date and start_date > end_date:
            self.add_error('end_date', u"終了日は開始日の前になっている、開始日の以降に設定してください。")
        # 期間が重複されているかどうかをチェック
        dates = [(start_date, end_date)]
        if self.instance and self.instance.pk:
            queryset = models.InsuranceLevelPeriod.objects.exclude(pk=self.instance.pk)
        else:
            queryset = models.InsuranceLevelPeriod.objects.public_all()
        for obj in queryset:
            dates.append((obj.start_date, obj.end_date))
        if len(dates) > 1:
            dates.sort(key=lambda date: date[0])
            for i, period in enumerate(dates):
                start_date, end_date = period
                if common.is_cross_date(dates, start_date, i):
                    self.add_error('start_date', u"期間の開始日が重複している。")
                if end_date and common.is_cross_date(dates, end_date, i):
                    self.add_error('end_date', u"期間の終了日が重複している。")
        return cleaned_data


class InsuranceLevelDetailForm(BaseForm):
    class Meta:
        model = models.InsuranceLevelDetail
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(InsuranceLevelDetailForm, self).__init__(*args, **kwargs)
        self.fields['salary'].widget.attrs.update({
            'onchange': 'calculate_insurance_rate(this, "level2", "amount1_total", "amount1_half", "amount2_total", "amount2_half", "amount3_total", "amount3_half")',
            'style': 'width: 70px;',
        })
        self.fields['amount1_total'].widget.attrs.update({'style': 'width: 70px;'})
        self.fields['amount1_half'].widget.attrs.update({'style': 'width: 70px;'})
        self.fields['amount2_total'].widget.attrs.update({'style': 'width: 70px;'})
        self.fields['amount2_half'].widget.attrs.update({'style': 'width: 70px;'})
        self.fields['amount3_total'].widget.attrs.update({'style': 'width: 70px;'})
        self.fields['amount3_half'].widget.attrs.update({'style': 'width: 70px;'})


class InsuranceLevelDetailFormset(forms.BaseInlineFormSet):

    def _construct_form(self, i, **kwargs):
        # kwargs.update({'request': self.request})
        initial = {'level1': i + 1}
        kwargs.update({'initial': initial})
        if 3 <= i < 34:
            initial.update({'level2': i - 2})
        form = super(InsuranceLevelDetailFormset, self)._construct_form(i, **kwargs)
        return form


class MemberInsuranceLevelForm(BaseForm):
    class Meta:
        model = models.MemberInsuranceLevel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

    start_date = forms.DateField(widget=AdminDateWidget, label=u"開始日")
    end_date = forms.DateField(widget=AdminDateWidget, label=u"終了日", required=False)


class MemberInsuranceLevelFormset(forms.BaseInlineFormSet):

    def clean(self):
        count = 0
        dates = []
        for form in self.forms:
            try:
                if form.cleaned_data:
                    start_date = form.cleaned_data.get("start_date")
                    end_date = form.cleaned_data.get("end_date")
                    dates.append((start_date, end_date))
                    count += 1
            except AttributeError:
                pass
        if count > 1:
            dates.sort(key=lambda date: date[0])
            for i, period in enumerate(dates):
                start_date, end_date = period
                if common.is_cross_date(dates, start_date, i):
                    raise forms.ValidationError(u"開始日が重複している。")
                if end_date and common.is_cross_date(dates, end_date, i):
                    raise forms.ValidationError(u"終了日が重複している。")
