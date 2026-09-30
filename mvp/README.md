# 新加坡地址校验（Address Validation）MVP

一个可在本地运行的地址校验服务：输入任意写法的新加坡地址（可以混着电话、收件人、配送备注、本地缩写、粘连和错拼），返回**结论**（ACCEPT / CONFIRM / FIX / CONFIRM_ADD_SUBPREMISES）、**标准化地址**、**逐组件判断**、**原因码**和坐标，并把电话 / 邮箱 / 订单号 / 收件人 / 公司名 / 备注单独拆出来放在 `nonAddressInfo` 里。接口字段语义对齐 Google Address Validation API，并带上 [05 文档](../docs/05-prd-and-roadmap.md) 规划的扩展字段（严格度档位、原因码、纠错前粒度、改动幅度、校验码、候选地址）。

技术方案与验证结论见 **[docs/07-mvp-technical-validation.md](../docs/07-mvp-technical-validation.md)**，完整评测报告见 [reports/eval_report.md](reports/eval_report.md)。

![演示页面](reports/demo_confirm.png)

## 快速开始

```bash
cd mvp
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_data.py          # 下载 OneMap 邮编导出（约 57MB），聚合为 13.3 万个地址实体
python -m avmvp.server                # 打开 http://127.0.0.1:8080/ 即可试用
```

调用接口：

```bash
curl -s -X POST http://127.0.0.1:8080/v1/address:validate \
  -H 'Content-Type: application/json' \
  -d '{"address":{"regionCode":"SG","addressLines":["blk 10 bayfrnt ave","s018956"]},"strictness":"BALANCED"}'
```

复现评测（约 1 分钟）：

```bash
python scripts/make_golden_set.py     # 生成开发集 1,000 条 + 测试集 4,000 条
python scripts/evaluate.py            # 输出 reports/eval_report.md 与 reports/eval_results.json
python scripts/make_noisy_set.py      # 生成"真实客户输入"风格的噪声评测集（开发 540 条 + 测试 1,800 条）
python scripts/evaluate_noisy.py      # 输出 reports/noisy_eval_report.md；加 --before-impl <旧版目录> 可对比旧版
python scripts/evaluate_bayes.py      # 贝叶斯打分：训练置信度模型并与规则方案对比（见 docs/09）
python scripts/make_labeled_orders.py # 模拟订单标注数据 10,000 单（已提交在 labeled/，重跑结果一致，见 docs/10）
python scripts/evaluate_labeled.py    # 在模拟订单上评测，并用训练部分重新统计置信度（models/confidence_sg_orders.json）
python scripts/fetch_overture.py      # 下载 Overture 新加坡数据：2026 年官方地址表 + 商户自填地址（见 docs/11）
python scripts/measure_noise.py       # 统计真实人写地址里的噪声种类和比例 -> reports/noise_stats.md
python scripts/make_research_testset.py   # 按调研比例在 2026 年地址上构造测试集（已提交在 labeled/）
python scripts/evaluate_labeled.py --orders labeled/testset_sg_research_v1.csv --confidence-train labeled/orders_sg_v1.csv --tag _research
python scripts/evaluate_real_strings.py   # 8,000 条真实人写地址评测
python scripts/whatif_current_reference.py  # 参考库换成 2026 年数据的效果
python scripts/profile_countries.py   # 澳洲 / 中东 / 东南亚 / 欧洲 17 个城市的地址画像（见 docs/12）
pytest -q                             # 77 个单元测试（使用 tests/ 下的小型真实数据夹具，无需下载）
```

接口的 `verdict.confidence` 为贝叶斯置信度：规则结论所属类别在带标注数据里的实际正确率（服务器默认加载 `models/confidence_sg.json`）。

可选：本地小模型兜底（如 Qwen，见 [08 文档](../docs/08-ai-local-model.md)）：

```bash
ollama pull qwen2.5:1.5b
python scripts/evaluate_llm.py --model qwen2.5:1.5b --pure            # 对比 规则 / 规则 + 模型兜底 / 纯模型
python -m avmvp.server --llm-endpoint http://127.0.0.1:11434          # 演示页面开启兜底
```

## 结果速览

**标准变形**（4,000 条从未参与开发迭代的测试样本，10 类错误）：

| 方案 | 完全正确率 | 误收率 | 误拒率 | 静默错误率 | 单条延迟 P50 / P95 |
|---|---|---|---|---|---|
| **本方案** | **99.9%** | 0.0% | 0.1% | 0.0% | 1.2ms / 12.5ms |
| B1 模糊整串匹配（Geocoder 式，阈值已调到对它最有利） | 53.9% | 7.0% | 28.3% | 13.9% | — |
| B2 仅查邮编 | 57.6% | 0.0% | 35.7% | 12.8% | — |

**真实客户输入风格**（1,800 条带业务噪声的测试样本，9 类）：

