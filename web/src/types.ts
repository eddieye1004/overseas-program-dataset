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
  max_stay_months: number | null;
  education: string | null;
  language_required: boolean;
  funds_amount: number | null;
  funds_currency: string | null;
  risk_levels: RiskLevel[];
  last_verified: string | null;
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

export interface Timeline {
  mechanism?: string;
  quota?: number | null;
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
