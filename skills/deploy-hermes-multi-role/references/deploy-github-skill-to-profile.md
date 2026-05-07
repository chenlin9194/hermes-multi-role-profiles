# 将 GitHub 仓库部署为 Hermes Profile Skill

> 本文件源自 `deploy-github-skill-to-profile` 技能，已合并至此。
> 适用于仓库自身包含 Hermes skill 目录结构（如 `skills/<skill-name>/SKILL.md`）
> 且需要跨文件系统搬运（Windows D: → WSL）的场景。

## 适用场景

将一个完整的 GitHub 项目（如 ppt-master）部署到某个 Hermes profile 的 `skills/` 目录下，使其成为该角色的专属技能。

典型特征：
- 仓库中自带 `skills/<skill-name>/SKILL.md`（嵌套结构）
- 包含 `references/`、`scripts/`、`templates/`、`workflows/` 等附属目录
- 需要 Python 虚拟环境和依赖安装

## 工作流

### 1. 确定源和目标

```bash
SRC=/mnt/d/Users/XXXX/ppt-master
PROFILE=writer
TARGET=~/.hermes/profiles/$PROFILE/skills/ppt-master
SKILL_NAME=ppt-master  # skill 目录名，通常与仓库名一致
```

### 2. 跨文件系统搬运（Windows ↔ WSL）

**不要用 `cp -r` 或 `mv`**——跨文件系统（D: 盘 → WSL home）时两者都会超时。

实测数据（ppt-master: 267MB / 12,968 文件）：
| 命令 | timeout | 结果 |
|------|---------|------|
| `cp -r` | 60s | ❌ 超时，部分文件复制（约5个文件） |
| `cp -r` | 180s | ❌ 超时 |
| `mv` | 60s | ❌ 超时（跨文件系统时 mv = copy + delete） |
| `rsync` | 300s | ✅ 45秒完成，12,968文件全部传输 |

使用 `rsync`，排除 `.venv/` 和 `.git/`：

```bash
# 清理目标残留（如果之前 mv/cp 部分成功了）
rm -rf $TARGET

# 创建目标目录
mkdir -p $TARGET

# rsync 搬运（显示进度，排除不需要的目录）
rsync -a --info=progress2 --exclude='.venv/' --exclude='.git/' $SRC/ $TARGET/
```

> 注意：末尾的 `$SRC/` 带斜杠表示搬运目录内容而非目录本身。
> 如果 rsync 被中断，再次执行会增量续传。

### 3. 创建 SKILL.md 软链接

如果仓库中的 SKILL.md 嵌套在子目录下（如 `skills/<skill-name>/SKILL.md`），Hermes 找不到它。需要在 skill 根目录建软链接：

```bash
cd $TARGET
ln -sf skills/$SKILL_NAME/SKILL.md SKILL.md
```

### 4. 创建虚拟环境并安装依赖

```bash
cd $TARGET
python3 -m venv .venv

# 安装核心依赖
.venv/bin/pip install python-pptx PyMuPDF mammoth markdownify Pillow numpy
.venv/bin/pip install requests beautifulsoup4 openpyxl

# SVG 处理（WSL 无系统 cairo 库时需 --no-deps）
.venv/bin/pip install svglib --no-deps
.venv/bin/pip install reportlab
```

### 5. 验证

```bash
ls -la $TARGET/SKILL.md
head -5 $TARGET/SKILL.md
find $TARGET -type f | wc -l
du -sh $TARGET
.venv/bin/python --version
.venv/bin/pip list | grep -iE "pptx|mupdf|mammoth|pillow|svglib"
```

## 已知限制

| 问题 | 影响 | 解决 |
|------|------|------|
| WSL 无系统级 cairo 库 | cairosvg / pycairo 无法安装 | svglib --no-deps 兜底 |
| 跨文件系统 mv/cp 超时 | >100MB 或 >5000 文件时易超时 | 使用 rsync + exclude |
| 仓库 SKILL.md 嵌套 | Hermes 在 skill 根目录找不到 | 创建软链接到根目录 |
| 旧 .venv 不能跨文件系统搬运 | 虚拟环境路径绑定无法复用 | 在新位置重建 |

## 清理源路径

```bash
find $TARGET -type f | wc -l   # 确认完整
rm -rf $SRC
```
