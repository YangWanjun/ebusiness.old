# coding: UTF-8
"""
Created on 2015/08/25

@author: Yang Wanjun
"""
import os
import re
import sys
import datetime
import pytz
import calendar
import xlsxwriter
import StringIO
import math
import logging
import traceback
import pdfkit
import urlparse
from openpyxl.drawing.image import Image

import constants, errors
import jholiday

from decimal import Decimal


def get_tz_jp():
    return pytz.timezone('Asia/Tokyo')


def get_tz_utc():
    return pytz.utc


def add_days(source_date, days=1):
    return source_date + datetime.timedelta(days=days)


def add_months(source_date, months=1):
    month = source_date.month - 1 + months
    year = int(source_date.year + month / 12)
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def get_first_day_by_month(source_date):
    return datetime.date(source_date.year, source_date.month, 1)


def get_last_day_by_month(source_date):
    next_month = add_months(source_date, 1)
    return next_month + datetime.timedelta(days=-next_month.day)


def get_first_day_current_month():
    today = datetime.date.today()
    return datetime.datetime(today.year, today.month, 1, tzinfo=get_tz_jp()).date()


def get_first_day_from_ym(ym):
    if re.match(r"^[0-9]{6}$", ym):
        try:
            return datetime.date(int(ym[:4]), int(ym[4:]), 1)
        except:
            return None
    else:
        return None


def get_last_day_from_ym(ym):
    first_day = get_first_day_from_ym(ym)
    if first_day:
        return get_last_day_by_month(first_day)
    else:
        return None


def get_last_day_current_month():
    from django.utils import timezone

    return get_last_day_by_month(timezone.now())


def get_year_list():
    from eb.models import Config
    year_start = Config.get_year_list_start()
    year_end = Config.get_year_list_end()
    return [(str(year), str(year)) for year in range(int(year_start), int(year_end) + 1)]


def get_month_list3():
    return [('%02d' % month, u"%02d月" % month) for month in range(1, 13)]


def get_month_list(start_index=0, end_index=2, start_ym=None):
    month_list = []
    today = datetime.date.today()
    if start_ym:
        first_day = get_first_day_from_ym(start_ym)
        for i in range((today.year * 12 + today.month) - (first_day.year * 12 + first_day.month)):
            next_month = add_months(first_day, i)
            month_list.append((str(next_month.year), "%02d" % (next_month.month,)))
    else:
        for i in range(start_index, end_index + 1):
            next_month = add_months(today, i)
            month_list.append((str(next_month.year), "%02d" % (next_month.month,)))

    return month_list


def get_month_list2(start_date, end_date):
    month_list = []
    for i in range((end_date.year * 12 + end_date.month) - (start_date.year * 12 + start_date.month)):
        next_month = add_months(start_date, i)
        month_list.append((str(next_month.year), "%02d" % (next_month.month,)))
    return month_list


def get_request_params(query_string):
    """Requestから並び替え以外おパラメーターを取得する。

    :param query_string:
    :return:
    """
    d = dict()
    params = None
    if query_string:
        param_list = []
        for key, value in dict(query_string).items():
            if not value or not value[0] or key in ("o", "page", "year", "month"):
                continue
            if key.startswith('_') or key in ('q',):
                param_list.append((key, value[0]))
                continue
            if isinstance(value, list) and value[0]:
                val = value[0]
                if val == 'True':
                    val = True
                elif val == 'False':
                    val = False
                d[str(key)] = val
                param_list.append((key, val))
        params = "&".join(["%s=%s" % (key, value) for key, value in param_list]) if param_list else ""
    return d, "&" + params if params else ""


def get_ordering_dict(data, fields):
    """ＵＲＬからの引数を解析し、並び順を取得する。

    Arguments：
      data: 解析対象の引数の内容

    Returns：
      dict

    Raises：
      なし
    """
    d = {}
    if not data:
        data = ""

    order_list = data.split(".")

    for i, order in enumerate(fields):
        is_asc = False if order in order_list else True
        priority = get_order_priority(data, order)
        is_in_ordering = True if order in [field.lstrip("-") for field in data.split(".")] else False
        url_list = get_ordering_list(data, order)
        url_removed = None
        if is_in_ordering:
            url_removed = ".".join(get_order_removed(data, order))
        d[order] = {'is_asc': is_asc,
                    'priority': priority,
                    'url': ".".join(url_list),
                    'is_in_ordering': is_in_ordering,
                    'url_list_removed': url_removed}

    return d


def get_order_removed(data, field):
    if not data or not field:
        return []

    if not data:
        data = ""

    order_list = [order.lstrip("-") for order in data.split(".")]
    if field in order_list:
        order_list.remove(field)
    return order_list


