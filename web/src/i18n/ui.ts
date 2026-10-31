// src/i18n/ui.ts
// 界面自身的词条（不来自数据文件）。数据里的中文串走 i18n.json 词典，
// 这里的词条是按钮、标题、筛选项标签这类页面骨架文字。
import type { Lang } from '../types';

export type UiKey =
  | 'siteTitle'
  | 'siteTagline'
  | 'searchPlaceholder'
  | 'filterRegion'
  | 'filterType'
  | 'filterStatus'
  | 'filterTags'
  | 'filterAgeOnly'
  | 'all'
  | 'reset'
  | 'results'
  | 'noResults'
  | 'noResultsHint'
  | 'eligible'
  | 'notEligible'
  | 'conditional'
  | 'unknown'
  | 'age'
  | 'stay'
  | 'fee'
  | 'lang'
  | 'required'
  | 'notRequired'
  | 'back'
  | 'officialSite'
  | 'authority'
  | 'passportCheck'
  | 'eligibility'
  | 'ageRequirement'
  | 'education'
  | 'languageReq'
  | 'funds'
  | 'otherReqs'
  | 'timeline'
  | 'mechanism'
  | 'quota'
  | 'windows'
  | 'processingTime'
  | 'documents'
  | 'steps'
  | 'workConditions'
  | 'maxStay'
  | 'sameEmployer'
  | 'renewable'
  | 'restricted'
  | 'risks'
  | 'sources'
  | 'lastVerified'
  | 'verifiedBy'
  | 'primary'
  | 'secondary'
  | 'openLink'
  | 'footerNote'
  | 'countPrograms'
  | 'searchHint'
  | 'riskCritical'
  | 'riskWarning'
  | 'riskInfo'
  | 'perYear'
  | 'months'
  | 'monthsUnit'
  | 'free'
  | 'statusUnknownNote'
  | 'sortBy'
  | 'sortDefault'
  | 'sortVerified'
  | 'sortStay'
  | 'sortAge'
  | 'savedOnly'
  | 'criticalOnly'
  // —— 工作台导航 ——
  | 'navBrowse'
  | 'navMatch'
  | 'navTrack'
  | 'navSaved'
  | 'navCompare'
  | 'navData'
  | 'workbench'
  // —— 智能匹配 ——
  | 'matchTitle'
  | 'matchIntro'
  | 'matchWhy'
  | 'matchEmpty'
  | 'matchTopHint'
  | 'matchBest'
  | 'profileTitle'
  | 'profileDesc'
  | 'profileStatus'
  | 'profileAge'
  | 'profileEdu'
  | 'profileBudget'
  | 'profileStay'
  | 'profilePaid'
  | 'profileNoAgency'
  | 'profileRegions'
  | 'profileReset'
  | 'profileAny'
  | 'profileSaved'
  // —— 申请进度 ——
  | 'trackTitle'
  | 'trackIntro'
  | 'trackEmpty'
  | 'trackAdd'
  | 'trackRemove'
  | 'trackNote'
  | 'trackClear'
  | 'trackOpen'
  // —— 收藏与对比 ——
  | 'save'
  | 'unsave'
  | 'savedTitle'
  | 'savedEmpty'
  | 'compare'
  | 'compareTitle'
  | 'compareEmpty'
  | 'compareFull'
  | 'compareClear'
  | 'recentTitle'
  | 'yes'
  | 'no'
  // —— 数据质量 ——
  | 'dataTitle'
  | 'dataIntro'
  | 'dataTotal'
  | 'dataVerified'
  | 'dataSources'
  | 'dataStale'
  | 'dataRules'
  // —— 信息架构与来源可视化（2026-10-29 追加）——
  | 'listTitle'
  | 'listIntro'
  | 'skipToContent'
  | 'verifiedOn'
  | 'sourceCount'
  | 'sourcePrimaryCount'
  | 'sourceSecondaryCount'
  | 'domainColumn'
  | 'openSource'
  | 'relaxHint'
  | 'relaxRemove'
  | 'clearAll'
  | 'pageTitleSuffix'
  // —— 未核实值（2026-10-30：官方没写的一律留空，不拿二手数字充数）——
  | 'notVerified'
  | 'notVerifiedHint'
  // —— 信息架构改版（2026-10-31：首屏讲结论、筛选分主次）——
  | 'statsStale'
  | 'statsCheckedTo'
  | 'sortEligible'
  | 'moreFilters'
  | 'fewerFilters'
  | 'otherTags'
  | 'selectedCount'
  | 'filtersToggle'
  | 'closeFilters'
  | 'noAgeLimit'
  | 'andUnder'
  | 'andOver'
  | 'ageUnit';

