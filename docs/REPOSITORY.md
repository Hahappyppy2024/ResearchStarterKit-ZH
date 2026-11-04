# 仓库目录

本次已用当前完整网站替换简化模板与旧的重复工具快照：

- `sites/mist-blue-lotus/app/`：当前完整网站，内部保留 `web`、`web-hub`、`web-learning`、`web-projects`、`web-shared` 等结构，避免打断相对引用。
- `run.py`：根目录一条命令启动。
- `tests/`：回归测试；`scripts/run_site_checks.py` 配置完整网站导入路径。
- `scripts/`：候选上传文件检查。
- `docs/local-toolkit/`、`docs/archive/`：历史参考文档，旧路径仅供历史查阅，以根 README 的新运行方式为准。
- `docs/screenshots/`：只存空数据库公开副本的验收截图。

私人原站未移动。Git 历史可恢复旧代码；未强推或改写历史。运行数据只在公开副本自己的 `app/local-data/` 中生成，不提交 Git。