def get_order_priority(data, field):
    if not data:
        data = ""

    order_list = [order.lstrip("-") for order in data.split(".")]
    if field in order_list:
        return order_list.index(field) + 1

    return None


def get_ordering_list(data, field=None):

    if not data:
        data = ""

    if not field:
        if not data:
            return []
        else:
            return data.split(".")

    d = {}
    for j, order in enumerate(data.split(".")):
        m = re.match("^(-?)(\w+)$", order)
        if m:
            d[m.group(2)] = (j, order)

    field_name = re.match("^(-?)(\w+)$", field).group(2)

    def get_new_orders():
        temp_list = []
        i = 1
        for o, n in orders:
            if n == field_name:
                temp_list.append("-" + field_name)
            elif n == "-" + field_name:
                temp_list.append(field_name)
        for o, n in orders:
            if n.lstrip("-") != field_name:
                temp_list.append(n)
                i += 1
        return temp_list

    if isinstance(d, dict):
        orders = d.values()
        orders.sort(key=lambda it: it[0])
        if field_name in d:
            new_orders = get_new_orders()
            return new_orders
        else:
            new_orders = [field_name]
            k = 1
            for o1, n1 in orders:
                new_orders.append(n1)
                k += 1
            return new_orders


def generate_business_plan(projects, filename):
    # create a workbook in memory
    output = StringIO.StringIO()
    row = 1
    col = 1

    book = xlsxwriter.Workbook(output)
    sheet = book.add_worksheet()
    # 見出しを書き込む
    title_format = book.add_format({'bold': True,
                                    'font_color': 'white',
                                    'bg_color': '#8db4e2',
                                    'border': 1})
    sheet.write(row + 1, col, u"顧客", title_format)
    sheet.set_column(get_excel_col_entire(col), 11)
    sheet.write(row + 1, col + 1, u"窓口", title_format)
    sheet.set_column(get_excel_col_entire(col + 1), 11)
    sheet.write(row + 1, col + 2, u"現場", title_format)
    sheet.set_column(get_excel_col_entire(col + 2), 11)
    sheet.write(row + 1, col + 3, u"部門", title_format)
    sheet.set_column(get_excel_col_entire(col + 3), 12)
    sheet.write(row + 1, col + 4, u"リーダー", title_format)
    sheet.set_column(get_excel_col_entire(col + 4), 12)
    sheet.write(row + 1, col + 5, u"メンバー", title_format)
    sheet.set_column(get_excel_col_entire(col + 5), 12)
    sheet.write(row + 1, col + 6, u"所属", title_format)
    sheet.set_column(get_excel_col_entire(col + 6), 6)
    sheet.write(row + 1, col + 7, u"入場時期", title_format)
    sheet.set_column(get_excel_col_entire(col + 7), 16)
    sheet.write(row + 1, col + 8, u"終了予定", title_format)
    sheet.set_column(get_excel_col_entire(col + 8), 16)
    sheet.write(row + 1, col + 9, u"現状・確認点", title_format)
    sheet.set_column(get_excel_col_entire(col + 9), 12)
    sheet.write(row + 1, col + 10, u"担当", title_format)
    sheet.set_column(get_excel_col_entire(col + 10), 12)
    sheet.write(row + 1, col + 11, u"進み状況", title_format)
    sheet.set_column(get_excel_col_entire(col + 11), 12)
    sheet.write(row + 1, col + 12, u"解決", title_format)
    sheet.set_column(get_excel_col_entire(col + 12), 12)

    # 詳細を書き込む
    cell_format = book.add_format({'bold': True,
                                   'border': 1})
    bp_format = book.add_format({'bold': True,
                                 'bg_color': 'yellow',
                                 'border': 1})
    date_format = book.add_format({'num_format': u'yyyy年mm月dd日',
                                   'bold': True,
                                   'border': 1})
    i = 0
    for project in projects:
        if project.members.all().count() == 0:
            continue
        # 顧客
        sheet.write(row + 2 + i, col + 0, project.client.name if project.client else "", cell_format)
        # 窓口
        sheet.write(row + 2 + i, col + 1, project.middleman.name if project.middleman else "", cell_format)
        sheet.write(row + 2 + i, col + 2, project.address, cell_format)
        first_project_member = project.get_first_project_member()
        sheet.write(row + 2 + i, col + 3, first_project_member.member.get_section().name, cell_format)
        member_name = first_project_member.member.__unicode__()
        position_ship = first_project_member.member.get_position_ship()
        member_name = u"%s(%s)" % (member_name, position_ship.get_position_display()) if position_ship else member_name
        if first_project_member.role >= 6:
            sheet.write(row + 2 + i, col + 4, member_name,
                        bp_format if first_project_member.member.subcontractor else cell_format)
            sheet.write(row + 2 + i, col + 5, "", cell_format)
        else:
            sheet.write(row + 2 + i, col + 4, "", cell_format)
            sheet.write(row + 2 + i, col + 5, member_name,
                        bp_format if first_project_member.member.subcontractor else cell_format)
        if first_project_member.member.subcontractor:
            sheet.write(row + 2 + i, col + 6, "BP", bp_format)
        else:
            sheet.write(row + 2 + i, col + 6, "", cell_format)
        sheet.write_datetime(row + 2 + i, col + 7, first_project_member.start_date, date_format)
        sheet.write_datetime(row + 2 + i, col + 8, first_project_member.end_date, date_format)
        sheet.write(row + 2 + i, col + 9, "", cell_format)
        sheet.write(row + 2 + i, col + 10, "", cell_format)
        sheet.write(row + 2 + i, col + 11, "", cell_format)
        sheet.write(row + 2 + i, col + 12, "", cell_format)
        i += 1

        for project_member in project.get_working_project_members():
            if project_member.pk == first_project_member.pk:
                continue
            sheet.write(row + 2 + i, col + 0, "", cell_format)
            sheet.write(row + 2 + i, col + 1, "", cell_format)
            sheet.write(row + 2 + i, col + 2, "", cell_format)
            sheet.write(row + 2 + i, col + 3, project_member.member.get_section().name, cell_format)
            member_name = project_member.member.__unicode__()
            position_ship = project_member.member.get_position_ship()
            member_name = u"%s(%s)" % (member_name, position_ship.get_position_display()) if position_ship else member_name
            if project_member.role >= 6:
                sheet.write(row + 2 + i, col + 4, member_name,
                            bp_format if project_member.member.subcontractor else cell_format)
                sheet.write(row + 2 + i, col + 5, "", cell_format)
            else:
                sheet.write(row + 2 + i, col + 4, "", cell_format)
                sheet.write(row + 2 + i, col + 5, member_name,
                            bp_format if project_member.member.subcontractor else cell_format)
            if project_member.member.subcontractor:
                sheet.write(row + 2 + i, col + 6, "BP", bp_format)
            else:
                sheet.write(row + 2 + i, col + 6, "", cell_format)
            sheet.write_datetime(row + 2 + i, col + 7, project_member.start_date, date_format)
            sheet.write_datetime(row + 2 + i, col + 8, project_member.end_date, date_format)
            sheet.write(row + 2 + i, col + 9, "", cell_format)
            sheet.write(row + 2 + i, col + 10, "", cell_format)
            sheet.write(row + 2 + i, col + 11, "", cell_format)
            sheet.write(row + 2 + i, col + 12, "", cell_format)
            i += 1

    # ページ設定
    sheet.set_landscape()
    sheet.set_paper(9)
    sheet.set_header('&L' + filename)
    sheet.set_margins(0, 0, 0.3, 0.1)
    sheet.set_print_scale(80)

    book.close()
    output.seek(0)
    return output


