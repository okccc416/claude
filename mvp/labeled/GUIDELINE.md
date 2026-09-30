# 地址校验标注规范（v1）

> 用途：给订单地址打"标准答案"，用于评测地址校验能力、统计置信度、设定自动通过门槛。
> 本规范同时适用于**模拟订单**（`orders_sg_v1.csv`，由 `scripts/make_labeled_orders.py` 按本规范自动生成标签）和今后的**真实订单人工标注**。两者字段完全一致，可以直接合并或替换。

---

## 1. 每单要标什么

| 字段 | 必填 | 含义 | 取值 / 例子 |
|---|---|---|---|
| `truth_blk` / `truth_street` / `truth_postal` / `truth_building` / `truth_unit` | 是 | **真实投递地址**：以签收、派送员反馈或客服确认为准，不是"文字看起来像什么" | `123` / `ANG MO KIO AVENUE 6` / `560123` / — / `#05-12` |
| `truth_eid` | 有则填 | 真实地址在参考库里的编号；参考库里找不到就留空 | `10432` |
| `property_type` | 是 | 物业类型 | `HDB` 组屋 / `CONDO` 公寓 / `COMMERCIAL` 写字楼、商场、工业楼 / `LANDED` 有地住宅及其他 |
| `unit_required` | 是 | 这栋楼是否需要单元号才能投递 | 组屋、公寓、写字楼 = `Y`；有地住宅 = `N` |
| `text_resolution` | 是 | **只看客户写的文字**，能判断到什么程度（第 2 节） | 七选一 |
| `gold_action` | 是 | 期望的校验结论（BALANCED 档，第 3 节） | `ACCEPT` / `CONFIRM` / `CONFIRM_ADD_SUBPREMISES` / `FIX` |
| `acceptable_actions` | 是 | 不算错的结论集合（至少包含 `gold_action`） | `CONFIRM|ACCEPT` |
| `error_tags` | 是 | 输入里出现了哪些问题（第 4 节，可多选） | `UNIT_MISSING|STREET_TYPO` |
| `field_states` | 建议 | 逐字段的状态 | `blk=ok;street=typo;postal=missing;building=absent;unit=ok` |
| `label_note` | 建议 | 一句话说明判断依据，便于复核 | `邮编+楼栋+道路 唯一确定` |

**两层标签要分开**："真实地址"回答*客户到底住哪*，`text_resolution` 回答*仅凭这段文字能不能知道他住哪*。两者不一致的情况（例如邮编打错、恰好撞上另一个真实邮编）正是校验系统最危险的地方，必须单独标出来。

---

## 2. `text_resolution`：只看文字能判断到什么程度

按顺序判断，命中即停：

| 顺序 | 取值 | 判断标准 | 例子 |
|---|---|---|---|
| 1 | `OUT_OF_REGION` | 不是新加坡地址 | `No. 12, Jalan Setia 3/5, Taman Setia, 81100 Johor Bahru` |
| 2 | `NO_ADDRESS` | 没有可投递的地址（只有区域名、"同上次"、"自取"等） | `self collect`、`Tampines`、`same as previous order` |
| 3 | `NOT_IN_REFERENCE` | 真实地址存在，但参考库里没有（新楼盘、数据缺失） | 2024 年落成的新组屋 |
| 4 | `RESOLVABLE` | 文字能**唯一**确定一个地址，且就是真实地址（允许需要纠错 / 补全） | `blk 123 amk ave 6 #05-12`（缺邮编也能唯一确定） |
| 5 | `MISLEADING` | 文字能唯一确定一个地址，但**不是**真实地址（输入错误恰好撞上另一个真实地址，仅凭文字发现不了） | 真实邮编 560123，写成 560132，且没写楼栋和道路 |
| 6 | `AMBIGUOUS` | 文字对应多个地址，无法确定是哪一个 | 只写了 `Tampines Street 81`；楼宇名对应多栋楼 |
| 7 | `CONFLICTING` | 字段之间互相矛盾，且无法判断哪个字段错了 | 楼栋 + 道路指向 A，邮编指向同一条路上的 B |

### 判断细则

1. **逐字段查参考库**：邮编 → 该邮编下的地址；楼栋 + 道路 → 该地址；只有道路 → 整条路上的地址；楼宇名 → 该楼宇的地址。取交集：1 个 = 可确定，多个 = 有歧义，0 个 = 矛盾。
2. **矛盾时按多数字段裁决**：某个候选得到至少 2 个字段支持，且严格多于其他候选 → 视为可确定（需纠错）；否则标 `CONFLICTING`。
   - 例：楼栋 + 道路都指向 A，只有邮编指向 B → A 得 2 票、B 得 1 票 → 可确定为 A。
   - 例：楼栋 + 道路指向 A，邮编 + 道路指向同一条路上的 B → 2 : 2 → `CONFLICTING`。
3. **楼栋号漏写字母后缀**（写了 268，实际是 268A），且这条路上只有这一个 268x → 视为同一栋（矛盾裁决时算半票）。反过来，写了字母后缀而参考库没有（写 268A，只有 268）不算同一栋：可能是新楼。
4. **不算错误、不影响判断的写法**：大小写、标点、缩写（Ave / St / Jln / Bt / AMK / CCK 等，包括不常见的 `Cent`、`S'goon`、`W'lands`）、`Blk` 前缀、`Singapore` / `S` / `SG` 前缀、邮编被 Excel 吞掉前导 0（`18956` 视为 `018956`）、电话 / 姓名 / 备注 / 公司名等非地址信息。
5. **拼写错误**：本地人一眼能认出是哪条路（且不会和另一条路混淆）才算认得出；认不出就当这个字段没写。
6. **中文地址**（`宏茂桥6道123座`）：懂中文的标注员能对应到英文地址即算可确定。
7. **只看文字，不看历史**：不参考客户历史订单、GPS 等文字以外的信息，这些是 `MISLEADING` 能被发现的唯一途径，属于系统之外的信号。

