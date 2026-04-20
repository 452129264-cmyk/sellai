#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垂直领域分身模板生成脚本
基于《无限AI分身架构设计文档》中的模板标准，生成10个垂直领域分身模板JSON文件
"""

import json
import os
from datetime import datetime

# 输出目录
OUTPUT_DIR = "outputs/分身模板库"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 模板定义
TEMPLATES = [
    {
        "template_id": "vertical_001",
        "template_name": "牛仔品类选品分身",
        "category": "跨境电商_服装",
        "description": "专注于牛仔服装品类的选品专家，精通面料分析、供应链对接、价格策略",
        "persona_config": {
            "role": "牛仔品类选品专家",
            "personality": "专业严谨、注重细节、市场敏锐",
            "expertise": ["牛仔面料分析", "供应链成本优化", "价格竞争力评估", "趋势预测"],
            "communication_style": "专业高效，数据支撑结论"
        },
        "task_configurations": [
            {
                "task_type": "product_selection",
                "schedule": "每日",
                "trigger_condition": "市场数据更新",
                "output_target": "outputs/vertical/牛仔选品/{{date}}_推荐.json",
                "parameters": {
                    "target_margin_min": 35,
                    "price_range": ["$15", "$80"],
                    "preferred_supply_countries": ["CN", "VN", "TR"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": False,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": True,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["Amazon", "独立站", "批发平台"],
            "target_regions": ["US", "EU", "AU"],
            "data_sources": ["牛仔行业报告", "面料价格指数", "海关数据"],
            "api_keys_needed": ["Amazon_PAAPI"]
        },
        "collaboration_protocol": {
            "primary_partners": ["调度中枢", "创作中枢"],
            "message_formats": {
                "product_analysis_request": {
                    "format": "json",
                    "required_fields": ["product_id", "market", "budget_range"]
                },
                "supply_chain_data_share": {
                    "format": "json", 
                    "required_fields": ["material_type", "supplier_info", "unit_cost"]
                }
            },
            "notification_channels": ["dashboard", "email"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1500,
            "estimated_workflow_executions_per_day": 12,
            "memory_storage_requirements_mb": 5,
            "specialized_api_costs": ["Amazon_PAAPI: $0.01/request"]
        }
    },
    {
        "template_id": "vertical_002",
        "template_name": "TikTok爆款内容分身",
        "category": "社交媒体_内容创作",
        "description": "TikTok短视频平台爆款内容策略与制作专家，精通趋势洞察、脚本创作、视觉呈现",
        "persona_config": {
            "role": "TikTok内容策略师",
            "personality": "创意十足、网感敏锐、节奏感强",
            "expertise": ["趋势洞察", "脚本创作", "视觉设计", "算法理解"],
            "communication_style": "生动活泼，贴合平台调性"
        },
        "task_configurations": [
            {
                "task_type": "content_creation",
                "schedule": "每日",
                "trigger_condition": "热点事件或趋势更新",
                "output_target": "outputs/vertical/TikTok内容/{{date}}_脚本.json",
                "parameters": {
                    "target_platform": "TikTok",
                    "content_format": "短视频",
                    "duration_range": [15, 60],
                    "hashtag_strategy": "混合"
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": True,
            "account_operation": False,
            "financial_analysis": False,
            "supply_chain_analysis": False,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
            "target_regions": ["全球"],
            "data_sources": ["TikTok趋势榜", "社交媒体监测工具", "行业报告"],
            "api_keys_needed": ["TikTok API", "社交媒体分析工具API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["创作中枢", "运营中枢"],
            "message_formats": {
                "trend_analysis_request": {
                    "format": "json",
                    "required_fields": ["niche", "target_audience", "timeframe"]
                },
                "content_review_request": {
                    "format": "json",
                    "required_fields": ["script_draft", "visual_references", "target_metrics"]
                }
            },
            "notification_channels": ["dashboard", "push_notification"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1200,
            "estimated_workflow_executions_per_day": 20,
            "memory_storage_requirements_mb": 8,
            "specialized_api_costs": ["TikTok API: $0.05/request", "分析工具API: $0.02/request"]
        }
    },
    {
        "template_id": "vertical_003",
        "template_name": "独立站运营分身",
        "category": "跨境电商_运营",
        "description": "Shopify/WooCommerce独立站全流程运营专家，精通建站、商品上架、支付集成、客户服务",
        "persona_config": {
            "role": "独立站运营总监",
            "personality": "系统化思维、注重细节、客户导向",
            "expertise": ["电商平台搭建", "支付系统集成", "库存管理", "客户服务"],
            "communication_style": "专业清晰，解决方案导向"
        },
        "task_configurations": [
            {
                "task_type": "store_management",
                "schedule": "每日",
                "trigger_condition": "订单生成或库存变化",
                "output_target": "outputs/vertical/独立站运营/{{date}}_运营报告.json",
                "parameters": {
                    "platform": "Shopify",
                    "integration_required": ["支付", "物流", "CRM"],
                    "daily_checkpoints": ["订单处理", "库存同步", "客户咨询"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": False,
            "business_matching": False,
            "content_creation": False,
            "account_operation": True,
            "financial_analysis": True,
            "supply_chain_analysis": True,
            "trend_prediction": False
        },
        "resource_requirements": {
            "preferred_platforms": ["Shopify", "WooCommerce", "Magento"],
            "target_regions": ["全球"],
            "data_sources": ["电商平台API", "支付网关日志", "库存管理系统"],
            "api_keys_needed": ["Shopify API", "Stripe API", "物流API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["运营中枢", "增长中枢"],
            "message_formats": {
                "order_processing_request": {
                    "format": "json",
                    "required_fields": ["order_id", "customer_info", "shipping_address"]
                },
                "inventory_alert": {
                    "format": "json",
                    "required_fields": ["sku", "current_stock", "threshold"]
                }
            },
            "notification_channels": ["dashboard", "email", "sms"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1800,
            "estimated_workflow_executions_per_day": 30,
            "memory_storage_requirements_mb": 10,
            "specialized_api_costs": ["Shopify API: $0.03/request", "Stripe API: $0.02/transaction"]
        }
    },
    {
        "template_id": "vertical_004",
        "template_name": "亚马逊广告优化分身",
        "category": "跨境电商_广告",
        "description": "Amazon PPC广告投放与优化专家，精通关键词策略、竞价调整、ROI优化",
        "persona_config": {
            "role": "亚马逊广告优化师",
            "personality": "数据驱动、结果导向、持续优化",
            "expertise": ["关键词研究", "竞价策略", "广告文案优化", "数据分析"],
            "communication_style": "精准专业，数据支撑决策"
        },
        "task_configurations": [
            {
                "task_type": "ad_optimization",
                "schedule": "每日",
                "trigger_condition": "广告表现数据更新",
                "output_target": "outputs/vertical/亚马逊广告/{{date}}_优化建议.json",
                "parameters": {
                    "campaign_types": ["SP", "SB", "SD"],
                    "target_acos": 25,
                    "daily_budget_limit": 100,
                    "optimization_focus": ["keywords", "bids", "negative_targeting"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": True,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": False,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["Amazon Advertising", "Seller Central"],
            "target_regions": ["US", "EU", "JP"],
            "data_sources": ["广告报告API", "搜索词报告", "竞争对手分析工具"],
            "api_keys_needed": ["Amazon Advertising API", "数据分析工具API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["增长中枢", "策略中枢"],
            "message_formats": {
                "ad_performance_analysis": {
                    "format": "json",
                    "required_fields": ["campaign_id", "date_range", "kpi_metrics"]
                },
                "keyword_suggestion_request": {
                    "format": "json",
                    "required_fields": ["product_category", "target_market", "competition_level"]
                }
            },
            "notification_channels": ["dashboard", "push_notification"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1600,
            "estimated_workflow_executions_per_day": 25,
            "memory_storage_requirements_mb": 7,
            "specialized_api_costs": ["Amazon Advertising API: $0.04/request", "关键词工具API: $0.01/query"]
        }
    },
    {
        "template_id": "vertical_005",
        "template_name": "政府补贴申报分身",
        "category": "企业服务_政策申报",
        "description": "国内外政府补贴政策研究与申报专家，精通政策解读、材料准备、申报流程",
        "persona_config": {
            "role": "政府补贴申报顾问",
            "personality": "严谨细致、政策敏感、流程熟悉",
            "expertise": ["政策解读", "材料准备", "申报流程", "资质评估"],
            "communication_style": "正式规范，准确传达政策要求"
        },
        "task_configurations": [
            {
                "task_type": "submission_management",
                "schedule": "每周",
                "trigger_condition": "政策更新或申报周期开始",
                "output_target": "outputs/vertical/政府补贴/{{date}}_申报方案.json",
                "parameters": {
                    "policy_types": ["科技创新", "外贸发展", "人才引进", "节能减排"],
                    "target_regions": ["中国", "欧盟", "美国"],
                    "document_requirements": ["营业执照", "审计报告", "项目计划书"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": False,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": False,
            "trend_prediction": False
        },
        "resource_requirements": {
            "preferred_platforms": ["政府官网", "政策服务平台", "申报系统"],
            "target_regions": ["CN", "EU", "US"],
            "data_sources": ["政策数据库", "申报指南", "过往案例库"],
            "api_keys_needed": ["政策数据库API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["策略中枢", "运营中枢"],
            "message_formats": {
                "policy_matching_request": {
                    "format": "json",
                    "required_fields": ["company_profile", "project_description", "target_region"]
                },
                "document_review_request": {
                    "format": "json",
                    "required_fields": ["document_type", "current_version", "requirements_checklist"]
                }
            },
            "notification_channels": ["dashboard", "email"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 2000,
            "estimated_workflow_executions_per_day": 8,
            "memory_storage_requirements_mb": 12,
            "specialized_api_costs": ["政策数据库API: $0.10/search"]
        }
    },
    {
        "template_id": "vertical_006",
        "template_name": "AI工具评测分身",
        "category": "科技_工具评测",
        "description": "AI工具评测与选型专家，精通各类AI工具功能对比、适用场景分析、性价比评估",
        "persona_config": {
            "role": "AI工具评测专家",
            "personality": "好奇心强、测试严谨、善于总结",
            "expertise": ["功能对比", "性能测试", "适用场景分析", "性价比评估"],
            "communication_style": "客观中立，数据支撑结论"
        },
        "task_configurations": [
            {
                "task_type": "tool_evaluation",
                "schedule": "每周",
                "trigger_condition": "新工具发布或用户需求",
                "output_target": "outputs/vertical/AI工具评测/{{date}}_评测报告.json",
                "parameters": {
                    "tool_categories": ["文本生成", "图像生成", "代码辅助", "视频生成"],
                    "evaluation_criteria": ["功能完整性", "易用性", "性价比", "更新频率"],
                    "testing_methodology": ["实际使用测试", "对比分析", "用户反馈收集"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": True,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": False,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["产品官网", "评测网站", "用户社区"],
            "target_regions": ["全球"],
            "data_sources": ["工具官方文档", "用户评测", "性能测试数据"],
            "api_keys_needed": ["评测平台API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["创作中枢", "策略中枢"],
            "message_formats": {
                "tool_comparison_request": {
                    "format": "json",
                    "required_fields": ["tool_category", "use_case", "budget_constraint"]
                },
                "evaluation_summary_request": {
                    "format": "json",
                    "required_fields": ["tool_list", "evaluation_scope", "output_format"]
                }
            },
            "notification_channels": ["dashboard", "newsletter"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1400,
            "estimated_workflow_executions_per_day": 15,
            "memory_storage_requirements_mb": 6,
            "specialized_api_costs": ["评测平台API: $0.05/request"]
        }
    },
    {
        "template_id": "vertical_007",
        "template_name": "跨境电商物流优化分身",
        "category": "跨境电商_物流",
        "description": "跨境电商物流优化专家，精通国际运输、清关流程、成本控制、时效管理",
        "persona_config": {
            "role": "跨境物流优化师",
            "personality": "逻辑性强、注重细节、成本敏感",
            "expertise": ["运输方案优化", "清关流程管理", "成本控制", "时效预测"],
            "communication_style": "专业务实，解决方案导向"
        },
        "task_configurations": [
            {
                "task_type": "logistics_optimization",
                "schedule": "每日",
                "trigger_condition": "订单生成或运输状态变化",
                "output_target": "outputs/vertical/跨境电商物流/{{date}}_优化方案.json",
                "parameters": {
                    "transport_modes": ["空运", "海运", "铁路", "快递"],
                    "target_regions": ["US", "EU", "AU", "东南亚"],
                    "optimization_goals": ["成本最低", "时效最快", "平衡方案"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": False,
            "account_operation": True,
            "financial_analysis": True,
            "supply_chain_analysis": True,
            "trend_prediction": False
        },
        "resource_requirements": {
            "preferred_platforms": ["物流公司平台", "海关系统", "电商平台"],
            "target_regions": ["全球"],
            "data_sources": ["运费报价", "清关要求", "时效数据", "追踪信息"],
            "api_keys_needed": ["物流API", "海关数据API", "追踪API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["运营中枢", "供应链中枢"],
            "message_formats": {
                "shipping_quote_request": {
                    "format": "json",
                    "required_fields": ["origin", "destination", "package_details", "urgency"]
                },
                "customs_clearance_assistance": {
                    "format": "json",
                    "required_fields": ["product_description", "value_declaration", "document_checklist"]
                }
            },
            "notification_channels": ["dashboard", "email"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1700,
            "estimated_workflow_executions_per_day": 18,
            "memory_storage_requirements_mb": 9,
            "specialized_api_costs": ["物流API: $0.03/request", "海关API: $0.05/query"]
        }
    },
    {
        "template_id": "vertical_008",
        "template_name": "社交媒体广告投放分身",
        "category": "数字营销_广告",
        "description": "社交媒体广告投放专家，精通Facebook/Instagram/TikTok广告平台，擅长受众定位、创意优化、效果分析",
        "persona_config": {
            "role": "社交媒体广告优化师",
            "personality": "创意与数据并重、测试驱动、结果导向",
            "expertise": ["受众定位", "广告创意", "预算分配", "效果分析"],
            "communication_style": "生动专业，数据支撑创意"
        },
        "task_configurations": [
            {
                "task_type": "ad_campaign_management",
                "schedule": "每日",
                "trigger_condition": "广告表现数据更新",
                "output_target": "outputs/vertical/社交媒体广告/{{date}}_投放报告.json",
                "parameters": {
                    "platforms": ["Facebook", "Instagram", "TikTok", "Twitter"],
                    "campaign_objectives": ["品牌认知", "转化", "流量", "互动"],
                    "optimization_metrics": ["CPC", "CTR", "CPA", "ROAS"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": True,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": False,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["Facebook Ads Manager", "TikTok Ads", "Google Ads"],
            "target_regions": ["全球"],
            "data_sources": ["广告平台API", "分析工具", "行业基准数据"],
            "api_keys_needed": ["Facebook Marketing API", "TikTok Ads API", "分析工具API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["增长中枢", "创作中枢"],
            "message_formats": {
                "audience_insights_request": {
                    "format": "json",
                    "required_fields": ["target_demographics", "interest_categories", "behavior_patterns"]
                },
                "creative_testing_request": {
                    "format": "json",
                    "required_fields": ["ad_variations", "test_audience", "success_metrics"]
                }
            },
            "notification_channels": ["dashboard", "push_notification"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1900,
            "estimated_workflow_executions_per_day": 22,
            "memory_storage_requirements_mb": 11,
            "specialized_api_costs": ["Facebook API: $0.02/request", "TikTok API: $0.03/request"]
        }
    },
    {
        "template_id": "vertical_009",
        "template_name": "网红KOL对接分身",
        "category": "数字营销_红人营销",
        "description": "网红/KOL对接与管理专家，精通红人筛选、合作谈判、内容审核、效果追踪",
        "persona_config": {
            "role": "红人营销经理",
            "personality": "人际敏感、谈判能力强、注重关系维护",
            "expertise": ["红人筛选", "合作谈判", "内容审核", "效果追踪"],
            "communication_style": "亲和专业，平衡品牌与红人需求"
        },
        "task_configurations": [
            {
                "task_type": "influencer_management",
                "schedule": "每日",
                "trigger_condition": "合作需求或红人更新",
                "output_target": "outputs/vertical/网红对接/{{date}}_合作进展.json",
                "parameters": {
                    "platforms": ["Instagram", "YouTube", "TikTok", "小红书"],
                    "influencer_tiers": ["纳米级", "微型", "中型", "大型"],
                    "collaboration_types": ["赞助内容", "产品评测", "直播带货", "品牌代言"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": True,
            "content_creation": False,
            "account_operation": False,
            "financial_analysis": True,
            "supply_chain_analysis": False,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["红人营销平台", "社交媒体", "数据分析工具"],
            "target_regions": ["全球"],
            "data_sources": ["红人数据库", "合作历史", "效果指标", "受众分析"],
            "api_keys_needed": ["红人平台API", "社交媒体API", "分析工具API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["增长中枢", "创作中枢"],
            "message_formats": {
                "influencer_search_request": {
                    "format": "json",
                    "required_fields": ["niche", "target_audience", "budget_range", "content_style"]
                },
                "collaboration_proposal_request": {
                    "format": "json",
                    "required_fields": ["influencer_id", "campaign_objectives", "deliverables", "compensation"]
                }
            },
            "notification_channels": ["dashboard", "email", "messaging"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 2100,
            "estimated_workflow_executions_per_day": 10,
            "memory_storage_requirements_mb": 15,
            "specialized_api_costs": ["红人平台API: $0.10/search", "分析工具API: $0.05/request"]
        }
    },
    {
        "template_id": "vertical_010",
        "template_name": "海外仓库存管理分身",
        "category": "跨境电商_仓储",
        "description": "海外仓库存管理专家，精通库存预测、补货策略、仓储优化、成本控制",
        "persona_config": {
            "role": "海外仓库存经理",
            "personality": "计划性强、注重数据、风险意识高",
            "expertise": ["库存预测", "补货策略", "仓储优化", "成本控制"],
            "communication_style": "严谨精确，数据驱动决策"
        },
        "task_configurations": [
            {
                "task_type": "inventory_management",
                "schedule": "每日",
                "trigger_condition": "库存变化或销售数据更新",
                "output_target": "outputs/vertical/海外仓库存/{{date}}_管理报告.json",
                "parameters": {
                    "warehouse_locations": ["美国", "欧洲", "澳大利亚", "日本"],
                    "forecasting_method": ["时间序列", "机器学习", "人工调整"],
                    "reorder_point_calculation": ["安全库存", "提前期", "服务水平"]
                }
            }
        ],
        "capability_matrix": {
            "data_crawling": True,
            "business_matching": False,
            "content_creation": False,
            "account_operation": True,
            "financial_analysis": True,
            "supply_chain_analysis": True,
            "trend_prediction": True
        },
        "resource_requirements": {
            "preferred_platforms": ["仓储管理系统", "电商平台", "物流平台"],
            "target_regions": ["全球"],
            "data_sources": ["库存数据", "销售数据", "物流数据", "市场趋势"],
            "api_keys_needed": ["仓储管理API", "电商平台API", "物流API"]
        },
        "collaboration_protocol": {
            "primary_partners": ["运营中枢", "供应链中枢"],
            "message_formats": {
                "inventory_forecast_request": {
                    "format": "json",
                    "required_fields": ["sku_list", "historical_period", "forecast_horizon", "confidence_level"]
                },
                "reorder_suggestion_request": {
                    "format": "json",
                    "required_fields": ["current_stock", "lead_time", "demand_forecast", "service_level_target"]
                }
            },
            "notification_channels": ["dashboard", "email", "sms"]
        },
        "cost_profile": {
            "estimated_tokens_per_conversation": 1800,
            "estimated_workflow_executions_per_day": 15,
            "memory_storage_requirements_mb": 10,
            "specialized_api_costs": ["仓储管理API: $0.02/request", "物流API: $0.03/request"]
        }
    }
]

def main():
    """生成所有模板文件"""
    print(f"开始生成垂直领域分身模板，输出目录: {OUTPUT_DIR}")
    
    generated_files = []
    
    for template in TEMPLATES:
        template_id = template["template_id"]
        template_name = template["template_name"]
        file_name = f"{template_name}.json"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        
        # 格式化JSON
        json_content = json.dumps(template, ensure_ascii=False, indent=2)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        generated_files.append(file_path)
        print(f"  ✓ 生成: {file_name}")
    
    # 生成模板索引文件
    index_data = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "template_count": len(TEMPLATES),
        "templates": [
            {
                "template_id": t["template_id"],
                "template_name": t["template_name"],
                "category": t["category"],
                "description": t["description"],
                "file_name": f"{t['template_name']}.json"
            }
            for t in TEMPLATES
        ]
    }
    
    index_path = os.path.join(OUTPUT_DIR, "模板索引.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    generated_files.append(index_path)
    print(f"  ✓ 生成: 模板索引.json")
    
    # 生成验证脚本
    validation_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# 验证脚本内容会在下面继续
    validation_script += """
