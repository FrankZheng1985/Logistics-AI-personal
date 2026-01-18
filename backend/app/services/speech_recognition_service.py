"""
语音识别服务
使用腾讯云长音频识别API进行会议录音转写
"""
import json
import hashlib
import hmac
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import httpx
from sqlalchemy import text

from app.models.database import AsyncSessionLocal
from app.core.config import settings


class SpeechRecognitionService:
    """语音识别服务（腾讯云ASR）"""
    
    def __init__(self):
        # 腾讯云配置（使用统一凭证）
        self.secret_id = getattr(settings, 'TENCENT_SECRET_ID', '') or ''
        self.secret_key = getattr(settings, 'TENCENT_SECRET_KEY', '') or ''
        self.region = "ap-guangzhou"
        self.service = "asr"
        self.host = "asr.tencentcloudapi.com"
        self.endpoint = f"https://{self.host}"
        
        # 轮询间隔（秒）
        self.poll_interval = 5
        self.max_wait_time = 3600  # 最长等待1小时
    
    def get_config_status(self) -> dict:
        """获取配置状态"""
        return {
            "configured": self.is_configured(),
            "secret_id": bool(self.secret_id),
            "secret_key": bool(self.secret_key),
            "message": "语音识别已配置" if self.is_configured() else "请配置TENCENT_SECRET_ID和TENCENT_SECRET_KEY"
        }
    
    def is_configured(self) -> bool:
        """检查是否已配置腾讯云凭证"""
        return bool(self.secret_id and self.secret_key)
    
    async def transcribe_audio(
        self,
        audio_url: str,
        meeting_id: Optional[str] = None,
        audio_format: str = "mp3",
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交长音频转写任务
        
        Args:
            audio_url: 音频文件URL（需要公网可访问）
            meeting_id: 关联的会议ID
            audio_format: 音频格式（mp3/wav/m4a/amr等）
            callback_url: 任务完成回调URL（可选）
        
        Returns:
            任务信息
        """
        if not self.is_configured():
            logger.error("腾讯云语音识别未配置")
            return {"success": False, "error": "语音识别服务未配置，请设置TENCENT_SECRET_ID和TENCENT_SECRET_KEY"}
        
        # 创建转写任务记录
        task_id = await self._create_task_record(meeting_id, audio_url, audio_format)
        
        try:
            # 调用腾讯云API创建转写任务
            result = await self._create_recognition_task(audio_url, audio_format)
            
            if not result.get("success"):
                await self._update_task_status(task_id, "failed", error=result.get("error"))
                return result
            
            tencent_task_id = result["task_id"]
            
            # 更新任务记录
            await self._update_task_record(task_id, tencent_task_id)
            
            logger.info(f"语音转写任务已提交: {tencent_task_id}")
            
            # 如果没有回调URL，开始轮询任务状态
            if not callback_url:
                # 在后台轮询
                asyncio.create_task(self._poll_task_result(task_id, tencent_task_id, meeting_id))
            
            return {
                "success": True,
                "task_id": task_id,
                "tencent_task_id": tencent_task_id,
                "message": "转写任务已提交，处理中..."
            }
            
        except Exception as e:
            logger.error(f"提交转写任务失败: {e}")
            await self._update_task_status(task_id, "failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _create_recognition_task(
        self,
        audio_url: str,
        audio_format: str
    ) -> Dict[str, Any]:
        """调用腾讯云API创建识别任务"""
        # 请求参数
        params = {
            "EngineModelType": "16k_zh",  # 16k中文通用模型
            "ChannelNum": 1,  # 单声道
            "ResTextFormat": 0,  # 返回识别结果
            "SourceType": 0,  # URL方式
            "Url": audio_url,
        }
        
        # 格式映射
        format_map = {
            "mp3": "mp3",
            "m4a": "m4a", 
            "wav": "wav",
            "amr": "amr",
            "ogg": "ogg"
        }
        
        # 生成签名并发送请求
        try:
            headers = self._generate_headers("CreateRecTask", params)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=params,
                    timeout=30
                )
                
                result = response.json()
                
                if "Response" in result:
                    if "Error" in result["Response"]:
                        error = result["Response"]["Error"]
                        return {
                            "success": False,
                            "error": f"{error['Code']}: {error['Message']}"
                        }
                    
                    task_id = result["Response"]["Data"]["TaskId"]
                    return {
                        "success": True,
                        "task_id": str(task_id)
                    }
                
                return {"success": False, "error": "Unknown response format"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _poll_task_result(
        self,
        task_id: str,
        tencent_task_id: str,
        meeting_id: Optional[str]
    ):
        """轮询任务结果"""
        start_time = time.time()
        
        while time.time() - start_time < self.max_wait_time:
            try:
                result = await self._query_task_result(tencent_task_id)
                
                if result.get("status") == "completed":
                    # 任务完成
                    transcription = result.get("result", "")
                    await self._update_task_status(
                        task_id, 
                        "completed",
                        result_text=transcription
                    )
                    
                    # 更新会议记录
                    if meeting_id:
                        await self._update_meeting_transcription(meeting_id, transcription)
                        # 生成会议纪要
                        await self._generate_meeting_summary(meeting_id, transcription)
                    
                    logger.info(f"语音转写完成: {task_id}")
                    return
                    
                elif result.get("status") == "failed":
                    await self._update_task_status(
                        task_id,
                        "failed",
                        error=result.get("error", "Unknown error")
                    )
                    logger.error(f"语音转写失败: {task_id} - {result.get('error')}")
                    return
                
                # 更新进度
                progress = result.get("progress", 0)
                await self._update_task_progress(task_id, progress)
                
            except Exception as e:
                logger.warning(f"查询转写任务状态失败: {e}")
            
            # 等待后继续轮询
            await asyncio.sleep(self.poll_interval)
        
        # 超时
        await self._update_task_status(task_id, "failed", error="任务超时")
        logger.error(f"语音转写任务超时: {task_id}")
    
    async def _query_task_result(self, tencent_task_id: str) -> Dict[str, Any]:
        """查询腾讯云任务结果"""
        params = {
            "TaskId": int(tencent_task_id)
        }
        
        try:
            headers = self._generate_headers("DescribeTaskStatus", params)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=params,
                    timeout=30
                )
                
                result = response.json()
                
                if "Response" in result:
                    if "Error" in result["Response"]:
                        return {
                            "status": "failed",
                            "error": result["Response"]["Error"]["Message"]
                        }
                    
                    data = result["Response"]["Data"]
                    status_code = data.get("StatusCode", 0)
                    
                    # 状态码：0-等待中，1-执行中，2-成功，3-失败
                    if status_code == 2:
                        return {
                            "status": "completed",
                            "result": data.get("Result", "")
                        }
                    elif status_code == 3:
                        return {
                            "status": "failed",
                            "error": data.get("ErrorMsg", "Unknown error")
                        }
                    else:
                        return {
                            "status": "processing",
                            "progress": 50 if status_code == 1 else 0
                        }
                
                return {"status": "unknown"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _generate_headers(self, action: str, params: Dict) -> Dict[str, str]:
        """生成腾讯云API签名请求头"""
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # 构造规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        content_type = "application/json; charset=utf-8"
        payload = json.dumps(params)
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{self.host}\n"
            f"x-tc-action:{action.lower()}\n"
        )
        signed_headers = "content-type;host;x-tc-action"
        
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_payload}"
        )
        
        # 构造待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_request}"
        
        # 计算签名
        def sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, self.service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 构造Authorization
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return {
            "Content-Type": content_type,
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Version": "2019-06-14",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
            "Authorization": authorization
        }
    
    # ==================== 数据库操作 ====================
    
    async def _create_task_record(
        self,
        meeting_id: Optional[str],
        audio_url: str,
        audio_format: str
    ) -> str:
        """创建转写任务记录"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO speech_transcription_tasks 
                    (meeting_id, audio_url, audio_format, status)
                    VALUES (:meeting_id, :audio_url, :audio_format, 'pending')
                    RETURNING id
                """),
                {
                    "meeting_id": meeting_id,
                    "audio_url": audio_url,
                    "audio_format": audio_format
                }
            )
            row = result.fetchone()
            await db.commit()
            return str(row[0])
    
    async def _update_task_record(self, task_id: str, tencent_task_id: str):
        """更新任务记录"""
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE speech_transcription_tasks
                    SET tencent_task_id = :tencent_task_id,
                        status = 'processing',
                        started_at = NOW()
                    WHERE id = :id
                """),
                {"id": task_id, "tencent_task_id": tencent_task_id}
            )
            await db.commit()
    
    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        result_text: Optional[str] = None,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE speech_transcription_tasks
                    SET status = :status,
                        result_text = :result_text,
                        error_message = :error,
                        completed_at = CASE WHEN :status IN ('completed', 'failed') THEN NOW() ELSE NULL END
                    WHERE id = :id
                """),
                {
                    "id": task_id,
                    "status": status,
                    "result_text": result_text,
                    "error": error
                }
            )
            await db.commit()
    
    async def _update_task_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE speech_transcription_tasks SET progress = :progress WHERE id = :id"),
                {"id": task_id, "progress": progress}
            )
            await db.commit()
    
    async def _update_meeting_transcription(self, meeting_id: str, transcription: str):
        """更新会议转写结果"""
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE meeting_records
                    SET raw_transcription = :transcription,
                        transcription_status = 'completed',
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": meeting_id, "transcription": transcription}
            )
            await db.commit()
    
    async def _generate_meeting_summary(self, meeting_id: str, transcription: str):
        """使用AI生成会议纪要"""
        from app.agents.assistant_agent import assistant_agent
        
        try:
            # 使用AI分析转写文本
            summary_prompt = f"""请根据以下会议录音转写内容，生成结构化的会议纪要。

