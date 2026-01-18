import logging
from typing import List, Dict, Any, Tuple
import re
from datetime import datetime
from openai import OpenAI
from config import config
from models import ContentItem
from conversation_manager import ConversationManager
from content_db import content_db

logger = logging.getLogger(__name__)

class ContentRecommender:
    """个性化内容推荐引擎"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.API_BASE_URL
        )
        self.model = config.CHAT_MODEL
        
        # 情绪到内容的映射权重
        self.emotion_weights = {
            "学业压力": ["academic", "stress_management"],
            "焦虑": ["relaxation", "mindfulness", "anxiety"],
            "抑郁": ["self_reflection", "mood_management"],
            "愤怒": ["anger_management", "emotional_regulation"],
            "压力": ["stress_management", "relaxation"],
            "人际矛盾": ["relationship", "communication"],
            "困惑": ["self_reflection", "decision_making"],
            "不确定": ["future", "decision_making"],
            "未来迷茫": ["future", "career_planning"],
            "自我怀疑": ["self_esteem", "self_reflection"],
            "孤独": ["relationship", "social_skills"],
            "失眠": ["sleep", "relaxation"]
        }
        
        # 对话阶段到内容深度的映射
        self.stage_depth_mapping = {
            "initial": "beginner",
            "exploring": "beginner",
            "deepening": "intermediate",
            "resolving": ["intermediate", "advanced"]
        }
    
    def recommend_content(self, 
                         user_input: str,
                         current_emotion: str,
                         conversation_summary: Dict[str, Any],
                         content_types: List[str] = None,
                         limit: int = 3) -> Tuple[List[ContentItem], str, Dict[str, float]]:
        """
        推荐个性化内容
        
        返回: (推荐内容列表, 推荐理由, 匹配度分数)
        """
        try:
            # 策略1: 基于情绪和对话上下文的规则推荐
            rule_based_recs = self._rule_based_recommendation(
                user_input, current_emotion, conversation_summary, limit
            )
            
            # 策略2: 使用AI进行智能推荐
            ai_based_recs = self._ai_based_recommendation(
                user_input, current_emotion, conversation_summary, limit
            )
            
            # 合并推荐结果，去重
            all_recs = {}
            for rec in rule_based_recs + ai_based_recs:
                if rec.id not in all_recs:
                    all_recs[rec.id] = rec
            
            # 按相关度排序
            recommended_items = list(all_recs.values())[:limit]
            
            # 生成推荐理由
            rationale = self._generate_rationale(
                recommended_items, user_input, current_emotion, conversation_summary
            )
            
            # 计算匹配度分数
            match_scores = self._calculate_match_scores(
                recommended_items, user_input, current_emotion, conversation_summary
            )
            
            return recommended_items, rationale, match_scores
            
        except Exception as e:
            logger.error(f"内容推荐失败: {e}")
            # 返回默认推荐
            default_recs = content_db.search_content(current_emotion, limit=limit)
            return default_recs, "根据你的当前状态推荐以下内容", {"default": 0.7}
    
    def _rule_based_recommendation(self,
                                  user_input: str,
                                  current_emotion: str,
                                  conversation_summary: Dict[str, Any],
                                  limit: int) -> List[ContentItem]:
        """基于规则的推荐"""
        all_content = content_db.get_all_content()
        scored_items = []
        
        # 提取关键词
        keywords = self._extract_keywords(user_input)
        
        for item in all_content:
            score = 0.0
            
            # 1. 情绪匹配（权重最高）
            if current_emotion in item.emotion_tags:
                score += 3.0
            for emotion_tag in item.emotion_tags:
                if emotion_tag in self.emotion_weights:
                    if current_emotion in self.emotion_weights[emotion_tag]:
                        score += 2.0
            
            # 2. 关键词匹配
            for keyword in keywords:
                if keyword in item.title.lower() or keyword in ' '.join(item.tags).lower():
                    score += 2.0
            
            # 3. 关切点匹配
            key_concerns = conversation_summary.get('key_concerns', [])
            for concern in key_concerns:
                if concern in item.tags or concern in item.category:
                    score += 1.5
            
            # 4. 对话阶段匹配（难度适配）
            stage = conversation_summary.get('conversation_stage', 'initial')
            depth = self.stage_depth_mapping.get(stage, 'beginner')
            if isinstance(depth, list):
                if item.difficulty in depth:
                    score += 1.0
            elif item.difficulty == depth:
                score += 1.0
            
            # 5. 热度加权
            score += item.popularity * 0.01
            
            if score > 0:
                scored_items.append((score, item))
        
        # 按分数排序
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored_items[:limit]]
    
    def _ai_based_recommendation(self,
                                user_input: str,
                                current_emotion: str,
                                conversation_summary: Dict[str, Any],
                                limit: int) -> List[ContentItem]:
        """基于AI的智能推荐"""
        try:
            # 构建系统提示词
            system_prompt = """你是一个心理内容推荐专家。请根据用户的情况,从以下内容库中选择最合适的3个推荐。
            考虑因素：
            1. 用户的当前情绪状态
            2. 用户的表达内容
            3. 对话阶段和深度
            4. 内容的匹配度和实用性
            
            请返回内容ID列表,格式:["id1", "id2", "id3"]"""
            
            # 获取所有内容描述
            all_content = content_db.get_all_content()
            content_descriptions = []
            for item in all_content:
                desc = f"ID: {item.id} | 标题: {item.title} | 类型: {item.type} | 描述: {item.description} | 标签: {', '.join(item.tags)}"
                content_descriptions.append(desc)
            
            user_prompt = f"""用户输入: {user_input}
            当前情绪: {current_emotion}
            对话阶段: {conversation_summary.get('conversation_stage', 'initial')}
            关切点: {', '.join(conversation_summary.get('key_concerns', []))}
            
            可用内容:
            {'\n'.join(content_descriptions[:20])}  # 限制数量避免token过多
            
            请推荐最合适的3个内容ID:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # 解析响应
            response_text = response.choices[0].message.content.strip()
            logger.info(f"AI推荐响应: {response_text}")
            
            # 提取内容ID
            content_ids = []
            import re
            id_pattern = r'["\']([a-zA-Z0-9_]+)["\']'
            matches = re.findall(id_pattern, response_text)
            
            for content_id in matches[:limit]:
                content_item = content_db.get_content_by_id(content_id)
                if content_item:
                    content_ids.append(content_item)
            
            return content_ids
            
        except Exception as e:
            logger.error(f"AI推荐失败: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的中文关键词提取
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        
        # 心理相关关键词增强
        psych_keywords = [
            "压力", "焦虑", "抑郁", "情绪", "学习", "考试", "工作",
            "关系", "朋友", "家人", "未来", "迷茫", "自我", "自信",
            "睡眠", "饮食", "运动", "放松", "冥想", "正念"
        ]
        
        keywords = list(set(chinese_words))
        
        # 添加匹配的心理关键词
        for kw in psych_keywords:
            if kw in text and kw not in keywords:
                keywords.append(kw)
        
        return keywords
    
    def _generate_rationale(self,
                           recommended_items: List[ContentItem],
                           user_input: str,
                           current_emotion: str,
                           conversation_summary: Dict[str, Any]) -> str:
        """生成推荐理由"""
        if not recommended_items:
            return "暂时没有找到特别匹配的内容。"
        
        # 根据推荐内容类型生成理由
        content_types = [item.type for item in recommended_items]
        stage = conversation_summary.get('conversation_stage', 'initial')
        
        rationale_templates = {
            "initial": "根据你提到的内容，这些资源可能对你有帮助：",
            "exploring": "在探索阶段，这些内容可以帮助你更深入地理解自己：",
            "deepening": "这些专业资源可以帮助你进一步分析问题：",
            "resolving": "这些实用工具和策略可以帮助你采取行动："
        }
        
        base_rationale = rationale_templates.get(stage, "根据你的情况推荐以下内容：")
        
        # 添加具体理由
        specific_reasons = []
        for item in recommended_items[:2]:  # 只取前两个详细说明
            if current_emotion in item.emotion_tags:
                specific_reasons.append(f"《{item.title}》特别适合处理{current_emotion}状态")
            elif any(tag in item.tags for tag in conversation_summary.get('key_concerns', [])):
                specific_reasons.append(f"《{item.title}》与你关注的方面相关")
        
        if specific_reasons:
            return f"{base_rationale} {'；'.join(specific_reasons)}"
        
        return base_rationale
    
    def _calculate_match_scores(self,
                               recommended_items: List[ContentItem],
                               user_input: str,
                               current_emotion: str,
                               conversation_summary: Dict[str, Any]) -> Dict[str, float]:
        """计算匹配度分数"""
        scores = {}
        
        for item in recommended_items:
            item_score = 0.0
            
            # 情绪匹配度
            if current_emotion in item.emotion_tags:
                item_score += 0.4
            
            # 关切点匹配度
            key_concerns = conversation_summary.get('key_concerns', [])
            for concern in key_concerns:
                if concern in item.tags or concern in item.category:
                    item_score += 0.3
                    break
            
            # 对话阶段适配度
            stage = conversation_summary.get('conversation_stage', 'initial')
            depth = self.stage_depth_mapping.get(stage, 'beginner')
            if item.difficulty == depth or (isinstance(depth, list) and item.difficulty in depth):
                item_score += 0.2
            
            # 内容热度
            item_score += min(item.popularity * 0.01, 0.1)
            
            scores[item.id] = min(item_score, 1.0)
        
        return scores

# 全局推荐器实例
content_recommender = ContentRecommender()