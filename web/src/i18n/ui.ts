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
  | 'quota_capped'
  | 'quota_no_quota'
  | 'quota_not_published'
  | 'quota_unverified'
  | 'quotaConcurrent'
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
  | 'reportDataIssue'
  | 'guideAgeWall'
  | 'guideMisinfo'
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
  | 'navVerdict'
  | 'navWatch'
  | 'navCalendar'
  | 'navTrack'
  | 'navSaved'
  | 'navCompare'
  | 'navData'
  | 'navVerdictHint'
  | 'navWatchHint'
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
  | 'profileStudent'
  | 'studentEnrolled'
  | 'studentRecentGrad'
  | 'studentWorking'
  | 'statsWorking'
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
  // —— 复核台账（2026-11-10：复核周期由 data/review-policy.json 定义）——
  | 'dataDueSoon'
  | 'dataNextReview'
  | 'dataOverdueBy'
  | 'dataDueIn'
  | 'dataNoDate'
  | 'dataPendingTitle'
  | 'dataPendingNote'
  | 'statsDueSoon'
  // —— 申请看板的「下一步」（2026-11-10：窗口与材料准备期由数据算）——
  | 'nextUpTitle'
  | 'nextUpEmpty'
  | 'nextClose'
  | 'nextCloseUnknown'
  | 'nextPrep'
  | 'nextOpen'
  | 'nextClosed'
  | 'nextIdle'
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
  | 'ageUnit'
  // —— 新手引导（2026-11-09：首访说明模块用途与操作路径）——
  | 'onboardStep1Title'
  | 'onboardStep1Body'
  | 'onboardStep2Title'
  | 'onboardStep3Title'
  | 'onboardNext'
  | 'onboardSkip'
  | 'onboardExpand'
  | 'onboardCollapse'
  | 'onboardStart'
  | 'onboardReplay'
  | 'onboardStepOf'
  | 'onboardModuleCol'
  | 'onboardPath1'
  | 'onboardPath2'
  | 'onboardPath3'
  // —— 侧栏用途（桌面常驻，窄屏隐藏）——
  | 'navBrowseHint'
  | 'navMatchHint'
  | 'navCalendarHint'
  | 'calTitle'
  | 'calLede'
  | 'calLegendConfirmed'
  | 'calLegendInferred'
  | 'calLegendUnknown'
  | 'calSecConfirmed'
  | 'calSecConfirmedHint'
  | 'calSecInferred'
  | 'calSecInferredHint'
  | 'calSecUnknown'
  | 'calSecUnknownHint'
  | 'calStatusOpen'
  | 'calStatusUpcoming'
  | 'calStatusClosed'
  | 'calStatusAlways'
  | 'calStatusUnknown'
  | 'calNoDate'
  | 'calDays'
  | 'calShouldPrepare'
  | 'calPassed'
  | 'calInDays'
  | 'calClosingSoon'
  | 'calEmpty'
  | 'calFoot'
  | 'calFootLink'
  | 'navTrackHint'
  | 'navSavedHint'
  | 'navCompareHint'
  | 'navDataHint'
  // —— 学籍门槛筛选（在职者最需要的那一维）——
  | 'filterEnroll'
  | 'enrollNone'
  | 'enrollRequired'
  | 'enrollRecent'
  | 'enrollUnknown'
  // —— 空状态正文（标题复用既有 trackEmpty / savedEmpty / compareEmpty）——
  | 'trackEmptyBody'
  | 'savedEmptyBody'
  | 'compareEmptyBody'
  | 'emptyRecentCta'
  | 'compareIntro'
  | 'compareCountLabel'
  // —— 资格判定（M2：五项输入 → 三态结论）——
  | 'verdictTitle'
  | 'verdictIntro'
  | 'verdictProfileTitle'
  | 'verdictProfileDesc'
  | 'verdictPassport'
  | 'verdictAge'
  | 'verdictEdu'
  | 'verdictIelts'
  | 'verdictIeltsNone'
  | 'verdictIeltsHint'
  | 'verdictBudget'
  | 'verdictSubmit'
  | 'verdictSubmitHint'
  | 'verdictSaved'
  | 'verdictReset'
  | 'verdictResultTitle'
  | 'verdictEmpty'
  | 'verdictCountCan'
  | 'verdictCountGap'
  | 'verdictCountUnknown'
  | 'verdictCountCannot'
  | 'verdictSecCan'
  | 'verdictSecCanHint'
  | 'verdictSecGap'
  | 'verdictSecGapHint'
  | 'verdictSecUnknown'
  | 'verdictSecUnknownHint'
  | 'verdictSecCannot'
  | 'verdictSecCannotHint'
  | 'verdictDetailLink'
  | 'verdictDisclaimer'
  | 'verdictInferred'
  | 'verdictNoVerdicts'
  | 'verdictRulesVersion'
  | 'verdictDimPassport'
  | 'verdictDimAge'
  | 'verdictDimEdu'
  | 'verdictDimLang'
  | 'verdictDimFunds'
  | 'verdictDimPrecondition'
  // —— 追踪清单（M3：窗口状态 + 关键日期，滚动型不编日期）——
  | 'watchTitle'
  | 'watchIntro'
  | 'watchEmpty'
  | 'watchEmptyBody'
  | 'watchAdd'
  | 'watchAdded'
  | 'watchRemove'
  | 'watchClear'
  | 'watchStatusOpen'
  | 'watchStatusUpcoming'
  | 'watchStatusClosed'
  | 'watchStatusAlways'
  | 'watchStatusUnknown'
  | 'watchNoDate'
  | 'watchRolling'
  | 'watchInferred'
  | 'watchInferredHint'
  | 'watchConfirmed'
  | 'watchWindow'
  | 'watchLead'
  | 'watchDaysFromNow'
  | 'watchDaysAgo'
  | 'watchToday'
  | 'watchNeither'
  | 'watchNoWindowData'
  // —— 安装引导（M4）——
  | 'installTitle'
  | 'installCta'
  | 'installBody'
  | 'installAndroid'
  | 'installIOS'
  | 'installDesktop'
  | 'installDismiss'
  | 'installMenuHint';

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
    quota_capped: '有名额上限',
    quota_no_quota: '无名额上限',
    quota_not_published: '官方设限额，未公布数字',
    quota_unverified: '待核实',
    quotaConcurrent: '同时在册人数上限',
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
    guideAgeWall: '长文：打工度假的年龄墙',
    guideMisinfo: '长文：被中介包装过的五个说法',
    reportDataIssue: '发现数据有误？提纠错',
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
    navVerdict: '资格判定',
    navMatch: '智能匹配',
    navWatch: '追踪清单',
    navCalendar: '窗口日历',
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
    profileStudent: '当前身份',
    studentEnrolled: '在校（本科或硕士在读）',
    studentRecentGrad: '毕业 2 年内',
    studentWorking: '在职 / 毕业超过 2 年',
    // {n} 由 ListView 插值。括号样式随语言变：中文全角、英文半角，
    // 数字位置也不同（中英都是「标签 + 数字」，所以只改括号与分隔符）。
    statsWorking: '（在职可申 {n}）',
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
    dataStale: '已超复核周期',
    dataRules: '收录规则',
    dataDueSoon: '即将到期',
    dataNextReview: '下次复核',
    dataOverdueBy: '已超 {n} 天',
    dataDueIn: '还剩 {n} 天',
    dataNoDate: '缺核实日期',
    dataPendingTitle: '该重新核这些了',
    dataPendingNote:
      '复核周期写在仓库的 data/review-policy.json 里：窗口写死到具体日期的项目 90 天核一次，其余 180 天。周期到了不一定会变，但没核过就不能说它还准。',
    statsDueSoon: '即将到期',
    nextUpTitle: '今天先做这几件',
    nextUpEmpty: '眼下没有要动手的事。窗口开放前这里会亮起来。',
    nextClose: '窗口还剩 {n} 天，{date} 截止——材料没交就来不及了',
    nextCloseUnknown: '窗口已开，官方没写截止日',
    nextPrep: '窗口 {n} 天后（{date}）开放，材料要 {prep} 天准备，现在就该动手',
    nextOpen: '窗口 {n} 天后（{date}）开放，材料准备期还没压上来',
    nextClosed: '上一轮 {date} 已结束，下一轮日期未公布——先备材料，别等公告',
    nextIdle: '窗口日期官方未公布，只能盯官网',

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

    // —— 新手引导 ——
    onboardStep1Title: '这里只回答一个问题：大陆护照，你能申哪些？',
    onboardStep1Body:
      '收录 {n} 条，每条都挂着官方链接和核实日期。「可申」只代表护照资格——年龄、学历、在读状态写在每一条里面。',
    onboardStep2Title: '六个模块分别做什么',
    onboardStep3Title: '三步拿到第一条结论',
    onboardNext: '下一步',
    onboardSkip: '跳过',
    onboardExpand: '展开看怎么用',
    onboardCollapse: '收起',
    onboardStart: '开始用',
    onboardReplay: '重看新手引导',
    onboardStepOf: '第 {i} 步 / 共 3 步',
    onboardModuleCol: '模块 → 你在这里做什么',
    onboardPath1: '点「我的资格」里的「大陆护照可申」，26 条会收窄到能申的那些',
    onboardPath2: '点开一条，先读标题下面那行判定——它只讲护照资格，其余门槛在「申请资格」区',
    onboardPath3: '拿不准就点星号收藏，回头在「收藏」里并排比',
    navBrowseHint: '全量列表，按资格筛',
    navMatchHint: '填条件，按匹配度排序',
    navVerdictHint: '五项条件，逐条判能不能申',
    navWatchHint: '关注的项目，窗口一目了然',
    navCalendarHint: '什么时候开、什么时候该准备',
    calTitle: '窗口日历',
    calLede: '每个项目的开放窗口，按「这个日期可不可信」分成三块。官方公布的和按规律推断的永远分开显示——把推断出来的日期摆在官方日期旁边，读者分不出来，就一定会有人按错的日子准备材料。',
    calLegendConfirmed: '官方已公布',
    calLegendInferred: '按规律推断',
    calLegendUnknown: '无从判断',
    calSecConfirmed: '① 官方已公布日期',
    calSecConfirmedHint: '可以直接按这个安排',
    calSecInferred: '② 按往年规律推断',
    calSecInferredHint: '只作参考，不是官方日期',
    calSecUnknown: '③ 无从判断 / 无窗口',
    calSecUnknownHint: '只能盯官方页面，不给日期',
    calStatusOpen: '开放中',
    calStatusUpcoming: '未开始',
    calStatusClosed: '已关闭',
    calStatusAlways: '随时可申',
    calStatusUnknown: '未知',
    calNoDate: '无确定日期',
    calDays: '天',
    calShouldPrepare: '现在就该准备',
    calPassed: '这一轮已过',
    calInDays: '还有',
    calClosingSoon: '两周内截止',
    calEmpty: '暂无',
    calFoot: '提醒日 = 开放日 − 建议提前天数。这个算法只有一处实现（scripts/build_calendar.py），页面不另算一套。想让某个项目的准备期更宽，改数据里的 lead_time_days，不要改这里。',
    calFootLink: '看一个例子：新西兰打工度假',
    navTrackHint: '记录每条申请进度',
    navSavedHint: '想再看一眼的放这',
    navCompareHint: '最多 4 条并排比',
    navDataHint: '来源、核实日期、缺口',
    filterEnroll: '学籍门槛',
    enrollNone: '不要求学籍',
    enrollRequired: '须在读',
    enrollRecent: '在读或毕业不久',
    enrollUnknown: '官方未公布',
    trackEmptyBody:
      '你在跟进的每条项目会占一行：一个状态（未开始 → 准备材料 → 已提交 → 面试中 → 已获录取 / 未通过）加一句备注。只存在这台设备。',
    savedEmptyBody:
      '收藏是给「还想再看一眼」的项目留位置，不是决定。卡片右下角的星号、详情页的「收藏」按钮都能加。',
    compareEmptyBody:
      '最多放 4 条，并排看年龄、停留期、资金证明、风险与核实日期。三条都差不多、只差细节时最有用。',
    emptyRecentCta: '从最近看过的开始',
    compareIntro: '同一行看同一字段，差异才会跳出来。最多 4 条。',
    compareCountLabel: '已选',

    // —— 资格判定 ——
    verdictTitle: '资格判定',
    verdictIntro:
      '填五项条件，逐条给出「能申 / 差什么 / 不能申」。判定只用仓内已核实的字段，算不出来的会明说「不可判」，不猜。',
    verdictProfileTitle: '你的条件',
    verdictProfileDesc:
      '五项都只影响这一次判定。填完自动保存在本机，刷新不用重填，也不会发到任何服务器。',
    verdictPassport: '护照',
    verdictAge: '年龄',
    verdictEdu: '最高学历',
    verdictIelts: '雅思总分',
    verdictIeltsNone: '没考过 / 不填',
    verdictIeltsHint: '没考过就选「没考过」。这与「考了但项目没登记分数线」是两件事，会影响结论。',
    verdictBudget: '可动用的资金证明（人民币）',
    verdictSubmit: '开始判定',
    verdictSubmitHint: '判定在你自己的浏览器里完成，不发服务器。',
    verdictSaved: '条件已存本机',
    verdictReset: '清空条件',
    verdictResultTitle: '判定结果',
    verdictEmpty: '填完上面五项条件后点「开始判定」，这里会按三态列出来。',
    verdictCountCan: '能申',
    verdictCountGap: '差什么',
    verdictCountUnknown: '不可判',
    verdictCountCannot: '不能申',
    verdictSecCan: '能申',
    verdictSecCanHint: '五项条件都满足，或该项目不设这一维的门槛。',
    verdictSecGap: '差什么',
    verdictSecGapHint: '有一项能补——差多少已经算出来，补上就够。',
    verdictSecUnknown: '不可判',
    verdictSecUnknownHint: '官方没公布，或仓内没登记到能比的数字。这类不替你担保，请点开详情页核对官网。',
    verdictSecCannot: '不能申',
    verdictSecCannotHint: '有硬性条件不符，补材料也绕不过去。原因写在每一条下面。',
    verdictDetailLink: '看官方原文与缺口',
    verdictDisclaimer:
      '判定是对照仓内数据的机械比较，不等于签证结果。递交前请点开每条项目核对官方原文——「能申」只表示数据里没有拦你的条款。',
    verdictInferred: '据官方「不按国籍设限」推出',
    verdictNoVerdicts: '没有算得出结论的项目。',
    verdictRulesVersion: '判定口径',
    verdictDimPassport: '护照资格',
    verdictDimAge: '年龄',
    verdictDimEdu: '学历',
    verdictDimLang: '语言',
    verdictDimFunds: '资金证明',
  verdictDimPrecondition: '前置身份',

    // —— 追踪清单 ——
    watchTitle: '追踪清单',
    watchIntro:
      '把关心的项目放进来，汇总看它们的申请窗口。滚动型项目显示「常年可申」，只有推算日期的不当官方日期写。',
    watchEmpty: '清单还是空的',
    watchEmptyBody:
      '在项目页点「加入追踪」，或在判定结果里逐条加入。清单只存这台设备，换设备不同步。',
    watchAdd: '加入追踪',
    watchAdded: '已在清单',
    watchRemove: '移除',
    watchClear: '清空清单',
    watchStatusOpen: '窗口开放中',
    watchStatusUpcoming: '尚未开放',
    watchStatusClosed: '本轮已截止',
    watchStatusAlways: '常年可申',
    watchStatusUnknown: '日期未公布',
    watchNoDate: '官方未公布日期',
    watchRolling: '常年可申，无申请窗口',
    watchInferred: '参考日期（未确认）',
    watchInferredHint: '按往年规律推算，不是官方公布的日期，不要拿它卡时间。',
    watchConfirmed: '官方已公布',
    watchWindow: '申请窗口',
    watchLead: '建议提前',
    watchDaysFromNow: '还有 {n} 天',
    watchDaysAgo: '已过 {n} 天',
    watchToday: '就是今天',
    watchNeither: '未加入任何项目，也没有可汇总的窗口。',
    watchNoWindowData: '这条项目在仓内没有窗口数据，只能盯官网。',

    // —— 安装引导 ——
    installTitle: '装到桌面，当应用打开',
    installCta: '现在安装',
    installBody: '装好后有独立图标、全屏无地址栏，条件与追踪清单照旧存在本机。',
    installAndroid: '安卓 Chrome：右上角 ⋮ → 「安装应用」或「添加到主屏幕」。',
    installIOS: 'iPhone / iPad Safari：底部分享按钮 → 「添加到主屏幕」。',
    installDesktop: '桌面 Chrome / Edge：地址栏右侧的安装图标，或菜单里的「安装」。',
    installDismiss: '知道了',
    installMenuHint: '浏览器菜单里找「安装」或「添加到主屏幕」',
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
    quota_capped: 'Capped',
    quota_no_quota: 'No quota cap',
    quota_not_published: 'Capped, number not published',
    quota_unverified: 'Not verified yet',
    quotaConcurrent: 'cap on concurrent pass holders',
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
    guideAgeWall: 'Long read: the working holiday age wall',
    guideMisinfo: 'Long read: five claims that agencies dress up',
    reportDataIssue: 'Spotted an error? Report it',
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
    navVerdict: 'Eligibility',
    navMatch: 'Smart match',
    navWatch: 'Watchlist',
    navCalendar: 'Calendar',
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
    profileStudent: 'Current status',
    studentEnrolled: 'Enrolled (undergrad or postgrad)',
    studentRecentGrad: 'Graduated within 2 years',
    studentWorking: 'Working / graduated over 2 years ago',
    statsWorking: '({n} open to workers)',
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
    dataStale: 'Past the re-check date',
    dataRules: 'Inclusion rules',
    dataDueSoon: 'Due soon',
    dataNextReview: 'Next re-check',
    dataOverdueBy: '{n} days overdue',
    dataDueIn: '{n} days left',
    dataNoDate: 'No verification date',
    dataPendingTitle: 'These need re-checking',
    dataPendingNote:
      'The schedule lives in data/review-policy.json: entries with hard-coded application windows are re-checked every 90 days, the rest every 180. Nothing is guaranteed to have changed by then — but an entry past its date cannot claim to still be current.',
    statsDueSoon: 'due soon',
    nextUpTitle: 'Do these first',
    nextUpEmpty: 'Nothing to do right now. This lights up before a window opens.',
    nextClose: '{n} days left — closes {date}. Prepare or wait a year',
    nextCloseUnknown: 'Window is open; the authority did not publish a closing date',
    nextPrep: 'Opens in {n} days ({date}). Documents take {prep} days — start now',
    nextOpen: 'Opens in {n} days ({date}); preparation has not become urgent yet',
    nextClosed: 'Last round closed {date}. Next dates unpublished — prepare now, do not wait',
    nextIdle: 'No published window dates — watch the official site',

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

    // —— onboarding ——
    onboardStep1Title: 'One question: which programs a mainland Chinese passport can actually apply to',
    onboardStep1Body:
      '{n} programs, each with an official link and the date it was checked. "Open" means passport eligibility only — age, degree and student status sit inside each entry.',
    onboardStep2Title: 'What each section does',
    onboardStep3Title: 'Three steps to your first answer',
    onboardNext: 'Next',
    onboardSkip: 'Skip',
    onboardExpand: 'See how to use it',
    onboardCollapse: 'Collapse',
    onboardStart: 'Start',
    onboardReplay: 'Show the intro again',
    onboardStepOf: 'Step {i} of 3',
    onboardModuleCol: 'Section → what you do there',
    onboardPath1:
      'Take "Open to mainland China" under My eligibility — the 26 entries narrow to the ones you can apply to',
    onboardPath2:
      'Open a program and read the verdict under its title — it covers passport eligibility only; the rest sits in the eligibility table',
    onboardPath3:
      'Unsure? Star it and compare side by side later under Saved',
    navBrowseHint: 'All entries, filtered',
    navMatchHint: 'Enter a profile, get a ranking',
    navVerdictHint: 'Five inputs, one verdict per program',
    navWatchHint: 'The programs you follow, windows in one view',
    navCalendarHint: 'When windows open, and when to prepare',
    calTitle: 'Application calendar',
    calLede: 'Every program application window, split into three blocks by how much the date can be trusted. Officially published dates never sit next to inferred ones — mixing them is how people end up preparing against the wrong day.',
    calLegendConfirmed: 'Officially published',
    calLegendInferred: 'Inferred from past years',
    calLegendUnknown: 'Not determinable',
    calSecConfirmed: '1. Officially published dates',
    calSecConfirmedHint: 'Safe to plan against',
    calSecInferred: '2. Inferred from previous years',
    calSecInferredHint: 'Reference only — not official dates',
    calSecUnknown: '3. Not determinable / no window',
    calSecUnknownHint: 'Watch the official page; no dates given',
    calStatusOpen: 'Open',
    calStatusUpcoming: 'Not yet open',
    calStatusClosed: 'Closed',
    calStatusAlways: 'Always open',
    calStatusUnknown: 'Unknown',
    calNoDate: 'No confirmed date',
    calDays: 'days',
    calShouldPrepare: 'Start preparing now',
    calPassed: 'This round has passed',
    calInDays: 'in',
    calClosingSoon: 'Closes within 2 weeks',
    calEmpty: 'None',
    calFoot: 'Reminder date = opening date minus lead time. That calculation lives in one place only (scripts/build_calendar.py); this page does not re-derive it. To widen the prep window for a program, change lead_time_days in the data, not here.',
    calFootLink: 'See an example: New Zealand working holiday',
    navTrackHint: 'One status per program',
    navSavedHint: 'Keep what you want to revisit',
    navCompareHint: 'Up to 4, field by field',
    navDataHint: 'Sources, dates, what is missing',
    filterEnroll: 'Student status',
    enrollNone: 'No enrolment needed',
    enrollRequired: 'Must be enrolled',
    enrollRecent: 'Enrolled or recent graduate',
    enrollUnknown: 'Not stated officially',
    trackEmptyBody:
      'Each program you follow gets one row: a status (Not started → Preparing → Submitted → Interviewing → Offer / Unsuccessful) and a note. Stored on this device.',
    savedEmptyBody:
      'Saving keeps a program on your shortlist — it is not a decision. Use the star on a card, or Save on a program page.',
    compareEmptyBody:
      'Add up to 4 programs and read age, stay length, funds, risks and verification date across one row. Most useful when a few look alike and the difference is in the details.',
    emptyRecentCta: 'Start from something you viewed',
    compareIntro: 'Read one field across every column — that is where the difference shows. Up to 4.',
    compareCountLabel: 'Selected',

    // —— Eligibility verdict ——
    verdictTitle: 'Eligibility check',
    verdictIntro:
      'Enter five conditions and get a verdict per program: eligible, one thing missing, or not eligible. Values come from verified fields only — where the data cannot decide, it says so instead of guessing.',
    verdictProfileTitle: 'Your details',
    verdictProfileDesc:
      'These five inputs only affect this check. They stay in this browser, survive a refresh, and are never sent to a server.',
    verdictPassport: 'Passport',
    verdictAge: 'Age',
    verdictEdu: 'Highest education',
    verdictIelts: 'IELTS overall',
    verdictIeltsNone: 'Not taken / leave blank',
    verdictIeltsHint:
      'Pick "Not taken" if you have no score. That is different from having a score a program does not publish a threshold for, and the verdict differs.',
    verdictBudget: 'Funds available for proof (CNY)',
    verdictSubmit: 'Run the check',
    verdictSubmitHint: 'The check runs in your browser. Nothing is uploaded.',
    verdictSaved: 'Saved on this device',
    verdictReset: 'Clear',
    verdictResultTitle: 'Verdicts',
    verdictEmpty: 'Fill in the five conditions and run the check — results appear here grouped by verdict.',
    verdictCountCan: 'Eligible',
    verdictCountGap: 'One gap',
    verdictCountUnknown: 'Undecidable',
    verdictCountCannot: 'Not eligible',
    verdictSecCan: 'Eligible',
    verdictSecCanHint: 'All five conditions are met, or the program sets no threshold on that dimension.',
    verdictSecGap: 'One gap',
    verdictSecGapHint: 'Something is fixable — the shortfall is calculated, and closing it is enough.',
    verdictSecUnknown: 'Undecidable',
    verdictSecUnknownHint:
      'The official page does not publish it, or the dataset has no comparable figure. Not vouched for either way — open the program page and check the source.',
    verdictSecCannot: 'Not eligible',
    verdictSecCannotHint: 'A hard condition fails; extra documents will not change it. The reason sits under each entry.',
    verdictDetailLink: 'Official source and gaps',
    verdictDisclaimer:
      'This is a mechanical comparison against the dataset, not a visa decision. Open each program and confirm against the official text before applying — "eligible" only means nothing in the data rules you out.',
    verdictInferred: 'Inferred from the official "no nationality restriction" wording',
    verdictNoVerdicts: 'No program produced a verdict.',
    verdictRulesVersion: 'Rules version',
    verdictDimPassport: 'Passport',
    verdictDimAge: 'Age',
    verdictDimEdu: 'Education',
    verdictDimLang: 'Language',
    verdictDimFunds: 'Proof of funds',
  verdictDimPrecondition: 'Prior status',

    // —— Watchlist ——
    watchTitle: 'Watchlist',
    watchIntro:
      'Collect the programs you care about and read their application windows in one place. Rolling programs show "open year-round"; inferred dates are never presented as official.',
    watchEmpty: 'Nothing on the watchlist yet',
    watchEmptyBody:
      'Use "Add to watchlist" on a program page, or add entries from the verdict results. The list lives on this device only.',
    watchAdd: 'Add to watchlist',
    watchAdded: 'On watchlist',
    watchRemove: 'Remove',
    watchClear: 'Clear watchlist',
    watchStatusOpen: 'Window open',
    watchStatusUpcoming: 'Not open yet',
    watchStatusClosed: 'Closed for this round',
    watchStatusAlways: 'Open year-round',
    watchStatusUnknown: 'Dates not published',
    watchNoDate: 'No date published',
    watchRolling: 'Open year-round, no application window',
    watchInferred: 'Reference date (unconfirmed)',
    watchInferredHint: 'Projected from past cycles. Not an official date — do not schedule against it.',
    watchConfirmed: 'Published by the authority',
    watchWindow: 'Application window',
    watchLead: 'Prepare by',
    watchDaysFromNow: '{n} days away',
    watchDaysAgo: '{n} days ago',
    watchToday: 'Today',
    watchNeither: 'No programs on the list, so there is no window to summarise.',
    watchNoWindowData: 'The dataset holds no window for this program; the official site is the only source.',

    // —— Install guidance ——
    installTitle: 'Install it like an app',
    installCta: 'Install now',
    installBody:
      'It gets its own icon and runs without browser chrome. Your conditions and watchlist stay on this device.',
    installAndroid: 'Android Chrome: menu ⋮ → "Install app" or "Add to Home screen".',
    installIOS: 'iPhone / iPad Safari: Share → "Add to Home Screen".',
    installDesktop: 'Desktop Chrome / Edge: the install icon in the address bar, or "Install" in the menu.',
    installDismiss: 'Got it',
    installMenuHint: 'Look for "Install" or "Add to Home screen" in the browser menu',
  },
};

