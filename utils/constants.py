# coding: UTF-8
"""
Created on 2015/09/28

@author: Yang Wanjun
"""
from decimal import Decimal

EXCEL_APPLICATION = "Excel.Application"
EXCEL_FORMAT_EXCEL2003 = 56

LOG_EB_SALES = 'eb_sales'

LOGIN_IN_URL = '/eb/login/'

REG_DATE_STR = ur"\d{4}([-/.年])\d{1,2}([-/.月])\d{1,2}([日]?)"
REG_DATE_STR2 = ur"\d{4}([-/.年])\d{1,2}([-/.月]?)"
REG_EXCEL_REPLACEMENT = ur"\{\$([A-Z0-9_]+)\$\}"

MIME_TYPE_EXCEL = 'application/excel'
MIME_TYPE_HTML = 'text/html'

NAME_SYSTEM = u"営業支援システム"
NAME_BUSINESS_PLAN = u"%02d月営業企画"
NAME_MEMBER_LIST = u"最新要員一覧"
NAME_RESUME = u"EB履歴書_%s_%s"
NAME_SECTION_ATTENDANCE = u"勤怠情報_%s_%04d年%02d月"
NAME_MEMBERS_COST = u"要員コスト一覧_%s"

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

MARK_POST_CODE = u"〒"

DOWNLOAD_REQUEST = "request"
DOWNLOAD_BUSINESS_PLAN = "business_plan"
DOWNLOAD_MEMBER_LIST = "member_list"
DOWNLOAD_RESUME = "resume"
DOWNLOAD_QUOTATION = "quotation"
DOWNLOAD_ORDER = "order"

ERROR_TEMPLATE_NOT_EXISTS = u"テンプレートファイルが存在しません。"
ERROR_REQUEST_FILE_NOT_EXISTS = u"作成された請求書は存在しません、" \
                                u"サーバーに該当する請求書が存在するのかを確認してください。"
ERROR_BP_ORDER_FILE_NOT_EXISTS = u"作成された注文書は存在しません、" \
                                 u"サーバーに該当する注文書が存在するのかを確認してください。"
ERROR_CANNOT_GENERATE_2MONTH_BEFORE = u"２ヶ月前の請求書は作成できない"
ERROR_INVALID_TOTAL_HOUR = u"勤務時間のデータ不正、空白になっているのか、または０になっているのかご確認ください。"
ERROR_BP_NO_CONTRACT = u"当該協力社員は契約情報が存在しません。"

PROJECT_STAGE = (u"要件定義", u"調査分析",
                 u"基本設計", u"詳細設計",
                 u"開発製造", u"単体試験",
                 u"結合試験", u"総合試験",
                 u"保守運用", u"サポート")

CHOICE_PROJECT_MEMBER_STATUS = (
    (1, u"提案中"),
    (2, u"作業確定")
)
CHOICE_PROJECT_STATUS = (
    (1, u"提案"),
    (2, u"予算審査"),
    (3, u"予算確定"),
    (4, u"実施中"),
    (5, u"完了")
)
CHOICE_PROJECT_BUSINESS_TYPE = (
    ('01', u"金融（銀行）"),
    ('02', u"金融（保険）"),
    ('03', u"金融（証券）"),
    ('04', u"製造"),
    ('05', u"サービス"),
    ('06', u"その他")
)
CHOICE_SKILL_TIME = ((0, u"未経験者可"),
                     (1, u"１年以上"),
                     (2, u"２年以上"),
                     (3, u"３年以上"),
                     (5, u"５年以上"),
                     (10, u"１０年以上"))
CHOICE_DEGREE_TYPE = ((1, u"小・中学校"),
                      (2, u"高等学校"),
                      (3, u"専門学校"),
                      (4, u"高等専門学校"),
                      (5, u"短期大学"),
                      (6, u"大学学部"),
                      (7, u"大学大学院"))
CHOICE_SALESPERSON_TYPE = ((0, u"営業部長"),
                           (1, u"その他"),
                           (5, u"営業担当"),
                           (6, u"取締役"),
                           (7, u"代表取締役社長"))
