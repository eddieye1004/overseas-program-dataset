// src/types.ts
// 与 data/schema.json 对齐的数据类型。只声明前端实际读到的字段，
// 未用到的字段一律用 [k: string]: unknown 兜住，避免 schema 扩展时类型报错。

export type EligibilityStatus = 'eligible' | 'not_eligible' | 'conditional' | 'unknown';
export type Region =
  | 'oceania'
  | 'asia'
  | 'europe'
  | 'north_america'
  | 'south_america'
  | 'africa'
  | 'global';
export type ProgramType =
  | 'working_holiday'
  | 'paid_internship'
  | 'internship_visa'
  | 'cultural_exchange'
  | 'short_term_work';
export type RiskLevel = 'info' | 'warning' | 'critical';
export type Lang = 'zh' | 'en';

/** 列表页用的轻量条目，来自 public/data/index.json（由 scripts/sync-data.mjs 生成） */
export interface ProgramIndexEntry {
  id: string;
  name: string;
  name_en: string;
  country: string;
  country_code: string;
  region: Region;
  program_type: ProgramType;
  visa_code: string | null;
  official_url: string;
  authority: string | null;
  summary: string;
  tags: string[];
  active: boolean;
  status: EligibilityStatus;
  age_min: number | null;
  age_max: number | null;
  /**
   * false 表示数据源写明「官方未公布年龄限制」，而不是「无上限」。
   * 两者在 schema 里都用 0–99 占位，只有 note 能把它们分开，
   * 所以由 sync-data.mjs 判好后带过来，前端不再重复猜。
   */
  age_verified: boolean;
  max_stay_months: number | null;
  education: string | null;
  /**
   * 学籍门槛，四档：
   *   required            必须提供在读证明、全程保持学籍（IAESTE、J-1）
   *   enrolled_or_recent  在读，或毕业 2 年内（德国 16e）
   *   unknown             官方未公布，无法判断（AIESEC）
   *   none                不要求学籍
   * education.minimum_level 分不出这件事——IAESTE、J-1、德国 16e 都写
   * bachelor_in_progress，实际要求却是三种。判据在 other_requirements 的
   * enrollment_proof 与 education.note，由 sync-data.mjs 判好带过来。
   */
  enrollment_scope: 'required' | 'enrolled_or_recent' | 'unknown' | 'none';
  language_required: boolean;
  funds_amount: number | null;
  funds_currency: string | null;
  risk_levels: RiskLevel[];
  /**
   * 配额四态，由 sync-data.mjs 从 timeline 透传。
   * 卡片上要能一眼看出「有上限 / 无上限 / 未公布 / 待核实」，
   * 而不是只看到一个可能为 null 的 quota 数字然后各自猜含义。
   */
  quota_status: QuotaStatus | null;
  /** 配额数字，仅 quota_status='capped' 时有值 */
  quota: number | null;
  /** 配额口径：annual=年度发放上限；concurrent=同时在册人数上限 */
  quota_basis: 'annual' | 'concurrent' | null;
  /**
   * 窗口日历（由 sync-data.mjs 从 timeline.schedule 透传）。
   * date_confidence 是「这个日期能不能信」的开关：
   *   confirmed 官方已公布 → 可以按此安排
   *   inferred  按往年规律推的 → 只能当参考，不许当官方日期展示
   *   unknown   无从判断 → 不显示日期
   */
  schedule_type: 'fixed_dates' | 'annual_cycle' | 'rolling' | 'no_window' | null;
  schedule_status: 'open' | 'closed' | 'upcoming' | 'always_open' | 'unknown' | null;
  date_confidence: 'confirmed' | 'inferred' | 'unknown' | null;
  /** 开放日，仅 date_confidence='confirmed' 时有值 */
  window_open: string | null;
  /** 截止日，仅 date_confidence='confirmed' 时有值 */
  window_close: string | null;
  /** 建议提前准备天数：提醒日 = 开放日 − 这个数 */
  lead_time_days: number | null;
  last_verified: string | null;
  /**
   * 复核状态，由 sync-data.mjs 按 data/review-policy.json 算好。
   * 前端不许自己拍一个「90 天」常数：仓库里的 data/FRESHNESS.md 用的是同一份策略，
   * 两处各写一份，页面说「0 条超期」而台账列着 3 条该核时没人能判断谁对。
   */
  review_state: 'overdue' | 'due_soon' | 'fresh' | 'unknown';
  /** 该记录的复核周期（天）：写死窗口的 90，其余 180 */
  review_interval: number;
  /** 下次该复核的日期（YYYY-MM-DD），缺核实日期时为 null */
  review_due: string | null;
  /** 距下次复核还有几天，已过期为负 */
  review_days_left: number | null;
  /** 来源条数（事实性元数据，列表卡片据此显示可信度） */
  source_count: number;
  /** 其中标为 primary 的条数 */
  source_primary: number;
}

