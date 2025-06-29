-- ==================================================
-- SQL for 工商信息 (API ID: 1001)
-- ==================================================
CREATE TABLE IF NOT EXISTS `base_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `id` BIGINT COMMENT '公司id'
  `base` VARCHAR(255) COMMENT '省份简称'
  `name` VARCHAR(255) COMMENT '企业名'
  `legal_person_name` VARCHAR(255) COMMENT '法人'
  `legal_person_type` BIGINT COMMENT '法人类型 ，1 人 2 公司'
  `reg_number` VARCHAR(255) COMMENT '注册号'
  `industry` VARCHAR(255) COMMENT '行业'
  `company_org_type` VARCHAR(255) COMMENT '企业类型'
  `reg_location` VARCHAR(255) COMMENT '注册地址'
  `estiblish_time` VARCHAR(255) COMMENT '成立时间'
  `from_time` VARCHAR(255) COMMENT '经营开始时间'
  `to_time` VARCHAR(255) COMMENT '经营结束时间'
  `business_scope` VARCHAR(255) COMMENT '经营范围'
  `approved_time` VARCHAR(255) COMMENT '核准时间'
  `reg_status` VARCHAR(255) COMMENT '企业状态'
  `reg_capital` VARCHAR(255) COMMENT '注册资本'
  `reg_institute` VARCHAR(255) COMMENT '登记机关'
  `org_number` VARCHAR(255) COMMENT '组织机构代码'
  `credit_code` VARCHAR(255) COMMENT '统一社会信用代码'
  `property3` VARCHAR(255) COMMENT '英文名'
  `updatetime` VARCHAR(255) COMMENT '更新时间'
  `company_id` BIGINT COMMENT '表对应id'
  `tax_number` VARCHAR(255) COMMENT '纳税人识别号'
  `email` VARCHAR(255) COMMENT '邮箱'
  `website` VARCHAR(255) COMMENT '网址'
  `phone_number` VARCHAR(255) COMMENT '电话号'
  `revoke_date` VARCHAR(255) COMMENT '吊销日期'
  `revoke_reason` VARCHAR(255) COMMENT '吊销原因'
  `cancel_date` VARCHAR(255) COMMENT '注销日期'
  `cancel_reason` VARCHAR(255) COMMENT '注销原因'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息';

CREATE TABLE IF NOT EXISTS `base_info_staff_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - staffList';

CREATE TABLE IF NOT EXISTS `base_info_staff_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_staff_list_id` BIGINT COMMENT '外键, 关联 `base_info_staff_list`.id',
  `id` BIGINT COMMENT 'id'
  `name` VARCHAR(255) COMMENT '主要人员名称'
  `logo` VARCHAR(255) COMMENT 'logo'
  `type` BIGINT COMMENT '主要人员类型 1-公司 2-人'
  `staff_type_name` VARCHAR(255) COMMENT '主要人员职位'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - staffList/_child';

CREATE TABLE IF NOT EXISTS `base_info_staff_list_child_type_join` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_staff_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_staff_list_child`.id',
  `_child` VARCHAR(255) COMMENT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - staffList/_child/typeJoin';

CREATE TABLE IF NOT EXISTS `base_info_abnormal_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - abnormalList';

CREATE TABLE IF NOT EXISTS `base_info_abnormal_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_abnormal_list_id` BIGINT COMMENT '外键, 关联 `base_info_abnormal_list`.id',
  `id` BIGINT COMMENT '表id'
  `put_reason` VARCHAR(255) COMMENT '列入原因'
  `put_date` VARCHAR(255) COMMENT '列入时间'
  `put_department` VARCHAR(255) COMMENT '决定列入机关'
  `remove_reason` VARCHAR(255) COMMENT '移出原因'
  `remove_date` VARCHAR(255) COMMENT '移出时间'
  `remove_department` VARCHAR(255) COMMENT '移出机关'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - abnormalList/_child';

CREATE TABLE IF NOT EXISTS `base_info_illegal_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - illegalList';

CREATE TABLE IF NOT EXISTS `base_info_illegal_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_illegal_list_id` BIGINT COMMENT '外键, 关联 `base_info_illegal_list`.id',
  `id` BIGINT COMMENT '表id'
  `put_reason` VARCHAR(255) COMMENT '列入原因'
  `put_date` VARCHAR(255) COMMENT '列入时间'
  `put_department` VARCHAR(255) COMMENT '决定列入机关'
  `remove_reason` VARCHAR(255) COMMENT '移出原因'
  `remove_date` VARCHAR(255) COMMENT '移出时间'
  `remove_department` VARCHAR(255) COMMENT '决定移出机关'
  `type` VARCHAR(255) COMMENT '类别'
  `fact` VARCHAR(255) COMMENT '违法事实'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - illegalList/_child';

CREATE TABLE IF NOT EXISTS `base_info_punish_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - punishList';

CREATE TABLE IF NOT EXISTS `base_info_punish_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_punish_list_id` BIGINT COMMENT '外键, 关联 `base_info_punish_list`.id',
  `id` BIGINT COMMENT '表id'
  `base` VARCHAR(255) COMMENT '省份简称（无用)'
  `punish_number` VARCHAR(255) COMMENT '行政处罚决定书文号'
  `name` VARCHAR(255) COMMENT '公司名称'
  `reg_number` VARCHAR(255) COMMENT '注册号'
  `legal_person_name` VARCHAR(255) COMMENT '法定代表人（负责人）姓名'
  `type` VARCHAR(255) COMMENT '违法行为类型'
  `content` VARCHAR(255) COMMENT '行政处罚内容'
  `department_name` VARCHAR(255) COMMENT '作出行政处罚决定机关名称'
  `decision_date` VARCHAR(255) COMMENT '作出行政处罚决定日期'
  `publish_date` VARCHAR(255) COMMENT '无用'
  `description` VARCHAR(255) COMMENT '无用'
  `source_name` VARCHAR(255) COMMENT '来源名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - punishList/_child';

CREATE TABLE IF NOT EXISTS `base_info_check_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - checkList';

CREATE TABLE IF NOT EXISTS `base_info_check_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_check_list_id` BIGINT COMMENT '外键, 关联 `base_info_check_list`.id',
  `id` BIGINT COMMENT '表id'
  `check_org` VARCHAR(255) COMMENT '检查实施机关'
  `check_type` VARCHAR(255) COMMENT '类型'
  `check_date` VARCHAR(255) COMMENT '日期'
  `check_result` VARCHAR(255) COMMENT '结果'
  `remark` VARCHAR(255) COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - checkList/_child';

CREATE TABLE IF NOT EXISTS `base_info_license_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - licenseList';

CREATE TABLE IF NOT EXISTS `base_info_license_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_license_list_id` BIGINT COMMENT '外键, 关联 `base_info_license_list`.id',
  `id` BIGINT COMMENT 'id'
  `licencename` VARCHAR(255) COMMENT '许可证名称'
  `licencenumber` VARCHAR(255) COMMENT '许可书文编号'
  `source` VARCHAR(255) COMMENT '来源'
  `scope` VARCHAR(255) COMMENT '范围'
  `fromdate` VARCHAR(255) COMMENT '起始日期'
  `todate` VARCHAR(255) COMMENT '截止日期'
  `department` VARCHAR(255) COMMENT '发证机关'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - licenseList/_child';

CREATE TABLE IF NOT EXISTS `base_info_liquidating_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id',
  `id` BIGINT COMMENT '表id'
  `manager` VARCHAR(255) COMMENT '清算组负责人'
  `member` VARCHAR(255) COMMENT '清算成员名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - liquidatingInfo';

CREATE TABLE IF NOT EXISTS `base_info_equity_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - equityList';

