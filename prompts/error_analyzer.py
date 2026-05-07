ERROR_ANALYZER_PROMPT = """你是一个代码调试专家。分析以下执行错误并给出修复建议。

执行命令：{command}
错误类型：{error_type}
错误信息：
{error_message}

仓库结构：
{structure}

依赖文件：
{requirements}

相关源码上下文：
{source_context}

请分析错误原因并给出修复方案。

输出严格的 JSON，不要输出其他内容：
{{
    "root_cause": "错误根因分析",
    "fix_type": "install_dep | modify_code | modify_config | skip_step | change_command",
    "fix_commands": ["修复命令1", "修复命令2"],
    "modified_files": [
        {{"path": "文件路径", "old": "原内容片段", "new": "新内容片段"}}
    ]
}}

如果是缺少依赖，fix_type 设为 "install_dep"，fix_commands 中给出 pip install 命令。
如果是命令本身有误（如路径错误），fix_type 设为 "change_command"，fix_commands 第一个元素是修正后的完整命令。
如果是 TypeError 提示本地函数缺少参数，必须优先根据“相关源码上下文”里的函数签名修正命令，不要猜测参数名或省略必需参数。
如果是 conda 无法找到 `pytorch-cuda`、`PackagesNotFoundError` 或 solver 找不到 PyTorch/CUDA 包，fix_type 设为 "change_command"，改用 `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`；不要继续添加 conda channel。
如果是 Hugging Face/Xet 下载出现 `Read timed out`、`cas-bridge.xethub.hf.co`、`HTTPSConnectionPool`，执行器会自动重试；不要跳过下载步骤，必要时保持原命令或改为 `HF_HUB_DISABLE_XET=1 HF_ENDPOINT=https://hf-mirror.com huggingface-cli download ...`。
如果是 pip install 超时，不要通过增大 --default-timeout 修复；执行器会统一注入镜像和 pip 超时。应优先判断是否可以跳过该安装步骤、减少安装范围，或保留原命令等待更长的外层命令超时。
如果是代码问题，fix_type 设为 "modify_code"，在 modified_files 中给出修改。
如果无法修复，fix_type 设为 "skip_step"。"""