export interface Money {
  local_amount?: number;
  currency?: string;
  cny_estimate?: number;
  note?: string;
}

export interface AgeRule {
  min?: number;
  max?: number;
  note?: string;
}

export interface EducationRule {
  minimum_level?: string;
  major_restriction?: string[];
  note?: string;
}

export interface LanguageTest {
  test: string;
  min_score?: number | null;
  validity_months?: number | null;
  note?: string;
}

export interface LanguageRule {
  required?: boolean;
  tests?: LanguageTest[];
  note?: string;
}

export interface FundsRule {
  required?: boolean;
  amount?: Money;
  note?: string;
}

export interface OtherRequirement {
  type: string;
  required?: boolean;
  note?: string;
}

export interface PassportTypes {
  mainland_china?: EligibilityStatus;
  hong_kong_china?: EligibilityStatus;
  taiwan_china?: EligibilityStatus;
  note?: string;
}

export interface Eligibility {
  passport_types?: PassportTypes;
  age?: AgeRule;
  education?: EducationRule;
  language?: LanguageRule;
  funds?: FundsRule;
  other_requirements?: OtherRequirement[];
}

export interface Window {
  year: number;
  status?: 'upcoming' | 'open' | 'closed' | 'unknown';
  opens_on?: string | null;
  closes_on?: string | null;
  note?: string;
}

export interface Fee {
  item: string;
  amount?: Money;
  refundable?: boolean | null;
  note?: string;
}

/**
 * 配额四态。空值不再兼职三种含义：null 既不表示「无配额」，也不表示「未公布」。
 * 与 data/schema.json 的 timeline.quota_status 一一对应。
 */
export type QuotaStatus = 'capped' | 'no_quota' | 'not_published' | 'unverified';

export interface Timeline {
  mechanism?: string;
  quota_status?: QuotaStatus;
  quota?: number | null;
  /** 配额口径：annual=年度发放上限；concurrent=同时在册人数上限 */
  quota_basis?: 'annual' | 'concurrent';
  /** 支撑该配额结论的官方来源 URL（必为本项目 sources[] 中的一条） */
  quota_source?: string;
  quota_note?: string;
  windows?: Window[];
  fees?: Fee[];
  processing_time?: string;
}

export interface DocumentItem {
  name: string;
  required?: boolean;
  note?: string;
  prepare_days?: number | null;
}

export interface Step {
  step_no: number;
  title: string;
  description?: string;
  duration?: string;
  official_link?: string | null;
}

export interface Risk {
  level: RiskLevel;
  description: string;
}

export interface Source {
  type: 'primary' | 'secondary';
  name: string;
  url: string;
  last_verified?: string;
}

export interface WorkConditions {
  max_stay_months?: number;
  max_same_employer_months?: number;
  max_study_months?: number;
  renewable?: boolean;
  renewal_condition?: string;
  restricted_occupations?: string[];
  note?: string;
}

export interface ProgramMeta {
  id: string;
  name: string;
  name_en?: string;
  country: string;
  country_code: string;
  region: Region;
  program_type: ProgramType;
  visa_code?: string;
  official_url: string;
  authority?: string;
  summary: string;
  tags?: string[];
  active?: boolean;
}

/** 单条程序完整档案，来自 public/data/programs.json */
export interface ProgramRecord {
  schema_version?: string;
  program: ProgramMeta;
  eligibility: Eligibility;
  timeline: Timeline;
  documents: DocumentItem[];
  steps: Step[];
  work_conditions?: WorkConditions;
  risks?: Risk[];
  sources?: Source[];
  last_verified?: string;
  verified_by?: string;
}
