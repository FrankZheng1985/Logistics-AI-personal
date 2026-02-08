"""
Maria Skill System - 模块化技能架构

每个Skill是一个独立的能力模块，负责一个特定领域的业务逻辑。
ClauwdbotAgent（编排层）只负责 ReAct 循环和上下文管理，
具体的"干活"逻辑全部委托给 Skill。

Skill 通过 SkillRegistry 注册，MariaToolExecutor 通过 registry 查找并调用。
"""
from app.skills.base import BaseSkill, SkillRegistry

__all__ = ["BaseSkill", "SkillRegistry"]
