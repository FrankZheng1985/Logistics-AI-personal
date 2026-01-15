#!/usr/bin/env python3
"""
创建物流行业营销序列内容
"""
import asyncio
import uuid
from sqlalchemy import text
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import async_session_maker


# 营销序列配置
MARKETING_SEQUENCES = [
    {
        "name": "新客户欢迎序列",
        "description": "针对首次询价的新客户，建立信任，展示专业实力",
        "trigger_type": "first_inquiry",
        "emails": [
            {
                "subject": "感谢您的询价 - 专业物流解决方案为您服务",
                "content": """尊敬的客户：

感谢您选择与我们联系！我们是专业的国际物流服务商，已为超过1000家企业提供优质服务。

🌟 我们的核心优势：
• 欧洲专线：7-15天稳定时效
• 清关无忧：专业团队处理海关事务
• 价格透明：无隐藏费用，报价即最终价
• 全程追踪：实时物流信息更新

📦 服务范围：
- 空运/海运/铁路运输
- 整柜/拼箱服务
- 仓储配送一体化
- 报关报检服务

我们的客服团队将在24小时内与您联系，为您定制最优运输方案。

如有任何疑问，欢迎随时回复此邮件或拨打我们的热线。

祝商祺！
物流获客AI团队""",
                "delay_days": 0
            },
            {
                "subject": "为您精选的物流解决方案 - 成功案例分享",
                "content": """尊敬的客户：

感谢您对我们服务的关注！今天想与您分享几个成功案例，帮助您更好地了解我们的服务能力。

📊 成功案例展示：

【案例1】深圳电子厂 → 德国汉堡
- 货物：电子配件 5CBM
- 方案：欧洲铁路专线
- 时效：18天门到门
- 结果：比海运快10天，比空运省60%成本

【案例2】义乌贸易商 → 西班牙马德里
- 货物：日用百货 15CBM  
- 方案：中欧班列+尾程配送
- 时效：22天完成清关配送
- 结果：客户返单率提升40%

【案例3】宁波制造商 → 波兰华沙
- 货物：机械设备 整柜
- 方案：海运+铁路联运
- 时效：25天
- 结果：年节省物流成本30万+

💡 我们能为您做什么：
1. 免费货物评估
2. 多方案对比报价
3. 清关风险预判
4. 全程物流追踪

期待为您提供同样优质的服务！

此致
物流获客AI团队""",
                "delay_days": 1
            },
            {
                "subject": "专属报价已准备好 - 限时优惠等您领取",
                "content": """尊敬的客户：

根据您的询价需求，我们已为您准备好专属运输方案。

🎁 新客户专属优惠：
• 首单运费减免 5%
• 免费货物保险（价值500元）
• 优先舱位保障
• 专属客服一对一服务

⏰ 优惠有效期：7天

📋 下一步操作：
1. 回复此邮件确认货物详情
2. 我们24小时内发送正式报价单
3. 确认订舱即可享受优惠

❓ 常见问题：
Q: 如何计算运费？
A: 根据货物重量、体积、目的地综合计算，我们会提供详细报价明细。

Q: 清关需要什么资料？
A: 商业发票、装箱单、原产地证等，我们会提供完整清单指导。

Q: 货物损坏怎么办？
A: 我们提供全程货运保险，损坏可获全额赔付。

立即回复，开启您的便捷物流体验！

祝商祺！
物流获客AI团队""",
                "delay_days": 3
            }
        ]
    },
    {
        "name": "报价跟进序列",
        "description": "报价发出后未得到回复，主动跟进促成转化",
        "trigger_type": "no_reply_3d",
        "emails": [
            {
                "subject": "关于您的报价 - 有任何疑问吗？",
                "content": """尊敬的客户：

希望您已收到我们之前发送的报价方案。

不知道您是否有任何疑问或需要进一步说明的地方？我们非常重视您的需求，希望能为您提供最满意的解决方案。

📞 如果您有以下疑虑，请告诉我们：

• 价格方面：我们可以根据货量提供阶梯优惠
• 时效方面：我们有多种运输方式可选
• 清关方面：我们的专业团队可提前评估风险
• 其他需求：任何特殊要求都可以沟通

💬 您可以通过以下方式联系我们：
- 直接回复此邮件
- 微信/WhatsApp: [联系方式]
- 电话: [联系电话]

期待您的回复！

物流获客AI团队""",
                "delay_days": 0
            },
            {
                "subject": "好消息！您的报价优惠期限已延长",
                "content": """尊敬的客户：

考虑到您可能需要更多时间做决定，我们特别为您延长了优惠期限！

🎉 延期优惠内容：
• 原报价有效期延长7天
• 额外赠送货物保险服务
• 首单运费再减2%

📊 为什么选择我们？

对比项目    |  我们   |  行业平均
时效保障   |  准时率98%  |  85%
价格透明   |  无隐藏费   |  常有附加费
清关成功率 |  99.5%     |  95%
售后响应   |  2小时内   |  24-48小时

🔔 温馨提示：
物流旺季即将来临，建议尽早确认订舱以保障舱位和时效。

如果您已选择其他供应商，也欢迎告诉我们原因，帮助我们改进服务。

期待与您合作！

物流获客AI团队""",
                "delay_days": 2
            },
            {
                "subject": "最后提醒：您的专属优惠即将过期",
                "content": """尊敬的客户：

这是关于您之前询价的最后一次提醒。

⏰ 您的专属优惠将于48小时后过期

在优惠过期前，您仍可享受：
✓ 首单运费减免优惠
✓ 免费货物保险
✓ 优先舱位预订

📌 如果您暂时没有运输需求：
完全理解！我们可以将您的信息存档，下次有需求时直接联系我们即可，我们承诺提供同样的优质价格。

📌 如果您选择了其他供应商：
欢迎将我们作为备选，当您需要比价或遇到问题时，我们随时在这里。

📌 如果有任何顾虑未解决：
请直接告诉我们，我们一定尽力帮您解决！

感谢您的时间，祝您生意兴隆！

物流获客AI团队""",
                "delay_days": 5
            }
        ]
    },
    {
        "name": "老客户激活序列",
        "description": "针对30天未联系的老客户，唤醒合作意愿",
        "trigger_type": "inactive_30d",
        "emails": [
            {
                "subject": "好久不见！我们想您了 🌟",
                "content": """亲爱的老朋友：

距离我们上次合作已经有一段时间了，希望您一切顺利！

我们始终记得与您的愉快合作，您的支持是我们不断进步的动力。

📊 您与我们的合作回顾：
• 累计运输票数：[历史数据]
• 准时送达率：99%+
• 服务满意度：持续好评

🎁 老客户专属福利：
作为我们的valued客户，您可享受：
1. 老客户专属价格
2. 优先舱位保障
3. 紧急订单特快通道
4. 免费货物保险升级

💡 近期行业动态：
• 欧洲航线价格有所调整
• 新增东南亚特惠专线
• 清关政策有新变化

如果您近期有物流需求，或者想了解最新的行业资讯，欢迎随时联系我们！

期待再次为您服务！

物流获客AI团队""",
                "delay_days": 0
            },
            {
                "subject": "物流行业最新资讯 & 新服务上线通知",
                "content": """尊敬的客户：

我们持续关注行业动态，为您整理了以下重要资讯：

📰 行业快讯：

【运价动态】
• 欧洲海运：基本持稳，预计下月小幅波动
• 空运：舱位紧张，建议提前预订
• 铁路：性价比优势明显，时效稳定

【政策变化】
• 部分商品清关要求更新
• 新的合规要求生效
• 我们已更新服务流程确保顺畅

🚀 新服务上线：

1. 【快速询价系统】
   在线提交信息，5分钟获取报价

2. 【物流追踪升级】
   实时推送、地图追踪、异常预警

3. 【清关预审服务】
   提前评估风险，避免延误

这些新服务均可免费体验，欢迎尝试！

物流获客AI团队""",
                "delay_days": 3
            },
            {
                "subject": "老客户回归礼遇 - 专属优惠码已生成",
                "content": """亲爱的老朋友：

为感谢您一直以来的支持，我们为您准备了专属回归礼遇！

🎁 专属优惠码：VIP2024BACK

使用此优惠码可享受：
✓ 首单运费立减 8%
✓ 免费提供货物保险
✓ 专属客服VIP通道
✓ 优先舱位预订

⏰ 有效期：30天

📋 使用方式：
1. 回复此邮件告知您的需求
2. 我们为您定制方案
3. 下单时报出优惠码即可

💬 不管您是否有即时需求，都欢迎和我们保持联系。

您的建议和反馈对我们非常宝贵，如果您对我们的服务有任何想法，也请随时告诉我们！

期待再次合作！

物流获客AI团队""",
                "delay_days": 7
            }
        ]
    },
    {
        "name": "节日营销序列",
        "description": "节假日关怀营销，增进客户关系",
        "trigger_type": "manual",
        "emails": [
            {
                "subject": "节日祝福 | 感恩有您一路同行 🎊",
                "content": """尊敬的客户：

值此佳节来临之际，物流获客AI全体同仁向您致以最诚挚的祝福！

🎉 祝您：
• 生意兴隆，财源广进
• 身体健康，阖家幸福
• 万事如意，前程似锦

📅 节假日服务安排：
• 客服热线：正常服务
• 运输时效：略有影响，建议提前安排
• 清关服务：我们已提前做好准备

🎁 节日特惠活动：
节日期间下单，可享受：
- 运费优惠 5%
- 免费货物保险
- 优先清关服务

感谢您一直以来的信任与支持，期待在新的一年继续为您服务！

再次祝您节日快乐！

物流获客AI团队""",
                "delay_days": 0
            },
            {
                "subject": "节后物流复工通知 & 舱位预订提醒",
                "content": """尊敬的客户：

希望您度过了一个愉快的假期！

我们已全面复工，各项服务恢复正常运营。

📢 重要提醒：

【舱位预订】
节后是物流高峰期，舱位紧张，建议尽早预订：
• 海运：建议提前7-10天订舱
• 空运：建议提前3-5天订舱
• 铁路：建议提前5-7天订舱

【价格调整】
节后运价可能有所调整，我们承诺：
• 第一时间通知价格变化
• 提供最具竞争力的报价
• 透明收费，无隐藏费用

【服务保障】
• 全面恢复正常服务
• 客服团队随时待命
• 紧急订单优先处理

如果您有物流需求，欢迎随时联系我们！

祝工作顺利！

物流获客AI团队""",
                "delay_days": 3
            }
        ]
    }
]


