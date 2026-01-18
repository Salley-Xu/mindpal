import logging
from typing import Optional, Dict, Tuple
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)

class EmotionAnalyzer:
    """情绪分析器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.API_BASE_URL
        )
        self.model = config.CHAT_MODEL
    
    def analyze_with_context(self, text: str, 
                            conversation_summary: Optional[Dict] = None) -> Tuple[str, str, float]:
        """
        基于上下文的情绪分析
        返回: (当前情绪, 基于上下文的情绪, 置信度)
        """
        try:
            current_emotion = self._analyze_base_emotion(text)
            
            if conversation_summary and conversation_summary.get('turn_count', 0) > 0:
                context_emotion = self._analyze_context_emotion(text, current_emotion, conversation_summary)
            else:
                context_emotion = current_emotion
            
            confidence = self._calculate_confidence(text, current_emotion)
            
            logger.info(f"情绪分析: 当前={current_emotion}, 深层={context_emotion}, 置信度={confidence}")
            return current_emotion, context_emotion, confidence
            
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return "中性", "中性", 0.5
    
    def _analyze_base_emotion(self, text: str) -> str:
        """基础情绪识别"""
        prompt = """分析以下文本的主要情绪（从选项中选择最贴切的）：
        选项：学业压力、焦虑、抑郁、愤怒、压力、人际矛盾、困惑、不确定、中性、快乐、平静、放松、其他

        文本："{}"
        情绪标签："""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "只返回情绪标签"},
                {"role": "user", "content": prompt.format(text)}
            ],
            temperature=0.1,
            max_tokens=10
        )
        return response.choices[0].message.content.strip()
    
    def _analyze_context_emotion(self, text: str, base_emotion: str, 
                               conversation_summary: Dict) -> str:
        """基于上下文分析深层情绪"""
        prompt = f"""你是一位专业的心理咨询师，正在分析一位用户的情绪状态。
        
        用户当前输入："{text}"
        当前检测到的表层情绪是：{base_emotion}
        
        对话上下文信息：
        - 对话阶段：{conversation_summary.get('conversation_stage', 'initial')}
        - 主要关切点：{', '.join(conversation_summary.get('key_concerns', []))}
        - 近期情绪变化：{', '.join(conversation_summary.get('recent_emotions', []))}
        
        请分析用户的深层情绪。深层情绪可能是用户没有直接表达，但隐藏在话语背后的情绪。
        深层情绪类型：
        1. 表层情绪（就是当前表达的情绪）
        2. 深层焦虑（表面情绪下隐藏的焦虑）
        3. 关系困扰（与人际关系相关的深层困扰）
        4. 自我怀疑（对自身能力或价值的怀疑）
        5. 未来迷茫（对未来的不确定和迷茫）
        6. 学业压力（与学业相关的深层压力）
        7. 情绪压抑（未能表达的负面情绪积压）
        8. 家庭压力（来自家庭的压力）
        9. 社交恐惧（对社交场合的恐惧）
        
        请以以下格式回答：
        深层情绪：[你的选择]
        解释：[简要解释]"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        result = response.choices[0].message.content.strip()
        
        # 解析结果
        if "深层情绪：" in result:
            lines = result.split('\n')
            for line in lines:
                if line.startswith("深层情绪："):
                    context_emotion = line.replace("深层情绪：", "").strip()
                    break
            else:
                context_emotion = base_emotion
        else:
            context_emotion = base_emotion
        
        logger.debug(f"深层情绪分析: {base_emotion} -> {context_emotion}")
        return context_emotion
    
    def _calculate_confidence(self, text: str, emotion: str) -> float:
        """计算置信度"""
        base_confidence = 0.85
        
        # 根据文本长度调整置信度
        if len(text) < 10:
            base_confidence -= 0.2
        elif len(text) > 100:
            base_confidence += 0.1
        
        # 中性情绪置信度较低
        if emotion == '中性':
            base_confidence -= 0.1
        
        return max(0.5, min(1.0, base_confidence))
    
emotion_analyzer = EmotionAnalyzer()