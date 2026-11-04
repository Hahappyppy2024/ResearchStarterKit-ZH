# 场景、方法图与数据集阅读任务

每篇论文新增 `background`、`methodology`、`datasets` 三项，总计 22 项。原有任务 ID、回答、勾选记录、今日安排入口和周 Quiz 保留。

- 场景：描述使用者、真实工作流程、输入输出、约束与研究动机。
- 方法：上传 PNG/JPEG/WebP 总览图（每张不超过 8 MB），再填写图号/页码、模块、数据流和个人图解。可查看原尺寸或解除图片关联。
- 数据集：从统一资料库选择或新建，说明本文使用的数据版本、划分、指标及其依据。

论文脉络左栏新增 Solution 方法树和“数据集 · Datasets”入口。数据集资料卡支持中英文名称、官方链接、来源论文（多篇）、补充引用、规模/标注/版本/划分/指标说明，以及多选 Topic、Problem、Solution 分类。分类可使用三级定义，筛选父类时包含其子类。资料卡反向显示哪些论文使用了该数据集。

数据集编辑器中的“刷新分类定义”会保留正在填写的表单；添加新分类后可刷新选项。来源没有收录到本地文献库时，可先填写原始论文引用、DOI 或链接，再补充题录关联。

上传图存放于 `study_service.DB.parent/paper-methodology/`，正式实例位于 `local-data/paper-methodology/`；元数据和数据集存入同一私人 SQLite 数据库。图片与数据不进入 Git。取消图片/数据集关联只解除当前论文的引用，保留本地资料。

验证：`python -m unittest discover -q`；`node --test web/study-tasks.test.mjs web/paper-relations.test.mjs web/reading-history.test.mjs web/todos.test.mjs`。`assets_qa_server.py` 为独立测试数据库，避免测试写入正式阅读记录。


## Required reading and completion

Dataset task 22 contains two parts: dataset name and dataset source papers. Source papers can be selected or created inline. Saving dataset sources or paper references queues them for today's intentional reading, deduplicated by date and paper ID. Weekly arXiv cards and curated picks have an explicit Add to required reading action. The intentional queue retains the existing schedule/task picker for Daily Effort.

A paper is complete only when every reading-task checkbox is complete. The server derives completion and readDate on save; unchecking a task removes whole-paper completion. Whole-paper schedule entries and paper subtasks derive completion from this same task list and cannot be manually checked. Pages refresh saved completion across tabs periodically, without overwriting pending reader drafts. Individual reading tasks can still be scheduled separately.

Validation: 55 Python tests; shared reading-history, study-task, relation, and schedule Node tests; isolated browser checks for dataset-source creation, related-paper creation with multiple relations, queue deduplication, 22/22 completion, and reverting a scheduled paper to incomplete at 21/22.


## Read library, review calendars, comparison and next problems

The comparison task selects only completed papers from the server-backed read library and excludes itself. Selected IDs and existing written comparisons survive reloads. The next-step task creates bilingual Problem definitions and keeps per-paper problem entries with editable keyword lists; removing an entry does not delete the shared taxonomy definition.

Completed queue papers are displayed below pending required reading in the read-library section. Week and month calendars use completion dates; reopening a paper's tasks makes it incomplete until all tasks are complete again. Completion logs preserve distinct completion dates locally. Daily/weekly/monthly reviews use separate period-normalized records with revision checks, browser drafts, a notes-based outline and Markdown export. No external AI service is used to invent review conclusions.


## Updated 20-task checklist

Removed visible tasks `connections`, `focus`, and `taxonomy`; their old answers remain stored, and `connections.references` continues to back the related-papers relationship editor. These auxiliary annotations are excluded from completion counts. Added `reading-questions`, containing separately editable question/answer items. `extensions` now contains separately editable problem items; its old prose remains available in a collapsed legacy-record section. Item IDs preserve answers across edits and deletions, and each list supports undoing its latest removal. No comma-based splitting or destructive conversion is performed.

## Paper Flash Cards and Daily Quiz

The checklist now ends with a 21st task, flashcards. Each card has a question and reference answer; cards can also be generated from the user's written reading answers. A separate per-paper selection joins these cards to daily-quiz.html. Per-day snapshots, answers and self-assessment remain in ignored local-data; paper answers are self-assessed, not semantically graded. Foundation evening and weekly practice are available in the same Daily Quiz page using the existing practice records; the foundations page retains morning Flash Cards. Browser QA used isolated records and verified selection, submission, flipping and persistence.
