# coding: UTF-8
"""
Created on 2015/09/28

@author: Yang Wanjun
"""
from __future__ import unicode_literals
from decimal import Decimal

EXCEL_APPLICATION = "Excel.Application"
EXCEL_FORMAT_EXCEL2003 = 56

LOG_EB_SALES = 'wt_sales'

LOGIN_IN_URL = '/wt/login/'

REG_DATE_STR = ur"\d{4}([-/.年])\d{1,2}([-/.月])\d{1,2}([日]?)"
REG_DATE_STR2 = ur"\d{4}([-/.年])\d{1,2}([-/.月]?)"
REG_EXCEL_REPLACEMENT = ur"\{\$([A-Z0-9_]+)\$\}"

MIME_TYPE_EXCEL = 'application/excel'
MIME_TYPE_PDF = 'application/pdf'
MIME_TYPE_ZIP = 'application/zip'
MIME_TYPE_HTML = 'text/html'

MAIL_GROUP_SUBCONTRACTOR_PAY_NOTIFY = 'mail_subcontractor_pay_notify'
MAIL_GROUP_MEMBER_ORDER = 'mail_member_order'

NAME_SYSTEM = "営業支援システム"
NAME_BUSINESS_PLAN = "%02d月営業企画"
NAME_MEMBER_LIST = "最新要員一覧"
NAME_RESUME = "WT履歴書_%s_%s"
NAME_SECTION_ATTENDANCE = "勤怠情報_%s_%04d年%02d月"
NAME_MEMBERS_COST = "要員コスト一覧_%s"

BATCH_MEMBER_STATUS = 'member_status'
BATCH_SYNC_MEMBERS = 'sync_members'
BATCH_SYNC_CONTRACT = 'sync_contract'
BATCH_SYNC_BP_CONTRACT = 'sync_bp_contract'
BATCH_SEND_ATTENDANCE_FORMAT = 'send_attendance_format'
BATCH_PUSH_NEW_MEMBER = 'push_new_member'
BATCH_PUSH_BIRTHDAY = 'push_birthday'
BATCH_PUSH_WAITING_MEMBER = 'push_waiting_member'
BATCH_SYNC_MEMBERS_COST = 'sync_members_cost'

CONFIG_ADMIN_EMAIL_ADDRESS = 'admin_email_address'
CONFIG_ADMIN_EMAIL_SMTP_HOST = 'admin_email_smtp_host'
CONFIG_ADMIN_EMAIL_SMTP_PORT = 'admin_email_smtp_port'
CONFIG_ADMIN_EMAIL_PASSWORD = 'admin_email_password'
CONFIG_DOMAIN_NAME = 'domain_name'
CONFIG_YEAR_LIST_START = 'year_list_start'
CONFIG_YEAR_LIST_END = 'year_list_end'
CONFIG_PAGE_SIZE = 'page_size'
CONFIG_THEME = 'theme'
CONFIG_ISSUE_MAIL_BODY = 'issue_mail_body'
CONFIG_USER_CREATE_MAIL_BODY = 'user_create_mail_body'
CONFIG_SERVICE_MEMBERS = 'service_members'
CONFIG_SERVICE_CONTRACT = 'service_contract'
CONFIG_SALES_SYSTEM_NAME = 'sales_system_name'
# 契約設定
CONFIG_GROUP_SYSTEM = 'system'
CONFIG_GROUP_CONTRACT = 'contract'
CONFIG_GROUP_BP_ORDER = 'bp_order'
CONFIG_EMPLOYMENT_PERIOD_COMMENT = 'employment_period_comment'
CONFIG_BUSINESS_ADDRESS = 'employment_business_address'
CONFIG_BUSINESS_TIME = 'business_time'
CONFIG_BUSINESS_OTHER = 'business_other'
CONFIG_ALLOWANCE_DATE_COMMENT = 'allowance_date_comment'
CONFIG_ALLOWANCE_CHANGE_COMMENT = 'allowance_change_comment'
CONFIG_BONUS_COMMENT = 'bonus_comment'
CONFIG_HOLIDAY_COMMENT = 'holiday_comment'
CONFIG_PAID_VACATION_COMMENT = 'paid_vacation_comment'
CONFIG_NO_PAID_VACATION_COMMENT = 'no_paid_vacation_comment'
CONFIG_RETIRE_COMMENT = 'retire_comment'
CONFIG_CONTRACT_COMMENT = 'contract_comment'
CONFIG_BP_ORDER_DELIVERY_PROPERTIES = 'delivery_properties'
CONFIG_BP_ORDER_PAYMENT_CONDITION = 'payment_condition'
CONFIG_BP_ORDER_CONTRACT_ITEMS = 'contract_items'
CONFIG_DEFAULT_EXPENSES_ID = 'default_expenses_category_id'
CONFIG_FIREBASE_SERVERKEY = 'firebase_serverkey'
CONFIG_GCM_URL = 'gcm_url'
CONFIG_BP_ATTENDANCE_TYPE = 'bp_attendance_type'

