"""
初始化共享状态库数据库
创建表结构和初始数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared_state_manager import SharedStateManager

def main():
    """初始化数据库"""
    print("开始初始化共享状态库数据库...")
    
    # 创建管理器实例（会自动建表）
    manager = SharedStateManager()
    
    # 注册四个中枢分身
    print("注册四中枢分身...")
    
    # 1. 情报官（调度中枢）
    manager.register_or_update_avatar_profile(
        avatar_id="intelligence_officer",
        avatar_name="情报官（调度中枢）",
        template_id="central_001",
        capability_scores={
            "data_crawling": 0.95,
            "business_matching": 0.85,
            "financial_analysis": 0.90,
            "trend_prediction": 0.88,
            "supply_chain_analysis": 0.75,
            "content_creation": 0.65,
            "account_operation": 0.70
        },
        specialization_tags=["数据爬取", "商机筛选", "调度协调", "中枢管理"]
    )
    
    # 2. 内容官（创作中枢）
    manager.register_or_update_avatar_profile(
        avatar_id="content_officer",
        avatar_name="内容官（创作中枢）",
        template_id="central_002",
        capability_scores={
            "content_creation": 0.95,
            "trend_prediction": 0.82,
            "account_operation": 0.75,
            "business_matching": 0.70,
            "data_crawling": 0.60,
            "financial_analysis": 0.65,
            "supply_chain_analysis": 0.55
        },
        specialization_tags=["内容创作", "多平台策略", "品牌一致性", "视觉设计"]
    )
    
    # 3. 运营官（执行中枢）
    manager.register_or_update_avatar_profile(
        avatar_id="operation_officer",
        avatar_name="运营官（执行中枢）",
        template_id="central_003",
        capability_scores={
            "account_operation": 0.92,
            "business_matching": 0.80,
            "supply_chain_analysis": 0.78,
            "financial_analysis": 0.75,
            "data_crawling": 0.70,
            "content_creation": 0.68,
            "trend_prediction": 0.72
        },
        specialization_tags=["运营管理", "执行跟踪", "资源协调", "进度监控"]
    )
    
    # 4. 增长官（优化中枢）
    manager.register_or_update_avatar_profile(
        avatar_id="growth_officer",
        avatar_name="增长官（优化中枢）",
        template_id="central_004",
        capability_scores={
            "financial_analysis": 0.94,
            "business_matching": 0.83,
            "trend_prediction": 0.79,
            "data_crawling": 0.72,
            "content_creation": 0.69,
            "account_operation": 0.77,
            "supply_chain_analysis": 0.74
        },
        specialization_tags=["成本优化", "效益分析", "策略制定", "A/B测试"]
    )
    
    # 注册几个垂直分身模板示例
    print("注册垂直分身模板示例...")
    
    # 1. 牛仔品类选品分身
    manager.register_or_update_avatar_profile(
        avatar_id="vertical_jeans_expert",
        avatar_name="牛仔品类选品分身",
        template_id="vertical_001",
        capability_scores={
            "supply_chain_analysis": 0.92,
            "financial_analysis": 0.88,
            "trend_prediction": 0.85,
            "data_crawling": 0.78,
            "business_matching": 0.75,
            "content_creation": 0.65,
            "account_operation": 0.60
        },
        specialization_tags=["牛仔服装", "跨境电商", "选品分析", "供应链"]
    )
    
    # 2. TikTok爆款内容分身
    manager.register_or_update_avatar_profile(
        avatar_id="vertical_tiktok_expert",
        avatar_name="TikTok爆款内容分身",
        template_id="vertical_002",
        capability_scores={
            "content_creation": 0.96,
            "trend_prediction": 0.89,
            "account_operation": 0.82,
            "data_crawling": 0.79,
            "business_matching": 0.73,
            "financial_analysis": 0.62,
            "supply_chain_analysis": 0.55
        },
        specialization_tags=["短视频", "TikTok", "内容策略", "社交媒体"]
    )
    
    # 插入一些测试商机数据
    print("插入测试商机数据...")
    
    test_opportunities = [
        {
            "source_platform": "Amazon",
            "original_id": "B08N5WRWNW",
            "title": "男士牛仔裤 - 高品质牛仔布料",
            "status": "completed"
        },
        {
            "source_platform": "TikTok",
            "original_id": "video_732154689",
            "title": "牛仔穿搭教程 - 一周获得100万赞",
            "status": "processing"
        },
        {
            "source_platform": "Instagram",
            "original_id": "post_987654321",
            "title": "牛仔品牌合作推广 - 网红营销机会",
            "status": "pending"
        },
        {
            "source_platform": "Amazon",
            "original_id": "B07ZPKN6YR",
            "title": "女士牛仔外套 - 秋冬新款",
            "status": "completed"
        }
    ]
    
    for opp in test_opportunities:
        is_new, hash_val = manager.check_and_record_opportunity(
            source_platform=opp["source_platform"],
            original_id=opp["original_id"],
            title=opp["title"],
            status=opp["status"]
        )
        
        # 如果是处理中的商机，分配任务
        if opp["status"] == "processing":
            assignment_id = manager.record_task_assignment(
                opportunity_hash=hash_val,
                assigned_avatar="intelligence_officer",
                priority=3
            )
            print(f"  分配任务: {opp['title']} -> 情报官 (分配ID: {assignment_id})")
        elif opp["status"] == "completed":
            # 模拟已完成的商机有任务记录
            assignment_id = manager.record_task_assignment(
                opportunity_hash=hash_val,
                assigned_avatar="intelligence_officer",
                priority=2
            )
            manager.update_task_completion(
                assignment_id=assignment_id,
                completion_status="completed",
                result_summary=f"商机分析完成，利润率约{35 if '男士' in opp['title'] else 28}%"
            )
    
    # 记录一些测试成本数据
    print("记录测试成本数据...")
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    cost_records = [
        {
            "avatar_id": "intelligence_officer",
            "cost_type": "tokens",
            "amount": 12500,
            "country_code": "US",
            "logistics_cost": 5.0,
            "tax_rate": 10.0,
            "local_operations_cost": 500.0,
            "shipping_time_days": 7,
            "notes": "24小时商机监控消耗（美国）"
        },
        {
            "avatar_id": "content_officer",
            "cost_type": "tokens",
            "amount": 9800,
            "country_code": "DE",
            "logistics_cost": 4.5,
            "tax_rate": 19.0,
            "local_operations_cost": 450.0,
            "shipping_time_days": 5,
            "notes": "多平台内容创作（德国）"
        },
        {
            "avatar_id": "vertical_jeans_expert",
            "cost_type": "api_calls",
            "amount": 45,
            "country_code": "CN",
            "logistics_cost": 3.0,
            "tax_rate": 13.0,
            "local_operations_cost": 300.0,
            "shipping_time_days": 10,
            "notes": "Amazon PAAPI商品数据查询（中国）"
        },
        {
            "avatar_id": "vertical_tiktok_expert",
            "cost_type": "workflow_executions",
            "amount": 32,
            "country_code": "SG",
            "logistics_cost": 3.5,
            "tax_rate": 7.0,
            "local_operations_cost": 400.0,
            "shipping_time_days": 3,
            "notes": "TikTok趋势分析任务执行（新加坡）"
        }
    ]
    
    for cost in cost_records:
        manager.record_cost_consumption(
            avatar_id=cost["avatar_id"],
            cost_type=cost["cost_type"],
            amount=cost["amount"],
            country_code=cost["country_code"],
            logistics_cost=cost["logistics_cost"],
            tax_rate=cost["tax_rate"],
            local_operations_cost=cost["local_operations_cost"],
            shipping_time_days=cost["shipping_time_days"],
            period_start=yesterday.isoformat(),
            period_end=now.isoformat(),
            notes=cost["notes"]
        )
    
    # 输出统计信息
    print("\n数据库初始化完成！")
    print("=" * 60)
    
    stats = manager.get_statistics()
    print(f"总商机数: {stats['total_opportunities']}")
    print(f"已完成商机数: {stats['completed_opportunities']}")
    print(f"总任务数: {stats['total_tasks']}")
    print(f"进行中任务数: {stats['in_progress_tasks']}")
    print(f"总分身数: {stats['total_avatars']}")
    print(f"活跃分身数: {stats['active_avatars']}")
    print(f"总成本: ${stats['total_cost_usd']:.2f} USD")
    
    print("=" * 60)
    print(f"数据库文件: {manager.db_path}")
    print("可以使用以下命令测试:")
    print("  python src/test_shared_state.py")
    print("  python src/shared_state_manager.py")
    
    manager.close()

if __name__ == "__main__":
    main()