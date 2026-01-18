#models.py
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TextInput(BaseModel):
    text: str
    user_id: str
    session_id: Optional[str] = None

class EmotionResponse(BaseModel):
    text: str
    emotion: str
    confidence: float
    context_emotion: Optional[str] = None  # 基于上下文的情绪
    trend: Optional[str] = None  # 情绪趋势
    urgent_issue: Optional[Dict[str, Any]] = None # 紧急问题识别结果

class ChatRequest(BaseModel):
    text: str
    user_id: str
    session_id: str
    context_summary: Optional[Dict[str, Any]] = None

class ContentItem(BaseModel):
    """内容项模型"""
    id: str
    title: str
    type: str  # article, audio, video, exercise, tool
    category: str  # 分类：stress, anxiety, relationship, academic, etc.
    description: str
    url: Optional[str] = None
    duration_minutes: Optional[int] = None
    tags: List[str] = []
    emotion_tags: List[str] = []  # 适合的情绪
    difficulty: Optional[str] = None  # beginner, intermediate, advanced
    created_at: datetime = datetime.now()
    popularity: int = 0  # 热度

class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_input: str
    current_emotion: str
    conversation_summary: Dict[str, Any]
    content_types: Optional[List[str]] = None  # 指定类型
    limit: int = 3

class RecommendationResponse(BaseModel):
    """推荐响应"""
    recommendations: List[ContentItem]
    rationale: str  # 推荐理由
    match_score: Dict[str, float]  # 匹配度分数

class ChatResponse(BaseModel):
    response: str
    emotion_summary: Optional[Dict[str, Any]] = None  # 返回情绪摘要供前端显示
    urgent_issue: Optional[Dict[str, Any]] = None # 紧急问题识别结果
    recommendations: Optional[List[ContentItem]] = None  # 新增：推荐内容
    recommendation_rationale: Optional[str] = None  # 新增：推荐理由
