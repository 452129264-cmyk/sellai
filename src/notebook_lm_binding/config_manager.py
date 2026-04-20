#!/usr/bin/env python3
"""
Notebook LM绑定配置管理器

此模块用于统一管理无限分身系统与Notebook LM知识底座的绑定配置，
包括配置验证、状态监控、同步管理等功能。
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NotebookLMBindingConfig:
    """Notebook LM绑定配置"""
    
    # 基本配置
    enabled: bool = True
    knowledge_base_id: str = "kb_global_sellai"
    
    # 检索策略
    retrieval_strategy: str = "priority_first"  # priority_first, hybrid, knowledge_only
    max_retrieval_results: int = 5
    min_relevance_score: float = 0.3
    
    # 知识驱动功能
    brand_consistency_check: bool = True
    fact_verification: bool = True
    context_enhancement: bool = True
    archive_results: bool = True
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    
    # 同步配置
    auto_sync_interval_hours: int = 24
    last_sync_time: Optional[str] = None
    sync_status: str = "pending"  # pending, in_progress, completed, failed
    
    # 元数据
    created_at: str = ""
    last_updated: str = ""
    version: str = "1.0.0"


class ConfigManager:
    """
    配置管理器
    
    负责Notebook LM绑定配置的加载、验证、保存和管理。
    """
    
    def __init__(self, config_dir: str = "configs/notebook_lm_binding"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        self.global_config_file = os.path.join(config_dir, "global_config.json")
        self.avatar_bindings_file = os.path.join(config_dir, "avatar_bindings.json")
        self.sync_history_file = os.path.join(config_dir, "sync_history.json")
        
        # 加载配置
        self.global_config = self._load_global_config()
        self.avatar_bindings = self._load_avatar_bindings()
        
        logger.info(f"配置管理器初始化完成，配置目录: {config_dir}")
    
    def _load_global_config(self) -> NotebookLMBindingConfig:
        """加载全局配置"""
        if os.path.exists(self.global_config_file):
            try:
                with open(self.global_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 转换回数据类
                return NotebookLMBindingConfig(**data)
                
            except Exception as e:
                logger.error(f"加载全局配置失败: {str(e)}")
        
        # 创建默认配置
        default_config = NotebookLMBindingConfig(
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        
        return default_config
    
    def _load_avatar_bindings(self) -> Dict[str, Dict[str, Any]]:
        """加载分身绑定配置"""
        if os.path.exists(self.avatar_bindings_file):
            try:
                with open(self.avatar_bindings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载分身绑定配置失败: {str(e)}")
        
        return {}
    
    def save_global_config(self, config: Optional[NotebookLMBindingConfig] = None) -> bool:
        """
        保存全局配置
        
        Args:
            config: 配置对象，None则保存当前配置
            
        Returns:
            保存是否成功
        """
        try:
            if config:
                self.global_config = config
            
            # 更新时间戳
            self.global_config.last_updated = datetime.now().isoformat()
            
            # 转换为字典并保存
            with open(self.global_config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.global_config), f, ensure_ascii=False, indent=2)
            
            logger.info("全局配置已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存全局配置失败: {str(e)}")
            return False
    
    def save_avatar_bindings(self) -> bool:
        """保存分身绑定配置"""
        try:
            with open(self.avatar_bindings_file, 'w', encoding='utf-8') as f:
                json.dump(self.avatar_bindings, f, ensure_ascii=False, indent=2)
            
            logger.info("分身绑定配置已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存分身绑定配置失败: {str(e)}")
            return False
    
    def register_avatar_binding(self, avatar_id: str, binding_config: Dict[str, Any]) -> bool:
        """
        注册分身绑定
        
        Args:
            avatar_id: 分身ID
            binding_config: 绑定配置
            
        Returns:
            注册是否成功
        """
        try:
            # 验证基本配置
            required_fields = ["knowledge_base_id", "retrieval_strategy", "enabled"]
            for field in required_fields:
                if field not in binding_config:
                    binding_config[field] = self.global_config.__dict__.get(field)
            
            # 添加元数据
            binding_config.update({
                "registered_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "binding_version": "1.0.0",
                "sync_status": "pending"
            })
            
            # 保存
            self.avatar_bindings[avatar_id] = binding_config
            
            # 更新统计
            self._update_binding_statistics()
            
            logger.info(f"分身绑定已注册: {avatar_id}")
            return self.save_avatar_bindings()
            
        except Exception as e:
            logger.error(f"注册分身绑定失败 {avatar_id}: {str(e)}")
            return False
    
    def update_avatar_activity(self, avatar_id: str) -> bool:
        """
        更新分身活动时间
        
        Args:
            avatar_id: 分身ID
            
        Returns:
            更新是否成功
        """
        if avatar_id in self.avatar_bindings:
            self.avatar_bindings[avatar_id]["last_active"] = datetime.now().isoformat()
            
            # 统计任务数
            if "task_count" not in self.avatar_bindings[avatar_id]:
                self.avatar_bindings[avatar_id]["task_count"] = 1
            else:
                self.avatar_bindings[avatar_id]["task_count"] += 1
            
            return self.save_avatar_bindings()
        
        return False
    
    def get_avatar_binding(self, avatar_id: str) -> Optional[Dict[str, Any]]:
        """
        获取分身绑定配置
        
        Args:
            avatar_id: 分身ID
            
        Returns:
            绑定配置，如果不存在则返回None
        """
        return self.avatar_bindings.get(avatar_id)
    
    def list_bound_avatars(self) -> List[str]:
        """列出所有已绑定的分身ID"""
        return list(self.avatar_bindings.keys())
    
    def get_binding_statistics(self) -> Dict[str, Any]:
        """获取绑定统计信息"""
        stats = {
            "total_bound_avatars": len(self.avatar_bindings),
            "enabled_avatars": 0,
            "recently_active_avatars": 0,
            "by_template": {},
            "by_category": {},
            "sync_status_summary": {
                "pending": 0,
                "completed": 0,
                "failed": 0
            }
        }
        
        now = datetime.now()
        
        for avatar_id, binding in self.avatar_bindings.items():
            # 统计启用状态
            if binding.get("enabled", True):
                stats["enabled_avatars"] += 1
            
            # 统计近期活动（7天内）
            last_active_str = binding.get("last_active")
            if last_active_str:
                try:
                    last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
                    if (now - last_active).days < 7:
                        stats["recently_active_avatars"] += 1
                except:
                    pass
            
            # 按模板统计
            template_id = binding.get("template_id", "unknown")
            if template_id not in stats["by_template"]:
                stats["by_template"][template_id] = 0
            stats["by_template"][template_id] += 1
            
            # 按类别统计
            category = binding.get("category", "general")
            if category not in stats["by_category"]:
                stats["by_category"][category] = 0
            stats["by_category"][category] += 1
            
            # 同步状态统计
            sync_status = binding.get("sync_status", "pending")
            if sync_status in stats["sync_status_summary"]:
                stats["sync_status_summary"][sync_status] += 1
        
        return stats
    
    def _update_binding_statistics(self):
        """更新绑定统计"""
        stats = self.get_binding_statistics()
        
        stats_file = os.path.join(self.config_dir, "binding_statistics.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    
    def record_sync_event(self, event_type: str, 
                         target_agent: str = "sellai_test",
                         status: str = "completed",
                         details: Optional[Dict[str, Any]] = None,
                         error_message: Optional[str] = None) -> bool:
        """
        记录同步事件
        
        Args:
            event_type: 事件类型，如 "config_sync", "knowledge_import", "capability_calibration"
            target_agent: 目标代理，如 "sellai_test"
            status: 状态，如 "pending", "in_progress", "completed", "failed"
            details: 详细信息
            error_message: 错误信息
            
        Returns:
            记录是否成功
        """
        try:
            # 加载同步历史
            sync_history = []
            if os.path.exists(self.sync_history_file):
                with open(self.sync_history_file, 'r', encoding='utf-8') as f:
                    sync_history = json.load(f)
            
            # 创建事件记录
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "target_agent": target_agent,
                "status": status,
                "details": details or {},
                "error_message": error_message
            }
            
            # 添加到历史
            sync_history.append(event)
            
            # 只保留最近100条记录
            if len(sync_history) > 100:
                sync_history = sync_history[-100:]
            
            # 保存
            with open(self.sync_history_file, 'w', encoding='utf-8') as f:
                json.dump(sync_history, f, ensure_ascii=False, indent=2)
            
            # 更新全局配置的同步时间
            if status == "completed" and event_type == "config_sync":
                self.global_config.last_sync_time = event["timestamp"]
                self.global_config.sync_status = "completed"
                self.save_global_config()
            
            logger.info(f"同步事件已记录: {event_type} -> {target_agent} ({status})")
            return True
            
        except Exception as e:
            logger.error(f"记录同步事件失败: {str(e)}")
            return False
    
    def validate_binding_configuration(self) -> Dict[str, Any]:
        """
        验证绑定配置的完整性和有效性
        
        Returns:
            验证结果
        """
        validation_result = {
            "status": "passed",
            "checks": [],
            "issues": [],
            "summary": {}
        }
        
        # 检查1: 全局配置是否有效
        if not self.global_config.enabled:
            validation_result["checks"].append({
                "name": "global_config_enabled",
                "status": "warning",
                "message": "全局绑定配置未启用"
            })
        else:
            validation_result["checks"].append({
                "name": "global_config_enabled",
                "status": "passed",
                "message": "全局绑定配置已启用"
            })
        
        # 检查2: 是否有绑定的分身
        bound_avatars = len(self.avatar_bindings)
        if bound_avatars == 0:
            validation_result["checks"].append({
                "name": "bound_avatars",
                "status": "warning",
                "message": "暂无分身绑定配置"
            })
        else:
            validation_result["checks"].append({
                "name": "bound_avatars",
                "status": "passed",
                "message": f"已绑定 {bound_avatars} 个分身"
            })
        
        # 检查3: 分身绑定配置完整性
        incomplete_bindings = []
        for avatar_id, binding in self.avatar_bindings.items():
            required_fields = ["knowledge_base_id", "retrieval_strategy"]
            missing_fields = []
            
            for field in required_fields:
                if field not in binding:
                    missing_fields.append(field)
            
            if missing_fields:
                incomplete_bindings.append({
                    "avatar_id": avatar_id,
                    "missing_fields": missing_fields
                })
        
        if incomplete_bindings:
            validation_result["checks"].append({
                "name": "binding_config_completeness",
                "status": "failed",
                "message": f"{len(incomplete_bindings)} 个分身绑定配置不完整",
                "details": incomplete_bindings
            })
            validation_result["issues"].extend(incomplete_bindings)
        else:
            validation_result["checks"].append({
                "name": "binding_config_completeness",
                "status": "passed",
                "message": "所有分身绑定配置完整"
            })
        
        # 检查4: 同步状态
        if self.global_config.last_sync_time:
            try:
                last_sync = datetime.fromisoformat(
                    self.global_config.last_sync_time.replace('Z', '+00:00')
                )
                sync_age_days = (datetime.now() - last_sync).days
                
                if sync_age_days > 1:  # 超过1天未同步
                    validation_result["checks"].append({
                        "name": "sync_recency",
                        "status": "warning",
                        "message": f"上次同步已过去 {sync_age_days} 天"
                    })
                else:
                    validation_result["checks"].append({
                        "name": "sync_recency",
                        "status": "passed",
                        "message": "同步状态良好"
                    })
            except:
                validation_result["checks"].append({
                    "name": "sync_recency",
                    "status": "warning",
                    "message": "上次同步时间格式无效"
                })
        
        # 更新状态
        if any(check["status"] == "failed" for check in validation_result["checks"]):
            validation_result["status"] = "failed"
        elif any(check["status"] == "warning" for check in validation_result["checks"]):
            validation_result["status"] = "warning"
        
        # 生成摘要
        validation_result["summary"] = {
            "total_checks": len(validation_result["checks"]),
            "passed_checks": sum(1 for check in validation_result["checks"] if check["status"] == "passed"),
            "warning_checks": sum(1 for check in validation_result["checks"] if check["status"] == "warning"),
            "failed_checks": sum(1 for check in validation_result["checks"] if check["status"] == "failed"),
            "total_issues": len(validation_result["issues"])
        }
        
        return validation_result
    
    def generate_configuration_report(self) -> Dict[str, Any]:
        """
        生成完整的配置报告
        
        Returns:
            配置报告
        """
        validation = self.validate_binding_configuration()
        statistics = self.get_binding_statistics()
        
        report = {
            "report_type": "notebook_lm_binding_configuration",
            "generated_at": datetime.now().isoformat(),
            "global_config": asdict(self.global_config),
            "binding_statistics": statistics,
            "validation_result": validation,
            "recommendations": self._generate_recommendations(validation, statistics),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self, validation: Dict[str, Any],
                                statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成改进建议"""
        recommendations = []
        
        # 建议1: 增加绑定分身数量
        if statistics["total_bound_avatars"] < 5:
            recommendations.append({
                "priority": "medium",
                "category": "coverage",
                "title": "增加绑定分身数量",
                "description": f"当前只有 {statistics['total_bound_avatars']} 个分身绑定，建议增加至至少10个以提高系统覆盖率",
                "action": "执行分身创建和绑定流程"
            })
        
        # 建议2: 解决配置不完整问题
        if validation["issues"]:
            recommendations.append({
                "priority": "high",
                "category": "configuration",
                "title": "修复绑定配置不完整问题",
                "description": f"有 {len(validation['issues'])} 个分身绑定配置不完整，需补充缺失字段",
                "action": "检查并更新不完整的绑定配置"
            })
        
        # 建议3: 启用未启用的分身
        if statistics["enabled_avatars"] < statistics["total_bound_avatars"]:
            disabled_count = statistics["total_bound_avatars"] - statistics["enabled_avatars"]
            recommendations.append({
                "priority": "low",
                "category": "performance",
                "title": "启用已绑定的分身",
                "description": f"有 {disabled_count} 个已绑定分身未启用，启用后可以提高系统性能",
                "action": "检查并启用所有已绑定分身"
            })
        
        # 建议4: 更新同步状态
        if self.global_config.sync_status != "completed":
            recommendations.append({
                "priority": "high",
                "category": "synchronization",
                "title": "完成配置同步",
                "description": "当前配置同步状态未完成，需确保所有配置已同步到目标代理",
                "action": "执行配置同步流程"
            })
        
        return recommendations
    
    def export_configuration(self, export_dir: str = "outputs/配置导出") -> str:
        """
        导出绑定配置
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出文件路径
        """
        try:
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = os.path.join(export_dir, f"notebook_lm_binding_config_{timestamp}.json")
            
            # 准备导出数据
            export_data = {
                "export_type": "notebook_lm_binding_configuration",
                "exported_at": datetime.now().isoformat(),
                "global_config": asdict(self.global_config),
                "avatar_bindings": self.avatar_bindings,
                "statistics": self.get_binding_statistics(),
                "version": "1.0.0"
            }
            
            # 保存
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"绑定配置已导出: {export_file}")
            
            # 同时生成配置报告
            report = self.generate_configuration_report()
            report_file = os.path.join(export_dir, f"binding_config_report_{timestamp}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置报告已生成: {report_file}")
            
            return export_file
            
        except Exception as e:
            logger.error(f"导出配置失败: {str(e)}")
            return ""


