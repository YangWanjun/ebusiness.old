# coding: utf8
"""
Created on 2015/08/21

@author: Yang Wanjun
"""
from __future__ import unicode_literals
import datetime
import json
import os
import urllib
import operator

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template import loader
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import resolve_url
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.contrib.auth import update_session_auth_hash
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.db.models import Count, Prefetch, Q

from eb import biz, biz_turnover, biz_config, biz_plot
from utils import constants, common, errors, loader as file_loader, file_gen
from . import forms, models


@method_decorator(login_required(login_url=constants.LOGIN_IN_URL), name='dispatch')
class BaseView(View, ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(BaseView, self).get_context_data(**kwargs)
        context.update({
            'company': biz.get_company(),
            'theme': biz_config.get_theme(),
        })
        return context

    def get(self, request, *args, **kwargs):
        kwargs.update({
            'request': request
        })
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        pass


class BaseTemplateView(TemplateResponseMixin, BaseView):
    pass


def get_base_context():
    context = {
        'company': biz.get_company(),
        'theme': biz_config.get_theme(),
    }
    return context


class IndexView(BaseTemplateView):
    template_name = 'default/home.html'

    def get(self, request, *args, **kwargs):
        now = datetime.date.today()
        prev_month = common.add_months(now, -1)
        next_month = common.add_months(now, 1)
        next_2_months = common.add_months(now, 2)
        filter_list = {'prev_ym': prev_month.strftime('%Y%m'),
                       'current_ym': now.strftime('%Y%m'),
                       'next_ym': next_month.strftime('%Y%m'),
                       'next_2_ym': next_2_months.strftime('%Y%m')}

        member_in_coming = biz.get_members_in_coming()

        status_monthly = models.ViewStatusMonthly.objects.filter(
            ym__in=[prev_month.strftime('%Y%m'), now.strftime('%Y%m'), next_month.strftime('%Y%m')]
        ).order_by('ym')
        release_info = biz.get_release_info()
        salesperson_status_list = models.ViewSalespersonStatus.objects.all()
        activities = biz.get_activities_incoming()

        own_member_status = False
        show_warning_projects = False
        if biz.is_salesperson_user(request.user):
            show_warning_projects = True
            if request.user.salesperson.member_type == 5:
                # 営業担当の場合
                try:
                    own_member_status = salesperson_status_list.get(salesperson=request.user.salesperson)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    own_member_status = None

        context = self.get_context_data()
        context.update({
            'title': 'Home | %s' % constants.NAME_SYSTEM,
            'filter_list': filter_list,
            'status_monthly': list(status_monthly),
            'members_in_coming_count': member_in_coming.count(),
            'release_info': release_info,
            'activities': activities,
            'own_member_status': own_member_status,
            'show_warning_projects': show_warning_projects,
            'salesperson_status_list': salesperson_status_list,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MemberListView(BaseTemplateView):
    template_name = 'default/employee_list.html'

    def get_context_data(self, **kwargs):
        context = super(MemberListView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member_name', 'division_name', 'section_name', 'salesofreason_name',
                                                  'subsection_name', 'subcontractor_name', 'salesperson_name'])
        order_list = common.get_ordering_list(o)
        today = datetime.date.today()
        year = str(today.year)
        month = '%02d' % today.month

        data_frame = biz.get_sales_members(year, month, param_dict=param_dict, order_list=order_list)
        paginator = Paginator(list(data_frame.iterrows()), biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context.update({
            'title': u'要員一覧 | %s' % constants.NAME_SYSTEM,
            'object_list': object_list,
            'sections': biz.get_on_sales_top_org(),
            'salesperson': models.Salesperson.objects.public_all(),
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
            'orders': "&o=%s" % (o,) if o else "",
        })
        return context


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MemberListMonthlyView(BaseTemplateView):
    template_name = 'default/member_status_list.html'

    def get_context_data(self, **kwargs):
        context = super(MemberListMonthlyView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        year = request.GET.get('_year', None)
        month = request.GET.get('_month', None)
        if not year or not month:
            date = datetime.date.today()
            year = str(date.year)
            month = '%02d' % date.month
        status = request.GET.get('_status', None)
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['employee_id', 'member_name',
                                                  'division_name', 'section_name', 'subsection_name',
                                                  'subcontractor_name', 'salesperson_name'])
        order_list = common.get_ordering_list(o)

        if status == "sales":
            data_frame = biz.get_sales_on_members(year, month, param_dict=param_dict, order_list=order_list)
        elif status == "working":
            data_frame = biz.get_working_members(year, month, param_dict=param_dict)
        elif status == "waiting":
            data_frame = biz.get_waiting_members(year, month, param_dict=param_dict)
        elif status == "off_sales":
            data_frame = biz.get_sales_off_members(year, month, param_dict=param_dict)
        else:
            data_frame = biz.get_sales_members(year, month, param_dict=param_dict)

        status_monthly = models.ViewStatusMonthly.objects.filter(ym='%s%s' % (year, month))

        paginator = Paginator(list(data_frame.iterrows()), biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context.update({
            'title': u'要員一覧 | %s' % constants.NAME_SYSTEM,
            'object_list': object_list,
            'year': year,
            'month': month,
            'sections': biz.get_on_sales_top_org(),
            'salesperson': models.Salesperson.objects.public_all(),
            'paginator': paginator,
            'status_monthly': status_monthly,
            'params': params,
            'dict_order': dict_order,
            'orders': "&o=%s" % (o,) if o else "",
        })
        return context


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MemberCostListView(BaseTemplateView):
    template_name = 'default/member_cost_list.html'

    def get_context_data(self, **kwargs):
        context = super(MemberCostListView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        section_id = request.GET.get('_section', None)
        param_dict, params = common.get_request_params(request.GET)

        all_members = models.get_sales_members()
        if section_id:
            all_members = biz.get_members_by_section(all_members, section_id)

        paginator = Paginator(all_members, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            members = paginator.page(page)
        except PageNotAnInteger:
            members = paginator.page(1)
        except EmptyPage:
            members = paginator.page(paginator.num_pages)

        context.update({
            'title': u'要員コスト一覧 | %s' % constants.NAME_SYSTEM,
            'sections': biz.get_on_sales_top_org(),
            'members': members,
            'paginator': paginator,
            'params': params,
        })
        return context


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MemberDetailView(BaseTemplateView):
    template_name = 'default/member_detail.html'

    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get('employee_id', '')
        member = get_object_or_404(models.Member, employee_id=employee_id)
        member.set_coordinate()

        project_count = member.projectmember_set.public_all().count()
        context = self.get_context_data()
        context.update({
            'member': member,
            'title': u'%s の履歴 | %s' % (member, constants.NAME_SYSTEM),
            'project_count': project_count,
            'all_project_count': project_count + member.historyproject_set.public_all().count(),
            'default_project_count': range(1, 14),
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MembersComingView(BaseTemplateView):
    template_name = 'default/employee_list.html'

    def get(self, request, *args, **kwargs):
        param_dict, params = common.get_request_params(request.GET)

        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['first_name', 'section', 'subcontractor__name',
                                                  'salesperson__first_name'])
        order_list = common.get_ordering_list(o)

        all_members = biz.get_members_in_coming()
        if param_dict:
            all_members = all_members.filter(**param_dict)
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

        context = self.get_context_data()
        context.update({
            'title': u'入社予定社員一覧 | %s' % constants.NAME_SYSTEM,
            'members': members,
            'sections': models.Section.objects.public_filter(is_on_sales=True),
            'salesperson': models.Salesperson.objects.public_all(),
            'paginator': paginator,
            'params': "&" + params if params else "",
            'dict_order': dict_order,
            'page_type': "members_in_coming",
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MembersSubcontractorView(BaseTemplateView):
    template_name = 'default/employee_list.html'

    def get_context_data(self, **kwargs):
        context = super(MembersSubcontractorView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        status = request.GET.get('_status', None)
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member_name', 'division_name', 'section_name', 'salesofreason_name',
                                                  'subsection_name', 'subcontractor_name', 'salesperson_name'])
        order_list = common.get_ordering_list(o)
        today = datetime.date.today()
        year = str(today.year)
        month = '%02d' % today.month

        if status == "sales":
            data_frame = biz.get_sales_on_members(year, month, param_dict=param_dict, order_list=order_list)
        elif status == "working":
            data_frame = biz.get_working_members(year, month, param_dict=param_dict, order_list=order_list)
        elif status == "waiting":
            data_frame = biz.get_waiting_members(year, month, param_dict=param_dict, order_list=order_list)
        elif status == "off_sales":
            data_frame = biz.get_sales_off_members(year, month, param_dict=param_dict, order_list=order_list)
        else:
            data_frame = biz.get_sales_members(year, month, param_dict=param_dict, order_list=order_list)

        data_frame = data_frame.loc[data_frame.subcontactor_id.isnull() == False]
        paginator = Paginator(list(data_frame.iterrows()), biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context.update({
            'title': u'協力社員一覧 | %s' % constants.NAME_SYSTEM,
            'object_list': object_list,
            'sections': models.Section.objects.public_filter(is_on_sales=True),
            'salesperson': models.Salesperson.objects.public_all(),
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
            'page_type': "off_sales" if status == "off_sales" else None,
        })
        return context


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class MemberChangeListView(BaseTemplateView):
    template_name = 'default/member_change_list.html'

    def get(self, request, *args, **kwargs):
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['first_name', 'section__name', 'salesperson__first_name'])
        order_list = common.get_ordering_list(o)

        all_members = biz.get_next_change_list()
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

        context = self.get_context_data()
        context.update({
            'title': u'入退場リスト | %s' % constants.NAME_SYSTEM,
            'members': members,
            'paginator': paginator,
            'dict_order': dict_order,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_project', raise_exception=True), name='get')
class ProjectListView(BaseTemplateView):
    template_name = 'default/project_list.html'

    def get(self, request, *args, **kwargs):
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        q = request.GET.get('q', None)
        dict_order = common.get_ordering_dict(o, ['name', 'client__name', 'salesperson__first_name', 'boss__name',
                                                  'middleman__name', 'update_date', 'business_type'])
        order_list = common.get_ordering_list(o)
        all_projects = biz.get_projects(q=param_dict, o=order_list)

        if q:
            orm_lookups = ['name__icontains', 'client__name__icontains']
            for bit in q.split():
                or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                all_projects = all_projects.filter(reduce(operator.or_, or_queries))

        paginator = Paginator(all_projects, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            projects = paginator.page(page)
        except PageNotAnInteger:
            projects = paginator.page(1)
        except EmptyPage:
            projects = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'案件一覧 | %s' % constants.NAME_SYSTEM,
            'projects': projects,
            'paginator': paginator,
            'salesperson': models.Salesperson.objects.public_all(),
            'params': params,
            'orders': "&o=%s" % (o,) if o else "",
            'dict_order': dict_order,
        })
        return self.render_to_response(context)


class ProjectEndView(BaseView):

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', 0)
        params = ""
        for p, v in dict(request.GET).items():
            params += "&%s=%s" % (p, v[0])
        params = params[1:] if params else ""
        src = request.GET.get('from', None)

        project = get_object_or_404(models.Project, pk=project_id)
        project.status = 5

        if src == 'home':
            return redirect(reverse('index') + "?" + params)
        else:
            return redirect(reverse('project_list') + "?" + params)


@method_decorator(permission_required('eb.view_project', raise_exception=True), name='get')
@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class ProjectOrdersView(BaseTemplateView):
    template_name = 'default/project_order_list.html'

    def get(self, request, *args, **kwargs):
        param_dict, params = common.get_request_params(request.GET)
        year = request.GET.get('_year', None)
        month = request.GET.get('_month', None)
        if not year or not month:
            today = common.add_months(datetime.date.today(), -1)
            year = "%04d" % today.year
            month = "%02d" % today.month
        ym = year + month
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['project__name', 'project__client__name',
                                                  'clientorder__order_no', 'project__projectrequest__request_no'])
        order_list = common.get_ordering_list(o)

        all_project_orders = biz.get_projects_orders(ym, q=param_dict, o=order_list)

        paginator = Paginator(all_project_orders, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            project_orders = paginator.page(page)
        except PageNotAnInteger:
            project_orders = paginator.page(1)
        except EmptyPage:
            project_orders = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'%s年%s月の注文情報一覧 | %s' % (ym[:4], ym[4:], constants.NAME_SYSTEM),
            'project_orders': project_orders,
            'paginator': paginator,
            'dict_order': dict_order,
            'params': params,
            'orders': "&o=%s" % (o,) if o else "",
            'year': year,
            'month': month,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_project', raise_exception=True), name='get')
class ProjectDetailView(BaseTemplateView):
    template_name = 'default/project_detail.html'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = get_object_or_404(models.Project, pk=project_id)

        context = self.get_context_data()
        context.update({
            'title': u'%s - 案件詳細 | %s' % (project.name, constants.NAME_SYSTEM),
            'project': project,
            'banks': models.BankInfo.objects.public_all(),
            'order_month_list': project.get_year_month_order_finished(),
            'attendance_month_list': project.get_year_month_attendance_finished(),
        })
        context.update(csrf(request))
        return self.render_to_response(context)


class ProjectOrderMemberAssignView(BaseView):

    def post(self, request, *args, **kwargs):
        pm_list = request.POST.get("pm_list", None)
        order_id = request.POST.get("order_id", None)
        d = dict()
        if pm_list and order_id:
            try:
                client_order = models.ClientOrder.objects.get(pk=order_id)
                client_order.member_comma_list = pm_list.strip(",")
                client_order.save()
                d['result'] = True
                d['message'] = u"成功しました。"
            except ObjectDoesNotExist:
                d['result'] = False
                d['message'] = u"注文書が削除されました。"
        else:
            d['result'] = False
            d['message'] = u"パラメータは空です。"
        return HttpResponse(json.dumps(d))


class ProjectMembersByOrderView(BaseView):

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id', 0)
        d = dict()
        try:
            client_order = models.ClientOrder.objects.get(pk=order_id)
            d['pm_list'] = client_order.member_comma_list
        except ObjectDoesNotExist:
            d['pm_list'] = ''
        return HttpResponse(json.dumps(d))


@method_decorator(permission_required('eb.input_attendance', raise_exception=True), name='dispatch')
class ProjectAttendanceView(BaseTemplateView):
    template_name = 'default/project_attendance_list.html'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = get_object_or_404(models.Project, pk=project_id)
        ym = request.GET.get('ym', None)

        context = self.get_context_data()
        context.update({
            'title': u'%s - 勤怠入力' % (project.name,),
            'project': project,
        })
        context.update(csrf(request))

        if ym:
            str_year = ym[:4]
            str_month = ym[4:]
            date = datetime.date(int(str_year), int(str_month), 1)
            initial_form_count = 0
            try:
                project_members = project.get_project_members_by_month(date)
                dict_initials = []
                for project_member in project_members:
                    # 既に入力済みの場合、DBから取得する。
                    attendance = project_member.get_attendance(date.year, date.month)
                    if attendance:
                        initial_form_count += 1
                        if project.is_hourly_pay:
                            d = {'id': attendance.pk,
                                 'pk': attendance.pk,
                                 'project_member': attendance.project_member,
                                 'year': str_year,
                                 'month': str_month,
                                 'total_hours': attendance.total_hours,
                                 'extra_hours': attendance.extra_hours,
                                 'price': attendance.price,
                                 'comment': attendance.comment,
                                 'hourly_pay': project_member.hourly_pay
                                 }
                        else:
                            d = {'id': attendance.pk,
                                 'pk': attendance.pk,
                                 'project_member': attendance.project_member,
                                 'year': str_year,
                                 'month': str_month,
                                 'basic_price': attendance.project_member.price,
                                 'max_hours': attendance.project_member.max_hours,
                                 'min_hours': attendance.project_member.min_hours,
                                 'rate': attendance.rate,
                                 'total_hours': attendance.total_hours,
                                 'extra_hours': attendance.extra_hours,
                                 'plus_per_hour': project_member.plus_per_hour,
                                 'minus_per_hour': project_member.minus_per_hour,
                                 'price': attendance.price,
                                 'comment': attendance.comment,
                                 }
                    else:
                        # まだ入力してない場合、EBOAの出勤情報から取得する。
                        total_hours = biz.get_attendance_time_from_eboa(project_member, date.year, date.month)
                        if project.is_hourly_pay:
                            d = {'id': u"",
                                 'project_member': project_member,
                                 'year': str_year,
                                 'month': str_month,
                                 'total_hours': total_hours,
                                 'hourly_pay': project_member.hourly_pay
                                 }
                        else:
                            total_price = 0
                            if total_hours > project_member.max_hours:
                                extra_hours = total_hours - float(project_member.max_hours)
                                total_price = project_member.price + (extra_hours * project_member.plus_per_hour)
                            elif 0 < total_hours < project_member.min_hours:
                                extra_hours = total_hours - float(project_member.min_hours)
                                total_price = project_member.price + (extra_hours * project_member.minus_per_hour)
                            elif total_hours > 0:
                                extra_hours = 0
                                total_price = project_member.price
                            else:
                                extra_hours = 0
                            d = {'id': u"",
                                 'project_member': project_member,
                                 'year': str_year,
                                 'month': str_month,
                                 'basic_price': project_member.price,
                                 'total_hours': total_hours,
                                 'extra_hours': extra_hours,
                                 'max_hours': project_member.max_hours,
                                 'min_hours': project_member.min_hours,
                                 'plus_per_hour': project_member.plus_per_hour,
                                 'minus_per_hour': project_member.minus_per_hour,
                                 'price': total_price,
                                 }
                    dict_initials.append(d)
                if project.is_hourly_pay:
                    attendance_formset = modelformset_factory(models.MemberAttendance,
                                                              form=forms.MemberAttendanceFormSetHourlyPay,
                                                              extra=len(project_members))
                else:
                    attendance_formset = modelformset_factory(models.MemberAttendance,
                                                              form=forms.MemberAttendanceFormSet,
                                                              extra=len(project_members))
                dict_initials.sort(key=lambda item: item['id'])
                context['formset'] = attendance_formset(queryset=models.MemberAttendance.objects.none(),
                                                        initial=dict_initials)
            except Exception as e:
                context['formset'] = None
                print e.message

            context['initial_form_count'] = initial_form_count

            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = get_object_or_404(models.Project, pk=project_id)

        context = self.get_context_data()
        context.update({
            'title': u'%s - 勤怠入力' % (project.name,),
            'project': project,
        })
        context.update(csrf(request))

        if project.is_hourly_pay:
            attendance_formset = modelformset_factory(models.MemberAttendance,
                                                      form=forms.MemberAttendanceFormSetHourlyPay,
                                                      extra=0)
        else:
            attendance_formset = modelformset_factory(models.MemberAttendance,
                                                      form=forms.MemberAttendanceFormSet, extra=0)
        formset = attendance_formset(request.POST)
        if formset.is_valid():
            attendance_list = formset.save(commit=False)
            for i, attendance in enumerate(attendance_list):
                if not attendance.pk:
                    attendance_id = request.POST.get("form-%s-id" % (i,), None)
                    attendance.pk = int(attendance_id) if attendance_id else None
                action_flag = CHANGE if attendance.pk else ADDITION
                attendance.save()
                if action_flag == ADDITION:
                    LogEntry.objects.log_action(request.user.id,
                                                ContentType.objects.get_for_model(attendance).pk,
                                                attendance.pk,
                                                unicode(attendance),
                                                action_flag)
            return redirect(reverse("project_detail", args=(project.pk,)))
        else:
            context.update({'formset': formset})
            return self.render_to_response(context)


@method_decorator(permission_required('eb.view_project', raise_exception=True), name='get')
class ProjectMembersView(BaseTemplateView):
    template_name = 'default/project_members.html'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', None)
        project = get_object_or_404(models.Project, pk=project_id)
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member__first_name', 'start_date', 'end_date', 'price'])
        order_list = common.get_ordering_list(o)

        all_project_members = project.projectmember_set.all()
        if param_dict:
            all_project_members = all_project_members.filter(**param_dict)

        # 現在所属の営業員を取得
        today = datetime.date.today()
        salesoff_set = models.MemberSalesOffPeriod.objects.filter(
            (Q(start_date__lte=today) & Q(end_date__isnull=True)) |
            (Q(start_date__lte=today) & Q(end_date__gte=today)))

        all_project_members = all_project_members.prefetch_related(
            Prefetch('member__membersalesoffperiod_set', queryset=salesoff_set, to_attr='current_salesoff_period'),
        )
        if order_list:
            all_project_members = all_project_members.order_by(*order_list)

        paginator = Paginator(all_project_members, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            project_members = paginator.page(page)
        except PageNotAnInteger:
            project_members = paginator.page(1)
        except EmptyPage:
            project_members = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'案件参加者一覧 | %s' % (project.name,),
            'project': project,
            'project_members': project_members,
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
        })
        return self.render_to_response(context)


class SectionListView(BaseTemplateView):
    template_name = 'default/section_list.html'

    def get(self, request, *args, **kwargs):
        sections = biz.get_on_sales_top_org()

        context = self.get_context_data()
        context.update({
            'title': u'部署情報一覧 | %s' % constants.NAME_SYSTEM,
            'sections': sections,
        })
        return self.render_to_response(context)


class SectionDetailView(BaseTemplateView):
    template_name = 'default/section_detail.html'

    def get(self, request, *args, **kwargs):
        section_id = kwargs.get('section_id', 0)
        section = get_object_or_404(models.Section, pk=section_id)
        all_members_period = section.get_members_period()

        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member__first_name', 'start_date',
                                                  'division', 'section', 'subsection'])
        order_list = common.get_ordering_list(o)

        if order_list:
            all_members_period = all_members_period.order_by(*order_list)

        paginator = Paginator(all_members_period, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            members_period = paginator.page(page)
        except PageNotAnInteger:
            members_period = paginator.page(1)
        except EmptyPage:
            members_period = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'%s | 部署 | %s' % (section.name, constants.NAME_SYSTEM),
            'section': section,
            'members_period': members_period,
            'dict_order': dict_order,
            'paginator': paginator,
            'year_list': biz.get_year_list(),
            'orders': "&o=%s" % (o,) if o else "",
        })
        return self.render_to_response(context)


class OrganizationTurnoverView(BaseTemplateView):
    template_name = 'default/organization_turnover.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationTurnoverView, self).get_context_data(**kwargs)
        today = datetime.date.today()
        section_id = kwargs.get('section_id', 0)
        section = get_object_or_404(models.Section, pk=section_id)
        request = kwargs.get('request')
        year = kwargs.get('year')
        month = kwargs.get('month')
        prev_month = common.add_months(datetime.date(int(year), int(month), 1), -1)
        next_month = common.add_months(datetime.date(int(year), int(month), 1), 1)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['first_name', 'employee_id', 'company_name', 'project_name',
                                                  'client_name', 'member_type'])
        order_list = common.get_ordering_list(o)

        data_frame = biz.get_organization_turnover(year, month, section, order_list=order_list)
        df = biz.get_organization_turnover(year, month, order_list=order_list)
        summary_subcontractor = data_frame.loc[data_frame.member_type == 4].sum()
        summary_self = data_frame.loc[data_frame.member_type != 4].sum()

        context.update({
            'title': u'出勤 | %s年%s月 | %s | %s' % (year, month, section.name, constants.NAME_SYSTEM),
            'section': section,
            'year': year,
            'month': month,
            'prev_month': prev_month,
            'next_month': next_month,
            'data_frame': data_frame,
            'summary_subcontractor': summary_subcontractor,
            'summary_self': summary_self,
            'dict_order': dict_order,
        })
        context.update(csrf(request))
        return context

    def post(self, request, *args, **kwargs):
        kwargs['request'] = request
        context = self.get_context_data(**kwargs)
        year = context.get('year')
        month = context.get('month')
        input_excel = request.FILES['attendance_file']
        format_error, messages = file_loader.load_section_attendance(input_excel.read(), year, month, request.user.id)
        context['format_error'] = format_error
        if format_error:
            return self.render_to_response(context)
        else:
            section = context.get('section')
            return redirect(reverse("organization_turnover", args=(section.pk, year, month)))


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class ProjectRequestView(BaseTemplateView):
    template_name = 'default/project_request.html'

    def get(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id', 0)
        project_request = get_object_or_404(models.ProjectRequest, pk=request_id)
        if hasattr(project_request, 'projectrequestheading'):
            request_heading = project_request.projectrequestheading
        else:
            request_heading = None
        request_details = list(project_request.projectrequestdetail_set.all())
        project_members = [detail.project_member for detail in request_details]
        detail_expenses, expenses_amount = biz.get_request_expenses_list(project_request.project,
                                                                         project_request.year,
                                                                         project_request.month,
                                                                         project_members)
        if len(request_details) < 20:
            request_details.extend([None] * (20 - len(request_details)))

        context = self.get_context_data()
        title_args = (project_request.project.name, project_request.year, project_request.month)
        context.update({
            'title': u'請求書 | %s | %s年%s月' % title_args,
            'project_request': project_request,
            'request_heading': request_heading,
            'request_details': request_details,
            'detail_expenses': detail_expenses,
        })
        return self.render_to_response(context)


class SubcontractorRequestView(BaseTemplateView):
    template_name = 'default/project_request.html'

    def get(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id', 0)
        subcontractor_request = get_object_or_404(models.SubcontractorRequest, pk=request_id)
        if hasattr(subcontractor_request, 'subcontractorrequestheading'):
            request_heading = subcontractor_request.subcontractorrequestheading
        else:
            request_heading = None
        request_details = list(subcontractor_request.subcontractorrequestdetail_set.all())
        project_members = [detail.project_member for detail in request_details]
        detail_expenses, expenses_amount = biz.get_subcontractor_request_expenses_list(
            subcontractor_request.year,
            subcontractor_request.month,
            project_members
        )
        if len(request_details) < 20:
            request_details.extend([None] * (20 - len(request_details)))

        context = self.get_context_data()
        title_args = (unicode(subcontractor_request.subcontractor),
                      subcontractor_request.year,
                      subcontractor_request.month)
        context.update({
            'title': u'請求書 | %s | %s年%s月' % title_args,
            'project_request': subcontractor_request,
            'request_heading': request_heading,
            'request_details': request_details,
            'detail_expenses': detail_expenses,
        })
        return self.render_to_response(context)


class SubcontractorPayNotifyView(BaseTemplateView):
    template_name = 'default/subcontractor_pay_notify.html'

    def get(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id', 0)
        subcontractor_request = get_object_or_404(models.SubcontractorRequest, pk=request_id)
        if hasattr(subcontractor_request, 'subcontractorrequestheading'):
            request_heading = subcontractor_request.subcontractorrequestheading
        else:
            request_heading = None
        request_details = list(subcontractor_request.subcontractorrequestdetail_set.all())
        detail_expenses = sum([d.expenses_price for d in request_details])

        context = self.get_context_data()
        title_args = (unicode(subcontractor_request.subcontractor),
                      subcontractor_request.year,
                      subcontractor_request.month)
        context.update({
            'title': u'支払通知書 | %s | %s年%s月' % title_args,
            'project_request': subcontractor_request,
            'request_heading': request_heading,
            'request_details': request_details,
            'detail_expenses': detail_expenses,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverCompanyYearlyView(BaseTemplateView):
    template_name = 'default/turnover_company_yearly.html'

    def get(self, request, *args, **kwargs):
        company_turnover = biz_turnover.turnover_company_year()
        company_turnover2 = biz_turnover.turnover_company_year2()

        context = self.get_context_data()
        context.update({
            'title': u'年間売上情報 | %s' % constants.NAME_SYSTEM,
            'company_turnover': company_turnover,
            'company_turnover2': company_turnover2,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverCompanyMonthlyView(BaseTemplateView):
    template_name = 'default/turnover_company_monthly.html'

    def get(self, request, *args, **kwargs):
        company_turnover = biz_turnover.turnover_company_monthly()
        month_list = [str(item['ym']) for item in company_turnover]
        turnover_amount_list = [item['turnover_amount'] for item in company_turnover]

        context = self.get_context_data()
        context.update({
            'title': u'売上情報 | %s' % constants.NAME_SYSTEM,
            'company_turnover': company_turnover,
            'month_list': month_list,
            'turnover_amount_list': turnover_amount_list,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverChartsMonthlyView(BaseTemplateView):
    template_name = 'default/turnover_charts_monthly.html'

    def get(self, request, *args, **kwargs):
        ym = kwargs.get('ym', None)
        sections_turnover = biz_turnover.sections_turnover_monthly(ym)
        section_attendance_amount_list = [item['attendance_amount'] for item in sections_turnover]
        section_attendance_tex_list = [item['attendance_tex'] for item in sections_turnover]
        section_expenses_amount_list = [item['expenses_amount'] for item in sections_turnover]
        section_name_list = ["'" + item['section'].name + "'" for item in sections_turnover]

        salesperson_turnover = biz_turnover.salesperson_turnover_monthly(ym)
        salesperson_attendance_amount_list = [item['attendance_amount'] for item in salesperson_turnover]
        salesperson_attendance_tex_list = [item['attendance_tex'] for item in salesperson_turnover]
        salesperson_expenses_amount_list = [item['expenses_amount'] for item in salesperson_turnover]
        salesperson_name_list = ["'" + unicode(item['salesperson']) + "'" for item in salesperson_turnover]

        clients_turnover = biz_turnover.clients_turnover_monthly(ym[:4], ym[4:])
        clients_attendance_amount_list = [item['attendance_amount'] for item in clients_turnover]
        clients_attendance_tex_list = [item['attendance_tex'] for item in clients_turnover]
        clients_expenses_amount_list = [item['expenses_amount'] for item in clients_turnover]
        clients_name_list = ["'" + item['client'].name + "'" for item in clients_turnover]

        context = self.get_context_data()
        context.update({
            'title': u'%s - 売上情報 | %s' % (ym, constants.NAME_SYSTEM),
            'sections_turnover': sections_turnover,
            'section_name_list': ",".join(section_name_list),
            'section_attendance_amount_list': section_attendance_amount_list,
            'section_attendance_tex_list': section_attendance_tex_list,
            'section_expenses_amount_list': section_expenses_amount_list,
            'salesperson_turnover': salesperson_turnover,
            'salesperson_name_list': ",".join(salesperson_name_list),
            'salesperson_attendance_amount_list': salesperson_attendance_amount_list,
            'salesperson_attendance_tex_list': salesperson_attendance_tex_list,
            'salesperson_expenses_amount_list': salesperson_expenses_amount_list,
            'clients_turnover': clients_turnover,
            'clients_name_list': ",".join(clients_name_list),
            'clients_attendance_amount_list': clients_attendance_amount_list,
            'clients_attendance_tex_list': clients_attendance_tex_list,
            'clients_expenses_amount_list': clients_expenses_amount_list,
            'ym': ym,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverMembersMonthlyView(BaseTemplateView):
    template_name = 'default/turnover_members_monthly.html'

    def get(self, request, *args, **kwargs):
        ym = kwargs.get('ym', None)
        year = ym[:4]
        month = ym[4:]
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member_name',
                                                  'section_name',
                                                  'project_name',
                                                  'client_name'])
        order_list = common.get_ordering_list(o)

        sections = biz_turnover.get_turnover_sections(ym)
        data_frame = biz_turnover.get_members_turnover(year, month, param_dict=param_dict, order_list=order_list)
        summary = data_frame.sum()
        summary['profit_rate'] = round(summary.profit / summary.total_price, 2) * 100 if summary.total_price else 0

        paginator = Paginator(list(data_frame.iterrows()), biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'%s年%s月の売上詳細情報' % (year, month),
            'sections': sections,
            'salesperson': models.Salesperson.objects.public_all(),
            'object_list': object_list,
            'summary': summary,
            'paginator': paginator,
            'dict_order': dict_order,
            'orders': "&o=%s" % (o,) if o else "",
            'params': params,
            'ym': ym,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverClientsYearlyView(BaseTemplateView):
    template_name = 'default/turnover_clients_yearly.html'

    def get(self, request, *args, **kwargs):
        year = kwargs.get('year', None)
        data_type = request.GET.get('data_type', "1")
        if data_type == '2':
            clients_turnover = biz_turnover.clients_turnover_yearly(year, data_type=2)
        else:
            clients_turnover = biz_turnover.clients_turnover_yearly(year)

        summary = {'attendance_amount': 0, 'expenses_amount': 0,
                   'attendance_tex': 0, 'all_amount': 0}
        for item in clients_turnover:
            summary['attendance_amount'] += item['attendance_amount']
            summary['attendance_tex'] += item['attendance_tex']
            summary['expenses_amount'] += item['expenses_amount']
            summary['all_amount'] += item['attendance_amount'] + item['attendance_tex'] + item['expenses_amount']
        max_attendance_amount = max([d['attendance_amount'] for d in clients_turnover])
        for item in clients_turnover:
            item['per'] = '%.1f%%' % ((item['attendance_amount'] / float(max_attendance_amount)) * 100)

        context = self.get_context_data()
        context.update({
            'title': u'%s年のお客様別売上情報 | %s' % (year, constants.NAME_SYSTEM),
            'clients_turnover': clients_turnover,
            'data_type': data_type,
            'year': year,
            'summary': summary,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverClientsMonthlyView(BaseTemplateView):
    template_name = 'default/turnover_clients_monthly.html'

    def get(self, request, *args, **kwargs):
        year = kwargs.get('year', None)
        month = kwargs.get('month', None)
        data_frame = biz_turnover.get_clients_turnover(year, month)
        summary = data_frame.sum()
        summary['profit_rate'] = round(summary.profit / summary.total_price, 2) * 100 if summary.total_price else 0

        context = self.get_context_data()
        context.update({
            'title': u'%s年%s月のお客様別売上情報 | %s' % (year, month, constants.NAME_SYSTEM),
            'data_frame': data_frame,
            'summary': summary,
            'year': year,
            'month': month,
            'ym': year + month,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverClientMonthlyView(BaseTemplateView):
    template_name = 'default/turnover_projects_monthly.html'

    def get(self, request, *args, **kwargs):
        client_id = kwargs.get('client_id', 0)
        ym = kwargs.get('ym', None)
        year = ym[:4]
        month = ym[4:]
        client = get_object_or_404(models.Client, pk=client_id)
        data_frame = biz_turnover.get_client_turnover(year, month, client)
        summary = data_frame.sum()
        summary['profit_rate'] = round(summary.profit / summary.total_price, 2) * 100 if summary.total_price else 0

        context = self.get_context_data()
        context.update({
            'title': u'%s年%s月　%sの案件別売上情報 | %s' % (year, month, unicode(client), constants.NAME_SYSTEM),
            'client': client,
            'data_frame': data_frame,
            'summary': summary,
            'ym': ym,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverClientYearlyView(BaseTemplateView):
    template_name = 'default/turnover_client_yearly.html'

    def get_context_data(self, **kwargs):
        context = super(TurnoverClientYearlyView, self).get_context_data(**kwargs)
        client_id = kwargs.get('client_id', 0)
        client = get_object_or_404(models.Client, pk=client_id)

        context.update({
            'title': u"%s の売上分析" % unicode(client),
            'client': client,
        })
        return context


@method_decorator(permission_required('eb.view_turnover', raise_exception=True), name='get')
class TurnoverBusinessTypeByYearView(BaseTemplateView):
    template_name = 'default/turnover_business_type_by_year.html'

    def get_context_data(self, **kwargs):
        context = super(TurnoverBusinessTypeByYearView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        year = kwargs.get('year', 0)
        data_type = request.GET.get('data_type', "1")
        # if data_type == '2':
        #     title = "%s年度(%s04～%s03) の事業別売上ブレイクダウン" % (year, year, int(year) + 1)
        # else:
        #     title = "%s年度(%s01～%s12) の事業別売上ブレイクダウン" % (year, year, year)

        context.update({
            'title': "%s年度 の事業別売上ブレイクダウン" % year,
            'year': year,
            'data_type': data_type,
        })
        return context


@method_decorator(permission_required('eb.view_member', raise_exception=True), name='get')
class ReleaseListView(BaseTemplateView):
    template_name = 'default/release_list.html'

    def get(self, request, *args, **kwargs):
        ym = kwargs.get('ym', None)
        param_dict, params = common.get_request_params(request.GET)
        year = int(ym[0:4])
        month = int(ym[-2:])
        section_id = request.GET.get('section', None)

        if 'section' in param_dict:
            del param_dict['section']

        members = models.ViewRelease.objects.filter(release_ym=ym)
        if param_dict:
            members = members.filter(**param_dict)
        if section_id:
            organization = get_object_or_404(models.Section, pk=section_id)
            org_pk_list = common.get_organization_children(organization)
            members = members.filter(Q(division__in=org_pk_list) | Q(section__in=org_pk_list) | Q(subsection__in=org_pk_list))

        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['member__first_name', 'member__subcontractor__name',
                                                  'project__name', 'project_member__start_date',
                                                  'salesperson__first_name'])
        order_list = common.get_ordering_list(o)
        if order_list:
            members = members.order_by(*order_list)

        sections = models.Section.objects.public_filter(is_on_sales=True)
        salesperson = models.Salesperson.objects.public_all()

        paginator = Paginator(members, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            members = paginator.page(page)
        except PageNotAnInteger:
            members = paginator.page(1)
        except EmptyPage:
            members = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'%s年%s月 | リリース状況一覧 | %s' % (year, month, constants.NAME_SYSTEM),
            'members': members,
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
            'ym': ym,
            'sections': sections,
            'salesperson': salesperson,
        })
        return self.render_to_response(context)


class MemberProjectsView(BaseTemplateView):
    template_name = 'default/member_project_list.html'

    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get('employee_id', '')
        status = request.GET.get('status', None)
        member = get_object_or_404(models.Member, employee_id=employee_id)
        if status and status != '0':
            project_members = models.ProjectMember.objects.public_filter(member=member, status=status)\
                .order_by('-status', 'end_date')
        else:
            project_members = models.ProjectMember.objects.public_filter(member=member)\
                .order_by('-status', 'end_date')

        context = self.get_context_data()
        context.update({
            'member': member,
            'title': u'%s の案件一覧 | %s' % (member, constants.NAME_SYSTEM),
            'project_members': project_members,
        })
        return self.render_to_response(context)


class RecommendedMembersView(BaseTemplateView):
    template_name = 'default/recommended_member.html'

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', 0)
        project = get_object_or_404(models.Project, pk=project_id)
        dict_skills = project.get_recommended_members()

        context = self.get_context_data()
        context.update({
            'title': u'%s - 推薦されるメンバーズ | %s' % (project.name, constants.NAME_SYSTEM),
            'project': project,
            'dict_skills': dict_skills,
        })
        return self.render_to_response(context)


class RecommendedProjectsView(BaseTemplateView):
    template_name = 'default/recommended_project.html'

    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get('employee_id', '')
        member = get_object_or_404(models.Member, employee_id=employee_id)
        skills = member.get_skill_list()
        project_id_list = member.get_recommended_projects()
        projects = models.Project.objects.public_filter(pk__in=project_id_list)

        context = self.get_context_data()
        context.update({
            'title': u'%s - 推薦される案件 | %s' % (member, constants.NAME_SYSTEM),
            'member': member,
            'skills': skills,
            'projects': projects,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class SubcontractorListView(BaseTemplateView):
    template_name = 'default/subcontractor_list.html'

    def get(self, request, *args, **kwargs):
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['name'])
        order_list = common.get_ordering_list(o)

        all_subcontractors = models.Subcontractor.objects.public_all()
        if param_dict:
            all_subcontractors = all_subcontractors.filter(**param_dict)
        if order_list:
            all_subcontractors = all_subcontractors.order_by(*order_list)

        paginator = Paginator(all_subcontractors, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            subcontractors = paginator.page(page)
        except PageNotAnInteger:
            subcontractors = paginator.page(1)
        except EmptyPage:
            subcontractors = paginator.page(paginator.num_pages)

        context = self.get_context_data()
        context.update({
            'title': u'協力会社一覧 | %s' % constants.NAME_SYSTEM,
            'subcontractors': subcontractors,
            'paginator': paginator,
            'params': params,
            'orders': "&o=%s" % (o,) if o else "",
            'dict_order': dict_order,
            'bp_count': models.Member.objects.public_filter(subcontractor__isnull=False).count(),
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class CostSubcontractorsMonthlyView(BaseTemplateView):
    template_name = 'default/cost_subcontractors_monthly.html'

    def get_context_data(self, **kwargs):
        context = super(CostSubcontractorsMonthlyView, self).get_context_data(**kwargs)
        object_list = biz_turnover.cost_subcontractors_monthly()

        context.update({
            'title': "協力会社月別コスト一覧",
            'object_list': object_list,
        })
        return context


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class CostSubcontractorMembersByMonthView(BaseTemplateView):
    template_name = 'default/cost_subcontractor_members_by_month.html'

    def get_context_data(self, **kwargs):
        context = super(CostSubcontractorMembersByMonthView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        year = kwargs.get('year')
        month = kwargs.get('month')
        subcontractor_id = kwargs.get('subcontractor_id', None)
        param_dict, params = common.get_request_params(request.GET)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['first_name', 'company_name', 'project_name'])
        order_list = common.get_ordering_list(o)

        data_frame = biz_turnover.get_bp_members_cost(year, month, subcontractor_id, param_dict, order_list)
        summary = data_frame.sum()
        object_list = list(data_frame.iterrows())

        subcontractor = None
        sections = []
        if subcontractor_id:
            subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)
            sections = subcontractor.get_request_sections(year, month)

        paginator = Paginator(object_list, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context.update({
            'title': u"%s年%s月の%sコスト一覧" % (
                year, month,
                '「' + unicode(subcontractor) + '」' if subcontractor else "ＢＰメンバー"
            ),
            'object_list': object_list,
            'summary': summary,
            'subcontractor': subcontractor,
            'sections': sections,
            'paginator': paginator,
            'params': params,
            'dict_order': dict_order,
            'orders': "&o=%s" % (o,) if o else "",
            'year': year,
            'month': month,
        })
        return context


class CostSubcontractorsByMonthView(BaseTemplateView):
    template_name = 'default/cost_subcontractors_by_month.html'

    def get_context_data(self, **kwargs):
        context = super(CostSubcontractorsByMonthView, self).get_context_data(**kwargs)
        year = kwargs.get('year')
        month = kwargs.get('month')

        data_frame = biz_turnover.get_bp_cost_by_subcontractor(year, month)

        context.update({
            'title': u"%s年%s月の協力会社別コスト" % (year, month),
            'data_frame': data_frame,
            'year': year,
            'month': month,
        })
        return context


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class SubcontractorDetailView(BaseTemplateView):
    template_name = 'default/subcontractor_detail.html'

    def get(self, request, *args, **kwargs):
        subcontractor_id = kwargs.get('subcontractor_id', 0)
        o = request.GET.get('o', None)
        dict_order = common.get_ordering_dict(o, ['first_name'])
        order_list = common.get_ordering_list(o)

        subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)
        all_members = subcontractor.member_set.all()
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

        context = self.get_context_data()
        context.update({
            'title': u'%s | 協力会社 | %s' % (subcontractor.name, constants.NAME_SYSTEM),
            'subcontractor': subcontractor,
            'members': members,
            'paginator': paginator,
            'orders': "&o=%s" % (o,) if o else "",
            'dict_order': dict_order,
            'order_month_list': subcontractor.get_year_month_order_finished(),
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class SubcontractorMembersView(BaseTemplateView):
    template_name = 'default/subcontractor_members.html'

    def get(self, request, *args, **kwargs):
        subcontractor_id = kwargs.get('subcontractor_id', 0)
        subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)
        ym = request.GET.get('ym', None)

        context = self.get_context_data()
        context.update({
            'title': u'注文情報入力 | %s | 協力会社 | %s' % (subcontractor.name, constants.NAME_SYSTEM),
            'subcontractor': subcontractor,
        })
        context.update(csrf(request))

        if ym:
            str_year = ym[:4]
            str_month = ym[4:]
        else:
            str_year = str(datetime.date.today().year)
            str_month = '%02d' % (datetime.date.today().month,)
            ym = str_year + str_month

        initial_form_count = 0
        first_day = common.get_first_day_from_ym(ym)
        # 現在案件実施中のメンバーを取得する。
        members = subcontractor.get_members_by_month(first_day)
        dict_initials = []
        for member in members:
            bp_member_info = member.get_bp_member_info(first_day)
            if bp_member_info:
                initial_form_count += 1
                d = {'id': bp_member_info.pk,
                     'pk': bp_member_info.pk,
                     'member': bp_member_info.member,
                     'year': bp_member_info.year,
                     'month': bp_member_info.month,
                     'min_hours': bp_member_info.min_hours,
                     'max_hours': bp_member_info.max_hours,
                     'cost': bp_member_info.cost,
                     'plus_per_hour': bp_member_info.plus_per_hour,
                     'minus_per_hour': bp_member_info.minus_per_hour,
                     'comment': bp_member_info.comment,
                     }
            else:
                d = {'id': u"",
                     'member': member,
                     'year': str_year,
                     'month': str_month,
                     'min_hours': 160,
                     'max_hours': 180,
                     'cost': member.cost,
                     'plus_per_hour': member.cost / 180,
                     'minus_per_hour': member.cost / 160,
                     'comment': "",
                     }
            dict_initials.append(d)
        bp_order_info_formset = modelformset_factory(models.BpMemberOrderInfo,
                                                     form=forms.BpMemberOrderInfoFormSet, extra=len(members))
        dict_initials.sort(key=lambda item: item['id'])
        formset = bp_order_info_formset(queryset=models.BpMemberOrderInfo.objects.none(), initial=dict_initials)

        context.update({'formset': formset, 'initial_form_count': initial_form_count})

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        subcontractor_id = kwargs.get('subcontractor_id', 0)
        subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)

        context = self.get_context_data()
        context.update({
            'title': u'注文情報入力 | %s | 協力会社 | %s' % (subcontractor.name, constants.NAME_SYSTEM),
            'subcontractor': subcontractor,
        })
        context.update(csrf(request))

        bp_order_info_formset = modelformset_factory(models.BpMemberOrderInfo,
                                                     form=forms.BpMemberOrderInfoFormSet, extra=0)
        formset = bp_order_info_formset(request.POST)
        if formset.is_valid():
            bp_member_list = formset.save(commit=False)
            for i, bp_member in enumerate(bp_member_list):
                # if not bp_member.pk:
                #     bp_member_id = request.POST.get("form-%s-id" % (i,), None)
                #     bp_member.pk = int(bp_member_id) if bp_member_id else None
                action_flag = CHANGE if bp_member.pk else ADDITION
                bp_member.save()
                change_messages = [
                    u"対象年(%s)" % bp_member.year,
                    u"対象月(%s)" % bp_member.month,
                    u"基準時間(%s)" % bp_member.min_hours,
                    u"最大時間(%s)" % bp_member.max_hours,
                    u"増(%s)" % bp_member.plus_per_hour,
                    u"減(%s)" % bp_member.minus_per_hour,
                    u"コスト(%s)" % bp_member.cost,
                    u"備考(%s)" % bp_member.comment,
                ]
                LogEntry.objects.log_action(request.user.id,
                                            ContentType.objects.get_for_model(bp_member).pk,
                                            bp_member.pk,
                                            unicode(bp_member),
                                            action_flag,
                                            change_message=u",".join(change_messages))
            return redirect(reverse('subcontractor_detail', args=(subcontractor_id,)))
        else:
            context.update({'formset': formset})
            template = loader.get_template('default/subcontractor_members.html')
            return HttpResponse(template.render(context, request))


@method_decorator(permission_required('eb.view_subcontractor', raise_exception=True), name='get')
class BpContractsView(BaseTemplateView):
    template_name = 'default/bp_contracts.html'

    def get_context_data(self, **kwargs):
        context = super(BpContractsView, self).get_context_data(**kwargs)
        request = kwargs.get('request')

        param_dict, params = common.get_request_params(request.GET)

        bp_contracts = biz.get_bp_latest_contracts()
        if param_dict:
            bp_contracts = bp_contracts.filter(**param_dict)

        paginator = Paginator(bp_contracts, biz_config.get_page_size())
        page = request.GET.get('page')
        try:
            bp_contracts = paginator.page(page)
        except PageNotAnInteger:
            bp_contracts = paginator.page(1)
        except EmptyPage:
            bp_contracts = paginator.page(paginator.num_pages)

        context.update({
            'title': u"ＢＰ契約一覧",
            'bp_contracts': bp_contracts,
            'salesperson_list': models.Salesperson.objects.public_all(),
            'paginator': paginator,
            'params': params,
        })
        return context


class BpMemberOrdersView(BaseTemplateView):
    template_name = 'default/bp_member_orders.html'

    def get_context_data(self, **kwargs):
        context = super(BpMemberOrdersView, self).get_context_data(**kwargs)
        member_id = kwargs.get('member_id')
        member = get_object_or_404(models.Member, pk=member_id)
        project_members = member.projectmember_set.public_filter(is_deleted=False).order_by('-start_date')
        context.update({
            'title': u"%s | ＢＰ注文書" % unicode(member),
            'member': member,
            'project_members': project_members,
            'year_list': common.get_year_list(),
            'month_list': common.get_month_list3(),
        })
        return context


class BpMemberOrderDetailView(BaseTemplateView):
    template_name = 'default/bp_member_order.html'

    def get_context_data(self, **kwargs):
        context = super(BpMemberOrderDetailView, self).get_context_data(**kwargs)
        request = kwargs.get('request')
        preview = kwargs.get('preview', False)
        if preview:
            project_member_id = kwargs.get('project_member_id')
            project_member = get_object_or_404(models.ProjectMember, pk=project_member_id)
            year = kwargs.get('year')
            month = kwargs.get('month')
            bp_order = models.BpMemberOrder.get_next_bp_order(project_member, year, month)
            error_message = u""
            try:
                contract = biz.get_bp_contract(project_member.member, year, month)
                data = biz.generate_bp_order_data(project_member, year, month, contract, request.user, bp_order)
            except Exception as ex:
                data = None
                error_message = ex.message if ex.message else unicode(ex)
            context.update({
                'data': data,
                'error_message': error_message,
            })
        else:
            order_id = kwargs.get('order_id')
            bp_order = get_object_or_404(models.BpMemberOrder, pk=order_id)
            context.update({
                'bp_order': bp_order,
            })
        context.update({
            'title': u"%s | %s(%s年%s月)" % (
                bp_order.order_no, unicode(bp_order.project_member),
                bp_order.year,
                bp_order.month,
            ),
        })
        return context


@login_required(login_url='/eb/login/')
@csrf_protect
def upload_resume(request):
    context = get_base_context()
    context.update({
        'title': u'履歴書をアップロード | %s' % constants.NAME_SYSTEM,
        'site_header': admin.site.site_header,
        'site_title': admin.site.site_title,
    })
    context.update(csrf(request))

    if request.method == 'POST':
        form = forms.UploadFileForm(request.POST, request.FILES)
        context.update({'form': form})
        if form.is_valid():
            input_excel = request.FILES['file']
            member_id = request.POST.get('select', None)
            new_member, members = file_loader.load_resume(input_excel.read(), int(member_id) if member_id else None)
            if members:
                # 同じ名前のメンバーが存在する場合
                context.update({'members': members, 'display': True})
            else:
                pass
    else:
        form = forms.UploadFileForm()
        context.update({'form': form})

    template = loader.get_template('default/upload_file.html')
    return HttpResponse(template.render(context, request))


class DownloadProjectQuotationView(BaseView):

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', 0)
        company = biz.get_company()
        project = get_object_or_404(models.Project, pk=project_id)
        try:
            now = datetime.datetime.now()
            path = file_gen.generate_quotation(project, request.user, company)
            filename = "見積書_%s.xls" % (now.strftime("%Y%m%d%H%M%S"),)
            response = HttpResponse(open(path, 'rb'), content_type="application/excel")
            response['Content-Disposition'] = "filename=" + urllib.quote(filename)
            # 一時ファイルを削除する。
            common.delete_temp_files(os.path.dirname(path))
            return response
        except errors.FileNotExistException, ex:
            return HttpResponse(u"<script>alert('%s');window.close();</script>" % (ex.message,))


class DownloadClientOrderView(BaseView):

    def get(self, request, *args, **kwargs):
        p = request.GET.get('path', None)
        if p:
            path = os.path.join(settings.MEDIA_ROOT, p.strip('./'))
            if os.path.exists(path):
                filename = os.path.basename(path)
                response = HttpResponse(open(path, 'rb'), content_type="application/excel")
                response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode("utf8"))
                return response


class DownloadSubcontractorOrderView(BaseView):

    def get(self, request, *args, **kwargs):
        subcontractor_id = kwargs.get('subcontractor_id', 0)
        company = biz.get_company()
        ym = request.GET.get('ym', None)
        subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)

        try:
            data = biz.generate_order_data(company, subcontractor, request.user, ym)
            path = file_gen.generate_order(company, data)
            filename = os.path.basename(path)
            response = HttpResponse(open(path, 'rb'), content_type="application/excel")
            response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('UTF-8'))
            return response
        except errors.FileNotExistException, ex:
            return HttpResponse(u"<script>alert('%s');window.close();</script>" % (ex.message,))


class DownloadBpMemberOrder(BaseView):

    def get(self, request, *args, **kwargs):
        project_member_id = kwargs.get('project_member_id')
        project_member = get_object_or_404(models.ProjectMember, pk=project_member_id)
        year = kwargs.get('year')
        month = kwargs.get('month')
        publish_date = request.GET.get('publish_date', None)
        end_year = request.GET.get('end_year', None)
        end_month = request.GET.get('end_month', None)
        is_request = kwargs.get('is_request')
        try:
            bp_order = models.BpMemberOrder.get_next_bp_order(project_member, year, month, publish_date=publish_date,
                                                              end_year=end_year, end_month=end_month)
            overwrite = request.GET.get("overwrite", None)
            if overwrite:
                if is_request:
                    filename = bp_order.filename_request if bp_order.filename_request else 'None'
                else:
                    filename = bp_order.filename if bp_order.filename else 'None'
                path = os.path.join(settings.GENERATED_FILES_ROOT, "partner_order",
                                    '%04d%02d' % (int(bp_order.year), int(bp_order.month)), filename)
                if not os.path.exists(path):
                    # ファイルが存在しない場合、エラーとする。
                    raise errors.FileNotExistException(constants.ERROR_BP_ORDER_FILE_NOT_EXISTS)
                LogEntry.objects.log_action(request.user.id,
                                            ContentType.objects.get_for_model(bp_order).pk,
                                            bp_order.pk,
                                            unicode(bp_order),
                                            CHANGE,
                                            u"ファイルをダウンロードしました：%s" % filename)
            else:
                contract = biz.get_bp_contract(project_member.member, year, month)
                data = biz.generate_bp_order_data(project_member, year, month, contract, request.user, bp_order,
                                                  publish_date=publish_date, end_year=end_year, end_month=end_month)
                template_path = common.get_template_order_path(contract, is_request)
                path = file_gen.generate_order(data=data, template_path=template_path, is_request=is_request)
                filename = os.path.basename(path)
                if not bp_order.pk:
                    bp_order.created_user = request.user
                    action_flag = ADDITION
                else:
                    action_flag = CHANGE
                bp_order.updated_user = request.user
                if is_request:
                    # 注文請書の場合
                    bp_order.filename_request = filename
                    bp_order.save()
                else:
                    bp_order.filename = filename
                    bp_order.save(data=data)
                if action_flag == ADDITION:
                    change_message = u'追加しました。'
                elif not is_request:
                    change_message = u'再作成しました。'
                else:
                    change_message = u"注文請書を作成しました。"
                LogEntry.objects.log_action(request.user.id,
                                            ContentType.objects.get_for_model(bp_order).pk,
                                            bp_order.pk,
                                            unicode(bp_order),
                                            action_flag,
                                            change_message)
            response = HttpResponse(open(path, 'rb'), content_type="application/excel")
            response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('UTF-8'))
            return response
        except Exception as ex:
            return HttpResponse(
                u"<script>alert('%s');window.close();</script>" % ex.message if ex.message else unicode(ex)
            )


@method_decorator(permission_required('eb.generate_request', raise_exception=True), name='get')
class DownloadProjectRequestView(BaseTemplateView):

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id', 0)
        company = biz.get_company()
        project = get_object_or_404(models.Project, pk=project_id)
        try:
            client_order_id = request.GET.get("client_order_id", None)
            client_order = models.ClientOrder.objects.get(pk=client_order_id)
            ym = request.GET.get("ym", None)
            first_day = common.get_first_day_from_ym(ym)
            project_request = project.get_project_request(ym[:4], ym[4:], client_order)
            overwrite = request.GET.get("overwrite", None)
            if overwrite:
                path = os.path.join(settings.GENERATED_FILES_ROOT, "project_request", str(ym), project_request.filename)
                if not os.path.exists(path):
                    # ファイルが存在しない場合、エラーとする。
                    raise errors.FileNotExistException(constants.ERROR_REQUEST_FILE_NOT_EXISTS)
                filename = project_request.filename
            else:
                if common.add_months(first_day, 1) < common.get_first_day_current_month() and project_request.filename:
                    # ２ヶ月前の請求書は生成できないようにする。
                    raise errors.CustomException(constants.ERROR_CANNOT_GENERATE_2MONTH_BEFORE)
                request_name = request.GET.get("request_name", None)
                bank_id = request.GET.get('bank', None)
                try:
                    bank = models.BankInfo.objects.get(pk=bank_id)
                except ObjectDoesNotExist:
                    bank = None
                project_request.request_name = request_name if request_name else project.name
                data = biz.generate_request_data(company, project, client_order, bank, ym, project_request)
                path = file_gen.generate_request(company, project, data, project_request.request_no, ym)
                filename = os.path.basename(path)
                project_request.filename = filename
                project_request.created_user = request.user if not project_request.pk else project_request.created_user
                project_request.updated_user = request.user
                # 請求履歴を保存する。
                action_flag = CHANGE if project_request.pk else ADDITION
                project_request.save(other_data=data)
                LogEntry.objects.log_action(request.user.id,
                                            ContentType.objects.get_for_model(project_request).pk,
                                            project_request.pk,
                                            unicode(project_request),
                                            action_flag,
                                            '' if action_flag == ADDITION else u'再作成しました。')

            response = HttpResponse(open(path, 'rb'), content_type="application/excel")
            response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('UTF-8'))
            return response
        except errors.MyBaseException, ex:
            return HttpResponse(u"<script>alert('%s');window.close();</script>" % (ex.message,))


class DownloadResumeView(BaseView):

    def get(self, request, *args, **kwargs):
        member_id = kwargs.get('member_id', 0)
        member = get_object_or_404(models.Member, pk=member_id)
        date = datetime.date.today().strftime("%Y%m")
        filename = constants.NAME_RESUME % (member.first_name + member.last_name, date)
        output = file_gen.generate_resume(member)
        response = HttpResponse(output.read(), content_type="application/ms-excel")
        response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('utf-8')) + ".xlsx"
        return response


class DownloadOrganizationTurnover(BaseView):
    def get(self, request, *args, **kwargs):
        section_id = kwargs.get('section_id', 0)
        year = kwargs.get('year', 0)
        month = kwargs.get('month', 0)
        section = get_object_or_404(models.Section, pk=section_id)
        batch = biz.get_batch_manage(constants.BATCH_SEND_ATTENDANCE_FORMAT)
        data_frame = biz.get_organization_turnover(year, month, section)
        filename = constants.NAME_SECTION_ATTENDANCE % (section.name, int(year), int(month))
        output = file_gen.generate_organization_turnover(
            request.user, batch.mail_template.attachment1.path, data_frame, year, month
        )
        response = HttpResponse(output, content_type="application/ms-excel")
        response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('utf-8')) + ".xlsx"
        return response


# class DownloadSectionAttendance(BaseView):
#
#     def get(self, request, *args, **kwargs):
#         section_id = kwargs.get('section_id', 0)
#         year = kwargs.get('year', 0)
#         month = kwargs.get('month', 0)
#         date = datetime.date(int(year), int(month), 21)
#         section = get_object_or_404(models.Section, pk=section_id)
#         batch = biz.get_batch_manage(constants.BATCH_SEND_ATTENDANCE_FORMAT)
#         project_members = biz.get_project_members_month_section(section, date)
#         lump_projects = biz.get_lump_projects_by_section(section, date)
#         filename = constants.NAME_SECTION_ATTENDANCE % (section.name, int(year), int(month))
#         output = file_gen.generate_attendance_format(
#             request.user, batch.mail_template.attachment1.path, project_members, lump_projects, year, month
#         )
#         response = HttpResponse(output, content_type="application/ms-excel")
#         response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('utf-8')) + ".xlsx"
#         return response


class DownloadMembersCostView(BaseView):

    def get(self, request, *args, **kwargs):
        section_id = request.GET.get('section', None)
        all_members = models.get_sales_members()
        if section_id:
            all_members = biz.get_members_by_section(all_members, section_id)
        now = datetime.datetime.now()
        filename = constants.NAME_MEMBERS_COST % now.strftime('%Y%m%d')
        output = file_gen.generate_members_cost(request.user, all_members)
        response = HttpResponse(output, content_type="application/ms-excel")
        response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('utf-8')) + ".xlsx"
        return response


class GenerateSubcontractorRequestView(BaseView):

    def post(self, request, *args, **kwargs):
        company = biz.get_company()
        subcontractor_id = kwargs.get(str('subcontractor_id'))
        org_id = kwargs.get(str('org_id'))
        year = kwargs.get(str('year'))
        month = kwargs.get(str('month'))
        organization = get_object_or_404(models.Section, pk=org_id)
        subcontractor = get_object_or_404(models.Subcontractor, pk=subcontractor_id)
        subcontractor_request = subcontractor.get_subcontractor_request(year, month, organization)
        data = biz.generate_subcontractor_request_data(subcontractor, year, month, subcontractor_request)
        # 協力会社請求書
        path = file_gen.generate_request_linux(subcontractor, data, subcontractor_request.request_no, year + month)
        filename = os.path.basename(path)
        subcontractor_request.filename = filename
        # お支払通知書
        path = file_gen.generate_pay_notify(data, template_path=common.get_template_pay_notify_path(company))
        filename = os.path.basename(path)
        subcontractor_request.pay_notify_filename = filename
        subcontractor_request.created_user = request.user if not subcontractor_request.pk \
            else subcontractor_request.created_user
        subcontractor_request.updated_user = request.user
        # 請求履歴を保存する。
        action_flag = CHANGE if subcontractor_request.pk else ADDITION
        subcontractor_request.save(other_data=data)
        LogEntry.objects.log_action(request.user.id,
                                    ContentType.objects.get_for_model(subcontractor_request).pk,
                                    subcontractor_request.pk,
                                    unicode(subcontractor_request),
                                    action_flag,
                                    '' if action_flag == ADDITION else u'再作成しました。')
        return JsonResponse({
            'pk': subcontractor_request.pk,
            'request_no': subcontractor_request.request_no
        })


class DownloadSubcontractorRequestView(BaseView):

    def get(self, request, *args, **kwargs):
        subcontractor_request_id = kwargs.get('subcontractor_request_id')
        subcontractor_request = get_object_or_404(models.SubcontractorRequest, pk=subcontractor_request_id)
        path = os.path.join(
            settings.GENERATED_FILES_ROOT,
            "subcontractor_request",
            subcontractor_request.year + subcontractor_request.month,
            subcontractor_request.filename
        )
        if not os.path.exists(path):
            # ファイルが存在しない場合、エラーとする。
            raise errors.FileNotExistException(constants.ERROR_REQUEST_FILE_NOT_EXISTS)
        filename = subcontractor_request.filename
        response = HttpResponse(open(path, 'rb'), content_type="application/excel")
        response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('UTF-8'))
        return response


class DownloadSubcontractorPayNotifyView(BaseView):

    def get(self, request, *args, **kwargs):
        subcontractor_request_id = kwargs.get('subcontractor_request_id')
        subcontractor_request = get_object_or_404(models.SubcontractorRequest, pk=subcontractor_request_id)
        path = os.path.join(
            settings.GENERATED_FILES_ROOT,
            "pay_notify",
            subcontractor_request.year + subcontractor_request.month,
            subcontractor_request.pay_notify_filename
        )
        if not os.path.exists(path):
            # ファイルが存在しない場合、エラーとする。
            raise errors.FileNotExistException(constants.ERROR_REQUEST_FILE_NOT_EXISTS)
        filename = subcontractor_request.pay_notify_filename
        response = HttpResponse(open(path, 'rb'), content_type="application/excel")
        response['Content-Disposition'] = "filename=" + urllib.quote(filename.encode('UTF-8'))
        return response


class ImageClientTurnoverChartView(BaseView):

    def get(self, request, *args, **kwargs):
        client_id = kwargs.get('client_id', 0)
        client = get_object_or_404(models.Client, pk=client_id)
        img_data = biz_turnover.client_turnover_monthly(client)
        response = HttpResponse(img_data, content_type="image/png")
        return response


class ImageClientsTurnoverMonthlyView(BaseView):

    def get(self, request, *args, **kwargs):
        year = kwargs.get('year', None)
        month = kwargs.get('month', None)
        img_data = biz_turnover.clients_turnover_monthly_pie_plot(year, month)
        response = HttpResponse(img_data, content_type="image/png")
        return response


class ImageTurnoverClientsYearlyView(BaseView):

    def get(self, request, *args, **kwargs):
        year = kwargs.get('year', None)
        data_type = request.GET.get('data_type', None)
        if data_type == '2':
            img_data = biz_turnover.clients_turnover_yearly_area_plot(year, data_type=2)
        else:
            img_data = biz_turnover.clients_turnover_yearly_area_plot(year)

        response = HttpResponse(img_data, content_type="image/png")
        return response


class ImageMemberStatusBar(BaseView):

    def get(self, request, *args, **kwargs):
        img_data = biz_plot.members_status_bar()
        response = HttpResponse(img_data, content_type="image/png")
        return response


class ImageBusinessTypeByYearView(BaseView):

    def get(self, request, *args, **kwargs):
        year = kwargs.get('year', 0)
        data_type = request.GET.get('data_type', "1")
        img_data = biz_plot.business_type_pie(year, data_type)
        response = HttpResponse(img_data, content_type="image/png")
        return response


class IssueListView(BaseTemplateView):
    template_name = 'default/issue_list.html'

    def get(self, request, *args, **kwargs):
        param_dict, params = common.get_request_params(request.GET)

        issue_list = models.Issue.objects.all()
        if param_dict:
            issue_list = issue_list.filter(**param_dict)

        context = self.get_context_data()
        context.update({
            'title': u'課題管理票一覧 | %s' % constants.NAME_SYSTEM,
            'issues': issue_list,
            'params': params,
        })
        return self.render_to_response(context)


class IssueDetailView(BaseTemplateView):
    template_name = 'default/issue.html'

    def get(self, request, *args, **kwargs):
        issue_id = kwargs.get('issue_id', 0)
        issue = get_object_or_404(models.Issue, pk=issue_id)
        log_entries = LogEntry.objects.filter(content_type_id=ContentType.objects.get_for_model(issue).pk,
                                              object_id=issue_id)

        context = self.get_context_data()
        context.update({
            'title': u'課題管理票 - %s | %s' % (issue.title, constants.NAME_SYSTEM),
            'issue': issue,
            'log_entries': log_entries,
        })
        return self.render_to_response(context)


class HistoryView(BaseTemplateView):
    template_name = 'default/history.html'

    def get(self, request, *args, **kwargs):
        histories = models.History.objects.all()
        total_hours = 0
        for h in histories:
            total_hours += h.get_hours()

        context = self.get_context_data()
        context.update({
            'title': u'更新履歴 | %s' % constants.NAME_SYSTEM,
            'histories': histories,
            'total_hours': total_hours,
        })
        return self.render_to_response(context)


@method_decorator(permission_required('eb.view_batch', raise_exception=True), name='get')
@method_decorator(permission_required('eb.execute_batch', raise_exception=True), name='post')
class BatchListView(BaseTemplateView):
    template_name = 'default/batch_list.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context.update({
            'title': u'バッチ一覧 | %s' % constants.NAME_SYSTEM,
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
        })
        context.update(csrf(request))
        batches = models.BatchManage.objects.public_all()
        context.update({
            'batches': batches,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        batch_name = request.POST.get('batch_name', None)
        options = {'username': request.user.username}
        call_command(batch_name, **options)
        return redirect(reverse("batch_log", args=(batch_name,)))


class BatchLogView(BaseView):

    def get(self, request, *args, **kwargs):
        name = kwargs.get('name', '')
        log_file = os.path.join(settings.BASE_DIR, 'log/batch', name + '.log')
        if os.path.exists(log_file):
            f = open(log_file, 'r')
            log = u"<pre>" + f.read().decode('utf-8') + u"</pre>"
            f.close()
        else:
            log = u"ログファイル「%s」が存在しません。" % (log_file,)
        return HttpResponse(log)


class AutoSendMailView(BaseTemplateView):
    template_name = 'default/auto_send_mail.html'

    def get_context_data(self, **kwargs):
        context = super(AutoSendMailView, self).get_context_data(**kwargs)
        # request = kwargs.get('request')
        groups = models.MailGroup.objects.public_all().annotate(member_count=Count('maillist'))
        context.update({
            'groups': groups,
        })

        return context


class AutoMailEditView(BaseTemplateView):
    template_name = 'default/auto_mail_edit.html'

    def get_context_data(self, **kwargs):
        context = super(AutoMailEditView, self).get_context_data(**kwargs)
        group_id = kwargs.get('group_id')
        group = get_object_or_404(models.MailGroup, pk=group_id)
        # request = kwargs.get('request')
        context.update({
            'group': group,
        })

        return context


class BusinessDaysView(BaseView):

    def post(self, request, *args, **kwargs):
        year = request.POST.get('year')
        month = request.POST.get('month')
        business_days = common.get_business_days(year, month)
        return JsonResponse({'business_days': business_days})


def login_user(request, qr=False):
    logout(request)
    img_base64 = None
    if qr:
        if request.POST:
            next_url = request.POST.get('next')
        else:
            next_url = request.GET.get('next')
            img_base64 = biz.gen_qr_code(request.META.get('wsgi.url_scheme'), request.META.get('HTTP_HOST'))
        user = None
    else:
        username = password = ''
        if request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            next_url = request.POST.get('next')
        else:
            next_url = request.GET.get('next')
        user = authenticate(username=username, password=password)

    if user is not None:
        if user.is_active:
            is_first_login = biz.is_first_login(user)
            login(request, user)
            if is_first_login:
                return redirect(reverse('password_change') + "?is_first_login=1")
            elif common.is_human_resources(user) and not request.user.is_superuser:
                return redirect(reverse('contract-index'))
            elif next_url:
                return redirect(next_url)
            else:
                return redirect('index')

    context = get_base_context()
    context.update({
        'next': next_url,
        'qr': qr,
        'img_base64': img_base64,
    })

    template = loader.get_template('default/login.html')
    return HttpResponse(template.render(context, request))


def logout_view(request):
    logout(request)
    return redirect('index')


@csrf_protect
@login_required(login_url=constants.LOGIN_IN_URL)
def password_change(request,
                    template_name='default/password_change_form.html',
                    post_change_redirect=None,
                    password_change_form=PasswordChangeForm,
                    extra_context=None):
    if post_change_redirect is None:
        post_change_redirect = reverse('home')
    else:
        post_change_redirect = resolve_url(post_change_redirect)
    if request.method == "POST":
        form = password_change_form(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Updating the password logs out all other sessions for the user
            # except the current one if
            # django.contrib.auth.middleware.SessionAuthenticationMiddleware
            # is enabled.
            update_session_auth_hash(request, form.user)
            return HttpResponseRedirect(post_change_redirect)
    else:
        form = password_change_form(user=request.user)

    is_first_login = request.GET.get('is_first_login', None)
    context = get_base_context()
    context.update({
        'form': form,
        'title': _('Password change'),
        'is_first_login': True if is_first_login == "1" else False,
    })
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)


def handler403(request):
    context = get_base_context()
    template = loader.get_template('default/403.html')
    response = HttpResponse(template.render(context, request))
    response.status_code = 403
    return response


def handler404(request):
    context = get_base_context()
    template = loader.get_template('default/404.html')
    response = HttpResponse(template.render(context, request))
    response.status_code = 404
    return response
