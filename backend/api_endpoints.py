# api_endpoints.py - 完整路由版本
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
import time

from models import TextInput, EmotionResponse, ChatRequest, ChatResponse, ContentItem
from conversation_manager import conversation_manager
from emotion_analyzer import emotion_analyzer
from response_generator import response_generator
from urgent_detector import urgent_detector, urgent_logger
from content_recommender import content_recommender
from content_db import content_db
from utils import validate_user_input

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# ==================== 首页和健康检查 ====================
@router.get("/")
async def root():
    """首页"""
    return {
        "message": "MindPal Pro 后端服务运行中",
        "version": "3.2",
        "feature": "上下文感知对话系统 + 个性化推荐",
        "active_sessions": len(conversation_manager.sessions),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "emotion_analysis": "/emotion/analyze",
            "chat": "/chat/intelligent",
            "content_recommend": "/content/recommend"
        }
    }

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "model": "deepseek-chat",
        "conversation_manager": "active",
        "session_count": len(conversation_manager.sessions),
        "content_items": len(content_db.content_items),
        "timestamp": time.time()
    }

# ==================== 情绪分析API ====================
@router.post("/emotion/analyze", response_model=EmotionResponse)
async def analyze_emotion(input_data: TextInput):
    """情绪分析API"""
    if not validate_user_input(input_data.text):
        raise HTTPException(status_code=400, detail="输入文本无效")
    
    logger.info(f"情绪分析请求: user_id={input_data.user_id}")
    
    # 获取对话摘要
    conversation_summary = None
    if input_data.session_id:
        conversation_summary = conversation_manager.get_conversation_summary(
            input_data.user_id, input_data.session_id
        )
    
    # 分析情绪
    current_emotion, context_emotion, confidence = emotion_analyzer.analyze_with_context(
        input_data.text, conversation_summary
    )
    
    # 检测紧急情况
    urgent_issue = urgent_detector.detect(input_data.text, current_emotion)
    
    # 分析趋势
    trend = "new"
    if conversation_summary and conversation_summary.get('recent_emotions'):
        recent = conversation_summary['recent_emotions']
        if current_emotion in recent:
            trend = "consistent"
        elif current_emotion in ['焦虑', '压力', '愤怒'] and '平静' in recent:
            trend = "escalating"
        elif current_emotion in ['平静', '中性', '快乐'] and '焦虑' in recent:
            trend = "calming"
    
    # 记录紧急情况
    if urgent_issue['level'] in ['urgent', 'warning_high']:
        logger.warning(f"紧急情况: {urgent_issue['level']}, 用户: {input_data.user_id}")
    
    return EmotionResponse(
        text=input_data.text,
        emotion=current_emotion,
        confidence=confidence,
        context_emotion=context_emotion,
        trend=trend,
        urgent_issue=urgent_issue
    )