| 方案 | 地址识别率 | 直接通过率 | 静默错误率 | 电话抽取 |
|---|---|---|---|---|
| **本方案** | **98.8%** | **86.1%** | 0.0% | 100% |
| 上一版（未做噪声处理） | 96.0% | 13.8% | 0.0% | — |
| B1 模糊整串匹配 | 58.7% | 58.7% | 10.3% | — |
| B2 仅查邮编 | 85.0% | 85.0% | 7.1% | — |

![噪声输入演示](reports/demo_noisy.png)

**模拟真实订单**（[labeled/](labeled/README.md)，按 5 个下单渠道的错误画像生成，含参考库没有的新地址、马来西亚地址、App 自动补全带出的错误地址；测试部分 4,000 单）：

| 自动通过率 | 静默错误率 | 误拒率 | 缺单元号检出率 |
|---|---|---|---|
| 78.6% | 0.33%（全部来自"文字自洽但指向别的真实地址"） | 1.0% | 22.5% |

问题清单与置信度重新统计的结果见 [docs/10](../docs/10-labeled-data.md)。

**按调研比例构造的测试集与真实人写地址**（[docs/11](../docs/11-research-testset.md)）：

| 测试集 | 条数 | 自动通过 | 可确定时找对 | 误拒 | 静默错误 |
|---|---|---|---|---|---|
| 调研测试集（2026 年地址 + 实测 / 文献比例的噪声） | 5,000 | 70.7% | 99.2% | 0.7% | 0.04% |
| 真实人写地址（商户自填，带邮编） | 8,000 | 76.5% | 97.9% | 1.2% | 0% |

参考库从 2017 年换成 2026 年数据后，调研测试集找对率 86.7% → 93.8%（新地址 0% → 95.1%）。

**注意：** 测试集由参考库构造，是"封闭世界"，数字证明的是**方案逻辑可行**，不等于真实流量上的准确率。真实准确率取决于参考数据的完整度和时效，详见 07 文档的"局限"一节。

## 目录

```
mvp/
├── avmvp/
│   ├── noise.py        业务噪声剥离：电话 / 邮箱 / 订单号 / 收件人 / 公司名 / 配送备注
│   ├── normalize.py    预处理：大小写 / 标点 / 缩写（含 AMK 等本地缩写）统一为"规范匹配键"
│   ├── parser.py       解析：邮编、单元号（多种写法）、楼栋号候选（N-best）、粘连拆分
│   ├── reference.py    参考库：多路索引（邮编 / 楼栋+道路 / 道路 / 楼宇名）+ 道路模糊检索
│   ├── validator.py    核心：假设生成与打分 → 规则化结论树 → 响应组装
│   ├── bayes.py        贝叶斯打分：候选后验概率（Fellegi–Sunter）与规则结论的置信度模型
│   ├── llm_fallback.py 本地小模型兜底（Ollama / OpenAI 兼容接口）+ 防编造规则
│   ├── baselines.py    对照方案 B1 / B2
│   └── server.py       本地 HTTP 服务 + 演示页面（仅标准库）
├── scripts/
│   ├── fetch_data.py       下载并构建参考库
│   ├── make_golden_set.py  按错误类别生成评测集
│   ├── evaluate.py         评测 + 消融 + 严格度 + 数据时效实验
│   ├── make_noisy_set.py   生成"真实客户输入"风格的噪声评测集
│   ├── evaluate_noisy.py   噪声评测（可对比旧版实现）
│   ├── evaluate_llm.py     本地小模型评测：规则 / 规则 + 模型兜底 / 纯模型
│   ├── evaluate_bayes.py   贝叶斯打分评测：准确率对比、置信度校准、按门槛通过率
│   ├── make_labeled_orders.py  生成模拟订单标注数据（按渠道模拟 + 独立标注规则）
│   ├── evaluate_labeled.py     模拟订单评测 + 置信度重新统计
│   ├── fetch_overture.py       下载 Overture 新加坡数据（2026 年地址表、商户地址）
│   ├── measure_noise.py        真实人写地址噪声统计
│   ├── make_research_testset.py  按调研比例构造测试集
│   ├── evaluate_real_strings.py  真实人写地址评测
│   ├── whatif_current_reference.py  换参考库的效果
│   └── profile_countries.py    多市场地址画像
├── labeled/            标注数据（模拟订单 orders_sg_v1.csv、调研测试集 testset_sg_research_v1.csv）、数据说明、标注规范
├── models/             贝叶斯参数（证据权重、置信度统计表）
├── tests/              77 个单元测试与 58 条真实地址夹具
└── reports/            评测报告与演示截图
```

## 数据来源与许可

参考数据来自 [xkjyeah/singapore-postal-codes](https://github.com/xkjyeah/singapore-postal-codes)，即 OneMap 邮编检索的全量导出（2017 年起）。使用受 [Singapore Open Data Licence](https://www.onemap.gov.sg/legal/opendatalicence.html) 约束，需注明出处（原仓库说明："This data dump contains information from Onemap.sg postal code search accessed on 25 Apr 2017, or later"）。该数据**不是最新数据**，生产环境需向 SLA / OneMap 获取最新授权数据。