/** 枚举值 → 界面标签。数据里的枚举是机器可读英文，展示要本地化。 */
export const ENUM_LABELS: Record<Lang, Record<string, string>> = {  zh: {
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
    'm.studentOk': '接受在校生，且要求全程保持学籍',
    'm.studentFree': '不要求在读，任何身份都能申',
    'm.studentNeeded': '要求在读证明并全程保持学籍，在职者无法申请',
    'm.studentRecentOk': '在读或毕业 2 年内可申',
    'm.studentTooLate': '只接受在读或毕业 2 年内，超过这个窗口无法申请',
    'm.studentUnknown': '官方未公布身份门槛，需自行向官方确认',
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
    'm.studentOk': 'Open to students; you must stay enrolled throughout',
    'm.studentFree': 'No enrolment required; open to any status',
    'm.studentNeeded': 'Requires proof of enrolment; not open to workers',
    'm.studentRecentOk': 'Open while enrolled or within 2 years of graduating',
    'm.studentTooLate': 'Only while enrolled or within 2 years of graduating',
    'm.studentUnknown': 'Enrolment requirement not published; confirm with the sponsor',
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

/**
 * 判定结论文案。key 与 src/lib/verdict.ts 的 DimVerdict.code 一一对应——
 * 两边同名同义，smoke-test 会检查每个 code 都有 zh 与 en 两条文案，
 * 否则界面会露出 v.lang_missing 这种裸 key。
 * 模板占位：{need} 门槛、{have} 本人条件。
 */
export const VERDICT_TEXT: Record<Lang, Record<string, string>> = {
  zh: {
    passport_ok: '护照已登记可申',
    passport_no: '该护照明确不可申',
    passport_open: '官方未按国籍设限',
    passport_conditional: '有条件开放，需查当年公告',
    passport_unknown: '官方未核实该护照资格',
    passport_missing: '该护照未登记，且无明文结论',
    age_ok: '年龄在要求区间内',
    age_low: '年龄低于下限：要求 {need}，你是 {have}',
    age_high: '年龄超出上限：要求 {need}，你是 {have}',
    age_none: '该项目不限年龄',
    age_unknown: '官方未公布年龄限制，无法判定',
    edu_ok: '学历达到门槛',
    edu_low: '学历低于门槛：要求 {need}',
    edu_years_unknown: '另要求 {need}，在读无法从你填的信息判定',
    edu_recency_unknown: '另要求 {need}；你的毕业时间未采集，无法判定是否在时限内',
    edu_category_unknown: '原文限定了参与人身份类别，是否成立由 Sponsor 判断；画像只采集学历层级，无法判定',
    edu_place_unknown: '原文要求学位在指定国家/名单内院校完成，院校与毕业年份未采集，无法判定',
    edu_by_sponsor: '原文写明学历层级由 Sponsor 判断，不作硬性门槛',
    lang_ok: '语言成绩达标',
    lang_low: '语言成绩不够：要求 {need}，你是 {have}',
    lang_missing: '要求语言成绩，你没填：需要 {need}',
    lang_none: '该项目不要求语言成绩',
    lang_by_design: '官方不设分数线（面试或自证）',
    lang_cefr: '官方用 CEFR/CLB 档位表述，仓内无对照表，无法判定',
    lang_no_score: '要求语言证明，但仓内未登记分数线',
    lang_no_test: '官方不要求任何标准化语言考试（由项目方测试或雇主面试把关）',
    funds_ok: '资金证明门槛在可动用范围内',
    funds_short: '资金证明不够：需要 {need}，你能提供 {have}',
    funds_none: '该项目不要求资金证明',
    funds_by_design: '要求资金证明但官方不设固定金额（递交时自证）',
    funds_unknown: '要求资金证明但未登记金额，无法判定',
    funds_income_basis: '该门槛是年收入（{need}）而非存款，与你填的可动用资金不是同一口径，需按官网核对',
    funds_term_unknown: '该门槛是每月金额（{need}），须乘停留月数才是总额；仓内未登记停留期上限，无法折算',
    funds_amount_inferred: '该金额（{need}）在仓内标注为按同类口径沿用/归类推定，不是本项目的独立规定，不作达标判断',
    pre_local_status: '原文把「先在该国持学生签/居留并完成学业」写成本项目的前置身份：{need}',
    pre_outside_country: '原文要求在递交时人位于该国境外，画像不采集现居地，无法判定',
    pre_home_residence: '原文要求常驻护照所属地区，画像不采集现居地，无法判定',
    pre_citizenship_basis: '原文该项是国籍条件，已由护照维判定，不另算缺口',
    pre_document_basis: '原文该项是递交时自备的材料（租约等），不是身份前置条件',
    pre_unclassified: '该项目有一条必填的前置身份/在地要求，原文类别未能识别，无法判定',
    pre_job_placement: '原文要求岗位须预先落实：{need}；这一步可以补（报名、面试、拿到 placement）',
  },
  en: {
    passport_ok: 'Passport recorded as eligible',
    passport_no: 'This passport is explicitly not eligible',
    passport_open: 'The authority sets no nationality restriction',
    passport_conditional: 'Conditionally open — check the current announcement',
    passport_unknown: 'Passport eligibility not verified',
    passport_missing: 'This passport is neither listed nor ruled out',
    age_ok: 'Age is within the required range',
    age_low: 'Below the minimum age: requires {need}, you are {have}',
    age_high: 'Above the maximum age: requires {need}, you are {have}',
    age_none: 'No age limit for this program',
    age_unknown: 'The authority publishes no age limit — cannot decide',
    edu_ok: 'Education meets the threshold',
    edu_low: 'Education is below the threshold: requires {need}',
    edu_years_unknown: 'Also requires {need}; not decidable from what you entered as a current student',
    edu_recency_unknown:
      'Also requires {need}; your graduation date is not collected, so whether you are within that window cannot be decided',
    edu_category_unknown:
      'The source limits eligibility to certain participant categories and leaves that call to the sponsor; only your education level is collected — cannot decide',
    edu_place_unknown:
      'The source requires the degree to come from an institution in a specified country or on an approved list; your institution and graduation year are not collected — cannot decide',
    edu_by_sponsor:
      'The source states the degree level is judged by the sponsor, not set as a hard threshold',
    lang_ok: 'Language score meets the requirement',
    lang_low: 'Language score is short: requires {need}, you have {have}',
    lang_missing: 'A language score is required and you entered none: needs {need}',
    lang_none: 'No language score required',
    lang_by_design: 'No published threshold (interview or self-certified)',
    lang_cefr: 'Stated as a CEFR/CLB level; no conversion table in the dataset, cannot decide',
    lang_no_score: 'A language proof is required but no threshold is recorded',
    lang_no_test: 'No standardised language test is required (programme test or employer interview applies)',
    funds_ok: 'Proof-of-funds threshold is within what you can show',
    funds_short: 'Proof of funds falls short: needs {need}, you can show {have}',
    funds_none: 'No proof of funds required',
    funds_by_design: 'Proof required but no fixed amount is published (self-certified on submission)',
    funds_unknown: 'Proof required but no amount recorded — cannot decide',
    funds_income_basis:
      'This threshold is annual income ({need}), not savings — a different basis from the funds you entered; check the official page',
    funds_term_unknown:
      'This threshold is a monthly amount ({need}); it must be multiplied by the months of stay, and no maximum stay is recorded here — cannot convert',
    funds_amount_inferred:
      'This amount ({need}) is marked in the dataset as borrowed from a comparable category / an inferred figure, not a rule of this permit — no pass/fail judgement',
    pre_local_status:
      'The source makes a prior status a prerequisite: you must already hold a student permit/residence there and have completed study there — {need}',
    pre_outside_country:
      'The source requires you to be outside that country when applying; your current location is not collected — cannot decide',
    pre_home_residence:
      'The source requires you to be residing in your passport region; your current location is not collected — cannot decide',
    pre_citizenship_basis:
      'This condition is a nationality rule and is already decided by the passport dimension — not counted as a separate gap',
    pre_document_basis:
      'This condition is a document you provide at application (a lease, etc.), not a prior-status prerequisite',
    pre_unclassified:
      'This program has a mandatory prior-status / location requirement whose category could not be recognised in the source text — cannot decide',
    pre_job_placement:
      'The source requires the placement to be arranged in advance: {need} — you have not recorded a placement yet, and this is a step you can still complete',
  },
};

/** 申请进度状态。顺序即看板列顺序。 */
export const TRACK_STATUS = ['todo', 'preparing', 'submitted', 'interview', 'offer', 'rejected'] as const;export type TrackStatus = (typeof TRACK_STATUS)[number];

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