def generate_member_list(members, filename):
    output = StringIO.StringIO()
    row = 0
    col = 0

    book = xlsxwriter.Workbook(output)
    sheet = book.add_worksheet()
    # 見出しを書き込む
    title_format_top = book.add_format({'bold': True,
                                        'font_size': 20})
    title_format = book.add_format({'bold': True,
                                    'right': 1,
                                    'top': 2,
                                    'bg_color': '#b7dee8',
                                    'align': 'center',
                                    'text_wrap': True,
                                    'valign': 'vcenter'})
    title_format_left = book.add_format({'bold': True,
                                         'right': 1,
                                         'top': 2,
                                         'left': 2,
                                         'bg_color': '#b7dee8',
                                         'align': 'center',
                                         'valign': 'vcenter'})
    title_format_right = book.add_format({'bold': True,
                                          'right': 2,
                                          'top': 2,
                                          'bg_color': '#b7dee8',
                                          'align': 'center',
                                          'valign': 'vcenter'})
    sheet.write(row, col + 5, filename, title_format_top)
    row += 2
    sheet.set_row(row, 33)
    sheet.write(row, col, u"No.", title_format_left)
    sheet.set_column(get_excel_col_entire(col), 3.5)
    sheet.write(row, col + 1, u"名前", title_format)
    sheet.set_column(get_excel_col_entire(col + 1), 10)
    sheet.write(row, col + 2, u"スキル", title_format)
    sheet.set_column(get_excel_col_entire(col + 2), 26)
    sheet.write(row, col + 3, u"年齢", title_format)
    sheet.set_column(get_excel_col_entire(col + 3), 7)
    sheet.write(row, col + 4, u"性別", title_format)
    sheet.set_column(get_excel_col_entire(col + 4), 7)
    sheet.write(row, col + 5, u"レベル", title_format)
    sheet.set_column(get_excel_col_entire(col + 5), 9)
    sheet.write(row, col + 6, u"役割", title_format)
    sheet.write(row, col + 7, u"IT業界\r\n経験年数", title_format)
    sheet.set_column(get_excel_col_entire(col + 7), 9.13)
    sheet.write(row, col + 8, u"最寄駅", title_format)
    sheet.set_column(get_excel_col_entire(col + 8), 11)
    sheet.write(row, col + 9, u"得意業務", title_format)
    sheet.set_column(get_excel_col_entire(col + 9), 12)
    sheet.write(row, col + 10, u"日本語", title_format)
    sheet.set_column(get_excel_col_entire(col + 10), 12)
    sheet.write(row, col + 11, u"参加可能日", title_format)
    sheet.set_column(get_excel_col_entire(col + 11), 11)
    sheet.write(row, col + 12, u"備考", title_format_right)
    sheet.set_column(get_excel_col_entire(col + 12), 20)

    # 詳細を書き込む
    cell_format_center = book.add_format({'align': 'center',
                                          'valign': 'vcenter',
                                          'border': 1})
    cell_format_left = book.add_format({'valign': 'vcenter',
                                        'text_wrap': True,
                                        'border': 1})
    row += 1
    for i, member in enumerate(members):
        sheet.set_row(row + i, 27)
        # No.
        sheet.write(row + i, col, i + 1, cell_format_center)
        # 名前
        sheet.write(row + i, col + 1, member.__unicode__(), cell_format_center)
        # スキル
        skill_list = member.get_skill_list()
        sheet.write(row + i, col + 2, ",".join([skill.name for skill in skill_list]), cell_format_center)
        # 年齢
        sheet.write(row + i, col + 3, member.get_age(), cell_format_center)
        # 性別
        sheet.write(row + i, col + 4, member.get_sex_display(), cell_format_center)
        # レベル
        sheet.write(row + i, col + 5, ",".join(member.get_project_role_list()), cell_format_center)
        # 役割
        position_ship = member.get_position_ship(is_min=True)
        position_name = position_ship.get_position_display() if position_ship else u"メンバー"
        sheet.write(row + i, col + 6, position_name, cell_format_center)
        # IT業界経験年数
        sheet.write(row + i, col + 7, "", cell_format_center)
        # 最寄駅
        sheet.write(row + i, col + 8, member.nearest_station, cell_format_center)
        # 得意業務
        sheet.write(row + i, col + 9, "", cell_format_center)
        # 日本語
        sheet.write(row + i, col + 10, member.japanese_description, cell_format_center)
        # 参加可能日
        sheet.write(row + i, col + 11, "", cell_format_center)
        # 備考
        sheet.write(row + i, col + 12, member.comment, cell_format_left)

    # ページ設定
    sheet.set_landscape()
    sheet.set_paper(9)  # 印刷用紙：A4
    sheet.set_print_scale(85)

    book.close()
    output.seek(0)
    return output


