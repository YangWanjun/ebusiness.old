# coding: UTF-8
"""
Created on 2016/01/12

@author: Yang Wanjun
"""
import datetime
import uuid
import StringIO
import pandas as pd

from django.db import connection
from django.db.models import Q, Max, Min, Prefetch, Count, Case, When, IntegerField, Sum
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.contrib.humanize.templatetags import humanize
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType

from utils import common, errors, constants
from eb import models
from . import biz_config
from contract import models as contract_models


def get_batch_manage(name):
    """バッチ名によてバッチを取得する。

    :param name: バッチ名
    :return:
    """
    try:
        return models.BatchManage.objects.get(name=name)
    except ObjectDoesNotExist:
        return None


def is_salesperson_user(user):
    """該当するユーザーは営業員なのか

    :param user:
    :return:
    """
    if hasattr(user, 'salesperson'):
        return True
    else:
        return False


def get_bp_next_employee_id():
    """自動採番するため、次に使う番号を取得する。

    これは最終的に使う社員番号ではありません。
    実際の番号は追加後の主キーを使って、設定しなおしてから、もう一回保存する 。

    :return: string
    """
    max_id = models.Member.objects.all().aggregate(Max('id'))
    max_id = max_id.get('id__max', None)
    if max_id:
        return 'BP%05d' % (int(max_id) + 1,)
    else:
        return ''


def get_company():
    company_list = models.Company.objects.all()
    if company_list.count() == 0:
        return None
    else:
        return company_list[0]


def get_admin_user():
    try:
        return User.objects.get(username='admin')
    except ObjectDoesNotExist:
        return None


def get_year_list():
    start = biz_config.get_year_start()
    end = biz_config.get_year_end()
    return range(int(start), int(end))


def get_sales_members(year, month, param_dict=None, order_list=None):
    """作業メンバー一覧を取得する

    :param year:
    :param month:
    :return:
    """
    df = pd.read_sql("call sp_sales_member('%s%s')" % (year, month), connection)
    # 出向の契約を洗い出す
    loan_df = df[df.is_loan == 1]
    for index, row in loan_df.iterrows():
        related_row = df.loc[(df.member_id == row.member_id) & (df.is_loan == 0)]
        if related_row.empty:
            # 完全出向の場合は何もしない。
            continue
        # # ＥＢ契約の月給を再設定する。
        # df.set_value(index, 'salary', df.loc[index]['salary'] + related_row.iloc[0].salary)
        # ＢＰ契約に値を再設定する。
        df.set_value(related_row.index[0], 'is_loan', row.is_loan)
        # df.set_value(related_row.index[0], 'salary', df.loc[index]['salary'] + related_row.iloc[0].salary)
        # df.set_value(related_row.index[0], 'allowance', df.loc[index]['allowance'] + related_row.iloc[0].allowance)
        # df.set_value(related_row.index[0], 'night_allowance', df.loc[index]['night_allowance'] + related_row.iloc[0].night_allowance)
        # df.set_value(related_row.index[0], 'expenses', df.loc[index]['expenses'] + related_row.iloc[0].expenses)
        # df.set_value(related_row.index[0], 'employment_insurance', df.loc[index]['employment_insurance'] + related_row.iloc[0].employment_insurance)
        # df.set_value(related_row.index[0], 'health_insurance', df.loc[index]['health_insurance'] + related_row.iloc[0].health_insurance)
        # ＥＢの出向契約は非表示
        df = df.iloc[df.index != index]
    # 重複レコードを洗い出す。
    # 営業支援料金として一括に振り替えで、注文書作成する必要なので、ＢＰ契約を追加することになる。
    duplicated_df = df[df.member_id.duplicated(keep=False)]
    duplicated_index = duplicated_df.groupby('member_id').apply(lambda x: list(x.index))
    for m_id, rows in duplicated_index.iteritems():
        basic_row = df.loc[(df.member_id == m_id) & (df.member_type != 4)]
        row_count, col_count = basic_row.shape
        if row_count == 0:
            continue
        basic_index = basic_row.iloc[0].name
        for index in rows:
            if index == basic_index:
                continue
            # df.set_value([basic_index], 'expenses', df.loc[basic_index]['expenses'] + df.loc[index]['salary'])
            df = df.iloc[df.index != index]
    return common.data_frame_filter(df, param_dict, order_list)


def get_sales_on_members(year, month, param_dict=None, order_list=None):
    """指定年月の営業対象内社員を取得する。

    :param year:
    :param month:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = get_sales_members(year, month, param_dict, order_list)
    df = df.loc[(df.is_retired == 0) & (df.is_sales_off == 0)]
    return df


def get_sales_off_members(year, month, param_dict=None, order_list=None):
    """指定年月の営業対象外社員を取得する。

    :param year:
    :param month:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = get_sales_members(year, month, param_dict, order_list)
    df = df.loc[(df.is_retired == 0) & (df.status_month == '03')]
    return df


def get_working_members(year, month, param_dict=None, order_list=None):
    """指定年月の稼働社員を取得する。

    :param year:
    :param month:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = get_sales_members(year, month, param_dict, order_list)
    df = df.loc[(df.is_retired == 0) & (df.status_month == '01')]
    return df


def get_waiting_members(year, month, param_dict=None, order_list=None):
    """

    :param year:
    :param month:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = get_sales_members(year, month, param_dict, order_list)
    df = df.loc[(df.is_retired == 0) & (df.status_month == '02') & (df.is_sales_off == 0)]
    return df


def get_release_info():
    """リリース情報を取得する。

    :return:
    """
    query_set = models.ViewRelease.objects.all().values('release_ym').annotate(
        count=Count(1),
        bp_count=Count(Case(When(subcontractor_id__isnull=False, then=1), output_field=IntegerField)),
    ).order_by('release_ym')
    release_list = list(query_set)
    today = datetime.date.today()
    current_ym = today.strftime('%Y%m')
    next_ym = common.add_months(today, 1).strftime('%Y%m')
    next_2_ym = common.add_months(today, 2).strftime('%Y%m')
    for ym in [current_ym, next_ym, next_2_ym]:
        if ym not in [item.get('release_ym') for item in release_list]:
            release_list.append({'release_ym': ym, 'count': 0, 'bp_count': 0})
    return sorted(release_list, key=lambda x: x.get('release_ym'))


def get_members_by_section(all_members, section_id):
    if not section_id:
        return all_members
    today = datetime.date.today()
    return all_members.filter((Q(membersectionperiod__start_date__lte=today) &
                               Q(membersectionperiod__end_date__isnull=True)) |
                              (Q(membersectionperiod__start_date__lte=today) &
                               Q(membersectionperiod__end_date__gte=today)),
                              Q(membersectionperiod__division__pk=section_id) |
                              Q(membersectionperiod__section__pk=section_id) |
                              Q(membersectionperiod__subsection__pk=section_id),
                              membersectionperiod__is_deleted=False)


def get_project_members_by_section(project_members, section_id, date):
    return project_members.filter((Q(member__membersectionperiod__start_date__lte=date) &
                                   Q(member__membersectionperiod__end_date__isnull=date)) |
                                  (Q(member__membersectionperiod__start_date__lte=date) &
                                   Q(member__membersectionperiod__end_date__gte=date)),
                                  Q(member__membersectionperiod__division__pk=section_id) |
                                  Q(member__membersectionperiod__section__pk=section_id) |
                                  Q(member__membersectionperiod__subsection__pk=section_id),
                                  member__membersectionperiod__is_deleted=False).distinct()


def get_project_members_by_salesperson(project_members, salesperson_id, date):
    return project_members.filter((Q(member__membersalespersonperiod__start_date__lte=date) &
                                   Q(member__membersalespersonperiod__end_date__isnull=date)) |
                                  (Q(member__membersalespersonperiod__start_date__lte=date) &
                                   Q(member__membersalespersonperiod__end_date__gte=date)),
                                  member__membersalespersonperiod__salesperson__pk=salesperson_id,
                                  member__membersalespersonperiod__is_deleted=False).distinct()


def get_on_sales_top_org():
    """営業対象のトップレベルの部署を取得する

    :return:
    """
    return models.Section.objects.public_filter(is_on_sales=True, parent__isnull=True)


def get_on_sales_section():
    """営業対象の部署を取得する。

    :return:
    """
    return models.Section.objects.public_filter(is_on_sales=True)


def get_members_in_coming():
    """新規入場要員リストを取得する。

    :return:
    """
    today = datetime.date.today()
    return models.Member.objects.public_filter(join_date__gt=today)


def get_subcontractor_all_members():
    """すべての協力社員を取得する。

    :return:
    """
    return models.get_sales_members().filter(subcontractor__isnull=False)


def get_subcontractor_sales_members():
    """すべての協力社員を取得する。

    :return:
    """
    return get_subcontractor_all_members().filter(is_on_sales=True)


