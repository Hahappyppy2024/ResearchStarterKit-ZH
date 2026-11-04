# 会议目录采集记录

核验日期：2026-10-20。数据：`data/conferences.json`；重跑：`python conference_sources.py`。

共 **49,022** 条去重元数据，ID 全部唯一，均含标题、作者及官方来源。
其中 **57** 条官方目录未给出可确认的 PDF 直链，保留会议论文页面，PDF 字段为空。
未下载论文全文。分类为标题/可用摘要关键词自动分类，须人工复核；“其他”仍然保留。

| 会议 | 2025 | 2026 | 来源与边界 |
|---|---:|---:|---|
| AAAI | 3,486 | 4,920 | OJS 年度卷全部分册：分别 28、48 册，包含该卷附属 track |
| NeurIPS | 5,823 | 5,999 | 2025 正式主会论文集；2026 官网已公布报告目录去重，含 journal 等 track，非最终正式论文集 |
| ICML | 3,330 | 6,552 | PMLR 官方卷 v267、v306 的全部目录 |
| ICCV | 2,701 | 0 | 2025 CVF 主会目录；2026 无 ICCV 主会 |
| CVPR | 2,871 | 4,042 | CVF 主会 day=all 目录 |
| ICLR | 3,830 | 5,468 | 官网报告目录去重，含 journal 等 track；不把报告事件数当论文数 |

不含独立 workshop 论文集；NeurIPS 2025 不含独立 Creative AI 论文集。
对“全部”的口径为上述明确官方索引/年度卷内全部条目，而非整个会议品牌下所有独立附属活动。

## 可重跑与验证

- 仅使用官方来源。每个请求间隔至少 0.7 秒，响应缓存 24 小时。
- `--refresh` 强制重新获取；`--only ICLR` 仅刷新指定会议，保留其他会议。
- 网络失败保留该源上次成功的数据并记录失败状态。
- 逐来源原子写入，并对 Windows 文件短暂被读锁的情况重试。
- 已验证：49,022 个唯一 ID；逐源计数之和与总数一致；全部标题、作者、来源非空。
- 已验证：`--only ICLR` 重跑后完整保留全部 49,022 个 ID。
- 抽查 AAAI `/article/download/34477/36632` 和 NeurIPS 2025 PDF 返回 `200 application/pdf`。
- 官网 ICLR 报告 JSON 中存在虚构形式的 `2025-Oral--...` 等 OpenReview 事件占位 ID。脚本排除这些伪论文链接，优先使用同标题真实论文记录。
- 缺 PDF：NeurIPS 2026 31 条、ICLR 2025 20 条、ICLR 2026 6 条。
- 大部分静态索引不提供摘要与精确发布日期，这些字段留空，不猜测。

## 官方入口

- https://ojs.aaai.org/index.php/AAAI/issue/archive
- https://papers.nips.cc/paper_files/paper/2025/vol38-main-conference
- https://neurips.cc/virtual/2026/papers.html
- https://proceedings.mlr.press/v267/
- https://proceedings.mlr.press/v306/
- https://openaccess.thecvf.com/ICCV2025?day=all
- https://openaccess.thecvf.com/CVPR2025?day=all
- https://openaccess.thecvf.com/CVPR2026?day=all
- https://iclr.cc/virtual/2025/papers.html
- https://iclr.cc/virtual/2026/papers.html
