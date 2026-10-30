# 2026-10-30 链接检查器自身偏差复核（P1-4）

> 执行者：dsh（DeepSeek Harness）
> 目的：验证 HANDOVER §4 P1-4「本机 CA 库缺失导致 4 条假 WARN」是否仍成立，并把检查器自身的判断偏差逐项定位
> 结论：**CA 库缺失的成因不成立**；12 条 WARN 里有 6 条是检查器的请求特征问题，已修。剩 6 条经浏览器 / curl 双通道复核，站点本身正常。

## 1. 环境实测（F:\python.exe 3.14.6）

```
ssl.get_default_verify_paths() -> cafile=None, capath=None
C:\Program Files\Common Files\SSL\cert.pem 存在? False
SSL_CERT_FILE / SSL_CERT_DIR 未设置
ssl.create_default_context().cert_store_stats() -> {'x509': 64, 'x509_ca': 62}
```

- 旧记录写「openssl_cafile 指向不存在的 C:\Program Files\Common Files\SSL\cert.pem」。**该路径在当前解释器上根本没有被引用**：`cafile` 与 `capath` 都是 `None`，走的是 Windows 证书存储（64 张）。
- 交叉验证：`urllib.request.urlopen('https://www.gov.uk/', context=默认ctx)` → 200，`https://www.canada.ca/` → 200。证书链校验是通的。
- 结论：**P1-4 的前提不成立**。若强行设 `SSL_CERT_FILE=F:\Lib\site-packages\certifi\cacert.pem`（156 张），验证也通过，但它解决的不是这里的问题。

## 2. 12 条 WARN 的真实归因

| 归因 | 条数 | 证据 |
|---|---|---|
| UA 版本被判过期，WAF 直接 403 | 5 | 同一 URL，UA 写 `Chrome/120` → 403，写 `Chrome/141` 或无 UA → 200。涉及 `iaeste.de`、`irishimmigration.ie`（3 条） |
| 307 回自身但需带 cookie | 1 | `overseas.mofa.go.kr/` 下 `TMOSHCooKie` 后 307 回同 URL；不存 cookie 时 curl `-L` 跟了 **23 跳** 后超时，带 cookie jar 一次 200 |
| 站点对数据中心 IP / 高频请求限流 | 6 | `canada.ca` 3 条（`ConnectionResetError [WinError 10054]` / 读超时）、`mofa.go.jp` 2 条（403）、`ceac.state.gov` 1 条（403） |

修复前 48 条里 36 ok / 12 warn；修复后 **42 ok / 6 warn**，且 0 条 404·410。

## 3. 剩余 6 条 —— 双通道复核，均非失效

| 链接 | urllib | curl（Chrome 全套头） | 无头 Edge | 判定 |
|---|---|---|---|---|
| `canada.ca/.../iec.html` | ConnectionReset / 读超时 | 200 | 200，标题 `Work and Travel in Canada with International Experience Canada - Canada.ca` | 站点正常 |
| `canada.ca/.../iec/eligibility.html` | 读超时 | 200 | 200 | 站点正常 |
| `canada.ca/.../eligibility-by-country.html` | 读超时 | 200 | 200 | 站点正常 |
| `mofa.go.jp/j_info/visit/w_holiday/index.html` | 403 | **200（两次，间隔 3s）** | 本次 403 `Access Denied` | Akamai 按请求特征选择性放行；站点正常 |
| `mofa.go.jp/mofaj/toko/visa/.../pagew_000001_02672.html` | 403 | 200 | — | 同上 |
| `ceac.state.gov/genniv/` | 403 | 403 | 403，标题 `Attention Required! \| Cloudflare` | Cloudflare 挑战页；站点存活，需人工过挑战 |

`mofa.go.jp` 在 urllib 与 curl 下结果不一致这一点值得记录：**同一台机器、同一时刻，只换客户端就换结论**。这直接印证了 AGENTS.md 第 3 节那条「判定链接失效前先用真实浏览器复测」的规则；本次还补一条——urllib 与 curl 也要交叉，不能只信一个。

## 4. 本轮改动

`scripts/validate.py`：

1. UA 从 `Chrome/120.0.0.0` 提到 `Chrome/141.0.0.0`，注释写明原因（版本号会过期，过期就凭空长出假告警）。
2. `check_link()` 每次请求挂独立 `HTTPCookieProcessor`，并把 `ssl` 从函数内 `import ssl as _ssl` 提到模块顶部。
3. `tests/test_validate.py` 新增 `TestCheckLinkBehaviour`（8 例）：UA 版本下限、cookie jar 必须挂上、404/410 判 fail、403 判 warn、超时判 warn、ConnectionReset 判 warn、2xx 判 ok。测试用替身拦截 opener，不发真实请求。测试总数 54 → 62。

## 5. 未核实项

- `ceac.state.gov` 的 Cloudflare 挑战在真实浏览器交互下大概率可通过，本轮未做人工过挑战验证，因此 `us-j1` step4 的链接只标到「站点存活、内容未取到」。
- `mofa.go.jp` 的放行是否与出口 IP 信誉、请求频率有关，未做控制变量实验；只知道「curl + Chrome 头」稳定 200，「urllib」稳定 403。
- 本机 `F:\python.exe` 装了 `pytest 9.2.0` 但 `import pytest` 失败（`F:\python314.zip` 排在 `sys.path` 首位，`F:\Lib\site-packages` 不在其中）。属环境配置问题，不影响 `python -m unittest discover -s tests`，未处理。