CHOICE_CLIENT_MEMBER_TYPE = (('01', u"代表取締役社長"),
                             ('02', u"取締役"),
                             ('03', u"営業"),
                             ('99', u"その他"))
CHOICE_MEMBER_TYPE = ((1, u"正社員"),
                      (2, u"契約社員"),
                      (3, u"個人事業者"),
                      (4, u"他社技術者"),
                      (5, u"パート"),
                      (6, u"アルバイト"),
                      (7, u"正社員（試用期間）"))
CHOICE_CLIENT_CONTRACT_TYPE = (
    ('01', u"業務委託"),
    ('02', u"準委任"),
    ('03', u"派遣"),
    ('04', u"一括"),
    ('05', u"ソフト加工"),
    ('10', u"出向"),
    # ('11', u"出向（在籍）"),
    # ('12', u"出向（完全）"),
    ('99', u"その他"),
)
CHOICE_BP_CONTRACT_TYPE = (
    ('01', u"業務委託"),
    ('02', u"準委任"),
    ('03', u"派遣"),
    ('04', u"一括"),
    # ('05', u"ソフト加工"),
    # ('10', u"出向"),
    ('11', u"出向（在籍）"),
    ('12', u"出向（完全）"),
    ('99', u"その他"),
)
CHOICE_PROJECT_ROLE = (
    ("OP", u"OP：ｵﾍﾟﾚｰﾀｰ"),
    ("PG", u"PG：ﾌﾟﾛｸﾞﾗﾏｰ"),
    ("SP", u"SP：ｼｽﾃﾑﾌﾟﾛｸﾞﾗﾏｰ"),
    ("SE", u"SE：ｼｽﾃﾑｴﾝｼﾞﾆｱ"),
    ("SL", u"SL：ｻﾌﾞﾘｰﾀﾞｰ"),
    ("L", u"L：ﾘｰﾀﾞｰ"),
    ("M", u"M：ﾏﾈｰｼﾞｬｰ")
)
CHOICE_POSITION = ((3, u"事業部長"),
                   (4, u"部長"),
                   (5, u"担当部長"),
                   (6, u"課長"),
                   (7, u"担当課長"),
                   (8, u"PM"),
                   (9, u"リーダー"),
                   (10, u"サブリーダー"),
                   (11, u"勤務統計者"))
CHOICE_SEX = (('1', u"男"), ('2', u"女"))
CHOICE_SEX_EBOA = (('1', u"男"), ('0', u"女"))
CHOICE_MARRIED = (('', u"------"), ('0', u"未婚"), ('1', u"既婚"))
CHOICE_PAYMENT_MONTH = (('1', u"翌月"),
                        ('2', u"翌々月"),
                        ('3', u"３月"),
                        ('4', u"４月"),
                        ('5', u"５月"),
                        ('6', u"６月"))
CHOICE_PAYMENT_DAY = (('01', u'1日'),
                      ('02', u'2日'),
                      ('03', u'3日'),
                      ('04', u'4日'),
                      ('05', u'5日'),
                      ('06', u'6日'),
                      ('07', u'7日'),
                      ('08', u'8日'),
                      ('09', u'9日'),
                      ('10', u'10日'),
                      ('11', u'11日'),
                      ('12', u'12日'),
                      ('13', u'13日'),
                      ('14', u'14日'),
                      ('15', u'15日'),
                      ('16', u'16日'),
                      ('17', u'17日'),
                      ('18', u'18日'),
                      ('19', u'19日'),
                      ('20', u'20日'),
                      ('21', u'21日'),
                      ('22', u'22日'),
                      ('23', u'23日'),
                      ('24', u'24日'),
                      ('25', u'25日'),
                      ('26', u'26日'),
                      ('27', u'27日'),
                      ('28', u'28日'),
                      ('29', u'29日'),
                      ('30', u'30日'),
                      ('99', u'月末'))