# ==================== 智能对话API ====================
@router.post("/chat/intelligent", response_model=ChatResponse)
async def intelligent_chat(chat_request: ChatRequest):
    """智能对话API"""
    start_time = time.time()
    
    if not validate_user_input(chat_request.text):
        raise HTTPException(status_code=400, detail="输入文本无效")
    
    logger.info(f"智能对话请求: user_id={chat_request.user_id}, session_id={chat_request.session_id}")
    
    try:
        # 1. 获取或创建对话会话
        session = conversation_manager.get_or_create_session(
            chat_request.user_id, chat_request.session_id
        )
        
        # 2. 获取对话摘要
        conversation_summary = conversation_manager.get_conversation_summary(
            chat_request.user_id, chat_request.session_id
        )
        
        # 确保conversation_summary不为None
        if not conversation_summary:
            conversation_summary = {
                'conversation_stage': 'initial',
                'key_concerns': [],
                'turn_count': 0,
                'recent_emotions': []
            }
        
        # 3. 分析当前情绪
        current_emotion, context_emotion, confidence = emotion_analyzer.analyze_with_context(
            chat_request.text, conversation_summary
        )
        
        logger.info(f"情绪分析结果: 当前={current_emotion}, 深层={context_emotion}")
        
        # 4. 检测紧急情况
        urgent_issue = urgent_detector.detect(chat_request.text, current_emotion)
        
        if urgent_issue['level'] in ['urgent', 'warning_high']:
            logger.warning(f"紧急情况检测: 级别={urgent_issue['level']}, 触发词={urgent_issue.get('triggers', [])}")
        
        # 5. 准备历史文本
        history_text = ""
        if session['history']:
            recent_history = session['history'][-3:]
            for i, h in enumerate(recent_history):
                history_text += f"用户{i+1}: {h['user_input'][:100]}...\n"
                history_text += f"助手{i+1}: {h['ai_response'][:100]}...\n\n"
        
        # 6. 生成回应
        if urgent_issue['level'] in ['urgent', 'warning_high', 'warning']:
            ai_response = urgent_detector.generate_crisis_response(
                chat_request.text, urgent_issue, conversation_summary
            )
            if not ai_response:
                ai_response = response_generator.generate_with_strategy(
                    user_input=chat_request.text,
                    current_emotion=current_emotion,
                    context_emotion=context_emotion,
                    conversation_summary=conversation_summary,
                    history_text=history_text
                )
        else:
            ai_response = response_generator.generate_with_strategy(
                user_input=chat_request.text,
                current_emotion=current_emotion,
                context_emotion=context_emotion,
                conversation_summary=conversation_summary,
                history_text=history_text
            )
        
        # 7. 记录交互
        conversation_manager.add_interaction(
            user_id=chat_request.user_id,
            session_id=chat_request.session_id,
            user_input=chat_request.text,
            emotion=current_emotion,
            ai_response=ai_response
        )
        
        # 8. 记录紧急情况
        if urgent_issue['level'] in ['urgent', 'warning_high']:
            interaction_data = {
                'user_id': chat_request.user_id,
                'session_id': chat_request.session_id,
                'user_input': chat_request.text,
                'emotion': current_emotion,
                'ai_response': ai_response,
                'urgent_issue': urgent_issue
            }
            urgent_logger.log_interaction(interaction_data)
        
        # 9. 内容推荐
        recommendations = []
        recommendation_rationale = ""
        
        turn_count = conversation_summary.get('turn_count', 0)
        should_recommend = (
            turn_count >= 2 and 
            turn_count % 5 == 0 and  # 每5轮推荐一次
            conversation_summary.get('conversation_stage') in ['exploring', 'deepening', 'resolving']
        )
        
        if should_recommend:
            try:
                rec_items, rationale, _ = content_recommender.recommend_content(
                    user_input=chat_request.text,
                    current_emotion=current_emotion,
                    conversation_summary=conversation_summary,
                    limit=2
                )
                recommendations = rec_items
                recommendation_rationale = rationale
                logger.info(f"推荐了 {len(recommendations)} 个内容")
            except Exception as e:
                logger.error(f"内容推荐失败: {e}")
        
        # 10. 获取更新后的对话摘要
        updated_summary = conversation_manager.get_conversation_summary(
            chat_request.user_id, chat_request.session_id
        )
        
        processing_time = time.time() - start_time
        logger.info(f"对话处理完成: 耗时={processing_time:.2f}秒")
        
        return ChatResponse(
            response=ai_response,
            emotion_summary={
                'current_emotion': current_emotion,
                'context_emotion': context_emotion,
                'conversation_stage': updated_summary['conversation_stage'],
                'emotion_trend': updated_summary['emotion_trend'],
                'turn_count': updated_summary['turn_count'],
                'key_concerns': updated_summary['key_concerns']
            },
            urgent_issue=urgent_issue,
            recommendations=recommendations,
            recommendation_rationale=recommendation_rationale
        )
        
    except Exception as e:
        logger.error(f"智能对话处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# ==================== 会话管理API ====================
@router.get("/session/{user_id}/{session_id}/summary")
async def get_session_summary(user_id: str, session_id: str):
    """获取会话摘要"""
    summary = conversation_manager.get_conversation_summary(user_id, session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session = conversation_manager.get_or_create_session(user_id, session_id)
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "summary": summary,
        "recent_history": session['history'][-5:] if session['history'] else [],
        "active": True
    }

@router.delete("/session/{user_id}/{session_id}")
async def clear_session(user_id: str, session_id: str):
    """清除会话"""
    key = f"{user_id}_{session_id}"
    if key in conversation_manager.sessions:
        del conversation_manager.sessions[key]
        logger.info(f"会话已清除: {key}")
    return {"message": "会话已清除"}

# ==================== 紧急情况管理API ====================
@router.get("/urgent/cases")
async def get_recent_urgent_cases(days: int = 1, level: Optional[str] = None):
    """获取最近的紧急情况记录"""
    if days > 30:  # 限制查询天数
        days = 30
    
    result = urgent_logger.get_recent_cases(days, level)
    return result

@router.get("/resources/emergency")
async def get_emergency_resources():
    """获取紧急求助资源"""
    return {
        'resources': [
            {
                'name': '全国心理援助热线',
                'phone': '400-161-9995',
                'hours': '24小时',
                'description': '专业的心理援助服务'
            },
            {
                'name': '北京心理援助热线',
                'phone': '010-82951332',
                'hours': '24小时',
                'description': '北京市心理援助热线'
            },
            {
                'name': '简单心理',
                'url': 'https://www.jiandanxinli.com',
                'description': '在线心理咨询平台'
            }
        ],
        'tips': [
            '你不是一个人，很多人愿意帮助你',
            '寻求帮助是勇敢和明智的选择',
            '紧急情况下请立即联系专业人员',
            '你的感受是重要的，值得被倾听'
        ]
    }

# ==================== 内容推荐API ====================
@router.post("/content/recommend")
async def recommend_content(
    user_input: str,
    current_emotion: str,
    conversation_stage: str,
    key_concerns: Optional[str] = None,
    limit: int = 3
):
    """个性化内容推荐API"""
    try:
        # 构建对话摘要
        conversation_summary = {
            'conversation_stage': conversation_stage,
            'key_concerns': key_concerns.split(',') if key_concerns else [],
            'turn_count': 1,
            'recent_emotions': [current_emotion]
        }
        
        recommendations, rationale, match_scores = content_recommender.recommend_content(
            user_input=user_input,
            current_emotion=current_emotion,
            conversation_summary=conversation_summary,
            limit=limit
        )
        
        return {
            "recommendations": recommendations,
            "rationale": rationale,
            "match_scores": match_scores
        }
        
    except Exception as e:
        logger.error(f"内容推荐API失败: {e}")
        raise HTTPException(status_code=500, detail="内容推荐失败")

@router.get("/content/search")
async def search_content(q: str, limit: int = 10):
    """搜索内容"""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="搜索关键词太短")
    
    results = content_db.search_content(q, limit)
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }

@router.get("/content/{content_id}")
async def get_content_detail(content_id: str):
    """获取内容详情"""
    content_item = content_db.get_content_by_id(content_id)
    if not content_item:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    # 增加热度
    content_db.increment_popularity(content_id)
    
    return content_item

@router.get("/content/stats")
async def get_content_stats():
    """获取内容统计信息"""
    all_content = content_db.get_all_content()
    
    stats = {
        "total_count": len(all_content),
        "by_type": {},
        "by_category": {},
        "top_popular": []
    }
    
    # 按类型统计
    for item in all_content:
        stats["by_type"][item.type] = stats["by_type"].get(item.type, 0) + 1
        stats["by_category"][item.category] = stats["by_category"].get(item.category, 0) + 1
    
    # 热门内容
    sorted_by_popularity = sorted(all_content, key=lambda x: x.popularity, reverse=True)[:10]
    stats["top_popular"] = [
        {"id": item.id, "title": item.title, "popularity": item.popularity}
        for item in sorted_by_popularity
    ]
    
    return stats