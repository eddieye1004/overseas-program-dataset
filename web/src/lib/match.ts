// src/lib/match.ts
// 智能匹配：把用户填的画像翻译成一个 0–100 的匹配分 + 命中/未命中理由。
// 纯函数，不依赖 React，可被 smoke-test 单独断言。
//
// 打分不是"资格判定"——判定只来自 eligibility 字段；这里回答的是
// "以你现在的条件，哪个更值得先看"，所以给的是排序和理由，不是"能不能申"。
import type { ProgramIndexEntry } from '../types';

export interface Profile {
  /** 护照类型对应的资格状态字段值：eligible / not_eligible / conditional / unknown */
  status: string | null;
  age: number | null;
  /** 最高学历。注意它不等于「现在是什么身份」——见 studentStatus */
  education: string | null;
  /**
   * 当前身份。这是唯一能区分「学生」与「在职者」的输入：
   * 学历字段做不到，因为 minimum_level 把「本科在读」与「本科已毕业」压成了
   * 两个相邻档位，而好几条项目对「在读」有硬要求、对「已毕业」另有时间窗。
   */
  studentStatus: StudentStatus | null;
  /** 可用于前期投入的预算（人民币元），null 表示不设限 */
  budgetCny: number | null;
  /** 希望的最短可停留月数，null 表示不挑 */
  minStayMonths: number | null;
  /** 是否必须带薪 */
  mustBePaid: boolean;
  /** 是否希望不需要中介 */
  preferNoAgency: boolean;
  /** 偏好的地区，空数组表示都行 */
  regions: string[];
}

export const EMPTY_PROFILE: Profile = {
  status: null,
  age: null,
  education: null,
  studentStatus: null,
  budgetCny: null,
  minStayMonths: null,
  mustBePaid: false,
  preferNoAgency: false,
  regions: [],
};

/**
 * 当前身份。三档对应三类真实的签证处境：
 *   enrolled      在校（本科/硕士都算，只要有学籍）
 *   recent_grad   毕业 2 年内——德国 16e、AIESEC 的时限都落在这个窗口
 *   working       在职 / 毕业超过 2 年 / 没打算回去读书
 * 选这几档而不是「学生 / 非学生」，是因为 16e 这类项目给毕业生留了 2 年口子，
 * 把它并进「非学生」会让本来就少的选择更少。
 */
export type StudentStatus = 'enrolled' | 'recent_grad' | 'working';

export const STUDENT_STATUS: StudentStatus[] = ['enrolled', 'recent_grad', 'working'];

/** 学历从低到高的次序，用来比较"我的学历是否够项目的门槛" */
const EDU_RANK: Record<string, number> = {
  high_school: 1,
  vocational: 2,
  bachelor_in_progress: 3,
  bachelor_completed: 4,
  master: 5,
  any: 0,
};

export type ReasonKind = 'pass' | 'fail' | 'warn';

export interface Reason {
  kind: ReasonKind;
  /** 词条 key，由界面层翻译；这里不写死中文，避免和 i18n 打架 */
  code: string;
  /** 可选的具体数值，用于插值显示 */
  value?: string;
}

export interface MatchResult {
  id: string;
  score: number;
  reasons: Reason[];
}

/** 权重合计 100：资格 36 / 年龄 20 / 身份 14 / 预算 8 / 学历 8 / 停留 8 / 偏好 6 */
const W = {
  status: 36,
  age: 20,
  student: 14,
  budget: 8,
  edu: 8,
  stay: 8,
  prefer: 6,
};

/**
 * 单条项目打分。缺失的信息不算扣分（数据没有 ≠ 你不符合），
 * 只在理由里标 warn，让用户自己去详情页确认。
 */