CREATE TABLE IF NOT EXISTS `base_info_equity_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_equity_list_id` BIGINT COMMENT '外键, 关联 `base_info_equity_list`.id',
  `id` BIGINT COMMENT '表id'
  `reg_number` VARCHAR(255) COMMENT '登记编号'
  `target_company` VARCHAR(255) COMMENT '出质股权标的企业'
  `pledgor` VARCHAR(255) COMMENT '出质人'
  `certif_number` VARCHAR(255) COMMENT '出质人证照/证件号码'
  `equity_amount` VARCHAR(255) COMMENT '出质股权数额'
  `pledgee` VARCHAR(255) COMMENT '质权人'
  `certif_number_r` VARCHAR(255) COMMENT '质权人证照/证件号码'
  `reg_date` VARCHAR(255) COMMENT '股权出质设立登记日期'
  `state` VARCHAR(255) COMMENT '状态'
  `put_date` VARCHAR(255) COMMENT '股权出质设立发布日期'
  `cancel_date` VARCHAR(255) COMMENT '注销日期'
  `cancel_reason` VARCHAR(255) COMMENT '注销原因'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - equityList/_child';

CREATE TABLE IF NOT EXISTS `base_info_branch_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - branchList';

CREATE TABLE IF NOT EXISTS `base_info_branch_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_branch_list_id` BIGINT COMMENT '外键, 关联 `base_info_branch_list`.id',
  `id` BIGINT COMMENT '公司'
  `alias` VARCHAR(255) COMMENT '简称'
  `estiblish_time` VARCHAR(255) COMMENT '成立日期'
  `reg_status` VARCHAR(255) COMMENT '经营状态'
  `legal_person_name` VARCHAR(255) COMMENT '法人'
  `category` VARCHAR(255) COMMENT '行业'
  `reg_capital` VARCHAR(255) COMMENT '注册资本'
  `name` VARCHAR(255) COMMENT '名称'
  `base` VARCHAR(255) COMMENT '省份简称'
  `person_type` BIGINT COMMENT '法人类型 1-人 2-公司'
  `logo` VARCHAR(255) COMMENT '企业logo'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - branchList/_child';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list`.id',
  `ass_id` BIGINT COMMENT '表id'
  `executed_person` VARCHAR(255) COMMENT '被执行人'
  `equity_amount` VARCHAR(255) COMMENT '股权数额'
  `execute_notice_num` VARCHAR(255) COMMENT '执行通知书文号'
  `executive_court` VARCHAR(255) COMMENT '执行法院'
  `type_state` VARCHAR(255) COMMENT '类型|状态'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child_company_judicial_shareholder_change_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list_child`.id',
  `executive_court` VARCHAR(255) COMMENT '执行法院'
  `implementation_matters` VARCHAR(255) COMMENT '执行事项'
  `execute_order_num` VARCHAR(255) COMMENT '执行裁定书文号'
  `execute_notice_num` VARCHAR(255) COMMENT '执行通知书文号'
  `executed_person` VARCHAR(255) COMMENT '被执行人'
  `equity_amount_other` VARCHAR(255) COMMENT '被执行人持有股权数额'
  `license_type` VARCHAR(255) COMMENT '被执行人证照种类'
  `license_num` VARCHAR(255) COMMENT '被执行人证照号码'
  `assignee` VARCHAR(255) COMMENT '受让人'
  `execution_date` VARCHAR(255) COMMENT '协助执行日期'
  `assignee_license_type` VARCHAR(255) COMMENT '受让人证照种类'
  `assignee_license_num` VARCHAR(255) COMMENT '受让人证照号码'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child/companyJudicialShareholderChangeInfo';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child_company_judicial_assistance_frozen_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list_child`.id',
  `executive_court` VARCHAR(255) COMMENT '执行法院'
  `implementation_matters` VARCHAR(255) COMMENT '执行事项'
  `execute_order_num` VARCHAR(255) COMMENT '执行裁定书文号'
  `execute_notice_num` VARCHAR(255) COMMENT '执行通知书文号'
  `executed_person` VARCHAR(255) COMMENT '被执行人'
  `equity_amount_other` VARCHAR(255) COMMENT '被执行人持有股权、其它投资权益的数额'
  `license_type` VARCHAR(255) COMMENT '被执行人证照种类'
  `license_num` VARCHAR(255) COMMENT '被执行人证照号码'
  `from_date` VARCHAR(255) COMMENT '冻结期限自'
  `to_date` VARCHAR(255) COMMENT '冻结期限至'
  `period` VARCHAR(255) COMMENT '冻结期限'
  `publicity_date` VARCHAR(255) COMMENT '冻结公示日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child/companyJudicialAssistanceFrozenInfo';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child_company_judicial_assistance_frozen_invalidation_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list_child`.id',
  `invalidation_reason` VARCHAR(255) COMMENT '失效原因'
  `invalidation_date` VARCHAR(255) COMMENT '失效日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child/companyJudicialAssistanceFrozenInvalidationInfo';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child_company_judicial_assistance_frozen_keep_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list_child`.id',
  `executive_court` VARCHAR(255) COMMENT '执行法院'
  `implementation_matters` VARCHAR(255) COMMENT '执行事项'
  `execute_order_num` VARCHAR(255) COMMENT '执行裁定书文号'
  `execute_notice_num` VARCHAR(255) COMMENT '执行通知书文号'
  `executed_person` VARCHAR(255) COMMENT '被执行人'
  `equity_amount_other` VARCHAR(255) COMMENT '被执行人持有股权、其它投资权益的数额'
  `license_type` VARCHAR(255) COMMENT '被执行人证照种类'
  `license_num` VARCHAR(255) COMMENT '被执行人证照号码'
  `from_date` VARCHAR(255) COMMENT '续行冻结期限自'
  `to_date` VARCHAR(255) COMMENT '续行冻结期限至'
  `period` VARCHAR(255) COMMENT '续行冻结期限'
  `publicity_date` VARCHAR(255) COMMENT '公示日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child/companyJudicialAssistanceFrozenKeepInfo';

CREATE TABLE IF NOT EXISTS `base_info_judicial_list_child_company_judicial_assistance_frozen_rem_info` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_judicial_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_judicial_list_child`.id',
  `executive_court` VARCHAR(255) COMMENT '执行法院'
  `implementation_matters` VARCHAR(255) COMMENT '执行事项'
  `execute_order_num` VARCHAR(255) COMMENT '执行裁定书文号'
  `execute_notice_num` VARCHAR(255) COMMENT '执行通知书文号'
  `executed_person` VARCHAR(255) COMMENT '被执行人'
  `equity_amount_other` VARCHAR(255) COMMENT '被执行人持有股权、其它投资权益的数额'
  `license_type` VARCHAR(255) COMMENT '被执行人证照种类'
  `license_num` VARCHAR(255) COMMENT '被执行人证照号码'
  `frozen_remove_date` VARCHAR(255) COMMENT '解除冻结日期'
  `publicity_date` VARCHAR(255) COMMENT '公示日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - judicialList/_child/companyJudicialAssistanceFrozenRemInfo';

CREATE TABLE IF NOT EXISTS `base_info_brief_cancel` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id',
  `id` BIGINT COMMENT '公告id'
  `company_name` VARCHAR(255) COMMENT '公司名'
  `reg_num` VARCHAR(255) COMMENT '注册号'
  `credit_code` VARCHAR(255) COMMENT '统一社会信用代码'
  `announcement_term` VARCHAR(255) COMMENT '公告期'
  `announcement_end_date` VARCHAR(255) COMMENT '公告结束日期'
  `reg_authority` VARCHAR(255) COMMENT '登记机关'
  `investor_commitment_download_url` VARCHAR(255) COMMENT '原链接'
  `oss_path` VARCHAR(255) COMMENT 'oss路径'
  `brief_cancel_result` VARCHAR(255) COMMENT '简易注销结果'
  `announcement_apply_date` VARCHAR(255) COMMENT '公告申请日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - briefCancel';

CREATE TABLE IF NOT EXISTS `base_info_brief_cancel_objection_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_brief_cancel_id` BIGINT COMMENT '外键, 关联 `base_info_brief_cancel`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - briefCancel/objectionList';

CREATE TABLE IF NOT EXISTS `base_info_brief_cancel_objection_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_brief_cancel_objection_list_id` BIGINT COMMENT '外键, 关联 `base_info_brief_cancel_objection_list`.id',
  `objection_apply_person` VARCHAR(255) COMMENT '异议申请人'
  `objection_content` VARCHAR(255) COMMENT '异议内容'
  `objection_date` VARCHAR(255) COMMENT '异议时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - briefCancel/objectionList/_child';

CREATE TABLE IF NOT EXISTS `base_info_ipr_pledge_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - iprPledgeList';