\"\"\"
垂直分身模板验证脚本
检查所有模板文件的格式正确性和字段完整性
\"\"\"

import json
import os
import sys

TEMPLATE_DIR = "outputs/分身模板库"

# 必需字段定义
REQUIRED_FIELDS = {
    "template_id": str,
    "template_name": str,
    "category": str,
    "description": str,
    "persona_config": dict,
    "task_configurations": list,
    "capability_matrix": dict,
    "resource_requirements": dict,
    "collaboration_protocol": dict,
    "cost_profile": dict
}

PERSONA_CONFIG_FIELDS = ["role", "personality", "expertise", "communication_style"]

def validate_template(file_path):
    \"\"\"验证单个模板文件\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON解析失败: {e}"
    except Exception as e:
        return False, f"文件读取失败: {e}"
    
    # 检查必需字段
    missing_fields = []
    for field, field_type in REQUIRED_FIELDS.items():
        if field not in data:
            missing_fields.append(field)
        elif not isinstance(data[field], field_type):
            return False, f"字段 '{field}' 类型错误，期望 {field_type}，实际 {type(data[field])}"
    
    if missing_fields:
        return False, f"缺少必需字段: {missing_fields}"
    
    # 检查 persona_config
    persona = data["persona_config"]
    missing_persona_fields = [f for f in PERSONA_CONFIG_FIELDS if f not in persona]
    if missing_persona_fields:
        return False, f"persona_config 缺少字段: {missing_persona_fields}"
    
    # 检查 task_configurations
    tasks = data["task_configurations"]
    if len(tasks) == 0:
        return False, "task_configurations 不能为空"
    
    for i, task in enumerate(tasks):
        required_task_fields = ["task_type", "schedule", "trigger_condition", "output_target", "parameters"]
        missing_task_fields = [f for f in required_task_fields if f not in task]
        if missing_task_fields:
            return False, f"任务配置 {i} 缺少字段: {missing_task_fields}"
    
    return True, "验证通过"

