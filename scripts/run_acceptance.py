"""Run unittest and export shareable evidence without machine-specific paths."""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PURPOSES = {
    'test_candidate_cannot_promote_unknown_scope_or_changed_id': '拒绝不存在的项目、被修改编号、错误状态及空经验，保留原候选。',
    'test_cli_capture_context_and_restore_end_to_end': '通过子进程完成创建项目、收集、检索、备份、验证、恢复和恢复后读取。',
    'test_corrupt_candidate_is_reported_without_traceback_or_promotion': 'JSON 数组候选返回错误而非崩溃，不晋升、不删除原记录。',
    'test_invalid_utf8_manifest_is_cleanly_reported': '备份清单编码异常时命令返回错误。',
    'test_unreadable_directory_does_not_create_incomplete_backup': '模拟目录权限错误，确保备份失败且不留下不完整快照。',
    'test_version_prefix_does_not_displace_exact_version': 'V1.2.30 不得按 V1.2.3 的精确匹配参与排名。',
    'test_chinese_sentence_retrieves_related_project_document_only': '中文长句召回当前项目资料，排除其他项目内容。',
    'test_context_respects_project_and_experience_approval': '经验确认前不加载，确认后仅用于指定项目。',
    'test_dotted_firmware_version_is_prioritized': '带小数点的固件版本在有限检索结果中优先。',
    'test_exact_version_is_prioritized_when_results_are_bounded': '型号版本精确关键词在结果超过上限时仍能命中。',
    'test_init_is_idempotent_and_does_not_overwrite_background': '重复初始化保留已有背景。',
    'test_intake_preserves_original_and_disallows_unknown_project': '原始附件字节保留，不存在的项目关联被拒绝。',
    'test_oversized_document_is_reported': '超大文件未参与搜索时明确提示。',
    'test_project_file_matches_are_bounded_and_report_truncation': '项目资料结果数受限且显示截断。',
    'test_project_id_cannot_escape_workspace': '拒绝项目路径穿越及无效标识。',
    'test_project_symlink_cannot_read_another_project': '真实项目符号链接不得越界读取；环境不允许创建时跳过。',
    'test_unapproved_or_malformed_experience_is_not_used': '异常 JSON 和未批准经验不进入上下文。',
    'test_archive_symlink_and_windows_path_are_rejected': '拒绝恶意 ZIP 符号链接及 Windows 路径穿越。',
    'test_backup_cannot_be_created_inside_source': '拒绝将快照写进源目录。',
    'test_backup_with_modified_contents_fails_and_no_restore_left': '损坏快照校验失败，清理未完成的恢复目录。',
    'test_create_or_restore_will_not_overwrite': '不覆盖已有快照或目标数据。',
    'test_real_restore_includes_audio_and_preserves_bytes': '恢复模拟录音、中文文本和空目录并验证内容。',
    'test_zip_traversal_is_rejected_without_writing_outside': '恶意归档路径不能写出恢复目录。',
}


def scrub(value: str) -> str:
    for path, label in ((str(ROOT), '<PROJECT>'), (tempfile.gettempdir(), '<TEMP>')):
        for form in (path, path.replace('\\', '/'), path.replace('\\', '\\\\')):
            value = value.replace(form, label)
    return value


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started = {}
        self.status = {}

    def startTest(self, test):
        self.started[test.id()] = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test):
        self.status[test.id()] = ('PASS', '')
        super().addSuccess(test)

    def addSkip(self, test, reason):
        self.status[test.id()] = ('SKIP', scrub(reason))
        super().addSkip(test, scrub(reason))

    def addFailure(self, test, err):
        self.status[test.id()] = ('FAIL', scrub(self._exc_info_to_string(err, test)))
        super().addFailure(test, err)

    def addError(self, test, err):
        self.status[test.id()] = ('ERROR', scrub(self._exc_info_to_string(err, test)))
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err:
            self.status[test.id()] = ('FAIL', scrub(self._exc_info_to_string(err, test)))
        super().addSubTest(test, subtest, err)

    def stopTest(self, test):
        status, detail = self.status.get(test.id(), ('UNKNOWN', ''))
        self.records.append({'id': test.id(), 'purpose': PURPOSES.get(test._testMethodName, '见测试源码'),
                             'status': status, 'seconds': round(time.perf_counter() - self.started[test.id()], 4),
                             'detail': detail})
        super().stopTest(test)


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    stream = io.StringIO()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=EvidenceResult).run(suite)
    files = [ROOT / 'app.py', ROOT / 'backup.py', Path(__file__), *sorted((ROOT / 'tests').glob('test_*.py'))]
    evidence = {'executed_at_utc': datetime.now(timezone.utc).isoformat(),
                'environment': {'os': platform.system(), 'release': platform.release(), 'python': platform.python_version()},
                'command': 'python scripts/run_acceptance.py',
                'tested_revision': os.environ.get('TESTED_REVISION', 'local files; see sha256'),
                'summary': {'total': result.testsRun, 'passed': sum(r['status'] == 'PASS' for r in result.records),
                            'skipped': len(result.skipped), 'failures': len(result.failures), 'errors': len(result.errors)},
                'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                'cases': result.records}
    out = ROOT / 'reports' / 'acceptance'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'test-output.txt').write_text(scrub(stream.getvalue() + '\nCaptured output:\n' + captured.getvalue()), encoding='utf-8')
    s = evidence['summary']
    lines = ['# 详细测试结果', '', f"执行时间（UTC）：{evidence['executed_at_utc']}", '',
             f"环境：{evidence['environment']}；测试基准：`{evidence['tested_revision']}`。", '',
             f"共 {s['total']} 项，{s['passed']} 通过，{s['skipped']} 跳过，{s['failures']} 失败，{s['errors']} 错误。", '',
             '样例为合成数据；跳过不计通过。源文件 SHA-256 见 results.json，完整命令输出见 test-output.txt。', '',
             '| 测试编号 | 覆盖内容与预期 | 结果 | 耗时（秒） |', '| --- | --- | --- | --- |']
    for record in result.records:
        lines.append(f"| `{record['id']}` | {record['purpose']} | {record['status']} | {record['seconds']} |")
    lines += ['', '## 跳过与失败详情', '']
    for record in result.records:
        if record['detail']:
            lines += [f"### {record['id']}", '', '```text', record['detail'], '```', '']
    lines += ['## 验收边界', '',
              '此报告验证本地程序，不证明真实模型回答质量、PPT 生成、提示注入防御、语音/企微/内网接入、真实双机同步或异地恢复。', '',
              '完整需求覆盖、缺陷修复与后续验收条件见 [GPT-6.1 验收报告](../../docs/GPT-6.1验收报告.md)。', '',
              '复跑：在项目根目录执行 `python scripts/run_acceptance.py`。报告将更新；历史证据由 Git 提交记录保存。']
    (out / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(evidence['summary'], ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