CREATE TABLE IF NOT EXISTS `base_info_ipr_pledge_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_ipr_pledge_list_id` BIGINT COMMENT '外键, 关联 `base_info_ipr_pledge_list`.id',
  `id` BIGINT COMMENT '表id'
  `ipr_certificate_num` VARCHAR(255) COMMENT '知识产权登记证号'
  `ipr_name` VARCHAR(255) COMMENT '名称'
  `ipr_type` VARCHAR(255) COMMENT '种类'
  `pledgor_name` VARCHAR(255) COMMENT '出质人'
  `pledgee_name` VARCHAR(255) COMMENT '质权人名称'
  `pledge_reg_period` VARCHAR(255) COMMENT '质权登记期限'
  `state` VARCHAR(255) COMMENT '状态'
  `publicity_date` VARCHAR(255) COMMENT '公示日期'
  `cancle_date` VARCHAR(255) COMMENT '注销日期'
  `cancle_reason` VARCHAR(255) COMMENT '注销原因'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - iprPledgeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_ipr_pledge_list_child_change_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_ipr_pledge_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_ipr_pledge_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - iprPledgeList/_child/changeList';

CREATE TABLE IF NOT EXISTS `base_info_ipr_pledge_list_child_change_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_ipr_pledge_list_child_change_list_id` BIGINT COMMENT '外键, 关联 `base_info_ipr_pledge_list_child_change_list`.id',
  `change_item` VARCHAR(255) COMMENT '变更事项'
  `content_before` VARCHAR(255) COMMENT '变更前'
  `content_after` VARCHAR(255) COMMENT '变更后'
  `change_time` VARCHAR(255) COMMENT '变更日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - iprPledgeList/_child/changeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_mort_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list`.id',
  `id` BIGINT COMMENT '表id'
  `base` VARCHAR(255) COMMENT '省份简称'
  `reg_num` VARCHAR(255) COMMENT '登记编号'
  `reg_date` VARCHAR(255) COMMENT '登记日期'
  `publish_date` VARCHAR(255) COMMENT '公示日期'
  `status` VARCHAR(255) COMMENT '状态'
  `reg_department` VARCHAR(255) COMMENT '登记机关'
  `type` VARCHAR(255) COMMENT '被担保债权种类'
  `amount` VARCHAR(255) COMMENT '被担保债权数额'
  `term` VARCHAR(255) COMMENT '债务人履行债务的期限'
  `scope` VARCHAR(255) COMMENT '担保范围'
  `remark` VARCHAR(255) COMMENT '备注'
  `overview_type` VARCHAR(255) COMMENT '概况种类(字段弃用)'
  `overview_amount` VARCHAR(255) COMMENT '概况数额(字段弃用)'
  `overview_scope` VARCHAR(255) COMMENT '概况担保的范围(字段弃用)'
  `overview_term` VARCHAR(255) COMMENT '概况债务人履行债务的期限(字段弃用)'
  `overview_remark` VARCHAR(255) COMMENT '概况备注(字段弃用)'
  `cancel_date` VARCHAR(255) COMMENT '注销日期'
  `cancel_reason` VARCHAR(255) COMMENT '注销原因'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_change_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/changeList';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_change_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_change_list_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child_change_list`.id',
  `change_date` VARCHAR(255) COMMENT '变更时间'
  `change_content` VARCHAR(255) COMMENT '变更内容'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/changeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_pawn_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/pawnList';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_pawn_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_pawn_list_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child_pawn_list`.id',
  `pawn_name` VARCHAR(255) COMMENT '名称'
  `ownership` VARCHAR(255) COMMENT '所有权归属'
  `detail` VARCHAR(255) COMMENT '数量、质量、状况、所在地等情况'
  `remark` VARCHAR(255) COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/pawnList/_child';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_people_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/peopleList';