export const UI: Record<Lang, Record<UiKey, string>> = {
  zh: {
    siteTitle: '海外项目数据库',
    siteTagline: '面向中国大陆申请人的打工度假与海外实习项目，逐条标注官方来源与核实日期',
    searchPlaceholder: '搜索项目名、国家、机构（中英文均可）',
    filterRegion: '地区',
    filterType: '项目类型',
    filterStatus: '我的资格',
    filterTags: '标签',
    filterAgeOnly: '只看我年龄符合的',
    all: '全部',
    reset: '清空筛选',
    results: '个结果',
    noResults: '没有符合条件的项目',
    noResultsHint: '试试少选几个筛选条件，或清空全部条件',
    eligible: '大陆护照可申',
    notEligible: '大陆护照不可申',
    conditional: '有条件可申',
    unknown: '资格未知',
    age: '年龄',
    stay: '停留期',
    fee: '费用',
    lang: '语言',
    required: '需要',
    notRequired: '不要求',
    back: '返回列表',
    officialSite: '官方网站',
    authority: '主管机构',
    passportCheck: '护照资格判定',
    eligibility: '申请资格',
    ageRequirement: '年龄要求',
    education: '学历要求',
    languageReq: '语言要求',
    funds: '资金证明',
    otherReqs: '其他要求',
    timeline: '时间与名额',
    mechanism: '申请机制',
    quota: '年度名额',
    windows: '申请窗口',
    processingTime: '审理时长',
    documents: '材料清单',
    steps: '申请流程',
    workConditions: '工作条件',
    maxStay: '最长停留',
    sameEmployer: '同一雇主上限',
    renewable: '可否续签',
    restricted: '禁止从事',
    risks: '风险提示',
    sources: '信息来源',
    lastVerified: '核实日期',
    verifiedBy: '核实人',
    primary: '官方一手来源',
    secondary: '二手来源',
    openLink: '打开链接',
    footerNote:
      '数据以各国官方移民部门页面为准。本站只做索引，不代办申请、不提供签证建议；提交前请自行复核官方页面。',
    countPrograms: '共收录项目',
    searchHint: '输入关键词开始筛选',
    riskCritical: '致命风险',
    riskWarning: '注意',
    riskInfo: '说明',
    perYear: '/ 年',
    months: '个月',
    monthsUnit: '个月',
    free: '免费',
    statusUnknownNote: '官方未公布当年窗口',
    sortBy: '排序',
    sortDefault: '默认',
    sortVerified: '最近核实',
    sortStay: '停留期长',
    sortAge: '年龄上限高',
    savedOnly: '只看已收藏',
    criticalOnly: '只看有致命风险',

    navBrowse: '项目库',
    navMatch: '智能匹配',
    navTrack: '我的申请',
    navSaved: '收藏',
    navCompare: '对比',
    navData: '数据说明',
    workbench: '工作台',

    matchTitle: '智能匹配',
    matchIntro: '填一次个人条件，按匹配度从高到低排。分数只用于排序，能不能申仍以「护照资格」判定为准。',
    matchWhy: '为什么排这个位',
    matchEmpty: '先填左边的条件，这里会给出排序和理由',
    matchTopHint: '按匹配度排序，点开卡片看完整依据',
    matchBest: '最匹配',
    profileTitle: '我的条件',
    profileDesc: '只存在你自己的浏览器里，不上传、不联网',
    profileStatus: '护照资格',
    profileAge: '年龄',
    profileEdu: '最高学历',
    profileBudget: '可用于前期的预算（人民币）',
    profileStay: '希望至少待多久',
    profilePaid: '必须带薪',
    profileNoAgency: '希望不需要中介',
    profileRegions: '倾向的地区',
    profileReset: '清空条件',
    profileAny: '不限',
    profileSaved: '条件已保存在本机',

    trackTitle: '我的申请',
    trackIntro: '给每个项目记一个当前进度，只存在本机。这是自用的进度板，不是申请系统。',
    trackEmpty: '还没有在跟进的项目。在详情页点「加入我的申请」即可。',
    trackAdd: '加入我的申请',
    trackRemove: '移出',
    trackNote: '备注（可选）',
    trackClear: '清空进度',
    trackOpen: '打开详情',

    save: '收藏',
    unsave: '取消收藏',
    savedTitle: '我的收藏',
    savedEmpty: '还没有收藏。在卡片或详情页点「收藏」即可，收藏只存在本机。',
    compare: '加入对比',
    compareTitle: '项目对比',
    compareEmpty: '还没有加入对比的项目。最多同时对比 4 个。',
    compareFull: '对比清单已满（最多 4 个），先移出一个再加入。',
    compareClear: '清空对比',
    recentTitle: '最近浏览',
    yes: '是',
    no: '否',

    dataTitle: '数据说明',
    dataIntro: '这一页解释数据从哪来、什么时候核的、哪些字段核不到。',
    dataTotal: '收录项目',
    dataVerified: '已标注核实日期',
    dataSources: '来源总数',
    dataStale: '超过 90 天未复核',
    dataRules: '收录规则',

    listTitle: '项目库',
    listIntro: '按国家、地区、项目类型与标签筛选，每条都标注官方来源与核实日期。',
    skipToContent: '跳到主内容',
    verifiedOn: '核实于',
    sourceCount: '来源',
    sourcePrimaryCount: '官方主源',
    sourceSecondaryCount: '二手参考',
    domainColumn: '域名',
    openSource: '打开来源',
    relaxHint: '条件过严，放宽一项看看：',
    relaxRemove: '移除',
    clearAll: '清空全部条件',
    notVerified: '未核实',
    notVerifiedHint: '官方页面未公布此项',
    pageTitleSuffix: '海外项目数据库',
    // 信息架构改版（2026-10-31）
    statsStale: '超期未复核',
    statsCheckedTo: '数据核实至',
    sortEligible: '可申优先',
    moreFilters: '更多筛选',
    fewerFilters: '收起筛选',
    otherTags: '其他标签',
    selectedCount: '已选',
    filtersToggle: '筛选条件',
    closeFilters: '收起筛选面板',
    noAgeLimit: '无年龄限制',
    andUnder: '岁及以下',
    andOver: '岁及以上',
    ageUnit: '岁',
  },
  en: {
    siteTitle: 'Overseas Program Dataset',
    siteTagline:
      'Working holiday and overseas internship programs for mainland Chinese applicants, each traced to an official source with a verification date',
    searchPlaceholder: 'Search program, country or authority (Chinese or English)',
    filterRegion: 'Region',
    filterType: 'Program type',
    filterStatus: 'My eligibility',
    filterTags: 'Tags',
    filterAgeOnly: 'Only programs matching my age',
    all: 'All',
    reset: 'Clear filters',
    results: 'results',
    noResults: 'No programs match',
    noResultsHint: 'Try removing a filter, or clear them all',
    eligible: 'Open to mainland China',
    notEligible: 'Not open to mainland China',
    conditional: 'Conditionally open',
    unknown: 'Eligibility unknown',
    age: 'Age',
    stay: 'Stay',
    fee: 'Fee',
    lang: 'Language',
    required: 'Required',
    notRequired: 'Not required',
    back: 'Back to list',
    officialSite: 'Official website',
    authority: 'Authority',
    passportCheck: 'Passport eligibility',
    eligibility: 'Eligibility',
    ageRequirement: 'Age',
    education: 'Education',
    languageReq: 'Language',
    funds: 'Proof of funds',
    otherReqs: 'Other requirements',
    timeline: 'Timeline and quota',
    mechanism: 'Selection mechanism',
    quota: 'Annual quota',
    windows: 'Application windows',
    processingTime: 'Processing time',
    documents: 'Documents',
    steps: 'Application steps',
    workConditions: 'Work conditions',
    maxStay: 'Maximum stay',
    sameEmployer: 'Limit per employer',
    renewable: 'Renewable',
    restricted: 'Prohibited work',
    risks: 'Risks',
    sources: 'Sources',
    lastVerified: 'Verified on',
    verifiedBy: 'Verified by',
    primary: 'Primary official source',
    secondary: 'Secondary source',
    openLink: 'Open link',
    footerNote:
      'The national immigration authorities are authoritative. This site is an index only: it does not file applications or give visa advice. Re-check the official page before you apply.',
    countPrograms: 'Programs listed',
    searchHint: 'Type a keyword to start filtering',
    riskCritical: 'Critical',
    riskWarning: 'Caution',
    riskInfo: 'Note',
    perYear: '/ year',
    months: 'months',
    monthsUnit: 'months',
    free: 'Free',
    statusUnknownNote: 'The official year has not been announced',
    sortBy: 'Sort',
    sortDefault: 'Default',
    sortVerified: 'Recently verified',
    sortStay: 'Longest stay',
    sortAge: 'Highest age cap',
    savedOnly: 'Saved only',
    criticalOnly: 'Critical risks only',

    navBrowse: 'Programs',
    navMatch: 'Smart match',
    navTrack: 'My applications',
    navSaved: 'Saved',
    navCompare: 'Compare',
    navData: 'About the data',
    workbench: 'Workspace',

    matchTitle: 'Smart match',
    matchIntro:
      'Enter your profile once and sort by fit. The score only orders the list — whether you can actually apply is decided by passport eligibility.',
    matchWhy: 'Why this rank',
    matchEmpty: 'Fill in the profile on the left and the ranked list appears here',
    matchTopHint: 'Sorted by fit; open a card to see the full basis',
    matchBest: 'Best fit',
    profileTitle: 'My profile',
    profileDesc: 'Stored only in this browser. Nothing is uploaded.',
    profileStatus: 'Passport eligibility',
    profileAge: 'Age',
    profileEdu: 'Highest education',
    profileBudget: 'Upfront budget available (CNY)',
    profileStay: 'Minimum stay you want',
    profilePaid: 'Must be paid',
    profileNoAgency: 'Prefer no agency',
    profileRegions: 'Preferred regions',
    profileReset: 'Reset profile',
    profileAny: 'Any',
    profileSaved: 'Profile saved on this device',

    trackTitle: 'My applications',
    trackIntro:
      'Track one status per program, stored on this device. A personal board, not an application system.',
    trackEmpty: 'Nothing tracked yet. Use "Add to my applications" on a program page.',
    trackAdd: 'Add to my applications',
    trackRemove: 'Remove',
    trackNote: 'Note (optional)',
    trackClear: 'Clear all',
    trackOpen: 'Open page',

    save: 'Save',
    unsave: 'Remove from saved',
    savedTitle: 'Saved programs',
    savedEmpty: 'Nothing saved yet. Use "Save" on a card or program page — saved items stay on this device.',
    compare: 'Compare',
    compareTitle: 'Compare programs',
    compareEmpty: 'Nothing to compare yet. Up to 4 at a time.',
    compareFull: 'The compare list is full (4 max). Remove one to add another.',
    compareClear: 'Clear compare',
    recentTitle: 'Recently viewed',
    yes: 'Yes',
    no: 'No',

    dataTitle: 'About the data',
    dataIntro: 'This page explains where the data comes from, when it was checked, and what could not be verified.',
    dataTotal: 'Programs listed',
    dataVerified: 'With a verification date',
    dataSources: 'Sources',
    dataStale: 'Not re-checked in 90 days',
    dataRules: 'Inclusion rules',

    listTitle: 'Programs',
    listIntro:
      'Filter by country, region, program type and tags. Every entry cites its official source and the date it was checked.',
    skipToContent: 'Skip to content',
    verifiedOn: 'Checked on',
    sourceCount: 'Sources',
    sourcePrimaryCount: 'Official sources',
    sourceSecondaryCount: 'Secondary references',
    domainColumn: 'Domain',
    openSource: 'Open source',
    relaxHint: 'Too narrow. Relax one condition:',
    relaxRemove: 'Remove',
    clearAll: 'Clear all filters',
    notVerified: 'Not verified',
    notVerifiedHint: 'Not published on the official page',
    pageTitleSuffix: 'Overseas Program Database',
    // Information architecture (2026-10-31)
    statsStale: 'past re-check date',
    statsCheckedTo: 'Data checked to',
    sortEligible: 'Eligible first',
    moreFilters: 'More filters',
    fewerFilters: 'Fewer filters',
    otherTags: 'Other tags',
    selectedCount: 'Selected',
    filtersToggle: 'Filters',
    closeFilters: 'Collapse filters',
    noAgeLimit: 'no age limit',
    andUnder: 'or under',
    andOver: 'or over',
    ageUnit: 'yrs',
  },
};

