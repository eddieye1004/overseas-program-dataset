// src/lib/profileFields.ts
// 条件显示的纯逻辑：哪些补充字段该出现在表单里。
//
// 为什么需要「条件显示」而不是一次性把七项全放出来：
//   判定页的六项是所有人都要答的（护照/年龄/学历/雅思/预算/现居地）——不答就
//   连一条结论都出不来。另外七项不是：家属构成、既往参加史、同类签证史、
//   在读状态、毕业月数、就读月数、工作年限，各自只影响**一条项目子集**。
//   一次性拉出十三个输入口，多数人看到第三行就退了；而退掉的人拿到的是
//   「不可判」，比不问更糟。
//
// **判据不在这里算。** 「这条项目读不读这个字段」由
// scripts/match_readiness.py 的 profile_readers() 实测得出，随
// data/match-flags.json 一起发下来（precondition.p1b2.reads）。
//
// 为什么不在前端重推一遍：本单第一版就是这么做的（按 p1b2 的布尔量推），
// 变异测试当场证明它不能自我保护——把前端规则改错，Python 侧测试仍然全绿，
// 因为它验的是自己的副本。同一条规则写两遍必然漂，而「门悄悄关掉」在界面上
// 看起来完全正常。所以口径只留引擎那一份，这里只回答「怎么用这份数据」。
//
// 纯函数、不碰 DOM、不读 localStorage：smoke-test 用 esbuild 单独打包断言。

import type { ProgramFlags, VerdictProfile } from './verdict';

/** 条件显示的补充字段。顺序即表单里的出现顺序（同分时按此稳定排序）。 */
export const EXTRA_FIELDS = [
  'enrollment_status',
  'prior_participation',
  'prior_same_category_visa',
  'dependents',
  'study_months',
  'months_since_graduation',
  'work_experience_years',
] as const;

export type ExtraField = (typeof EXTRA_FIELDS)[number];

/** 引擎产出的「这条项目读哪些画像字段」 */
export type FieldReads = Record<ExtraField, boolean>;

/**
 * 一条项目对「门」有用的事实。
 *
 * `undecided` 是**这个用户**此刻对这条项目是否拿不到结论（state === 'unknown'）。
 * 门只关心这一类：已经能判的项目，填补充字段一分钱都改不动。
 */
export interface GateProgram {
  id: string;
  reads: FieldReads;
  /** 当前画像下这条项目判不出结论（unknown） */
  undecided: boolean;
}

/**
 * 从 match-flags 的一条记录里取「读哪些字段」。
 *
 * `reads` 缺失（老产物）时返回全 false —— 门全关。这是**安全方向**：
 * 宁可不问，也不要在没有依据的情况下凭一个猜出来的规则去问。
 * 全关的后果是那些项目显示「不可判」，那本来就是我们不知道的事；
 * 猜错的后果是用户填了一条与判定无关的信息，还以为它起了作用。
 */
export function readersOf(flags: ProgramFlags): FieldReads {
  const raw = flags.precondition?.p1b2?.reads;
  const out = {} as FieldReads;
  for (const f of EXTRA_FIELDS) {
    out[f] = raw?.[f] === true;
  }
  return out;
}

/** 门需要的输入：项目清单（已带 reads 与是否不可判）+ 用户已填的主字段 */
export interface GateInput {
  profile: VerdictProfile;
  programs: GateProgram[];
}

/**
 * 某个补充字段该不该出现。
 *
 * **判据是「能不能改变你眼前的结论」，不是「这个字段有没有用」**：
 * 至少有一条**当前判不出结论**的项目读它，才问。这是工单第 3 条
 * 「只在与用户已填信息相关时出现」的可执行定义。
 *
 * 反例（本单初版犯过）：按「全库有项目读它」开门，于是七项对所有人
 * 永远全开——一个已经能判完 40 条项目的人，仍被问家属、问签证史，
 * 而那些项目对他早已给出结论。那不是条件显示，只是把表单拉长了。
 */
export function shouldAsk(field: ExtraField, input: GateInput): boolean {
  return input.programs.some((p) => p.undecided && p.reads[field]);
}