CHOICE_ATTENDANCE_YEAR = (('2014', u"2014年"),
                          ('2015', u"2015年"),
                          ('2016', u"2016年"),
                          ('2017', u"2017年"),
                          ('2018', u"2018年"),
                          ('2019', u"2019年"),
                          ('2020', u"2020年"))
CHOICE_ATTENDANCE_MONTH = (
    ('01', u'1月'),
    ('02', u'2月'),
    ('03', u'3月'),
    ('04', u'4月'),
    ('05', u'5月'),
    ('06', u'6月'),
    ('07', u'7月'),
    ('08', u'8月'),
    ('09', u'9月'),
    ('10', u'10月'),
    ('11', u'11月'),
    ('12', u'12月')
)
CHOICE_ACCOUNT_TYPE = (("1", u"普通預金"),
                       ("2", u"定期預金"),
                       ("3", u"総合口座"),
                       ("4", u"当座預金"),
                       ("5", u"貯蓄預金"),
                       ("6", u"大口定期預金"),
                       ("7", u"積立定期預金"))
CHOICE_ATTENDANCE_TYPE = (('1', u"１５分ごと"),
                          ('2', u"３０分ごと"),
                          ('3', u"１時間ごと"))
CHOICE_TAX_RATE = ((Decimal('0.00'), u"税なし"),
                   (Decimal('0.05'), u"5％"),
                   (Decimal('0.08'), u"8％"))
CHOICE_DECIMAL_TYPE = (('0', u"四捨五入"),
                       ('1', u"切り捨て"))
CHOICE_DEV_LOCATION = (('01', u"東大島"),
                       ('02', u"田町"),
                       ('03', u"府中"),
                       ('04', u"西葛西"),
                       ('05', u"中目黒"))
CHOICE_NOTIFY_TYPE = ((1, u"EBのメールアドレス"),
                      (2, u"個人メールアドレス"),
                      (3, u"EBと個人両方のメールアドレス"))
CHOICE_ISSUE_STATUS = (('1', u"起票"),
                       ('2', u"対応中"),
                       ('3', u"対応完了"),
                       ('4', u"クローズ"),
                       ('5', u"取下げ"))
CHOICE_ISSUE_LEVEL = ((1, u"低"),
                      (2, u"中"),
                      (3, u"高"),
                      (4, u"至急"),
                      (5, u"大至急"))
CHOICE_THEME = (('default', u'デフォルト'),
                ('full_screen', u'フルスクリーン'))
CHOICE_ORG_TYPE = (('', '--------'),
                   ('01', u"事業部"),
                   ('02', u"部署"),
                   ('03', u"課・グループ"))
CHOICE_WORKFLOW_OPERATION = (('01', u"項目値変更"),
                             ('02', u"レコード追加"))
CHOICE_BUSINESS_TYPE = (('01', u"業務の種類（プログラマー）"),
                        ('02', u"業務の種類（シニアプログラマー）"),
                        ('03', u"業務の種類（システムエンジニア）"),
                        ('04', u"業務の種類（シニアシステムエンジニア）"),
                        ('05', u"業務の種類（課長）"),
                        ('06', u"業務の種類（部長）"),
                        ('07', u"業務の種類（営業担当）"),
                        ('08', u"業務の種類（マネージャー）"),
                        ('09', u"業務の種類（新規事業推進部担当）"),
                        ('10', u"業務の種類（一般社員）"),
                        ('11', u"業務の種類（担当課長）"),
                        ('12', u"業務の種類（担当部長）"),
                        ('13', u"業務の種類（シニアコンサルタント兼中国現地担当）"),
                        ('14', u"業務の種類（営業アシスタント事務）"),
                        ('15', u"業務の種類（経営管理業務及び管理）"),
                        ('17', u"業務の種類（システムエンジニア業務および課内の管理）"),
                        ('18', u"業務の種類（システムエンジニア業務および課内の管理補佐）"),
                        ('16', u"その他"))
CHOICE_CONTRACT_STATUS = (('01', u"登録済み"),
                          ('02', u"承認待ち"),
                          ('03', u"承認済み"),
                          ('04', u"廃棄"),
                          ('05', u"自動更新"))
