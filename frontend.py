# frontend.py - 上下文感知对话版
import streamlit as st
import requests
import time
import uuid
from datetime import datetime

def display_recommendations(recommendations, rationale):
    """显示推荐内容"""
    if recommendations:
        # 创建一个漂亮的卡片式展示
        st.markdown("---")
        st.markdown("### 📚 为你推荐")
        
        # 显示推荐理由
        if rationale:
            st.info(f"💡 {rationale}")
        
        # 创建列来显示推荐内容
        cols = st.columns(min(3, len(recommendations)))
        
        for idx, item in enumerate(recommendations[:3]):  # 最多显示3个
            with cols[idx]:
                # 根据类型选择图标
                type_icons = {
                    "article": "📄",
                    "audio": "🎧",
                    "video": "🎬",
                    "exercise": "📝",
                    "tool": "🛠️"
                }
                icon = type_icons.get(item.get('type', 'article'), "📄")
                
                # 创建卡片容器
                with st.container():
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 10px;
                        padding: 15px;
                        margin-bottom: 10px;
                        background-color: #f9f9f9;
                        height: 280px;
                        overflow: hidden;
                    ">
                        <div style="color: #666; margin-bottom: 8px;">
                            {icon} {item.get('type', '内容').upper()}
                        </div>
                        <h4 style="margin-top: 0; color: #333;">
                            {item.get('title', '无标题')}
                        </h4>
                        <p style="color: #555; font-size: 0.9em; height: 80px; overflow: hidden;">
                            {item.get('description', '无描述')[:100]}...
                        </p>
                        <div style="margin-top: 10px;">
                            <small style="color: #888;">
                                {', '.join(item.get('tags', [])[:3])}
                            </small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 添加操作按钮
                    if item.get('url'):
                        st.markdown(f"""
                        <div style="text-align: center; margin-top: 5px;">
                            <a href="{item['url']}" target="_blank" style="
                                display: inline-block;
                                background-color: #4CAF50;
                                color: white;
                                padding: 6px 12px;
                                text-decoration: none;
                                border-radius: 5px;
                                font-size: 0.9em;
                            ">
                                查看详情
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("📝 内部资源")
        
        # 如果还有更多推荐，显示提示
        if len(recommendations) > 3:
            st.caption(f"还有 {len(recommendations) - 3} 个相关推荐...")

# 在显示推荐内容之前，先检查是否有紧急情况
def show_urgent_warning(urgent_issue):
    """显示紧急情况警告"""
    if urgent_issue and urgent_issue.get('level') == 'urgent':
        st.error("""
        🚨 **紧急情况检测**
        
        检测到可能需要立即关注的内容。请记住：
        - 你并不孤单，很多人愿意帮助你
        - 寻求帮助是勇敢的表现
        - 专业支持随时可用
        """)
        return True
    elif urgent_issue and urgent_issue.get('level') in ['warning_high', 'warning']:
        st.warning("""
        ⚠️ **风险提示**
        
        检测到可能需要关注的内容。
        如果你感到困扰，请考虑联系专业支持。
        """)
        return True
    return False

# ------------------ 页面配置 ------------------
st.set_page_config(
    page_title="心灵伙伴 Pro",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 心灵伙伴 Pro")
st.caption("上下文感知的心理对话伙伴")

# ------------------ 会话状态初始化 ------------------
# 初始化核心状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_base" not in st.session_state:
    st.session_state.api_base = "http://localhost:8000"
if "session_id" not in st.session_state:
    # 生成唯一的会话ID
    st.session_state.session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
if "user_id" not in st.session_state:
    # 生成用户ID（实际应用中应来自登录系统）
    st.session_state.user_id = f"user_{hash(str(time.time())) % 10000}"
if "conversation_summary" not in st.session_state:
    st.session_state.conversation_summary = {}
if "latest_recommendations" not in st.session_state:  # 新增：推荐内容
    st.session_state.latest_recommendations = []
if "recommendation_rationale" not in st.session_state:  # 新增：推荐理由
    st.session_state.recommendation_rationale = ""

# ------------------ 侧边栏配置 ------------------
with st.sidebar:
    st.header("⚙️ 配置")
    api_base = st.text_input("后端API地址", value=st.session_state.api_base)
    if api_base != st.session_state.api_base:
        st.session_state.api_base = api_base
        st.rerun()
    
    st.divider()
    st.header("📊 系统状态")
    
    # 更健壮的后端连接测试
    try:
        # 尝试多个可能的健康检查端点
        test_endpoints = ["/", "/health", "/docs"]
        connected = False
        health_data = {}
        
        for endpoint in test_endpoints:
            try:
                resp = requests.get(f"{st.session_state.api_base}{endpoint}", timeout=3)
                if resp.status_code == 200:
                    connected = True
                    if endpoint == "/health":
                        try:
                            health_data = resp.json()
                        except:
                            pass
                    break
            except:
                continue
        
        if connected:
            st.success("✅ 后端连接正常")
            # 显示后端信息
            if health_data:
                model = health_data.get('model') or health_data.get('chat_model')
                session_count = health_data.get('session_count')
                
                if model:
                    st.info(f"对话模型: {model}")
                if session_count is not None:
                    st.info(f"活跃会话: {session_count}")
        else:
            st.error("❌ 无法连接到后端")
            st.info("请确保已运行后端服务 (python backend.py)")
            
    except Exception as e:
        st.error(f"连接检查出错: {str(e)}")
    
    st.divider()
    st.header("💬 对话状态")
    
    # 显示当前对话状态
    if st.session_state.conversation_summary:
        summary = st.session_state.conversation_summary
        
        # 对话阶段
        stage_map = {
            'initial': '🟢 建立连接',
            'exploring': '🔵 探索问题',
            'deepening': '🟣 深入分析',
            'resolving': '🟠 寻找方案'
        }
        stage = stage_map.get(summary.get('conversation_stage'), '探索中')
        st.caption(f"对话阶段: {stage}")
        
        # 情绪趋势
        trend_map = {
            'stable': '→ 稳定',
            'escalating': '↑ 上升',
            'improving': '↓ 改善',
            'calming': '↘ 平复',
            'consistent': '→ 持续',
            'new': '🆕 新对话'
        }
        trend = trend_map.get(summary.get('emotion_trend'), '稳定')
        st.caption(f"情绪趋势: {trend}")
        
        # 关键关切
        concerns = summary.get('key_concerns', [])
        if concerns:
            concern_map = {
                'relationship': '人际关系',
                'academic': '学业压力',
                'future': '未来规划',
                'self': '自我探索'
            }
            display_concerns = [concern_map.get(c, c) for c in concerns[:3]]
            st.caption(f"关注点: {', '.join(display_concerns)}")
        
        # 对话轮次
        turn_count = summary.get('turn_count', 0)
        if turn_count > 0:
            st.caption(f"对话轮次: {turn_count}")
    
    st.divider()
    
    # 会话管理按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新状态", use_container_width=True):
            # 刷新会话摘要
            try:
                summary_url = f"{st.session_state.api_base}/session/{st.session_state.user_id}/{st.session_state.session_id}/summary"
                summary_resp = requests.get(summary_url, timeout=5)
                if summary_resp.status_code == 200:
                    st.session_state.conversation_summary = summary_resp.json().get('summary', {})
            except:
                pass
            st.rerun()
    
    with col2:
        if st.button("🗑️ 新会话", use_container_width=True):
            # 清除当前会话并创建新会话
            st.session_state.chat_history = []
            st.session_state.session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            st.session_state.conversation_summary = {}
            
            # 通知后端清除旧会话
            try:
                clear_url = f"{st.session_state.api_base}/session/{st.session_state.user_id}/{st.session_state.session_id}"
                requests.delete(clear_url, timeout=3)
            except:
                pass
                
            st.rerun()
    
    st.divider()
    st.header("📚 推荐内容")
    
    if st.session_state.latest_recommendations:
        st.success(f"🎯 有 {len(st.session_state.latest_recommendations)} 个推荐")
        if st.session_state.recommendation_rationale:
            st.caption(st.session_state.recommendation_rationale[:50] + "...")
        
        # 快速查看按钮
        if st.button("👁️ 查看推荐", use_container_width=True):
            # 展开显示推荐内容
            for item in st.session_state.latest_recommendations[:2]:  # 只显示前2个
                with st.expander(f"{item.get('title', '无标题')}", expanded=False):
                    st.write(item.get('description', '无描述'))
                    if item.get('tags'):
                        st.caption(f"标签: {', '.join(item.get('tags', []))}")
    else:
        st.caption("暂无推荐内容")
    
    # 手动刷新推荐按钮
    if st.button("🔄 刷新推荐", use_container_width=True, help="基于当前对话生成新推荐"):
        if st.session_state.chat_history:
            # 使用最近的用户消息来生成推荐
            recent_user_messages = [m for m in st.session_state.chat_history if m["role"] == "user"]
            if recent_user_messages:
                latest_user_message = recent_user_messages[-1]["content"]
                
                # 调用推荐API
                try:
                    recommend_url = f"{st.session_state.api_base}/content/recommend"
                    recommend_data = {
                        "user_input": latest_user_message,
                        "current_emotion": st.session_state.conversation_summary.get("current_emotion", "中性"),
                        "conversation_stage": st.session_state.conversation_summary.get("conversation_stage", "initial"),
                        "key_concerns": ",".join(st.session_state.conversation_summary.get("key_concerns", [])),
                        "limit": 3
                    }
                    
                    resp = requests.post(recommend_url, json=recommend_data, timeout=10)
                    if resp.status_code == 200:
                        result = resp.json()
                        st.session_state.latest_recommendations = result.get("recommendations", [])
                        st.session_state.recommendation_rationale = result.get("rationale", "")
                        st.success("推荐已刷新！")
                        st.rerun()
                except Exception as e:
                    st.error(f"刷新失败: {e}")

# ------------------ 主聊天界面 ------------------
# 显示对话历史
for idx, chat in enumerate(st.session_state.chat_history):
    if chat["role"] == "user":
        with st.chat_message("user"):
            st.markdown(chat["content"])
            # 显示情绪标签（如果有）
            if "current_emotion" in chat:
                emotion = chat["current_emotion"]
                # 情绪图标映射
                emotion_icons = {
                    "焦虑": "😰", "压力": "😫", "抑郁": "😔", "愤怒": "😠",
                    "学业压力": "📚", "人际矛盾": "👥", "困惑": "🤔",
                    "不确定": "❓", "中性": "😐", "平静": "😌", "快乐": "😊",
                    "放松": "😎", "自我怀疑": "🤨", "未来迷茫": "🌀"
                }
                icon = emotion_icons.get(emotion, "💭")
                st.caption(f"{icon} {emotion}")
    else:
        with st.chat_message("assistant"):
            st.markdown(chat["content"])
            
            # 显示对话阶段提示（如果是第一轮或阶段变化）
            if idx == 0 or (idx > 0 and idx % 5 == 0):
                if st.session_state.conversation_summary:
                    stage = st.session_state.conversation_summary.get('conversation_stage')
                    stage_messages = {
                        'exploring': "💡 我正在探索你的问题...",
                        'deepening': "🔍 我正在深入分析...",
                        'resolving': "✨ 我正在思考可能的解决方案..."
                    }
                    if stage in stage_messages:
                        st.caption(stage_messages[stage])
    
    # 如果这是最新的AI消息且有推荐内容，在消息后显示推荐
    if (chat["role"] == "assistant" and 
        idx == len(st.session_state.chat_history) - 1 and
        st.session_state.latest_recommendations):
        
        # 不在chat_message中显示，而是独立显示
        display_recommendations(
            st.session_state.latest_recommendations,
            st.session_state.recommendation_rationale
        )

# 用户输入区域
user_input = st.chat_input("请描述你的心情或困扰...")

if user_input:
    # 1. 显示用户消息（先显示，再处理）
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 立即添加到历史记录（临时，等待API响应后会更新）
    temp_message_id = len(st.session_state.chat_history)
    st.session_state.chat_history.append({
        "role": "user", 
        "content": user_input,
        "time": datetime.now().strftime("%H:%M")
    })
    
    # 2. 调用智能对话API（整合了情绪分析和对话生成）
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 使用新的智能对话API
                chat_url = f"{st.session_state.api_base}/chat/intelligent"
                chat_data = {
                    "text": user_input,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id
                }
                
                chat_resp = requests.post(chat_url, json=chat_data, timeout=30)
                
                if chat_resp.status_code == 200:
                    chat_result = chat_resp.json()
                    ai_response = chat_result["response"]
                    
                    # 获取情绪摘要信息
                    emotion_summary = chat_result.get("emotion_summary", {})
                    
                    # 获取推荐内容
                    recommendations = chat_result.get("recommendations", [])
                    recommendation_rationale = chat_result.get("recommendation_rationale", "")
                    
                    # 显示AI回复
                    st.markdown(ai_response)
                    
                    # 更新用户消息的情绪信息
                    if emotion_summary:
                        st.session_state.chat_history[temp_message_id]["current_emotion"] = emotion_summary.get("current_emotion", "未知")
                        st.session_state.chat_history[temp_message_id]["context_emotion"] = emotion_summary.get("context_emotion", "未知")
                    
                    # 保存推荐内容
                    st.session_state.latest_recommendations = recommendations
                    st.session_state.recommendation_rationale = recommendation_rationale
                    
                    # 保存AI回复到历史
                    ai_message_data = {
                        "role": "assistant",
                        "content": ai_response,
                        "time": datetime.now().strftime("%H:%M")
                    }
                    
                    # 如果有紧急情况，标记
                    urgent_issue = chat_result.get("urgent_issue")
                    if urgent_issue and urgent_issue.get("level") in ["urgent", "warning_high"]:
                        ai_message_data["urgent"] = True
                    
                    st.session_state.chat_history.append(ai_message_data)
                    
                    # 更新对话摘要
                    st.session_state.conversation_summary = emotion_summary
                    
                    # 如果有推荐内容，立即显示
                    if recommendations:
                        # 这里不直接调用display_recommendations，而是在渲染对话历史时显示
                        pass
                    
                else:
                    error_msg = f"对话生成失败 (状态码: {chat_resp.status_code})"
                    st.error(error_msg)
                    
                    # 添加错误回复到历史
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "抱歉，我暂时无法回应。请检查后端服务。",
                        "time": datetime.now().strftime("%H:%M")
                    })
                    
            except requests.exceptions.Timeout:
                st.error("对话请求超时，请稍后重试")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "响应时间较长，请稍等片刻或重试。",
                    "time": datetime.now().strftime("%H:%M")
                })
            except Exception as e:
                st.error(f"对话生成异常: {str(e)}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "系统遇到了一些问题，请稍后再试。",
                    "time": datetime.now().strftime("%H:%M")
                })
    
    # 强制重新运行以更新UI
    st.rerun()
# ------------------ 对话信息栏（底部） ------------------
st.divider()

if st.session_state.chat_history:
    # 显示简要统计
    user_msgs = len([m for m in st.session_state.chat_history if m["role"] == "user"])
    assistant_msgs = len([m for m in st.session_state.chat_history if m["role"] == "assistant"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"💬 对话: {user_msgs+assistant_msgs} 轮")
    with col2:
        st.caption(f"👤 用户: {user_msgs} 条")
    with col3:
        st.caption(f"🤖 助手: {assistant_msgs} 条")
    
    # 显示当前会话信息
    st.caption(f"会话ID: {st.session_state.session_id[:12]}...")

# ------------------ 页脚说明 ------------------
st.divider()
with st.expander("ℹ️ 关于此系统", expanded=False):
    st.markdown("""
    **心灵伙伴 Pro - 上下文感知心理对话系统**
    
    ### ✨ 核心功能
    1. **上下文感知**：系统理解整个对话历史，而非单条消息
    2. **情绪演变跟踪**：分析情绪变化趋势和模式
    3. **智能回应策略**：根据对话阶段调整回应方式
    4. **专业对话流程**：从建立信任到深入分析的自然过渡
    
    ### 🔄 对话阶段
    - **建立连接** (初期): 共情、了解基本情况
    - **探索问题** (中期): 帮助理清思绪、识别模式
    - **深入分析** (后期): 提供洞察、连接想法
    - **寻找方案** (解决期): 具体建议、行动计划
    
    ### ⚠️ 重要说明
    1. 本系统为原型验证，不替代专业心理咨询
    2. 所有对话数据仅用于改善对话体验
    3. 如遇危机情况，请立即联系专业机构
    
    **技术栈**: FastAPI + DeepSeek API + Streamlit
    **版本**: Pro v3.0 (上下文感知版)
    """)

# ------------------ 自动刷新对话状态 ------------------
# 每60秒自动刷新一次对话状态（如果对话活跃）
if st.session_state.chat_history and len(st.session_state.chat_history) > 0:
    last_message_time = st.session_state.chat_history[-1].get("time", "00:00")
    current_time = datetime.now().strftime("%H:%M")
    
    # 简单的时间差计算（实际应用中应更精确）
    if st.session_state.get("last_refresh") != current_time:
        try:
            # 每5分钟刷新一次状态
            if int(current_time.split(":")[1]) % 5 == 0:
                summary_url = f"{st.session_state.api_base}/session/{st.session_state.user_id}/{st.session_state.session_id}/summary"
                summary_resp = requests.get(summary_url, timeout=3)
                if summary_resp.status_code == 200:
                    st.session_state.conversation_summary = summary_resp.json().get('summary', {})
        except:
            pass
        
        st.session_state["last_refresh"] = current_time