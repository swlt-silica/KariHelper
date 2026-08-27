# KariHelper

借物表生成工具 — 从 Blender 工程（.blend）和 MikuMikuDance 工程（.pmm）中自动提取模型/场景，对照本地模型库 readme 匹配作者，生成借物表。

## 功能

- 解析 `.blend`（需 Blender 后台模式）/ `.pmm`（纯 Python）
- 自动读取模型库 readme 提取作者（多编码：Shift-JIS / GBK / UTF-8 / CP932）
- 作者识别支持 OpenAI 兼容接口与本机 Codex CLI（使用 ChatGPT 登录）
- 可从两个渠道获取模型列表、下拉选择并测试实际模型连接
- 无 readme 时从 PMX 内部注释挖掘作者
- 自动找同目录 `.emm` 文件，提取 MME 特效作者
- 检索表缓存：已识别的模型直接命中，不重复调用 AI
- 借物表 / 检索表均可双击编辑（Excel 式）
- 按工程分别导出 / 合并导出
- 全部作者 / 仅主要作者切换

## 使用

### Windows 便携版

1. 从 GitHub Releases 下载 `KariHelper-v1.1.0-windows-x64.zip`
2. 将 ZIP 完整解压到普通文件夹
3. 双击 `KariHelper.exe`

首次保存设置后，程序会在 EXE 旁创建 `config.json`；检索数据保存在 `data` 文件夹。移动软件时请连同整个文件夹一起移动。

### 从源码运行

```bash
python app.py
```

1. **设置** → 选择「OpenAI 兼容」或「GPT（Codex CLI / ChatGPT 登录）」渠道
2. OpenAI 兼容渠道显示 API Base、Key 和 OpenAI 模型；GPT 渠道只显示 Codex CLI 路径和 GPT 模型
3. 点击「获取模型」，在对应渠道的下拉栏选择模型；模型 ID 会回填到手动模型名
4. 点击「测试连接」发送一个极短请求，确认当前渠道和模型可用
5. **设置** → 填写模型库路径（如 `D:\模型`）和 Blender 路径
6. 添加工程文件 → 点击「解析并生成借物表」

## 目录结构

```
KariHelper/
├── app.py                  # 入口
├── main_window.py          # 主窗口（借物表表格 + 日志）
├── settings_window.py      # 设置
├── index_window.py         # 检索表管理
├── about_window.py         # 关于
├── credit_gen.py           # 借物表生成核心
├── ai_extract.py           # AI 作者提取与渠道分发
├── ai_clients.py           # OpenAI 兼容 / Codex CLI 渠道、模型枚举与连接测试
├── index_db.py             # 检索表读写
├── pmx_reader.py           # PMX 注释读取
├── editable_tree.py        # 可编辑表格组件
├── util.py                 # 编码探测、readme 查找
├── config.py               # 配置管理
├── parser/
│   ├── pmm_parser.py       # .pmm 解析
│   ├── blend_parser.py     # .blend 解析（调 Blender）
│   └── emm_parser.py       # .emm 解析（MME 特效）
└── data/
    └── models_index.json   # 检索表数据
```

## 打包

```powershell
pip install pyinstaller
.\build_release.ps1
```

输出文件位于 `release\KariHelper-v1.1.0-windows-x64.zip`。打包脚本会先运行自动测试，并只放入干净的空检索表，不会复制本机 `config.json`。