def get_excel_col_by_index(col):
    # col は０から
    if (col >= 0) and (col <= 25):
        return chr(col + 65)
    elif (col > 25) and (col < 702):
        a, b = divmod(col, 26)
        return chr(a + 64) + chr(b + 65)


def get_excel_col_entire(col):
    c = get_excel_col_by_index(col)
    return "%s:%s" % (c, c)


def get_default_password(member):
    return "password"


def line_counter():

    def get_line_count(p):
        cnt = 0
        if os.path.exists(p):
            for line in open(p, 'r'):
                if not re.match(r"^\s*#", line) and not re.match(r"^\s*$", line):
                    cnt += 1
        return cnt

    path = os.path.abspath(os.path.dirname(os.path.dirname(sys.argv[0])))
    all_count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            name, ext = os.path.splitext(f)
            path_file = os.path.join(root, f)
            if ext == ".py" and os.path.dirname(path_file).split("\\")[-1] != "migrations":
                count = get_line_count(path_file)
                all_count += count
                print path_file.ljust(80), count
    print "Total line count: %s" % (all_count,)


def get_insert_sql():
    path = r"C:\Github\ebusiness\data.sql"
    sql_list = []
    for line in open(path, 'r'):
        if line.startswith('CREATE TABLE "eb_') or line.startswith("INSERT INTO `eb_"):
            sql_list.append(line)
    if not sql_list:
        return

    lst = []
    items = []
    for i in sql_list:
        i = i.strip()
        if i.startswith("CREATE TABLE"):
            del lst[:]
            for item in re.findall(r'"([a-z_0-9]+)"', i):
                if (item == "id") or lst:
                    if not item.startswith("eb_") and not item.startswith("auth_") and item not in lst:
                        lst.append(item)
            items = ",".join(lst)
        else:
            print i.replace("VALUES", "(%s) VALUES" % (items,))


