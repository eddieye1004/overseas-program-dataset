// src/lib/verdict.ts
// 资格判定：五项画像 → 每个项目三态结论（能申 / 不能申 / 差什么 / 不可判）。
//
// 为什么这里一行正则都没有：
//   「note 里是不是写了『官方未按国籍设限』」「语言是不是『官方不设分数线』」
//   这两类判据全部在 scripts/match_readiness.py 里，算好落成 data/match-flags.json
//   （每维一个状态量 + 数字阈值）。前端只做类型层面的比较：够不够、差多少。
//
//   这不是洁癖。判据写两份的后果是：某天有人放宽了 Python 侧的正则，审计报告
//   说 41 条都能判，网页仍按旧口径把五条标成「不可判」，而没有任何测试会红。
//   现在两侧共用一组 (dim, kind, code)，smoke-test 拿 data/match-samples.json
//   逐条比对，任何一边改了口径另一边没跟上，构建就红。
//
// 纯函数、不碰 DOM、不读 localStorage：smoke-test 用 esbuild 单独打包来断言。

/** 五项输入。字段名与 data/match-samples.json 的 samples 一致。 */
export interface VerdictProfile {
  passport: 'mainland_china' | 'hong_kong_china' | 'taiwan_china';
  age: number;
  education: 'high_school' | 'vocational' | 'bachelor_in_progress' | 'bachelor_completed' | 'master';
  /** 雅思总分；没考过填 null —— 这与「考了但项目没登记分数线」是两件事 */
  ielts: number | null;
  budget_cny: number;
}

export const EMPTY_VERDICT_PROFILE: VerdictProfile = {
  passport: 'mainland_china',
  age: 22,
  education: 'bachelor_in_progress',
  ielts: null,
  budget_cny: 30000,
};

/** 一条项目六个维度的状态量，由 scripts/match_readiness.py --emit 产出。 */
export interface ProgramFlags {
  passport: {
    mainland_china: string;
    hong_kong_china: string;
    taiwan_china: string;
    note_open: boolean;
  };
  age: { min: number | null; max: number | null; unverified: boolean };
  education: {
    level: string | null;
    years_completed: number | null;
    /** note 另写的硬性年限门槛（结构化字段没有时靠它判不可判）——§4-2 */
    years_required: number | null;
    /** note 另写的「须在申请日前 N 年内完成学业/取得学位」毕业时限——P2-0 */
    recency_required: number | null;
    /** 原文把资格写成「须属于某几类参与人身份之一」，学历层级表达不了——P2-0 */
    category_required: boolean;
    /** 学位须在指定国家/名单内院校完成，画像不采集院校与毕业年份——§4-3/4/6 */
    place_constrained: boolean;
    /** 结构化层级比 note 严，原文写「由 Sponsor 判断」，以原文为准——§4-5 */
    by_sponsor: boolean;
  };
  language: {
    required: boolean;
    ielts_min: number | null;
    by_design: boolean;
    cefr: boolean;
    /** 官方不要求任何标准化考试（项目方测试/雇主面试把关），判 na 不判 silent */
    no_test: boolean;
  };
  funds: {
    required: boolean;
    cny_estimate: number | null;
    by_design: boolean;
    /** 门槛是「年收入」而非存款：不能与用户填的可动用资金相减 */
    income_basis: boolean;
    /** 金额是「每月」口径：必须乘停留月数再比，不能拿月额当总额——§4-1 */
    monthly: boolean;
    /** 停留期上限（月）。monthly 为真而它为 null 时，无法折算 → 不可判 */
    months: number | null;
    /** 金额被标注为「按同类口径沿用/归类推定」，不作达标判断 */
    amount_inferred: boolean;
  };
  /** 前置身份 / 在地要求；kind 与 Python 的 precondition_kind() 一一对应 */
  precondition: {
    kind:
      | 'local_status'
      | 'outside'
      | 'home_residence'
      | 'citizenship'
      | 'document'
      | 'unclassified'
      | null;
    /** 原文要求「岗位须预先落实」——材料/流程前提，与 kind 可同时成立——P2-0 */
    job_placement?: boolean;
  };
  window: {
    type: string | null;
    status: string | null;
    confidence: string | null;
    open: string | null;
    close: string | null;
  };
}

export interface MatchFlagsFile {
  rules_version: number;
  total: number;
  programs: Record<string, ProgramFlags>;
}

/** 判定口径的版本。改了判定逻辑，Python 的 RULES_VERSION 必须一起 +1。 */
export const RULES_VERSION = 5;

export type VerdictState = 'can' | 'cannot' | 'gap' | 'unknown';
export type DimKind = 'pass' | 'fail' | 'gap' | 'silent' | 'na';

