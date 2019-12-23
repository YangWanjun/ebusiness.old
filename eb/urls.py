# coding: UTF-8
"""
Created on 2015/08/20

@author: Yang Wanjun
"""

from django.conf.urls import url, include

from rest_framework import routers

from . import views, views_api
# from eboa import views as eboa_views

router = routers.DefaultRouter()
router.register(r'subcontractor-order-recipient', views_api.SubcontractorOrderRecipientViewSet)
router.register(r'mail-group', views_api.MailGroupViewSet)
router.register(r'subcontractor', views_api.SubcontractorViewSet)
router.register(r'client-request', views_api.ClientRequestViewSet)
router.register(r'subcontractor-request', views_api.SubcontractorRequestViewSet)
router.register(r'organization', views_api.OrganizationViewSet)


member_patterns = [
    url(r'^list.html$', views.MemberListView.as_view(), name='employee_list'),
    url(r'^list_by_monthly\.html$', views.MemberListMonthlyView.as_view(), name='member_list_monthly'),
    url(r'^detail/(?P<employee_id>[^,/]+).html$', views.MemberDetailView.as_view(), name='member_detail'),
    url(r'^(?P<employee_id>[^,/]+)/recommended_project.html$', views.RecommendedProjectsView.as_view(),
        name='recommended_project'),
    url(r'^list/in_coming.html$', views.MembersComingView.as_view(), name='members_in_coming'),
    url(r'^list/subcontractor.html$', views.MembersSubcontractorView.as_view(), name='members_subcontractor'),
    url(r'^change_list.html$', views.MemberChangeListView.as_view(), name='change_list'),
    url(r'^project_list/(?P<employee_id>[^,/]+).html$', views.MemberProjectsView.as_view(),
        name='member_project_list'),
    url(r'^cost_list\.html$', views.MemberCostListView.as_view(), name='member_cost_list'),
    url(r'^dispatch_members\.html', views.DispatchMembersView.as_view(), name='dispatch_members'),
]

section_patterns = [
    url(r'^sections.html$', views.SectionListView.as_view(), name='section_list'),
    url(r'^(?P<section_id>[0-9]+).html$', views.SectionDetailView.as_view(), name='section_detail'),
    url(r'^section_all\.html$', views.SectionAllDetailView.as_view(), name='section_all_detail'),
    url(r'^(?P<section_id>[0-9]+)/attendance/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.OrganizationTurnoverView.as_view(), {'is_all': False},
        name='organization_turnover'),
    url(r'^section_all/attendance/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.OrganizationTurnoverView.as_view(), {'is_all': True},
        name='organization_all_turnover'),
]