/** 该显示的补充字段（保持 EXTRA_FIELDS 顺序，表单不会跳来跳去） */
export function visibleExtraFields(input: GateInput): ExtraField[] {
  return EXTRA_FIELDS.filter((f) => shouldAsk(f, input));
}

/**
 * 表单「一次最多露出几项补充字段」。
 *
 * 三条以上就要用户连续作答，实测会让多数人在第三项放弃（放弃的人拿到
 * 「不可判」）。折中是：默认只露影响最大的三项，其余收在「继续细化」里。
 * 注意这里的「三」是**上限**——门本身可能只开一两项，那就只露一两项。
 */
export const MAX_VISIBLE_EXTRA = 3;

/**
 * 按「对当前画像的翻动潜力」排序。
 *
 * 打分只用已填的主字段 + 项目事实，不试跑判定（前端不做判定，判定口径
 * 唯一权威在 Python 侧）。所以这是**代理指标**，不是精确收益：
 *   · 读它的项目越多 → 越靠前（影响面）
 *   · 与用户当前身份相关 → 加分（在读的人先问在读状态）
 *
 * 代理指标的偏差是「顺序可能不最优」，代价是多点一次「继续细化」；
 * 而精确收益要前端重跑 41 条判定，那是把判定口径搬进前端——M1 明令禁止。
 */
export function payoffRank(field: ExtraField, input: GateInput): number {
  const hits = input.programs.filter((p) => p.undecided && p.reads[field]).length;
  const pr = input.profile;
  let affinity = 0;

  if (field === 'enrollment_status') {
    // 在读 / 应届的人先答学籍；已工作多年的人这条优先级低
    if (pr.education === 'bachelor_in_progress') affinity = 3;
    else if (pr.age <= 26) affinity = 1;
  }
  if (field === 'months_since_graduation') {
    // 已毕业且年轻：毕业多久正是应届身份的关键
    if (pr.education !== 'bachelor_in_progress' && pr.age <= 30) affinity = 2;
  }
  if (field === 'work_experience_years') {
    // 已毕业且有几年可工作的人，经验年限才是真有值的字段
    if (pr.education !== 'bachelor_in_progress' && pr.age >= 24) affinity = 2;
  }
  if (field === 'dependents') {
    // 25 岁以上问家属更自然（刚毕业的人多半还没成家）
    if (pr.age >= 25) affinity = 1;
  }
  if (field === 'study_months') {
    if (pr.education === 'bachelor_in_progress') affinity = 1;
  }

  return hits * 2 + affinity;
}

/** 当前该显示、且排在前 MAX_VISIBLE_EXTRA 的字段 */
export function primaryExtraFields(input: GateInput): ExtraField[] {
  const ranked = [...visibleExtraFields(input)].sort((a, b) => {
    const d = payoffRank(b, input) - payoffRank(a, input);
    // 同分时按 EXTRA_FIELDS 的固定顺序，避免每次渲染顺序抖动
    return d !== 0 ? d : EXTRA_FIELDS.indexOf(a) - EXTRA_FIELDS.indexOf(b);
  });
  return ranked.slice(0, MAX_VISIBLE_EXTRA);
}

/** 被收进「继续细化」的字段（visible 里去掉 primary） */
export function secondaryExtraFields(input: GateInput): ExtraField[] {
  const prim = new Set(primaryExtraFields(input));
  return visibleExtraFields(input).filter((f) => !prim.has(f));
}

/**
 * 清掉「当前不该问」的字段值。
 *
 * 场景：用户先填了「已毕业」，于是露出「毕业月数」并填了 36；随后把学历改成
 * 「本科在读」——这条事实就自相矛盾了（在读的人没有毕业月数）。留着它会让
 * 判定拿一个已经不可能成立的值去比，结论看着正常但是错的。
 *
 * 规则：门关着的字段一律置回 null（= 未知），不静默保留。
 * 只清**补充字段**，六项主字段从不清（它们永远该问）。
 */
export function pruneHidden(input: GateInput, profile: VerdictProfile): VerdictProfile {
  const vis = new Set<string>(visibleExtraFields(input));
  const out = { ...profile } as VerdictProfile & Record<string, unknown>;
  for (const f of EXTRA_FIELDS) {
    if (!vis.has(f)) {
      out[f] = null;
    }
  }
  return out;
}
