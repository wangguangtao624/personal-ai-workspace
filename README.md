# 个人 AI 工作与成长系统

这是一个本地优先的知识项目起点：收集文字、链接和文件，维护个人与岗位背景、项目和目标，并让 Codex 根据任务读取相关资料、提出成果和经验候选。家里和公司可各持有一份副本，通过经授权的私有 GitHub 仓库同步。

第一版采用 **Python 标准库 + 本地文件 + Codex**。收件箱保存输入，AI 整理、语音转写、PPT 制作和经验提炼由你在相应工具中主动发起；项目本身不提供模型、不自动运行、不自动下载抖音、不监听企业微信。MCP、定时任务和网页界面均未预设为可用。

## 开始使用

1. 安装可用的 Python 3，并在终端中进入项目根目录。Windows 可将下文的 `python` 换成可用的 `py`。
2. 执行 `python app.py --data data init` 创建数据区。`data/` 是本机资料；确认项目的 Git 忽略设置后，再决定哪些资料有权进入私有仓库。不要提交密码、API 密钥和受限制的资料。
3. 编辑 `data/context/personal/profile.md` 和 `data/context/role/role.md`。创建项目后，编辑 `data/projects/<项目标识>/overview.md`。也可参考 `templates/` 中的模板；未填的字段就是未知信息，不是事实。
4. 在本项目中打开 Codex，提交任务，要求它阅读适用的 `AGENTS.md` 和相关资料。也可先通过 CLI 生成上下文，再请 Codex检查和完成任务。

下例以 `data` 为数据目录、`chip-a` 为项目标识。项目是示例，不能当成用户的真实资料：

```powershell
python app.py --data data init
python app.py --data data project create chip-a --name "芯片 A 示例"
python app.py --data data intake --type text --value "今天需要梳理固件测试环境" --project chip-a
python app.py --data data intake --type link --value "https://example.com/example" --project chip-a
python app.py --data data context --project chip-a --task "准备固件测试方案"
python app.py --data data experience propose --text "测试汇报中列出阻塞事项" --scope chip-a --source "示例反馈"
```

最后一条命令产生待确认编号；`--scope` 接受 `general` 或已有项目标识。本例只适用于 `chip-a`；经你检查并决定复用后，将下面的示例编号替换成实际编号：

```powershell
python app.py --data data experience approve 示例编号
```

详细选项以 `python app.py --help` 和相应子命令的 `--help` 为准。项目背景与文件保存位置见 [使用说明](docs/操作指南.md)。

`context` 读取个人和岗位 Markdown、指定项目概览、项目内与任务关键词或中文双字相匹配的 Markdown，以及通用或该项目的已确认经验；它不读取收件箱或联网，每个文件最多取前 12000 个字符，匹配的项目资料最多 20 个文件。双字匹配可能产生无关结果或遗漏，不是语义检索。输出是供检查的原文草稿，并非 AI 生成的最终方案。收件箱资料需先通过你和 Codex 整理到合适的位置。具体能力和检索不足时要查看原文。

## 每天怎么用

1. 开始工作前同步获准同步的资料，检查有没有冲突。
2. 录音后使用获准的语音转文字工具，或直接输入文字；添加分享链接和资料。系统保存输入，不保证自动提取链接内容。
3. 告诉 Codex：“整理今天的收件箱，区分事实、任务和待确认事项，保留来源。”
4. 遇到工作任务时指定项目和版本，让 AI 列出检索到的依据及缺口，再生成方案。对于 PPT，明确选择已获准使用的模板和原始资料，预览并修改。
5. 确认最终成果后，请 AI 提取“经验候选”；逐条确认适用范围再保存。其他聊天平台的对话需要你主动提供或通过获授权的接口取得。
6. 检查要同步的内容，完成提交和推送；音频、附件和知识库另外执行独立备份。

## 文档与模板

- [操作指南](docs/操作指南.md)：背景录入、固件测试、PPT 与经验反馈。
- [同步与备份](docs/同步与备份.md)：双设备、冲突、独立备份和恢复检查。
- [个人背景模板](templates/个人背景.md)、[岗位背景模板](templates/岗位背景.md)、[项目背景模板](templates/项目背景.md)、[目标模板](templates/目标.md)。
- `.agents/skills/`：输入整理、固件测试、PPT、目标规划和反馈沉淀的 Codex 工作流程；使用需要相应 Codex 环境和必要的文件权限。

公司资料、会议录音和第三方聊天信息在收集、提交给外部 AI、上传个人 GitHub 和备份前，分别确认有权这样做。私有仓库控制访问，但并非绝对保密；转写或摘要发往云端 AI 也属于向服务提供内容。