MARK_POST_CODE = "〒"

DOWNLOAD_REQUEST = "request"
DOWNLOAD_BUSINESS_PLAN = "business_plan"
DOWNLOAD_MEMBER_LIST = "member_list"
DOWNLOAD_RESUME = "resume"
DOWNLOAD_QUOTATION = "quotation"
DOWNLOAD_ORDER = "order"

ERROR_TEMPLATE_NOT_EXISTS = "テンプレートファイルが存在しません。"
ERROR_REQUEST_FILE_NOT_EXISTS = "作成された請求書は存在しません、" \
                                "サーバーに該当する請求書が存在するのかを確認してください。"
ERROR_BP_ORDER_FILE_NOT_EXISTS = "作成された注文書は存在しません、" \
                                 "サーバーに該当する注文書が存在するのかを確認してください。"
ERROR_CANNOT_GENERATE_2MONTH_BEFORE = "２ヶ月前の請求書は作成できない"
ERROR_INVALID_TOTAL_HOUR = "勤務時間のデータ不正、空白になっているのか、または０になっているのかご確認ください。"
ERROR_BP_NO_CONTRACT = "当該協力社員は契約情報が存在しません。"

PROJECT_STAGE = (
    "要件定義", "調査分析",
    "基本設計", "詳細設計",
    "開発製造", "単体試験",
    "結合試験", "総合試験",
    "保守運用", "サポート"
)