def is_salesperson(user):
    try:
        if user.salesperson:
            return True
        else:
            return False
    except:
        return False


def is_salesperson_director(user):
    try:
        if user.salesperson.member_type == 0:
            return True
        else:
            return False
    except:
        return False


def parse_date_from_string(str_date, split1=u'/', split2=u'/', split3=u''):
    """文字列から、日付を解析する。

    Arguments：
      str_date: 解析要の文字列
      split1: 区切り
      split2:
      split3:

    Returns：
      date型

    Raises：
      なし
    """
    if str_date and str_date.strip():
        str_date = str_date.strip().encode("utf-8")
        dt = datetime.datetime.strptime(str_date, "%Y" +
                                        split1.encode("utf-8") + "%m" +
                                        split2.encode("utf-8") + "%d" +
                                        split3.encode("utf-8"))
        return datetime.date(dt.year, dt.month, dt.day)
    else:
        return None


def parse_date_from_string2(str_date, split1=u'/', split2=u''):
    """文字列から、日付を解析する。

    Arguments：
      str_date: 解析要の文字列
      split1: 区切り
      split2:

    Returns：
      date型

    Raises：
      なし
    """
    if str_date and str_date.strip():
        str_date = str_date.strip().encode("utf-8")
        dt = datetime.datetime.strptime(str_date, "%Y" +
                                        split1.encode("utf-8") + "%m" +
                                        split2.encode("utf-8"))
        return datetime.date(dt.year, dt.month, dt.day)
    else:
        return None


def parse_os_lang(name):
    """履歴書を読み込む時、文字列からＯＳを解析する。

    Arguments：
      name: 解析要の文字列

    Returns：
      解析後の文字列

    Raises：
      なし
    """
    if not name:
        return None

    name = name.strip().lower()
    new_name = ""
    for i in name:
        if re.match(ur"[0-9a-z/# ]", i, re.U):
            new_name += i
    if new_name:
        return new_name.title()
    else:
        return None


def parse_project_role(name):
    """案件の作業区分を解析する。

    Arguments：
      name: 解析要の文字列

    Returns：
      解析後の文字列

    Raises：
      なし
    """
    if not name:
        return None
    name = name.strip().upper()
    if name == "PM":
        return "PM"
    elif name == "PL":
        return "L"
    elif name in [v for v, m in constants.CHOICE_PROJECT_ROLE]:
        return name
    else:
        return None


def get_first_last_name(name):
    if name:
        name = name.strip()
        reg = re.compile(ur"[ 　]+", re.UNICODE)
        if reg.search(name):
            return reg.split(name)
        else:
            return name[:1], name[1:]
    else:
        return None, None


def get_first_last_ja_name(name):
    if name:
        reg = re.compile(ur"[ 　]+", re.UNICODE)
        return reg.split(name)
    else:
        return None, None


def get_next_employee_id(max_employee_id, min_value=10000):
    if not max_employee_id:
        return min_value
    m = re.search(r"^[A-Za-z]*", max_employee_id)
    prefix = m.group()
    m = re.search(r"[0-9]+", max_employee_id)
    max_num = m.group()
    len_num = len(max_num)
    next_num = int(max_num) + 1
    len_right_num = len(str(next_num))
    str_num = "0" * (len_num - len_right_num) + str(next_num)
    return prefix + str_num


def get_full_postcode(postcode):
    if postcode:
        return "%s-%s" % (postcode[:3], postcode[3:])
    else:
        return ""


def get_request_file_path(request_no, client_name, ym):
    """生成された請求書のパスを取得する。

    :param request_no: 請求番号
    :param client_name: お客様名称
    :param ym: 対象年月
    :return:
    """
    from django.conf import settings

    now = datetime.datetime.now()
    filename = "WT請求書_%s_%s_%s" % (str(request_no), client_name.encode('UTF-8'), now.strftime("%Y%m%d_%H%M%S%f"))
    path = os.path.join(settings.GENERATED_FILES_ROOT, "project_request", str(ym))
    if not os.path.exists(path):
        os.makedirs(path)
    xlsx_path = "%s.xlsx" % os.path.join(path, filename).decode('UTF-8')
    pdf_path = "%s.pdf" % os.path.join(path, filename).decode('UTF-8')
    return xlsx_path, pdf_path