CREATE TABLE IF NOT EXISTS `base_info_mort_list_child_people_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_mort_list_child_people_list_id` BIGINT COMMENT '外键, 关联 `base_info_mort_list_child_people_list`.id',
  `people_name` VARCHAR(255) COMMENT '抵押权人名称'
  `license_type` VARCHAR(255) COMMENT '抵押权人证照/证件类型'
  `license_num` VARCHAR(255) COMMENT '证照/证件号码'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - mortList/_child/peopleList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list`.id',
  `id` BIGINT COMMENT '年报id'
  `release_time` VARCHAR(255) COMMENT '发布时间'
  `report_year` VARCHAR(255) COMMENT '年报年度'
  `company_name` VARCHAR(255) COMMENT '企业名称'
  `credit_code` VARCHAR(255) COMMENT '统一社会信用代码'
  `reg_number` VARCHAR(255) COMMENT '注册号'
  `phone_number` VARCHAR(255) COMMENT '电话号'
  `postcode` VARCHAR(255) COMMENT '邮政编码'
  `postal_address` VARCHAR(255) COMMENT '企业通信地址'
  `email` VARCHAR(255) COMMENT '邮箱'
  `manage_state` VARCHAR(255) COMMENT '企业经营状态'
  `employee_num` VARCHAR(255) COMMENT '从业人数'
  `operator_name` VARCHAR(255) COMMENT '经营者名称'
  `total_assets` VARCHAR(255) COMMENT '资产总额'
  `total_equity` VARCHAR(255) COMMENT '所有者权益合计'
  `total_sales` VARCHAR(255) COMMENT '销售总额(营业总收入)'
  `total_profit` VARCHAR(255) COMMENT '利润总额'
  `prime_bus_profit` VARCHAR(255) COMMENT '主营业务收入'
  `retained_profit` VARCHAR(255) COMMENT '净利润'
  `total_tax` VARCHAR(255) COMMENT '纳税总额'
  `total_liability` VARCHAR(255) COMMENT '负债总额'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_equity_change_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/equityChangeList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_equity_change_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_equity_change_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_equity_change_list`.id',
  `investor_name` VARCHAR(255) COMMENT '股东（发起人）'
  `ratio_before` VARCHAR(255) COMMENT '变更前股权比例'
  `ratio_after` VARCHAR(255) COMMENT '变更后股权比例'
  `change_time` VARCHAR(255) COMMENT '股权变更日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/equityChangeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_guarantee_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/guaranteeList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_guarantee_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_guarantee_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_guarantee_list`.id',
  `creditor` VARCHAR(255) COMMENT '债权人'
  `obligor` VARCHAR(255) COMMENT '债务人'
  `credito_type` VARCHAR(255) COMMENT '主债权种类'
  `credito_amount` VARCHAR(255) COMMENT '主债权数额'
  `credito_term` VARCHAR(255) COMMENT '履行债务的期限'
  `guarantee_term` VARCHAR(255) COMMENT '保证的期间'
  `guarantee_way` VARCHAR(255) COMMENT '保证的方式'
  `guarantee_scope` VARCHAR(255) COMMENT '保证担保的范围'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/guaranteeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_out_bound_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/outBoundList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_out_bound_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_out_bound_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_out_bound_list`.id',
  `outcompany_name` VARCHAR(255) COMMENT '对外投资企业名称'
  `reg_num` VARCHAR(255) COMMENT '注册号'
  `credit_code` VARCHAR(255) COMMENT '统一信用代码'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/outBoundList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_share_holder_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/shareHolderList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_share_holder_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_share_holder_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_share_holder_list`.id',
  `investor_name` VARCHAR(255) COMMENT '股东名称'
  `subscribe_amount` VARCHAR(255) COMMENT '认缴出资额'
  `subscribe_time` VARCHAR(255) COMMENT '认缴出资时间'
  `subscribe_type` VARCHAR(255) COMMENT '认缴出资方式'
  `paid_amount` VARCHAR(255) COMMENT '实缴出资额'
  `paid_time` VARCHAR(255) COMMENT '实缴出资时间'
  `paid_type` VARCHAR(255) COMMENT '实缴出资方式'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/shareHolderList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_web_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/webList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_web_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_web_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_web_list`.id',
  `web_type` VARCHAR(255) COMMENT '网站类型'
  `name` VARCHAR(255) COMMENT '名称'
  `website` VARCHAR(255) COMMENT '网址'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/webList/_child';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_social_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/socialList';

CREATE TABLE IF NOT EXISTS `base_info_report_list_child_social_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_report_list_child_social_list_id` BIGINT COMMENT '外键, 关联 `base_info_report_list_child_social_list`.id',
  `endowment_insurance` VARCHAR(255) COMMENT '城镇职工基本养老保险人数'
  `unemployment_insurance` VARCHAR(255) COMMENT '失业保险人数'
  `medical_insurance` VARCHAR(255) COMMENT '职工基本医疗保险人数'
  `employment_injury_insurance` VARCHAR(255) COMMENT '工伤保险'
  `maternity_insurance` VARCHAR(255) COMMENT '生育保险人数'
  `endowment_insurance_base` VARCHAR(255) COMMENT '单位参加城镇职工基本养老保险缴费基数'
  `unemployment_insurance_base` VARCHAR(255) COMMENT '单位参加失业保险缴费基数'
  `medical_insurance_base` VARCHAR(255) COMMENT '单位参加职工基本医疗保险缴费基数'
  `maternity_insurance_base` VARCHAR(255) COMMENT '单位参加生育保险缴费基数'
  `endowment_insurance_pay_amount` VARCHAR(255) COMMENT '参加城镇职工基本养老保险本期实际缴费金额'
  `unemployment_insurance_pay_amount` VARCHAR(255) COMMENT '参加失业保险本期实际缴费金额'
  `medical_insurance_pay_amount` VARCHAR(255) COMMENT '参加职工基本医疗保险本期实际缴费金额'
  `employment_injury_insurance_pay_amount` VARCHAR(255) COMMENT '参加工伤保险本期实际缴费金额'
  `maternity_insurance_pay_amount` VARCHAR(255) COMMENT '参加生育保险本期实际缴费金额'
  `endowment_insurance_owe_amount` VARCHAR(255) COMMENT '单位参加城镇职工基本养老保险累计欠缴金额'
  `unemployment_insurance_owe_amount` VARCHAR(255) COMMENT '单位参加失业保险累计欠缴金额'
  `medical_insurance_owe_amount` VARCHAR(255) COMMENT '单位参加职工基本医疗保险累计欠缴金额'
  `employment_injury_insurance_owe_amount` VARCHAR(255) COMMENT '单位参加工伤保险累计欠缴金额'
  `maternity_insurance_owe_amount` VARCHAR(255) COMMENT '单位参加生育保险累计欠缴金额'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - reportList/_child/socialList/_child';

CREATE TABLE IF NOT EXISTS `base_info_change_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - changeList';

CREATE TABLE IF NOT EXISTS `base_info_change_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_change_list_id` BIGINT COMMENT '外键, 关联 `base_info_change_list`.id',
  `id` BIGINT COMMENT '表id'
  `change_item` VARCHAR(255) COMMENT '变更事项'
  `change_time` VARCHAR(255) COMMENT '变更时间'
  `content_before` VARCHAR(255) COMMENT '变更前'
  `content_after` VARCHAR(255) COMMENT '变更后'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - changeList/_child';

CREATE TABLE IF NOT EXISTS `base_info_invest_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - investList';

CREATE TABLE IF NOT EXISTS `base_info_invest_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_invest_list_id` BIGINT COMMENT '外键, 关联 `base_info_invest_list`.id',
  `org_type` VARCHAR(255) COMMENT '公司类型'
  `business_scope` VARCHAR(255) COMMENT '经营范围'
  `percent` VARCHAR(255) COMMENT '投资占比'
  `reg_status` VARCHAR(255) COMMENT '企业状态'
  `estiblish_time` VARCHAR(255) COMMENT '开业时间'
  `legal_person_name` VARCHAR(255) COMMENT '法人'
  `type` VARCHAR(255) COMMENT '1-公司 2-人（无用）'
  `amount` BIGINT COMMENT '投资金额'
  `id` BIGINT COMMENT '公司id'
  `category` VARCHAR(255) COMMENT '行业'
  `reg_capital` VARCHAR(255) COMMENT '注册资金'
  `name` VARCHAR(255) COMMENT '被投资公司'
  `base` VARCHAR(255) COMMENT '省份简称'
  `credit_code` VARCHAR(255) COMMENT '统一社会信用代码'
  `person_type` BIGINT COMMENT '法人类型1 人 2 公司'
  `alias` VARCHAR(255) COMMENT '// 简称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - investList/_child';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_share_holder_list_id` BIGINT COMMENT '外键, 关联 `base_info_share_holder_list`.id',
  `id` BIGINT COMMENT '对应表id'
  `logo` VARCHAR(255) COMMENT 'logo'
  `name` VARCHAR(255) COMMENT '股东名'
  `alias` VARCHAR(255) COMMENT '简称'
  `type` BIGINT COMMENT '1-公司 2-人'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList/_child';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list_child_capital` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_share_holder_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_share_holder_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList/_child/capital';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list_child_capital_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_share_holder_list_child_capital_id` BIGINT COMMENT '外键, 关联 `base_info_share_holder_list_child_capital`.id',
  `amomon` VARCHAR(255) COMMENT '认缴金额'
  `time` VARCHAR(255) COMMENT '认缴时间'
  `percent` VARCHAR(255) COMMENT '占比'
  `paymet` VARCHAR(255) COMMENT '认缴方式'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList/_child/capital/_child';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list_child_capital_actl` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_share_holder_list_child_id` BIGINT COMMENT '外键, 关联 `base_info_share_holder_list_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList/_child/capitalActl';

CREATE TABLE IF NOT EXISTS `base_info_share_holder_list_child_capital_actl_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_share_holder_list_child_capital_actl_id` BIGINT COMMENT '外键, 关联 `base_info_share_holder_list_child_capital_actl`.id',
  `amomon` VARCHAR(255) COMMENT '认缴金额'
  `time` VARCHAR(255) COMMENT '认缴时间'
  `percent` VARCHAR(255) COMMENT '占比'
  `paymet` VARCHAR(255) COMMENT '认缴方式'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - shareHolderList/_child/capitalActl/_child';

