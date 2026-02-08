"""
SelfConfigSkill - 自我配置技能

职责：
- 改名字
"""
from typing import Dict, Any
from loguru import logger

from app.skills.base import BaseSkill, SkillRegistry


class SelfConfigSkill(BaseSkill):
    """自我配置技能"""

    name = "self_config"
    description = "自我配置：改名字等"
    tool_names = [
        "change_my_name",
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        if tool_name == "change_my_name":
            return await self._handle_change_name(message=message, user_id=user_id)
        return self._err(f"未知工具: {tool_name}")

    async def _handle_change_name(self, message: str, user_id: str) -> Dict[str, Any]:
        """老板要给我改名字"""
        extract_prompt = f"""从以下消息中提取用户想给AI助理取的新名字。
用户消息：{message}
只返回名字本身，不要任何其他内容。比如用户说"你以后名字就叫Maria"，你就返回"Maria"。"""

        try:
            new_name = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.1)
            new_name = new_name.strip().strip('"').strip("'").strip()

            if not new_name or len(new_name) > 20:
                return self._ok("你想让我叫什么名字呀？")

            from app.services.memory_service import memory_service
            await memory_service.remember(user_id, "bot_name", new_name, "communication")

            if self.agent:
                self.agent._bot_display_name = new_name

            logger.info(f"[SelfConfigSkill] 名字已更改为: {new_name}")

            return self._ok(f"好呀，以后我就叫{new_name}啦~ 你直接叫我{new_name}就行！")

        except Exception as e:
            logger.error(f"[SelfConfigSkill] 改名失败: {e}")
            return self._ok("改名的时候出了点小问题，你再说一遍要叫我什么？")


# 注册
SkillRegistry.register(SelfConfigSkill())