会议录音转写：
{transcription[:8000]}  

请按以下JSON格式返回：
{{
    "summary": "一句话会议摘要",
    "participants": "识别到的参会人员（如果有）",
    "content": [
        {{"topic": "议题1", "content": "讨论内容"}},
        {{"topic": "议题2", "content": "讨论内容"}}
    ],
    "action_items": [
        {{"assignee": "负责人", "task": "任务内容", "deadline": "截止时间（如果提到）"}}
    ]
}}

只返回JSON，不要其他内容。
"""
            
            response = await assistant_agent.think(
                [{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            
            # 解析JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                summary_data = json.loads(json_match.group())
                
                # 更新会议记录
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        text("""
                            UPDATE meeting_records
                            SET summary = :summary,
                                participants = :participants,
                                content_structured = :content,
                                action_items = :action_items,
                                updated_at = NOW()
                            WHERE id = :id
                        """),
                        {
                            "id": meeting_id,
                            "summary": summary_data.get("summary", ""),
                            "participants": summary_data.get("participants", ""),
                            "content": json.dumps(summary_data.get("content", []), ensure_ascii=False),
                            "action_items": json.dumps(summary_data.get("action_items", []), ensure_ascii=False)
                        }
                    )
                    await db.commit()
                
                # 从会议纪要创建待办事项
                from app.services.assistant_service import assistant_service
                action_items = summary_data.get("action_items", [])
                if action_items:
                    await assistant_service.create_todos_from_meeting(meeting_id, action_items)
                
                logger.info(f"会议纪要生成完成: {meeting_id}")
                
                # TODO: 通过企业微信发送会议纪要给用户
                
        except Exception as e:
            logger.error(f"生成会议纪要失败: {e}")


# 创建单例
speech_recognition_service = SpeechRecognitionService()