export interface DimVerdict {
  dim: 'passport' | 'age' | 'education' | 'language' | 'funds' | 'precondition';
  kind: DimKind;
  /** 稳定标识，界面按它查文案；与 Python 侧同名同义 */
  code: string;
  /** 门槛（数字或档位），用于「差多少」 */
  need?: string;
  /** 本人实际条件，用于「你差多少」 */
  have?: string;
  /** 该维来自「官方未按国籍设限」这类明文推断，界面要标注 */
  inferred?: boolean;
}

export interface ProgramVerdict {
  state: VerdictState;
  dims: DimVerdict[];
}

/** 学历从低到高的次序。与 Python 的 EDU_RANK 必须完全一致。 */
const EDU_RANK: Record<string, number> = {
  high_school: 1,
  vocational: 2,
  bachelor_in_progress: 3,
  bachelor_completed: 4,
  master: 5,
  any: 0,
};

/**
 * 判一条项目。
 *
 * 状态优先级与 Python 的 judge() 完全一致，且**不可调换**：
 *   fail（有一条硬性不符）> gap（差一项，差多少可知）> silent（数据不表态）> can
 * 先判 fail 是因为「你超龄了」比「你还差雅思」更接近结论；反过来把 gap 排前面，
 * 一个超龄的人会在最上面先看到「先考个雅思」，考完照样不能申。
 */