def get_subcontractor_working_members(date=None):
    """対象月の稼働中の協力社員を取得する。

    :param date: 対象年月
    :return:
    """
    if not date:
        first_day = last_day = datetime.date.today()
    else:
        first_day = common.get_first_day_by_month(date)
        last_day = common.get_last_day_by_month(date)

    return get_subcontractor_sales_members().filter(projectmember__start_date__lte=last_day,
                                                    projectmember__end_date__gte=first_day,
                                                    projectmember__is_deleted=False,
                                                    projectmember__status=2).distinct()


def get_subcontractor_waiting_members(date=None):
    """対象月の待機中の協力社員を取得する

    :param date: 対象年月
    :return:
    """
    working_members = get_subcontractor_working_members(date)
    return get_subcontractor_sales_members().exclude(pk__in=working_members)


def get_subcontractor_off_sales_members():
    """営業対象外の協力社員を取得する。

    :return:
    """
    return get_subcontractor_all_members().filter(is_on_sales=False)


def get_members_section(section):
    all_members = models.get_sales_members()
    return get_members_by_section(all_members, section.id)


def get_business_partner_members():
    """BPメンバーを取得する

    :return:
    """
    today = datetime.date.today()
    # 現在所属の営業員を取得
    sales_set = models.MemberSalespersonPeriod.objects.filter((Q(start_date__lte=today) & Q(end_date__isnull=True)) |
                                                              (Q(start_date__lte=today) & Q(end_date__gte=today)))
    # 現在の案件
    project_member_set = models.ProjectMember.objects.public_filter(
        start_date__lte=today,
        end_date__gte=today,
        status=2
    )

    queryset = models.Member.objects.filter(
        subcontractor__isnull=False
    ).select_related('subcontractor').order_by('subcontractor')
    return queryset.prefetch_related(
        Prefetch('membersalespersonperiod_set', queryset=sales_set, to_attr='current_salesperson_period'),
        Prefetch('projectmember_set', queryset=project_member_set, to_attr='current_project_member'),
    )


def get_bp_latest_contracts():
    """ＢＰの最新の契約一覧を取得する

    :return:
    """
    query_set = contract_models.ViewLatestBpContract.objects.all()
    return query_set


def get_bp_contract(member, year, month):
    """指定メンバーと指定年月でＢＰ契約を取得する。

    :param member:
    :param year:
    :param month:
    :return:
    """
    try:
        first_day = common.get_first_day_from_ym("%04d%02d" % (int(year), int(month)))
        last_day = common.get_last_day_by_month(first_day)
        bp_contract = contract_models.BpContract.objects.get(
            Q(end_date__gte=first_day) | Q(end_date__isnull=True),
            member=member,
            start_date__lte=last_day,
        )
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        bp_contract = None
    return bp_contract