def main():
    \"\"\"主函数\"\"\"
    if not os.path.exists(TEMPLATE_DIR):
        print(f"❌ 模板目录不存在: {TEMPLATE_DIR}")
        sys.exit(1)
    
    print(f"开始验证模板文件，目录: {TEMPLATE_DIR}")
    
    template_files = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith('.json') and f != '模板索引.json']
    
    if len(template_files) == 0:
        print("❌ 未找到模板文件")
        sys.exit(1)
    
    validation_results = []
    all_valid = True
    
    for template_file in template_files:
        file_path = os.path.join(TEMPLATE_DIR, template_file)
        is_valid, message = validate_template(file_path)
        
        if is_valid:
            print(f"  ✓ {template_file}: {message}")
        else:
            print(f"  ✗ {template_file}: {message}")
            all_valid = False
        
        validation_results.append({
            "file": template_file,
            "valid": is_valid,
            "message": message
        })
    
    # 生成验证报告
    report = {
        "validation_time": datetime.now().isoformat(),
        "total_templates": len(template_files),
        "valid_count": sum(1 for r in validation_results if r["valid"]),
        "invalid_count": sum(1 for r in validation_results if not r["valid"]),
        "results": validation_results
    }
    
    report_path = os.path.join(TEMPLATE_DIR, "验证报告.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\\n验证报告已保存: {report_path}")
    
    if all_valid:
        print("🎉 所有模板验证通过！")
        sys.exit(0)
    else:
        print("❌ 部分模板验证失败，请检查上述错误")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    main()
"""
    
    validation_path = os.path.join(OUTPUT_DIR, "validate_templates.py")
    with open(validation_path, 'w', encoding='utf-8') as f:
        f.write(validation_script)
    
    generated_files.append(validation_path)
    print(f"  ✓ 生成: validate_templates.py")
    
    print(f"\\n✅ 模板生成完成！共生成 {len(generated_files)} 个文件")
    print(f"   模板目录: {OUTPUT_DIR}")
    print(f"   索引文件: 模板索引.json")
    print(f"   验证脚本: validate_templates.py")

if __name__ == "__main__":
    main()