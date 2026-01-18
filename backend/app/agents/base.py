"""
AI员工基类
所有AI员工都继承自这个基类
集成物流专业老人级别知识库
支持实时工作直播功能
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from loguru import logger
import json

from app.core.llm import chat_completion
from app.models.conversation import AgentType
from app.core.prompts.logistics_expert import LOGISTICS_EXPERT_BASE_PROMPT


class BaseAgent(ABC):
    """AI员工基类
    
    所有AI员工都具备专业物流老人级别的知识水平
    支持实时工作步骤记录和直播功能
    """
    
    # 子类必须定义这些属性
    name: str = "未命名"
    agent_type: AgentType = None
    description: str = ""
    
    # 是否启用专业物流知识
    enable_logistics_expertise: bool = True
    
    # 是否启用实时工作直播
    enable_live_broadcast: bool = True
    
    def __init__(self):
        self.system_prompt = self._build_full_system_prompt()
        # 当前任务会话ID
        self._current_session_id: Optional[UUID] = None
        self._session_start_time: Optional[datetime] = None
        logger.info(f"🤖 {self.name} 初始化完成 (物流专家模式: {'开启' if self.enable_logistics_expertise else '关闭'}, 实时直播: {'开启' if self.enable_live_broadcast else '关闭'})")
    
    def _build_full_system_prompt(self) -> str:
        """构建完整的系统提示词，包含专业知识"""
        base_prompt = self._build_system_prompt()
        
        if self.enable_logistics_expertise:
            # 集成物流专业知识
            expertise_intro = """

## 专业背景
你具备15年国际物流从业经验的专业水准：
- 熟悉海运、空运、铁路、快递等全物流链条
- 精通各国清关政策和流程
- 了解危险品、敏感品处理规范
- 掌握报价策略和成本控制技巧
- 深谙客户痛点和解决方案

