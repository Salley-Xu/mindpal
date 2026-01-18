import logging
from typing import Dict, Optional
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """智能回应生成器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.API_BASE_URL
        )
        self.model = config.CHAT_MODEL
        
        # 不同阶段的回应策略
        self.strategy_prompts = {
            'initial': """你刚与用户开始对话。主要目标是建立信任、表达共情，并了解核心问题。
            回应重点：
            1. 温暖的共情和确认
            2. 开放式的探索问题
            3. 简要说明你能如何帮助对方
            避免：给过多建议、深入分析、过长回应""",
            
            'exploring': """你正在探索用户问题的阶段。主要目标是帮助用户理清思绪、识别模式。
            回应重点：
            1. 深度共情和理解
            2. 帮助用户看到情绪/思维模式的提问
            3. 适度的正常化（"很多人都会有类似感受"）
            可以：适当提供简单观察或反思
            避免：直接解决方案、过多工具建议""",
            
            'deepening': """你正在深入处理核心问题的阶段。用户已表达足够信息。
            回应重点：
            1. 基于已有信息的深度分析
            2. 帮助连接不同想法/感受
            3. 提供有洞察力的观察
            4. 可选：提供1个相关的心理工具
            可以：较长回应、深度分析、适度建议
            避免：跳跃到解决方案""",
            
            'resolving': """对话进入解决阶段。用户已充分表达，寻求具体帮助。
            回应重点：
            1. 总结关键洞察
            2. 提供1-2个具体、可行的工具/策略
            3. 鼓励小步行动
            4. 展望积极变化
            可以：具体建议、行动计划、工具推荐"""
        }
    
    def generate_with_strategy(self, user_input: str, 
                              current_emotion: str,
                              context_emotion: str,
                              conversation_summary: Dict,
                              history_text: str = "") -> str:
        """
        根据对话阶段和策略生成回应
        """
        # 确保conversation_summary不为None
        if conversation_summary is None:
            conversation_summary = {
                'conversation_stage': 'initial',
                'key_concerns': [],
                'turn_count': 0
            }
        
        stage = conversation_summary.get('conversation_stage', 'initial')
        strategy = self.strategy_prompts.get(stage, self.strategy_prompts['initial'])
        
        # 根据阶段调整参数
        temperature, max_tokens = self._adjust_parameters_by_stage(stage)
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt(
            stage=stage,
            strategy=strategy,
            user_input=user_input,
            current_emotion=current_emotion,
            context_emotion=context_emotion,
            conversation_summary=conversation_summary,
            history_text=history_text
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"回应生成成功，阶段: {stage}, 长度: {len(ai_response)}")
            return ai_response
            
        except Exception as e:
            logger.error(f"生成回应失败: {e}")
            return f"我理解你现在可能感到{current_emotion}。能多和我聊聊吗？"
    
    def _adjust_parameters_by_stage(self, stage: str) -> tuple:
        """根据对话阶段调整生成参数"""
        parameters = {
            'initial': (0.75, 400),
            'exploring': (0.75, 600),
            'deepening': (0.7, 800),
            'resolving': (0.65, 700)
        }
        return parameters.get(stage, (0.75, 600))
    
    def _build_system_prompt(self, stage: str, strategy: str, user_input: str,
                           current_emotion: str, context_emotion: str,
                           conversation_summary: Dict, history_text: str) -> str:
        """构建系统提示词"""
        return f"""# 角色与策略
你是一位专业的"大学生心理对话伙伴"。当前对话阶段：{stage}。
{strategy}

# 用户状态
当前表达：{user_input}
表层情绪：{current_emotion}
深层情绪：{context_emotion}
关键关切：{', '.join(conversation_summary.get('key_concerns', []))}

# 历史上下文（最近3轮）：
{history_text if history_text else '这是对话的开始，还没有历史记录。'}

# 回应要求
1. 保持自然对话流，不要用列表或标题
2. 根据阶段策略调整回应内容和长度
3. 深度优先于广度，质量优先于数量
4. 如果适用，可将心理知识自然融入对话中
5. 始终以用户为中心，而非展示专业知识

现在，请生成适合当前阶段的回应："""
    
response_generator = ResponseGenerator()