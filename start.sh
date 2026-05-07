#!/bin/bash
cd "$(dirname "$0")"

conda activate langgraph 2>/dev/null || source activate langgraph 2>/dev/null

LG_PORT=2026
ST_PORT=8502

export CODE_AGENT_COMMAND_TIMEOUT=${CODE_AGENT_COMMAND_TIMEOUT:-3600}
export CODE_AGENT_GIT_CLONE_TIMEOUT=${CODE_AGENT_GIT_CLONE_TIMEOUT:-1200}
export PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}
export PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}
export PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT:-3000}
export PIP_RETRIES=${PIP_RETRIES:-10}
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export CODE_AGENT_GIT_SSL_BACKEND=${CODE_AGENT_GIT_SSL_BACKEND:-gnutls}
export CODE_AGENT_CONDA_CHANNELS=${CODE_AGENT_CONDA_CHANNELS:-https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main,https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r,https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge}

# --- 清理旧进程 ---
if lsof -i :$LG_PORT -sTCP:LISTEN &>/dev/null; then
    OLD_PID=$(lsof -ti :$LG_PORT -sTCP:LISTEN | head -1)
    echo "[清理] 关闭旧 langgraph dev (PID: $OLD_PID)..."
    kill $OLD_PID 2>/dev/null
    sleep 1
fi

if lsof -i :$ST_PORT -sTCP:LISTEN &>/dev/null; then
    OLD_PID=$(lsof -ti :$ST_PORT -sTCP:LISTEN | head -1)
    echo "[清理] 关闭旧 streamlit (PID: $OLD_PID)..."
    kill $OLD_PID 2>/dev/null
    sleep 1
fi

# --- 找可用端口 ---
find_free_port() {
    local port=$1
    while lsof -i :$port -sTCP:LISTEN &>/dev/null; do
        port=$((port + 1))
    done
    echo $port
}

LG_PORT=$(find_free_port $LG_PORT)
ST_PORT=$(find_free_port $ST_PORT)

# --- 启动 langgraph dev ---
echo "[启动] langgraph dev (port $LG_PORT)..."
mkdir -p outputs
nohup langgraph dev --port $LG_PORT > outputs/langgraph_dev.log 2>&1 &
LG_PID=$!
sleep 3

STUDIO_URL=$(grep -Eo 'https://smith\.langchain\.com/studio/\?baseUrl=[^[:space:]]+' outputs/langgraph_dev.log | tail -1)
if [ -z "$STUDIO_URL" ]; then
    STUDIO_URL="https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:${LG_PORT}"
fi

if kill -0 $LG_PID 2>/dev/null; then
    echo "[OK] langgraph dev 已启动 (PID: $LG_PID)"
else
    echo "[警告] langgraph dev 启动失败，查看 outputs/langgraph_dev.log"
fi

# --- 输出访问信息 ---
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
SERVER_IP=${SERVER_IP:-$(hostname)}

echo ""
echo "=============================================="
echo "  服务已启动"
echo "=============================================="
echo ""
echo "  LangGraph Studio:"
echo "    ${STUDIO_URL}"
echo ""
echo "  Streamlit App:"
echo "    http://localhost:${ST_PORT}"
echo ""
echo "----------------------------------------------"
echo "  SSH 端口转发（在本地终端执行）:"
echo ""
echo "    ssh -L ${ST_PORT}:127.0.0.1:${ST_PORT} -L ${LG_PORT}:127.0.0.1:${LG_PORT} ${USER}@${SERVER_IP}"
echo ""
echo "  转发后本地浏览器打开:"
echo "    Streamlit:       http://localhost:${ST_PORT}"
echo "    LangGraph Studio: ${STUDIO_URL}"
echo "=============================================="
echo ""

# --- 启动 streamlit（前台） ---
echo "[启动] streamlit run app.py (port $ST_PORT)..."
streamlit run app.py --server.port $ST_PORT --server.address 0.0.0.0