export function scoreOne(p: ProgramIndexEntry, pr: Profile): MatchResult {
  const reasons: Reason[] = [];
  let score = 0;

  // 1) 资格（权重最高）：这是硬门槛，不符合就直接低分，但仍显示在列表里
  if (pr.status != null) {
    if (p.status === pr.status) {
      score += W.status;
      reasons.push({ kind: 'pass', code: 'm.statusOk' });
    } else {
      reasons.push({ kind: 'fail', code: 'm.statusNo' });
    }
  }

  // 2) 年龄
  if (pr.age != null) {
    // 0–99 是「官方没公布年龄限制」的占位区间，不能当成「你符合」，只能算未知
    const ageUnknown = p.age_min === 0 && p.age_max === 99;
    if (!ageUnknown && p.age_min != null && pr.age < p.age_min) {
      reasons.push({ kind: 'fail', code: 'm.ageLow', value: String(p.age_min) });
    } else if (!ageUnknown && p.age_max != null && pr.age > p.age_max) {
      reasons.push({ kind: 'fail', code: 'm.ageHigh', value: String(p.age_max) });
    } else if (ageUnknown || (p.age_min == null && p.age_max == null)) {
      reasons.push({ kind: 'warn', code: 'm.ageUnknown' });
      score += W.age / 2;
    } else {
      score += W.age;
      reasons.push({ kind: 'pass', code: 'm.ageOk' });
    }
  }

  // 3) 身份（在读 / 毕业 2 年内 / 在职）——这是学历字段分不出来的那一层
  if (pr.studentStatus != null) {
    if (p.enrollment_scope === 'required') {
      // 项目明文要求在读证明且全程保持学籍
      if (pr.studentStatus === 'enrolled') {
        score += W.student;
        reasons.push({ kind: 'pass', code: 'm.studentOk' });
      } else {
        reasons.push({ kind: 'fail', code: 'm.studentNeeded' });
      }
    } else if (p.enrollment_scope === 'enrolled_or_recent') {
      // 在读，或毕业 2 年内——在职者递不上去，但它不是「必须在校」，理由单独说
      if (pr.studentStatus === 'working') {
        reasons.push({ kind: 'fail', code: 'm.studentTooLate' });
      } else {
        score += W.student;
        reasons.push({ kind: 'pass', code: 'm.studentRecentOk' });
      }
    } else if (p.enrollment_scope === 'unknown') {
      // 官方没公布身份门槛。不扣分，也不给 pass——给半分的 warn，
      // 和年龄/预算的未知处理保持一致，让用户知道这条要靠自己确认。
      score += W.student / 2;
      reasons.push({ kind: 'warn', code: 'm.studentUnknown' });
    } else {
      // 不要求学籍的项目对三种身份都开放
      score += W.student;
      reasons.push({ kind: 'pass', code: 'm.studentFree' });
    }
  }

  // 4) 预算：资金证明是硬门槛，钱不够去了也过不了关
  if (pr.budgetCny != null) {
    if (p.funds_amount != null) {
      // 数据里 funds 的币种不统一，index 里带了 cny 折算前的原币值；
      // 只有币种是 CNY 时才能直接比，其余按"未知"处理，不猜汇率。
      if (p.funds_currency === 'CNY' && p.funds_amount > pr.budgetCny) {
        reasons.push({ kind: 'fail', code: 'm.budgetLow', value: String(p.funds_amount) });
      } else {
        score += W.budget;
        reasons.push({ kind: 'pass', code: 'm.budgetOk' });
      }
    } else {
      score += W.budget / 2;
      reasons.push({ kind: 'warn', code: 'm.budgetUnknown' });
    }
  }

  // 5) 学历门槛
  if (pr.education != null) {
    const need = EDU_RANK[p.education ?? 'any'] ?? 0;
    const have = EDU_RANK[pr.education] ?? 0;
    if (need > have) {
      reasons.push({ kind: 'fail', code: 'm.eduLow' });
    } else {
      score += W.edu;
      reasons.push({ kind: 'pass', code: 'm.eduOk' });
    }
  }

  // 5) 可停留时长
  if (pr.minStayMonths != null) {
    if (p.max_stay_months == null) {
      score += W.stay / 2;
      reasons.push({ kind: 'warn', code: 'm.stayUnknown' });
    } else if (p.max_stay_months >= pr.minStayMonths) {
      score += W.stay;
      reasons.push({ kind: 'pass', code: 'm.stayOk', value: String(p.max_stay_months) });
    } else {
      reasons.push({ kind: 'fail', code: 'm.stayLow', value: String(p.max_stay_months) });
    }
  }

  // 7) 偏好：带薪 / 免中介 / 地区
  let pref = 0;
  let prefMax = 0;
  if (pr.mustBePaid) {
    prefMax += 1;
    if (p.tags.includes('paid') || p.tags.includes('high_wage')) {
      pref += 1;
      reasons.push({ kind: 'pass', code: 'm.paidOk' });
    } else {
      reasons.push({ kind: 'warn', code: 'm.paidUnknown' });
    }
  }
  if (pr.preferNoAgency) {
    prefMax += 1;
    if (p.tags.includes('no_agency_needed')) {
      pref += 1;
      reasons.push({ kind: 'pass', code: 'm.agencyOk' });
    } else if (p.tags.includes('requires_agency')) {
      reasons.push({ kind: 'warn', code: 'm.agencyNeeded' });
    }
  }
  if (pr.regions.length > 0) {
    prefMax += 1;
    if (pr.regions.includes(p.region)) {
      pref += 1;
      reasons.push({ kind: 'pass', code: 'm.regionOk' });
    } else {
      reasons.push({ kind: 'fail', code: 'm.regionNo' });
    }
  }
  if (prefMax > 0) score += (pref / prefMax) * W.prefer;

  // 有硬性 fail 的项目不让它冲到前面，但仍然返回，用户能看到"为什么不行"。
  // 两条学籍相关的 fail 都算硬性：一条要求在读证明，一条只给毕业 2 年内的人。
  const hardFail = reasons.some(
    (r) =>
      r.kind === 'fail' &&
      [
        'm.statusNo',
        'm.ageLow',
        'm.ageHigh',
        'm.eduLow',
        'm.studentNeeded',
        'm.studentTooLate',
      ].includes(r.code),
  );

  return {
    id: p.id,
    score: Math.round(hardFail ? Math.min(score, 30) : score),
    reasons,
  };
}

/** 全量打分并按分数降序；同分按 id 稳定排序，避免每次渲染顺序抖动 */
export function matchAll(list: ProgramIndexEntry[], pr: Profile): MatchResult[] {
  return list
    .map((p) => scoreOne(p, pr))
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
}