CHOICE_PROJECT_MEMBER_STATUS = (
    (1, "提案中"),
    (2, "作業確定")
)
CHOICE_PROJECT_STATUS = (
    (1, "提案"),
    (2, "予算審査"),
    (3, "予算確定"),
    (4, "実施中"),
    (5, "完了")
)
CHOICE_PROJECT_BUSINESS_TYPE = (
    ('01', "金融（銀行）"),
    ('02', "金融（保険）"),
    ('03', "金融（証券）"),
    ('04', "製造"),
    ('05', "サービス"),
    ('06', "その他")
)
CHOICE_SKILL_TIME = (
    (0, "未経験者可"),
    (1, "１年以上"),
    (2, "２年以上"),
    (3, "３年以上"),
    (5, "５年以上"),
    (10, "１０年以上")
)
CHOICE_DEGREE_TYPE = (
    (1, "小・中学校"),
    (2, "高等学校"),
    (3, "専門学校"),
    (4, "高等専門学校"),
    (5, "短期大学"),
    (6, "大学学部"),
    (7, "大学大学院")
)
CHOICE_SALESPERSON_TYPE = (
    (0, "営業部長"),
    (1, "その他"),
    (5, "営業担当"),
    (6, "取締役"),
    (7, "代表取締役社長")
)
CHOICE_CLIENT_MEMBER_TYPE = (
    ('01', "代表取締役社長"),
    ('02', "取締役"),
    ('03', "営業"),
    ('99', "その他")
)
CHOICE_MEMBER_TYPE = (
    (1, "正社員"),
    (2, "契約社員"),
    (3, "個人事業者"),
    (4, "他社技術者"),
    (5, "パート"),
    (6, "アルバイト"),
    (7, "正社員（試用期間）")
)
CHOICE_CLIENT_CONTRACT_TYPE = (
    ('01', "業務委託"),
    ('02', "準委任"),
    ('03', "派遣"),
    ('04', "一括"),
    # ('05', "ソフト加工"),
    ('10', "出向"),
    # ('11', "出向（在籍）"),
    # ('12', "出向（完全）"),
    ('99', "その他"),
)
CHOICE_BP_CONTRACT_TYPE = (
    ('01', "業務委託"),
    ('02', "準委任"),
    ('03', "派遣"),
    ('04', "一括"),
    # ('05', "ソフト加工"),
    # ('10', "出向"),
    ('11', "出向（在籍）"),
    ('12', "出向（完全）"),
    ('99', "その他"),
)
CHOICE_PROJECT_ROLE = (
    ("OP", "OP：ｵﾍﾟﾚｰﾀｰ"),
    ("PG", "PG：ﾌﾟﾛｸﾞﾗﾏｰ"),
    ("SP", "SP：ｼｽﾃﾑﾌﾟﾛｸﾞﾗﾏｰ"),
    ("SE", "SE：ｼｽﾃﾑｴﾝｼﾞﾆｱ"),
    ("SL", "SL：ｻﾌﾞﾘｰﾀﾞｰ"),
    ("L", "L：ﾘｰﾀﾞｰ"),
    ("M", "M：ﾏﾈｰｼﾞｬｰ")
)
CHOICE_POSITION = (
    (Decimal('1.0'), "代表取締役"),
    (Decimal('1.1'), "取締役"),
    (Decimal('3.0'), "事業部長"),
    (Decimal('3.1'), "副事業部長"),
    (Decimal('4.0'), "部長"),
    (Decimal('5.0'), "担当部長"),
    (Decimal('6.0'), "課長"),
    (Decimal('7.0'), "担当課長"),
    (Decimal('8.0'), "PM"),
    (Decimal('9.0'), "リーダー"),
    (Decimal('10.0'), "サブリーダー"),
    (Decimal('11.0'), "勤務統計者")
)
CHOICE_SEX = (
    ('1', "男"), ('2', "女")
)
CHOICE_SEX_EBOA = (
    ('1', "男"), ('0', "女")
)
CHOICE_MARRIED = (
    ('', "------"), ('0', "未婚"), ('1', "既婚")
)
CHOICE_PAYMENT_MONTH = (
    ('1', "翌月"),
    ('2', "翌々月"),
    ('3', "３月"),
    ('4', "４月"),
    ('5', "５月"),
    ('6', "６月")
)
CHOICE_PAYMENT_DAY = (
    ('01', '1日'),
    ('02', '2日'),
    ('03', '3日'),
    ('04', '4日'),
    ('05', '5日'),
    ('06', '6日'),
    ('07', '7日'),
    ('08', '8日'),
    ('09', '9日'),
    ('10', '10日'),
    ('11', '11日'),
    ('12', '12日'),
    ('13', '13日'),
    ('14', '14日'),
    ('15', '15日'),
    ('16', '16日'),
    ('17', '17日'),
    ('18', '18日'),
    ('19', '19日'),
    ('20', '20日'),
    ('21', '21日'),
    ('22', '22日'),
    ('23', '23日'),
    ('24', '24日'),
    ('25', '25日'),
    ('26', '26日'),
    ('27', '27日'),
    ('28', '28日'),
    ('29', '29日'),
    ('30', '30日'),
    ('99', '月末')
)
CHOICE_ATTENDANCE_YEAR = (
    ('2014', "2014年"),
    ('2015', "2015年"),
    ('2016', "2016年"),
    ('2017', "2017年"),
    ('2018', "2018年"),
    ('2019', "2019年"),
    ('2020', "2020年")
)
CHOICE_ATTENDANCE_MONTH = (
    ('01', '1月'),
    ('02', '2月'),
    ('03', '3月'),
    ('04', '4月'),
    ('05', '5月'),
    ('06', '6月'),
    ('07', '7月'),
    ('08', '8月'),
    ('09', '9月'),
    ('10', '10月'),
    ('11', '11月'),
    ('12', '12月')
)
CHOICE_ACCOUNT_TYPE = (
    ("1", "普通預金"),
    ("2", "定期預金"),
    ("3", "総合口座"),
    ("4", "当座預金"),
    ("5", "貯蓄預金"),
    ("6", "大口定期預金"),
    ("7", "積立定期預金")
)
CHOICE_ATTENDANCE_TYPE = (
    ('1', "１５分ごと"),
    ('2', "３０分ごと"),
    ('3', "１時間ごと")
)
CHOICE_TAX_RATE = (
    (Decimal('0.00'), "税なし"),
    (Decimal('0.05'), "5％"),
    (Decimal('0.08'), "8％"),
    (Decimal('0.10'), "10％"),
)
CHOICE_DECIMAL_TYPE = (
    ('0', "四捨五入"),
    ('1', "切り捨て")
)
CHOICE_DEV_LOCATION = (
    ('01', "東大島"),
    ('02', "田町"),
    ('03', "府中"),
    ('04', "西葛西"),
    ('05', "中目黒")
)
CHOICE_NOTIFY_TYPE = (
    (1, "EBのメールアドレス"),
    (2, "個人メールアドレス"),
    (3, "EBと個人両方のメールアドレス")
)
CHOICE_ISSUE_STATUS = (
    ('1', "起票"),
    ('2', "対応中"),
    ('3', "対応完了"),
    ('4', "クローズ"),
    ('5', "取下げ")
)
CHOICE_ISSUE_LEVEL = (
    (1, "低"),
    (2, "中"),
    (3, "高"),
    (4, "至急"),
    (5, "大至急")
)
CHOICE_THEME = (
    ('default', 'デフォルト'),
    ('materialize', 'Materialize')
)
CHOICE_ORG_TYPE = (
    ('', '--------'),
    ('01', "事業部"),
    ('02', "部署"),
    ('03', "課・グループ")
)
CHOICE_WORKFLOW_OPERATION = (
    ('01', "項目値変更"),
    ('02', "レコード追加")
)
CHOICE_BUSINESS_TYPE = (
    ('01', "業務の種類（プログラマー）"),
    ('02', "業務の種類（シニアプログラマー）"),
    ('03', "業務の種類（システムエンジニア）"),
    ('04', "業務の種類（シニアシステムエンジニア）"),
    ('05', "業務の種類（課長）"),
    ('06', "業務の種類（部長）"),
    ('07', "業務の種類（営業担当）"),
    ('08', "業務の種類（マネージャー）"),
    ('09', "業務の種類（新規事業推進部担当）"),
    ('10', "業務の種類（一般社員）"),
    ('11', "業務の種類（担当課長）"),
    ('12', "業務の種類（担当部長）"),
    ('13', "業務の種類（シニアコンサルタント兼中国現地担当）"),
    ('14', "業務の種類（営業アシスタント事務）"),
    ('15', "業務の種類（経営管理業務及び管理）"),
    ('17', "業務の種類（システムエンジニア業務および課内の管理）"),
    ('18', "業務の種類（システムエンジニア業務および課内の管理補佐）"),
    ('16', "その他")
)
CHOICE_CONTRACT_STATUS = (
    ('01', "登録済み"),
    ('02', "承認待ち"),
    ('03', "承認済み"),
    ('04', "廃棄"),
    ('05', "自動更新")
)
CHOICE_RECIPIENT_TYPE = (
    ('01', "宛先"),
    ('02', "ＣＣ"),
    ('03', "ＢＣＣ")
)
CHOICE_MEMBER_RANK = (
    ('01', "グループ長"),
    ('02', "副グループ長"),
    ('11', "PM"),
    ('21', "PL1"),
    ('22', "PL2"),
    ('31', "SE1"),
    ('32', "SE2"),
    ('33', "SE3"),
    ('41', "PG1"),
    ('42', "PG2"),
    ('43', "PG3"),
)
CHOICE_RESIDENCE_TYPE = (
    ('01', "特定活動"),
    ('02', "企業内転勤"),
    ('03', "技術・人文知識・国際業務"),
    ('04', "高度専門職1号"),
    ('09', "高度専門職2号"),
    ('05', "永住者"),
    ('06', "永住者の配偶者"),
    ('07', "日本人の配偶者"),
    ('08', "日本籍"),
)
CHOICE_CALCULATE_TYPE = (
    ('01', '固定１６０時間'),
    ('02', '営業日数 × ８'),
    ('03', '営業日数 × ７.９'),
    ('04', '営業日数 × ７.７５'),
    ('99', "その他（任意）"),
)
CHOICE_ENDOWMENT_INSURANCE = (
    ('1', "加入する"),
    ('0', "加入しない")
)
CHOICE_MAIL_GROUP = (
    ('0400', '注文書と注文請書の送付'),
)
CHOICE_INSURANCE = (
    ('1', "加入する"),
    ('0', "加入しない")
)
CHOICE_CONTRACT_COMMENT = (
    ('0001', '雇用期間'),
    ('0002', '職位'),
    ('0003', '就業の場所'),
    ('0004', '業務の種類'),
    ('0005', '業務の種類その他'),
    ('0006', '業務のコメント'),
    ('0007', '就業時間'),
    ('0200', '給与締め切り日及び支払日'),
    ('0201', '昇給及び降給'),
    ('0202', '賞与'),
    ('0300', '休日'),
    ('0301', '有給休暇'),
    ('0302', '無給休暇'),
    ('0800', '退職に関する項目'),
    ('9999', 'その他備考'),
)
CHOICE_CONTRACT_ALLOWANCE = (
    ('0001', '基本給（税抜）'),
    ('0002', '基本給（税金）'),
    ('0003', '基本給その他'),
    ('1000', '現場手当'),
    ('1001', '役職手当'),
    ('1002', '職務手当'),
    ('1003', '精勤手当'),
    ('1004', '安全手当'),
    ('1005', '資格手当'),
    ('1006', '通勤手当'),
    ('1007', '残業手当'),
    ('1008', '欠勤控除'),
    ('9999', 'その他手当'),
)
CHOICE_ALLOWANCE_UNIT = (
    ('01', '円/月'),
    ('02', '円/年'),
    ('03', '円/時間'),
)