CREATE TABLE IF NOT EXISTS `base_info_headquarters` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `base_info_id` BIGINT COMMENT '外键, 关联 `base_info`.id',
  `reg_capital` VARCHAR(255) COMMENT '注册资本'
  `estiblish_time` VARCHAR(255) COMMENT '成立日期'
  `legal_person_name` VARCHAR(255) COMMENT '法人'
  `person_logo` VARCHAR(255) COMMENT '法人图片'
  `reg_status` VARCHAR(255) COMMENT '经营状态'
  `name` VARCHAR(255) COMMENT '总公司名'
  `logo` VARCHAR(255) COMMENT 'logo'
  `alias` VARCHAR(255) COMMENT '公司简称'
  `id` BIGINT COMMENT '公司id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工商信息 - headquarters';

-- ==================================================
-- SQL for 疑似实际控制人 (API ID: 1123)
-- ==================================================
CREATE TABLE IF NOT EXISTS `suspected_controller` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人';

CREATE TABLE IF NOT EXISTS `suspected_controller_actual_controller_list` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_id` BIGINT COMMENT '外键, 关联 `suspected_controller`.id',
  `h_id` BIGINT COMMENT '人id'
  `g_id` BIGINT COMMENT '公司id'
  `h_pid` VARCHAR(255) COMMENT '人员pid'
  `name` VARCHAR(255) COMMENT '控制人姓名'
  `type` BIGINT COMMENT '1-人 2-公司'
  `ratio` BIGINT COMMENT '占比'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - actualControllerList';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_id` BIGINT COMMENT '外键, 关联 `suspected_controller`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_relationships` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/relationships';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_relationships_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_relationships_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0_relationships`.id',
  `start_node` BIGINT COMMENT '起始节点'
  `type` VARCHAR(255) COMMENT 'OWN->执行事务合伙人：BRANCH->分支机构：INVEST->投资关系'
  `end_node` VARCHAR(255) COMMENT '结束节点'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/relationships/_child';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_relationships_child_properties` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_relationships_child_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0_relationships_child`.id',
  `percent` VARCHAR(255) COMMENT '股份比例'
  `is_red` BIGINT COMMENT '是否标红 0-未标红 1-标红'
  `percent_str` VARCHAR(255) COMMENT '股份比例'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/relationships/_child/properties';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_nodes` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/nodes';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_nodes_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_nodes_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0_nodes`.id',
  `id` VARCHAR(255) COMMENT '公司id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/nodes/_child';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_nodes_child_properties` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_nodes_child_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0_nodes_child`.id',
  `gid` VARCHAR(255) COMMENT '公司id'
  `name` VARCHAR(255) COMMENT '公司名'
  `type` BIGINT COMMENT '1-人 2-公司'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/nodes/_child/properties';

CREATE TABLE IF NOT EXISTS `suspected_controller_path_map_p_0_nodes_child_labels` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suspected_controller_path_map_p_0_nodes_child_id` BIGINT COMMENT '外键, 关联 `suspected_controller_path_map_p_0_nodes_child`.id',
  `_child` VARCHAR(255) COMMENT '类型'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疑似实际控制人 - pathMap/p_0/nodes/_child/labels';

-- ==================================================
-- SQL for 所属集团查询 (API ID: 1105)
-- ==================================================
CREATE TABLE IF NOT EXISTS `group_affiliation` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `group_rename` VARCHAR(255) COMMENT '集团名称'
  `group_uuid` VARCHAR(255) COMMENT '集团uuid'
  `group_logo` VARCHAR(255) COMMENT '集团Logo'
  `group_num` BIGINT COMMENT '集团成员数量'
  `group_type` BIGINT COMMENT '集团类型：0-集团 1-族群'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='所属集团查询';

-- ==================================================
-- SQL for 资质证书 (API ID: 880)
-- ==================================================
CREATE TABLE IF NOT EXISTS `certifications` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资质证书';

CREATE TABLE IF NOT EXISTS `certifications_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `certifications_id` BIGINT COMMENT '外键, 关联 `certifications`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资质证书 - items';

CREATE TABLE IF NOT EXISTS `certifications_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `certifications_items_id` BIGINT COMMENT '外键, 关联 `certifications_items`.id',
  `cert_no` VARCHAR(255) COMMENT '证书编号'
  `id` VARCHAR(255) COMMENT 'uuid'
  `certificate_name` VARCHAR(255) COMMENT '证书类型'
  `certificate_type` VARCHAR(255) COMMENT '证书类型（新）'
  `start_date` VARCHAR(255) COMMENT '发证日期'
  `end_date` VARCHAR(255) COMMENT '截止日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资质证书 - items/_child';

CREATE TABLE IF NOT EXISTS `certifications_items_child_detail` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `certifications_items_child_id` BIGINT COMMENT '外键, 关联 `certifications_items_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资质证书 - items/_child/detail';

CREATE TABLE IF NOT EXISTS `certifications_items_child_detail_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `certifications_items_child_detail_id` BIGINT COMMENT '外键, 关联 `certifications_items_child_detail`.id',
  `content` VARCHAR(255) COMMENT '内容'
  `title` VARCHAR(255) COMMENT '标题'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资质证书 - items/_child/detail/_child';

-- ==================================================
-- SQL for 股权变更 (API ID: 998)
-- ==================================================
CREATE TABLE IF NOT EXISTS `equity_changes` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股权变更';

CREATE TABLE IF NOT EXISTS `equity_changes_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `equity_changes_id` BIGINT COMMENT '外键, 关联 `equity_changes`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股权变更 - items';

CREATE TABLE IF NOT EXISTS `equity_changes_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `equity_changes_items_id` BIGINT COMMENT '外键, 关联 `equity_changes_items`.id',
  `gid` BIGINT COMMENT '公司id'
  `investor_name` VARCHAR(255) COMMENT '股东名'
  `ratio_after` VARCHAR(255) COMMENT '变更后'
  `logo` VARCHAR(255) COMMENT 'logo'
  `ratio_before` VARCHAR(255) COMMENT '变更前'
  `id` BIGINT COMMENT '股东id'
  `type` BIGINT COMMENT '类型，1-公司 2-人'
  `change_time` BIGINT COMMENT '变更时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股权变更 - items/_child';

-- ==================================================
-- SQL for 供应商 (API ID: 946)
-- ==================================================
CREATE TABLE IF NOT EXISTS `suppliers` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商';

CREATE TABLE IF NOT EXISTS `suppliers_supplies_year` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suppliers_id` BIGINT COMMENT '外键, 关联 `suppliers`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商 - suppliesYear';

CREATE TABLE IF NOT EXISTS `suppliers_supplies_year_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suppliers_supplies_year_id` BIGINT COMMENT '外键, 关联 `suppliers_supplies_year`.id',
  `title` VARCHAR(255) COMMENT '年份（数量）'
  `value` VARCHAR(255) COMMENT '年份'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商 - suppliesYear/_child';

CREATE TABLE IF NOT EXISTS `suppliers_page_bean` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suppliers_id` BIGINT COMMENT '外键, 关联 `suppliers`.id',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商 - pageBean';

CREATE TABLE IF NOT EXISTS `suppliers_page_bean_result` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suppliers_page_bean_id` BIGINT COMMENT '外键, 关联 `suppliers_page_bean`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商 - pageBean/result';