def main():
    """主函数：配置管理器演示"""
    print("🚀 Notebook LM绑定配置管理器")
    print("=" * 50)
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    print("📊 配置状态:")
    print(f"   全局绑定启用: {'✅' if config_manager.global_config.enabled else '❌'}")
    print(f"   知识库ID: {config_manager.global_config.knowledge_base_id}")
    print(f"   检索策略: {config_manager.global_config.retrieval_strategy}")
    print(f"   最后同步: {config_manager.global_config.last_sync_time or '从未同步'}")
    print(f"   绑定分身数: {len(config_manager.avatar_bindings)}")
    
    print("\n🔍 执行配置验证...")
    validation_result = config_manager.validate_binding_configuration()
    
    print(f"\n✅ 验证完成，状态: {validation_result['status'].upper()}")
    print("=" * 50)
    
    summary = validation_result.get("summary", {})
    print(f"📈 验证统计:")
    print(f"   总检查项: {summary.get('total_checks', 0)}")
    print(f"   通过项: {summary.get('passed_checks', 0)}")
    print(f"   警告项: {summary.get('warning_checks', 0)}")
    print(f"   失败项: {summary.get('failed_checks', 0)}")
    print(f"   问题总数: {summary.get('total_issues', 0)}")
    
    # 显示问题详情
    if validation_result["issues"]:
        print("\n⚠️  发现的问题:")
        for issue in validation_result["issues"][:5]:  # 最多显示5个
            if isinstance(issue, dict):
                if "avatar_id" in issue:
                    print(f"   • 分身 {issue['avatar_id']}: {issue.get('missing_fields', '配置不完整')}")
    
    # 生成报告
    print("\n📝 生成配置报告...")
    report_dir = "outputs/配置报告"
    export_file = config_manager.export_configuration(export_dir=report_dir)
    
    if export_file:
        print(f"📄 配置导出: {os.path.abspath(export_file)}")
        print(f"📊 配置报告: {os.path.abspath(export_file.replace('_config_', '_config_report_'))}")
    
    print("\n🎯 下一步建议:")
    recommendations = config_manager.generate_configuration_report().get("recommendations", [])
    for rec in recommendations[:3]:
        print(f"   • [{rec.get('priority', 'normal').upper()}] {rec.get('title', '未命名建议')}")
    
    print("\n✅ 配置管理完成!")


if __name__ == "__main__":
    main()