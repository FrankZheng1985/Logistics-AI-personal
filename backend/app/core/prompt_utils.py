"""
Prompt 安全工具
防止 Prompt 注入攻击，清理用户输入
"""
import re
from typing import Optional
from loguru import logger


# 危险的 Prompt 注入模式
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|above)",
    r"forget\s+(everything|all)",
    r"new\s+instructions?:",
    r"system\s*:",
    r"assistant\s*:",
    r"你现在是",
    r"忽略(之前|上面|以上)(的|所有)",
    r"忘记(之前|上面|以上)",
    r"新的指令",
    r"从现在开始你是",
]

# 编译正则表达式
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_user_input(
    text: str, 
    max_length: int = 10000,
    strip_code_blocks: bool = True,
    check_injection: bool = True
) -> str:
    """
    清理用户输入，防止 Prompt 注入
    
    Args:
        text: 原始用户输入
        max_length: 最大长度限制
        strip_code_blocks: 是否移除代码块标记（```）
        check_injection: 是否检查注入模式
    
    Returns:
        清理后的安全文本
    """
    if not text:
        return ""
    
    # 确保是字符串
    if not isinstance(text, str):
        text = str(text)
    
    # 1. 限制长度
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"用户输入过长，已截断至 {max_length} 字符")
    
    # 2. 移除可能的代码块标记（防止注入提示词）
    if strip_code_blocks:
        text = text.replace("```", "")
        text = text.replace("---", "")
    
    # 3. 移除控制字符（保留换行和制表符）
    text = ''.join(
        char for char in text 
        if char.isprintable() or char in '\n\r\t'
    )
    
    # 4. 检查注入模式
    if check_injection:
        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                logger.warning(f"检测到可能的 Prompt 注入尝试: {pattern.pattern}")
                # 不完全拒绝，但记录警告
                break
    
    return text.strip()


def sanitize_for_json(text: str) -> str:
    """
    清理文本以便安全地嵌入 JSON
    转义特殊字符
    """
    if not text:
        return ""
    
    # JSON 特殊字符转义
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return text


def validate_llm_response(
    response: str, 
    min_length: int = 10,
    expected_format: Optional[str] = None
) -> bool:
    """
    验证 LLM 响应是否合理
    
    Args:
        response: LLM 响应文本
        min_length: 最小长度要求
        expected_format: 期望的格式 (None, "json", "markdown")
    
    Returns:
        是否通过验证
    """
    if not response:
        return False
    
    if len(response.strip()) < min_length:
        return False
    
    # 检查是否包含明显的错误标记
    error_markers = [
        "error", "无法处理", "系统错误", "我不能", "I cannot",
        "抱歉，我无法", "Sorry, I can't"
    ]
    response_lower = response.lower()
    for marker in error_markers:
        if marker.lower() in response_lower:
            logger.warning(f"LLM 响应包含错误标记: {marker}")
            # 不返回 False，只是记录警告
            break
    
    # JSON 格式验证
    if expected_format == "json":
        import json
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError:
            logger.warning("LLM 响应不是有效的 JSON 格式")
            return False
    
    return True


def wrap_user_content(content: str, context: str = "用户输入") -> str:
    """
    安全地包装用户内容，明确标记边界
    
    Args:
        content: 用户内容
        context: 上下文说明
    
    Returns:
        包装后的内容
    """
    sanitized = sanitize_user_input(content)
    
    return f"""
<{context}>
{sanitized}
</{context}>
""".strip()


def extract_safe_json(text: str) -> Optional[dict]:
    """
    从 LLM 响应中安全地提取 JSON
    处理常见的格式问题
    """
    import json
    
    if not text:
        return None
    
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 块
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'\{[\s\S]*\}',                   # { ... }
        r'\[[\s\S]*\]',                   # [ ... ]
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    logger.warning("无法从响应中提取有效 JSON")
    return None
