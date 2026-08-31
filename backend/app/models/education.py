"""人员继教管理模块数据模型（ renamed from 旧"继教培训"）。

六大子功能：
A. 人员档案（生免室人员档案，对应 BG-KS-GL-017）：独立人员主表 personnel_master + 5 张子表
   （学历教育 / 工作履历 / 资格证书 / 奖惩 / 继续教育经历）。
B. 新员工培训（BG-SM-PX-005 生免室新员工培训及考核表）+ 独立上岗资格认证（BG-SM-PX-001）。
C. 年度人员能力评估（BG-KS-PX-808 人员能力评估记录表）+ 人员比对（BG-SM-CZ-023）。
D. 组内培训（BG-KS-PX-804 检验科培训记录表）：年度培训计划 + 每次培训（签到表打印/扫描上传 +
   课件/通知/考题/效果评价存档）。
E. 实习/进修带教（BG-SM-PX-003 培训大纲及带教评价表 / BG-SM-PX-004 实操考核成绩单，依据 SM-SOP-025）。
F. 艾梅乙培训：复用 D 的 training_session，tag='艾梅乙'。

所有记录表格需 1:1 复刻原表，故字段严格对齐原始 Word 表单。附件（照片/签到扫描件/课件/通知/考题/
效果评价等）统一存入 education_attachments（LONGBLOB，复刻 comparison_attachments 模式，
优先落 COS，失败回退 MySQL BLOB）。
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# =========================================================================
# A. 人员档案
# =========================================================================
class PersonnelMaster(Base):
    """生免室人员档案（BG-KS-GL-017）。每人一行，照片存 education_attachments。"""

    __tablename__ = "personnel_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, default="")  # 姓名
    gender: Mapped[str] = mapped_column(String(10), default="")  # 性别
    birth_date: Mapped[str] = mapped_column(String(20), default="")  # 出生年月
    education: Mapped[str] = mapped_column(String(50), default="")  # 学历
    title: Mapped[str] = mapped_column(String(50), default="")  # 职称
    position: Mapped[str] = mapped_column(String(50), default="")  # 职务
    political_status: Mapped[str] = mapped_column(String(30), default="")  # 政治面貌
    group_duty: Mapped[str] = mapped_column(String(100), default="")  # 组内职责
    work_start: Mapped[str] = mapped_column(String(20), default="")  # 参加工作时间
    hospital_join: Mapped[str] = mapped_column(String(20), default="")  # 来院时间
    group_join: Mapped[str] = mapped_column(String(20), default="")  # 来组时间
    id_card: Mapped[str] = mapped_column(String(30), default="")  # 身份证号
    phone: Mapped[str] = mapped_column(String(30), default="")  # 联系电话
    photo_attachment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)  # 照片附件 id
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PersonnelEducation(Base):
    """人员学历教育经历。"""

    __tablename__ = "personnel_education"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personnel_master.id", ondelete="CASCADE"), index=True)
    school: Mapped[str] = mapped_column(String(200), default="")  # 院校
    major: Mapped[str] = mapped_column(String(200), default="")  # 专业
    degree: Mapped[str] = mapped_column(String(50), default="")  # 学历/学位
    start_date: Mapped[str] = mapped_column(String(20), default="")
    end_date: Mapped[str] = mapped_column(String(20), default="")
    remark: Mapped[str] = mapped_column(String(300), default="")


class PersonnelWorkExp(Base):
    """人员工作履历。"""

    __tablename__ = "personnel_work_exp"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personnel_master.id", ondelete="CASCADE"), index=True)
    org: Mapped[str] = mapped_column(String(200), default="")  # 单位/科室
    post: Mapped[str] = mapped_column(String(100), default="")  # 岗位
    start_date: Mapped[str] = mapped_column(String(20), default="")
    end_date: Mapped[str] = mapped_column(String(20), default="")
    remark: Mapped[str] = mapped_column(String(300), default="")


class PersonnelCert(Base):
    """人员资格/证书。"""

    __tablename__ = "personnel_cert"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personnel_master.id", ondelete="CASCADE"), index=True)
    cert_name: Mapped[str] = mapped_column(String(200), default="")  # 证书名称
    cert_no: Mapped[str] = mapped_column(String(100), default="")  # 证书编号
    issue_org: Mapped[str] = mapped_column(String(200), default="")  # 发证机构
    issue_date: Mapped[str] = mapped_column(String(20), default="")  # 发证日期
    valid_until: Mapped[str] = mapped_column(String(20), default="")  # 有效期至
    remark: Mapped[str] = mapped_column(String(300), default="")


class PersonnelReward(Base):
    """人员奖惩记录。"""

    __tablename__ = "personnel_reward"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personnel_master.id", ondelete="CASCADE"), index=True)
    reward_type: Mapped[str] = mapped_column(String(20), default="奖励")  # 奖励 / 惩罚
    title: Mapped[str] = mapped_column(String(200), default="")  # 事项
    date: Mapped[str] = mapped_column(String(20), default="")  # 日期
    org: Mapped[str] = mapped_column(String(200), default="")  # 授予/处理机构
    remark: Mapped[str] = mapped_column(String(300), default="")


class PersonnelEduExp(Base):
    """人员继续教育/培训经历。"""

    __tablename__ = "personnel_edu_exp"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personnel_master.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), default="")  # 培训项目
    organizer: Mapped[str] = mapped_column(String(200), default="")  # 组织方
    train_date: Mapped[str] = mapped_column(String(40), default="")  # 日期（完整起止区间，可能 >20 字符）
    hours: Mapped[str] = mapped_column(String(20), default="")  # 学时
    credits: Mapped[str] = mapped_column(String(20), default="")  # 学分
    cert_no: Mapped[str] = mapped_column(String(100), default="")  # 证书编号
    remark: Mapped[str] = mapped_column(String(300), default="")


# =========================================================================
# B. 新员工培训（BG-SM-PX-005）+ 独立上岗资格认证（BG-SM-PX-001）
# =========================================================================
class NewEmployeeTrain(Base):
    """生免室新员工培训及考核表（BG-SM-PX-005）。"""

    __tablename__ = "new_employee_train"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, default=None)
    name: Mapped[str] = mapped_column(String(100), index=True, default="")  # 员工姓名
    employee_category: Mapped[str] = mapped_column(String(50), default="新职工")  # 轮转/新职工/离岗6个月再上岗
    train_major: Mapped[str] = mapped_column(String(50), default="生免室")  # 培训专业
    group_join_date: Mapped[str] = mapped_column(String(20), default="")  # 入组时间
    train_duration: Mapped[str] = mapped_column(Text, default="")  # 培训时长（自由文本/各岗月数）

    # 能力评估（生化、免疫各一次）
    ability_bio_result: Mapped[str] = mapped_column(String(20), default="")  # 合格/不合格
    ability_bio_responsible: Mapped[str] = mapped_column(String(100), default="")  # 评估时间及负责人
    ability_immuno_result: Mapped[str] = mapped_column(String(20), default="")
    ability_immuno_responsible: Mapped[str] = mapped_column(String(100), default="")
    # 理论考核（试卷）、现场操作、口试
    theory_operation_oral_result: Mapped[str] = mapped_column(String(20), default="")  # 合格/不合格
    # 考核结果
    exam_result: Mapped[str] = mapped_column(String(20), default="")  # 通过/不通过
    exam_responsible: Mapped[str] = mapped_column(String(100), default="")  # 考核时间及负责人
    exam_time: Mapped[str] = mapped_column(String(20), default="")  # 考核时间

    # 培训计划及考核内容（原表大表）：[{category, content, teacher, method, exam_method, score}]
    plan_items: Mapped[str] = mapped_column(Text, default="[]")
    detail_json: Mapped[str] = mapped_column(Text, default="{}")  # 其它自由字段（如轮转明细）
    status: Mapped[str] = mapped_column(String(20), default="进行中")  # 进行中/已完成
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewEmployeeCertAuth(Base):
    """生化免疫组独立上岗资格认证审核表（BG-SM-PX-001）。"""

    __tablename__ = "new_employee_cert_auth"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, default=None)
    applicant: Mapped[str] = mapped_column(String(100), index=True, default="")  # 申请人
    apply_date: Mapped[str] = mapped_column(String(20), default="")  # 申请日期
    apply_content: Mapped[str] = mapped_column(Text, default="")  # 申请内容（岗位/仪器）
    theory_eval: Mapped[str] = mapped_column(Text, default="")  # 理论考核
    operation_eval: Mapped[str] = mapped_column(Text, default="")  # 操作考核
    group_leader_opinion: Mapped[str] = mapped_column(Text, default="")  # 组长意见
    director_opinion: Mapped[str] = mapped_column(Text, default="")  # 主任意见
    status: Mapped[str] = mapped_column(String(20), default="待审核")  # 待审核/通过/不通过
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =========================================================================
# C. 年度人员能力评估（BG-KS-PX-808）+ 人员比对（BG-SM-CZ-023）
# =========================================================================
class CompetencyAssessment(Base):
    """人员能力评估记录表（操作人员）（BG-KS-PX-808）。"""

    __tablename__ = "competency_assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, default=None)
    name: Mapped[str] = mapped_column(String(100), index=True, default="")  # 姓名
    department: Mapped[str] = mapped_column(String(50), default="生化免疫组")  # 所在部门
    post: Mapped[str] = mapped_column(String(50), default="")  # 岗位
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 年份

    # 20 个评分项：{项名: 得分(整数)}；合计 100 分（职业道德25+专业技术50+员工表现15+业绩10）
    scores_json: Mapped[str] = mapped_column(Text, default="{}")
    # 评估依据：{ 项名: { method, evidence, ref_id, assessor, date } }
    # method 枚举：observation / blind_sample / internal_comparison / pt_eqa / data_analysis
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    total: Mapped[int] = mapped_column(Integer, default=0)  # 总分
    conclusion: Mapped[str] = mapped_column(String(20), default="")  # 合格(≥80)/不合格
    assessor: Mapped[str] = mapped_column(String(100), default="")  # 评估人
    authorizer: Mapped[str] = mapped_column(String(100), default="")  # 授权人
    assess_date: Mapped[str] = mapped_column(String(20), default="")  # 评估日期
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PersonnelComparison(Base):
    """人员比对记录表（BG-SM-CZ-023）。与 interlab（室间比对）区分，此为组内人员比对。"""

    __tablename__ = "personnel_comparison"

    id: Mapped[int] = mapped_column(primary_key=True)
    department: Mapped[str] = mapped_column(String(50), default="检验科")  # 科室
    specialty_group: Mapped[str] = mapped_column(String(50), default="生免组")  # 专业组
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)
    project: Mapped[str] = mapped_column(String(200), default="")  # 比对项目
    method: Mapped[str] = mapped_column(String(200), default="")  # 方法
    reagent: Mapped[str] = mapped_column(String(200), default="")  # 试剂
    reagent_batch: Mapped[str] = mapped_column(String(100), default="")  # 试剂批号
    reagent_expire: Mapped[str] = mapped_column(String(20), default="")  # 试剂有效期
    test_date: Mapped[str] = mapped_column(String(20), default="")  # 检测日期
    sample_nos: Mapped[str] = mapped_column(Text, default="[]")  # 样本编号列表
    results_json: Mapped[str] = mapped_column(Text, default="[]")  # [{sample, lab_value, compare_value, bias, conclusion}]
    concordance: Mapped[str] = mapped_column(String(50), default="")  # 一致性结论（可接受/不可接受）
    summary: Mapped[str] = mapped_column(Text, default="")  # 结果分析与总结
    operator: Mapped[str] = mapped_column(String(100), default="")
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =========================================================================
# D/E/F. 组内培训 / 艾梅乙培训（BG-KS-PX-804 检验科培训记录表）
# =========================================================================
class TrainingPlan(Base):
    """年度培训计划。"""

    __tablename__ = "training_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)
    title: Mapped[str] = mapped_column(String(200), default="")  # 计划标题（如"2026年度生免组培训计划"）
    items_json: Mapped[str] = mapped_column(Text, default="[]")  # [{item, goal, trainer, expected_date, remark}]
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrainingSession(Base):
    """每次培训记录（BG-KS-PX-804）。课件/通知/考题/效果评价以 education_attachments 留存。"""

    __tablename__ = "training_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, default=None)
    name: Mapped[str] = mapped_column(String(300), index=True, default="")  # 培训名称
    teacher: Mapped[str] = mapped_column(String(100), default="")  # 培训老师
    target: Mapped[str] = mapped_column(String(300), default="")  # 培训对象
    train_time: Mapped[str] = mapped_column(String(50), default="")  # 时间
    location: Mapped[str] = mapped_column(String(200), default="")  # 地点
    content: Mapped[str] = mapped_column(Text, default="")  # 培训内容
    effect_eval: Mapped[str] = mapped_column(Text, default="")  # 培训效果及评价
    tag: Mapped[str] = mapped_column(String(50), default="组内培训")  # 组内培训 / 艾梅乙 / 其它
    sign_in_attachment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)  # 签到表扫描件附件 id
    sign_in_header: Mapped[str] = mapped_column(Text, default="{}")  # 打印空白签到表表头 {name,teacher,time,location}
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =========================================================================
# E. 实习/进修带教（BG-SM-PX-003 / BG-SM-PX-004，依据 SM-SOP-025）
# =========================================================================
class InternshipMentor(Base):
    """实习生培训大纲及带教教师评价表（BG-SM-PX-003）。"""

    __tablename__ = "internship_mentor"

    id: Mapped[int] = mapped_column(primary_key=True)
    intern_name: Mapped[str] = mapped_column(String(100), index=True, default="")  # 实习生/进修生姓名
    intern_type: Mapped[str] = mapped_column(String(20), default="实习")  # 实习 / 进修
    sop_ref: Mapped[str] = mapped_column(String(50), default="SM-SOP-025")  # 依据 SOP
    # 大纲要求及带教评价：[{seq, requirement, mastery, teacher, score(1-5), evaluator, date}]
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InternshipScore(Base):
    """实习生实操考核成绩单（BG-SM-PX-004）。"""

    __tablename__ = "internship_score"

    id: Mapped[int] = mapped_column(primary_key=True)
    intern_name: Mapped[str] = mapped_column(String(100), index=True, default="")  # 实习生/进修生姓名
    intern_type: Mapped[str] = mapped_column(String(20), default="实习")
    date: Mapped[str] = mapped_column(String(20), default="")  # 考核日期
    # 实操考核科目：[{subject, score_value(分值), teacher, score(成绩)}]
    subjects_json: Mapped[str] = mapped_column(Text, default="[]")
    overall_comment: Mapped[str] = mapped_column(Text, default="")  # 总体评价
    group_leader: Mapped[str] = mapped_column(String(100), default="")  # 组长签字
    sign_date: Mapped[str] = mapped_column(String(20), default="")  # 日期
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =========================================================================
# 附件（复刻 comparison_attachments 模式）
# =========================================================================
class EducationAttachment(Base):
    """人员继教模块附件：照片、签到扫描件、课件、通知、考题、效果评价等。

    owner_type 区分归属（personnel/new_employee/cert_auth/competency/comparison/
    training_session/intern_mentor/intern_score/ai_mei_yi），owner_id 为对应记录 id，
    kind 区分用途（photo/sign_in/courseware/notice/exam/effect_eval/other）。
    文件字节优先落 COS，失败回退 MySQL LONGBLOB。
    """

    __tablename__ = "education_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(40), index=True, default="")  # 归属类型
    owner_id: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 归属记录 id
    kind: Mapped[str] = mapped_column(String(40), default="other")  # 用途分类
    file_type: Mapped[str] = mapped_column(String(20), default="other")  # image / pdf / doc / other
    original_name: Mapped[str] = mapped_column(String(300), default="")
    stored_name: Mapped[str] = mapped_column(String(300), default="")
    rel_path: Mapped[str] = mapped_column(String(500), default="")
    data: Mapped[bytes | None] = mapped_column(LargeBinary(16 * 1024 * 1024), nullable=True)
    cloud_key: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