export function judgeOne(flags: ProgramFlags, pr: VerdictProfile): ProgramVerdict {
  const dims: DimVerdict[] = [];

  // —— 护照 ——
  const pv = flags.passport[pr.passport];
  if (pv === 'not_eligible') {
    dims.push({ dim: 'passport', kind: 'fail', code: 'passport_no' });
  } else if (pv === 'eligible') {
    dims.push({ dim: 'passport', kind: 'pass', code: 'passport_ok' });
  } else if (pv === 'conditional') {
    dims.push({ dim: 'passport', kind: 'silent', code: 'passport_conditional' });
  } else if (pv === 'unknown') {
    dims.push({ dim: 'passport', kind: 'silent', code: 'passport_unknown' });
  } else if (flags.passport.note_open) {
    // 未单独登记护照，但官方明文不按国籍设限 —— 可判，且标注是推断
    dims.push({ dim: 'passport', kind: 'pass', code: 'passport_open', inferred: true });
  } else {
    dims.push({ dim: 'passport', kind: 'silent', code: 'passport_missing' });
  }

  // —— 年龄 ——
  const { min, max, unverified } = flags.age;
  if (unverified) {
    // 0–99 占位不能当「无限制」，那是替官方担保
    dims.push({ dim: 'age', kind: 'silent', code: 'age_unknown' });
  } else if (min === 0 && max === 99) {
    dims.push({ dim: 'age', kind: 'na', code: 'age_none' });
  } else if (min != null && pr.age < min) {
    dims.push({
      dim: 'age',
      kind: 'fail',
      code: 'age_low',
      need: `${min}-${max ?? '∞'} 岁`,
      have: `${pr.age} 岁`,
    });
  } else if (max != null && pr.age > max) {
    dims.push({
      dim: 'age',
      kind: 'fail',
      code: 'age_high',
      need: `${min ?? 0}-${max} 岁`,
      have: `${pr.age} 岁`,
    });
  } else {
    dims.push({ dim: 'age', kind: 'pass', code: 'age_ok' });
  }

  // —— 学历 ——
  const need = EDU_RANK[flags.education.level ?? 'any'] ?? 0;
  const have = EDU_RANK[pr.education] ?? 0;
  const yearsNeed = flags.education.years_required;
  if (need > 0 && flags.education.by_sponsor) {
    // 结构化 minimum_level 比原文更严：note 明说法规没规定学位层级、由 Sponsor
    // 判断。这时按层级判 fail 是替官方拒绝（§4-5），以原文为准判不可判。
    dims.push({ dim: 'education', kind: 'silent', code: 'edu_by_sponsor' });
  } else if (have < need) {
    dims.push({
      dim: 'education',
      kind: 'fail',
      code: 'edu_low',
      need: flags.education.level ?? 'any',
      have: pr.education,
    });
  } else if (yearsNeed) {
    // note 另写「不少于 N 年高等教育」且明说不足 N 年不满足（§4-2）。
    // 画像不采集学制，所以「本科毕业」不能直接判达标，也不能替三年制判失败。
    dims.push({
      dim: 'education',
      kind: 'silent',
      code: 'edu_years_unknown',
      need: `已完成 ${yearsNeed} 年高等教育`,
    });
  } else if (flags.education.years_completed && pr.education === 'bachelor_in_progress') {
    // 门槛只写了「本科」，但另要求已完成 N 年——在读的人他填的信息判不出来
    dims.push({
      dim: 'education',
      kind: 'silent',
      code: 'edu_years_unknown',
      need: `已完成 ${flags.education.years_completed} 年本科`,
    });
  } else if (flags.education.recency_required) {
    // note 另写「须在申请日前 N 年内完成学业或取得学位」（P2-0）。结构化 education
    // 只有层级与学制年数，没有毕业年份；画像也不采集，所以不能默认判达标。
    dims.push({
      dim: 'education',
      kind: 'silent',
      code: 'edu_recency_unknown',
      need: `申请日前 ${flags.education.recency_required} 年内完成学业或研究`,
    });
  } else if (flags.education.category_required) {
    // 原文把资格写成「须属于某几类参与人身份之一，且由 Sponsor 判断是否成立」
    // （P2-0）。结构化 minimum_level 是 any，判 edu_ok 等于说「学历层级任何值都
    // 达标」——那句话与「你是在读学生/在职青年/教师/有专门技能吗」不是一回事。
    // 与 §4-5 的 edu_by_sponsor 同口径：「由 Sponsor 判断」的事我们没有判据。
    dims.push({
      dim: 'education',
      kind: 'silent',
      code: 'edu_category_unknown',
    });
  } else if (flags.education.place_constrained) {
    // 学位须在指定国家/名单内院校完成（英国毕业生签证 / PGWP 的 DLI /
    // HPI 的认可名单）。画像不采集院校与毕业年份，判 pass 就是静默放行。
    dims.push({ dim: 'education', kind: 'silent', code: 'edu_place_unknown' });
  } else {
    dims.push({ dim: 'education', kind: 'pass', code: 'edu_ok' });
  }

  // —— 语言 ——
  const lang = flags.language;
  if (!lang.required) {
    dims.push({ dim: 'language', kind: 'na', code: 'lang_none' });
  } else if (lang.no_test) {
    // 官方要求英语沟通能力，但不要求任何标准化考试。判 na 而非 silent：
    // silent 会让用户以为自己还有未知的语言缺口，而官方已经写明不用考。
    dims.push({ dim: 'language', kind: 'na', code: 'lang_no_test' });
  } else if (lang.ielts_min != null) {
    if (pr.ielts == null) {
      dims.push({
        dim: 'language',
        kind: 'gap',
        code: 'lang_missing',
        need: `雅思 ${lang.ielts_min}`,
        have: '未提供',
      });
    } else if (pr.ielts < lang.ielts_min) {
      dims.push({
        dim: 'language',
        kind: 'gap',
        code: 'lang_low',
        need: `雅思 ${lang.ielts_min}`,
        have: `雅思 ${pr.ielts}`,
      });
    } else {
      dims.push({ dim: 'language', kind: 'pass', code: 'lang_ok' });
    }
  } else if (lang.by_design) {
    dims.push({ dim: 'language', kind: 'na', code: 'lang_by_design' });
  } else if (pr.ielts == null) {
    // 关键的不对称：没填成绩时，「这条要求语言、你没有」是确定的事实，
    // 不依赖仓内有没有登记分数线 —— 判 gap。反过来填了成绩而项目没登记
    // 分数线，才轮到 silent（说够不够都是替官方担保）。
    dims.push({
      dim: 'language',
      kind: 'gap',
      code: 'lang_missing',
      need: '语言成绩（项目要求）',
      have: '未提供',
    });
  } else if (lang.cefr) {
    dims.push({ dim: 'language', kind: 'silent', code: 'lang_cefr' });
  } else {
    dims.push({ dim: 'language', kind: 'silent', code: 'lang_no_score' });
  }

  // —— 预算 ——
  const funds = flags.funds;
  if (!funds.required) {
    dims.push({ dim: 'funds', kind: 'na', code: 'funds_none' });
  } else if (funds.cny_estimate == null) {
    dims.push(
      funds.by_design
        ? { dim: 'funds', kind: 'na', code: 'funds_by_design' }
        : { dim: 'funds', kind: 'silent', code: 'funds_unknown' },
    );
  } else if (funds.income_basis) {
    // 门槛是年收入，用户填的是可动用资金——两个口径不能相减。
    // 一个存款不足但有稳定远程收入的人其实符合，反之亦然，所以不给结论。
    dims.push({
      dim: 'funds',
      kind: 'silent',
      code: 'funds_income_basis',
      need: `年收入约 ${Math.round(funds.cny_estimate).toLocaleString('en-US')} 元`,
    });
  } else if (funds.amount_inferred) {
    // 数字在仓内被标注为「按同类口径沿用 / 归类推定」，不是本项目的独立规定
    dims.push({
      dim: 'funds',
      kind: 'silent',
      code: 'funds_amount_inferred',
      need: `约 ${Math.round(funds.cny_estimate).toLocaleString('en-US')} 元`,
    });
  } else if (funds.monthly && funds.months == null) {
    // 金额按「每月」计，但不知道要覆盖几个月 —— 既不能乘，也不能直接比。
    // 拿月额当总额比正是 §4-1 那个把「差什么」判成「能申」的错误。
    dims.push({
      dim: 'funds',
      kind: 'silent',
      code: 'funds_term_unknown',
      need: `每月约 ${Math.round(funds.cny_estimate).toLocaleString('en-US')} 元`,
    });
  } else if (funds.monthly && funds.months != null) {
    const total = funds.cny_estimate * funds.months;
    if (pr.budget_cny < total) {
      dims.push({
        dim: 'funds',
        kind: 'gap',
        code: 'funds_short',
        need: `约 ${Math.round(total).toLocaleString('en-US')} 元（每月 ${Math.round(
          funds.cny_estimate,
        ).toLocaleString('en-US')} × ${funds.months} 个月）`,
        have: `${pr.budget_cny.toLocaleString('en-US')} 元`,
      });
    } else {
      dims.push({ dim: 'funds', kind: 'pass', code: 'funds_ok' });
    }
  } else if (pr.budget_cny < funds.cny_estimate) {
    dims.push({
      dim: 'funds',
      kind: 'gap',
      code: 'funds_short',
      need: `约 ${Math.round(funds.cny_estimate).toLocaleString('en-US')} 元`,
      have: `${pr.budget_cny.toLocaleString('en-US')} 元`,
    });
  } else {
    dims.push({ dim: 'funds', kind: 'pass', code: 'funds_ok' });
  }

  // —— 前置身份 / 在地要求 ——
  // 这一段过去完全不存在：judge() 只读五处结构化字段，other_requirements 一个字
  // 没读，于是「只对已在英留学生开放」的毕业生签证被判成谁都能申（§4-3）。
  const pre = flags.precondition?.kind ?? null;
  if (pre === 'local_status') {
    dims.push({
      dim: 'precondition',
      kind: 'gap',
      code: 'pre_local_status',
      need: '先在该国持学生/居留身份并完成学业',
      have: '未采集该项经历',
    });
    // 同一件事在教育维已判 silent 的话，去掉教育维那条，避免两条重复缺口
    if (flags.education.place_constrained) {
      const i = dims.findIndex((d) => d.code === 'edu_place_unknown');
      if (i >= 0) dims.splice(i, 1);
    }
  } else if (pre === 'outside') {
    dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_outside_country' });
  } else if (pre === 'home_residence') {
    dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_home_residence' });
  } else if (pre === 'citizenship') {
    // 「须为参与国公民」是国籍条件，护照维已判同一件事，不另算缺口。
    dims.push({ dim: 'precondition', kind: 'na', code: 'pre_citizenship_basis' });
  } else if (pre === 'document') {
    // 「须持有效租约」是递交时自备的材料，不是身份前置。
    dims.push({ dim: 'precondition', kind: 'na', code: 'pre_document_basis' });
  } else if (pre === 'unclassified') {
    // 有必填的前置要求但原文类别没认出来 —— 不能落 pass，那是 §4-3 的错因。
    dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_unclassified' });
  }

  // 岗位前置（P2-0）：与上面的身份类别**不是** if/else 关系，两者可同时成立
  // （us-j1-camp-counselor 既是四类身份之一，又必须先落实营地岗位）。
  if (flags.precondition?.job_placement) {
    dims.push({
      dim: 'precondition',
      kind: 'gap',
      code: 'pre_job_placement',
      need: '预先落实的岗位（Sponsor 不得为未落实岗位者办理入境）',
      have: '未采集岗位落实情况',
    });
  }

  const kinds = new Set(dims.map((d) => d.kind));
  const state: VerdictState = kinds.has('fail')
    ? 'cannot'
    : kinds.has('gap')
      ? 'gap'
      : kinds.has('silent')
        ? 'unknown'
        : 'can';

  return { state, dims };
}

/** 批量判定。顺序沿用索引顺序，排序交给调用方（三态分组比分数更该按状态排）。 */
export function judgeAll(
  flags: MatchFlagsFile,
  ids: string[],
  pr: VerdictProfile,
): { id: string; verdict: ProgramVerdict }[] {
  return ids
    .filter((id) => flags.programs[id])
    .map((id) => ({ id, verdict: judgeOne(flags.programs[id], pr) }));
}

/** 三态的分组顺序：能申 → 差什么 → 不可判 → 不能申。
 *  不能申放最后不是因为它不重要，而是「先看还能做什么」比「先看不能做什么」
 *  对使用者更有用；不能申的那一组仍然完整列出原因。 */
export const STATE_ORDER: VerdictState[] = ['can', 'gap', 'unknown', 'cannot'];

export function countByState(rows: { verdict: ProgramVerdict }[]): Record<VerdictState, number> {
  const c: Record<VerdictState, number> = { can: 0, cannot: 0, gap: 0, unknown: 0 };
  for (const r of rows) c[r.verdict.state] += 1;
  return c;
}
