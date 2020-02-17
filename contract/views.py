# coding: UTF-8
import datetime
import json
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.translation import ugettext as _
from django.utils.text import get_text_list
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.forms import inlineformset_factory
from django.template.loader import render_to_string

from . import biz, models, forms
from eb import biz_config
from eb import models as sales_models
from eb.biz import member_retired
from utils import constants, common
import operator

# Create your views here.


@method_decorator(login_required(login_url=constants.LOGIN_IN_URL), name='dispatch')
@method_decorator(permission_required('contract.change_contract', raise_exception=True), name='get')
class BaseView(View, ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(BaseView, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        if not common.is_human_resources(request.user):
            return HttpResponseForbidden()
        kwargs.update({
            'request': request
        })
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        pass


class BaseTemplateView(TemplateResponseMixin, BaseView):
    pass


class IndexView(BaseTemplateView):
    template_name = 'members.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        q = request.GET.get('q', None)
        o = request.GET.get('o', None)
        params_list, params = common.get_request_params(request.GET)

        all_members = biz.get_members()
        if params_list:
            all_members = all_members.filter(**params_list)
        if q:
            orm_lookups = ['first_name__icontains', 'last_name__icontains', 'id_from_api', 'eboa_user_id']
            for bit in q.split():
                or_queries = [Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                all_members = all_members.filter(reduce(operator.or_, or_queries))

        dict_order = common.get_ordering_dict(o, ['first_name',
                                                  'id_from_api',
                                                  'birthday',
                                                  'join_date',
                                                  'eboa_user_id',
                                                  'contract_member_type',
                                                  'endowment_insurance'])
        order_list = common.get_ordering_list(o)

        if order_list:
            all_members = all_members.order_by(*order_list)

        paginator = Paginator(all_members, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            members = paginator.page(page)
        except PageNotAnInteger:
            members = paginator.page(1)
        except EmptyPage:
            members = paginator.page(paginator.num_pages)
        context.update({
            'members': members,
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
            'orders': "&o=%s" % (o,) if o else "",
        })
        return context


class ContractChangeView(BaseTemplateView):
    template_name = 'contract_change.html'

    def get_context_data(self, **kwargs):
        context = super(ContractChangeView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        api_id = kwargs.get('api_id')
        member = get_object_or_404(sales_models.Member, id_from_api=api_id)
        contract_set = biz.get_latest_contract(member)
        all_contract = models.ViewContract.objects.public_filter(member=member)

        ver = request.GET.get('ver', None)
        if ver and contract_set.filter(contract_no=ver).count() > 0:
            contract = contract_set.get(contract_no=ver)
        elif contract_set.count() > 0:
            contract = contract_set[0]
        else:
            contract = models.Contract(member=member)
            contract.contract_no = contract.get_next_contract_no()
        form = forms.ContractForm(instance=contract)
        context.update({
            'member': member,
            'contract_set': contract_set,
            'all_contract': all_contract,
            'contract': contract,
            'form': form,
        })
        return context

    def get(self, request, *args, **kwargs):
        if not common.is_human_resources(request.user):
            return HttpResponseForbidden()
        kwargs.update({
            'request': request
        })
        context = self.get_context_data(**kwargs)
        contract = context.get('contract')
        form = forms.ContractForm(instance=contract)
        context.update({
            'form': form,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not common.is_human_resources(request.user):
            return HttpResponseForbidden()
        kwargs.update({
            'request': request
        })
        context = self.get_context_data(**kwargs)
        member = context.get('member')
        old_contract = context.get('contract')
        form = forms.ContractForm(request.POST, instance=old_contract)
        context.update({
            'form': form,
        })
        if form.is_valid():
            contract = form.save(commit=False)
            change_message = []
            if form.changed_data:
                changed_list = []
                for field in form.changed_data:
                    changed_list.append(u"%s(%s→%s)" % common.get_form_changed_value(form, field))
                change_message.append(_('Changed %s.') % get_text_list(changed_list, _('and')))
            message = ",".join(change_message) or _('No fields changed.')

            contract.member = member
            next_contract_no = contract.get_next_contract_no()
            if contract.status == '04':
                # 破棄する場合
                contract.pk = contract.id = old_contract.pk
                contract.save()
                action_flg = CHANGE
                message = u"破棄しました。" + message
            elif contract.contract_no == next_contract_no:
                # 契約当日、変更しません
                contract.pk = contract.id = old_contract.pk
                contract.created_date = old_contract.created_date
                contract.save()
                action_flg = CHANGE
            else:
                # 契約を追加する。
                contract.pk = None
                contract.contract_no = next_contract_no
                contract.save()
                action_flg = ADDITION

            LogEntry.objects.log_action(request.user.id,
                                        ContentType.objects.get_for_model(contract).pk,
                                        contract.pk,
                                        unicode(contract),
                                        action_flg,
                                        change_message=message)

            return redirect(reverse("contract_change",
                                    args=(contract.member.id_from_api,)) + "?" + "ver=%s" % contract.contract_no
                            )

        return self.render_to_response(context)


class ContractView(BaseTemplateView):
    template_name = 'contract.html'

    def get_context_data(self, **kwargs):
        context = super(ContractView, self).get_context_data(**kwargs)
        contract_id = kwargs.get('contract_id')
        contract = get_object_or_404(models.Contract, pk=contract_id)
        context.update({
            'contract': contract,
        })
        return context


class ContractRetire(BaseView):

    def post(self, request, *args, **kwargs):
        contract_id = kwargs.get('contract_id')
        date = request.POST.get('retired_date')
        d = dict()
        if date:
            contract = get_object_or_404(models.Contract, pk=contract_id)
            contract.retired_date = date
            contract.save()
            d.update({
                'result': True,
                'message': '成功しました。'
            })
            message = u"契約は「%s」に終了とします" % date
            LogEntry.objects.log_action(request.user.id,
                                        ContentType.objects.get_for_model(contract).pk,
                                        contract.pk,
                                        unicode(contract),
                                        CHANGE,
                                        change_message=message)
        else:
            d.update({
                'result': False,
                'message': '退職年月日を設定してください。'
            })
        return JsonResponse(d)


class CertificateView(BaseTemplateView):
    template_name = 'certificate.html'

    def get_context_data(self, **kwargs):
        context = super(CertificateView, self).get_context_data(**kwargs)
        member_id = kwargs.get('member_id')
        member = get_object_or_404(sales_models.Member, pk=member_id)
        contract = member.get_latest_contract()
        if contract is None:
            contract = models.Contract.objects.public_filter(start_date__gte=datetime.date.today()).first()
        context.update({
            'member': member,
            'contract': contract,
            'today': datetime.date.today()
        })
        return context


class IncomeView(BaseTemplateView):
    template_name = 'income.html'

    def get_context_data(self, **kwargs):
        context = super(IncomeView, self).get_context_data(**kwargs)
        member_id = kwargs.get('member_id')
        member = get_object_or_404(sales_models.Member, pk=member_id)
        context.update({
            'member': member,
            'contract': member.get_latest_contract(),
            'today': datetime.date.today()
        })
        return context


@method_decorator(csrf_protect, name='dispatch')
class GenerateApiIdView(BaseView):
    def post(self, request, *args, **kwargs):
        if common.is_human_resources(request.user):
            try:
                member_id = kwargs.get('member_id')
                member = sales_models.Member.objects.get(pk=member_id)
                member.id_from_api = sales_models.Member.get_max_api_id()
                member.save()
                d = {'error': 0, 'msg': ''}
            except Exception as ex:
                d = {'error': 1, 'msg': unicode(ex)}
        else:
            d = {'error': 1, 'msg': u"403: 権限ありません。"}
        return HttpResponse(json.dumps(d))


class MemberChangeView(BaseTemplateView):
    template_name = 'member.html'

    def get_context_data(self, **kwargs):
        context = super(MemberChangeView, self).get_context_data(**kwargs)
        member_id = kwargs.get('member_id', None)
        if member_id:
            member = get_object_or_404(sales_models.Member, pk=member_id)
        else:
            id_from_api = sales_models.Member.get_max_api_id()
            member = sales_models.Member(id_from_api=id_from_api, employee_id=id_from_api)
        form = forms.MemberForm(instance=member)
        context.update({
            'member': member,
            'form': form,
        })
        return context

    def post(self, request, *args, **kwargs):
        if not common.is_human_resources(request.user):
            return HttpResponseForbidden()
        kwargs.update({
            'request': request
        })
        context = self.get_context_data(**kwargs)
        old_member = context.get('member')
        is_add = False if old_member.pk else True
        form = forms.MemberForm(request.POST, instance=old_member, files=request.FILES)
        context.update({
            'form': form,
        })
        if form.is_valid():
            member = form.save(commit=False)
            if member.pk:
                update_fields = ['first_name', 'last_name', 'first_name_ja', 'last_name_ja',
                                 'first_name_en', 'last_name_en', 'member_type', 'birthday',
                                 'common_first_name', 'common_last_name',
                                 'common_first_name_ja', 'common_last_name_ja',
                                 'sex', 'join_date', 'employee_id', 'post_code', 'address1', 'address2',
                                 'nearest_station', 'phone', 'section', 'email', 'private_email',
                                 'is_retired', 'retired_date', 'eboa_user_id', 'is_unofficial',
                                 'personal_number', 'basic_pension_no', 'employment_insurance_no',
                                 'passport_number', 'passport_expired_dt', 'id_number', 'id_card_expired_date',
                                 'residence_type', 'pay_bank', 'pay_branch', 'pay_account', 'pay_bank_code',
                                 'pay_branch_code',
                                 'pay_owner', 'pay_owner_kana', 'visa_start_date', 'visa_expire_date',
                                 'emergency_post_code', 'emergency_address1', 'emergency_address2',
                                 'emergency_name', 'emergency_phone', 'emergency_relationship',
                                 'cash_card_image', 'passport_image', 'id_card_image_front', 'id_card_image_back',
                                 'personal_number_image_front', 'personal_number_image_back',
                                 'basic_pension_image', 'prev_employment_insurance_image']
            else:
                update_fields = None
            member.save(update_fields=update_fields)
            if 'is_retired' in form.changed_data:
                member_retired(member, request.user)

            change_message = []
            if form.changed_data:
                changed_list = []
                for field in form.changed_data:
                    if update_fields is None or field in update_fields:
                        changed_list.append(u"%s(%s→%s)" % common.get_form_changed_value(form, field))
                change_message.append(_('Changed %s.') % get_text_list(changed_list, _('and')))
            message = ",".join(change_message) or _('No fields changed.')
            action_flg = ADDITION if is_add else CHANGE
            LogEntry.objects.log_action(request.user.id,
                                        ContentType.objects.get_for_model(member).pk,
                                        member.pk,
                                        unicode(member),
                                        action_flg,
                                        change_message=message)

            return redirect(reverse("member_change", args=(member.pk,)))
        else:
            return self.render_to_response(context)


class MemberDeleteView(BaseView):
    def post(self, request, *args, **kwargs):
        try:
            member_id = kwargs.get('member_id')
            member = sales_models.Member.objects.get(pk=member_id)
            is_deletable, related_list = member.is_deletable()
            if is_deletable or (related_list and len([c for c in related_list if isinstance(c, models.Contract)]) > 0):
                member.delete()
                message = u"削除は成功しました。"
                if related_list:
                    message += u'\n下記契約情報も一緒削除しました：'
                    for contract in related_list:
                        message += u'\n契約番号：' + contract.contract_no
                        contract.delete()
                message += u"\n間違って削除した場合、システム管理者にご連絡ください、データの復元できます！"
                d = {'error': 0, 'msg': message}
                LogEntry.objects.log_action(request.user.id,
                                            ContentType.objects.get_for_model(member).pk,
                                            member.pk,
                                            unicode(member),
                                            DELETION,
                                            change_message=u"削除しました。")
            else:
                d = {'error': 1, 'msg': u"%sに関連している情報が存在しているため、削除できません。" % unicode(member)}
        except Exception as ex:
            d = {'error': 1, 'msg': unicode(ex)}
        return JsonResponse(d)


class MemberInsurancesView(BaseTemplateView):
    template_name = 'insurances.html'

    def get_context_data(self, **kwargs):
        context = super(MemberInsurancesView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        q = request.GET.get('q', None)
        o = request.GET.get('o', None)
        params_list, params = common.get_request_params(request.GET)

        members_insurances = models.ViewMemberInsurance.objects.all()    
        if q:
            orm_lookups = ['member__first_name__icontains', 'member__last_name__icontains']
            for bit in q.split():
                or_queries = [Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                members_insurances = members_insurances.filter(reduce(operator.or_, or_queries))

        paginator = Paginator(members_insurances, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            members_insurances = paginator.page(page)
        except PageNotAnInteger:
            members_insurances = paginator.page(1)
        except EmptyPage:
            members_insurances = paginator.page(paginator.num_pages)

        context.update({
            'members_insurances': members_insurances,
            'paginator': paginator,
        })

        return context


class MemberInsuranceEditView(BaseTemplateView):
    template_name = 'insurance.html'

    def get(self, request, *args, **kwargs):
        member_id = kwargs.get('member_id')
        member = get_object_or_404(sales_models.Member, pk=member_id)
        MemberInsuranceLevelFormset = inlineformset_factory(
            parent_model=sales_models.Member,
            model=models.MemberInsuranceLevel,
            form=forms.MemberInsuranceLevelForm,
            formset=forms.MemberInsuranceLevelFormset,
            extra=1,
            fk_name='member',
        )
        formset = MemberInsuranceLevelFormset(instance=member)
        context = self.get_context_data(**kwargs)
        context.update({
            'member': member,
            'formset': formset,
        })
        html = render_to_string(self.template_name, context)
        return JsonResponse({'html': html})

    def post(self, request, *args, **kwargs):
        member_id = kwargs.get('member_id')
        member = get_object_or_404(sales_models.Member, pk=member_id)
        MemberInsuranceLevelFormset = inlineformset_factory(
            parent_model=sales_models.Member,
            model=models.MemberInsuranceLevel,
            form=forms.MemberInsuranceLevelForm,
            formset=forms.MemberInsuranceLevelFormset,
            extra=1,
            fk_name='member',
        )
        formset = MemberInsuranceLevelFormset(request.POST, instance=member)
        d = dict()
        if formset.is_valid():
            insurance_list = formset.save(commit=False)
            start_date = None
            salary = 0
            today = datetime.date.today()
            if insurance_list:
                for insurance in insurance_list:
                    if start_date is None and insurance.start_date <= today \
                            and (insurance.end_date is None or insurance.end_date >= today):
                        start_date = insurance.start_date
                        salary = insurance.salary
                    insurance.save()
            d.update({'result': True, 'message': u"保存しました。", 'start_date': start_date, 'salary': salary})
        else:
            context = self.get_context_data(**kwargs)
            context.update({
                'member': member,
                'formset': formset,
            })
            html = render_to_string(self.template_name, context)
            d.update({
                'result': False, 'message': u"失敗しました。", 'html': html,
            })
        return JsonResponse(d)
