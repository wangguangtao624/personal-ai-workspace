# 详细测试结果

执行时间（UTC）：2026-11-10T17:22:51.666237+00:00

环境：{'os': 'Windows', 'release': '11', 'python': '3.12.14'}；测试基准：`077cf1a85a73fd1f5259dbadb80d5d82090c3702 plus local transcription changes; see hashes`。

共 28 项，27 通过，1 跳过，0 失败，0 错误。

样例为合成数据；跳过不计通过。源文件 SHA-256 见 results.json，完整命令输出见 test-output.txt。

| 测试编号 | 覆盖内容与预期 | 结果 | 耗时（秒） |
| --- | --- | --- | --- |
| `test_acceptance.AcceptanceRegression.test_candidate_cannot_promote_unknown_scope_or_changed_id` | 拒绝不存在的项目、被修改编号、错误状态及空经验，保留原候选。 | PASS | 0.0246 |
| `test_acceptance.AcceptanceRegression.test_cli_capture_context_and_restore_end_to_end` | 通过子进程完成创建项目、收集、检索、备份、验证、恢复和恢复后读取。 | PASS | 0.7736 |
| `test_acceptance.AcceptanceRegression.test_corrupt_candidate_is_reported_without_traceback_or_promotion` | JSON 数组候选返回错误而非崩溃，不晋升、不删除原记录。 | PASS | 0.0119 |
| `test_acceptance.AcceptanceRegression.test_invalid_utf8_manifest_is_cleanly_reported` | 备份清单编码异常时命令返回错误。 | PASS | 0.0126 |
| `test_acceptance.AcceptanceRegression.test_unreadable_directory_does_not_create_incomplete_backup` | 模拟目录权限错误，确保备份失败且不留下不完整快照。 | PASS | 0.0072 |
| `test_acceptance.AcceptanceRegression.test_version_prefix_does_not_displace_exact_version` | V1.2.30 不得按 V1.2.3 的精确匹配参与排名。 | PASS | 0.0697 |
| `test_app.WorkspaceTest.test_chinese_sentence_retrieves_related_project_document_only` | 中文长句召回当前项目资料，排除其他项目内容。 | PASS | 0.0234 |
| `test_app.WorkspaceTest.test_context_respects_project_and_experience_approval` | 经验确认前不加载，确认后仅用于指定项目。 | PASS | 0.0524 |
| `test_app.WorkspaceTest.test_dotted_firmware_version_is_prioritized` | 带小数点的固件版本在有限检索结果中优先。 | PASS | 0.0633 |
| `test_app.WorkspaceTest.test_exact_version_is_prioritized_when_results_are_bounded` | 型号版本精确关键词在结果超过上限时仍能命中。 | PASS | 0.061 |
| `test_app.WorkspaceTest.test_init_is_idempotent_and_does_not_overwrite_background` | 重复初始化保留已有背景。 | PASS | 0.0103 |
| `test_app.WorkspaceTest.test_intake_preserves_original_and_disallows_unknown_project` | 原始附件字节保留，不存在的项目关联被拒绝。 | PASS | 0.0186 |
| `test_app.WorkspaceTest.test_oversized_document_is_reported` | 超大文件未参与搜索时明确提示。 | PASS | 0.0198 |
| `test_app.WorkspaceTest.test_project_file_matches_are_bounded_and_report_truncation` | 项目资料结果数受限且显示截断。 | PASS | 0.0632 |
| `test_app.WorkspaceTest.test_project_id_cannot_escape_workspace` | 拒绝项目路径穿越及无效标识。 | PASS | 0.0138 |
| `test_app.WorkspaceTest.test_project_symlink_cannot_read_another_project` | 真实项目符号链接不得越界读取；环境不允许创建时跳过。 | SKIP | 0.0107 |
| `test_app.WorkspaceTest.test_unapproved_or_malformed_experience_is_not_used` | 异常 JSON 和未批准经验不进入上下文。 | PASS | 0.0219 |
| `test_backup.BackupTest.test_archive_symlink_and_windows_path_are_rejected` | 拒绝恶意 ZIP 符号链接及 Windows 路径穿越。 | PASS | 0.0112 |
| `test_backup.BackupTest.test_backup_cannot_be_created_inside_source` | 拒绝将快照写进源目录。 | PASS | 0.0027 |
| `test_backup.BackupTest.test_backup_with_modified_contents_fails_and_no_restore_left` | 损坏快照校验失败，清理未完成的恢复目录。 | PASS | 0.0234 |
| `test_backup.BackupTest.test_create_or_restore_will_not_overwrite` | 不覆盖已有快照或目标数据。 | PASS | 0.0126 |
| `test_backup.BackupTest.test_real_restore_includes_audio_and_preserves_bytes` | 恢复模拟录音、中文文本和空目录并验证内容。 | PASS | 0.0149 |
| `test_backup.BackupTest.test_zip_traversal_is_rejected_without_writing_outside` | 恶意归档路径不能写出恢复目录。 | PASS | 0.0108 |
| `test_transcription_queue.QueueTest.test_completed_job_exposes_result_in_shared_queue` | 模拟成功任务，将结果交还共享队列且不重复处理。 | PASS | 0.0304 |
| `test_transcription_queue.QueueTest.test_failed_job_preserves_audio_and_marks_failed` | 模拟转写失败，任务进入失败状态且保留音频。 | PASS | 0.0306 |
| `test_transcription_queue.QueueTest.test_invalid_files_and_projects_rejected` | 拒绝不受支持的文件及不安全项目标识。 | PASS | 0.013 |
| `test_transcription_queue.QueueTest.test_malformed_job_is_marked_failed_without_crashing` | 错误任务元数据归档失败并保留音频。 | PASS | 0.0192 |
| `test_transcription_queue.QueueTest.test_submit_is_atomic_and_preserves_audio` | 任务完整写入暂存后才发布，并保留原始音频。 | PASS | 0.0199 |

## 跳过与失败详情

### test_app.WorkspaceTest.test_project_symlink_cannot_read_another_project

```text
创建符号链接不可用: [WinError 1314] 客户端没有所需的特权。: '<TEMP>\\tmp0btob4il\\workspace\\projects\\chip-b' -> '<TEMP>\\tmp0btob4il\\workspace\\projects\\chip-a'
```

## 验收边界

此报告验证本地程序，不证明真实模型回答质量、PPT 生成、提示注入防御、语音/企微/内网接入、真实双机同步或异地恢复。

完整需求覆盖、缺陷修复与后续验收条件见 [GPT-6.1 验收报告](../../docs/GPT-6.1验收报告.md)。

复跑：在项目根目录执行 `python scripts/run_acceptance.py`。报告将更新；历史证据由 Git 提交记录保存。
