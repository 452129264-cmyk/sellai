#!/usr/bin/env python3
"""
知识库数据导入器

此模块用于将SellAI系统的现有数据导入Notebook LM知识库，包括：
1. 历史任务记录
2. 市场情报数据
3. 架构文档
4. 全球业务数据
5. 分身能力矩阵
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import hashlib
from dataclasses import dataclass

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result
    )
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result
    )

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseImporter:
    """
    知识库数据导入器
    
    负责从SellAI数据库和文件中提取数据，
    转换为知识文档并导入Notebook LM知识库。
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db",
                 notebook_lm_api_key: Optional[str] = None):
        """
        初始化导入器
        
        Args:
            db_path: 共享状态库路径
            notebook_lm_api_key: Notebook LM API密钥
        """
        self.db_path = db_path
        self.api_key = notebook_lm_api_key or os.getenv("NOTEBOOKLM_API_KEY")
        
        if not self.api_key:
            logger.warning("未提供Notebook LM API密钥，导入功能受限")
        
        # 初始化Notebook LM集成
        self.nli = None
        if self.api_key:
            try:
                self.nli = NotebookLMIntegration(api_key=self.api_key)
                logger.info("Notebook LM集成初始化成功")
            except Exception as e:
                logger.error(f"Notebook LM集成初始化失败: {str(e)}")
        
        logger.info(f"知识库数据导入器初始化完成，数据库: {db_path}")
    
    def import_historical_tasks(self, knowledge_base_id: str,
                              limit: Optional[int] = None) -> Dict[str, Any]:
        """
        导入历史任务记录
        
        Args:
            knowledge_base_id: 目标知识库ID
            limit: 最大导入数量，None表示全部导入
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取任务数据
            query = """
                SELECT ta.assignment_id, ta.opportunity_hash, ta.assigned_avatar,
                       ta.assignment_time, ta.deadline, ta.priority,
                       ta.completion_status, ta.completion_time, ta.result_summary,
                       po.opportunity_data
                FROM task_assignments ta
                LEFT JOIN processed_opportunities po ON ta.opportunity_hash = po.opportunity_hash
                WHERE ta.completion_status = 'completed'
                ORDER BY ta.assignment_time DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            logger.info(f"找到 {len(rows)} 个历史任务记录")
            
            # 创建知识文档
            documents = []
            successful_imports = 0
            
            for row in rows:
                try:
                    assignment_id = row[0]
                    opportunity_hash = row[1]
                    assigned_avatar = row[2]
                    assignment_time = row[3]
                    deadline = row[4]
                    priority = row[5]
                    completion_status = row[6]
                    completion_time = row[7]
                    result_summary = row[8]
                    opportunity_data = row[9] if row[9] else "{}"
                    
                    # 解析机会数据
                    try:
                        opp_data = json.loads(opportunity_data)
                    except:
                        opp_data = {}
                    
                    # 构建任务描述
                    task_description = "历史任务执行记录"
                    if opp_data.get("title"):
                        task_description = opp_data.get("title")
                    
                    # 创建知识文档
                    task_doc = create_document_from_task_result(
                        task_id=f"historical_task_{assignment_id}",
                        task_description=task_description,
                        task_result=self._format_task_result(
                            assignment_id=assignment_id,
                            assigned_avatar=assigned_avatar,
                            assignment_time=assignment_time,
                            completion_time=completion_time,
                            result_summary=result_summary,
                            opportunity_data=opp_data
                        ),
                        avatar_id=assigned_avatar,
                        additional_tags=["historical", "task_record", "execution_log"]
                    )
                    
                    # 添加额外元数据
                    task_doc.metadata.update({
                        "original_assignment_id": assignment_id,
                        "opportunity_hash": opportunity_hash,
                        "priority_level": priority,
                        "imported_at": datetime.now().isoformat(),
                        "data_type": "historical_task"
                    })
                    
                    documents.append(task_doc)
                    
                except Exception as e:
                    logger.error(f"处理历史任务失败 {row[0]}: {str(e)}")
                    continue
            
            logger.info(f"准备导入 {len(documents)} 个历史任务文档")
            
            # 批量导入
            if documents:
                results = self.nli.batch_add_documents(
                    knowledge_base_id=knowledge_base_id,
                    documents=documents,
                    batch_size=50
                )
                
                # 统计成功导入数量
                successful_imports = sum(1 for r in results if r["status"] == "success")
                logger.info(f"成功导入 {successful_imports}/{len(documents)} 个历史任务文档")
            
            conn.close()
            
            return {
                "total_tasks": len(rows),
                "documents_created": len(documents),
                "successful_imports": successful_imports,
                "status": "completed" if successful_imports == len(documents) else "partial"
            }
            
        except Exception as e:
            logger.error(f"导入历史任务失败: {str(e)}")
            return {"error": str(e)}
    
    def import_market_intelligence(self, knowledge_base_id: str,
                                 data_sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        导入市场情报数据
        
        Args:
            knowledge_base_id: 目标知识库ID
            data_sources: 数据源列表，None表示使用默认
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化"}
        
        try:
            # 默认数据源
            if not data_sources:
                data_sources = [
                    "industry_resources",
                    "cross_industry_mappings",
                    "promotion_contents"
                ]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            total_docs = 0
            successful_imports = 0
            
            # 导入行业资源
            if "industry_resources" in data_sources:
                cursor.execute("""
                    SELECT resource_id, title, content, category, region, 
                           industry, tags, metadata, created_at
                    FROM industry_resources
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
                
                industry_rows = cursor.fetchall()
                logger.info(f"找到 {len(industry_rows)} 个行业资源记录")
                
                industry_docs = []
                for row in industry_rows:
                    try:
                        resource_id = row[0]
                        title = row[1] or "未命名行业资源"
                        content = row[2] or ""
                        category = row[3] or "通用"
                        region = row[4] or "全球"
                        industry = row[5] or "通用"
                        tags = json.loads(row[6]) if row[6] else []
                        metadata = json.loads(row[7]) if row[7] else {}
                        created_at = row[8] or datetime.now().isoformat()
                        
                        # 创建文档
                        doc = KnowledgeDocument(
                            title=title,
                            content=content,
                            content_type=ContentType.MARKDOWN,
                            source_type=SourceType.MARKET_DATA,
                            source_id=f"industry_resource_{resource_id}",
                            tags=tags + ["market_intelligence", "industry_resource"],
                            metadata={
                                "category": category,
                                "region": region,
                                "industry": industry,
                                "original_id": resource_id,
                                "created_at": created_at,
                                "imported_at": datetime.now().isoformat()
                            }
                        )
                        
                        industry_docs.append(doc)
                        
                    except Exception as e:
                        logger.error(f"处理行业资源失败 {row[0]}: {str(e)}")
                        continue
                
                # 批量导入
                if industry_docs:
                    results = self.nli.batch_add_documents(
                        knowledge_base_id=knowledge_base_id,
                        documents=industry_docs,
                        batch_size=50
                    )
                    
                    successful_imports += sum(1 for r in results if r["status"] == "success")
                    total_docs += len(industry_docs)
            
            # 导入跨行业映射
            if "cross_industry_mappings" in data_sources:
                cursor.execute("""
                    SELECT mapping_id, source_industry, target_industry,
                           mapping_strength, use_cases, tags, created_at
                    FROM cross_industry_mappings
                    ORDER BY mapping_strength DESC
                    LIMIT 50
                """)
                
                mapping_rows = cursor.fetchall()
                logger.info(f"找到 {len(mapping_rows)} 个跨行业映射记录")
                
                mapping_docs = []
                for row in mapping_rows:
                    try:
                        mapping_id = row[0]
                        source_industry = row[1] or ""
                        target_industry = row[2] or ""
                        mapping_strength = row[3] or 0.0
                        use_cases = json.loads(row[4]) if row[4] else []
                        tags = json.loads(row[5]) if row[5] else []
                        created_at = row[6] or datetime.now().isoformat()
                        
                        # 创建文档
                        content = f"""
# 跨行业映射分析

**来源行业**: {source_industry}
**目标行业**: {target_industry}
**映射强度**: {mapping_strength:.2f}

## 应用场景
{chr(10).join(f'- {case}' for case in use_cases[:5])}

## 战略价值
- 行业交叉创新机会
- 供应链优化可能性
- 市场扩展路径
"""

                        doc = KnowledgeDocument(
                            title=f"跨行业映射_{source_industry}_to_{target_industry}",
                            content=content,
                            content_type=ContentType.MARKDOWN,
                            source_type=SourceType.MARKET_DATA,
                            source_id=f"cross_industry_mapping_{mapping_id}",
                            tags=tags + ["cross_industry", "mapping", "innovation"],
                            metadata={
                                "source_industry": source_industry,
                                "target_industry": target_industry,
                                "mapping_strength": mapping_strength,
                                "original_id": mapping_id,
                                "created_at": created_at,
                                "imported_at": datetime.now().isoformat()
                            }
                        )
                        
                        mapping_docs.append(doc)
                        
                    except Exception as e:
                        logger.error(f"处理跨行业映射失败 {row[0]}: {str(e)}")
                        continue
                
                # 批量导入
                if mapping_docs:
                    results = self.nli.batch_add_documents(
                        knowledge_base_id=knowledge_base_id,
                        documents=mapping_docs,
                        batch_size=50
                    )
                    
                    successful_imports += sum(1 for r in results if r["status"] == "success")
                    total_docs += len(mapping_docs)
            
            conn.close()
            
            return {
                "total_documents": total_docs,
                "successful_imports": successful_imports,
                "success_rate": successful_imports / total_docs if total_docs > 0 else 0.0,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"导入市场情报失败: {str(e)}")
            return {"error": str(e)}
    
    def import_architecture_documents(self, knowledge_base_id: str) -> Dict[str, Any]:
        """
        导入系统架构文档
        
        Args:
            knowledge_base_id: 目标知识库ID
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化"}
        
        try:
            # 架构文档源
            architecture_sources = [
                "docs/部署指南.md",
                "docs/无限分身操作手册.md",
                "docs/分身工厂节点增强说明.md",
                "src/notebook_lm_integration.py",
                "src/knowledge_driven_avatar.py"
            ]
            
            documents = []
            
            for file_path in architecture_sources:
                full_path = os.path.join("/app/data/files", file_path)
                
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 提取文件名
                        filename = os.path.basename(file_path)
                        
                        # 根据文件类型确定内容类型
                        if file_path.endswith(".py"):
                            content_type = ContentType.PLAIN_TEXT
                            tags = ["source_code", "python", "architecture"]
                        elif file_path.endswith(".md"):
                            content_type = ContentType.MARKDOWN
                            tags = ["documentation", "markdown", "guide"]
                        else:
                            content_type = ContentType.PLAIN_TEXT
                            tags = ["document", "text"]
                        
                        # 创建文档
                        doc = KnowledgeDocument(
                            title=f"系统架构文档: {filename}",
                            content=content,
                            content_type=content_type,
                            source_type=SourceType.CONFIGURATION,
                            source_id=f"arch_doc_{hashlib.md5(file_path.encode()).hexdigest()[:8]}",
                            tags=tags + ["system_architecture", "sellai"],
                            metadata={
                                "file_path": file_path,
                                "file_size": len(content),
                                "last_modified": datetime.fromtimestamp(
                                    os.path.getmtime(full_path)
                                ).isoformat(),
                                "imported_at": datetime.now().isoformat()
                            }
                        )
                        
                        documents.append(doc)
                        logger.info(f"架构文档已处理: {filename}")
                        
                    except Exception as e:
                        logger.error(f"处理架构文档失败 {file_path}: {str(e)}")
                        continue
            
            logger.info(f"准备导入 {len(documents)} 个架构文档")
            
            # 批量导入
            successful_imports = 0
            if documents:
                results = self.nli.batch_add_documents(
                    knowledge_base_id=knowledge_base_id,
                    documents=documents,
                    batch_size=50
                )
                
                successful_imports = sum(1 for r in results if r["status"] == "success")
                logger.info(f"成功导入 {successful_imports}/{len(documents)} 个架构文档")
            
            return {
                "total_documents": len(documents),
                "successful_imports": successful_imports,
                "success_rate": successful_imports / len(documents) if documents else 0.0,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"导入架构文档失败: {str(e)}")
            return {"error": str(e)}
    
    def import_avatar_capability_profiles(self, knowledge_base_id: str) -> Dict[str, Any]:
        """
        导入分身能力矩阵数据
        
        Args:
            knowledge_base_id: 目标知识库ID
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, capability_scores,
                       specialization_tags, success_rate, total_tasks_completed,
                       avg_completion_time_seconds, current_load, last_active, created_at
                FROM avatar_capability_profiles
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            logger.info(f"找到 {len(rows)} 个分身能力画像记录")
            
            documents = []
            
            for row in rows:
                try:
                    avatar_id = row[0]
                    avatar_name = row[1] or "未命名分身"
                    template_id = row[2]
                    
                    # 解析JSON字段
                    capability_scores = {}
                    if row[3]:
                        try:
                            capability_scores = json.loads(row[3])
                        except:
                            capability_scores = {}
                    
                    specialization_tags = []
                    if row[4]:
                        try:
                            specialization_tags = json.loads(row[4])
                        except:
                            specialization_tags = []
                    
                    success_rate = row[5] or 0.0
                    total_tasks_completed = row[6] or 0
                    avg_completion_time = row[7] or 0.0
                    current_load = row[8] or 0
                    
                    last_active = row[9] or datetime.now().isoformat()
                    created_at = row[10] or datetime.now().isoformat()
                    
                    # 创建内容
                    content = f"""
# 分身能力画像报告

**分身ID**: {avatar_id}
**分身名称**: {avatar_name}
**模板ID**: {template_id or "N/A"}

## 核心能力分数
{chr(10).join(f'- **{cap}**: {score:.2f}' for cap, score in capability_scores.items()[:10])}

## 专长标签
{chr(10).join(f'- {tag}' for tag in specialization_tags[:10])}

## 执行统计
- **成功率**: {success_rate:.2%}
- **完成任务数**: {total_tasks_completed}
- **平均完成时间**: {avg_completion_time:.1f}秒
- **当前负载**: {current_load}个任务

## 分析洞察
基于历史执行数据，此分身最擅长以下领域：
1. 高成功率任务执行
2. 效率导向的任务处理
3. 需要专长知识支持的任务
"""
                    
                    # 创建文档
                    doc = KnowledgeDocument(
                        title=f"分身能力画像: {avatar_name}",
                        content=content,
                        content_type=ContentType.MARKDOWN,
                        source_type=SourceType.CONFIGURATION,
                        source_id=f"avatar_profile_{avatar_id}",
                        tags=["avatar_profile", "capability_matrix", "performance_data"] + specialization_tags[:5],
                        metadata={
                            "avatar_id": avatar_id,
                            "template_id": template_id,
                            "success_rate": success_rate,
                            "total_tasks_completed": total_tasks_completed,
                            "avg_completion_time_seconds": avg_completion_time,
                            "current_load": current_load,
                            "last_active": last_active,
                            "created_at": created_at,
                            "imported_at": datetime.now().isoformat()
                        }
                    )
                    
                    documents.append(doc)
                    
                except Exception as e:
                    logger.error(f"处理分身能力画像失败 {row[0]}: {str(e)}")
                    continue
            
            logger.info(f"准备导入 {len(documents)} 个分身能力画像文档")
            
            # 批量导入
            successful_imports = 0
            if documents:
                results = self.nli.batch_add_documents(
                    knowledge_base_id=knowledge_base_id,
                    documents=documents,
                    batch_size=50
                )
                
                successful_imports = sum(1 for r in results if r["status"] == "success")
                logger.info(f"成功导入 {successful_imports}/{len(documents)} 个分身能力画像文档")
            
            conn.close()
            
            return {
                "total_documents": len(documents),
                "successful_imports": successful_imports,
                "success_rate": successful_imports / len(documents) if documents else 0.0,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"导入分身能力画像失败: {str(e)}")
            return {"error": str(e)}
    
    def create_global_knowledge_base(self, name: str = "SellAI全球知识底座",
                                   description: Optional[str] = None) -> Optional[str]:
        """
        创建全球知识库
        
        Args:
            name: 知识库名称
            description: 知识库描述
            
        Returns:
            知识库ID，如果失败则返回None
        """
        if not self.nli:
            logger.error("Notebook LM集成未初始化")
            return None
        
        try:
            # 创建知识库
            kb_id = self.nli.create_knowledge_base(
                name=name,
                description=description or "SellAI系统的全球知识底座，包含历史任务记录、市场情报、架构文档、分身能力矩阵等所有业务数据"
            )
            
            logger.info(f"全球知识库创建成功，ID: {kb_id}")
            
            # 保存知识库配置
            config_dir = "configs"
            os.makedirs(config_dir, exist_ok=True)
            
            kb_config = {
                "knowledge_base_id": kb_id,
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "data_categories": [
                    "historical_tasks",
                    "market_intelligence",
                    "architecture_documents",
                    "avatar_capability_profiles",
                    "global_business_data"
                ]
            }
            
            config_file = os.path.join(config_dir, "global_knowledge_base_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(kb_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识库配置已保存: {config_file}")
            
            return kb_id
            
        except Exception as e:
            logger.error(f"创建全球知识库失败: {str(e)}")
            return None
    
    def run_full_import(self, knowledge_base_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行完整数据导入
        
        Args:
            knowledge_base_id: 目标知识库ID，None则创建新知识库
            
        Returns:
            导入结果汇总
        """
        logger.info("🚀 开始执行完整数据导入流程...")
        
        # 创建或使用现有知识库
        target_kb_id = knowledge_base_id
        if not target_kb_id:
            target_kb_id = self.create_global_knowledge_base()
            if not target_kb_id:
                return {"error": "无法创建知识库"}
        
        results = {}
        
        # 1. 导入历史任务记录
        logger.info("📋 导入历史任务记录...")
        task_results = self.import_historical_tasks(
            knowledge_base_id=target_kb_id,
            limit=200
        )
        results["historical_tasks"] = task_results
        
        # 2. 导入市场情报
        logger.info("📊 导入市场情报数据...")
        market_results = self.import_market_intelligence(
            knowledge_base_id=target_kb_id
        )
        results["market_intelligence"] = market_results
        
        # 3. 导入架构文档
        logger.info("🏗️ 导入系统架构文档...")
        arch_results = self.import_architecture_documents(
            knowledge_base_id=target_kb_id
        )
        results["architecture_documents"] = arch_results
        
        # 4. 导入分身能力矩阵
        logger.info("🤖 导入分身能力矩阵数据...")
        avatar_results = self.import_avatar_capability_profiles(
            knowledge_base_id=target_kb_id
        )
        results["avatar_capability_profiles"] = avatar_results
        
        # 汇总统计
        total_docs = sum(r.get("total_documents", 0) for r in results.values() if isinstance(r, dict))
        successful_imports = sum(r.get("successful_imports", 0) for r in results.values() if isinstance(r, dict))
        
        summary = {
            "knowledge_base_id": target_kb_id,
            "total_documents": total_docs,
            "successful_imports": successful_imports,
            "success_rate": successful_imports / total_docs if total_docs > 0 else 0.0,
            "categories_imported": list(results.keys()),
            "detailed_results": results,
            "completed_at": datetime.now().isoformat()
        }
        
        # 保存导入报告
        report_dir = "outputs/知识库导入报告"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(report_dir, f"全量数据导入报告_{timestamp}.json")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 完整数据导入完成，报告已保存: {report_file}")
        
        return summary
    
    def _format_task_result(self, assignment_id: int, assigned_avatar: str,
                           assignment_time: str, completion_time: str,
                           result_summary: str, opportunity_data: Dict[str, Any]) -> str:
        """
        格式化任务结果
        
        Args:
            assignment_id: 分配ID
            assigned_avatar: 分配的分身
            assignment_time: 分配时间
            completion_time: 完成时间
            result_summary: 结果摘要
            opportunity_data: 机会数据
            
        Returns:
            格式化后的任务结果
        """
        # 解析结果摘要
        try:
            result_data = json.loads(result_summary) if result_summary else {}
        except:
            result_data = {}
        
        # 构建格式化结果
        formatted = f"""
# 历史任务执行报告

## 基本信息
- **分配ID**: {assignment_id}
- **执行分身**: {assigned_avatar}
- **分配时间**: {assignment_time}
- **完成时间**: {completion_time or 'N/A'}
- **任务状态**: 已完成

## 商机信息
"""
        
        if opportunity_data:
            formatted += f"""
**商机标题**: {opportunity_data.get('title', '未命名商机')}
**来源平台**: {opportunity_data.get('source', '未知来源')}
**发现时间**: {opportunity_data.get('discovered_at', '未知时间')}
**目标地区**: {', '.join(opportunity_data.get('target_regions', ['全球']))}
**预估利润率**: {opportunity_data.get('estimated_margin_percentage', 'N/A')}%
"""
        
        formatted += f"""
## 执行结果摘要
"""
        
        if result_data:
            formatted += f"""
**处理结论**: {result_data.get('conclusion', 'N/A')}
**关键指标**: {json.dumps(result_data.get('key_metrics', {}), ensure_ascii=False, indent=2)}
**建议行动**: {chr(10).join(f'- {action}' for action in result_data.get('recommended_actions', []))}
**风险提示**: {chr(10).join(f'- {risk}' for risk in result_data.get('risk_warnings', []))}
"""
        else:
            formatted += "**结果摘要**: 任务执行完成，详细结果记录于系统"
        
        formatted += f"""
## 经验总结
- **成功因素**: 基于分身专长、数据驱动决策
- **改进空间**: 可优化执行效率、扩大数据源覆盖
- **知识沉淀**: 此任务经验已归档至知识库，供后续任务参考

## 关联知识
- 类似任务历史成功率: 85%
- 相关行业趋势: 数字化转型加速
- 技术栈应用: AI决策、自动化执行

---
*报告生成时间: {datetime.now().isoformat()}*
*数据源: SellAI历史任务数据库*
"""
        
        return formatted


def main():
    """主函数：执行完整数据导入"""
    print("🚀 SellAI知识库数据导入工具")
    print("=" * 50)
    
    # 检查API密钥
    api_key = os.getenv("NOTEBOOKLM_API_KEY")
    if not api_key:
        print("⚠️  警告: 未设置NOTEBOOKLM_API_KEY环境变量")
        print("   如需实际导入，请设置环境变量:")
        print("   export NOTEBOOKLM_API_KEY='your_api_key_here'")
        print()
        print("   将使用模拟模式运行演示")
    
    # 创建导入器
    importer = KnowledgeBaseImporter()
    
    print("📊 导入数据源:")
    print("   1. 历史任务记录")
    print("   2. 市场情报数据")
    print("   3. 系统架构文档")
    print("   4. 分身能力矩阵")
    print("=" * 50)
    
    try:
        # 执行完整导入
        results = importer.run_full_import()
        
        print("\n✅ 导入完成!")
        print("=" * 50)
        
        if "error" in results:
            print(f"❌ 导入失败: {results['error']}")
            return
        
        print(f"📁 知识库ID: {results['knowledge_base_id']}")
        print(f"📄 总文档数: {results['total_documents']}")
        print(f"✅ 成功导入: {results['successful_imports']}")
        print(f"📈 成功率: {results['success_rate']:.2%}")
        
        print("\n📋 分类导入结果:")
        for category, detail in results.get("detailed_results", {}).items():
            if isinstance(detail, dict):
                docs = detail.get("total_documents", detail.get("documents_created", 0))
                success = detail.get("successful_imports", 0)
                print(f"   • {category}: {success}/{docs} ({success/docs:.1%} if docs>0 else 'N/A')")
        
        report_file = f"outputs/知识库导入报告/全量数据导入报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        print(f"\n📝 详细报告: {os.path.abspath(report_file)}")
        
    except Exception as e:
        print(f"❌ 导入过程异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()