def get_subcontractor_request_root_path():
    from django.conf import settings
    path = os.path.join(settings.GENERATED_FILES_ROOT, "subcontractor_request")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_subcontractor_pay_notify_root_path():
    from django.conf import settings
    path = os.path.join(settings.GENERATED_FILES_ROOT, "pay_notify")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_subcontractor_request_file_path(request_no, subcontractor_name, ym):
    now = datetime.datetime.now()
    filename = "協力会社請求書_%s_%s_%s" % (
        str(request_no), subcontractor_name.encode('UTF-8'), now.strftime("%Y%m%d_%H%M%S%f")
    )
    path = os.path.join(get_subcontractor_request_root_path(), str(ym))
    if not os.path.exists(path):
        os.makedirs(path)
    xlsx_path = "%s.xlsx" % os.path.join(path, filename).decode('UTF-8')
    pdf_path = "%s.pdf" % os.path.join(path, filename).decode('UTF-8')
    return xlsx_path, pdf_path


def get_pay_notify_file_path(no, client_name, ym):
    now = datetime.datetime.now()
    name_format = "WT支払通知書_%s_%s_%s"
    filename = name_format % (str(no), client_name.encode('UTF-8'), now.strftime("%Y%m%d_%H%M%S%f"))
    path = os.path.join(get_subcontractor_pay_notify_root_path(), str(ym))
    if not os.path.exists(path):
        os.makedirs(path)
    xlsx_path = "%s.xlsx" % os.path.join(path, filename).decode('UTF-8')
    pdf_path = "%s.pdf" % os.path.join(path, filename).decode('UTF-8')
    return xlsx_path, pdf_path


def get_order_file_path(order_no, client_name, project_name, member_name, ym, is_request=False):
    """協力会社の注文書のパスを取得する。

    :param order_no:
    :param client_name:
    :param member_name:
    :param ym:
    :param is_request: 注文請書
    :return:
    """
    from django.conf import settings

    now = datetime.datetime.now()
    if is_request:
        name_xls_format = "WT注文請書_%s_%s%s%s_%s.xlsx"
        name_pdf_format = "WT注文請書_%s_%s%s%s_%s.pdf"
    else:
        name_xls_format = "WT注文書_%s_%s%s%s_%s.xlsx"
        name_pdf_format = "WT注文書_%s_%s%s%s_%s.pdf"
    filename_xls = name_xls_format % (
        str(order_no),
        (project_name.replace('/', u"／").encode('UTF-8') + "_") if project_name else '',
        (member_name.encode('UTF-8') + "_") if member_name else '',
        client_name.encode('UTF-8'),
        now.strftime("%H%M%S%f")
    )
    filename_pdf = name_pdf_format % (
        str(order_no),
        (project_name.replace('/', u"／").encode('UTF-8') + "_") if project_name else '',
        (member_name.encode('UTF-8') + "_") if member_name else '',
        client_name.encode('UTF-8'),
        now.strftime("%H%M%S%f")
    )
    path = os.path.join(settings.GENERATED_FILES_ROOT, "partner_order", str(ym))
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, filename_xls).decode('UTF-8'), os.path.join(path, filename_pdf).decode('UTF-8')


def get_template_pay_notify_path(company):
    return company.pay_notify_file.path


def get_temp_path():
    from django.conf import settings
    path = os.path.join(settings.MEDIA_ROOT, 'temp')
    if not os.path.exists(path):
        os.mkdir(path)
    return path


def get_template_order_path(contract, is_request=False):
    """注文書のテンプレートパスを取得する

    :param contract:
    :param is_request: 注文請書
    :return:
    """
    from django.conf import settings

    if not contract:
        raise errors.CustomException(constants.ERROR_BP_NO_CONTRACT)
    if hasattr(contract, 'is_hourly_pay') and contract.is_hourly_pay:
        # 時給
        filename = "eb_order_hourly"
    elif hasattr(contract, 'is_fixed_cost') and contract.is_fixed_cost:
        # 固定給料
        filename = "eb_order_fixed"
    elif type(contract).__name__ == 'BpLumpContract':
        # 一括
        filename = "eb_order_lump"
    else:
        # 既定
        filename = "eb_order"
    if is_request:
        filename = "%s(request).xlsx" % filename
    else:
        filename = "%s.xlsx" % filename
    return os.path.join(settings.MEDIA_ROOT, 'eb_order', filename)


def delete_temp_files(path):
    """一時ファイルを削除する。

    Arguments：
      path: 一時ファイルの存在するフォルダー

    Returns：
      なし

    Raises：
      なし
    """
    for f in os.listdir(path):
        try:
            os.remove(os.path.join(path, f))
        except Exception as e:
            print e.message


