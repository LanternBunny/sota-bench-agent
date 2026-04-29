ERROR_ANALYZER_PROMPT = """你是一个代码调试专家。分析以下执行错误并给出修复建议。

执行命令：{command}
错误类型：{error_type}
错误信息：
{error_message}

仓库结构：
{structure}

依赖文件：
{requirements}

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
如果是代码问题，fix_type 设为 "modify_code"，在 modified_files 中给出修改。
如果无法修复，fix_type 设为 "skip_step"。"""
