# P2-9「存在废弃副本」排查

**日期**：2026-10-31
**对应**：`docs/HANDOVER.md` §4 P2-9（原文仅一句「存在废弃副本」，未指明对象）
**仓库**：`3726d56`

---

## 一、结论

**程序读取的路径里没有废弃副本。** `data/programs/` 11 个文件对应 11 个唯一 id，文件名与 id 全部一致；全仓库 96 个受控文件**零字节级重复**；无 `backup/old/copy/draft/副本` 类命名；`web/deploy/` 已随 `git mv` 消失。

**但找到一处真正的「第二份数据」：`data/sources.md`。** 它不是废弃副本，是**手工维护的同源清单**，已与 JSON 漂移：

| 指标 | 数值 |
|---|---|
| `sources.md` 列出的 URL | 28 |
| 11 个 program JSON 的 URL（`official_url` + 全部 `sources[].url`） | 37 |
| 只在 md 有、JSON 没有 | **9** |
| 只在 JSON 有、md 没有 | **18** |
| md 自称核实日期 | 全部 `2026-09-17`（已过时 44 天） |
| JSON 实际 `last_verified` | 2026-10-29 / 2026-10-30 |

它不被任何脚本读取（`validate.py`、`sync-data.mjs`、两个 workflow 都只读 `data/programs/`），但 `README.md`、`CHANGELOG.md`、`docs/HANDOVER.md` 三处都把它当「官方来源清单」指向读者。也就是：**读者会被引到一份 44 天前、缺 18 条来源的清单上**。

---

## 二、逐条排查证据

判定「废弃副本」的四条标准，逐条实测：

| # | 标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | 同一 `program.id` 出现在多个文件 | **无** | `git ls-files data/programs/*.json` = 11 个；`program.id` 唯一 11 个，无重复；文件名与 id 无一处不一致 |
| 2 | 文件与 `program.id` 不一致 | **无** | 同上，逐个比对文件名去 `.json` 与 `program.id` |
| 3 | 字节级内容重复 | **无** | 全仓库 96 个受控文件 sha256 分组，重复组 **0** |
| 4 | 不被任何消费方引用的 data 类文件 | **1 个：`data/sources.md`** | `grep -rn "data/programs"` 在 `scripts/validate.py`、`web/scripts/sync-data.mjs`、`.github/workflows/validate.yml`、`.github/workflows/pages.yml` 全部命中；`data/sources.md` 在代码侧零引用，仅 README/CHANGELOG/HANDOVER 文档提及 |

补充检查：

- `web/deploy/` → **不存在**（`pages.yml` 早已 `git mv` 到 `.github/workflows/`，只剩 README 目录树里删过此行）
- `git ls-files | grep -iE "bak|backup|copy|old|orig|tmp|draft|副本|~$"` → **无命中**
- `web/i18n-src/merged.json`（本地合并中间产物）→ 已 gitignore，未入库，不算副本
- `web/tsconfig.tsbuildinfo` / `tsconfig.node.tsbuildinfo` → 已 gitignore
- `docs/audit/` 三份文档互不重复，分别是 links 审计、ego 独立验证、链接检查器偏差

---

## 三、`data/sources.md` 漂移明细

### 只在 md 里（JSON 已不引用，9 条）

```
http://learngive.cn/iaeste
https://anabin.kmk.org/anabin.html
https://ceac.state.gov/genniv/
https://online.immi.gov.au/lusc/login
https://onlineservices.immigration.govt.nz/?WHS
https://www.cn.emb-japan.go.jp/
https://www.hikorea.go.kr
https://www.irishimmigration.ie/
https://www.ustraveldocs.com/cn_zh/
```

这批里有一半是可解释的——它们是**办理入口**（ImmiAccount 登录、新西兰在线申请、CEAC 填表、ustraveldocs 预约、韩国 HiKorea），不是资格依据。但 `https://www.irishimmigration.ie/` 正是 P1 阶段判定「首页不含任何 WHA 内容」的那个 URL，md 仍在用它当来源，等于把已被否定的引用留在清单里。

### 只在 JSON 里（md 缺，18 条）

按项目归组：