xlPart = 2
xlByRows = 1
xlFormulas = -4123
xlNext = 1
xlDown = -4121

DATABASE_BPM_EBOA = "bpm_eboa"
DATABASE_EB = "default"

POS_DISPATCH_START_ROW = 2

POS_ATTENDANCE_START_ROW = 5
POS_ATTENDANCE_COL_PROJECT_MEMBER_ID = 2
POS_ATTENDANCE_COL_MEMBER_CODE = 3
POS_ATTENDANCE_COL_MEMBER_NAME = 4
POS_ATTENDANCE_COL_TOTAL_HOURS = 13
POS_ATTENDANCE_COL_TOTAL_DAYS = 14
POS_ATTENDANCE_COL_NIGHT_DAYS = 15
POS_ATTENDANCE_COL_ADVANCES_PAID_CLIENT = 16
POS_ATTENDANCE_COL_ADVANCES_PAID = 17
POS_ATTENDANCE_COL_TRAFFIC_COST = 18  # 通勤交通費
POS_ATTENDANCE_COL_ALLOWANCE = 23  # 手当
POS_ATTENDANCE_COL_EXPENSES = 27  # 経費(原価)
POS_ATTENDANCE_COL_EXPENSES_CONFERENCE = 32  # 会議費
POS_ATTENDANCE_COL_EXPENSES_ENTERTAINMENT = 33  # 交際費
POS_ATTENDANCE_COL_EXPENSES_TRAVEL = 34  # 旅費交通費
POS_ATTENDANCE_COL_EXPENSES_COMMUNICATION = 35  # 通信費
POS_ATTENDANCE_COL_EXPENSES_TAX_DUES = 36  # 租税公課
POS_ATTENDANCE_COL_EXPENSES_EXPENDABLES = 37  # 消耗品

