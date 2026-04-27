---
name: ppt-master
description: >
  AI驱动的PPT生成工具，将PDF/DOCX/URL/Markdown转换为原生可编辑的PPTX。
  使用ppt-master项目（https://github.com/hugohe3/ppt-master）的工作流。
  当用户要求"生成PPT"、"做PPT"、"制作演示文稿"时使用此技能。
---

# PPT Master Skill

## 项目位置

`/mnt/d/Users/80318604/ppt-master/`

虚拟环境：`.venv/bin/python`

## 快速使用

### 方式一：在项目目录下与AI对话

1. 进入项目目录，启动AI IDE（Claude Code / Cursor等）
2. 将源文件放入 `projects/` 目录
3. 告诉AI："请用 projects/xxx.pdf 生成PPT"
4. AI自动执行完整工作流，输出到 `exports/`

### 方式二：命令行脚本（部分功能）

```bash
cd /mnt/d/Users/80318604/ppt-master

# 源文件转Markdown
.venv/bin/python skills/ppt-master/scripts/source_to_md/pdf_to_md.py <PDF文件>
.venv/bin/python skills/ppt-master/scripts/source_to_md/doc_to_md.py <DOCX文件>
.venv/bin/python skills/ppt-master/scripts/source_to_md/web_to_md.py <URL>

# 创建项目
.venv/bin/python skills/ppt-master/scripts/project_manager.py init <项目名> --format ppt169

# 导入源文件
.venv/bin/python skills/ppt-master/scripts/project_manager.py import-sources <项目路径> <源文件...> --move

# 后处理流程（必须依次执行）
.venv/bin/python skills/ppt-master/scripts/total_md_split.py <项目路径>
.venv/bin/python skills/ppt-master/scripts/finalize_svg.py <项目路径>
.venv/bin/python skills/ppt-master/scripts/svg_to_pptx.py <项目路径> -s final

# 输出：exports/<项目名>_<时间戳>.pptx
```

## 核心工作流

```
源文档 → 创建项目 → 模板选择 → 八项确认 → SVG生成 → PPTX导出
```

**重要约束：**
- 必须严格串行执行，不可并行或跳步
- SVG生成必须由主Agent完成，不可委派给子Agent
- 输出文件在 `exports/` 目录

## 模板类型

| 模板 | 用途 |
|------|------|
| Magazine | 杂志风格，暖色调，图文并茂 |
| Academic | 学术研究，结构化，数据驱动 |
| Dark Art | 电影风格，深色背景，画廊美学 |
| Nature | 自然纪录片，沉浸式摄影 |
| Tech/SaaS | 科技产品，白色卡片，定价表 |
| Product Launch | 产品发布，高对比，规格突出 |

## 支持的源格式

- PDF
- DOCX / Word
- PPTX / PowerPoint
- EPUB / HTML
- URL / 网页（包括微信公众号）
- Markdown / 纯文本

## 画布格式

| 格式 | 尺寸 |
|------|------|
| PPT 16:9 | 1280×720 |
| PPT 4:3 | 1024×768 |
| 小红书 | 1242×1660 |
| 微信朋友圈 | 1080×1080 |
| Story | 1080×1920 |

## 注意事项

1. 首次使用需在AI IDE中执行完整工作流
2. 输出的PPTX可直接在PowerPoint中编辑（真实形状，非图片）
3. 需要 Office 2016+ 打开
4. 可选AI图像生成（需配置 .env 中的 API key）

## 部署与运维

### 首次部署（WSL 无 sudo 环境）

```bash
# 1. 克隆到目标路径（仓库 ~229MB，下载可能较慢）
mkdir -p /mnt/d/Users/80318604
cd /mnt/d/Users/80318604
git clone --depth 1 https://github.com/hugohe3/ppt-master.git

# 2. 安装 pip（系统可能没有 pip3）
curl -sS https://bootstrap.pypa.io/get-pip.py | python3 --user
# pip 安装到 ~/.local/bin/pip

# 3. 创建虚拟环境（注意：python3 -m venv 失败因为没有 ensurepip）
~/.local/bin/pip install virtualenv    # 先安装 virtualenv
~/.local/bin/virtualenv .venv          # 用 virtualenv 命令创建

# 4. 安装依赖（逐个安装以避免 pycairo 阻断）
.venv/bin/pip install python-pptx PyMuPDF mammoth markdownify ebooklib nbconvert
.venv/bin/pip install openpyxl Pillow numpy requests beautifulsoup4
.venv/bin/pip install svglib --no-deps        # pycairo 缺少系统级 cairo 库
.venv/bin/pip install reportlab
```

### Writer 角色集成

Writer 的专属技能已注册到 `~/.hermes/profiles/writer/skills/productivity/ppt-master/`。
当使用 Writer 角色生成 PPT 时，路径为 `/mnt/d/Users/80318604/ppt-master/`。

## 已知限制

| 问题 | 影响 | 解决方案 |
|------|------|----------|
| pycairo 未安装（缺系统 cairo 库） | SVG→PNG 兼容模式降级 | svglib --no-deps 兜底，可处理大部分 SVG |
| `python3 -m venv` 不可用 | 无法用标准方式创建虚拟环境 | 使用 virtualenv 替代 |
| 无 `sudo`/`apt` 权限 | 无法安装系统级依赖 | pip --user 安装 Python 包，跳过系统级依赖 |