在回答问题和处理任务时，请运用你的专业知识，给出专业、可靠的建议。
"""
            return base_prompt + expertise_intro
        
        return base_prompt
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """构建系统提示词，子类必须实现"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务，子类必须实现"""
        pass
    
    # ==================== 实时工作直播功能 ====================
    
    async def start_task_session(self, task_type: str, task_description: str = None) -> UUID:
        """开始一个新的任务会话
        
        Args:
            task_type: 任务类型
            task_description: 任务描述
            
        Returns:
            会话ID
        """
        self._current_session_id = uuid4()
        self._session_start_time = datetime.now()
        
        if self.enable_live_broadcast:
            try:
                from app.models.database import AsyncSessionLocal
                from sqlalchemy import text
                
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        text("""
                            INSERT INTO agent_task_sessions 
                            (id, agent_type, agent_name, task_type, task_description, status, started_at)
                            VALUES (:id, :agent_type, :agent_name, :task_type, :task_description, 'running', NOW())
                        """),
                        {
                            "id": self._current_session_id,
                            "agent_type": self.agent_type.value if self.agent_type else "unknown",
                            "agent_name": self.name,
                            "task_type": task_type,
                            "task_description": task_description
                        }
                    )
                    await db.commit()
                
                # 发送任务开始通知
                await self.log_live_step(
                    "start", 
                    f"开始任务: {task_type}",
                    task_description,
                    {"task_type": task_type}
                )
                
            except Exception as e:
                logger.error(f"[{self.name}] 创建任务会话失败: {e}")
        
        return self._current_session_id
    
    async def end_task_session(self, result_summary: str = None, error_message: str = None):
        """结束当前任务会话
        
        Args:
            result_summary: 结果摘要
            error_message: 错误信息（如果失败）
        """
        if not self._current_session_id:
            return
        
        status = "failed" if error_message else "completed"
        duration_ms = None
        if self._session_start_time:
            duration_ms = int((datetime.now() - self._session_start_time).total_seconds() * 1000)
        
        if self.enable_live_broadcast:
            try:
                from app.models.database import AsyncSessionLocal
                from sqlalchemy import text
                
                async with AsyncSessionLocal() as db:
                    # 更新任务会话状态
                    await db.execute(
                        text("""
                            UPDATE agent_task_sessions 
                            SET status = :status,
                                completed_at = NOW(),
                                duration_ms = :duration_ms,
                                result_summary = :result_summary,
                                error_message = :error_message
                            WHERE id = :id
                        """),
                        {
                            "id": self._current_session_id,
                            "status": status,
                            "duration_ms": duration_ms,
                            "result_summary": result_summary,
                            "error_message": error_message
                        }
                    )
                    
                    # 更新AI员工任务统计（仅在任务成功完成时）
                    if status == "completed" and self.agent_type:
                        await db.execute(
                            text("""
                                UPDATE ai_agents 
                                SET tasks_completed_today = tasks_completed_today + 1,
                                    total_tasks_completed = total_tasks_completed + 1,
                                    last_active_at = NOW()
                                WHERE agent_type = :agent_type
                            """),
                            {"agent_type": self.agent_type.value}
                        )
                    
                    await db.commit()
                
                # 发送任务结束通知
                step_type = "error" if error_message else "complete"
                step_title = f"任务{'失败' if error_message else '完成'}"
                step_content = error_message if error_message else result_summary
                
                await self.log_live_step(
                    step_type,
                    step_title,
                    step_content,
                    {"duration_ms": duration_ms, "status": status}
                )
                
            except Exception as e:
                logger.error(f"[{self.name}] 结束任务会话失败: {e}")
        
        self._current_session_id = None
        self._session_start_time = None
    
    async def log_live_step(
        self, 
        step_type: str, 
        title: str, 
        content: str = None, 
        data: dict = None,
        status: str = "completed"
    ):
        """记录实时工作步骤并通过WebSocket推送
        
        Args:
            step_type: 步骤类型 (search/fetch/think/write/result/error/start/complete)
            title: 步骤标题
            content: 步骤详细内容
            data: 结构化数据
            status: 步骤状态 (running/completed/failed)
        """
        if not self.enable_live_broadcast:
            return
        
        step = {
            "id": str(uuid4()),
            "agent_type": self.agent_type.value if self.agent_type else "unknown",
            "agent_name": self.name,
            "session_id": str(self._current_session_id) if self._current_session_id else None,
            "step_type": step_type,
            "step_title": title,
            "step_content": content,
            "step_data": data,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            # 1. 存入数据库
            from app.models.database import AsyncSessionLocal
            from sqlalchemy import text
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO agent_live_steps 
                        (id, agent_type, agent_name, session_id, step_type, 
                         step_title, step_content, step_data, status, created_at)
                        VALUES 
                        (:id, :agent_type, :agent_name, :session_id, :step_type,
                         :step_title, :step_content, :step_data, :status, NOW())
                    """),
                    {
                        "id": step["id"],
                        "agent_type": step["agent_type"],
                        "agent_name": step["agent_name"],
                        "session_id": self._current_session_id,
                        "step_type": step_type,
                        "step_title": title,
                        "step_content": content,
                        "step_data": json.dumps(data, ensure_ascii=False) if data else None,
                        "status": status
                    }
                )
                await db.commit()
            
            # 2. 通过WebSocket广播
            from app.services.websocket_manager import websocket_manager
            await websocket_manager.broadcast_step(step)
            
            # 3. 同时记录到日志
            self.log(f"[{step_type}] {title}")
            
        except Exception as e:
            logger.error(f"[{self.name}] 记录实时步骤失败: {e}")
    
    # ==================== 便捷的步骤记录方法 ====================
    
    async def log_search(self, keyword: str, platform: str = None, extra_data: dict = None):
        """记录搜索步骤"""
        content = f"平台: {platform}" if platform else None
        data = {"keyword": keyword, "platform": platform}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("search", f"正在搜索: {keyword}", content, data)
    
    async def log_fetch(self, url: str, title: str = None, extra_data: dict = None):
        """记录访问网页步骤"""
        data = {"url": url, "title": title}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("fetch", "正在访问网页", url[:100] if url else None, data)
    
    async def log_think(self, thinking: str, context: str = None, extra_data: dict = None):
        """记录AI思考步骤"""
        data = {"thinking": thinking[:200] if thinking else None}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("think", "AI正在分析...", context, data, status="running")
    
    async def log_think_complete(self, result: str, extra_data: dict = None):
        """记录AI思考完成"""
        data = {"result_preview": result[:200] if result else None}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("think", "分析完成", result[:100] if result else None, data)
    
    async def log_write(self, content_type: str, preview: str = None, extra_data: dict = None):
        """记录写作步骤"""
        data = {"content_type": content_type}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("write", f"正在撰写: {content_type}", preview, data, status="running")
    
    async def log_write_complete(self, content_type: str, preview: str = None, extra_data: dict = None):
        """记录写作完成"""
        data = {"content_type": content_type}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("write", f"完成撰写: {content_type}", preview, data)
    
    async def log_result(self, title: str, content: str = None, extra_data: dict = None):
        """记录结果步骤"""
        await self.log_live_step("result", title, content, extra_data)
    
    async def log_error(self, error: str, context: str = None, extra_data: dict = None):
        """记录错误步骤"""
        data = {"error": str(error)}
        if extra_data:
            data.update(extra_data)
        await self.log_live_step("error", "发生错误", str(error), data, status="failed")
    
    # ==================== 原有功能 ====================
    
    async def think(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        调用LLM进行思考
        
        Args:
            messages: 对话消息列表
            temperature: 创造性参数
        
        Returns:
            AI回复内容
        """
        try:
            response = await chat_completion(
                messages=messages,
                system_prompt=self.system_prompt,
                temperature=temperature
            )
            return response
        except Exception as e:
            logger.error(f"{self.name} 思考出错: {e}")
            raise
    
    async def think_and_stream(
        self,
        messages: List[Dict[str, str]],
        title: str = "正在生成内容",
        temperature: float = 0.7,
        chunk_size: int = 2,
        delay: float = 0.015
    ) -> str:
        """
        调用LLM进行思考，并将结果以打字机效果流式传输到前端
        
        Args:
            messages: 对话消息列表
            title: 显示的标题
            temperature: 创造性参数
            chunk_size: 每次发送的字符数
            delay: 每次发送之间的延迟（秒）
        
        Returns:
            AI回复内容
        """
        try:
            # 1. 先调用LLM获取完整回复
            response = await chat_completion(
                messages=messages,
                system_prompt=self.system_prompt,
                temperature=temperature
            )
            
            # 2. 如果启用了直播，流式传输内容
            if self.enable_live_broadcast and self._current_session_id:
                from app.services.websocket_manager import websocket_manager
                await websocket_manager.stream_content(
                    agent_type=self.agent_type.value if self.agent_type else "unknown",
                    session_id=str(self._current_session_id),
                    content=response,
                    title=title,
                    chunk_size=chunk_size,
                    delay=delay
                )
            
            return response
        except Exception as e:
            logger.error(f"{self.name} 思考出错: {e}")
            raise
    
    async def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """
        简单的单轮对话
        
        Args:
            user_message: 用户消息
            context: 额外上下文
        
        Returns:
            AI回复
        """
        messages = []
        
        if context:
            messages.append({"role": "user", "content": f"背景信息：{context}"})
            messages.append({"role": "assistant", "content": "好的，我已了解背景信息。"})
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.think(messages)
    
    def log(self, message: str, level: str = "info"):
        """记录日志"""
        log_message = f"[{self.name}] {message}"
        getattr(logger, level)(log_message)


class AgentRegistry:
    """AI员工注册表"""
    
    _agents: Dict[AgentType, BaseAgent] = {}
    
    @classmethod
    def register(cls, agent: BaseAgent):
        """注册AI员工"""
        cls._agents[agent.agent_type] = agent
        logger.info(f"✓ {agent.name} 已注册")
    
    @classmethod
    def get(cls, agent_type: AgentType) -> Optional[BaseAgent]:
        """获取AI员工"""
        return cls._agents.get(agent_type)
    
    @classmethod
    def get_all(cls) -> Dict[AgentType, BaseAgent]:
        """获取所有AI员工"""
        return cls._agents.copy()
