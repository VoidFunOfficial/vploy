from ai_analysis import deep_analysis
from polymarket_api import event_summary_readableforai
from polymarket_api import GammaMarketsAPI
from auto_decision import position_manager
from ai_analysis import gpt_api
import asyncio
import json

async def main():
    with GammaMarketsAPI() as api:
        # events = api.get_event_by_slug("how-many-gold-cards-will-trump-sell-in-2025")
        # deep_ana = deep_analysis.AnalysisTaskManager(initial_delay=100,cookie_string="__Secure-auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjQ0ODg1OTIsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzMjc4OTkyLCJ0b2tlbl90eXBlIjoiYXV0aF90b2tlbiJ9.OybGxLfP3tz6pcclLp2CKcpiEIKxGm3GuliEKu5hp6c;oai-nav-state=1;oai-did=4bc875ef-9530-4184-88c5-0e425f655700;__Secure-access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjM3ODcyNTgsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzNjUyMjU4LCJ0b2tlbl90eXBlIjoiYWNjZXNzX3Rva2VuIiwic3Vic2NyaXB0aW9uX2lkIjoiNjY0MGM3NWMxNDQ4MGI4YWZmZGUxY2VhIiwiYWNjb3VudF9pZCI6IjY4ZTBjMDNmMTNjMTE1ZDM5NWQwNzM2NyJ9.PHhr1dw9Yoizp9iM4bEXUY9BgVw60xoKmEVLdYqWBVA;_account=f9f24477-3b6b-4a27-a298-c8663fd4edc5;oai-locale=en-US")
        # await deep_ana.start_workers(num_workers=1)
        # task_id = await deep_ana.submit_analysis_task(event_summary_readableforai(events))
        # ai_analysis = await deep_ana.wait_for_task_completion(task_id)
        # print(ai_analysis)

        # 获取 GPT 分析结果
        decison = gpt_api.get_result(
            conversation_id="691f358c-5bdc-8000-b2aa-7477021c3bc3",
            cookie_header="__Secure-auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjQ0ODg1OTIsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzMjc4OTkyLCJ0b2tlbl90eXBlIjoiYXV0aF90b2tlbiJ9.OybGxLfP3tz6pcclLp2CKcpiEIKxGm3GuliEKu5hp6c;oai-nav-state=1;oai-did=4bc875ef-9530-4184-88c5-0e425f655700;__Secure-access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjM3ODcyNTgsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzNjUyMjU4LCJ0b2tlbl90eXBlIjoiYWNjZXNzX3Rva2VuIiwic3Vic2NyaXB0aW9uX2lkIjoiNjY0MGM3NWMxNDQ4MGI4YWZmZGUxY2VhIiwiYWNjb3VudF9pZCI6IjY4ZTBjMDNmMTNjMTE1ZDM5NWQwNzM2NyJ9.PHhr1dw9Yoizp9iM4bEXUY9BgVw60xoKmEVLdYqWBVA;_account=f9f24477-3b6b-4a27-a298-c8663fd4edc5;oai-locale=en-US"
        )

        # 获取市场数据
        markets = api.get_event_markets(19720)
        print(markets)
        # print(f"市场数量: {len(markets)}")

        # 解析 AI 响应（从字符串转换为 JSON 对象）
        ai_response_text = decison["ai_response"]

        # 使用 validate_analysis_result 验证并解析
        is_valid, ai_analysis_json = deep_analysis.validate_analysis_result(ai_response_text)


        # 执行仓位分配
        allocation_result = position_manager.allocate_optimal_positions_pro(
            gamma_markets=markets,
            ai_analysis_result=ai_analysis_json,  # 传入解析后的 JSON 对象
            M_cents=100,
            kappa=0.7,
            xi=0.5
        )
        print(f"\n仓位分配结果:\n{allocation_result}")
    
if __name__ == "__main__":
    asyncio.run(main())