CREATE TABLE IF NOT EXISTS `suppliers_page_bean_result_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `suppliers_page_bean_result_id` BIGINT COMMENT '外键, 关联 `suppliers_page_bean_result`.id',
  `supplier_graph_id` BIGINT COMMENT '供应商id'
  `announcement_date` BIGINT COMMENT '报告期'
  `amt` VARCHAR(255) COMMENT '采购金额（万元）'
  `logo` VARCHAR(255) COMMENT 'logo'
  `alias` VARCHAR(255) COMMENT '简称'
  `supplier_name` VARCHAR(255) COMMENT '供应商名称'
  `relationship` VARCHAR(255) COMMENT '关联关系'
  `data_source` VARCHAR(255) COMMENT '数据来源'
  `ratio` VARCHAR(255) COMMENT '采购占比'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商 - pageBean/result/_child';

-- ==================================================
-- SQL for 客户 (API ID: 947)
-- ==================================================
CREATE TABLE IF NOT EXISTS `customers` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户';

CREATE TABLE IF NOT EXISTS `customers_clients_year` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `customers_id` BIGINT COMMENT '外键, 关联 `customers`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户 - clientsYear';

CREATE TABLE IF NOT EXISTS `customers_clients_year_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `customers_clients_year_id` BIGINT COMMENT '外键, 关联 `customers_clients_year`.id',
  `title` VARCHAR(255) COMMENT '年份（数量）'
  `value` VARCHAR(255) COMMENT '年份'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户 - clientsYear/_child';

CREATE TABLE IF NOT EXISTS `customers_page_bean` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `customers_id` BIGINT COMMENT '外键, 关联 `customers`.id',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户 - pageBean';

CREATE TABLE IF NOT EXISTS `customers_page_bean_result` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `customers_page_bean_id` BIGINT COMMENT '外键, 关联 `customers_page_bean`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户 - pageBean/result';

CREATE TABLE IF NOT EXISTS `customers_page_bean_result_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `customers_page_bean_result_id` BIGINT COMMENT '外键, 关联 `customers_page_bean_result`.id',
  `announcement_date` BIGINT COMMENT '报告期'
  `amt` VARCHAR(255) COMMENT '销售金额（万元）'
  `logo` VARCHAR(255) COMMENT 'logo'
  `alias` VARCHAR(255) COMMENT '简称'
  `client_graph_id` BIGINT COMMENT '客户id'
  `relationship` VARCHAR(255) COMMENT '关联关系'
  `client_name` VARCHAR(255) COMMENT '客户名'
  `data_source` VARCHAR(255) COMMENT '数据来源'
  `ratio` VARCHAR(255) COMMENT '销售占比'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户 - pageBean/result/_child';

-- ==================================================
-- SQL for 融资信息 (API ID: 826)
-- ==================================================
CREATE TABLE IF NOT EXISTS `financing_history` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='融资信息';

CREATE TABLE IF NOT EXISTS `financing_history_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `financing_history_id` BIGINT COMMENT '外键, 关联 `financing_history`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='融资信息 - items';

CREATE TABLE IF NOT EXISTS `financing_history_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `financing_history_items_id` BIGINT COMMENT '外键, 关联 `financing_history_items`.id',
  `company_name` VARCHAR(255) COMMENT '公司名'
  `date` BIGINT COMMENT '融资时间'
  `pub_time` BIGINT COMMENT '披露时间'
  `investor_name` VARCHAR(255) COMMENT '投资企业'
  `money` VARCHAR(255) COMMENT '金额'
  `news_title` VARCHAR(255) COMMENT '新闻标题'
  `news_url` VARCHAR(255) COMMENT '新闻url'
  `round` VARCHAR(255) COMMENT '轮次'
  `share` VARCHAR(255) COMMENT '投资比例'
  `value` VARCHAR(255) COMMENT '估值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='融资信息 - items/_child';

-- ==================================================
-- SQL for 财务指标 (API ID: 967)
-- ==================================================
CREATE TABLE IF NOT EXISTS `financial_indicators` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务指标';

CREATE TABLE IF NOT EXISTS `financial_indicators_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `financial_indicators_id` BIGINT COMMENT '外键, 关联 `financial_indicators`.id',
  `crfgsasr_to_revenue` BIGINT COMMENT '销售现金流/营业收入'
  `np_atsopc_nrgal_yoy` BIGINT COMMENT '扣非净利润同比增长(%)'
  `asset_liab_ratio` BIGINT COMMENT '资产负债率(%)'
  `revenue_yoy` BIGINT COMMENT '营业总收入同比增长(%)'
  `net_profit_atsopc_yoy` BIGINT COMMENT '归属净利润同比增长(%)'
  `fully_dlt_roe` BIGINT COMMENT '摊薄净资产收益率(%)'
  `tax_rate` BIGINT COMMENT '实际税率(%)'
  `receivable_turnover_days` BIGINT COMMENT '应收账款周转天数(天)'
  `pre_receivable` BIGINT COMMENT '预收款/营业收入'
  `current_ratio` BIGINT COMMENT '流动比率'
  `operate_cash_flow_ps` BIGINT COMMENT '每股经营现金流(元)'
  `show_year` VARCHAR(255) COMMENT '年份'
  `gross_selling_rate` BIGINT COMMENT '毛利率(%)'
  `current_liab_to_total_liab` BIGINT COMMENT '流动负债/总负债(%)'
  `quick_ratio` BIGINT COMMENT '速动比率'
  `net_interest_of_total_assets` BIGINT COMMENT '摊薄总资产收益率(%)'
  `operating_total_revenue_lrr_sq` BIGINT COMMENT '营业总收入滚动环比增长(%)'
  `profit_deduct_nrgal_lrr_sq` BIGINT COMMENT '扣非净利润滚动环比增长(%)'
  `wgt_avg_roe` BIGINT COMMENT '加权净资产收益率(%)'
  `basic_eps` BIGINT COMMENT '基本每股收益(元)'
  `net_selling_rate` BIGINT COMMENT '净利率(%)'
  `total_capital_turnover` BIGINT COMMENT '总资产周转率(次)'
  `net_profit_atsopc_lrr_sq` BIGINT COMMENT '归属净利润滚动环比增长(%)'
  `net_profit_per_share` BIGINT COMMENT '每股净资产(元)'
  `capital_reserve` BIGINT COMMENT '每股公积金(元)'
  `profit_nrgal_sq` BIGINT COMMENT '扣非净利润(元)'
  `inventory_turnover_days` BIGINT COMMENT '存货周转天数(天)'
  `total_revenue` BIGINT COMMENT '营业总收入(元)'
  `undistri_profit_ps` BIGINT COMMENT '每股未分配利润(元)'
  `dlt_earnings_per_share` BIGINT COMMENT '稀释每股收益(元)'
  `net_profit_atsopc` BIGINT COMMENT '归属净利润(元)'
  `basic_e_ps_net_of_nrgal` BIGINT COMMENT '扣非每股收益(元)'
  `op_to_revenue` BIGINT COMMENT '毛利润（元）'
  `ncf_from_oa_to_revenue` BIGINT COMMENT '经营现金流/营业收入'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务指标 - _child';

-- ==================================================
-- SQL for 税务评级 (API ID: 884)
-- ==================================================
CREATE TABLE IF NOT EXISTS `tax_ratings` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='税务评级';

CREATE TABLE IF NOT EXISTS `tax_ratings_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `tax_ratings_id` BIGINT COMMENT '外键, 关联 `tax_ratings`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='税务评级 - items';

CREATE TABLE IF NOT EXISTS `tax_ratings_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `tax_ratings_items_id` BIGINT COMMENT '外键, 关联 `tax_ratings_items`.id',
  `grade` VARCHAR(255) COMMENT '纳税等级'
  `year` VARCHAR(255) COMMENT '年份'
  `eval_department` VARCHAR(255) COMMENT '评价单位'
  `type` VARCHAR(255) COMMENT '类型'
  `id_number` VARCHAR(255) COMMENT '纳税人识别号'
  `name` VARCHAR(255) COMMENT '纳税人名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='税务评级 - items/_child';

-- ==================================================
-- SQL for 新闻舆情 (API ID: 943)
-- ==================================================
CREATE TABLE IF NOT EXISTS `public_sentiment_news` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻舆情';