async def create_marketing_content():
    """创建营销序列和邮件内容"""
    print("🚀 开始创建营销序列内容...")
    
    try:
        async with async_session_maker() as db:
            created_count = 0
            
            for seq_data in MARKETING_SEQUENCES:
                # 检查序列是否已存在
                result = await db.execute(
                    text("SELECT id FROM marketing_sequences WHERE name = :name"),
                    {"name": seq_data["name"]}
                )
                existing = result.fetchone()
                
                if existing:
                    print(f"  ⏭️  序列已存在: {seq_data['name']}")
                    continue
                
                # 创建序列
                sequence_id = str(uuid.uuid4())
                await db.execute(
                    text("""
                        INSERT INTO marketing_sequences 
                        (id, name, description, trigger_type, status, email_count)
                        VALUES (:id, :name, :description, :trigger_type, 'draft', :email_count)
                    """),
                    {
                        "id": sequence_id,
                        "name": seq_data["name"],
                        "description": seq_data["description"],
                        "trigger_type": seq_data["trigger_type"],
                        "email_count": len(seq_data["emails"])
                    }
                )
                print(f"  ✅ 创建序列: {seq_data['name']}")
                
                # 创建邮件
                for idx, email_data in enumerate(seq_data["emails"]):
                    email_id = str(uuid.uuid4())
                    await db.execute(
                        text("""
                            INSERT INTO sequence_emails 
                            (id, sequence_id, order_index, subject, content, delay_days)
                            VALUES (:id, :sequence_id, :order_index, :subject, :content, :delay_days)
                        """),
                        {
                            "id": email_id,
                            "sequence_id": sequence_id,
                            "order_index": idx + 1,
                            "subject": email_data["subject"],
                            "content": email_data["content"],
                            "delay_days": email_data["delay_days"]
                        }
                    )
                    print(f"      📧 添加邮件 {idx + 1}: {email_data['subject'][:30]}...")
                
                created_count += 1
            
            await db.commit()
            
            print(f"\n🎉 创建完成！共创建 {created_count} 个营销序列")
            
            # 显示统计
            result = await db.execute(
                text("SELECT COUNT(*) FROM marketing_sequences")
            )
            total_sequences = result.scalar()
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM sequence_emails")
            )
            total_emails = result.scalar()
            
            print(f"📊 当前统计：{total_sequences} 个序列，{total_emails} 封邮件")
            
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_marketing_content())
