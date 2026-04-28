#!/bin/bash
# Hermes 多角色协作系统 - 部署脚本
# 在新机器上执行：bash setup.sh
# 完整安装（含 ppt-master）：bash setup.sh --with-ppt-master

set -e

echo "========================================"
echo " Hermes 多角色协作系统 - 部署"
echo "========================================"

# 1. 检查 Hermes 是否已安装
if ! command -v hermes &> /dev/null; then
    echo "❌ 请先安装 Hermes Agent"
    exit 1
fi
echo "✅ Hermes 已安装: $(hermes --version 2>/dev/null || echo 'unknown')"

# 获取仓库路径
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📁 仓库路径: $REPO_DIR"

# 2. 部署 profiles（角色定义）
echo ""
echo "--- 部署角色 Profiles ---"
for role in writer reviewer se assistant; do
    if [ -d "$REPO_DIR/profiles/$role" ]; then
        mkdir -p ~/.hermes/profiles/$role
        cp -r "$REPO_DIR/profiles/$role/"* ~/.hermes/profiles/$role/ 2>/dev/null || true
        echo "  ✅ $role 已部署"
    fi
done

# 3. 部署 PM SOUL.md
if [ -f "$REPO_DIR/SOUL.md" ]; then
    cp "$REPO_DIR/SOUL.md" ~/.hermes/SOUL.md
    echo "  ✅ PM SOUL.md 已部署"
fi

# 4. 部署 config.yaml（如果不存在，从模板复制）
if [ ! -f ~/.hermes/config.yaml ]; then
    if [ -f "$REPO_DIR/config.yaml.example" ]; then
        cp "$REPO_DIR/config.yaml.example" ~/.hermes/config.yaml
        echo "  ⚠️  config.yaml 已从模板创建，请自行配置 API Key"
    fi
else
    echo "  ✅ config.yaml 已存在，跳过"
fi

# 5. 部署 memories
if [ -f "$REPO_DIR/memories/USER.md" ]; then
    mkdir -p ~/.hermes/memories
    cp "$REPO_DIR/memories/USER.md" ~/.hermes/memories/USER.md
    echo "  ✅ USER.md 已部署"
fi

# 6. 部署 bin
if [ -d "$REPO_DIR/bin" ]; then
    mkdir -p ~/.hermes/bin
    cp "$REPO_DIR/bin/"* ~/.hermes/bin/ 2>/dev/null || true
    echo "  ✅ bin 已部署"
fi

# 7. 部署自定义 skills
echo ""
echo "--- 部署自定义 Skills ---"

# PM 独有技能
mkdir -p ~/.hermes/skills
for skill in pptx-generator ppt-review-workflow; do
    if [ -d "$REPO_DIR/skills/$skill" ]; then
        cp -r "$REPO_DIR/skills/$skill" ~/.hermes/skills/
        echo "  ✅ PM/$skill 已部署"
    fi
done

# Writer 独有技能（文档生成类）
mkdir -p ~/.hermes/profiles/writer/skills
for skill in minimax-docx minimax-pdf minimax-xlsx; do
    if [ -d "$REPO_DIR/skills/$skill" ]; then
        cp -r "$REPO_DIR/skills/$skill" ~/.hermes/profiles/writer/skills/
        echo "  ✅ Writer/$skill 已部署"
    fi
done

# Reviewer 独有技能（文档修改类）
mkdir -p ~/.hermes/profiles/reviewer/skills/productivity
for skill in powerpoint nano-pdf; do
    if [ -d "$REPO_DIR/skills/$skill" ]; then
        cp -r "$REPO_DIR/skills/$skill" ~/.hermes/profiles/reviewer/skills/productivity/
        echo "  ✅ Reviewer/$skill 已部署"
    fi
done

# 8. ppt-master（可选大技能）
if [ "$1" = "--with-ppt-master" ]; then
    echo ""
    echo "--- 安装 ppt-master ---"
    PPT_DIR=~/.hermes/profiles/writer/skills/ppt-master
    if [ -d "$PPT_DIR" ]; then
        echo "  ✅ ppt-master 已存在，跳过"
    else
        echo "  克隆仓库..."
        git clone --depth 1 https://github.com/hugohe3/ppt-master.git "$PPT_DIR"
        echo "  创建虚拟环境..."
        cd "$PPT_DIR"
        python3 -m venv .venv
        echo "  安装依赖..."
        .venv/bin/pip install --quiet python-pptx PyMuPDF mammoth markdownify Pillow numpy requests beautifulsoup4 openpyxl
        .venv/bin/pip install --quiet svglib --no-deps reportlab
        ln -sf skills/ppt-master/SKILL.md SKILL.md
        echo "  ✅ ppt-master 已安装 (515MB)"
    fi
else
    echo ""
    echo "  💡 ppt-master 未安装（~515MB）"
    echo "     需要时执行: bash setup.sh --with-ppt-master"
fi

echo ""
echo "========================================"
echo " 部署完成！"
echo " 注意事项："
echo " 1. 编辑 ~/.hermes/config.yaml，配置 API Key"
echo " 2. 部署后重启 gateway: hermes gateway run --replace"
echo " 3. 手动重启各角色 gateway:"
echo "    hermes --profile writer gateway run --replace"
echo "    hermes --profile reviewer gateway run --replace"
echo "    hermes --profile se gateway run --replace"
echo "    hermes --profile assistant gateway run --replace"
echo "========================================"