generate_patterns = [
    url(r'^subcontractor_request/(?P<subcontractor_id>[0-9]+)/'
        r'(?P<org_id>[0-9]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.GenerateSubcontractorRequestView.as_view(), name='generate_subcontractor_request'),
]

download_patterns = [
    url(r'^project_request/(?P<project_id>[0-9]+).html$', views.DownloadProjectRequestView.as_view(),
        name='download_project_request'),
    url(r'^subcontractor_order/(?P<subcontractor_id>[0-9]+).html$', views.DownloadSubcontractorOrderView.as_view(),
        name='download_subcontractor_order'),
    url(r'^bp_lump_order/(?P<contract_id>[0-9]+)\.html$',
        views.DownloadBpLumpOrder.as_view(), {'is_request': False}, name='download_bp_lump_order'),
    url(r'^bp_lump_order_request/(?P<contract_id>[0-9]+)\.html$',
        views.DownloadBpLumpOrder.as_view(), {'is_request': True}, name='download_bp_lump_order_request'),
    url(r'^bp_order/(?P<project_member_id>[0-9]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.DownloadBpMemberOrder.as_view(), {'is_request': False}, name='download_bp_order'),
    url(r'^bp_order_request/(?P<project_member_id>[0-9]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.DownloadBpMemberOrder.as_view(), {'is_request': True}, name='download_bp_order_request'),
    url(r'^project_client_order/$', views.DownloadClientOrderView.as_view(), name='download_client_order'),
    url(r'^project_quotation/(?P<project_id>[0-9]+).html$', views.DownloadProjectQuotationView.as_view(),
        name='download_project_quotation'),
    url(r'^resume/(?P<member_id>[0-9]+).html$', views.DownloadResumeView.as_view(), name='download_resume'),
    url(r'^section/(?P<section_id>[0-9]+)/attendance/(?P<year>[0-9]{4})/(?P<month>[0-9]{2}).html$',
        views.DownloadOrganizationTurnover.as_view(), {'is_all': False},
        name='download_organization_turnover'),
    url(r'^section_all/attendance/(?P<year>[0-9]{4})/(?P<month>[0-9]{2}).html$',
        views.DownloadOrganizationTurnover.as_view(), {'is_all': True},
        name='download_organization_all_turnover'),
    # url(r'^member/list/eboa_info.html$', eboa_views.download_eboa_members, name='download_eboa_members'),
    url(r'^member/cost_list.html$', views.DownloadMembersCostView.as_view(), name='download_members_cost'),
    url(r'^subcontractor_request/(?P<subcontractor_request_id>[0-9]+).html$',
        views.DownloadSubcontractorRequestView.as_view(), name='download_subcontractor_request'),
    url(r'^subcontractor_pay_notify/(?P<subcontractor_request_id>[0-9]+).html$',
        views.DownloadSubcontractorPayNotifyView.as_view(), name='download_subcontractor_pay_notify'),
    url(r'^dispatch_members/(?P<year>[0-9]{4})/(?P<month>[0-9]{2}).html$', views.DownloadDispatchMembers.as_view(),
        name='download_dispatch_members')
]

upload_patterns = [
]

image_patterns = [
    url(r'^turnover_chart/client/(?P<client_id>[0-9]+)\.html$', views.ImageClientTurnoverChartView.as_view(),
        name='image_client_turnover_chart'),
    url(r'^turnover_chart/clients/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.ImageClientsTurnoverMonthlyView.as_view(), name='image_clients_turnover_monthly'),
    url(r'^clients/(?P<year>[0-9]{4}).html$', views.ImageTurnoverClientsYearlyView.as_view(),
        name='image_turnover_clients_yearly_area_plot'),
    url(r'^member_status_bar.html$', views.ImageMemberStatusBar.as_view(), name='member_status_bar'),
    url(r'^business_type/(?P<year>[0-9]{4})\.html$', views.ImageBusinessTypeByYearView.as_view(),
        name='image_business_type_by_year')
]

turnover_patterns = [
    url(r'^company_yearly.html$', views.TurnoverCompanyYearlyView.as_view(), name="turnover_company_yearly"),
    url(r'^company_monthly.html$', views.TurnoverCompanyMonthlyView.as_view(), name="turnover_company_monthly"),
    url(r'^charts/(?P<ym>[0-9]{6}).html$', views.TurnoverChartsMonthlyView.as_view(),
        name='turnover_charts_monthly'),
    url(r'^members/(?P<ym>[0-9]{6}).html$', views.TurnoverMembersMonthlyView.as_view(),
        name='turnover_members_monthly'),
    url(r'^clients/(?P<year>[0-9]{4}).html$', views.TurnoverClientsYearlyView.as_view(),
        name='turnover_clients_yearly'),
    url(r'^clients/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$', views.TurnoverClientsMonthlyView.as_view(),
        name='turnover_clients_monthly'),
    url(r'^client/(?P<client_id>[0-9]+)/(?P<ym>[0-9]{6}).html$', views.TurnoverClientMonthlyView.as_view(),
        name='turnover_client_monthly'),
    url(r'^client/(?P<client_id>[0-9]+)/history.html$', views.TurnoverClientYearlyView.as_view(),
        name='turnover_client_yearly'),
    url(r'^business_type/(?P<year>[0-9]{4})\.html$', views.TurnoverBusinessTypeByYearView.as_view(),
        name='turnover_business_type_by_year'),
    url(r'^division/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$', views.TurnoverDivisionsByMonth.as_view(),
        name='turnover_divisions_by_month'),
    url(r'^division/(?P<pk>\d+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.TurnoverDivisionByMonth.as_view(),
        name='turnover_division_by_month'),
]

subcontractor_patterns = [
    url(r'^list.html$', views.SubcontractorListView.as_view(), name='subcontractor_list'),
    url(r'^detail/(?P<subcontractor_id>[0-9]+).html$', views.SubcontractorDetailView.as_view(),
        name='subcontractor_detail'),
    url(r'^members/(?P<subcontractor_id>[0-9]+).html$', views.SubcontractorMembersView.as_view(),
        name='subcontractor_members'),
    url(r'^bp_contracts.html$', views.BpContractsView.as_view(), name='business_partner_members'),
    url(r'^(?P<member_id>[0-9]+)/order_info\.html$', views.BpMemberOrdersView.as_view(), name='bp_member_orders'),
    url(r'^(?P<contract_id>[0-9]+)/lump_order_info\.html$', views.BpLumpContractOrdersView.as_view(),
        name='bp_lump_contract_orders'),
    url(r'^(?P<contract_id>[0-9]+)/lump_order\.html$',
        views.BpLumpOrderDetailView.as_view(), {'preview': True}, name='bp_lump_order_preview'),
    url(r'^lump_order/(?P<order_id>[0-9]+)\.html$',
        views.BpLumpOrderDetailView.as_view(), {'preview': False}, name='bp_lump_order'),
    url(r'^(?P<project_member_id>[0-9]+)/order/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.BpMemberOrderDetailView.as_view(), {'preview': True}, name='bp_member_order_preview'),
    url(r'^order/(?P<order_id>[0-9]+)\.html$', views.BpMemberOrderDetailView.as_view(), name='bp_member_order'),
    url(r'^cost_monthly.html$', views.CostSubcontractorsMonthlyView.as_view(), name='cost_subcontractors_monthly'),
    url(r'^cost_business_owner.html$', views.CostBusinessOwnerView.as_view(), name='cost_business_owner'),
    url(r'^members_cost/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.CostSubcontractorMembersByMonthView.as_view(),
        name='cost_all_subcontractor_members_by_month'),
    url(r'^cost/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$', views.CostSubcontractorsByMonthView.as_view(),
        name='cost_subcontractors_by_month'),
    url(r'^cost/(?P<year>[0-9]{4})\.html$', views.ConstSubcontractorInYearView.as_view(),
        name='cost_subcontractors_in_year'),
    url(r'^cost_2/(?P<year>[0-9]{4})\.html$', views.ConstSubcontractorInYear2View.as_view(),
        name='cost_subcontractors_in_year2'),
    url(r'^cost/download/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.DownloadCostSubcontractorsByMonthView.as_view(),
        name='download_cost_subcontractors_by_month'),
    url(r'^(?P<subcontractor_id>[0-9]+)/members_cost/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})\.html$',
        views.CostSubcontractorMembersByMonthView.as_view(),
        name='cost_subcontractor_members_by_month'),
    url(r'^subcontractor_request_view/(?P<request_id>[0-9]+).html$', views.SubcontractorRequestView.as_view(),
        name='view_subcontractor_request'),
    url(r'^subcontractor_pay_notify_view/(?P<request_id>[0-9]+).html$',
        views.SubcontractorPayNotifyView.as_view(),
        name='view_subcontractor_pay_notify'),
    url(r'^subcontractor_request_mail/(?P<subcontractor_id>[0-9]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2}).html$',
        views.SendMailBpRequestView.as_view(), name='send_mail_bp_request'),
    url(r'^subcontractor_member_mail/(?P<member_id>[0-9]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2}).html$',
        views.SendMailBpMemberView.as_view(), name='send_mail_bp_member'),
]

project_patterns = [
    url(r'^list.html$', views.ProjectListView.as_view(), name='project_list'),
    url(r'^order_list.html', views.ProjectOrdersView.as_view(), name='project_order_list'),
    url(r'^(?P<project_id>[0-9]+).html$', views.ProjectDetailView.as_view(), name='project_detail'),
    url(r'^members/(?P<project_id>[0-9]+).html$', views.ProjectMembersView.as_view(), name='project_members'),
    url(r'^end/(?P<project_id>[0-9]+).html$', views.ProjectEndView.as_view(), name='project_end'),
    url(r'^attendance/(?P<project_id>[0-9]+).html$', views.ProjectAttendanceView.as_view(),
        name='project_attendance_list'),
    url(r'^request_view/(?P<request_id>[0-9]+).html$', views.ProjectRequestView.as_view(),
        name='view_project_request'),
    url(r'^(?P<project_id>[0-9]+)/recommended_member.html$', views.RecommendedMembersView.as_view(),
        name='recommended_member'),
    url(r'^order_member_assign/(?P<project_id>[0-9]+).html$', views.ProjectOrderMemberAssignView.as_view(),
        name='project_order_member_assign'),
    url(r'^members_by_order/(?P<order_id>[0-9]+).html$', views.ProjectMembersByOrderView.as_view(),
        name='project_members_by_order'),
]

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^member/', include(member_patterns)),
    url(r'^section/', include(section_patterns)),
    url(r'^project/', include(project_patterns)),
    url(r'^release_list/(?P<ym>[0-9]{6}).html$', views.ReleaseListView.as_view(), name='release_list'),
    url(r'^subcontractor/', include(subcontractor_patterns)),
    url(r'^turnover/', include(turnover_patterns)),
    url(r'^generate/', include(generate_patterns)),
    url(r'^download/', include(download_patterns)),
    url(r'^image/', include(image_patterns)),
    url(r'^issues.html$', views.IssueListView.as_view(), name='issues'),
    url(r'^issue/(?P<issue_id>[0-9]+).html$', views.IssueDetailView.as_view(), name='issue_detail'),
    url(r'^history.html$', views.HistoryView.as_view(), name='history'),
    url(r"^batch_list.html", views.BatchListView.as_view(), name="batch_list"),
    url(r"^batch/(?P<name>[A-Za-z0-9_-]+).log$", views.BatchLogView.as_view(), name="batch_log"),
    url(r"^upload_file.html$", views.upload_resume, name="upload_file"),
    url(r'^login/$', views.login_user, {'qr': False}, name='login'),
    url(r'^login_qr/$', views.login_user, {'qr': True}, name='login_qr'),
    url(r'^logout/$', views.logout_view, name='logout_view'),
    url(r'^accounts/password/change/$', views.password_change, name='password_change'),
    url(r'^business_days\.html$', views.BusinessDaysView.as_view(), name='get_business_days'),
]