CREATE TABLE IF NOT EXISTS `public_sentiment_news_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `public_sentiment_news_id` BIGINT COMMENT '外键, 关联 `public_sentiment_news`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻舆情 - items';

CREATE TABLE IF NOT EXISTS `public_sentiment_news_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `public_sentiment_news_items_id` BIGINT COMMENT '外键, 关联 `public_sentiment_news_items`.id',
  `website` VARCHAR(255) COMMENT '数据来源'
  `abstracts` VARCHAR(255) COMMENT '简介'
  `docid` VARCHAR(255) COMMENT '新闻唯一标识符'
  `rtm` BIGINT COMMENT '发布时间'
  `title` VARCHAR(255) COMMENT '标题'
  `uri` VARCHAR(255) COMMENT '新闻url'
  `emotion` BIGINT COMMENT '情感分类（1-正面，0-中性，-1-负面）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻舆情 - items/_child';

CREATE TABLE IF NOT EXISTS `public_sentiment_news_items_child_tags` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `public_sentiment_news_items_child_id` BIGINT COMMENT '外键, 关联 `public_sentiment_news_items_child`.id',
  `_child` VARCHAR(255) COMMENT '标签'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻舆情 - items/_child/tags';

-- ==================================================
-- SQL for 立案信息 (API ID: 961)
-- ==================================================
CREATE TABLE IF NOT EXISTS `litigation_filing` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='立案信息';

CREATE TABLE IF NOT EXISTS `litigation_filing_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `litigation_filing_id` BIGINT COMMENT '外键, 关联 `litigation_filing`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='立案信息 - items';

CREATE TABLE IF NOT EXISTS `litigation_filing_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `litigation_filing_items_id` BIGINT COMMENT '外键, 关联 `litigation_filing_items`.id',
  `litigant` VARCHAR(255) COMMENT '当事人'
  `filing_date` VARCHAR(255) COMMENT '立案时间'
  `litigant_gids` VARCHAR(255) COMMENT '当事人id'
  `case_status` VARCHAR(255) COMMENT '案件状态'
  `source` VARCHAR(255) COMMENT '来源'
  `content` VARCHAR(255) COMMENT '案件详情'
  `case_type` VARCHAR(255) COMMENT '案件类型'
  `source_url` VARCHAR(255) COMMENT '源链接'
  `defendant` VARCHAR(255) COMMENT '被告人/被告/被上诉人/被申请人'
  `juge` VARCHAR(255) COMMENT '承办法官'
  `start_time` VARCHAR(255) COMMENT '开始时间'
  `id` VARCHAR(255) COMMENT 'id'
  `department` VARCHAR(255) COMMENT '承办部门'
  `area` VARCHAR(255) COMMENT '地区'
  `plaintiff` VARCHAR(255) COMMENT '公诉人/原告/上诉人/申请人'
  `assistant` VARCHAR(255) COMMENT '法官助理'
  `court` VARCHAR(255) COMMENT '法院'
  `case_no` VARCHAR(255) COMMENT '案号'
  `case_reason` VARCHAR(255) COMMENT '案由'
  `close_date` VARCHAR(255) COMMENT '结案时间'
  `third` VARCHAR(255) COMMENT '第三人'
  `create_time` VARCHAR(255) COMMENT '创建时间'
  `cid` BIGINT COMMENT '公司id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='立案信息 - items/_child';

-- ==================================================
-- SQL for 被执行人 (API ID: 839)
-- ==================================================
CREATE TABLE IF NOT EXISTS `enforcement_records` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='被执行人';

CREATE TABLE IF NOT EXISTS `enforcement_records_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `enforcement_records_id` BIGINT COMMENT '外键, 关联 `enforcement_records`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='被执行人 - items';

CREATE TABLE IF NOT EXISTS `enforcement_records_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `enforcement_records_items_id` BIGINT COMMENT '外键, 关联 `enforcement_records_items`.id',
  `case_code` VARCHAR(255) COMMENT '案号'
  `exec_court_name` VARCHAR(255) COMMENT '执行法院'
  `pname` VARCHAR(255) COMMENT '被执行人名称'
  `party_card_num` VARCHAR(255) COMMENT '身份证号／组织机构代码'
  `case_create_time` BIGINT COMMENT '创建时间'
  `exec_money` VARCHAR(255) COMMENT '执行标的（元）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='被执行人 - items/_child';

-- ==================================================
-- SQL for 失信人 (API ID: 843)
-- ==================================================
CREATE TABLE IF NOT EXISTS `dishonest_persons` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失信人';

CREATE TABLE IF NOT EXISTS `dishonest_persons_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `dishonest_persons_id` BIGINT COMMENT '外键, 关联 `dishonest_persons`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失信人 - items';

CREATE TABLE IF NOT EXISTS `dishonest_persons_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `dishonest_persons_items_id` BIGINT COMMENT '外键, 关联 `dishonest_persons_items`.id',
  `businessentity` VARCHAR(255) COMMENT '法人、负责人姓名'
  `areaname` VARCHAR(255) COMMENT '省份地区'
  `courtname` VARCHAR(255) COMMENT '法院'
  `unperform_part` VARCHAR(255) COMMENT '未履行部分'
  `type` VARCHAR(255) COMMENT '失信人类型，0代表人，1代表公司'
  `performed_part` VARCHAR(255) COMMENT '已履行部分'
  `iname` VARCHAR(255) COMMENT '失信人名称'
  `disrupttypename` VARCHAR(255) COMMENT '失信被执行人行为具体情形'
  `casecode` VARCHAR(255) COMMENT '案号'
  `cardnum` VARCHAR(255) COMMENT '身份证号码/组织机构代码'
  `performance` VARCHAR(255) COMMENT '履行情况'
  `regdate` BIGINT COMMENT '立案时间'
  `publishdate` BIGINT COMMENT '发布时间'
  `gistunit` VARCHAR(255) COMMENT '做出执行的依据单位'
  `duty` VARCHAR(255) COMMENT '生效法律文书确定的义务'
  `gistid` VARCHAR(255) COMMENT '执行依据文号'
  `amount_involved` BIGINT COMMENT '涉案金额，单位：元'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失信人 - items/_child';

CREATE TABLE IF NOT EXISTS `dishonest_persons_items_child_staff` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `dishonest_persons_items_child_id` BIGINT COMMENT '外键, 关联 `dishonest_persons_items_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失信人 - items/_child/staff';

CREATE TABLE IF NOT EXISTS `dishonest_persons_items_child_staff_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `dishonest_persons_items_child_staff_id` BIGINT COMMENT '外键, 关联 `dishonest_persons_items_child_staff`.id',
  `role` VARCHAR(255) COMMENT '角色'
  `code` VARCHAR(255) COMMENT '脱敏证件号'
  `name` VARCHAR(255) COMMENT '法人姓名'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失信人 - items/_child/staff/_child';

-- ==================================================
-- SQL for 限制消费令 (API ID: 1014)
-- ==================================================
CREATE TABLE IF NOT EXISTS `consumption_restrictions` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限制消费令';

CREATE TABLE IF NOT EXISTS `consumption_restrictions_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `consumption_restrictions_id` BIGINT COMMENT '外键, 关联 `consumption_restrictions`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限制消费令 - items';