CHOICE_RECIPIENT_TYPE = (('01', u"宛先"),
                         ('02', u"ＣＣ"),
                         ('03', u"ＢＣＣ"))
CHOICE_MEMBER_RANK = (('01', u"グループ長"),
                      ('02', u"副グループ長"),
                      ('11', u"PM"),
                      ('21', u"PL1"),
                      ('22', u"PL2"),
                      ('31', u"SE1"),
                      ('32', u"SE2"),
                      ('33', u"SE3"),
                      ('41', u"PG1"),
                      ('42', u"PG2"),
                      ('43', u"PG3"),
                      )
CHOICE_CALCULATE_TYPE = (('01', u'固定１６０時間'),
                         ('02', u'営業日数 × ８'),
                         ('03', u'営業日数 × ７.９'),
                         ('99', u"その他（任意）"),
                         )
CHOICE_ENDOWMENT_INSURANCE = (('1', u"加入する"),
                              ('0', u"加入しない"))

xlPart = 2
xlByRows = 1
xlFormulas = -4123
xlNext = 1
xlDown = -4121

DATABASE_BPM_EBOA = "bpm_eboa"
DATABASE_EB = "default"

POS_ATTENDANCE_START_ROW = 5
POS_ATTENDANCE_COL_PROJECT_MEMBER_ID = 2
POS_ATTENDANCE_COL_MEMBER_CODE = 3
POS_ATTENDANCE_COL_MEMBER_NAME = 4
POS_ATTENDANCE_COL_TOTAL_HOURS = 12
POS_ATTENDANCE_COL_TOTAL_DAYS = 13
POS_ATTENDANCE_COL_NIGHT_DAYS = 14
POS_ATTENDANCE_COL_ADVANCES_PAID_CLIENT = 15
POS_ATTENDANCE_COL_ADVANCES_PAID = 16
POS_ATTENDANCE_COL_TRAFFIC_COST = 17                # 通勤交通費
POS_ATTENDANCE_COL_ALLOWANCE = 22                   # 手当
POS_ATTENDANCE_COL_EXPENSES = 26                    # 経費(原価)
POS_ATTENDANCE_COL_EXPENSES_CONFERENCE = 31         # 会議費
POS_ATTENDANCE_COL_EXPENSES_ENTERTAINMENT = 32      # 交際費
POS_ATTENDANCE_COL_EXPENSES_TRAVEL = 33             # 旅費交通費
POS_ATTENDANCE_COL_EXPENSES_COMMUNICATION = 34      # 通信費
POS_ATTENDANCE_COL_EXPENSES_TAX_DUES = 35           # 租税公課
POS_ATTENDANCE_COL_EXPENSES_EXPENDABLES = 36        # 消耗品

FORMAT_ATTENDANCE_TITLE1 = (
    u"",
    u"No",
    u"ID",
    u"基本データ",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"案件情報",
    u"",
    u"",
    u"勤務情報",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"売上",
    u"",
    u"",
    u"原価",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"粗利",
    u"経費",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"",
    u"営業利益",
)
FORMAT_ATTENDANCE_TITLE2 = (
    u"",
    u"",
    u"",
    u"社員番号",
    u"氏名",
    u"所在部署",
    u"所属",
    u"社会保険\n加入有無",
    u"契約形態",
    u"案件名",
    u"顧客",
    u"契約種類",
    u"勤務時間",
    u"勤務日数",
    u"深夜日数",
    u"客先立替金",
    u"立替金",
    u"通勤交通費",
    u"税込",
    u"税別",
    u"経費",
    u"月給",
    u"手当",
    u"深夜手当",
    u"残業／控除",
    u"交通費",
    u"経費",
    u"雇用／労災",
    u"健康／厚生",
    u"原価合計",
    u"",
    u"会議費",
    u"交際費",
    u"旅費交通費",
    u"通信費",
    u"租税公課",
    u"消耗品費",
    u"経費合計",
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
