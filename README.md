# SongFiscalAutoSourceExtractor

一个可重复运行的“史籍检索抽取”工程：从公开来源自动发现文本，面向北宋四期（熙宁、元丰、绍圣、徽宗朝）抽取财政与粮食流量指标，输出带审计信息的 Excel 面板文档。

## 1) 功能概览

- 自动抓取来源（Tier A/B/C）并维护 `Sources_Registry`（抓取时间 + 内容哈希 + URL）。
- 支持繁体/简体归一、古汉语同义词扩展、汉字数字+单位解析、弱语法规则增强抽取。
- 长表优先：先构建 `Records_Long`，再聚合主面板。
- 主面板只接收 Tier A/B 一手定位数据；Tier C 仅用于线索与回溯（可选开关）。
- 输出：`outputs/song_fiscal_panel.xlsx` + `outputs/Run_Report.md`。

## 2) 目录结构

```text
song_fiscal/
  __init__.py
  cli.py
  config/
    example.yaml
    synonym_lexicon.yaml
    unit_map.yaml
    north_south_map.csv
    place_gazetteer.csv
  sources/
    registry.py
    fetch.py
    ctext.py
    wikisource.py
  extract/
    query_plan.py
    text_normalize.py
    number_parse.py
    record_builder.py
    conflict.py
    derive.py
  panel/
    build_panel.py
    export_excel.py
outputs/
README.md
pyproject.toml
```

## 3) 最小可行配置

默认使用 `song_fiscal/config/example.yaml`。

配置重点：
- `periods`：四期时间窗 + 年号别名。
- `sources`：Tier A 主证据源（CText/Wikisource）与 Tier C 线索源。
- `metrics`：财政与粮食流量指标字典。
- `run.min_confidence`：抽取阈值。

## 4) 安装与运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

python -m song_fiscal.cli run --round 1
python -m song_fiscal.cli run --round 2
python -m song_fiscal.cli run --round 1 --enable_backtrace true
# 可指定配置
python -m song_fiscal.cli run --round 1 --config song_fiscal/config/example.yaml
```

## 5) 输出文件说明

### `outputs/song_fiscal_panel.xlsx`

至少包含以下 sheet：

1. `Panel_National_Period`
   - period, metric, value, unit, primary_record_ids, note
2. `Panel_Grainflow_Region_Period`
   - period, region, north_south, metric, value, unit, primary_record_ids, note
3. `Records_Long`
   - 每个数字/候选记录一行，含 `primary_record_id`、原文摘录、URL、anchor、置信度、时点精度
4. `Sources_Registry`
   - source_id, tier, book, url, parser, fetched_at, content_hash, anchor
5. `Conflict_Log`
   - period/region/metric 下多值冲突 + 推荐值
6. `Gap_List`
   - 缺口项（period × metric）与下一轮检索建议
7. `Secondary_Leads`（仅 backtrace 开启）
8. `Backtrace_Map`（仅 backtrace 开启）

### `outputs/Run_Report.md`

每轮自动生成，包括：
- 来源 tier 分布
- 指标命中与期别覆盖率
- 冲突摘要
- 缺口摘要
- 回溯成功率与差异（若开启）

## 6) 质量约束（实现策略）

- 主面板仅由 Tier A/B 来源聚合。
- 每个主面板单元保留 `primary_record_ids` 回链 `Records_Long`。
- 每条记录保留短摘（excerpt）避免断章取义。
- 派生值（如商业税占比）仅在分子/分母同 period-region 存在时生成。

## 7) 说明

该仓库提供可重复工程管线与审计框架。实际史籍覆盖率受公开站点可访问性、页面结构与文本完整度影响；建议按 `Gap_List` 迭代补充 Tier A/B 来源与卷次锚点。
