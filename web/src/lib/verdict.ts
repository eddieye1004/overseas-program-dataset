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

/** 画像五项输入。字段名与 data/match-samples.json 的 samples 一致。 */
export interface VerdictProfile {
  passport: 'mainland_china' | 'hong_kong_china' | 'taiwan_china';
  age: number;
  education:
    | 'high_school'
    | 'vocational'
    | 'bachelor_in_progress'
    | 'bachelor_completed'
    | 'master'
    | 'doctorate';
  /** 雅思总分；没考过填 null —— 这与「考了但项目没登记分数线」是两件事 */
  ielts: number | null;
  budget_cny: number;
  /** 家属构成：none | children | partner | other。缺省 = 未知（不是「没有」） */
  dependents?: 'none' | 'children' | 'partner' | 'other' | null;
  /** 既往参加过本项目/同类项目：none | used。缺省 = 未知 */
  prior_participation?: 'none' | 'used' | null;
  /** 曾持过同类签证：none | used。缺省 = 未知 */
  prior_same_category_visa?: 'none' | 'used' | null;
  /** 在读 / 已毕业：enrolled | completed。缺省 = 未知 */
  enrollment_status?: 'enrolled' | 'completed' | null;
  /**
   * 现居地国家代码（ISO 3166-1 alpha-2，如 CN / TW / AU）。缺省 = 未知。
   *
   * 与 passport 不同：护照决定「你是谁」，现居地决定「你人在哪」。有些项目要求
   * 递交时人必须在该国境内（`you must be in the UK when you apply`），那条要求
   * 判的是后者——一个人拿着中国护照在英国读完书，护照条件与在地条件是两项。
   *
   * 取值必须与项目的 country_code 同一套代码体系，否则比较不成立（判分只会
   * 变成「永远不相等」）。格式不对一律当未知，绝不猜测。
   */
  current_location?: string | null;
  /**
   * 与目标岗位相关的**境外**工作经验年限（P3）。缺省 = 未知。
   *
   * 为什么 `0` 与 `null` 必须分开：J-1 Trainee 的两条路径分别要「学位 + 1 年」
   * 与「无学位 + 5 年」。一个在校生填 0 是**已知事实**（→ 判 fail），
   * 没填是「没问过」（→ 判 silent）。把 0 当成缺省值会把「不能申」说成
   * 「不可判」，反过来把 null 当 0 就是替官方拒绝。
   */
  work_experience_years?: number | null;
  /** 距最近一次毕业多少个月（P3）。缺省 = 未知 */
  months_since_graduation?: number | null;
  /** 在最高学历里已实际就读多少个月（P3）。缺省 = 未知 */
  study_months?: number | null;
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
  /**
   * 项目所在国（ISO 3166-1 alpha-2）。P1d 起 `inside` 那条在地要求要用它：
   * 与画像的 `current_location` 相等 → 人已在境内。缺省（老产物）时按「不知道
   * 是哪个国家」处理，落 silent，不猜。
   */
  country_code?: string | null;
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
    /**
     * 教育资格的**并列路径**（P3）。任一成立即达标。
     *
     * 这是本单的核心数据结构：`level` 那个单值表达不了「学位 或 经验」与
     * 「在读 或 毕业后 N 个月内」，把它们硬压进一个层级序就是原先那批假
     * pass / 假 cannot 的根因。月数由 Python 侧算好再传，前端不再做单位换算。
     */
    paths: EducationPath[] | null;
    /** 项目侧就读时长门槛（月，已折算）。与 duration_required 配合判 silent */
    min_duration_months: number | null;
    /** 原文是否提出了就读时长要求（true 而 min_duration_months 为 null = 有要求无数字） */
    duration_required: boolean;
    /** note 另写的「须在申请日前 N 年内完成学业/取得学位」毕业时限——P2-0 */
    recency_required: number | null;
    /** 原文把资格写成「须属于某几类参与人身份之一」，学历层级表达不了——P2-0 */
    category_required: boolean;
    /** 原文要求「学历/职业资格须被主管机构认定」（另含积分门槛）——P2-0 */
    credential_required: string | null;
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
  /** 前置身份 / 在地要求；kind 与 Python 的 precondition_kinds() 一一对应 */
  precondition: {
    /**
     * 两族里最靠前的类别（身份族优先）。保留单值是为了向后兼容；
     * **判定必须读 `kinds`**，否则一个项目同时有身份条与在地条时只会画一条。
     */
    kind:
      | 'local_status'
      | 'inside'
      | 'outside'
      | 'home_residence'
      | 'citizenship'
      | 'document'
      | 'unclassified'
      | null;
    /**
     * P1c：全部前置类别，身份族在前、在地族在后。与 Python `precondition_kinds()`
     * 的顺序逐一对应（smoke-test 比的是 (dim,kind,code) 整串，顺序错一位也会红）。
     * 缺省（老产物）时退回 `kind` 单值。
     */
    kinds?: Array<
      | 'local_status'
      | 'inside'
      | 'outside'
      | 'home_residence'
      | 'citizenship'
      | 'document'
      | 'unclassified'
    >;
    /** 原文要求「岗位须预先落实」——材料/流程前提，与 kind 可同时成立——P2-0 */
    job_placement?: boolean;
    /**
     * P4 §3：岗位前置属四种表述里的哪一种。前端按它取 need 文案，
     * 与 Python 的 `JOB_PLACEMENT_NEED` 一一对应；缺省时退回 `camp`
     * （最严的一份法规原文），但 smoke-test 会比对两侧 need 整串，串台立刻红。
     */
    job_placement_flavor?: 'camp' | 'sponsor_ds2019' | 'summer_job' | 'ds7002' | null;
    /**
     * P4 §2：`government_support_letter` 的语义分型 + 是否必填。
     *
     * type 名不表示同一种东西（政府支持信 / 官方求职登记 / 学历认证 / 院校推荐 /
     * Sponsor 的 DS-2019），所以前端与审计都按 kind 读、不按 type 名猜。
     * 没有该 type 的条目时为 null（不是空对象）。
     */
    government_support_letter?: {
      kind:
        | 'sponsorship'
        | 'official_registration'
        | 'credential_check'
        | 'institutional_recommendation'
        | 'government_letter'
        | 'unclassified';
      required: boolean;
    } | null;
    /** 原文要求「具体雇主的合格聘用」（雇主担保类：offer + ≥80% + 岗位对得上）——P2-0 */
    employer_offer?: boolean;
    /** P1b-2：家属 / 签证史 / 学籍三个家族的 typed 值（项目侧布尔，画像侧由前端重演） */
    p1b2?: {
      forbid_child: boolean;
      forbid_other: boolean;
      cannot_work: boolean;
      separate: boolean;
      allowed: boolean;
      declaration: boolean;
      participation: boolean;
      same_category_visa: boolean;
      specific_visa_required: boolean;
      enrollment: boolean;
      degree_completed: boolean;
      either: boolean;
      scoring_input: boolean;
      /**
       * 这条项目**读哪些画像字段**（2026-11-20 表单关键字段补齐）。
       *
       * 与上方布尔量的分工：上方是「为什么读」（语义，给人看），
       * 这一项是「读不读」（事实，给门用）。门只读这一项，不按上方自己推——
       * 同一条规则写两遍必然漂，而「门悄悄关掉」在界面上看起来完全正常。
       *
       * 由引擎实测得出（profile_readers()），不是手写的清单：
       * 把字段从 None 换成真值，看 (dim,kind,code) 整串变不变。
       *
       * 可选：老产物没有这一项，readersOf() 会退化成「全不读」= 门全关，
       * 属于安全方向（宁可不问，也不凭猜出来的规则去问）。
       */
      reads?: Record<string, boolean>;
    };
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

/**
 * 现居地代码的合法化：只接受两位大写字母（ISO 3166-1 alpha-2），其余返回 null。
 *
 * 与 Python 的 `current_location_of()` **同一套严格度**，这不是洁癖：
 * 在地要求判错方向的代价是把能申的人判成不能申（或反之），而这种错误在界面上
 * 看起来完全正常。空串、小写 `cn`、`CHINA`、中文「中国」一律当未知，让用户
 * 看到「无法判定」，而不是替他把值猜成某个国家。
 */
function normalizeLocation(v: string | null | undefined): string | null {
  if (typeof v !== 'string') return null;
  const s = v.trim();
  return /^[A-Z]{2}$/.test(s) ? s : null;
}

/** 判定口径的版本。改了判定逻辑，Python 的 RULES_VERSION 必须一起 +1。 */
export const RULES_VERSION = 12;

/**
 * 岗位前置的四种表述（P4 §3）。与 Python 的 `JOB_PLACEMENT_NEED` **逐字节一致**：
 * smoke-test 比的是 `(dim,kind,code)` 整串，need 文本不进快照，所以两侧串台
 * 只能靠「同一张表 + 同一条键」保证。改一侧必改另一侧。
 *
 * 为什么必须分四种：四个 J-1 子类的「落实」链条根本不同——营地是「先有营地岗位
 * 才准入境」，研究学者是「先有接收机构与 DS-2019」，SWT 是「Sponsor 落实暑期岗位
 * + 雇主面试」，intern/trainee 是「DS-7002 三方签字文件链」。用营地文案去讲研究
 * 学者，等于修一处漏网、引入一处错文案（Muse 2026-11-14 裁决 2）。
 */
export const JOB_PLACEMENT_NEED: Record<string, string> = {
  camp: '预先落实的营地岗位（Sponsor 不得为未落实营地岗位者办理入境）',
  sponsor_ds2019:
    '国务院指定 Sponsor 出具的 DS-2019（须先拿到接收机构的邀请与 Sponsorship，个人无法自行申请）',
  summer_job:
    'Sponsor 已落实并审查过的暑期岗位 + 通过美方雇主面试拿到的 Job Offer（美国国务院授权 Sponsor 统一办理，无法自主申请）',
  ds7002:
    '雇主签署的 DS-7002 培训/实习安置计划（申请人、雇主、Sponsor 三方签字后，Sponsor 才签发 DS-2019）',
};

/**
 * 护照 → 护照所属国家/地区代码。与 Python 的 `PASSPORT_COUNTRY` 逐条一致。
 *
 * **只登记库里真有的三类**（P1e）：`home_residence`（须常驻护照所属地区）判的是
 * 「现居 == 护照所属地」，两边用同一套代码，比较就是字符串相等。表里没有的护照
 * 返回 undefined → 判 silent，而不是猜一个国家去判 fail。
 *
 * 与 `normalizeLocation` 分开：那个把用户输入合法化（接受任意两位大写），
 * 这个只查表（护照是受枚举约束的存储值，不做格式宽容）。
 */
const PASSPORT_COUNTRY: Record<VerdictProfile['passport'], string> = {
  mainland_china: 'CN',
  hong_kong_china: 'HK',
  taiwan_china: 'TW',
};

/** 护照的中文名，用于 `home_residence` 的 need 文案（与 Python 的 `PASSPORT_ZH` 一致）。 */
const PASSPORT_ZH_LOCAL: Record<string, string> = {
  mainland_china: '大陆护照',
  hong_kong_china: '香港护照',
  taiwan_china: '台湾护照',
};

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

/** 一条教育资格路径（P3）。与 Python 的 `edu_paths()` 产出一一对应。 */
export interface EducationPath {
  /** 该路径要求的最低学历层级；`any` = 不限 */
  level: string;
  /** 在读状态要求：enrolled | graduated；null = 不限 */
  enrollment: 'enrolled' | 'graduated' | null;
  /** 毕业后多少个月内仍算符合；null = 无此限 */
  graduated_within_months: number | null;
  /** 相关工作经验年限；null = 不要求 */
  min_years_experience: number | null;
  /** 经验须在何处取得：outside | any | null */
  experience_region: 'outside' | 'any' | null;
  /** 就读时长下限（月，已折算）；null = 不要求 */
  min_months: number | null;
}

/**
 * 学历层级是否满足。**显式集合，不是数字比较**（P3）。
 *
 * 原先这里是一张 `EDU_RANK` 数字表 + `have < need`。那个写法有两个错：
 *   ① 「在读」是状态不是层级：`bachelor_completed(4) > bachelor_in_progress(3)`，
 *      于是已毕业的人在「必须现在在读」的项目上反而更够格（假 pass）；
 *   ② 层级序回答不了「无学历 + 5 年经验也算合格」（假 cannot）。
 * 现在层级只是路径里的**一个谓词**，用集合表达「持有 have 是否满足 need」。
 *
 * 与 Python 的 `EDU_LEVEL_QUALIFIES` 必须逐项一致，否则 smoke-test 会红。
 */
const LEVEL_QUALIFIES: Record<string, readonly string[]> = {
  any: ['high_school', 'vocational', 'bachelor_in_progress', 'bachelor_completed', 'master', 'doctorate'],
  high_school: ['high_school', 'vocational', 'bachelor_in_progress', 'bachelor_completed', 'master', 'doctorate'],
  vocational: ['vocational', 'bachelor_in_progress', 'bachelor_completed', 'master', 'doctorate'],
  bachelor_in_progress: ['bachelor_in_progress', 'bachelor_completed', 'master', 'doctorate'],
  bachelor_completed: ['bachelor_completed', 'master', 'doctorate'],
  master: ['master', 'doctorate'],
  doctorate: ['doctorate'],
};

function levelOk(need: string | null | undefined, have: string | null | undefined): boolean {
  const allowed = LEVEL_QUALIFIES[need ?? 'any'];
  if (!allowed) return false; // 不认识的门槛值不构成达标证据
  return have != null && allowed.includes(have);
}

/** 单条路径的三态判定结果。与 Python `edu_path_eval()` 的字段同名同义。 */
interface PathEval {
  verdict: 'pass' | 'fail' | 'unknown';
  need: string;
  have: string;
  blocked: string[];
  failed: string[];
}

/**
 * 判一条教育路径。与 Python `edu_path_eval()` **逐条镜像**。
 *
 * 三态而不是布尔：路径里某个谓词缺数据时，这条路径既不能算成立也不能算不成立。
 * 把 unknown 折成 fail 会让「数据没登记」变成「你不能申」；折成 pass 就是本单
 * 要消灭的假 pass。`blocked` / `failed` 记录**是哪一类谓词**，调用方据此选 code。
 */
function evalPath(path: EducationPath, pr: VerdictProfile): PathEval {
  const need: string[] = [];
  const have: string[] = [];
  const statuses: string[] = [];
  const blocked: string[] = [];
  const failed: string[] = [];

  const level = path.level ?? 'any';
  const hasLevel = level !== 'any';
  if (hasLevel) {
    need.push(`学历 ${level}`);
    have.push(`你的学历 ${pr.education}`);
  }

  if (path.enrollment === 'enrolled') need.push('当前在读');
  else if (path.enrollment === 'graduated') need.push('已毕业');

  const minExp = path.min_years_experience;
  if (minExp != null && minExp > 0) {
    const where = path.experience_region === 'outside' ? '境外相关' : '相关';
    need.push(`${where}工作经验 ${minExp} 年`);
  }

  const minMonths = path.min_months;
  if (minMonths != null && minMonths > 0) need.push(`就读时长 ≥ ${minMonths} 个月`);

  // ① 层级
  if (hasLevel) {
    if (!pr.education) {
      statuses.push('unknown');
      blocked.push('level');
    } else if (!levelOk(level, pr.education)) {
      statuses.push('fail');
      failed.push('level');
    }
  }

  // ② 在读状态
  if (path.enrollment) {
    const actual = pr.enrollment_status ?? null;
    if (actual == null) {
      statuses.push('unknown');
      blocked.push('enrollment');
    } else if (path.enrollment === 'enrolled') {
      if (actual === 'enrolled') statuses.push('pass');
      else {
        statuses.push('fail');
        failed.push('enrollment');
      }
    } else if (actual === 'completed') {
      statuses.push('pass');
    } else {
      statuses.push('fail');
      failed.push('enrollment');
    }
  }

  // ③ 毕业宽限期（intern 的「毕业不超过 12 个月」）
  const within = path.graduated_within_months;
  if (within != null && within > 0) {
    const actual = pr.enrollment_status ?? null;
    const monthsSince = pr.months_since_graduation ?? null;
    if (actual === 'enrolled') {
      statuses.push('pass'); // 在读走的是另一条腿，不受宽限期约束
    } else if (monthsSince != null) {
      if (monthsSince <= within) statuses.push('pass');
      else {
        statuses.push('fail');
        failed.push('graduation_recency');
      }
      have.push(`你毕业 ${monthsSince} 个月`);
    } else {
      statuses.push('unknown');
      blocked.push('graduation_recency');
    }
  }

  // ④ 经验年限
  if (minExp != null && minExp > 0) {
    const years = pr.work_experience_years ?? null;
    if (years != null) {
      if (years >= minExp) statuses.push('pass');
      else {
        statuses.push('fail');
        failed.push('experience');
      }
      have.push(`你的经验 ${years} 年`);
    } else {
      statuses.push('unknown');
      blocked.push('experience');
    }
  }

  // ⑤ 就读时长
  if (minMonths != null && minMonths > 0) {
    const done = pr.study_months ?? null;
    if (done != null) {
      if (done >= minMonths) statuses.push('pass');
      else {
        statuses.push('fail');
        failed.push('duration');
      }
      have.push(`你已读 ${done} 个月`);
    } else {
      statuses.push('unknown');
      blocked.push('duration');
    }
  }

  let verdict: PathEval['verdict'];
  if (statuses.includes('fail')) verdict = 'fail';
  else if (statuses.includes('unknown')) verdict = 'unknown';
  else verdict = 'pass';

  return {
    verdict,
    need: need.join(' 且 ') || '无额外条件',
    have: have.join(' / ') || '已满足',
    blocked,
    failed,
  };
}

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

  // —— 学历（P3 路径化）——
  //
  // 判定顺序与 Python `judge()` 的学历块逐条镜像。与旧代码的关键差别：
  // 旧代码第一条就是 `have < need → fail`，于是在有并列路径的项目上必然判死
  // （J-1 Trainee「无学位 + 5 年经验」被判 edu_low 的那个假 cannot）。
  // 现在先按路径算，最后才决定 fail / silent / pass。
  const edu = flags.education;
  const paths: EducationPath[] =
    edu.paths && edu.paths.length > 0
      ? edu.paths
      : [
          {
            level: edu.level ?? 'any',
            enrollment: null,
            graduated_within_months: null,
            min_years_experience: null,
            experience_region: null,
            min_months: null,
          },
        ];
  const evals = paths.map((path) => evalPath(path, pr));
  const anyPass = evals.some((e) => e.verdict === "pass");
  const anyUnknown = evals.some((e) => e.verdict === "unknown");
  const combinedNeed = evals.map((e) => e.need).join(" 或 ");

  if (edu.by_sponsor && paths.some((p) => (p.level ?? "any") !== "any")) {
    // 结构化字段比原文更严：note 明说「法规未规定学位层级、由 Sponsor 判断」。
    // 判在最前，因为它是「结构化字段不该被采信」，与路径成不成立无关（§4-5）。
    dims.push({ dim: "education", kind: "silent", code: "edu_by_sponsor" });
  } else if (!anyPass && !anyUnknown) {
    // 全部路径都不成立 → 唯一该判 fail 的情形。code 按**共同失败的谓词**选：
    // 「你毕业了」与「你学历低了」是两件事，共用一个 code 会让修法无从下手。
    const failed = new Set<string>();
    for (const e of evals) for (const f of e.failed) failed.add(f);
    const notEnrolled =
      !failed.has("level") &&
      (failed.has("enrollment") || failed.has("graduation_recency"));
    dims.push({
      dim: "education",
      kind: "fail",
      code: notEnrolled ? "edu_not_enrolled" : "edu_low",
      need: combinedNeed,
      have: notEnrolled ? (pr.enrollment_status ?? "") : pr.education,
    });
  } else if (anyPass && edu.duration_required) {
    // 路径成立，但另有就读时长门槛。时长是硬条件：缺数字就不可判，不许 pass。
    const durNeed = edu.min_duration_months;
    const durHave = pr.study_months;
    if (durNeed == null) {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_duration_unknown",
        need: "就读时长（原文有要求，仓内无数字）",
      });
    } else if (durHave == null || durHave === undefined) {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_duration_unknown",
        need: `就读 ≥ ${durNeed} 个月`,
      });
    } else if (durHave >= durNeed) {
      dims.push({ dim: "education", kind: "pass", code: "edu_ok" });
    } else {
      dims.push({
        dim: "education",
        kind: "fail",
        code: "edu_duration_short",
        need: `就读 ≥ ${durNeed} 个月`,
        have: `${durHave} 个月`,
      });
    }
  } else if (anyPass && edu.recency_required) {
    // note 另写「须在申请日前 N 年内完成学业」（P2-0）。毕业时间未采集，
    // 不能默认「层级到了 = 达标」。
    dims.push({
      dim: "education",
      kind: "silent",
      code: "edu_recency_unknown",
      need: `申请日前 ${edu.recency_required} 年内完成学业或研究`,
    });
  } else if (anyUnknown) {
    // 判不了，但要分清缺的是哪一类谓词 —— 不同补法对应不同 code。
    const blocked = new Set<string>();
    for (const e of evals) for (const b of e.blocked) blocked.add(b);
    if (blocked.has("duration")) {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_duration_unknown",
        need: combinedNeed,
      });
    } else if (blocked.has("enrollment") || blocked.has("graduation_recency")) {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_enrollment_unknown",
        need: combinedNeed,
      });
    } else if (blocked.has("experience")) {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_experience_unknown",
        need: combinedNeed,
      });
    } else {
      dims.push({
        dim: "education",
        kind: "silent",
        code: "edu_years_unknown",
        need: combinedNeed,
      });
    }
  } else if (edu.years_completed && pr.education === "bachelor_in_progress") {
    dims.push({
      dim: "education",
      kind: "silent",
      code: "edu_years_unknown",
      need: `已完成 ${edu.years_completed} 年本科`,
    });
  } else if (edu.category_required) {
    // 原文把资格写成「须属于某几类参与人身份之一，且由 Sponsor 判断是否成立」
    // （P2-0）。判 edu_ok 等于说「学历层级任何值都达标」，与原文不是一回事。
    dims.push({
      dim: "education",
      kind: "silent",
      code: "edu_category_unknown",
    });
  } else if (edu.credential_required) {
    // 「资格须被主管机构认定 + 积分达 N 分」（P2-0）。认定结论与积分总分都未采集，
    // 判 pass 就是静默放行。
    dims.push({
      dim: "education",
      kind: "silent",
      code: "edu_credential_unknown",
      need: edu.credential_required,
    });
  } else if (edu.place_constrained) {
    // 学位须在指定国家/名单内院校完成。画像不采集院校与毕业年份。
    dims.push({ dim: "education", kind: "silent", code: "edu_place_unknown" });
  } else {
    dims.push({ dim: "education", kind: "pass", code: "edu_ok" });
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
  //
  // P1c：身份族与在地族**各出各的结论**。过去两者共用一条 if/else 链，在地那条
  // 只能靠同一链上的 local_status 出口发声（借接），而 us-f1-opt 同时有两条要求，
  // 地图上只会画出第一条。现在按 kinds 顺序逐条判，与 Python 的 for 循环镜像。
  const preKinds = flags.precondition?.kinds ?? (flags.precondition?.kind ? [flags.precondition.kind] : []);
  for (const pre of preKinds) {
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
    } else if (pre === 'inside') {
      // 在地：与 outside 互为镜像，不并进 outside（方向相反的条件共用一个 code
      // 会让「必须人在境外」与「必须人在境内」在报告里长得一模一样）。
      //
      // P1d 接地：与 Python 的 inside 分支逐条镜像。
      //   现居 == 项目国 → pass（人已在境内，这条不构成障碍）
      //   有值但不同     → fail（→ cannot）
      //   缺失/非法      → silent（缺省绝不判 pass）
      // 三个 code 各管一件事：`pre_inside_country` 仍是「画像不采集现居地」的原码。
      const loc = normalizeLocation(pr.current_location);
      const cc = flags.country_code ?? null;
      if (loc == null || cc == null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_inside_country' });
      } else if (loc === cc) {
        dims.push({
          dim: 'precondition',
          kind: 'pass',
          code: 'pre_inside_country_ok',
          need: `递交时人在 ${cc} 境内`,
          have: `你现在在 ${loc}`,
        });
      } else {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_inside_country_no',
          need: `递交时须身在 ${cc} 境内`,
          have: `你现在在 ${loc}`,
        });
      }
    } else if (pre === 'outside') {
      // 在地的镜像方向（P1e 接地）：递交时人须在该国**境外**。
      // 判法是 inside 的镜像，比的是同一个 current_location 与同一个 country_code：
      //   现居 != 项目国 → pass（人在境外，这条不构成障碍）
      //   现居 == 项目国 → fail（申请本身无效）
      //   缺失/非法/项目国缺失 → silent（原码，绝不默认 pass）
      //
      // 为什么不能复用 inside 的 code：方向相反的两条要求共用一个 code 会让
      // 「必须人在境外」与「必须人在境内」在报告里长得一模一样（batch8 立项理由）。
      const loc = normalizeLocation(pr.current_location);
      const cc = flags.country_code ?? null;
      if (loc == null || cc == null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_outside_country' });
      } else if (loc !== cc) {
        dims.push({
          dim: 'precondition',
          kind: 'pass',
          code: 'pre_outside_country_ok',
          need: `递交时人须在 ${cc} 境外`,
          have: `你现在在 ${loc}`,
        });
      } else {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_outside_country_no',
          need: `递交时人须在 ${cc} 境外`,
          have: `你现在在 ${loc}`,
        });
      }
    } else if (pre === 'home_residence') {
      // 常驻护照所属地区（P1e 接地）。**判据是「现居 == 护照所属地」，
      // 不是「现居 == 项目国」**——JP 项目在 JP，但要求的是台/港籍住在台/港。
      // 方向搞反会把全部目标人群判错（原文从未要求申请人住在项目国）。
      // 两条之一拿不到就 silent，不硬凑。
      const loc = normalizeLocation(pr.current_location);
      const home = PASSPORT_COUNTRY[pr.passport] ?? null;
      if (loc == null || home == null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_home_residence' });
      } else if (loc === home) {
        dims.push({
          dim: 'precondition',
          kind: 'pass',
          code: 'pre_home_residence_ok',
          need: `常驻护照所属地区（${PASSPORT_ZH_LOCAL[pr.passport] ?? home} → ${home}）`,
          have: `你现在在 ${loc}`,
        });
      } else {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_home_residence_no',
          need: `常驻护照所属地区（${PASSPORT_ZH_LOCAL[pr.passport] ?? home} → ${home}）`,
          have: `你现在在 ${loc}`,
        });
      }
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
  }

  // 岗位前置（P2-0）：与上面的身份类别**不是** if/else 关系，两者可同时成立
  // （us-j1-camp-counselor 既是四类身份之一，又必须先落实营地岗位）。
  //
  // P4 §3：need 文案按项目取四种表述，与 Python 的 JOB_PLACEMENT_NEED 逐字节一致。
  // 改前这里硬编码营地那条法规原文，研究学者/学徒页会显示一句讲营地的话——
  // 「修了一处漏网、引入一处错文案」（batch2 §4.2④ / batch4 §219 / batch9b §1.2②）。
  if (flags.precondition?.job_placement) {
    const flavor = flags.precondition.job_placement_flavor ?? null;
    dims.push({
      dim: 'precondition',
      kind: 'gap',
      code: 'pre_job_placement',
      need: (flavor && JOB_PLACEMENT_NEED[flavor]) || JOB_PLACEMENT_NEED.camp,
      have: '未采集岗位落实情况',
    });
  }

  // 聘用前置（P2-0 no-skilled-worker）：雇主担保类项目的 offer 门槛。与上面那个
  // placement 前提互斥（一个是 Sponsor 制项目的 placement，一个是雇主担保项目的
  // 具体聘用），但同样不与 kind 构成 if/else——三者可以并存，故各判各的。
  if (flags.precondition?.employer_offer) {
    dims.push({
      dim: 'precondition',
      kind: 'gap',
      code: 'pre_employer_offer',
      need: '具体雇主的具体聘用（全职或至少 80% 岗位，且岗位与你的学历/资格对应）',
      have: '未采集 offer 情况',
    });
  }

  // —— P1b-2：家属 / 签证史 / 学籍三个家族的 typed 值 ——
  //
  // 与 Python 的 p1b2_precondition_dims() **逐条镜像**：顺序、code、kind 必须
  // 完全一致，smoke-test 拿 data/match-samples.json 比的是
  // "dim:kind:code" 拼成的整串，顺序错一位也会红。
  //
  // 这里只做类型层面的比较，不做任何 note 判读——判据全在 Python 侧算好落成
  // flags.precondition.p1b2 的状态量。
  const p = flags.precondition?.p1b2;
  if (p) {
    // 画像侧的取值。缺省（undefined / null）一律当「未知」处理 → silent，绝不默认 pass。
    const dep = pr.dependents ?? null;
    const part = pr.prior_participation ?? null;
    const visa = pr.prior_same_category_visa ?? null;
    const enroll = pr.enrollment_status ?? null;
    // 家属禁令（两个值的边界不同，分别判）
    if (p.forbid_child) {
      if (dep === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_dependents_unknown' });
      } else if (dep === 'children') {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_dependents_child_present',
          need: '无受抚养子女随行',
          have: '有受抚养子女',
        });
      } else if (dep === 'other') {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_dependents_unknown' });
      } else {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_dependents_none' });
      }
    }
    if (p.forbid_other) {
      if (dep === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_dependents_unknown' });
      } else if (dep === 'none') {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_dependents_none' });
      } else {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_dependents_other_present',
          need: '无家属随行',
          have: '有家属随行',
        });
      }
    }
    if (p.cannot_work) {
      if (dep === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_dependents_unknown' });
      } else if (dep === 'none') {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_dependents_none' });
      } else {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_dependents_work_unknown' });
      }
    }
    if (p.separate) {
      dims.push({ dim: 'precondition', kind: 'na', code: 'pre_dependents_separate' });
    }
    if (p.allowed) {
      dims.push({ dim: 'precondition', kind: 'na', code: 'pre_dependents_allowed' });
    }
    if (p.declaration) {
      dims.push({ dim: 'precondition', kind: 'na', code: 'pre_declaration_only' });
    }

    // 既往参加史（按人 / 按项目段 / 按次数，方向一致）
    if (p.participation) {
      if (part === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_participation_unknown' });
      } else if (part === 'used') {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_participation_used',
          need: '未曾参加过本项目/同类项目',
          have: '已参加过',
        });
      } else {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_participation_none' });
      }
    }

    // 同类别签证史
    if (p.same_category_visa) {
      if (visa === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_prior_visa_unknown' });
      } else if (visa === 'used') {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_prior_visa_used',
          need: '未曾持过同类签证',
          have: '曾持过',
        });
      } else {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_prior_visa_none' });
      }
    }

    // **正向**：须持过指定类别签证（au-485-graduate）。方向与上面三条相反，
    // 判 silent（画像不采集签证史）。
    if (p.specific_visa_required) {
      dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_prior_visa_required' });
    }

    // 学籍 / 学历证明：三个值方向各不相同
    if (p.enrollment) {
      if (enroll === null) {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_enrollment_unknown' });
      } else if (enroll === 'enrolled') {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_enrolled_ok' });
      } else {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_not_enrolled',
          need: '当前在读',
          have: '已毕业',
        });
      }
    }
    if (p.degree_completed) {
      if (pr.education === 'bachelor_in_progress') {
        dims.push({
          dim: 'precondition',
          kind: 'fail',
          code: 'pre_degree_missing',
          need: '已毕业（取得学位/文凭）',
          have: '本科在读',
        });
      } else {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_degree_ok' });
      }
    }
    if (p.either) {
      const completed =
        pr.education === 'bachelor_completed' ||
        pr.education === 'master' ||
        pr.education === 'vocational' ||
        pr.education === 'high_school';
      if (pr.education === 'bachelor_in_progress' || enroll === 'enrolled') {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_degree_ok' });
      } else if (enroll === 'completed' || completed) {
        dims.push({ dim: 'precondition', kind: 'pass', code: 'pre_degree_ok' });
      } else {
        dims.push({ dim: 'precondition', kind: 'silent', code: 'pre_enrollment_unknown' });
      }
    }
    if (p.scoring_input) {
      dims.push({ dim: 'precondition', kind: 'na', code: 'pre_scoring_input_only' });
    }
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
