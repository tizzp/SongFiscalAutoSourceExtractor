# SongFiscalAutoSourceExtractor

面向研究级迭代的宋代财政/粮流抽取管线，支持 **Round 分工**、**段落级审计定位**、**Secondary→Primary 回溯对齐**。

## 运行

```bash
python -m song_fiscal.cli run --round 1
python -m song_fiscal.cli run --round 2
python -m song_fiscal.cli run --round 1 --enable_backtrace true
```

## Round 分工说明

- **Round 1（财政收入端）**：`total_tax`, `liangshui_share`, `commercial_tax/share`, `commercial_structure`。
  - 来源 allowlist 以《宋史·食货志》为主。
  - 关键词偏向：岁入、会计、上供、两税、商税、课利、榷盐/榷酒/榷茶。
- **Round 2（粮食流量端）**：`pingdi_or_hedi`, `supply_capital`, `supply_frontier`。
  - 来源 allowlist 以《宋会要辑稿·食货》分项为主。
  - 关键词偏向：和籴/平籴/均籴、漕运/转运、京师/入京、边储/军储/支移。

配置见 `song_fiscal/config/example.yaml` 中 `rounds`。 

## 段落级定位字段

`Records_Long` 每条记录至少包含：
- `book_title`
- `section_path`
- `paragraph_index`
- `paragraph_hash`
- `context_before` / `context_after`
- `citation_key=source_id+section_path+paragraph_index`
- `raw_text` + `normalized_text`

`Sources_Registry` 增加：`fetched_at`, `content_hash`, `canonical_url`, `parser_version`。

## Backtrace 对齐规则与失败类型

`Secondary_Leads` 只作为线索，不直接写入主面板。`Backtrace_Map` 的 success 需要对齐：
1. metric 对齐（含同义词）；
2. period 对齐（或允许 dynasty 级窗口）；
3. unit 可一致/可换算；
4. value 在阈值内（默认 1%）。

失败或部分命中会标记：
- `metric_mismatch`
- `period_mismatch`
- `unit_mismatch`
- `value_mismatch`

## 输出

- `outputs/song_fiscal_panel.xlsx`（6 个基础 sheet，开启 backtrace 时附加 2 个 sheet）
- `outputs/Run_Report.md`（含 round 覆盖、冲突、缺口、backtrace 成功率/错配统计）