---

## 3. `gold_action`：期望的校验结论（BALANCED 档）

| 情况 | `gold_action` | `acceptable_actions` |
|---|---|---|
| 可确定；地址本身无需改动；单元号齐全或不需要 | `ACCEPT` | `ACCEPT` |
| 可确定；地址本身无需改动；缺单元号（多单元楼） | `CONFIRM_ADD_SUBPREMISES` | `CONFIRM_ADD_SUBPREMISES`、`CONFIRM` |
| 可确定；只需"轻微"改动（道路拼写纠错、补全邮编、附加的楼宇名拼错），单元号不缺 | `CONFIRM` | `CONFIRM`、`ACCEPT` |
| 可确定；需要实质改动（邮编错、楼栋错 / 缺、道路编号错、只写了楼宇名、中文地址等） | `CONFIRM` | `CONFIRM`（缺单元号时另加 `CONFIRM_ADD_SUBPREMISES`） |
| `CONFLICTING` | `CONFIRM` | `CONFIRM`、`FIX` |
| `AMBIGUOUS` | `FIX` | `FIX`、`CONFIRM`（给出候选让用户选） |
| `NOT_IN_REFERENCE` | `FIX` | `FIX`、`CONFIRM` |
| `OUT_OF_REGION`、`NO_ADDRESS` | `FIX` | `FIX` |
| `MISLEADING` | 按文字给（通常 `ACCEPT`） | 不参与结论评测，单独统计为"仅凭文字不可避免的错误" |

评测时把系统结果分成 7 类（见 `scripts/evaluate_labeled.py`）：正确、正确拒绝、多余确认、漏报、误拒、错误建议、**静默错误**（地址不对却直接通过，最需要压低）。

---

## 4. `error_tags`：输入里出现了哪些问题

| 标签 | 含义 | 是否需要改动地址 |
|---|---|---|
| `UNIT_MISSING` | 多单元楼缺单元号 | 需补充 |
| `STREET_TYPO` | 道路拼写错误 | 轻微 |
| `STREET_NUMBER_WRONG` | 道路编号 / 类型写错（Ave 3 写成 Ave 4、Street 写成 Avenue） | 是 |
| `STREET_TRUNCATED` | 道路名被字段长度截断 | 是 |
| `POSTAL_MISSING` | 没写邮编 | 轻微 |
| `POSTAL_TYPO` | 邮编打错（相邻数字对调、按错键） | 是 |
| `POSTAL_OTHER_ADDRESS` | 写了另一个地址的邮编（旧地址、附近楼） | 是 |
| `POSTAL_LEADING_ZERO_LOST` | 邮编前导 0 丢失 | 否 |
| `BLOCK_MISSING` / `BLOCK_TYPO` / `BLOCK_LETTER_DROPPED` | 楼栋号缺失 / 打错 / 漏了字母后缀 | 是 |
| `BUILDING_ONLY` | 只写了楼宇名（公寓、写字楼），没写楼栋和道路 | 是 |
| `BUILDING_TYPO` | 楼宇名拼写错误 | 轻微（只写了楼宇名时按 `BUILDING_ONLY` 算实质改动） |
| `AUTOFILL_WRONG` | App 按打错的邮编自动带出了另一个地址 | 是 |
| `CHINESE_ADDRESS` | 用中文写的地址 | 是（需转写） |
| `NEW_HDB_BLOCK` / `NEW_ESTATE` / `NEW_CONDO` | 参考库没有的新地址（新组屋 / 新片区 / 新公寓） | — |
| `OUT_OF_REGION` / `NO_ADDRESS` | 非新加坡地址 / 没有地址 | — |
| `ABBREV` / `TOWN_ABBREV` / `UNIT_FORMAT` / `DUPLICATED_TEXT` / `LOCATION_HINT` | 缩写、市镇缩写、单元号非标准写法、重复文字、位置提示（void deck、guardhouse） | 否 |
| `NOISE_PHONE` / `NOISE_NAME` / `NOISE_NOTE` / `NOISE_COMPANY` | 混入电话、姓名、备注、公司名 | 否 |

---

## 5. 真实订单怎么标（上线前要做的事）

1. **真实地址从哪来**：优先用**签收结果**（派送员确认的楼栋 + 单元、签收 GPS 落在哪栋楼），其次是客服改址记录、退件原因。不要让标注员凭文字"猜"真实地址，否则 `MISLEADING` 永远标不出来。
2. **抽样**：按渠道分层（网页 / App / 聊天 / 平台导出 / 企业上传），每层至少 300 单；另对校验器判为 `ACCEPT` 的订单单独多抽，因为自动通过里的错误率是最关键的指标。
3. **样本量**：要证明某类结论的错误率低于 0.5%（95% 置信），该类至少需要约 600 单且一个错都没有（"三分之一法则"：0 错 / n 单 → 上限约 3 / n）。
4. **双人标注**：每单两人独立标注 `text_resolution` 和 `gold_action`，计算一致率（Cohen's κ，目标 ≥ 0.8）；不一致的由第三人裁决，并把争议案例补充进本规范。
5. **隐私**：标注前把电话、姓名、邮箱脱敏（符合新加坡 PDPA），只保留地址相关文字。
6. **定期重标**：地址数据和客户输入习惯会变，建议每季度抽样重标一次，重新统计置信度。
