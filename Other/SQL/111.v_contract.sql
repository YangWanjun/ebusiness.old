CREATE OR REPLACE VIEW v_contract AS
    SELECT 
        c.id AS id,
        c.contract_no AS contract_no,
        c.contract_date AS contract_date,
        c.member_type AS member_type,
        null as contract_type,
        c.employment_date AS employment_date,
        c.start_date AS start_date,
        CASE
            WHEN (c.end_date2 IS NOT NULL) THEN c.end_date2
            ELSE c.end_date
        END AS end_date,
        c.employment_period_comment AS employment_period_comment,
        c.position AS position,
        c.business_address AS business_address,
        c.business_type AS business_type,
        c.business_type_other AS business_type_other,
        c.business_other AS business_other,
        c.business_time AS business_time,
        c.is_hourly_pay AS is_hourly_pay,
        0 AS is_fixed_cost,
        0 AS is_show_formula,
        c.allowance_base AS allowance_base,
        c.allowance_base_memo AS allowance_base_memo,
        c.allowance_base_tax as allowance_base_tax,
        c.allowance_base_other AS allowance_base_other,
        c.allowance_base_other_memo AS allowance_base_other_memo,
        c.allowance_work AS allowance_work,
        c.allowance_work_memo AS allowance_work_memo,
        c.allowance_director AS allowance_director,
        c.allowance_director_memo AS allowance_director_memo,
        c.allowance_position AS allowance_position,
        c.allowance_position_memo AS allowance_position_memo,
        c.allowance_diligence AS allowance_diligence,
        c.allowance_diligence_memo AS allowance_diligence_memo,
        c.allowance_region,
        c.allowance_region_memo,
        c.allowance_security AS allowance_security,
        c.allowance_security_memo AS allowance_security_memo,
        c.allowance_qualification AS allowance_qualification,
        c.allowance_qualification_memo AS allowance_qualification_memo,
        c.allowance_traffic AS allowance_traffic,
        c.allowance_traffic_memo AS allowance_traffic_memo,
        c.allowance_time_min AS allowance_time_min,
        c.allowance_time_max AS allowance_time_max,
        '' AS allowance_time_memo,
        '99' AS calculate_type,
        0 AS calculate_time_min,
        0 AS calculate_time_max,
        c.allowance_overtime AS allowance_overtime,
        c.allowance_overtime_memo AS allowance_overtime_memo,
        c.allowance_absenteeism AS allowance_absenteeism,
        c.allowance_absenteeism_memo AS allowance_absenteeism_memo,
        c.allowance_other AS allowance_other,
        c.allowance_other_memo AS allowance_other_memo,
        c.endowment_insurance AS endowment_insurance,
        c.allowance_ticket_comment AS allowance_ticket_comment,
        c.allowance_date_comment AS allowance_date_comment,
        c.allowance_change_comment AS allowance_change_comment,
        c.bonus_comment AS bonus_comment,
        c.holiday_comment AS holiday_comment,
        c.paid_vacation_comment AS paid_vacation_comment,
        c.non_paid_vacation_comment AS non_paid_vacation_comment,
        c.retire_comment AS retire_comment,
        c.status AS status,
        c.comment AS comment,
        c.member_id AS member_id,
        7 AS content_type_id,
        c.company_id AS company_id,
        c.is_loan AS is_loan,
        c.move_flg AS move_flg,
        CASE
            WHEN
                (SELECT MAX(c1.contract_no)
                   FROM eb_contract c1
                  WHERE c1.start_date = c.start_date
                    AND c1.member_id = c.member_id
                    AND c1.is_deleted = 0
                    AND c1.status <> '04') = c.contract_no
            THEN
                0
            ELSE 1
        END AS is_old,                                   /* 上書きされた契約、同じ契約期間で新しい契約が作成された場合 */
        c.join_date AS join_date,
        c.retired_date AS retired_date,
        CASE c.member_type
            WHEN 1 THEN truncate((c.allowance_base + 
                              c.allowance_base_other + 
                              c.allowance_work + 
                              c.allowance_director + 
                              c.allowance_position + 
                              c.allowance_diligence +
                              c.allowance_security +
                              c.allowance_qualification +
                              c.allowance_other) * 14 / 12, 0)
            ELSE truncate((c.allowance_base + 
                       c.allowance_base_other + 
                       c.allowance_work + 
                       c.allowance_director + 
                       c.allowance_position + 
                       c.allowance_diligence +
                       c.allowance_security +
                       c.allowance_qualification +
                       c.allowance_other), 0)
        END AS cost, 
        c.created_date AS created_date,
        c.updated_date AS updated_date,
        c.is_deleted AS is_deleted,
        c.deleted_date AS deleted_date
    FROM
        eb_contract c
    WHERE c.status <> '04'
      AND c.is_deleted = 0
    UNION ALL SELECT
        c.id AS id,
        NULL AS contract_no,
        NULL AS contract_date,
        4 AS member_type,
        c.contract_type,
        NULL AS employment_date,
        c.start_date AS start_date,
        c.end_date AS end_date,
        '' AS employment_period_comment,
        '' AS position,
        '' AS business_address,
        '' AS business_type,
        '' AS business_type_other,
        '' AS business_other,
        '' AS business_time,
        c.is_hourly_pay AS is_hourly_pay,
        c.is_fixed_cost AS is_fixed_cost,
        c.is_show_formula AS is_show_formula,
        c.allowance_base AS allowance_base,
        c.allowance_base_memo AS allowance_base_memo,
        0 as allowance_base_tax,
        0 AS allowance_base_other,
        '' AS allowance_base_other_memo,
        0 AS allowance_work,
        '' AS allowance_work_memo,
        0 AS allowance_director,
        '' AS allowance_director_memo,
        0 AS allowance_position,
        '' AS allowance_position_memo,
        0 AS allowance_diligence,
        '' AS allowance_diligence_memo,
        0 as allowance_region,
        '' as allowance_region_memo,
        0 AS allowance_security,
        '' AS allowance_security_memo,
        0 AS allowance_qualification,
        '' AS allowance_qualification_memo,
        0 AS allowance_traffic,
        '' AS allowance_traffic_memo,
        c.allowance_time_min AS allowance_time_min,
        c.allowance_time_max AS allowance_time_max,
        c.allowance_time_memo AS allowance_time_memo,
        c.calculate_type AS calculate_type,
        c.calculate_time_min AS calculate_time_min,
        c.calculate_time_max AS calculate_time_max,
        c.allowance_overtime AS allowance_overtime,
        c.allowance_overtime_memo AS allowance_overtime_memo,
        c.allowance_absenteeism AS allowance_absenteeism,
        c.allowance_absenteeism_memo AS allowance_absenteeism_memo,
        c.allowance_other AS allowance_other,
        c.allowance_other_memo AS allowance_other_memo,
        '0' AS endowment_insurance,
        '' AS allowance_ticket_comment,
        '' AS allowance_date_comment,
        '' AS allowance_change_comment,
        '' AS bonus_comment,
        '' AS holiday_comment,
        '' AS paid_vacation_comment,
        '' AS non_paid_vacation_comment,
        '' AS retire_comment,
        c.status,
        c.comment AS comment,
        c.member_id AS member_id,
        8 AS content_type_id,
        c.company_id AS company_id,
        0 AS is_loan,
        0 AS move_flg,
        0 AS is_old,
        NULL AS join_date,
        NULL AS retired_date,
        IF(c.is_hourly_pay or c.is_fixed_cost, c.allowance_base, c.allowance_base + c.allowance_other) AS cost,
        c.created_date AS created_date,
        c.updated_date AS updated_date,
        c.is_deleted AS is_deleted,
        c.deleted_date AS deleted_date
    FROM
        eb_bp_contract c
    WHERE c.status <> '04'
      AND c.is_deleted = 0