def get_year_month_list(start_date, end_date, is_reverse=True, add_future=False):
    """開始日付から終了日付までの年月を取得する。

    Arguments：
      start_date: 開始日付
      end_date: 終了日付
      is_reverse: 戻り値の並び順

    Returns：
      なし

    Raises：
      なし
    """
    ret = []
    if start_date and end_date:
        today = datetime.date.today()
        months1 = (start_date.year * 12) + start_date.month
        months2 = (end_date.year * 12) + end_date.month
        if months1 <= months2:
            for i in range(months2 - months1 + 1):
                d = add_months(start_date, i)
                if (today.year * 12 + today.month) >= (d.year * 12 + d.month) or add_future:
                    ret.append(["%04d" % (d.year,), "%02d" % (d.month,)])

    ret.sort(key=lambda ym: ym[0] + ym[1], reverse=is_reverse)
    return ret


def get_quotation_no(user):
    prefix = '#'
    try:
        if user and user.salesperson:
            if user.salesperson.first_name_en:
                prefix = user.salesperson.first_name_en[0]
    except:
        pass
    today = datetime.date.today()
    return "WT{0:04d}{1:02d}{2:02d}{3}{4}".format(today.year, today.month, today.day, prefix, "001")


def get_excel_replacements(text):
    """エクセルの置換文字列を取得する。

    :param text セルの文字列
    :return 置換文字列
    """
    return re.findall(constants.REG_EXCEL_REPLACEMENT, text, re.U)


def get_unicode(s):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, str):
        return s.decode('utf8')
    else:
        return s


def get_business_days(year, month, exclude=None):
    from eb.models import Holiday
    business_days = []
    eb_holidays = [holiday.date for holiday in Holiday.objects.public_all()]
    for i in range(1, 32):
        try:
            this_date = datetime.date(int(year), int(month), i)
        except ValueError:
            break
        if this_date.weekday() < 5 and jholiday.holiday_name(int(year), int(month), i) is None:
            # Monday == 0, Sunday == 6
            if exclude and this_date.strftime("%Y/%m/%d") not in exclude:
                business_days.append(this_date)
            elif exclude is None:
                business_days.append(this_date)
    return [date for date in business_days if date not in eb_holidays]


def get_form_changed_value(form, field):
    """フォームに指定した項目と変更前、変更後の値を取得する。

    :param form:
    :param field:
    :return: (ラベル名、変更前値、変更後値)
    """
    old_value = form.initial.get(field, 'Unknown')
    new_value = form.cleaned_data.get(field, 'Unknown')
    label_name = form.fields.get(field).label
    if form.instance and hasattr(form.instance, 'get_' + field + '_display'):
        new_value = getattr(form.instance, 'get_' + field + '_display')()
        if form.fields.get(field).choices:
            for value, text in form.fields.get(field).choices:
                if value == old_value:
                    old_value = text
                    break
    return label_name, old_value, new_value


def get_formset_changed_value(formset, changed_object, changed_fields):
    """Formsetに変更した項目と変更前、変更後の値を取得する。

    :param formset:
    :param changed_object:
    :param changed_fields:
    :return: (ラベル名、変更前値、変更後値)のリスト
    """
    changed_values = []
    for form in formset.forms:
        if form.instance.pk == changed_object.pk:
            for field in changed_fields:
                changed_values.append(get_form_changed_value(form, field))
    return changed_values


def get_object_changed_message(obj, field, new_value, changed_list=None):
    """models.Modelのインスタンスから変更メッセージを取得する。

    :param obj: models.Modelのインスタンス
    :param field:
    :param new_value:
    :param changed_list:
    :return:
    """
    verbose_name = obj._meta.get_field(field).verbose_name
    if obj.pk:
        # 更新の場合
        old_value = getattr(obj, field)
        if isinstance(old_value, Decimal):
            old_value = "%.2f" % old_value
            new_value = "%.2f" % new_value
        if old_value != new_value:
            message = u"%s(%s→%s)" % (verbose_name, old_value, new_value)
            if isinstance(changed_list, list):
                changed_list.append(message)
            return message
        else:
            return ''
    else:
        # 追加の場合
        if new_value:
            message = u"%s(%s)" % (verbose_name, new_value)
            if isinstance(changed_list, list):
                changed_list.append(message)
            return message
        else:
            return ''


def get_attendance_total_hours(total_hours, attendance_type):
    """出勤の計算区分によって、勤務期間を取得する。

    :param total_hours: 入力した時間
    :param attendance_type: 出勤の計算区分
    :return:
    """
    if not total_hours:
        return 0
    elif isinstance(total_hours, int) or isinstance(total_hours, long):
        return total_hours
    elif isinstance(total_hours, float) or isinstance(total_hours, Decimal):
        float_part, int_part = math.modf(total_hours)
        if attendance_type == '1':
            # １５分ごと
            if 0 <= float_part < 0.25:
                return int_part
            elif 0.25 <= float_part < 0.5:
                return int_part + 0.25
            elif 0.5 <= float_part < 0.75:
                return int_part + 0.5
            else:
                return int_part + 0.75
        elif attendance_type == '2':
            # ３０分ごと
            if 0 <= float_part < 0.5:
                return int_part
            else:
                return int_part + 0.5
        else:
            # １時間ごと
            return int_part
    else:
        return 0


