#!/usr/bin/env bash
# =====================================================
#  OneHub 启动脚本 (Linux/macOS)
# =====================================================

set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  OneHub 后端服务"
echo "============================================"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 文件，将使用默认配置"
    echo "请复制 .env.example 为 .env 并填写配置"
    echo ""
fi

# 检测 Python（优先用 venv 里的，其次找真实安装，避免 Windows App Store 假 Python）
find_real_python() {
    # 1. 如果 venv 已存在，直接用 venv 里的
    if [ -f "venv/Scripts/python.exe" ]; then
        echo "venv/Scripts/python.exe"
        return
    elif [ -f "venv/bin/python" ]; then
        echo "venv/bin/python"
        return
    fi

    # 2. 扫描常见 Python 安装路径（Windows + Linux）
    local windows_user="${USERNAME:-$USER}"
    for cand in \
        "/c/Users/$windows_user/AppData/Local/Programs/Python/Python311/python.exe" \
        "/c/Users/$windows_user/AppData/Local/Programs/Python/Python312/python.exe" \
        "/c/Users/$windows_user/AppData/Local/Programs/Python/Python310/python.exe" \
        "/c/Program Files/Python311/python.exe" \
        "/c/Program Files/Python312/python.exe" \
        "/usr/bin/python3" \
        "/usr/local/bin/python3"; do
        if [ -x "$cand" ]; then
            echo "$cand"
            return
        fi
    done

    # 3. 兜底：试试 PATH 中的，但要验证它真的能跑
    for p in python3 python; do
        local found
        found="$(command -v "$p" 2>/dev/null)" || continue
        # 排除 Windows App Store 重定向器（路径含 WindowsApps）
        case "$found" in
            *WindowsApps*) continue ;;
        esac
        # 验证能否真正执行
        if "$found" --version >/dev/null 2>&1; then
            echo "$found"
            return
        fi
    done

    return 1
}

PYTHON=$(find_real_python) || {
    echo "[错误] 未找到可用的 Python，请先安装 Python 3.10+"
    echo "如果已安装，请手动指定: PYTHON=/path/to/python ./start.sh"
    exit 1
}

echo "[信息] 使用 Python: $PYTHON"
$PYTHON --version
echo ""

# 检查 FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "[信息] FFmpeg 已就绪: $(ffmpeg -version 2>&1 | head -1)"
    echo ""
else
    echo "[警告] 未找到 ffmpeg，视频转MP3功能将不可用"
    echo "请安装: apt install ffmpeg / yum install ffmpeg"
    echo ""
fi

# 创建虚拟环境（首次运行时）
if [ ! -d "venv" ]; then
    echo "[信息] 创建虚拟环境..."
    $PYTHON -m venv venv
    echo "[信息] 虚拟环境创建完成"
    echo ""
fi

# 激活虚拟环境
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[错误] 虚拟环境激活脚本未找到"
    exit 1
fi

# 安装依赖
if [ -f "requirements.txt" ]; then
    echo "[信息] 安装/更新依赖..."
    pip install -r requirements.txt -q
    echo "[信息] 依赖已就绪"
    echo ""
fi

# 启动服务
echo "[信息] 启动服务 http://0.0.0.0:8000"
echo "[信息] API 文档 http://0.0.0.0:8000/docs"
echo "[信息] 按 Ctrl+C 停止"
echo "============================================"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
