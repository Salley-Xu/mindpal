import logging
from typing import Any, Dict
from datetime import datetime, timedelta
import json

def setup_logging(log_level: str = "INFO"):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

def format_timedelta(td: timedelta) -> str:
    """格式化时间差"""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    elif minutes > 0:
        return f"{minutes}分钟{seconds}秒"
    else:
        return f"{seconds}秒"

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """安全地解析JSON字符串"""
    try:
        return json.loads(json_str)
    except:
        return {}

def validate_user_input(text: str, min_length: int = 1, max_length: int = 1000) -> bool:
    """验证用户输入"""
    if not text or not text.strip():
        return False
    if len(text.strip()) < min_length:
        return False
    if len(text) > max_length:
        return False
    return True

def anonymize_user_id(user_id: str) -> str:
    """匿名化用户ID（用于日志）"""
    import hashlib
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]

def calculate_support_score(conversation_summary: Dict) -> float:
    """计算对话支持度评分（0-10分）"""
    score = 5.0  # 基础分
    
    # 加分项
    if conversation_summary['conversation_stage'] == 'resolving':
        score += 2.0
    if conversation_summary['emotion_trend'] == 'improving':
        score += 2.0
    if conversation_summary['turn_count'] > 5:  # 较长的对话
        score += 1.0
    
    # 减分项
    if conversation_summary['primary_emotion'] in ['焦虑', '抑郁', '愤怒']:
        score -= 1.0
    
    return max(0.0, min(10.0, score))