def is_human_resources(user):
    return has_group(user, u"人事")


def has_group(user, group_name):
    """ユーザーが指定にグループに所属しているかどうかをチェックする。

    :param user:
    :param group_name:
    :return:
    """
    from django.contrib.auth.models import Group

    if user.username == 'admin':
        return True
    try:
        group = Group.objects.get(name=group_name)
        return True if group in user.groups.all() else False
    except Group.DoesNotExist:
        return False


def is_cross_date(dates, d, index):
    for j, p in enumerate(dates):
        d1, d2 = p
        if j == index:
            continue
        if d2 is not None and d1 <= d <= d2:
            return True
        elif d2 is None and d1 <= d:
            return True
    return False


def to_wareki(date):
    prefix = ''
    years = date.year
    return u"%s%s年%02d月%02d日" % (prefix, years, date.month, date.day)


def get_bp_order_publish_date(year, month, str_date):
    """ＢＰ注文書の発行年月日を取得する。

    :param year:
    :param month:
    :param str_date:
    :return:
    """
    if str_date and isinstance(str_date, basestring):
        try:
            publish_date = datetime.datetime.strptime(str_date, '%Y/%m/%d').date()
            return publish_date
        except ValueError:
            pass
    today = datetime.date.today()
    if '%04d%02d' % (int(year), int(month) - 1) == today.strftime('%Y%m'):
        # 作成しようとしている注文書はちょうど来月の場合、発行年月日は現在の日付とする。
        return today
    else:
        from pandas.tseries.offsets import BDay
        return datetime.date(int(year), int(month), 1) - BDay(1)


def get_sales_logger():
    """営業システムのロガーを取得する。

    :return:
    """
    return logging.getLogger('wt_sales')


def get_organization_children(organization):
    """組織及び子組織のリストを取得する

    :param organization:
    :return:
    """
    all_children = organization.get_children()
    org_pk_list = [org.pk for org in all_children]
    org_pk_list.append(organization.pk)
    return org_pk_list


def data_frame_filter(df, param_dict=None, order_list=None):
    if param_dict and isinstance(param_dict, dict):
        from eb import models
        for k, v in param_dict.items():
            if k == 'organization_id':
                organization = models.Section.objects.get(pk=v)
                org_pk_list = get_organization_children(organization)
                df = df[(df.division_id.isin(org_pk_list)) | (df.section_id.isin(org_pk_list)) | (
                df.subsection_id.isin(org_pk_list))]
            elif k.endswith('_id'):
                df = df[df[k] == int(v)]
            elif k.startswith('is_'):
                df = df[df[k] == int(v)]
            else:
                df = df[df[k].str.contains(v, na=False)]
    if order_list:
        name = order_list[0].strip('-')
        ascending = not order_list[0].startswith('-')
        df = df.sort_values(by=name, ascending=ascending)
    return df


def generate_pdf_from_url(url, out_path):
    try:
        # config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        # TODO: パスに日本語があったら、エラーになる。暫定対策：英語にしてから、また日本語名に変更する。
        path, name = os.path.split(out_path)
        en_name = get_alpha_beta(name)
        options = {'encoding': "UTF-8"}
        pdfkit.from_url(url, os.path.join(path, en_name), options=options)
        os.rename(os.path.join(path, en_name), os.path.join(path, name))
    except Exception as ex:
        logger = get_sales_logger()
        logger.error(ex)
        logger.error(traceback.format_exc())


def get_alpha_beta(s):
    if s and isinstance(s, basestring):
        return ".".join(re.findall(r"\w+", s))
    else:
        return s


def get_absolute_url(url):
    from eb.models import Config
    domain_name = Config.get_domain_name()
    return urlparse.urljoin(domain_name, url)


def get_pay_notify_deadline(year, month):
    """支払通知書とＢＰ注文書をメール送信時の支払締切日を取得する

    来月の第六営業日

    :return:
    """
    date = get_first_day_from_ym('%04d%02d' % (int(year), int(month)))
    next_month = add_months(date, 1)
    business_days = get_business_days(next_month.year, next_month.month)
    if len(business_days) > 5:
        return business_days[5]
    else:
        return next_month


def get_signature_image():
    """電子印鑑の画像を取得する。

    :return:
    """
    from django.conf import settings
    img_path = os.path.join(settings.STATICFILES_DIRS[0], 'admin/img/signature.png')
    img = Image(img_path)
    img.width = 90
    img.height = 90
    return img


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


if __name__ == "__main__":
    for it in range(1, 10):
        print u'2016年%02d月' % (it,), get_business_days(2016, it)
