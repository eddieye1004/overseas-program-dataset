# 贡献指南 · Contributing Guide

感谢你愿意帮助修正这个数据集。**在提交之前，请务必读完本页。**

---

## 核心原则

> ### 没有官方来源的数据，不予合并。

这是本数据集存在的唯一理由。如果我们允许二手来源，那我们就会变成我们想要消灭的那种信息污染源。

**可作为依据的官方来源：**
- ✅ 目的地国家移民局官网（如 `immi.homeaffairs.gov.au`、`immigration.govt.nz`）
- ✅ 目的地国家驻华使领馆官网
- ✅ 项目官方运营方页面（如 IAESTE 官网、美国国务院 `j1visa.state.gov`）
- ✅ 目的地国家政府法律文本（如德国《居留法》§16e）

**不可作为依据的来源：**
- ❌ 留学 / 移民中介网站
- ❌ 微信公众号、小红书、知乎
- ❌ AI 生成的内容（包括 ChatGPT、Claude 等）
- ❌ 其他攻略博客
- ❌ 维基百科（可作为线索，但必须回溯到原始来源）

---

## 如何提交数据纠错

1. 打开 [新建 Issue](https://github.com/eddieye1004/overseas-program-dataset/issues/new/choose)
2. 选择 **"数据纠错"** 模板
3. 填写：
   - 哪个项目、哪个字段有误
   - 正确的值是什么
   - **官方来源 URL**（必填）
   - 你核实该信息的日期

---

## 如何新增一个项目

1. Fork 本仓库
2. 在 `data/programs/` 下新建 JSON 文件，命名规则：`{国家代码}-{项目简称}.json`
   - 例：`au-462-work-holiday.json`、`nz-china-whv.json`
3. 严格按照 [`data/schema.json`](../data/schema.json) 的字段定义填写
4. **每个字段都必须能指向 `sources` 中的一条来源**
5. 本地运行校验：
   ```bash
   python scripts/validate.py
   ```
6. 提交 Pull Request，并说明：
   - 你新增了什么
   - 你的信息来源
   - 你的核实方式（是否访问过官网、是否阅读过官方文件）

---

## 字段填写规范

### `last_verified`（核实日期）

- 格式：`YYYY-MM-DD`
- 含义：你**亲自核实**该条信息的最新日期
- **不要填项目的发布日期，填你确认它准确的那一天**

### `sources`（来源）

每个项目至少包含 1 条 `primary`（官方一手）来源：

```json
"sources": [
  {
    "type": "primary",
    "name": "Australian Department of Home Affairs",
    "url": "https://immi.homeaffairs.gov.au/...",
    "last_verified": "2026-09-17",
    "verified_by": "eddieye1004"
  }
]
```

### `passport_types`（护照类型）— **最关键字段**

必须明确列出**哪些护照可以申请**：

```json
"passport_types": {
  "mainland_china": true,
  "hong_kong_china": false,
  "taiwan_china": false
}
```

> ⚠️ **请格外小心这个字段。** 中文互联网上最常见的错误，就是把中国台湾 / 中国香港的资格误写成"中国"。
> 如果你不确定，请**不要猜**，在 Issue 里提出来讨论。

### 枚举值

请只使用 `schema.json` 中定义的枚举值。校验脚本会拒绝非法值。

---

## 数据格式要求

- 文件编码：UTF-8
- JSON 缩进：2 空格
- 字符串引号：双引号
- **不得包含注释**（JSON 标准不允许）
- 金额字段统一提供 `local_amount` + `currency` + `cny_estimate`（人民币估算，可选）

---

## Pull Request 检查清单

提交前请确认：

- [ ] 每个新增/修改的字段都有官方来源支撑
- [ ] `last_verified` 已更新为今天
- [ ] 本地运行 `python scripts/validate.py` 通过
- [ ] 没有使用二手来源作为依据
- [ ] 护照类型（`passport_types`）填写准确，不猜测
- [ ] PR 描述中说明了修改原因和来源

---

## 行为准则

- 讨论对事不对人
- 对政策有不同理解时，**以官方文件为准**
- 如果你的信息被指出有误，请冷静核对，而不是争辩

---

感谢你让这个数据集更准确。你修正的每一个字段，都可能帮某个学生避免一次代价高昂的误判。
