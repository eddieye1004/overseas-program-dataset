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
  /** education.minimum_level 的实测值之一；null 表示不限/不想说 */
  education: string | null;
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
  budgetCny: null,
  minStayMonths: null,
  mustBePaid: false,
  preferNoAgency: false,
  regions: [],
};

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

/** 权重合计 100：资格 40 / 年龄 20 / 预算 10 / 学历 10 / 停留 10 / 偏好 10 */
const W = {
  status: 40,
  age: 20,
  budget: 10,
  edu: 10,
  stay: 10,
  prefer: 10,
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

  // 3) 预算：资金证明是硬门槛，钱不够去了也过不了关
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

  // 4) 学历门槛
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

  // 6) 偏好：带薪 / 免中介 / 地区
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

  // 有硬性 fail 的项目不让它冲到前面，但仍然返回，用户能看到"为什么不行"
  const hardFail = reasons.some(
    (r) => r.kind === 'fail' && ['m.statusNo', 'm.ageLow', 'm.ageHigh', 'm.eduLow'].includes(r.code),
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
