#conversation_manager.py
from datetime import datetime
from typing import Dict, List

class ConversationManager:
    """管理对话上下文和情绪演变"""
    
    def __init__(self):
        self.sessions = {}  # session_id -> 对话数据
        self.max_history = 20  # 最大对话轮次
    
    def get_or_create_session(self, user_id: str, session_id: str):
        """获取或创建对话会话"""
        key = f"{user_id}_{session_id}"
        if key not in self.sessions:
            self.sessions[key] = {
                'history': [],  # 对话历史
                'emotion_timeline': [],  # 情绪时间线
                'key_concerns': [],  # 关键关切点
                'conversation_stage': 'initial',  # initial, exploring, deepening, resolving
                'last_active': datetime.now()
            }
        return self.sessions[key]
    
    def add_interaction(self, user_id: str, session_id: str, 
                        user_input: str, emotion: str, ai_response: str):
        """添加一次完整交互"""
        session = self.get_or_create_session(user_id, session_id)
        
        # 添加到历史
        session['history'].append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'detected_emotion': emotion,
            'ai_response': ai_response
        })
        
        # 保持历史长度
        if len(session['history']) > self.max_history:
            session['history'] = session['history'][-self.max_history:]
        
        # 更新情绪时间线
        session['emotion_timeline'].append({
            'time': datetime.now().isoformat(),
            'emotion': emotion,
            'text_snippet': user_input[:50]
        })
        
        # 分析对话阶段
        self._analyze_conversation_stage(session)
        
        # 提取关键关切点
        self._extract_key_concerns(session, user_input)
        
        session['last_active'] = datetime.now()
        
        return session
    
    def _analyze_conversation_stage(self, session: Dict):
        """分析当前对话阶段"""
        history_len = len(session['history'])
        
        if history_len <= 2:
            session['conversation_stage'] = 'initial'
        elif history_len <= 6:
            session['conversation_stage'] = 'exploring'
        elif history_len <= 12:
            session['conversation_stage'] = 'deepening'
        else:
            session['conversation_stage'] = 'resolving'
    
    def _extract_key_concerns(self, session: Dict, user_input: str):
        """提取关键关切点"""
        # 简单关键词提取，实际可更复杂
        concern_keywords = {
            'relationship': ['对象', '男朋友', '女朋友', '室友', '朋友', '关系'],
            'academic': ['考试', '学习', '论文', '毕业', '成绩', '复习'],
            'future': ['将来', '未来', '以后', '规划', '方向'],
            'self': ['我', '自己', '个人', '性格', '习惯']
        }
        
        for concern_type, keywords in concern_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                if concern_type not in session['key_concerns']:
                    session['key_concerns'].append(concern_type)
        
        # 保持最多5个关切点
        session['key_concerns'] = session['key_concerns'][:5]
    
    def get_conversation_summary(self, user_id: str, session_id: str):
        """获取对话摘要"""
        session = self.get_or_create_session(user_id, session_id)
        
        if not session['history']:
            # 返回默认摘要而不是None
            return {
                'conversation_stage': 'initial',
                'primary_emotion': '中性',
                'emotion_trend': 'new',
                'key_concerns': [],
                'turn_count': 0,
                'recent_emotions': []
            }
        
        # 分析情绪趋势
        emotions = [h['detected_emotion'] for h in session['history'][-5:]]
        primary_emotion = max(set(emotions), key=emotions.count) if emotions else '中性'
        
        # 计算趋势
        trend = 'stable'
        if len(emotions) >= 3:
            recent = emotions[-3:]
            if all(e in ['焦虑', '压力', '愤怒'] for e in recent):
                trend = 'escalating'
            elif all(e in ['平静', '中性', '快乐'] for e in recent):
                trend = 'improving'
        
        return {
            'conversation_stage': session['conversation_stage'],
            'primary_emotion': primary_emotion,
            'emotion_trend': trend,
            'key_concerns': session['key_concerns'],
            'turn_count': len(session['history']),
            'recent_emotions': emotions[-3:] if len(emotions) >= 3 else emotions
        }
    
conversation_manager=ConversationManager()