/** 枚举值 → 界面标签。数据里的枚举是机器可读英文，展示要本地化。 */
export const ENUM_LABELS: Record<Lang, Record<string, string>> = {
  zh: {
    oceania: '大洋洲',
    asia: '亚洲',
    europe: '欧洲',
    north_america: '北美洲',
    south_america: '南美洲',
    africa: '非洲',
    global: '全球',
    working_holiday: '打工度假',
    paid_internship: '带薪实习',
    internship_visa: '实习签证',
    cultural_exchange: '文化交流',
    short_term_work: '短期工作',
    eligible: '大陆护照可申',
    not_eligible: '大陆护照不可申',
    conditional: '有条件可申',
    unknown: '未知',
    ballot: '抽签',
    first_come_first_served: '先到先得',
    rolling: '滚动受理',
    appointment: '预约制',
    annual_negotiation: '年度协商',
    open: '开放中',
    closed: '已关闭',
    upcoming: '即将开放',
    primary: '官方一手来源',
    secondary: '二手来源',
    info: '说明',
    warning: '注意',
    critical: '致命风险',
    high_school: '高中',
    vocational: '职高/中专',
    bachelor_in_progress: '本科在读',
    bachelor_completed: '本科毕业',
    master: '硕士',
    any: '不限',
    no_quota_cap: '无名额上限',
    ballot_required: '需抽签',
    first_come_first_served_tag: '先到先得',
    rolling_tag: '滚动受理',
    once_in_lifetime: '一生一次',
    renewable_tag: '可续签',
    renewable: '可续签',
    requires_agency: '需通过机构',
    no_agency_needed: '无需中介',
    farm_work_available: '有农场岗位',
    high_wage: '高时薪',
    low_cost: '低成本',
    requires_degree: '需学位',
    stem_friendly: '适合 STEM',
    high_demand: '名额紧张',
    cultural_exchange_tag: '文化交流',
    engineering_friendly: '适合工科',
    paid: '带薪',
    unpaid: '无薪',
    english_required: '需英语成绩',
    no_english_required: '无需英语成绩',
    residency_required: '有居住要求',
    blocked_account: '需冻结账户',
    criminal_record: '需无犯罪记录',
    enrollment_proof: '需在读证明',
    government_support_letter: '需政府推荐信',
    health_check: '需体检',
    internship_contract: '需实习合同',
    no_dependents: '不可带家属',
    no_prior_visa: '此前未持过该签证',
    return_ticket: '需返程机票',
    residency_requirement: '需居住在当地',
    insurance: '需医疗保险',
    IELTS: 'IELTS',
    TOEFL_iBT: 'TOEFL iBT',
    PTE: 'PTE',
    Cambridge: 'Cambridge',
    CEFR: 'CEFR',
    OET: 'OET',
    none: '无',
  },
  en: {
    oceania: 'Oceania',
    asia: 'Asia',
    europe: 'Europe',
    north_america: 'North America',
    south_america: 'South America',
    africa: 'Africa',
    global: 'Global',
    working_holiday: 'Working holiday',
    paid_internship: 'Paid internship',
    internship_visa: 'Internship visa',
    cultural_exchange: 'Cultural exchange',
    short_term_work: 'Short-term work',
    eligible: 'Open to mainland China',
    not_eligible: 'Not open to mainland China',
    conditional: 'Conditionally open',
    unknown: 'Unknown',
    ballot: 'Ballot',
    first_come_first_served: 'First come, first served',
    rolling: 'Rolling',
    appointment: 'By appointment',
    annual_negotiation: 'Annual negotiation',
    open: 'Open',
    closed: 'Closed',
    upcoming: 'Opening soon',
    primary: 'Primary official source',
    secondary: 'Secondary source',
    info: 'Note',
    warning: 'Caution',
    critical: 'Critical',
    high_school: 'High school',
    vocational: 'Vocational',
    bachelor_in_progress: 'Bachelor in progress',
    bachelor_completed: 'Bachelor completed',
    master: "Master's",
    any: 'None',
    no_quota_cap: 'No quota cap',
    ballot_required: 'Ballot required',
    first_come_first_served_tag: 'First come, first served',
    rolling_tag: 'Rolling intake',
    once_in_lifetime: 'Once in a lifetime',
    renewable_tag: 'Renewable',
    renewable: 'Renewable',
    requires_agency: 'Sponsor required',
    no_agency_needed: 'No agency needed',
    farm_work_available: 'Farm jobs available',
    high_wage: 'High wage',
    low_cost: 'Low cost',
    requires_degree: 'Degree required',
    stem_friendly: 'STEM friendly',
    high_demand: 'High demand',
    cultural_exchange_tag: 'Cultural exchange',
    engineering_friendly: 'Engineering friendly',
    paid: 'Paid',
    unpaid: 'Unpaid',
    english_required: 'English test required',
    no_english_required: 'No English test',
    residency_required: 'Residency required',
    blocked_account: 'Blocked account required',
    criminal_record: 'Police certificate required',
    enrollment_proof: 'Proof of enrolment',
    government_support_letter: 'Government support letter',
    health_check: 'Medical check',
    internship_contract: 'Internship contract',
    no_dependents: 'No dependants',
    no_prior_visa: 'No prior visa held',
    return_ticket: 'Return ticket',
    residency_requirement: 'Local residency',
    insurance: 'Health insurance',
    IELTS: 'IELTS',
    TOEFL_iBT: 'TOEFL iBT',
    PTE: 'PTE',
    Cambridge: 'Cambridge',
    CEFR: 'CEFR',
    OET: 'OET',
    none: 'None',
  },
};