| 项目 | 缺口 |
|---|---|
| 澳大利亚 | `first-work-holiday-462`、`new-work-and-holiday-subclass-462-visa-pre-application-process`（抽签专页） |
| 加拿大 | `iec/eligibility.html`、`iec/eligibility/eligibility-by-country.html`（36 国年龄矩阵就在这页） |
| 德国 | `gesetze-im-internet.de/aufenthg_2004/__16e.html`（§16e 法条原文，2026-10-30 新加的主源） |
| 爱尔兰 | `ireland.ie/en/dfa/visas-for-ireland/working-holiday-authorisation/`、两片官方 PDF（2026 申请表、台湾指南） |
| 日本 | `mofa.go.jp/mofaj/toko/visa/tetsuzuki/pagew_000001_02672.html`（査証手数料页，费用 15,000 日元的唯一依据） |
| 韩国 | `whic.mofa.go.kr` 正文页 + 英文 PDF |
| 英国 | `gov.uk/youth-mobility/eligibility`、`gov.uk/youth-mobility/documents-you-must-provide` |
| IAESTE | `iaeste.org/student-faqs`（学历门槛的唯一原文出处）、`iaeste.org/member-countries/china-hlg` |
| AIESEC | `opportunitynest.org/...`（已降级为二手，但仍在 JSON 里） |
| 澳门 | `gao.um.edu.mo?lang=zh-hant&p=7735/` |

**最要紧的两条**：`gesetze-im-internet.de` 与 `mofa.go.jp/mofaj/.../02672.html` 是 P0-A 阶段新确立的**唯一 A 级依据**，sources.md 里完全没有。读者按 md 去核德国 §16e 或日本费用，会找不到支撑。

### 日期声明过时

md 头部写「所有来源的最后核实日期为 `2026-09-17`」。实际 11 个 JSON 的 `last_verified` 已经是 2026-10-29（ca-iec、jp）与 2026-10-30（其余 9 个）。这句现在是**错的**，而且错在「让人以为数据没更新过」。

---

## 四、处理建议（三选一，需你拍板）

| 方案 | 做法 | 成本 | 副作用 |
|---|---|---|---|
| **A. 生成而非手写**（推荐） | 写 `scripts/gen-sources-md.py`，从 11 个 JSON 抽出 `official_url` + `sources[]`，按国家分组生成 `data/sources.md`；CI 加一步「生成结果与仓库内文件一致，否则失败」 | 约 40 分钟 | md 变成派生物，手工编辑会被 CI 打回；但从此不可能漂移 |
| B. 只修日期与缺口 | 手工补 18 条、删 9 条、日期改 2026-10-30 | 约 20 分钟 | 下次改数据还会漂移，治标 |
| C. 删除 md | 从 README/CHANGELOG/HANDOVER 摘掉指向，说明「来源以各 JSON 的 `sources[]` 为准」 | 约 10 分钟 | 少一份人可读的清单，非技术读者更难看 |

我倾向 **A**：这个项目的立身之本是「每条判定可追溯到官方」，那么「来源清单」必须由数据生成，不能手工维护——手工维护的清单迟早说谎，而这里已经说了 44 天。

**未做任何修改。** `data/sources.md` 不在 T2 授权范围内（授权只到 `data/programs/*.json`、`scripts/validate.py`、`tests/test_validate.py`），本轮只做排查与留证。

---

## 五、可复现命令

```bash
# 1. id 唯一性与文件名一致性
cd F:/2026-09-17-20-35-22/overseas-program-dataset
python -c "import json,glob,collections;c=collections.Counter(json.load(open(f,encoding='utf-8'))['program']['id'] for f in glob.glob('data/programs/*.json'));print(len(c),[k for k,v in c.items() if v>1])"

# 2. 全仓库字节级重复
python -c "import hashlib,subprocess;from collections import defaultdict;h=defaultdict(list);[h[hashlib.sha256(open(f,'rb').read()).hexdigest()].append(f) for f in subprocess.run(['git','ls-files'],capture_output=True).stdout.decode().split()];print({k:v for k,v in h.items() if len(v)>1})"

# 3. sources.md 与 JSON 的 URL 差集
python -c "import json,glob,re;md=set(re.findall(r'https?://[^\s|)]+',open('data/sources.md',encoding='utf-8').read()));j=set();[j.update([d['program']['official_url']]+[s['url'] for s in d.get('sources',[])]) for d in (json.load(open(f,encoding='utf-8')) for f in glob.glob('data/programs/*.json'))];print('md only',len(md-j),'json only',len(j-md))"

# 4. 可疑文件名
git ls-files | grep -iE "bak|backup|copy|old|orig|tmp|draft|副本|~$"
```