CREATE TABLE IF NOT EXISTS `consumption_restrictions_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `consumption_restrictions_items_id` BIGINT COMMENT '外键, 关联 `consumption_restrictions_items`.id',
  `case_code` VARCHAR(255) COMMENT '案号'
  `qyinfo_alias` VARCHAR(255) COMMENT '企业信息简称'
  `file_path` VARCHAR(255) COMMENT 'pdf文件地址'
  `qyinfo` VARCHAR(255) COMMENT '企业信息'
  `case_create_time` BIGINT COMMENT '立案时间'
  `alias` VARCHAR(255) COMMENT '别名'
  `id` BIGINT COMMENT '对应表id'
  `xname` VARCHAR(255) COMMENT '限制消费者名称'
  `cid` BIGINT COMMENT '企业id'
  `hcgid` VARCHAR(255) COMMENT '限制消费者id'
  `applicant` VARCHAR(255) COMMENT '申请人信息'
  `applicant_cid` VARCHAR(255) COMMENT '申请人id'
  `publish_date` BIGINT COMMENT '发布日期'
  `amount_involved` BIGINT COMMENT '涉案金额，单位：元'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限制消费令 - items/_child';

-- ==================================================
-- SQL for 破产重整 (API ID: 1036)
-- ==================================================
CREATE TABLE IF NOT EXISTS `bankruptcy_cases` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
  `gid` BIGINT COMMENT '公司id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='破产重整';

CREATE TABLE IF NOT EXISTS `bankruptcy_cases_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `bankruptcy_cases_id` BIGINT COMMENT '外键, 关联 `bankruptcy_cases`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='破产重整 - items';

CREATE TABLE IF NOT EXISTS `bankruptcy_cases_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `bankruptcy_cases_items_id` BIGINT COMMENT '外键, 关联 `bankruptcy_cases_items`.id',
  `submit_time` VARCHAR(255) COMMENT '公开时间，发布时间'
  `respondent` VARCHAR(255) COMMENT '被申请人'
  `uuid` VARCHAR(255) COMMENT '唯一标示'
  `case_no` VARCHAR(255) COMMENT '案号'
  `case_type` VARCHAR(255) COMMENT '案件类型'
  `status` BIGINT COMMENT '案件状态（0-历史，1-当前）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='破产重整 - items/_child';

CREATE TABLE IF NOT EXISTS `bankruptcy_cases_items_child_applicant` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `bankruptcy_cases_items_child_id` BIGINT COMMENT '外键, 关联 `bankruptcy_cases_items_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='破产重整 - items/_child/applicant';

CREATE TABLE IF NOT EXISTS `bankruptcy_cases_items_child_applicant_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `bankruptcy_cases_items_child_applicant_id` BIGINT COMMENT '外键, 关联 `bankruptcy_cases_items_child_applicant`.id',
  `applicant_gid` BIGINT COMMENT '申请人gid'
  `applicant_name` VARCHAR(255) COMMENT '申请人名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='破产重整 - items/_child/applicant/_child';

-- ==================================================
-- SQL for 终本案件 (API ID: 1013)
-- ==================================================
CREATE TABLE IF NOT EXISTS `zhongben_cases` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='终本案件';

CREATE TABLE IF NOT EXISTS `zhongben_cases_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `zhongben_cases_id` BIGINT COMMENT '外键, 关联 `zhongben_cases`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='终本案件 - items';

CREATE TABLE IF NOT EXISTS `zhongben_cases_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `zhongben_cases_items_id` BIGINT COMMENT '外键, 关联 `zhongben_cases_items`.id',
  `case_code` VARCHAR(255) COMMENT '案号'
  `case_final_time` BIGINT COMMENT '终本日期'
  `business_id` VARCHAR(255) COMMENT '终本案件详情唯一ID'
  `case_create_time` BIGINT COMMENT '立案时间'
  `exec_court_name` VARCHAR(255) COMMENT '执行法院'
  `exec_money` VARCHAR(255) COMMENT '执行标的'
  `no_exec_money` VARCHAR(255) COMMENT '未履行金额'
  `zname` VARCHAR(255) COMMENT '被执行人名称'
  `cid` BIGINT COMMENT '企业id'
  `status` BIGINT COMMENT '终本案件状态 0-当前、1-历史'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='终本案件 - items/_child';

-- ==================================================
-- SQL for 法律诉讼(人员) (API ID: 1163)
-- ==================================================
CREATE TABLE IF NOT EXISTS `person_legal_proceedings` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律诉讼(人员)';

CREATE TABLE IF NOT EXISTS `person_legal_proceedings_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `person_legal_proceedings_id` BIGINT COMMENT '外键, 关联 `person_legal_proceedings`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律诉讼(人员) - items';

CREATE TABLE IF NOT EXISTS `person_legal_proceedings_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `person_legal_proceedings_items_id` BIGINT COMMENT '外键, 关联 `person_legal_proceedings_items`.id',
  `id` BIGINT COMMENT '对应表ID'
  `case_money` VARCHAR(255) COMMENT '案件金额'
  `pid` VARCHAR(255) COMMENT '人pid'
  `submit_time` BIGINT COMMENT '发布日期'
  `doc_type` VARCHAR(255) COMMENT '文书类型'
  `lawsuit_url` VARCHAR(255) COMMENT '天眼查url（Web）'
  `lawsuit_h5_url` VARCHAR(255) COMMENT '天眼查url（H5）'
  `uuid` VARCHAR(255) COMMENT 'uuid'
  `title` VARCHAR(255) COMMENT '案件名称'
  `court` VARCHAR(255) COMMENT '审理法院'
  `judge_time` VARCHAR(255) COMMENT '裁判日期'
  `case_no` VARCHAR(255) COMMENT '案号'
  `case_type` VARCHAR(255) COMMENT '案件类型'
  `case_reason` VARCHAR(255) COMMENT '案由'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律诉讼(人员) - items/_child';

CREATE TABLE IF NOT EXISTS `person_legal_proceedings_items_child_case_persons` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `person_legal_proceedings_items_child_id` BIGINT COMMENT '外键, 关联 `person_legal_proceedings_items_child`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律诉讼(人员) - items/_child/casePersons';

CREATE TABLE IF NOT EXISTS `person_legal_proceedings_items_child_case_persons_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `person_legal_proceedings_items_child_case_persons_id` BIGINT COMMENT '外键, 关联 `person_legal_proceedings_items_child_case_persons`.id',
  `role` VARCHAR(255) COMMENT '案件身份'
  `type` VARCHAR(255) COMMENT '类型（1=人员；2=公司）'
  `name` VARCHAR(255) COMMENT '名称'
  `gid` BIGINT COMMENT '公司ID'
  `result` VARCHAR(255) COMMENT '结果标签'
  `emotion` BIGINT COMMENT '裁判结果对应的情感倾向（1=正面；0=中性；-1=负面）'
  `hid` BIGINT COMMENT '人名ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律诉讼(人员) - items/_child/casePersons/_child';

-- ==================================================
-- SQL for 企业信用评级 (API ID: 1049)
-- ==================================================
CREATE TABLE IF NOT EXISTS `credit_ratings` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `total` BIGINT COMMENT '总数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='企业信用评级';

CREATE TABLE IF NOT EXISTS `credit_ratings_items` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `credit_ratings_id` BIGINT COMMENT '外键, 关联 `credit_ratings`.id'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='企业信用评级 - items';

CREATE TABLE IF NOT EXISTS `credit_ratings_items_child` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `credit_ratings_items_id` BIGINT COMMENT '外键, 关联 `credit_ratings_items`.id',
  `rating_outlook` VARCHAR(255) COMMENT '评级展望'
  `rating_date` VARCHAR(255) COMMENT '评级时间'
  `gid` BIGINT COMMENT '评级公司id'
  `rating_company_name` VARCHAR(255) COMMENT '评级公司'
  `bond_credit_level` VARCHAR(255) COMMENT '债券信用等级'
  `logo` VARCHAR(255) COMMENT '评级公司的logo'
  `alias` VARCHAR(255) COMMENT '评级公司简称'
  `subject_level` VARCHAR(255) COMMENT '主体等级'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='企业信用评级 - items/_child';