/**
 * 匹配理由文案。key 与 src/lib/match.ts 里的 Reason.code 一一对应。
 * 单独放一张表而不塞进 UI：理由句子里有数值插值，模板用 {v} 占位。
 */
export const MATCH_TEXT: Record<Lang, Record<string, string>> = {
  zh: {
    'm.statusOk': '护照资格符合',
    'm.statusNo': '护照资格不符合',
    'm.ageOk': '年龄在区间内',
    'm.ageLow': '年龄低于下限 {v}',
    'm.ageHigh': '年龄高于上限 {v}',
    'm.ageUnknown': '数据未标注年龄限制',
    'm.budgetOk': '资金证明门槛在预算内',
    'm.budgetLow': '资金证明需要 {v} 元，超出预算',
    'm.budgetUnknown': '资金要求本机无法折算，未计入',
    'm.eduOk': '学历达到门槛',
    'm.eduLow': '学历低于该项目门槛',
    'm.stayOk': '可停留 {v} 个月，满足预期',
    'm.stayLow': '最长只待 {v} 个月，短于预期',
    'm.stayUnknown': '停留期数据缺失',
    'm.paidOk': '带薪',
    'm.paidUnknown': '薪酬待遇未标注',
    'm.agencyOk': '不需要中介',
    'm.agencyNeeded': '需要通过指定机构办理',
    'm.regionOk': '在你倾向的地区',
    'm.regionNo': '不在你选的地区',
  },
  en: {
    'm.statusOk': 'Passport eligibility matches',
    'm.statusNo': 'Passport not eligible',
    'm.ageOk': 'Age within range',
    'm.ageLow': 'Below the minimum age of {v}',
    'm.ageHigh': 'Above the maximum age of {v}',
    'm.ageUnknown': 'No age limit recorded',
    'm.budgetOk': 'Proof-of-funds threshold is within budget',
    'm.budgetLow': 'Proof of funds needs {v}, above your budget',
    'm.budgetUnknown': 'Funds cannot be converted locally; not scored',
    'm.eduOk': 'Education meets the threshold',
    'm.eduLow': 'Education below this program threshold',
    'm.stayOk': 'Up to {v} months, meets your expectation',
    'm.stayLow': 'Only {v} months, shorter than expected',
    'm.stayUnknown': 'Stay length not recorded',
    'm.paidOk': 'Paid',
    'm.paidUnknown': 'Pay not recorded',
    'm.agencyOk': 'No agency required',
    'm.agencyNeeded': 'Must go through a designated agency',
    'm.regionOk': 'In a region you prefer',
    'm.regionNo': 'Not in your selected regions',
  },
};

/** 申请进度状态。顺序即看板列顺序。 */
export const TRACK_STATUS = ['todo', 'preparing', 'submitted', 'interview', 'offer', 'rejected'] as const;
export type TrackStatus = (typeof TRACK_STATUS)[number];

export const TRACK_TEXT: Record<Lang, Record<TrackStatus, string>> = {
  zh: {
    todo: '未开始',
    preparing: '准备材料',
    submitted: '已提交',
    interview: '面试中',
    offer: '已获录取',
    rejected: '未通过',
  },
  en: {
    todo: 'Not started',
    preparing: 'Preparing',
    submitted: 'Submitted',
    interview: 'Interviewing',
    offer: 'Offer',
    rejected: 'Unsuccessful',
  },
};
