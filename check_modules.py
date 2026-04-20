#!/usr/bin/env python3
"""
SellAI v3.2.0 启动检查脚本
===========================
自动检测所有模块状态，跳过无法加载的模块
"""

import sys
import importlib

def check_module(module_path, class_name=None):
    """检查模块是否可导入"""
    try:
        module = importlib.import_module(module_path)
        if class_name:
            return hasattr(module, class_name), getattr(module, class_name, None)
        return True, module
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("SellAI v3.2.0 模块状态检查")
    print("=" * 60)
    
    # v2.6.0 核心模块
    v26_modules = {
        "自我进化大脑": ("src.self_evolution_brain", "SelfEvolutionBrainController"),
        "Memory V2": ("src.memory_v2_integration", "MemoryV2IntegrationManager"),
        "全局调度器": ("src.global_orchestrator", "CoreScheduler"),
        "HyperHorse视频": ("src.hyperhorse", "HyperHorseEngine"),
    }
    
    # v2.3.0 基础模块
    v23_modules = {
        "AI谈判引擎": ("src.ai_negotiation_engine", "AINegotiationEngine"),
        "AIGC服务中心": ("src.aigc_service_center", "AIGCServiceCenter"),
        "电商集成": ("src.banana_ecommerce_integration", "EcommerceIntegrationManager"),
        "人脸一致性": ("src.banana_face_consistency", "BananaImageGenerationEngine"),
        "Notebook LM": ("src.notebook_lm_binding", "NotebookLMBindingController"),
        "原创性检测": ("src.originality_compliance", "OriginalityDetectionService"),
        "风控合规": ("src.risk_compliance", "ComplianceCheckService"),
    }
    
    # v3.0.0 业务模块
    v30_modules = {
        "全域商业大脑": ("src.global_business_brain", "GlobalBusinessBrain"),
        "AI分身市场": ("src.avatar_market", "AvatarMarket"),
        "达人外联引擎": ("src.influencer_outreach_engine", "InfluencerOutreachEngine"),
        "社交关系管理": ("src.social_relationship_manager", "SocialRelationshipManager"),
        "安全系统": ("src.multi_layer_security", "MultiLayerSecurity"),
        "健康监控": ("src.health_monitor", "HealthMonitor"),
        "邀请裂变": ("src.invitation_fission_manager", "InvitationFissionManager"),
        "任务调度": ("src.task_scheduler", "TaskScheduler"),
        "短视频分发": ("src.short_video_distributor", "ShortVideoDistributor"),
        "聊天系统": ("src.chat_system", "ChatManager"),
        "佣金计算": ("src.commission_calculator", "CommissionCalculator"),
        "数据同步": ("src.network_data_sync", "NetworkDataSync"),
        "行业资源": ("src.industry_resource_importer", "IndustryResourceImporter"),
    }
    
    # v3.2.0 新增模块
    v32_modules = {
        "权限管理": ("src.permission_manager", "PermissionManager"),
        "任务分发": ("src.task_dispatcher", "TaskDispatcher"),
        "社交API": ("src.social_relationship_api", "SocialRelationshipAPI"),
        "共享状态": ("src.shared_state_manager", "SharedStateManager"),
        "聊天记忆桥": ("src.chat_memory_bridge", "ChatMemoryBridge"),
        "达人面板": ("src.add_influencer_panel", "InfluencerPanelManager"),
        "邀请面板": ("src.add_invitation_panel", "InvitationPanelManager"),
        "智能路由": ("src.smart_router", "SmartRouter"),
        "性能基准": ("src.performance_benchmark", "PerformanceBenchmark"),
        "负载均衡": ("src.load_balanced_allocator", "LoadBalancedAllocator"),
        "达人群发": ("src.influencer_mass_messenger", "InfluencerMassMessenger"),
        "网络服务": ("src.sellai_network_server", "SellaiNetworkServer"),
        "网络客户端": ("src.sellai_network_client", "SellaiNetworkClient"),
        "语音合成": ("src.voice_synthesis_service", "VoiceSynthesisService"),
        "语音识别": ("src.voice_recognition_service", "VoiceRecognitionService"),
        "语音对话": ("src.voice_conversation_engine", "VoiceConversationEngine"),
        "实时音频": ("src.real_time_audio_stream", "RealTimeAudioStream"),
        "MemoryV2索引": ("src.memory_v2_indexer", "MemoryV2Indexer"),
        "MemoryV2验证": ("src.memory_v2_validator", "MemoryV2Validator"),
        "知识分身": ("src.knowledge_driven_avatar", "KnowledgeDrivenAvatar"),
    }
    
    all_categories = {
        "v2.6.0 核心模块": v26_modules,
        "v2.3.0 基础模块": v23_modules,
        "v3.0.0 业务模块": v30_modules,
        "v3.2.0 新增模块": v32_modules,
    }
    
    total_active = 0
    total_modules = 0
    
    for category, modules in all_categories.items():
        print(f"\n{category}:")
        print("-" * 40)
        
        for name, (path, cls) in modules.items():
            total_modules += 1
            available, result = check_module(path, cls)
            status = "✅ 已激活" if available else "⚠️ 未激活"
            print(f"  {name}: {status}")
            if not available:
                print(f"    原因: {result}")
            else:
                total_active += 1
    
    print("\n" + "=" * 60)
    print(f"模块激活率: {total_active}/{total_modules} ({100*total_active//total_modules}%)")
    print("=" * 60)
    
    if total_active == total_modules:
        print("🎉 所有模块已成功激活!")
        return 0
    else:
        print(f"⚠️ 还有 {total_modules - total_active} 个模块未激活")
        print("请检查依赖是否安装: pip install -r requirements_complete.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
