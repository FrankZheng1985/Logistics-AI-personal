"""
Maria 直接执行技能模块（混合方案核心）

让 Maria 直接调用其他 AI 员工的核心能力，不经过任务派发流程。
实现更快的响应速度和更流畅的对话体验。

支持的直接能力：
1. search_leads - 直接搜索线索（小猎能力）
2. discover_topics - 发现热门话题（小猎能力）
3. write_copy - 撰写文案（小文能力）
4. create_video - 生成视频（小影能力）
5. analyze_customer - 客户分析（小析能力）
6. generate_followup - 生成跟进内容（小跟能力）
7. send_followup_email - 发送跟进邮件
8. lead_to_video_workflow - 一键工作流
9. generate_website - 生成网站代码（小码能力）
10. deploy_website - 部署网站（小码能力）
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime
import json

from app.skills.base import BaseSkill, skill_registry


@skill_registry.register
class MariaDirectSkill(BaseSkill):
    """Maria 直接执行技能 - 绕过任务派发，直接调用核心能力"""
    
    name = "maria_direct"
    description = "Maria直接执行能力，不经过任务派发"
    
    # 这个技能处理的工具列表
    handled_tools = [
        "search_leads",
        "discover_topics", 
        "write_copy",
        "create_video",
        "analyze_customer",
        "generate_followup",
        "send_followup_email",
        "lead_to_video_workflow",
        "generate_website",
        "deploy_website",
        "save_project_file",
    ]
    
    async def handle(
        self,
        tool_name: str,
        args: Dict[str, Any],
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """路由到对应的直接执行方法"""
        logger.info(f"[Maria直接执行] 工具: {tool_name}, 参数: {args}")
        
        handlers = {
            "search_leads": self._search_leads,
            "discover_topics": self._discover_topics,
            "write_copy": self._write_copy,
            "create_video": self._create_video,
            "analyze_customer": self._analyze_customer,
            "generate_followup": self._generate_followup,
            "send_followup_email": self._send_followup_email,
            "lead_to_video_workflow": self._lead_to_video_workflow,
            "generate_website": self._generate_website,
            "deploy_website": self._deploy_website,
            "save_project_file": self._save_project_file,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            return await handler(args, user_id)
        
        return {"status": "error", "message": f"未知的直接执行工具: {tool_name}"}
    
    # ========== 1. 线索搜索（小猎能力）==========
    
    async def _search_leads(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接搜索线索，不经过任务派发"""
        try:
            from app.agents.lead_hunter import lead_hunter_agent
            
            keywords = args.get("keywords", [])
            platforms = args.get("platforms", [])
            max_results = args.get("max_results", 10)
            
            logger.info(f"[Maria直接执行] 搜索线索: keywords={keywords}, max_results={max_results}")
            
            # 直接调用小猎的智能搜索
            input_data = {
                "action": "smart_hunt",
                "max_keywords": len(keywords) if keywords else 3,
                "max_results": max_results
            }
            
            if keywords:
                input_data["keywords"] = keywords
            
            result = await lead_hunter_agent.process(input_data)
            
            # 格式化返回结果
            leads_found = result.get("leads_found", [])
            high_intent = result.get("high_intent_leads", 0)
            
            return {
                "status": "success",
                "message": f"搜索完成！发现 {len(leads_found)} 条线索，其中 {high_intent} 条高意向",
                "total_leads": len(leads_found),
                "high_intent_leads": high_intent,
                "leads": leads_found[:max_results],  # 限制返回数量
                "keywords_used": result.get("keywords_used", []),
                "sources_searched": result.get("sources_searched", []),
                "execution_time": result.get("stats", {}).get("duration_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 搜索线索失败: {e}")
            return {"status": "error", "message": f"搜索线索时出错: {str(e)}"}
    
    async def _discover_topics(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接发现热门话题"""
        try:
            from app.agents.lead_hunter import lead_hunter_agent
            
            max_topics = args.get("max_topics", 5)
            
            logger.info(f"[Maria直接执行] 发现热门话题: max_topics={max_topics}")
            
            result = await lead_hunter_agent.process({
                "action": "discover_topics",
                "max_keywords": 5,
                "max_results": max_topics * 2  # 多搜一些再筛选
            })
            
            topics = result.get("topics_found", [])[:max_topics]
            high_value = result.get("high_value_topics", 0)
            
            return {
                "status": "success",
                "message": f"发现 {len(topics)} 个热门话题，其中 {high_value} 个高价值",
                "total_topics": len(topics),
                "high_value_topics": high_value,
                "topics": topics,
                "platforms_searched": result.get("platforms_searched", [])
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 发现话题失败: {e}")
            return {"status": "error", "message": f"发现话题时出错: {str(e)}"}
    
    # ========== 2. 文案创作（小文能力）==========
    
    async def _write_copy(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接撰写文案"""
        try:
            from app.agents.copywriter import copywriter_agent
            
            copy_type = args.get("copy_type", "general")
            topic = args.get("topic", "物流服务")
            target_audience = args.get("target_audience", "有物流需求的企业客户")
            duration = args.get("duration", 60)
            language = args.get("language", "zh-CN")
            
            logger.info(f"[Maria直接执行] 撰写文案: type={copy_type}, topic={topic}")
            
            # 映射copy_type到小文的task_type
            task_type_map = {
                "script": "script",
                "long_script": "long_script",
                "moments": "moments",
                "ad": "ad",
                "email": "email",
                "general": "general"
            }
            
            input_data = {
                "task_type": task_type_map.get(copy_type, "general"),
                "title": topic,
                "topic": topic,
                "target_audience": target_audience,
                "duration": duration,
                "language": language
            }
            
            result = await copywriter_agent.process(input_data)
            
            # 提取文案内容
            copy_content = (
                result.get("script") or 
                result.get("copy") or 
                result.get("content") or 
                result.get("sequence") or
                ""
            )
            
            return {
                "status": "success",
                "message": f"文案创作完成！类型: {copy_type}",
                "copy_type": copy_type,
                "topic": topic,
                "content": copy_content,
                "keywords": result.get("keywords", []),
                "segments": result.get("segments", [])
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 撰写文案失败: {e}")
            return {"status": "error", "message": f"撰写文案时出错: {str(e)}"}
    
    # ========== 3. 视频生成（小影能力）==========
    
    async def _create_video(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接生成视频"""
        try:
            from app.agents.video_creator import video_creator_agent
            from app.agents.copywriter import copywriter_agent
            
            title = args.get("title", "物流服务视频")
            script = args.get("script", "")
            mode = args.get("mode", "quick")  # 默认快速模式
            duration = args.get("duration", 60 if mode == "quick" else 120)
            language = args.get("language", "zh-CN")
            
            logger.info(f"[Maria直接执行] 生成视频: title={title}, mode={mode}")
            
            # 如果没有脚本，先生成脚本
            if not script:
                logger.info("[Maria直接执行] 无脚本，先调用小文生成脚本")
                script_result = await copywriter_agent.process({
                    "task_type": "script" if mode == "quick" else "long_script",
                    "title": title,
                    "duration": duration
                })
                script = script_result.get("script", "")
                keywords = script_result.get("keywords", [])
            else:
                keywords = []
            
            # 生成视频
            video_result = await video_creator_agent.process({
                "title": title,
                "script": script,
                "keywords": keywords,
                "mode": mode,
                "duration": duration,
                "language": language
            })
            
            return {
                "status": video_result.get("status", "processing"),
                "message": video_result.get("message", "视频生成中"),
                "title": title,
                "mode": mode,
                "video_url": video_result.get("video_url"),
                "task_id": video_result.get("task_id"),
                "script_used": script[:200] + "..." if len(script) > 200 else script
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 生成视频失败: {e}")
            return {"status": "error", "message": f"生成视频时出错: {str(e)}"}
    
    # ========== 4. 客户分析（小析能力）==========
    
    async def _analyze_customer(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接分析客户意向"""
        try:
            from app.agents.analyst import analyst_agent
            
            customer_id = args.get("customer_id")
            conversation = args.get("conversation", "")
            customer_info = args.get("customer_info", {})
            
            logger.info(f"[Maria直接执行] 分析客户: customer_id={customer_id}")
            
            # 调用小析的分析能力
            result = await analyst_agent.process({
                "action": "analyze_intent",
                "customer_id": customer_id,
                "conversation": conversation,
                "customer_info": customer_info
            })
            
            return {
                "status": "success",
                "message": "客户分析完成",
                "customer_id": customer_id,
                "intent_score": result.get("intent_score", 0),
                "intent_level": result.get("intent_level", "unknown"),
                "signals": result.get("intent_signals", []),
                "profile": result.get("customer_profile", {}),
                "followup_suggestion": result.get("followup_suggestion", ""),
                "next_action": result.get("recommended_action", "")
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 客户分析失败: {e}")
            # 如果小析不可用，Maria自己做简单分析
            return await self._fallback_analyze_customer(args, user_id)
    
    async def _fallback_analyze_customer(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """备用客户分析（Maria自己执行）"""
        conversation = args.get("conversation", "")
        
        # 高意向信号关键词
        high_intent_keywords = [
            "报价", "价格", "费用", "多少钱", "怎么收费",
            "时效", "几天到", "多久",
            "发货", "需要运", "想发", "要发",
            "合作", "签合同", "开始做"
        ]
        
        # 计算意向分数
        score = 30  # 基础分
        signals = []
        
        for kw in high_intent_keywords:
            if kw in conversation:
                score += 10
                signals.append(f"提到'{kw}'")
        
        score = min(100, score)
        
        if score >= 70:
            level = "high"
            suggestion = "高意向客户，建议尽快电话联系，提供详细报价"
        elif score >= 50:
            level = "medium"
            suggestion = "中等意向，建议发送详细资料并约定下次沟通时间"
        else:
            level = "low"
            suggestion = "意向待培育，建议保持定期联系，分享有价值内容"
        
        return {
            "status": "success",
            "message": "客户分析完成（Maria快速分析）",
            "intent_score": score,
            "intent_level": level,
            "signals": signals,
            "followup_suggestion": suggestion
        }
    
    # ========== 5. 客户跟进（小跟能力）==========
    
    async def _generate_followup(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接生成跟进内容"""
        try:
            from app.agents.follow_agent import follow_agent
            
            customer_id = args.get("customer_id")
            followup_type = args.get("followup_type", "email")
            context = args.get("context", "")
            language = args.get("language", "zh-CN")
            
            logger.info(f"[Maria直接执行] 生成跟进内容: type={followup_type}")
            
            result = await follow_agent.process({
                "action": "generate_followup",
                "customer_id": customer_id,
                "followup_type": followup_type,
                "context": context,
                "language": language
            })
            
            return {
                "status": "success",
                "message": f"跟进{followup_type}内容已生成",
                "followup_type": followup_type,
                "content": result.get("content", ""),
                "subject": result.get("subject", ""),  # 邮件主题
                "suggested_time": result.get("suggested_time", "")
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 生成跟进内容失败: {e}")
            # Maria自己生成跟进内容
            return await self._fallback_generate_followup(args, user_id)
    
    async def _fallback_generate_followup(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """备用跟进内容生成（Maria自己执行）"""
        followup_type = args.get("followup_type", "email")
        context = args.get("context", "询价后未回复")
        
        # Maria使用LLM生成
        if self.agent:
            prompt = f"""请帮我生成一封客户跟进{followup_type}：

背景: {context}

要求:
1. 语气专业友好
2. 不要过于推销
3. 提供有价值的信息
4. 有明确的下一步建议

请直接输出跟进内容，不要解释。"""
            
            from app.core.llm import call_llm
            content = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                model_preference="fast"
            )
            
            return {
                "status": "success",
                "message": f"跟进{followup_type}内容已生成（Maria直接生成）",
                "followup_type": followup_type,
                "content": content
            }
        
        return {
            "status": "error",
            "message": "无法生成跟进内容"
        }
    
    async def _send_followup_email(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接发送跟进邮件"""
        try:
            to_email = args.get("to_email", "")
            customer_name = args.get("customer_name", "客户")
            followup_reason = args.get("followup_reason", "")
            previous_context = args.get("previous_context", "")
            language = args.get("language", "zh-CN")
            
            if not to_email:
                return {"status": "error", "message": "请提供收件人邮箱"}
            
            logger.info(f"[Maria直接执行] 发送跟进邮件到: {to_email}")
            
            # 先生成内容
            followup_result = await self._generate_followup({
                "followup_type": "email",
                "context": f"{followup_reason}。之前沟通内容: {previous_context}",
                "language": language
            }, user_id)
            
            email_content = followup_result.get("content", "")
            email_subject = followup_result.get("subject", f"关于您的物流咨询 - 跟进")
            
            if not email_content:
                return {"status": "error", "message": "生成邮件内容失败"}
            
            # 发送邮件
            from app.skills.email import EmailSkill
            email_skill = EmailSkill()
            
            send_result = await email_skill.handle(
                tool_name="send_email",
                args={
                    "to_emails": [to_email],
                    "subject": email_subject,
                    "body": email_content
                },
                message="发送跟进邮件",
                user_id=user_id
            )
            
            return {
                "status": send_result.get("status", "error"),
                "message": f"跟进邮件已发送到 {to_email}" if send_result.get("status") == "sent" else "发送失败",
                "to_email": to_email,
                "subject": email_subject,
                "content_preview": email_content[:200] + "..." if len(email_content) > 200 else email_content
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 发送跟进邮件失败: {e}")
            return {"status": "error", "message": f"发送邮件时出错: {str(e)}"}
    
    # ========== 6. 一键工作流 ==========
    
    async def _lead_to_video_workflow(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """一键工作流：线索→分析→文案→视频"""
        topic = args.get("topic", "欧洲物流服务")
        video_duration = args.get("video_duration", 60)
        
        logger.info(f"[Maria直接执行] 启动一键工作流: topic={topic}")
        
        workflow_result = {
            "status": "processing",
            "topic": topic,
            "steps": [],
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # 步骤1: 搜索线索，了解市场需求
            logger.info("[工作流] 步骤1: 搜索线索")
            leads_result = await self._search_leads({
                "keywords": [topic, f"{topic}报价", f"{topic}推荐"],
                "max_results": 5
            }, user_id)
            
            workflow_result["steps"].append({
                "step": 1,
                "name": "搜索线索",
                "status": leads_result.get("status"),
                "result": f"发现 {leads_result.get('total_leads', 0)} 条线索"
            })
            
            # 提取线索中的关键需求
            leads = leads_result.get("leads", [])
            customer_needs = []
            for lead in leads[:3]:
                needs = lead.get("needs", [])
                customer_needs.extend(needs)
            
            # 步骤2: 根据线索需求生成文案
            logger.info("[工作流] 步骤2: 生成针对性文案")
            copy_result = await self._write_copy({
                "copy_type": "script",
                "topic": topic,
                "target_audience": f"有{', '.join(customer_needs[:3]) if customer_needs else '物流'}需求的客户",
                "duration": video_duration
            }, user_id)
            
            workflow_result["steps"].append({
                "step": 2,
                "name": "生成文案",
                "status": copy_result.get("status"),
                "result": "脚本创作完成" if copy_result.get("content") else "创作失败"
            })
            
            script = copy_result.get("content", "")
            keywords = copy_result.get("keywords", [])
            
            # 步骤3: 生成视频
            logger.info("[工作流] 步骤3: 生成视频")
            video_result = await self._create_video({
                "title": topic,
                "script": script,
                "mode": "quick",
                "duration": video_duration
            }, user_id)
            
            workflow_result["steps"].append({
                "step": 3,
                "name": "生成视频",
                "status": video_result.get("status"),
                "result": video_result.get("message", "")
            })
            
            # 汇总结果
            workflow_result["status"] = "completed"
            workflow_result["end_time"] = datetime.now().isoformat()
            workflow_result["summary"] = {
                "leads_found": leads_result.get("total_leads", 0),
                "script_generated": bool(script),
                "video_status": video_result.get("status"),
                "video_url": video_result.get("video_url")
            }
            workflow_result["message"] = f"工作流完成！发现{leads_result.get('total_leads', 0)}条线索，生成了针对性脚本，视频{video_result.get('status')}"
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 工作流失败: {e}")
            workflow_result["status"] = "failed"
            workflow_result["error"] = str(e)
            return workflow_result
    
    # ========== 7. 网站生成（小码能力）==========
    
    async def _generate_website(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """直接生成网站代码"""
        try:
            from app.agents.code_engineer import CodeEngineerAgent
            from app.services.project_storage_service import project_storage_service, ensure_project_exists
            
            project_name = args.get("project_name", "my-website")
            website_type = args.get("website_type", "corporate")
            tech_stack = args.get("tech_stack", "static")
            requirements = args.get("requirements", "")
            design_guide = args.get("design_guide", {})
            content = args.get("content", {})
            assets = args.get("assets", {})
            save_to_cos = args.get("save_to_cos", True)
            
            logger.info(f"[Maria直接执行] 生成网站: project={project_name}, type={website_type}")
            
            # 1. 确保项目存在
            if save_to_cos:
                project_result = await ensure_project_exists(
                    project_name=project_name,
                    description=requirements[:200] if requirements else f"{website_type}类型网站",
                    created_by="maria"
                )
                logger.info(f"[Maria直接执行] 项目状态: {project_result}")
            
            # 2. 调用小码生成代码
            code_engineer = CodeEngineerAgent()
            
            result = await code_engineer.process({
                "task_type": "generate",
                "project_name": project_name,
                "website_type": website_type,
                "tech_stack": tech_stack,
                "requirements": requirements,
                "design_guide": design_guide,
                "content": content,
                "assets": assets,
                "save_to_cos": save_to_cos
            })
            
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "message": f"网站代码已生成！共 {result.get('file_count', 0)} 个文件",
                    "project_name": project_name,
                    "website_type": website_type,
                    "tech_stack": tech_stack,
                    "files": result.get("files", []),
                    "file_count": result.get("file_count", 0),
                    "cos_urls": result.get("cos_urls", {}),
                    "preview_info": result.get("preview_info", {}),
                    "generated_files": result.get("generated_files", {}),  # 完整代码
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "代码生成失败"),
                    "error": result.get("error")
                }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 生成网站失败: {e}")
            return {"status": "error", "message": f"生成网站时出错: {str(e)}"}
    
    async def _deploy_website(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """部署网站到 GitHub Pages"""
        try:
            from app.agents.code_engineer import CodeEngineerAgent
            
            project_name = args.get("project_name")
            files = args.get("files", {})
            repo_name = args.get("repo_name", project_name)
            
            if not project_name:
                return {"status": "error", "message": "请提供项目名称"}
            
            if not files:
                return {"status": "error", "message": "请提供要部署的文件"}
            
            logger.info(f"[Maria直接执行] 部署网站: {project_name} -> GitHub Pages")
            
            code_engineer = CodeEngineerAgent()
            
            result = await code_engineer.process({
                "task_type": "deploy",
                "project_name": project_name,
                "files": files,
                "repo_name": repo_name
            })
            
            return {
                "status": result.get("status", "error"),
                "message": result.get("message", "部署结果未知"),
                "site_url": result.get("site_url"),
                "repo_url": result.get("repo_url")
            }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 部署网站失败: {e}")
            return {"status": "error", "message": f"部署网站时出错: {str(e)}"}
    
    async def _save_project_file(self, args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """保存文件到项目 COS 目录"""
        try:
            from app.services.project_storage_service import project_storage_service
            
            project_name = args.get("project_name")
            content = args.get("content", "")
            filename = args.get("filename", "document.md")
            agent_type = args.get("agent_type")  # 可选，自动决定目录
            subfolder = args.get("subfolder")  # 可选，指定目录
            
            if not project_name:
                return {"status": "error", "message": "请提供项目名称"}
            
            if not content:
                return {"status": "error", "message": "请提供要保存的内容"}
            
            logger.info(f"[Maria直接执行] 保存项目文件: {project_name}/{filename}")
            
            result = await project_storage_service.save_text_file(
                project_name=project_name,
                content=content,
                filename=filename,
                agent_type=agent_type,
                subfolder=subfolder
            )
            
            if result.get("success"):
                return {
                    "status": "success",
                    "message": f"文件已保存到 COS: {result.get('path')}",
                    "filename": filename,
                    "path": result.get("path"),
                    "url": result.get("url"),
                    "directory": result.get("directory")
                }
            else:
                return {
                    "status": "error",
                    "message": f"保存失败: {result.get('error')}"
                }
            
        except Exception as e:
            logger.error(f"[Maria直接执行] 保存项目文件失败: {e}")
            return {"status": "error", "message": f"保存文件时出错: {str(e)}"}