def get_organization_turnover(year, month, section=None, param_dict=None, order_list=None):
    """指定年月の経営データを取得する。

    :param year:
    :param month:
    :param section:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = get_cost_by_month(year, month, param_dict, order_list)
    if section:
        all_children = section.get_children()
        org_pk_list = [org.pk for org in all_children]
        org_pk_list.append(section.pk)
        df = df[(df.division_id.isin(org_pk_list)) | (df.section_id.isin(org_pk_list)) | (df.subsection_id.isin(org_pk_list))]
    # 出向の契約を洗い出す
    loan_df = df[df.is_loan == 1]
    for index, row in loan_df.iterrows():
        related_row = df.loc[(df.projectmember_id == row.projectmember_id) & (df.is_loan == 0)]
        if related_row.empty:
            # 完全出向の場合は何もしない。
            continue
        # # ＥＢ契約の月給を再設定する。
        # df.set_value(index, 'salary', df.loc[index]['salary'] + related_row.iloc[0].salary)
        # ＢＰ契約に値を再設定する。
        df.set_value(related_row.index[0], 'is_loan', row.is_loan)
        df.set_value(related_row.index[0], 'salary', df.loc[index]['salary'] + related_row.iloc[0].salary)
        df.set_value(related_row.index[0], 'allowance', df.loc[index]['allowance'] + related_row.iloc[0].allowance)
        df.set_value(related_row.index[0], 'night_allowance', df.loc[index]['night_allowance'] + related_row.iloc[0].night_allowance)
        df.set_value(related_row.index[0], 'expenses', df.loc[index]['expenses'] + related_row.iloc[0].expenses)
        df.set_value(related_row.index[0], 'employment_insurance', df.loc[index]['employment_insurance'] + related_row.iloc[0].employment_insurance)
        df.set_value(related_row.index[0], 'health_insurance', df.loc[index]['health_insurance'] + related_row.iloc[0].health_insurance)
        # ＥＢの出向契約は非表示
        df = df.iloc[df.index!=index]
    # 重複レコードを洗い出す。
    # 営業支援料金として一括に振り替えで、注文書作成する必要なので、ＢＰ契約を追加することになる。
    duplicated_df = df[df.projectmember_id.duplicated(keep=False)]
    duplicated_index = duplicated_df.groupby('projectmember_id').apply(lambda x: list(x.index))
    for pm_id, rows in duplicated_index.iteritems():
        basic_row = df.loc[(df.projectmember_id == pm_id) & (df.member_type != 4)]
        if basic_row.empty:
            continue
        basic_index = basic_row.iloc[0].name
        for index in rows:
            if index == basic_index:
                continue
            df.set_value([basic_index], 'expenses', df.loc[basic_index]['expenses'] + df.loc[index]['salary'])
            df = df.iloc[df.index != index]

    return df


def get_dispatch_members(year, month):
    """指定年月の派遣社員一覧

    :param year:
    :param month:
    :return:
    """
    df = pd.read_sql("call sp_dispatch_members('%s%s')" % (year, month), connection)
    return df


def get_cost_by_month(year, month, param_dict=None, order_list=None):
    """指定年月の経営データを取得する。

    :param year:
    :param month:
    :param section:
    :param param_dict:
    :param order_list:
    :return:
    """
    df = pd.read_sql("call sp_organization_cost('%s%s')" % (year, month), connection)

    # 原価合計を計算する。
    df['total_cost'] = df['salary'] + df['allowance'] + df['night_allowance'] + df['overtime_cost'] + df[
        'traffic_cost'] + df['expenses'] + df['employment_insurance'] + df['health_insurance']
    # 粗利
    df['profit'] = df['total_price'] - df['total_cost']
    # 経費合計
    df['expenses_total'] = df['expenses_conference'] + df['expenses_entertainment'] + df['expenses_travel'] + df[
        'expenses_communication'] + df['expenses_tax_dues'] + df['expenses_expendables']
    # 営業利益
    df['income'] = df['total_price'] - df['total_cost'] - df['expenses_total']
    df.project_id = df.project_id.fillna(0).astype(int)
    return common.data_frame_filter(df, param_dict, order_list)


def get_project_members_month_section(section, date, user=None):
    """該当する日付に指定された部署に配属される案件メンバーを取得する。

    :param section: 部署
    :param date: 日付
    :param user:
    :return:
    """
    project_members = models.get_project_members_by_month(date)
    # 出勤情報を取得する
    current_attendance_set = models.MemberAttendance.objects.filter(year="%04d" % date.year,
                                                                    month="%02d" % date.month,
                                                                    is_deleted=False)
    prev_month = common.add_months(date, months=-1)
    prev_attendance_set = models.MemberAttendance.objects.filter(year="%04d" % prev_month.year,
                                                                 month="%02d" % prev_month.month,
                                                                 is_deleted=False)
    # 請求明細情報
    project_request_detail_set = models.ProjectRequestDetail.objects.filter(
        project_request__year="%04d" % date.year,
        project_request__month="%02d" % date.month
    )
    all_children = section.get_children()
    org_pk_list = [org.pk for org in all_children]
    org_pk_list.append(section.pk)

    queryset = project_members.filter((Q(member__membersectionperiod__start_date__lte=date) &
                                       Q(member__membersectionperiod__end_date__isnull=date)) |
                                      (Q(member__membersectionperiod__start_date__lte=date) &
                                       Q(member__membersectionperiod__end_date__gte=date)),
                                      Q(member__membersectionperiod__division__in=org_pk_list) |
                                      Q(member__membersectionperiod__section__in=org_pk_list) |
                                      Q(member__membersectionperiod__subsection__in=org_pk_list),
                                      member__membersectionperiod__is_deleted=False).distinct().prefetch_related(
        Prefetch('member'),
        Prefetch('project'),
        Prefetch('memberattendance_set', queryset=current_attendance_set, to_attr='current_attendance_set'),
        Prefetch('memberattendance_set', queryset=prev_attendance_set, to_attr='prev_attendance_set'),
        Prefetch('projectrequestdetail_set', queryset=project_request_detail_set, to_attr='project_request_detail_set'),
    )
    # 待機案件
    first_day = common.get_first_day_by_month(date)
    last_day = common.get_last_day_by_month(date)
    queryset2 = models.ProjectMember.objects.public_filter(end_date__gte=first_day,
                                                           start_date__lte=last_day,
                                                           project__status=4,
                                                           status=2,
                                                           project__is_reserve=True,
                                                           project__department__in=org_pk_list
                                                           ).distinct().prefetch_related(
        Prefetch('member'),
        Prefetch('project'),
    )

    return queryset | queryset2


def get_lump_projects_by_section(section, date):
    all_children = section.get_children()
    all_children = list(all_children)
    all_children.append(section)
    first_day = common.get_first_day_by_month(date)
    last_day = common.get_last_day_by_month(first_day)

    # 請求情報
    project_request_set = models.ProjectRequest.objects.filter(
        year="%04d" % date.year,
        month="%02d" % date.month
    )
    queryset = models.Project.objects.public_filter(
        is_lump=True,
        department__in=list(all_children),
        start_date__lte=last_day,
        end_date__gte=first_day
    ).distinct().prefetch_related(
        Prefetch('projectrequest_set', queryset=project_request_set, to_attr='project_request_set'),
    )
    return queryset


def get_subcontractor_project_members_month(date):
    """指定月の案件メンバー全部取得する。

    :param date 指定月
    :return
    """
    return models.get_project_members_by_month(date).filter(member__member_type=4)


def get_next_change_list():
    """入退場リスト

    :return:
    """
    first_day = common.get_first_day_current_month()
    last_day = common.get_last_day_by_month(first_day)
    next_first_day = common.get_first_day_by_month(common.add_months(first_day, 1))
    next_last_day = common.get_last_day_by_month(next_first_day)
    members = models.Member.objects.public_filter(Q(projectmember__end_date__gte=first_day,
                                                    projectmember__end_date__lte=last_day,
                                                    projectmember__is_deleted=False,
                                                    projectmember__status=2) |
                                                  Q(projectmember__start_date__gte=next_first_day,
                                                      projectmember__start_date__lte=next_last_day,
                                                      projectmember__is_deleted=False,
                                                      projectmember__status=2)).distinct()
    return members.filter(membersectionperiod__section__is_on_sales=True)


def get_subcontractor_release_members_by_month(date):
    """指定年月にリリースする協力社員を取得する。

    :param date 指定月
    """
    return models.get_release_members_by_month(date).filter(member__member_type=4)


def get_subcontractor_release_current_month():
    """今月にリリースする協力社員を取得する

    """
    return get_subcontractor_release_members_by_month(datetime.date.today())


def get_subcontractor_release_next_month():
    """来月にリリースする協力社員を取得する

    """
    next_month = common.add_months(datetime.date.today(), 1)
    return get_subcontractor_release_members_by_month(next_month)


def get_subcontractor_release_next_2_month():
    """再来月にリリースする協力社員を取得する

    """
    next_month = common.add_months(datetime.date.today(), 2)
    return get_subcontractor_release_members_by_month(next_month)


def get_projects(q=None, o=None):
    """案件を取得する。

    :param q:絞り込み条件
    :param o:並び順
    :return:
    """
    projects = models.Project.objects.public_all()
    today = datetime.date.today()
    working_members = models.ProjectMember.objects.public_filter(start_date__lte=today,
                                                                 end_date__gte=today)
    projects = projects.prefetch_related(
        'projectmember_set',
        Prefetch('projectmember_set', queryset=working_members, to_attr='working_project_members')
    )
    if q:
        projects = projects.filter(**q)
    if o:
        projects = projects.order_by(*o)
    return projects


def get_projects_orders(ym, q=None, o=None):
    """案件の注文情報を取得する。

    :param ym:対象年月
    :param q:絞り込み条件
    :param o:並び順
    :return:
    """
    first_day = common.get_first_day_from_ym(ym)
    last_day = common.get_last_day_by_month(first_day)

    project_orders = models.ClientOrder.projects.through.objects\
        .filter(Q(clientorder__isnull=True) | Q(clientorder__start_date__lte=last_day,
                                                clientorder__end_date__gte=first_day),
                project__start_date__lte=last_day,
                project__end_date__gte=first_day).distinct()

    if q:
        if 'project__projectrequest__request_no__contains' in q:
            q.update({'project__projectrequest__year': ym[:4],
                      'project__projectrequest__month': ym[4:]})
        project_orders = project_orders.filter(**q)

    order_by_request_no = None
    if o:
        if 'project__projectrequest__request_no' in o:
            order_by_request_no = 'ASC'
            o.remove('project__projectrequest__request_no')
        elif '-project__projectrequest__request_no' in o:
            order_by_request_no = 'DESC'
            o.remove('-project__projectrequest__request_no')
        project_orders = project_orders.order_by(*o)

    all_project_orders = []
    for project_order in project_orders:
        project_request = project_order.project.get_project_request(ym[:4], ym[4:], project_order.clientorder)
        all_project_orders.append((project_order.project, project_request, project_order.clientorder))
    if order_by_request_no == 'ASC':
        all_project_orders.sort(key=lambda d: d[1].request_no)
    elif order_by_request_no == 'DESC':
        all_project_orders.sort(key=lambda d: d[1].request_no, reverse=True)
    return all_project_orders


def get_activities_incoming():
    """これから実施する活動一覧

    :return:
    """
    now = timezone.now()
    activities = models.ProjectActivity.objects.public_filter(open_date__gte=now).order_by('open_date')
    return activities[:5]


def get_members_without_contract():
    """契約のないメンバーまたは契約期間が切れましたメンバーを洗い出す。

    :return:
    """
    return models.VMemberWithoutContract.objects.all()


def get_user_profile(user):
    """ログインしているユーザの詳細情報を取得する。

    :param user ログインしているユーザ
    """
    if hasattr(user, 'salesperson'):
        return user.salesperson
    return None


def generate_bp_lump_order_data(contract, bp_order, user, publish_date=None):
    """ＢＰ一括注文書を作成するためのデータを取得する。

    :param contract:
    :param bp_order:
    :param user:
    :param publish_date:
    :return:
    """
    if not contract:
        raise errors.CustomException(constants.ERROR_BP_NO_CONTRACT)
    company = get_company()
    data = {'DETAIL': {}}
    # 発行年月日
    publish_date = common.get_bp_order_publish_date(bp_order.year, bp_order.month, publish_date)
    data['DETAIL']['PUBLISH_DATE'] = common.to_wareki(publish_date)
    data['DETAIL']['YM'] = '%04d%02d' % (int(bp_order.year), int(bp_order.month))
    # 下請け会社名
    data['DETAIL']['SUBCONTRACTOR_NAME'] = contract.company.name
    # 下請け会社郵便番号
    if contract.company.post_code and len(contract.company.post_code) == 7:
        post_code = contract.company.post_code[:3] + '-' + \
                    contract.company.post_code[3:]
    else:
        post_code = ''
    data['DETAIL']['SUBCONTRACTOR_POST_CODE'] = post_code
    # 下請け会社住所
    data['DETAIL']['SUBCONTRACTOR_ADDRESS1'] = contract.company.address1
    data['DETAIL']['SUBCONTRACTOR_ADDRESS2'] = contract.company.address2 if contract.company.address2 else ''
    # 下請け会社電話番号
    data['DETAIL']['SUBCONTRACTOR_TEL'] = contract.company.tel
    # 下請け会社ファックス
    data['DETAIL']['SUBCONTRACTOR_FAX'] = contract.company.fax
    # 作成者
    create_user = get_user_profile(user)
    data['DETAIL']['AUTHOR_FIRST_NAME'] = create_user.first_name if create_user else ''
    # 会社名
    data['DETAIL']['COMPANY_NAME'] = company.name
    # 本社郵便番号
    data['DETAIL']['POST_CODE'] = common.get_full_postcode(company.post_code)
    # 本社電話番号
    data['DETAIL']['TEL'] = company.tel
    # 本社ファックス
    data['DETAIL']['FAX'] = company.fax
    # 代表取締役
    data['DETAIL']['MASTER'] = company.president if company.president else ""
    # 本社住所
    data['DETAIL']['ADDRESS1'] = company.address1
    data['DETAIL']['ADDRESS2'] = company.address2
    # 業務名称
    data['DETAIL']['PROJECT_NAME'] = unicode(contract.project) if contract.project else ''
    # 作業内容
    data['DETAIL']['PROJECT_CONTENT'] = contract.project_content
    # 作業量
    data['DETAIL']['WORKLOAD'] = contract.workload
    # 納入成果品
    data['DETAIL']['PROJECT_RESULT'] = contract.project_result
    # 作業期間
    data['DETAIL']['START_DATE'] = contract.start_date.strftime('%Y年%m月%d日').decode('utf8')
    data['DETAIL']['END_DATE'] = contract.end_date.strftime('%Y年%m月%d日').decode('utf8')
    data['DETAIL']['DELIVERY_DATE'] = contract.delivery_date.strftime('%Y年%m月%d日').decode('utf8')
    # 契約金額
    data['DETAIL']['ALLOWANCE_BASE'] = u'¥%s' % humanize.intcomma(contract.allowance_base)
    data['DETAIL']['ALLOWANCE_BASE_TAX'] = u'¥%s' % humanize.intcomma(contract.allowance_base_tax)
    data['DETAIL']['ALLOWANCE_BASE_TOTAL'] = u'¥%s' % humanize.intcomma(contract.allowance_base_total)
    # 備考
    data['DETAIL']['COMMENT'] = contract.comment
    # 注文番号
    data['DETAIL']['ORDER_NO'] = bp_order.order_no
    return data


def generate_bp_order_data(project_member, year, month, contract, user, bp_order,
                           publish_date=None, end_year=None, end_month=None):
    """ＢＰ注文書を作成するためのデータを取得する。

    :param project_member:
    :param year:
    :param month:
    :param contract:
    :param user:
    :param bp_order:
    :param publish_date:
    :param end_year:
    :param end_month:
    :return:
    """
    if not end_year or not end_month:
        end_year = year
        end_month = month
    elif '%04d%02d' % (int(year), int(month)) > '%04d%02d' % (int(end_year), int(end_month)):
        # 終了年月は開始年月の前の場合エラーとする。
        raise errors.CustomException(u"終了年月「%s年%s月」は不正です、開始年月以降に選択してください。" % (end_year, end_month))
    if not contract:
        raise errors.CustomException(constants.ERROR_BP_NO_CONTRACT)
    elif contract.end_date and contract.end_date.strftime('%Y%m') < common.get_last_day_by_month(
            datetime.date(int(end_year), int(end_month), 1)).strftime('%Y%m'):
        # 注文書の終了年月はＢＰ契約の終了日以降の場合、エラーとする
        raise errors.CustomException(u"契約は指定年月「%s年%s月」前にすでに終了しました。" % (end_year, end_month))
    company = get_company()
    data = {'DETAIL': {}}
    data['DETAIL']['YM'] = '%04d%02d' % (int(year), int(month))
    data['DETAIL']['END_YM'] = '%04d%02d' % (int(end_year), int(end_month))
    data['DETAIL']['INTERVAL'] = interval = (int(end_year) * 12 + int(end_month)) - (int(year) * 12 + int(month))
    first_day = datetime.date(int(year), int(month), 1)
    if project_member.start_date > first_day:
        first_day = project_member.start_date
    if interval > 0:
        last_day = common.get_last_day_by_month(datetime.date(int(end_year), int(end_month), 1))
    else:
        last_day = common.get_last_day_by_month(first_day)
        if contract.end_date and contract.end_date.strftime('%Y%m') == last_day.strftime('%Y%m'):
            last_day = contract.end_date
    # 発行年月日
    publish_date = common.get_bp_order_publish_date(year, month, publish_date)
    data['DETAIL']['PUBLISH_DATE'] = common.to_wareki(publish_date)
    # 下請け会社名
    data['DETAIL']['SUBCONTRACTOR_NAME'] = contract.company.name
    # 下請け会社郵便番号
    if contract.company.post_code and len(contract.company.post_code) == 7:
        post_code = contract.company.post_code[:3] + '-' + \
                    contract.company.post_code[3:]
    else:
        post_code = ''
    data['DETAIL']['SUBCONTRACTOR_POST_CODE'] = post_code
    # 下請け会社住所
    data['DETAIL']['SUBCONTRACTOR_ADDRESS1'] = contract.company.address1
    data['DETAIL']['SUBCONTRACTOR_ADDRESS2'] = contract.company.address2 or ''
    # 下請け会社電話番号
    data['DETAIL']['SUBCONTRACTOR_TEL'] = contract.company.tel or ''
    # 下請け会社ファックス
    data['DETAIL']['SUBCONTRACTOR_FAX'] = contract.company.fax or ''
    # 委託業務責任者（乙）
    data['DETAIL']['SUBCONTRACTOR_MASTER'] = contract.company.president
    # 連絡窓口担当者（甲）
    salesperson = project_member.member.get_salesperson(datetime.date(int(year), int(month), 20))
    data['DETAIL']['MIDDLEMAN'] = unicode(salesperson) if salesperson else ''
    # 連絡窓口担当者（乙）
    data['DETAIL']['SUBCONTRACTOR_MIDDLEMAN'] = contract.company.middleman or ''
    # 作成者
    data['DETAIL']['AUTHOR_FIRST_NAME'] = user.first_name if user else ''
    # 会社名
    data['DETAIL']['COMPANY_NAME'] = company.name
    # 本社郵便番号
    data['DETAIL']['POST_CODE'] = common.get_full_postcode(company.post_code)
    # 本社電話番号
    data['DETAIL']['TEL'] = company.tel or ''
    # 本社FAX番号
    data['DETAIL']['FAX'] = company.fax or ''
    # 代表取締役
    data['DETAIL']['MASTER'] = company.president if company.president else ""
    # 本社住所
    data['DETAIL']['ADDRESS1'] = company.address1 or ''
    data['DETAIL']['ADDRESS2'] = company.address2 or ''
    # 業務名称
    data['DETAIL']['PROJECT_NAME'] = project_member.project.name
    # 作業期間
    data['DETAIL']['START_DATE'] = common.to_wareki(first_day)
    data['DETAIL']['END_DATE'] = common.to_wareki(last_day)
    # 作業責任者
    data['DETAIL']['MEMBER_NAME'] = unicode(project_member.member)
    # 時給
    data['DETAIL']['IS_HOURLY_PAY'] = contract.is_hourly_pay
    # 基本給
    allowance_base = contract.get_cost()
    if contract.is_hourly_pay:
        allowance_base_memo = u"時間単価：¥%s/h  (消費税を含まない)" % humanize.intcomma(allowance_base)
    elif contract.is_fixed_cost:
        # 注文書は２か月以上の場合月額基本料金も２か月分以上
        if interval > 0:
            allowance_base *= (interval + 1)
            allowance_base_memo = u"基本料金：¥%s円  (固定、税金抜き)" % humanize.intcomma(allowance_base)
        else:
            allowance_base_memo = u"月額基本料金：¥%s円/月  (固定、税金抜き)" % humanize.intcomma(allowance_base)
    elif contract.allowance_base_memo and interval == 0:
        allowance_base_memo = contract.allowance_base_memo
    else:
        # 注文書は２か月以上の場合月額基本料金も２か月分以上
        if interval > 0:
            allowance_base *= (interval + 1)
            allowance_base_memo = u"基本料金：¥%s円  (税金抜き)" % humanize.intcomma(allowance_base)
        else:
            allowance_base_memo = u"月額基本料金：¥%s円/月  (税金抜き)" % humanize.intcomma(allowance_base)
    data['DETAIL']['ALLOWANCE_BASE'] = allowance_base
    data['DETAIL']['ALLOWANCE_BASE_MEMO'] = allowance_base_memo
    data['DETAIL']['ALLOWANCE_OTHER'] = contract.allowance_other
    data['DETAIL']['ALLOWANCE_OTHER_MEMO'] = u"%s：¥%s円" % (
        contract.allowance_other_memo, humanize.intcomma(contract.allowance_other)
    ) if contract.allowance_other else ""
    # 固定
    data['DETAIL']['IS_FIXED_COST'] = contract.is_fixed_cost
    # 計算式を表示するか
    data['DETAIL']['IS_SHOW_FORMULA'] = contract.is_show_formula
    # 変動基準時間方式の説明
    data['DETAIL']['CALCULATE_TYPE_COMMENT'] = contract.get_calculate_type_comment()
    if not contract.is_fixed_cost:
        # 超過単価
        allowance_overtime = humanize.intcomma(contract.allowance_overtime) if contract else ''
        if contract.allowance_overtime_memo:
            allowance_overtime_memo = contract.allowance_overtime_memo
        else:
            allowance_overtime_memo = u"超過単価：¥%s/%sh=¥%s/h" % (
                allowance_base, contract.allowance_time_max, allowance_overtime
            )
        data['DETAIL']['ALLOWANCE_OVERTIME'] = allowance_overtime
        data['DETAIL']['ALLOWANCE_OVERTIME_MEMO'] = allowance_overtime_memo
        # 不足単価
        # allowance_absenteeism = humanize.intcomma(contract.allowance_absenteeism) if contract else ''
        # if contract.allowance_absenteeism_memo:
        #     allowance_absenteeism_memo = contract.allowance_absenteeism_memo
        # else:
        #     allowance_absenteeism_memo = u"不足単価：¥%s/%sh=¥%s/h" % (
        #         allowance_base, contract.allowance_time_min, allowance_absenteeism
        #     )
        data['DETAIL']['ALLOWANCE_ABSENTEEISM'] = contract.get_allowance_absenteeism(year, month)
        data['DETAIL']['ALLOWANCE_ABSENTEEISM_MEMO'] = contract.get_allowance_absenteeism_memo(year, month)
        # 基準時間
        data['DETAIL']['ALLOWANCE_TIME_MIN'] = unicode(contract.get_allowance_time_min(year, month))
        data['DETAIL']['ALLOWANCE_TIME_MAX'] = unicode(contract.allowance_time_max)
        # if contract.allowance_time_memo:
        #     allowance_time_memo = contract.allowance_time_memo
        # else:
        #     allowance_time_memo = u"※基準時間：%s～%sh/月" % (contract.allowance_time_min, contract.allowance_time_max)
        data['DETAIL']['ALLOWANCE_TIME_MEMO'] = contract.get_allowance_time_memo(year, month)
    # 追記コメント
    data['DETAIL']['COMMENT'] = contract.comment
    # 作業場所
    data['DETAIL']['LOCATION'] = project_member.project.address if project_member.project.address else u"弊社指定場所"
    # 納入物件
    data['DETAIL']['DELIVERY_PROPERTIES'] = models.Config.get_bp_order_delivery_properties()
    # 支払条件
    data['DETAIL']['PAYMENT_CONDITION'] = models.Config.get_bp_order_payment_condition()
    # 支払日付
    data['DETAIL']['PAYMENT_DAY'] = contract.company.payment_day
    # 契約条項
    data['DETAIL']['CONTRACT_ITEMS'] = models.Config.get_bp_order_contract_items()

    data['DETAIL']['ORDER_NO'] = bp_order.order_no
    return data


def generate_order_data(company, subcontractor, user, ym):
    """註文書を生成するために使うデータを生成する。

    :param company 発注元会社
    :param subcontractor 発注先
    :param user ログインしているユーザ
    :param ym 対象年月
    :return エクセルのバイナリー
    """
    data = {'DETAIL': {}}
    # 発行年月日
    date = datetime.date.today()
    data['DETAIL']['PUBLISH_DATE'] = u"%s年%02d月%02d日" % (date.year, date.month, date.day)
    # 下請け会社名
    data['DETAIL']['SUBCONTRACTOR_NAME'] = subcontractor.name
    # 委託業務責任者（乙）
    data['DETAIL']['SUBCONTRACTOR_MASTER'] = subcontractor.president
    # 作成者
    salesperson = get_user_profile(user)
    data['DETAIL']['AUTHOR_FIRST_NAME'] = salesperson.first_name if salesperson else ''
    # 会社名
    data['DETAIL']['COMPANY_NAME'] = company.name
    # 本社郵便番号
    data['DETAIL']['POST_CODE'] = common.get_full_postcode(company.post_code)
    # 本社電話番号
    data['DETAIL']['TEL'] = company.tel
    # 代表取締役
    member = get_master()
    data['DETAIL']['MASTER'] = company.president
    # 本社住所
    data['DETAIL']['ADDRESS1'] = company.address1
    data['DETAIL']['ADDRESS2'] = company.address2
    # 作業期間
    if not ym:
        first_day = common.get_first_day_current_month()
    else:
        first_day = common.get_first_day_from_ym(ym)
    last_day = common.get_last_day_by_month(first_day)
    data['DETAIL']['START_DATE'] = u"%s年%02d月%02d日" % (first_day.year, first_day.month, first_day.day)
    data['DETAIL']['END_DATE'] = u"%s年%02d月%02d日" % (last_day.year, last_day.month, last_day.day)

    members = []
    # 全ての協力社員の注文情報を取得する。
    for member in subcontractor.get_members_by_month(first_day):
        bp_member_info = member.get_bp_member_info(first_day)
        members.append({'ITEM_NAME': member.__unicode__(),  # 協力社員名前
                        'ITEM_COST': humanize.intcomma(member.cost),  # 月額基本料金
                        'ITEM_MIN_HOUR': humanize.intcomma(bp_member_info.min_hours),  # 基準時間（最小値）
                        'ITEM_MAX_HOUR': humanize.intcomma(bp_member_info.max_hours),  # 基準時間（最大値）
                        'ITEM_PLUS_PER_HOUR': humanize.intcomma(bp_member_info.plus_per_hour),  # 超過単価
                        'ITEM_MINUS_PER_HOUR': humanize.intcomma(bp_member_info.minus_per_hour),  # 不足単価
                        })
    data['MEMBERS'] = members

    return data


def get_request_members_in_project(project, client_order, ym):
    """指定案件の指定注文書の中に、対象のメンバーを取得する。

    :param project: 指定案件
    :param client_order: 指定注文書
    :param ym: 対象年月
    :return: メンバーのリスト
    """
    first_day = common.get_first_day_from_ym(ym)
    last_day = common.get_last_day_by_month(first_day)
    if client_order.projects.public_filter(is_deleted=False).count() > 1:
        # 一つの注文書に複数の案件がある場合
        projects = client_order.projects.public_filter(is_deleted=False)
        project_members = models.ProjectMember.objects.public_filter(
            project__in=projects, start_date__lte=last_day, end_date__gte=first_day
        )
    elif project.get_order_by_month(ym[:4], ym[4:]).count() > 1:
        # １つの案件に複数の注文書ある場合
        project_members = []
        if client_order.member_comma_list:
            # 重複したメンバーを外す。
            member_id_list = sorted(set(client_order.member_comma_list.split(",")))
            for pm_id in member_id_list:
                try:
                    project_members.append(
                        models.ProjectMember.objects.get(pk=int(pm_id), is_deleted=False, status=2,
                                                         start_date__lte=last_day,
                                                         end_date__gte=first_day))
                except ObjectDoesNotExist:
                    pass
    else:
        project_members = project.get_project_members_by_month(ym=ym)
    return project_members


def generate_request_data(company, project, client_order, bank_info, ym, project_request):
    first_day = common.get_first_day_from_ym(ym)
    last_day = common.get_last_day_by_month(first_day)
    data = {'DETAIL': {}, 'EXTRA': {}}
    data['EXTRA']['YM'] = ym
    # お客様郵便番号
    data['DETAIL']['CLIENT_POST_CODE'] = common.get_full_postcode(project.client.post_code)
    # お客様住所
    data['DETAIL']['CLIENT_ADDRESS'] = (project.client.address1 or '') + (project.client.address2 or '')
    # お客様電話番号
    data['DETAIL']['CLIENT_TEL'] = project.client.tel or ''
    # お客様名称
    data['DETAIL']['CLIENT_COMPANY_NAME'] = project.client.name
    # 作業期間
    f = u'%Y年%m月%d日'
    period_start = first_day.strftime(f.encode('utf-8')).decode('utf-8')
    period_end = last_day.strftime(f.encode('utf-8')).decode('utf-8')
    data['DETAIL']['WORK_PERIOD'] = period_start + u" ～ " + period_end
    data['EXTRA']['WORK_PERIOD_START'] = first_day
    data['EXTRA']['WORK_PERIOD_END'] = last_day
    # 注文番号
    data['DETAIL']['ORDER_NO'] = client_order.order_no if client_order.order_no else u""
    # 注文日
    data['DETAIL']['REQUEST_DATE'] = client_order.order_date.strftime('%Y/%m/%d') if client_order.order_date else ""
    # 契約件名
    data['DETAIL']['CONTRACT_NAME'] = project_request.request_name
    # お支払い期限
    data['DETAIL']['REMIT_DATE'] = project.client.get_pay_date(date=first_day).strftime('%Y/%m/%d')
    data['EXTRA']['REMIT_DATE'] = project.client.get_pay_date(date=first_day)
    # 請求番号
    data['DETAIL']['REQUEST_NO'] = project_request.request_no
    # 発行日（対象月の最終日）
    data['DETAIL']['PUBLISH_DATE'] = last_day.strftime(u"%Y年%m月%d日".encode('utf-8')).decode('utf-8')
    data['EXTRA']['PUBLISH_DATE'] = last_day
    # 本社郵便番号
    data['DETAIL']['POST_CODE'] = common.get_full_postcode(company.post_code)
    # 本社住所
    data['DETAIL']['ADDRESS'] = (company.address1 or '') + (company.address2 or '')
    # 会社名
    data['DETAIL']['COMPANY_NAME'] = company.name
    # 代表取締役
    member = get_master()
    data['DETAIL']['MASTER'] = company.president
    # 本社電話番号
    data['DETAIL']['TEL'] = company.tel
    # 振込先銀行名称
    data['EXTRA']['BANK'] = bank_info
    data['DETAIL']['BANK_NAME'] = bank_info.bank_name if bank_info else u""
    # 支店番号
    data['DETAIL']['BRANCH_NO'] = bank_info.branch_no if bank_info else u""
    # 支店名称
    data['DETAIL']['BRANCH_NAME'] = bank_info.branch_name if bank_info else u""
    # 預金種類
    data['DETAIL']['ACCOUNT_TYPE'] = bank_info.get_account_type_display() if bank_info else u""
    # 口座番号
    data['DETAIL']['ACCOUNT_NUMBER'] = bank_info.account_number if bank_info else u""
    # 口座名義人
    data['DETAIL']['BANK_ACCOUNT_HOLDER'] = bank_info.account_holder if bank_info else u""

    # 全員の合計明細
    detail_all = dict()
    # メンバー毎の明細
    detail_members = []

    project_members = get_request_members_in_project(project, client_order, ym)
    members_amount = 0
    if project.is_lump:
        members_amount = project.lump_amount
        # 番号
        detail_all['NO'] = u"1"
        # 項目：契約件名に設定
        detail_all['ITEM_NAME_ATTENDANCE_TOTAL'] = data['DETAIL']['CONTRACT_NAME']
        # 数量
        detail_all['ITEM_COUNT'] = u"1"
        # 単位
        detail_all['ITEM_UNIT'] = u"一式"
        # 金額
        detail_all['ITEM_AMOUNT_ATTENDANCE_ALL'] = members_amount
        # 備考
        detail_all['ITEM_COMMENT'] = project.lump_comment if project.is_lump and project.lump_comment else u""
    else:
        for i, project_member in enumerate(project_members):
            dict_expenses = dict()
            # この項目は請求書の出力ではなく、履歴データをProjectRequestDetailに保存するために使う。
            dict_expenses["EXTRA_PROJECT_MEMBER"] = project_member
            # 番号
            dict_expenses['NO'] = str(i + 1)
            # 項目
            dict_expenses['ITEM_NAME'] = project_member.member.__unicode__()
            # 時給の場合
            if project.is_hourly_pay:
                # 単価（円）
                dict_expenses['ITEM_PRICE'] = project_member.hourly_pay or 0
                # Min/Max（H）
                dict_expenses['ITEM_MIN_MAX'] = u""
            else:
                # 単価（円）
                dict_expenses['ITEM_PRICE'] = project_member.price or 0
                # Min/Max（H）
                dict_expenses['ITEM_MIN_MAX'] = "%s/%s" % (int(project_member.min_hours), int(project_member.max_hours))
            dict_expenses.update(project_member.get_attendance_dict(first_day.year, first_day.month))
            # 金額合計
            members_amount += dict_expenses['ITEM_AMOUNT_TOTAL']
            detail_members.append(dict_expenses)

    detail_expenses, expenses_amount = get_request_expenses_list(project,
                                                                 first_day.year,
                                                                 '%02d' % (first_day.month,),
                                                                 project_members)

    data['detail_all'] = detail_all
    data['MEMBERS'] = detail_members
    data['EXPENSES'] = detail_expenses  # 清算リスト
    data['DETAIL']['ITEM_AMOUNT_ATTENDANCE'] = members_amount
    if project.client.decimal_type == '0':
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = int(round(members_amount * project.client.tax_rate))
    else:
        # 出勤のトータル金額の税金
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = int(members_amount * project.client.tax_rate)
    data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_ALL'] = members_amount + int(data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'])
    data['DETAIL']['ITEM_AMOUNT_ALL'] = int(data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_ALL']) + expenses_amount
    data['DETAIL']['ITEM_AMOUNT_ALL_COMMA'] = humanize.intcomma(data['DETAIL']['ITEM_AMOUNT_ALL'])

    project_request.amount = data['DETAIL']['ITEM_AMOUNT_ALL']
    project_request.turnover_amount = members_amount
    project_request.tax_amount = data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX']
    project_request.expenses_amount = expenses_amount

    return data


def generate_subcontractor_request_data(subcontractor, year, month, subcontractor_request):
    company = get_company()
    first_day = common.get_first_day_by_month(datetime.date(int(year), int(month), 1))
    last_day = common.get_last_day_by_month(first_day)
    today = datetime.date.today()
    data = {'DETAIL': {}, 'EXTRA': {}}
    data['EXTRA']['YM'] = first_day.strftime('%Y%m')
    data['EXTRA']['COMPANY'] = company
    # お客様郵便番号
    data['DETAIL']['CLIENT_POST_CODE'] = common.get_full_postcode(company.post_code)
    # お客様住所
    data['DETAIL']['CLIENT_ADDRESS'] = (company.address1 or '') + (company.address2 or '')
    # お客様電話番号
    data['DETAIL']['CLIENT_TEL'] = company.tel or ''
    # お客様ファックス
    data['DETAIL']['CLIENT_FAX'] = company.fax or ''
    # お客様名称
    data['DETAIL']['CLIENT_COMPANY_NAME'] = company.name
    # 作業期間
    f = u'%Y年%m月%d日'
    period_start = first_day.strftime(f.encode('utf-8')).decode('utf-8')
    period_end = last_day.strftime(f.encode('utf-8')).decode('utf-8')
    data['DETAIL']['WORK_PERIOD'] = period_start + u" ～ " + period_end
    data['EXTRA']['WORK_PERIOD_START'] = first_day
    data['EXTRA']['WORK_PERIOD_END'] = last_day
    # 注文番号
    data['DETAIL']['ORDER_NO'] = u""
    # 注文日
    data['DETAIL']['REQUEST_DATE'] = u""
    # 契約件名
    data['DETAIL']['CONTRACT_NAME'] = u""
    # 部署名称
    data['DETAIL']['ORG_NAME'] = unicode(subcontractor_request.section)
    # お支払い期限
    # data['DETAIL']['REMIT_DATE'] = company.get_pay_date(date=first_day).strftime('%Y/%m/%d')
    # data['EXTRA']['REMIT_DATE'] = company.get_pay_date(date=first_day)
    data['DETAIL']['REMIT_DATE'] = subcontractor.get_pay_date(date=first_day).strftime('%Y/%m/%d')
    data['EXTRA']['REMIT_DATE'] = subcontractor.get_pay_date(date=first_day)
    # 請求番号
    data['DETAIL']['REQUEST_NO'] = subcontractor_request.request_no
    # お支払通知書番号
    data['DETAIL']['PAY_NOTIFY_NO'] = subcontractor_request.pay_notify_no
    # 発行日（対象月の最終日）
    data['DETAIL']['PUBLISH_DATE'] = last_day.strftime(u"%Y年%m月%d日".encode('utf-8')).decode('utf-8')
    data['EXTRA']['PUBLISH_DATE'] = last_day
    # 作成日
    data['DETAIL']['CREATE_DATE'] = today
    # 本社郵便番号
    data['DETAIL']['POST_CODE'] = common.get_full_postcode(subcontractor.post_code)
    # 本社住所
    data['DETAIL']['ADDRESS'] = (subcontractor.address1 or '') + (subcontractor.address2 or '')
    # 会社名
    data['DETAIL']['COMPANY_NAME'] = subcontractor.name
    # 代表取締役
    data['DETAIL']['MASTER'] = subcontractor.president
    # 本社電話番号
    data['DETAIL']['TEL'] = subcontractor.tel
    # 振込先銀行名称
    if subcontractor.subcontractorbankinfo_set.all().count() == 0:
        bank_info = None
    else:
        bank_info = subcontractor.subcontractorbankinfo_set.all()[0]
    data['EXTRA']['BANK'] = bank_info
    data['DETAIL']['BANK_NAME'] = bank_info.bank_name if bank_info else u""
    # 支店番号
    data['DETAIL']['BRANCH_NO'] = bank_info.branch_no if bank_info else u""
    # 支店名称
    data['DETAIL']['BRANCH_NAME'] = bank_info.branch_name if bank_info else u""
    # 預金種類
    data['DETAIL']['ACCOUNT_TYPE'] = bank_info.get_account_type_display() if bank_info else u""
    # 口座番号
    data['DETAIL']['ACCOUNT_NUMBER'] = bank_info.account_number if bank_info else u""
    # 口座名義人
    data['DETAIL']['BANK_ACCOUNT_HOLDER'] = bank_info.account_holder if bank_info else u""

    # 全員の合計明細
    detail_all = dict()
    # メンバー毎の明細
    detail_members = []

    sub_sections = subcontractor_request.section.get_children()
    sub_sections.append(subcontractor_request.section)
    section_members = subcontractor.get_members_by_month_and_section(year, month, subcontractor_request.section)
    lump_contracts = subcontractor.get_lump_contracts(year, month).filter(
        project__department__in=sub_sections
    )
    members_amount = 0
    project_members = []
    lump_tax = None
    if False:
        members_amount = 0
        # 番号
        detail_all['NO'] = u"1"
        # 項目：契約件名に設定
        detail_all['ITEM_NAME_ATTENDANCE_TOTAL'] = data['DETAIL']['CONTRACT_NAME']
        # 数量
        detail_all['ITEM_COUNT'] = u"1"
        # 単位
        detail_all['ITEM_UNIT'] = u"一式"
        # 金額
        detail_all['ITEM_AMOUNT_ATTENDANCE_ALL'] = members_amount
        # 備考
        detail_all['ITEM_COMMENT'] = u""
    else:
        for i, member in enumerate(section_members):
            member_attendance_set = models.MemberAttendance.objects.public_filter(
                project_member__member=member,
                year=year,
                month=month,
            )
            if member_attendance_set.count() > 0:
                member_attendance = member_attendance_set[0]
                project_members.append(member_attendance.project_member)
                contract_list = member.bpcontract_set.filter(
                    start_date__lte=last_day,
                    is_deleted=False,
                ).order_by('-start_date')
                try:
                    bp_member_order = models.BpMemberOrder.objects.get(
                        project_member=member_attendance.project_member,
                        year=member_attendance.year,
                        month=member_attendance.month
                    )
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    bp_member_order = None
                if contract_list.count() > 0:
                    contract = contract_list[0]
                    allowance_time_min = contract.allowance_time_min
                    if bp_member_order and hasattr(bp_member_order, 'bpmemberorderheading'):
                        if bp_member_order.bpmemberorderheading.allowance_time_min:
                            allowance_time_min = float(bp_member_order.bpmemberorderheading.allowance_time_min)
                        allowance_absenteeism = int(bp_member_order.bpmemberorderheading.allowance_absenteeism or 0)
                        allowance_overtime = int(str(bp_member_order.bpmemberorderheading.allowance_overtime or 0).replace(',', ''))
                    else:
                        allowance_absenteeism = contract.allowance_absenteeism
                        allowance_overtime = contract.allowance_overtime
                    dict_expenses = dict()
                    # この項目は請求書の出力ではなく、履歴データをProjectRequestDetailに保存するために使う。
                    dict_expenses["EXTRA_PROJECT_MEMBER"] = member_attendance.project_member
                    # BP注文書
                    dict_expenses['BP_MEMBER_ORDER'] = bp_member_order
                    # 番号
                    dict_expenses['NO'] = str(i + 1)
                    # 項目
                    dict_expenses['ITEM_NAME'] = unicode(member)
                    # 時間下限
                    dict_expenses['ITEM_MIN_HOURS'] = allowance_time_min
                    # 時間上限
                    dict_expenses['ITEM_MAX_HOURS'] = contract.allowance_time_max
                    # 勤務時間
                    dict_expenses['ITEM_WORK_HOURS'] = member_attendance.total_hours_bp \
                        if member_attendance.total_hours_bp else member_attendance.total_hours
                    # 超過金額と控除金額
                    extra_amount = member_attendance.get_overtime_cost(allowance_time_min=allowance_time_min)
                    # 諸経費
                    dict_expenses['ITEM_EXPENSES_TOTAL'] = member_attendance.get_bp_expenses_amount()
                    if extra_amount > 0:
                        dict_expenses['ITEM_PLUS_AMOUNT'] = extra_amount
                        dict_expenses['ITEM_MINUS_AMOUNT'] = 0
                    else:
                        dict_expenses['ITEM_PLUS_AMOUNT'] = 0
                        dict_expenses['ITEM_MINUS_AMOUNT'] = extra_amount
                    # 基本金額
                    dict_expenses['ITEM_AMOUNT_BASIC'] = contract.get_cost()
                    # 時給の場合
                    if contract.is_hourly_pay or contract.is_fixed_cost:
                        # 単価（円）
                        dict_expenses['ITEM_PRICE'] = contract.allowance_base or 0
                        # Min/Max（H）
                        dict_expenses['ITEM_MIN_MAX'] = u""
                        # 残業時間
                        dict_expenses['ITEM_EXTRA_HOURS'] = 0
                        # 率
                        dict_expenses['ITEM_RATE'] = 1
                        # 減（円）
                        dict_expenses['ITEM_MINUS_PER_HOUR'] = 0
                        # 増（円）
                        dict_expenses['ITEM_PLUS_PER_HOUR'] = 0
                        # 基本金額＋残業金額
                        dict_expenses['ITEM_AMOUNT_TOTAL'] = member_attendance.get_cost()
                    else:
                        # 単価（円）
                        dict_expenses['ITEM_PRICE'] = contract.get_cost() or 0
                        # Min/Max（H）
                        dict_expenses['ITEM_MIN_MAX'] = "%.1f/%s" % (
                            allowance_time_min, int(contract.allowance_time_max)
                        )
                        # 残業時間
                        extra_hours = member_attendance.get_overtime(contract)
                        dict_expenses['ITEM_EXTRA_HOURS'] = extra_hours
                        # 率
                        dict_expenses['ITEM_RATE'] = 1
                        # 減（円）
                        dict_expenses['ITEM_MINUS_PER_HOUR'] = allowance_absenteeism
                        # 増（円）
                        dict_expenses['ITEM_PLUS_PER_HOUR'] = allowance_overtime

                        if extra_hours > 0:
                            dict_expenses['ITEM_AMOUNT_EXTRA'] = extra_hours * dict_expenses['ITEM_PLUS_PER_HOUR']
                            dict_expenses['ITEM_PLUS_PER_HOUR2'] = dict_expenses['ITEM_PLUS_PER_HOUR']
                            dict_expenses['ITEM_MINUS_PER_HOUR2'] = u""
                        elif extra_hours < 0:
                            dict_expenses['ITEM_AMOUNT_EXTRA'] = extra_hours * dict_expenses['ITEM_MINUS_PER_HOUR']
                            dict_expenses['ITEM_PLUS_PER_HOUR2'] = u""
                            dict_expenses['ITEM_MINUS_PER_HOUR2'] = dict_expenses['ITEM_MINUS_PER_HOUR']
                        else:
                            dict_expenses['ITEM_AMOUNT_EXTRA'] = 0
                            dict_expenses['ITEM_PLUS_PER_HOUR2'] = u""
                            dict_expenses['ITEM_MINUS_PER_HOUR2'] = u""
                        # 基本金額＋残業金額
                        dict_expenses['ITEM_AMOUNT_TOTAL'] = member_attendance.get_cost() + member_attendance.get_overtime_cost(allowance_time_min=allowance_time_min)
                    # 備考
                    dict_expenses['ITEM_COMMENT'] = member_attendance.comment \
                        if member_attendance and member_attendance.comment else u""
                    dict_expenses['ITEM_OTHER'] = u""
                    # 金額合計
                    members_amount += dict_expenses['ITEM_AMOUNT_TOTAL']
                    detail_members.append(dict_expenses)
        for i, lump_contract in enumerate(lump_contracts):
            dict_expenses = dict()
            # この項目は請求書の出力ではなく、履歴データをProjectRequestDetailに保存するために使う。
            dict_expenses["EXTRA_PROJECT_MEMBER"] = None
            dict_expenses['EXTRA_LUMP_CONTRACT'] = lump_contract
            # BP注文書
            dict_expenses['BP_MEMBER_ORDER'] = lump_contract.bplumporder if hasattr(lump_contract, 'lump_contract') else None
            # 番号
            dict_expenses['NO'] = str(i + 1)
            # 項目
            dict_expenses['ITEM_NAME'] = u"一括"
            # 時間下限
            dict_expenses['ITEM_MIN_HOURS'] = 0
            # 時間上限
            dict_expenses['ITEM_MAX_HOURS'] = 0
            # 勤務時間
            dict_expenses['ITEM_WORK_HOURS'] = 0
            # 諸経費
            dict_expenses['ITEM_EXPENSES_TOTAL'] = 0
            # 超過金額と控除金額
            dict_expenses['ITEM_PLUS_AMOUNT'] = 0
            dict_expenses['ITEM_MINUS_AMOUNT'] = 0
            # 基本金額
            dict_expenses['ITEM_AMOUNT_BASIC'] = lump_contract.get_cost()
            # 単価（円）
            dict_expenses['ITEM_PRICE'] = lump_contract.get_cost()
            # Min/Max（H）
            dict_expenses['ITEM_MIN_MAX'] = u""
            # 残業時間
            dict_expenses['ITEM_EXTRA_HOURS'] = 0
            # 率
            dict_expenses['ITEM_RATE'] = 1
            # 減（円）
            dict_expenses['ITEM_MINUS_PER_HOUR'] = 0
            # 増（円）
            dict_expenses['ITEM_PLUS_PER_HOUR'] = 0
            # 基本金額＋残業金額
            dict_expenses['ITEM_AMOUNT_TOTAL'] = lump_contract.get_cost()
            # 備考
            dict_expenses['ITEM_COMMENT'] = lump_contract.comment if lump_contract.comment else u""
            dict_expenses['ITEM_OTHER'] = u""
            # 金額合計
            members_amount += dict_expenses['ITEM_AMOUNT_TOTAL']
            # 税金
            if lump_tax is None:
                lump_tax = lump_contract.allowance_base_tax or 0
            else:
                lump_tax += (lump_contract.allowance_base_tax or 0)
            # 一括時の契約
            detail_members.append(dict_expenses)

    detail_expenses, expenses_amount = get_subcontractor_request_expenses_list(
        first_day.year,
        '%02d' % (first_day.month,),
        project_members
    )

    data['detail_all'] = detail_all
    data['MEMBERS'] = detail_members
    data['EXPENSES'] = detail_expenses  # 清算リスト
    data['DETAIL']['ITEM_AMOUNT_ATTENDANCE'] = members_amount
    if subcontractor.pk == 154:
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = 0
    elif lump_tax is not None:
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = lump_tax
    elif company.decimal_type == '0':
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = int(round(members_amount * company.tax_rate))
    else:
        # 出勤のトータル金額の税金
        data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'] = int(members_amount * company.tax_rate)
    data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_ALL'] = members_amount + int(data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX'])
    data['DETAIL']['ITEM_AMOUNT_ALL'] = int(data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_ALL']) + expenses_amount
    data['DETAIL']['ITEM_AMOUNT_ALL_COMMA'] = humanize.intcomma(data['DETAIL']['ITEM_AMOUNT_ALL'])

    subcontractor_request.amount = data['DETAIL']['ITEM_AMOUNT_ALL']
    subcontractor_request.turnover_amount = members_amount
    subcontractor_request.tax_amount = data['DETAIL']['ITEM_AMOUNT_ATTENDANCE_TAX']
    subcontractor_request.expenses_amount = expenses_amount

    return data


def get_subcontractor_request_expenses_list(year, month, project_members):
    # 精算リスト
    dict_expenses = {}
    expenses_list = models.SubcontractorMemberExpenses.objects.public_filter(
        year=year, month=month,
        project_member__in=project_members
    )
    for expenses in expenses_list:
        if expenses.category.name not in dict_expenses:
            dict_expenses[expenses.category.name] = [expenses]
        else:
            dict_expenses[expenses.category.name].append(expenses)
    detail_expenses = []
    expenses_amount = 0
    for key, value in dict_expenses.iteritems():
        d = dict()
        member_list = []
        amount = 0
        for expenses in value:
            member_list.append(expenses.project_member.member.first_name +
                               expenses.project_member.member.last_name +
                               u"¥%s" % (expenses.price,))
            amount += expenses.price
            expenses_amount += expenses.price
        d['ITEM_EXPENSES_CATEGORY_SUMMARY'] = u"%s(%s)" % (key, u"、".join(member_list))
        d['ITEM_EXPENSES_CATEGORY_AMOUNT'] = amount
        detail_expenses.append(d)
    return detail_expenses, expenses_amount


def get_request_expenses_list(project, year, month, project_members):
    # 精算リスト
    dict_expenses = {}
    for expenses in project.get_expenses(year, month, project_members):
        if expenses.category.name not in dict_expenses:
            dict_expenses[expenses.category.name] = [expenses]
        else:
            dict_expenses[expenses.category.name].append(expenses)
    detail_expenses = []
    expenses_amount = 0
    for key, value in dict_expenses.iteritems():
        d = dict()
        member_list = []
        amount = 0
        for expenses in value:
            member_list.append(expenses.project_member.member.first_name +
                               expenses.project_member.member.last_name +
                               u"¥%s" % (expenses.price,))
            amount += expenses.price
            expenses_amount += expenses.price
        d['ITEM_EXPENSES_CATEGORY_SUMMARY'] = u"%s(%s)" % (key, u"、".join(member_list))
        d['ITEM_EXPENSES_CATEGORY_AMOUNT'] = amount
        detail_expenses.append(d)
    return detail_expenses, expenses_amount


def get_attendance_time_from_eboa(project_member, year, month):
    """EBOAから出勤時間を取得する。

    :param project_member:
    :param year:
    :param month:
    :return:
    """
    if not project_member.member.eboa_user_id:
        return 0

    # period = '%04d/%02d' % (int(year), int(month))
    # eboa_attendances = eboa_models.EbAttendance.objects.filter(applicant__userid=project_member.member.eboa_user_id,
    #                                                            period=period)
    # if eboa_attendances.count() > 0:
    #     return float(eboa_attendances[0].totaltime)
    # else:
    #     return 0
    return 0


def get_master():
    # 代表取締役を取得する。
    members = models.Salesperson.objects.public_filter(member_type=7)
    if members.count() == 1:
        return members[0]
    else:
        return None


def is_first_login(user):
    """初めてのログインなのかどうか

    :param user:
    :return:
    """
    try:
        User.objects.get(username=user.username, last_login__isnull=True)
        return True
    except ObjectDoesNotExist:
        return False
    except MultipleObjectsReturned:
        return False


def gen_qr_code(url_schema, domain):
    import qrcode
    uid = uuid.uuid4()
    # url = domain + reverse('login_qr') + "?uid=" + str(uid)
    url = "%s://%s%s?uid=%s" % (url_schema, domain, reverse('login_qr'), str(uid))
    img = qrcode.make(url)
    output = StringIO.StringIO()
    img.save(output, "PNG")
    contents = output.getvalue().encode("base64")
    output.close()
    return contents


def member_retired(member, user):
    """退職フラグが変更時、契約も自動的に更新する。

    このメソッドを呼び出す前に、Formで退職フラグが変わったかどうかの判断が必要です。

    :param member: 退職する社員
    :return:
    """
    v_contract_set = contract_models.ViewContract.objects.filter(
        member=member, is_old=False, is_deleted=False
    ).exclude(status='04')
    if member.is_retired and member.retired_date:
        # 退職した場合
        query_set = v_contract_set.filter(
            Q(end_date__gte=member.retired_date) | Q(end_date__isnull=True),
            start_date__lte=member.retired_date
        )
        if query_set.count() > 0:
            for v_contract in query_set:
                if v_contract.member_type == 4:
                    # ＢＰ社員の場合
                    bp_contract = contract_models.BpContract.objects.get(pk=v_contract.id)
                    bp_contract.end_date = member.retired_date
                    bp_contract.save(update_fields=['end_date'])
                    change_message = u"契約終了日（%s）は退職で自動変更しました。" % member.retired_date
                    LogEntry.objects.log_action(user.id,
                                                ContentType.objects.get_for_model(bp_contract).pk,
                                                bp_contract.pk,
                                                unicode(bp_contract),
                                                CHANGE,
                                                change_message=change_message)
                else:
                    # ＥＢ社員の場合
                    contract = contract_models.Contract.objects.get(pk=v_contract.id)
                    contract.end_date2 = member.retired_date
                    contract.retired_date = member.retired_date
                    contract.save(update_fields=['end_date2', 'retired_date'])
                    change_message = u"契約終了日（%s）は退職で自動変更しました。" % member.retired_date
                    LogEntry.objects.log_action(user.id,
                                                ContentType.objects.get_for_model(contract).pk,
                                                contract.pk,
                                                unicode(contract),
                                                CHANGE,
                                                change_message=change_message)
        # 後ろに自動更新の契約しか存在しない場合、自動更新された契約を全部削除する。
        next_contracts = member.contract_set.filter(
            is_deleted=False,
            start_date__gt=member.retired_date
        ).exclude(status='04')
        if next_contracts.count() > 0 and next_contracts.count() == next_contracts.filter(status='05').count():
            for contract in next_contracts:
                contract.delete()
                change_message = u"自動更新された契約（%s(%s～)）は退職で自動削除しました。" % (
                    contract.contract_no, contract.start_date
                )
                LogEntry.objects.log_action(user.id,
                                            ContentType.objects.get_for_model(contract).pk,
                                            contract.pk,
                                            unicode(contract),
                                            CHANGE,
                                            change_message=change_message)


def get_divisions_turnover_by_month(year, month):
    """各事業部の月別売上一覧

    :param year:
    :param month:
    :return:
    """
    with connection.cursor() as cursor:
        cursor.callproc('sp_divisions_turnover_by_month', ('{:04d}'.format(int(year)), '{:02d}'.format(int(month))))
        data = common.dictfetchall(cursor)
    return data


def get_division_turnover_by_month(division_id, year, month):
    """各事業部の月別売上一覧

    :param division_id: 事業部ＩＤ
    :param year:
    :param month:
    :return:
    """
    with connection.cursor() as cursor:
        cursor.callproc('sp_division_turnover_by_month', (
            division_id, '{:04d}'.format(int(year)), '{:02d}'.format(int(month))
        ))
        data = common.dictfetchall(cursor)
    return data


def get_partner_cost_yearly():
    qs = models.PartnerCostMonthly.objects.values(
        'year',
    ).annotate(
        min_month=Min('month'),
        max_month=Max('month'),
    ).order_by('year')
    return qs


def get_partner_cost_in_year(year):
    qs = models.PartnerCostMonthly.objects.filter(year=year).values(
        'subcontractor',
        'name',
        'year',
    ).annotate(
        min_month=Min('month'),
        max_month=Max('month'),
        turnover_amount=Sum('turnover_amount'),
        tax_amount=Sum('tax_amount'),
        expenses_amount=Sum('expenses_amount'),
        amount=Sum('amount'),
    ).order_by('name')
    return qs


def get_partner_cost_in_year2(year):
    start_ym = '{}{}'.format(year, '04')
    end_ym = '{}{}'.format(int(year) + 1, '03')
    qs = models.PartnerCostMonthly.objects.filter(
        ym__gte=start_ym,
        ym__lte=end_ym,
    ).values(
        'subcontractor',
        'name',
    ).annotate(
        min_month=Min('ym'),
        max_month=Max('ym'),
        turnover_amount=Sum('turnover_amount'),
        tax_amount=Sum('tax_amount'),
        expenses_amount=Sum('expenses_amount'),
        amount=Sum('amount'),
    ).order_by('name')
    return qs
