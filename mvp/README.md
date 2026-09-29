# 新加坡地址校验（Address Validation）MVP

一个可在本地运行的地址校验服务：输入任意写法的新加坡地址，返回**结论**（ACCEPT / CONFIRM / FIX / CONFIRM_ADD_SUBPREMISES）、**标准化地址**、**逐组件判断**、**原因码**和坐标。接口字段语义对齐 Google Address Validation API，并带上 [05 文档](../docs/05-prd-and-roadmap.md) 规划的扩展字段（严格度档位、原因码、纠错前粒度、改动幅度、校验码、候选地址）。

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
pytest -q                             # 27 个单元测试（使用 tests/ 下的小型真实数据夹具，无需下载）
```

## 结果速览（4,000 条从未参与开发迭代的测试样本）

| 方案 | 完全正确率 | 误收率 | 误拒率 | 静默错误率 | 单条延迟 P50 / P95 |
|---|---|---|---|---|---|
| **本方案** | **99.9%** | 0.0% | 0.1% | 0.0% | 1.0ms / 9.2ms |
| B1 模糊整串匹配（Geocoder 式，阈值已调到对它最有利） | 53.8% | 7.0% | 28.3% | 13.9% | — |
| B2 仅查邮编 | 57.6% | 0.0% | 35.7% | 12.8% | — |

**注意：** 测试集由参考库构造，是"封闭世界"，数字证明的是**方案逻辑可行**，不等于真实流量上的准确率。真实准确率取决于参考数据的完整度和时效，详见 07 文档的"局限"一节。

## 目录

```
mvp/
├── avmvp/
│   ├── normalize.py    预处理：大小写 / 标点 / 缩写统一为"规范匹配键"
│   ├── parser.py       解析：邮编、单元号、楼栋号候选（N-best）
│   ├── reference.py    参考库：多路索引（邮编 / 楼栋+道路 / 道路 / 楼宇名）+ 道路模糊检索
│   ├── validator.py    核心：假设生成与打分 → 规则化结论树 → 响应组装
│   ├── baselines.py    对照方案 B1 / B2
│   └── server.py       本地 HTTP 服务 + 演示页面（仅标准库）
├── scripts/
│   ├── fetch_data.py       下载并构建参考库
│   ├── make_golden_set.py  按错误类别生成评测集
│   └── evaluate.py         评测 + 消融 + 严格度 + 数据时效实验
├── tests/              单元测试与 58 条真实地址夹具
└── reports/            评测报告与演示截图
```

## 数据来源与许可

参考数据来自 [xkjyeah/singapore-postal-codes](https://github.com/xkjyeah/singapore-postal-codes)，即 OneMap 邮编检索的全量导出（2017 年起）。使用受 [Singapore Open Data Licence](https://www.onemap.gov.sg/legal/opendatalicence.html) 约束，需注明出处（原仓库说明："This data dump contains information from Onemap.sg postal code search accessed on 25 Apr 2017, or later"）。该数据**不是最新数据**，生产环境需向 SLA / OneMap 获取最新授权数据。
