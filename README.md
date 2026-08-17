# KariHelper

借物表生成工具 — 从 Blender 工程（.blend）和 MikuMikuDance 工程（.pmm）中自动提取模型/场景，对照本地模型库 readme 匹配作者，生成借物表。

## 功能

- 解析 `.blend`（需 Blender 后台模式）/ `.pmm`（纯 Python）
- 自动读取模型库 readme 提取作者（多编码：Shift-JIS / GBK / UTF-8 / CP932）
- 无 readme 时从 PMX 内部注释挖掘作者
- 自动找同目录 `.emm` 文件，提取 MME 特效作者
- 检索表缓存：已识别的模型直接命中，不重复调用 AI
- 借物表 / 检索表均可双击编辑（Excel 式）
- 按工程分别导出 / 合并导出
- 全部作者 / 仅主要作者切换

## 使用

```bash
python app.py
```

1. **设置** → 填写 OpenAI 兼容 API 地址和 Key（如 DeepSeek）
2. **设置** → 填写模型库路径（如 `D:\模型`）
3. **设置** → Blender 路径（解析 .blend 时需要，.pmm 不需要）
4. 添加工程文件 → 点击「解析并生成借物表」

## 目录结构

```
KariHelper/
├── app.py                  # 入口
├── main_window.py          # 主窗口（借物表表格 + 日志）
├── settings_window.py      # 设置
├── index_window.py         # 检索表管理
├── about_window.py         # 关于
├── credit_gen.py           # 借物表生成核心
├── ai_extract.py           # AI 作者提取（OpenAI 兼容）
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

```bash
pip install pyinstaller
pyinstaller -F -w --name KariHelper app.py
```