FORMAT_ATTENDANCE_TITLE1 = (
    u"",
    "No",
    "ID",
    "基本データ",
    u"",
    u"",
    u"",
    u"",
    u"",
    "案件情報",
    u"",
    u"",
    u"",
    "勤務情報",
    u"",
    u"",
    u"",
    u"",
    u"",
    "売上",
    u"",
    u"",
    "原価",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    "粗利",
    "経費",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    "営業利益",
)
FORMAT_ATTENDANCE_TITLE2 = (
    u"",
    u"",
    u"",
    "社員番号",
    "氏名",
    "所在部署",
    "所属",
    "社会保険\n加入有無",
    "契約形態",
    "案件名",
    "最寄駅",
    "顧客",
    "契約種類",
    "勤務時間",
    "勤務日数",
    "深夜日数",
    "客先立替金",
    "立替金",
    "通勤交通費",
    "税込",
    "税別",
    "経費",
    "月給",
    "手当",
    "深夜手当",
    "残業／控除",
    "交通費",
    "経費",
    "雇用／労災",
    "健康／厚生",
    "原価合計",
    u"",
    "会議費",
    "交際費",
    "旅費交通費",
    "通信費",
    "租税公課",
    "消耗品費",
    "経費合計",
    u"",
)
DICT_ORG_MAPPING = {
    '14': 3,
    '17': 16,
    '4': 4,
    '5': 1,
    '6': 7,
    '7': 10,
    '13': 5,
    '15': 8,
    '2': 2,
    '16': 11,
    '1': 28,
    '11': 14,
    '9': 15,
    '3': 6,
    '18': 29,
    '19': 4,
    '20': 1,
    '21': 7,
    '22': 30
}
