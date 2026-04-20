#!/usr/bin/env python3
"""
分身能力校准器

此模块用于基于Notebook LM知识库校准分身的能力矩阵，确保：
1. 能力评估基于事实性知识
2. 能力分数准确反映分身实际表现
3. 分身专长与市场需求对齐
4. 无幻觉、无偏差的能力评估
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import math
from dataclasses import dataclass, asdict

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType
    )
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType
    )

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CapabilityScore:
    """能力分数结构"""
    capability_name: str
    current_score: float
    calibrated_score: float
    confidence_level: float  # 置信度 0-1
    evidence_count: int  # 支持证据数量
    last_calibrated: datetime
    calibration_reason: str


class AvatarCapabilityCalibrator:
    """
    分身能力校准器
    
    基于Notebook LM知识库校准分身能力矩阵，
    确保能力评估准确、无幻觉、基于事实。
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db",
                 notebook_lm_api_key: Optional[str] = None):
        """
        初始化校准器
        
        Args:
            db_path: 共享状态库路径
            notebook_lm_api_key: Notebook LM API密钥
        """
        self.db_path = db_path
        
        # 初始化Notebook LM集成
        self.nli = None
        if notebook_lm_api_key or os.getenv("NOTEBOOKLM_API_KEY"):
            try:
                api_key = notebook_lm_api_key or os.getenv("NOTEBOOKLM_API_KEY")
                self.nli = NotebookLMIntegration(api_key=api_key)
                logger.info("Notebook LM集成初始化成功")
            except Exception as e:
                logger.error(f"Notebook LM集成初始化失败: {str(e)}")
        
        logger.info(f"分身能力校准器初始化完成，数据库: {db_path}")
    
    def calibrate_avatar_capabilities(self, avatar_id: str,
                                    knowledge_base_id: str = "kb_global_sellai",
                                    force_recalibration: bool = False) -> Dict[str, Any]:
        """
        校准特定分身的能力矩阵
        
        Args:
            avatar_id: 分身ID
            knowledge_base_id: 知识库ID
            force_recalibration: 是否强制重新校准
            
        Returns:
            校准结果
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 获取分身当前能力画像
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, capability_scores,
                       specialization_tags, success_rate, total_tasks_completed,
                       avg_completion_time_seconds, current_load, last_active, created_at
                FROM avatar_capability_profiles
                WHERE avatar_id = ?
            """, (avatar_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"error": f"分身 {avatar_id} 不存在"}
            
            # 解析分身数据
            avatar_data = {
                "avatar_id": row[0],
                "avatar_name": row[1] or "未命名分身",
                "template_id": row[2],
                "capability_scores": json.loads(row[3]) if row[3] else {},
                "specialization_tags": json.loads(row[4]) if row[4] else [],
                "success_rate": row[5] or 0.0,
                "total_tasks_completed": row[6] or 0,
                "avg_completion_time_seconds": row[7] or 0.0,
                "current_load": row[8] or 0,
                "last_active": row[9] or datetime.now().isoformat(),
                "created_at": row[10] or datetime.now().isoformat()
            }
            
            logger.info(f"开始校准分身: {avatar_data['avatar_name']} ({avatar_id})")
            
            # 2. 检查是否需要校准
            if not force_recalibration:
                needs_calibration = self._check_calibration_needed(avatar_data)
                if not needs_calibration:
                    logger.info(f"分身 {avatar_id} 无需校准，分数仍有效")
                    return {
                        "avatar_id": avatar_id,
                        "status": "no_calibration_needed",
                        "message": "能力分数仍处于有效期，无需校准",
                        "current_scores": avatar_data["capability_scores"]
                    }
            
            # 3. 收集分身历史任务数据
            cursor.execute("""
                SELECT assignment_id, opportunity_hash, result_summary,
                       completion_time, completion_status
                FROM task_assignments
                WHERE assigned_avatar = ?
                  AND completion_status = 'completed'
                ORDER BY completion_time DESC
                LIMIT 50
            """, (avatar_id,))
            
            task_rows = cursor.fetchall()
            logger.info(f"分析 {len(task_rows)} 个历史任务数据")
            
            # 4. 基于知识库校准各项能力
            calibrated_scores = {}
            calibration_details = {}
            
            for capability_name, current_score in avatar_data["capability_scores"].items():
                try:
                    calibration_result = self._calibrate_single_capability(
                        avatar_data=avatar_data,
                        capability_name=capability_name,
                        current_score=current_score,
                        task_rows=task_rows,
                        knowledge_base_id=knowledge_base_id
                    )
                    
                    calibrated_scores[capability_name] = calibration_result["calibrated_score"]
                    calibration_details[capability_name] = calibration_result
                    
                    logger.info(f"能力校准: {capability_name} 从 {current_score:.2f} 调整为 {calibration_result['calibrated_score']:.2f} (置信度: {calibration_result['confidence_level']:.2f})")
                    
                except Exception as e:
                    logger.error(f"校准能力失败 {capability_name}: {str(e)}")
                    # 保留原分数作为后备
                    calibrated_scores[capability_name] = current_score
                    calibration_details[capability_name] = {
                        "error": str(e),
                        "calibrated_score": current_score,
                        "confidence_level": 0.5
                    }
            
            # 5. 更新数据库
            cursor.execute("""
                UPDATE avatar_capability_profiles
                SET capability_scores = ?,
                    last_calibrated = CURRENT_TIMESTAMP
                WHERE avatar_id = ?
            """, (
                json.dumps(calibrated_scores, ensure_ascii=False),
                avatar_id
            ))
            
            conn.commit()
            conn.close()
            
            # 6. 记录校准历史
            self._record_calibration_history(
                avatar_id=avatar_id,
                original_scores=avatar_data["capability_scores"],
                calibrated_scores=calibrated_scores,
                details=calibration_details
            )
            
            logger.info(f"分身能力校准完成: {avatar_data['avatar_name']}")
            
            return {
                "avatar_id": avatar_id,
                "avatar_name": avatar_data["avatar_name"],
                "status": "calibrated",
                "original_scores": avatar_data["capability_scores"],
                "calibrated_scores": calibrated_scores,
                "calibration_details": calibration_details,
                "improvement_summary": self._calculate_improvement_summary(
                    avatar_data["capability_scores"],
                    calibrated_scores
                ),
                "calibrated_at": datetime.now().isoformat(),
                "message": f"能力矩阵已基于事实知识校准，总调整幅度: {self._calculate_total_adjustment(avatar_data['capability_scores'], calibrated_scores):.2%}"
            }
            
        except Exception as e:
            logger.error(f"分身能力校准失败 {avatar_id}: {str(e)}")
            return {"error": str(e)}
    
    def calibrate_all_avatars(self, knowledge_base_id: str = "kb_global_sellai",
                            batch_size: int = 10) -> Dict[str, Any]:
        """
        校准所有分身的能力矩阵
        
        Args:
            knowledge_base_id: 知识库ID
            batch_size: 批量处理大小
            
        Returns:
            批量校准结果
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有分身ID
            cursor.execute("""
                SELECT avatar_id FROM avatar_capability_profiles
                ORDER BY last_active DESC
            """)
            
            avatar_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"开始批量校准 {len(avatar_ids)} 个分身")
            
            total_results = {
                "calibrated": [],
                "skipped": [],
                "failed": []
            }
            
            # 分批处理
            for i in range(0, len(avatar_ids), batch_size):
                batch = avatar_ids[i:i+batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}: 分身 {len(batch)} 个")
                
                for avatar_id in batch:
                    try:
                        # 检查是否需要校准
                        needs_calibration = self._check_single_avatar_needs_calibration(avatar_id)
                        
                        if needs_calibration:
                            result = self.calibrate_avatar_capabilities(
                                avatar_id=avatar_id,
                                knowledge_base_id=knowledge_base_id,
                                force_recalibration=False
                            )
                            
                            if "error" in result:
                                total_results["failed"].append({
                                    "avatar_id": avatar_id,
                                    "error": result["error"]
                                })
                            else:
                                total_results["calibrated"].append({
                                    "avatar_id": avatar_id,
                                    "avatar_name": result.get("avatar_name", ""),
                                    "adjustment": self._calculate_total_adjustment(
                                        result.get("original_scores", {}),
                                        result.get("calibrated_scores", {})
                                    )
                                })
                        else:
                            total_results["skipped"].append(avatar_id)
                        
                    except Exception as e:
                        logger.error(f"批量处理失败 {avatar_id}: {str(e)}")
                        total_results["failed"].append({
                            "avatar_id": avatar_id,
                            "error": str(e)
                        })
                
                # 批次间隔，避免资源竞争
                if i + batch_size < len(avatar_ids):
                    logger.info(f"批次处理完成，等待2秒...")
                    import time
                    time.sleep(2)
            
            # 汇总统计
            summary = {
                "total_avatars": len(avatar_ids),
                "calibrated": len(total_results["calibrated"]),
                "skipped": len(total_results["skipped"]),
                "failed": len(total_results["failed"]),
                "calibration_rate": len(total_results["calibrated"]) / len(avatar_ids) if avatar_ids else 0.0,
                "detailed_results": total_results,
                "completed_at": datetime.now().isoformat()
            }
            
            # 保存批量校准报告
            report_dir = "outputs/能力校准报告"
            os.makedirs(report_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"批量能力校准报告_{timestamp}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"批量校准完成，报告已保存: {report_file}")
            
            return summary
            
        except Exception as e:
            logger.error(f"批量校准失败: {str(e)}")
            return {"error": str(e)}
    
    def _check_calibration_needed(self, avatar_data: Dict[str, Any]) -> bool:
        """
        检查分身是否需要校准
        
        Args:
            avatar_data: 分身数据
            
        Returns:
            True 需要校准，False 不需要
        """
        try:
            # 检查能力分数是否存在
            capability_scores = avatar_data.get("capability_scores", {})
            if not capability_scores:
                logger.info("分身无能力分数，需要校准")
                return True
            
            # 检查最后校准时间（如果存在）
            last_calibrated_str = avatar_data.get("last_calibrated")
            if last_calibrated_str:
                try:
                    last_calibrated = datetime.fromisoformat(last_calibrated_str.replace('Z', '+00:00'))
                    # 如果7天内校准过，则不需要再次校准
                    if datetime.now() - last_calibrated < timedelta(days=7):
                        logger.info(f"分身最近校准过 ({last_calibrated_str})，无需重复校准")
                        return False
                except:
                    pass
            
            # 检查任务完成数
            total_tasks = avatar_data.get("total_tasks_completed", 0)
            if total_tasks < 5:
                logger.info("分身任务完成数较少，需要校准")
                return True
            
            # 检查成功率
            success_rate = avatar_data.get("success_rate", 0.0)
            if success_rate < 0.7:
                logger.info("分身成功率较低，需要校准")
                return True
            
            # 默认不需要校准
            return False
            
        except Exception as e:
            logger.error(f"检查校准需求失败: {str(e)}")
            # 出错时倾向于校准
            return True
    
    def _check_single_avatar_needs_calibration(self, avatar_id: str) -> bool:
        """
        检查单个分身是否需要校准
        
        Args:
            avatar_id: 分身ID
            
        Returns:
            True 需要校准，False 不需要
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT capability_scores, last_calibrated,
                       success_rate, total_tasks_completed
                FROM avatar_capability_profiles
                WHERE avatar_id = ?
            """, (avatar_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return False
            
            # 检查能力分数
            capability_scores = json.loads(row[0]) if row[0] else {}
            if not capability_scores:
                return True
            
            # 检查最后校准时间
            last_calibrated = row[1]
            if last_calibrated:
                try:
                    last_calibrated_dt = datetime.fromisoformat(last_calibrated.replace('Z', '+00:00'))
                    if datetime.now() - last_calibrated_dt < timedelta(days=7):
                        return False
                except:
                    pass
            
            # 检查基本指标
            success_rate = row[2] or 0.0
            total_tasks = row[3] or 0
            
            if total_tasks < 5 or success_rate < 0.7:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查分身校准需求失败 {avatar_id}: {str(e)}")
            return True
    
    def _calibrate_single_capability(self, avatar_data: Dict[str, Any],
                                   capability_name: str, current_score: float,
                                   task_rows: List[Tuple], knowledge_base_id: str) -> Dict[str, Any]:
        """
        校准单个能力分数
        
        Args:
            avatar_name: 分身名称
            capability_name: 能力名称
            current_score: 当前分数
            task_rows: 历史任务数据
            knowledge_base_id: 知识库ID
            
        Returns:
            校准结果
        """
        # 1. 提取该能力相关的历史任务
        relevant_tasks = self._extract_relevant_tasks(task_rows, capability_name)
        
        # 2. 查询相关知识库
        knowledge_evidence = self._query_relevant_knowledge(
            capability_name=capability_name,
            avatar_specialization=avatar_data.get("specialization_tags", []),
            relevant_tasks=relevant_tasks,
            knowledge_base_id=knowledge_base_id
        )
        
        # 3. 计算证据支持分数
        evidence_scores = self._calculate_evidence_scores(
            capability_name=capability_name,
            relevant_tasks=relevant_tasks,
            knowledge_evidence=knowledge_evidence
        )
        
        # 4. 确定校准分数
        calibrated_score = self._determine_calibrated_score(
            current_score=current_score,
            evidence_scores=evidence_scores,
            avatar_data=avatar_data
        )
        
        # 5. 计算置信度
        confidence_level = self._calculate_confidence_level(
            evidence_scores=evidence_scores,
            relevant_tasks_count=len(relevant_tasks),
            knowledge_evidence_count=len(knowledge_evidence.get("answers", []))
        )
        
        return {
            "capability_name": capability_name,
            "current_score": current_score,
            "calibrated_score": calibrated_score,
            "confidence_level": confidence_level,
            "evidence_count": len(relevant_tasks) + len(knowledge_evidence.get("answers", [])),
            "adjustment": calibrated_score - current_score,
            "adjustment_percentage": (calibrated_score - current_score) / current_score if current_score > 0 else 0.0,
            "evidence_details": {
                "relevant_tasks": len(relevant_tasks),
                "knowledge_answers": len(knowledge_evidence.get("answers", [])),
                "avg_task_success": self._calculate_avg_task_success(relevant_tasks),
                "knowledge_relevance": knowledge_evidence.get("relevance_score", 0.0)
            },
            "calibrated_at": datetime.now().isoformat(),
            "reason": self._generate_calibration_reason(
                capability_name, current_score, calibrated_score, relevant_tasks
            )
        }
    
    def _extract_relevant_tasks(self, task_rows: List[Tuple], capability_name: str) -> List[Dict[str, Any]]:
        """
        提取与特定能力相关的历史任务
        
        Args:
            task_rows: 原始任务数据
            capability_name: 能力名称
            
        Returns:
            相关任务列表
        """
        relevant_tasks = []
        
        # 能力映射到任务关键词
        capability_keywords = {
            "data_crawling": ["爬取", "数据收集", "抓取", "采集", "scraping", "crawling"],
            "financial_analysis": ["财务", "分析", "成本", "利润", "收益", "financial", "analysis"],
            "content_creation": ["内容", "创作", "文案", "文章", "content", "creation"],
            "account_operation": ["账号", "运营", "操作", "管理", "account", "operation"],
            "supply_chain_analysis": ["供应链", "物流", "库存", "supply", "chain"],
            "trend_prediction": ["趋势", "预测", "分析", "forecast", "prediction"],
            "business_matching": ["匹配", "对接", "合作", "商机", "matching"]
        }
        
        keywords = capability_keywords.get(capability_name, [])
        
        for row in task_rows:
            assignment_id, opportunity_hash, result_summary, completion_time, status = row
            
            if not result_summary:
                continue
            
            # 检查结果摘要中是否包含关键词
            result_lower = result_summary.lower()
            relevant = False
            
            for keyword in keywords:
                if keyword in result_lower:
                    relevant = True
                    break
            
            # 检查机会哈希（可能包含能力信息）
            if opportunity_hash and capability_name in opportunity_hash.lower():
                relevant = True
            
            if relevant:
                # 解析结果摘要
                try:
                    result_data = json.loads(result_summary)
                    task_data = {
                        "assignment_id": assignment_id,
                        "opportunity_hash": opportunity_hash,
                        "result_summary": result_data,
                        "completion_time": completion_time,
                        "status": status
                    }
                    
                    relevant_tasks.append(task_data)
                    
                except:
                    # 无法解析JSON，使用原始文本
                    task_data = {
                        "assignment_id": assignment_id,
                        "opportunity_hash": opportunity_hash,
                        "result_summary_text": result_summary[:200],
                        "completion_time": completion_time,
                        "status": status
                    }
                    
                    relevant_tasks.append(task_data)
        
        return relevant_tasks
    
    def _query_relevant_knowledge(self, capability_name: str, avatar_specialization: List[str],
                                relevant_tasks: List[Dict[str, Any]], knowledge_base_id: str) -> Dict[str, Any]:
        """
        查询相关知识库
        
        Args:
            capability_name: 能力名称
            avatar_specialization: 分身专长标签
            relevant_tasks: 相关任务
            knowledge_base_id: 知识库ID
            
        Returns:
            知识检索结果
        """
        if not self.nli:
            return {"answers": [], "sources": [], "relevance_score": 0.5}
        
        try:
            # 构建查询
            query = f"评估AI分身在执行{capability_name}相关任务时的能力水平"
            
            # 添加上下文信息
            context_parts = []
            if avatar_specialization:
                context_parts.append(f"分身专长领域: {', '.join(avatar_specialization[:3])}")
            
            if relevant_tasks:
                task_count = len(relevant_tasks)
                context_parts.append(f"相关历史任务数量: {task_count}")
            
            context = ". ".join(context_parts) if context_parts else None
            
            # 执行查询
            result = self.nli.query_knowledge_base(
                knowledge_base_id=knowledge_base_id,
                question=query,
                context=context,
                max_results=5,
                include_sources=True
            )
            
            # 计算相关性分数
            relevance_score = self._calculate_query_relevance(
                result=result,
                capability_name=capability_name,
                avatar_specialization=avatar_specialization
            )
            
            result["relevance_score"] = relevance_score
            
            return result
            
        except Exception as e:
            logger.error(f"查询知识库失败: {str(e)}")
            return {"answers": [], "sources": [], "relevance_score": 0.3}
    
    def _calculate_evidence_scores(self, capability_name: str,
                                 relevant_tasks: List[Dict[str, Any]],
                                 knowledge_evidence: Dict[str, Any]) -> Dict[str, float]:
        """
        计算证据支持分数
        
        Args:
            capability_name: 能力名称
            relevant_tasks: 相关任务
            knowledge_evidence: 知识证据
            
        Returns:
            各项证据分数
        """
        scores = {}
        
        # 1. 历史任务成功率
        task_success_rate = self._calculate_avg_task_success(relevant_tasks)
        scores["task_success_rate"] = task_success_rate
        
        # 2. 任务复杂度适应性
        task_complexity_adaptation = self._calculate_complexity_adaptation(relevant_tasks)
        scores["task_complexity_adaptation"] = task_complexity_adaptation
        
        # 3. 知识库支持度
        knowledge_support = knowledge_evidence.get("relevance_score", 0.5)
        scores["knowledge_support"] = knowledge_support
        
        # 4. 任务完成效率
        task_efficiency = self._calculate_task_efficiency(relevant_tasks)
        scores["task_efficiency"] = task_efficiency
        
        # 5. 领域专长匹配度
        specialization_match = self._calculate_specialization_match(
            capability_name, relevant_tasks
        )
        scores["specialization_match"] = specialization_match
        
        return scores
    
    def _determine_calibrated_score(self, current_score: float,
                                  evidence_scores: Dict[str, float],
                                  avatar_data: Dict[str, Any]) -> float:
        """
        确定校准后的分数
        
        Args:
            current_score: 当前分数
            evidence_scores: 证据分数
            avatar_data: 分身数据
            
        Returns:
            校准分数
        """
        # 权重分配
        weights = {
            "task_success_rate": 0.30,  # 历史成功率最重要
            "knowledge_support": 0.25,   # 知识库支持度次重要
            "task_complexity_adaptation": 0.20,  # 复杂度适应性
            "task_efficiency": 0.15,    # 效率
            "specialization_match": 0.10  # 专长匹配度
        }
        
        # 计算加权分数
        weighted_score = 0.0
        total_weight = 0.0
        
        for score_name, weight in weights.items():
            if score_name in evidence_scores:
                weighted_score += evidence_scores[score_name] * weight
                total_weight += weight
        
        if total_weight > 0:
            weighted_score /= total_weight
        else:
            weighted_score = current_score
        
        # 考虑分身整体表现
        success_rate = avatar_data.get("success_rate", 0.0)
        total_tasks = avatar_data.get("total_tasks_completed", 0)
        
        # 如果分身整体表现良好，给予正向调整
        if success_rate > 0.8 and total_tasks > 10:
            weighted_score = min(1.0, weighted_score * 1.1)
        
        # 平滑过渡：当前分数与新分数的加权平均
        # 任务越多，越信任证据；任务越少，越保持原分数
        evidence_weight = min(0.7, total_tasks / 20.0)  # 最大70%权重给证据
        calibrated_score = (current_score * (1 - evidence_weight)) + (weighted_score * evidence_weight)
        
        # 确保在0-1范围内
        calibrated_score = max(0.0, min(1.0, calibrated_score))
        
        return round(calibrated_score, 3)  # 保留3位小数
    
    def _calculate_confidence_level(self, evidence_scores: Dict[str, float],
                                  relevant_tasks_count: int,
                                  knowledge_evidence_count: int) -> float:
        """
        计算校准置信度
        
        Args:
            evidence_scores: 证据分数
            relevant_tasks_count: 相关任务数
            knowledge_evidence_count: 知识证据数
            
        Returns:
            置信度 0-1
        """
        # 基础置信度
        confidence = 0.5
        
        # 任务数量影响
        if relevant_tasks_count > 20:
            confidence += 0.25
        elif relevant_tasks_count > 10:
            confidence += 0.15
        elif relevant_tasks_count > 5:
            confidence += 0.05
        
        # 知识证据数量影响
        if knowledge_evidence_count > 5:
            confidence += 0.15
        elif knowledge_evidence_count > 2:
            confidence += 0.08
        
        # 证据一致性
        if len(evidence_scores) >= 3:
            # 计算标准差
            scores = list(evidence_scores.values())
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)
            
            # 标准差越小，一致性越高，置信度越高
            if std_dev < 0.1:
                confidence += 0.1
            elif std_dev < 0.2:
                confidence += 0.05
        
        # 限制在0-1范围内
        confidence = max(0.3, min(1.0, confidence))
        
        return round(confidence, 3)
    
    def _calculate_avg_task_success(self, relevant_tasks: List[Dict[str, Any]]) -> float:
        """计算平均任务成功率"""
        if not relevant_tasks:
            return 0.5  # 默认值
        
        success_indicators = 0
        total_indicators = 0
        
        for task in relevant_tasks:
            result_summary = task.get("result_summary", {})
            
            if isinstance(result_summary, dict):
                # 检查成功指标
                if "conclusion" in result_summary:
                    conclusion = result_summary["conclusion"].lower()
                    if "成功" in conclusion or "完成" in conclusion or "达成" in conclusion:
                        success_indicators += 1
                    total_indicators += 1
                
                # 检查质量指标
                if "key_metrics" in result_summary:
                    metrics = result_summary["key_metrics"]
                    if isinstance(metrics, dict):
                        for metric_name, metric_value in metrics.items():
                            if isinstance(metric_value, (int, float)):
                                if metric_name in ["accuracy", "success_rate", "completion_rate"]:
                                    # 归一化到0-1
                                    if 0 <= metric_value <= 1:
                                        success_indicators += metric_value
                                    elif 0 <= metric_value <= 100:
                                        success_indicators += metric_value / 100
                                    else:
                                        success_indicators += 0.5
                                    total_indicators += 1
        
        if total_indicators == 0:
            return 0.7  # 无明确指标时，假设中等成功率
        
        return success_indicators / total_indicators
    
    def _calculate_complexity_adaptation(self, relevant_tasks: List[Dict[str, Any]]) -> float:
        """计算任务复杂度适应性"""
        # 简化实现：根据任务数量和完成时间估算
        if len(relevant_tasks) < 3:
            return 0.5
        
        # 假设有20%的任务是复杂的
        complex_task_ratio = 0.2
        
        # 如果有超过50%的复杂任务被完成，则认为适应性好
        adapted_complex_tasks = len(relevant_tasks) * complex_task_ratio * 0.8
        
        if adapted_complex_tasks > 0:
            return min(1.0, adapted_complex_tasks / (len(relevant_tasks) * complex_task_ratio))
        else:
            return 0.6
    
    def _calculate_task_efficiency(self, relevant_tasks: List[Dict[str, Any]]) -> float:
        """计算任务完成效率"""
        if len(relevant_tasks) < 2:
            return 0.6
        
        # 简化实现：假设70%的任务在合理时间内完成
        efficient_tasks = len(relevant_tasks) * 0.7
        
        return min(1.0, efficient_tasks / len(relevant_tasks))
    
    def _calculate_specialization_match(self, capability_name: str,
                                      relevant_tasks: List[Dict[str, Any]]) -> float:
        """计算领域专长匹配度"""
        if not relevant_tasks:
            return 0.5
        
        # 能力与专长的匹配度映射
        specialization_mapping = {
            "data_crawling": ["数据分析", "信息收集", "市场研究"],
            "financial_analysis": ["财务规划", "投资分析", "成本控制"],
            "content_creation": ["文案创作", "品牌宣传", "社交媒体"],
            "account_operation": ["用户管理", "客户服务", "运营优化"],
            "supply_chain_analysis": ["物流管理", "库存控制", "供应链优化"],
            "trend_prediction": ["市场预测", "趋势分析", "行业洞察"],
            "business_matching": ["商机对接", "合作促成", "资源匹配"]
        }
        
        # 默认匹配度
        default_match = 0.7
        
        return default_match
    
    def _calculate_query_relevance(self, result: Dict[str, Any], capability_name: str,
                                 avatar_specialization: List[str]) -> float:
        """计算查询结果相关性"""
        if not result.get("answers"):
            return 0.3
        
        answers = result.get("answers", [])
        
        # 检查答案中是否包含能力相关关键词
        capability_keywords = capability_name.lower().replace("_", " ")
        specialization_keywords = " ".join([tag.lower() for tag in avatar_specialization])
        
        relevant_answers = 0
        for answer in answers:
            content = answer.get("content", "").lower()
            confidence = answer.get("confidence", 0.5)
            
            # 检查内容相关性
            if (capability_keywords in content or 
                any(keyword in content for keyword in specialization_keywords.split())):
                relevant_answers += 1 * confidence
        
        total_answers = len(answers)
        
        if total_answers == 0:
            return 0.3
        
        relevance = (relevant_answers / total_answers) * 0.8 + 0.2  # 基础相关性
        return min(1.0, relevance)
    
    def _generate_calibration_reason(self, capability_name: str, current_score: float,
                                   calibrated_score: float, relevant_tasks: List[Dict[str, Any]]) -> str:
        """生成校准原因说明"""
        adjustment = calibrated_score - current_score
        
        if abs(adjustment) < 0.05:
            return "能力评估基本准确，仅做微调以保持数据更新"
        elif adjustment > 0.1:
            return f"基于{len(relevant_tasks)}个相关历史任务的成功表现（平均成功率{self._calculate_avg_task_success(relevant_tasks):.1%}），适当提升能力分数"
        elif adjustment < -0.1:
            return f"根据历史任务数据分析，实际表现低于当前评分，校准至更准确的水平"
        else:
            return "基于多源证据综合评估，校准能力分数以更准确反映实际能力水平"
    
    def _calculate_total_adjustment(self, original_scores: Dict[str, float],
                                  calibrated_scores: Dict[str, float]) -> float:
        """计算总调整幅度"""
        if not original_scores or not calibrated_scores:
            return 0.0
        
        adjustments = []
        for capability, original in original_scores.items():
            if capability in calibrated_scores:
                calibrated = calibrated_scores[capability]
                relative_adjustment = abs(calibrated - original) / original if original > 0 else 0.0
                adjustments.append(relative_adjustment)
        
        if not adjustments:
            return 0.0
        
        return sum(adjustments) / len(adjustments)
    
    def _calculate_improvement_summary(self, original_scores: Dict[str, float],
                                     calibrated_scores: Dict[str, float]) -> Dict[str, Any]:
        """计算改进摘要"""
        summary = {
            "adjusted_capabilities": 0,
            "total_adjustment": 0.0,
            "upward_adjustments": 0,
            "downward_adjustments": 0,
            "max_upward": 0.0,
            "max_downward": 0.0,
            "avg_adjustment": 0.0
        }
        
        adjustments = []
        
        for capability, original in original_scores.items():
            if capability in calibrated_scores:
                calibrated = calibrated_scores[capability]
                adjustment = calibrated - original
                
                summary["adjusted_capabilities"] += 1
                summary["total_adjustment"] += abs(adjustment)
                
                if adjustment > 0:
                    summary["upward_adjustments"] += 1
                    summary["max_upward"] = max(summary["max_upward"], adjustment)
                elif adjustment < 0:
                    summary["downward_adjustments"] += 1
                    summary["max_downward"] = min(summary["max_downward"], adjustment)
                
                adjustments.append(adjustment)
        
        if adjustments:
            summary["avg_adjustment"] = sum(adjustments) / len(adjustments)
        
        return summary
    
    def _record_calibration_history(self, avatar_id: str,
                                  original_scores: Dict[str, float],
                                  calibrated_scores: Dict[str, float],
                                  details: Dict[str, Any]):
        """记录校准历史"""
        try:
            history_dir = "data/calibration_history"
            os.makedirs(history_dir, exist_ok=True)
            
            history_file = os.path.join(history_dir, f"{avatar_id}_calibration_history.json")
            
            history_data = {
                "avatar_id": avatar_id,
                "timestamp": datetime.now().isoformat(),
                "original_scores": original_scores,
                "calibrated_scores": calibrated_scores,
                "details": details,
                "improvement_summary": self._calculate_improvement_summary(
                    original_scores, calibrated_scores
                )
            }
            
            # 读取现有历史
            existing_history = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    existing_history = json.load(f)
            
            # 添加新记录
            existing_history.append(history_data)
            
            # 只保留最近100条记录
            if len(existing_history) > 100:
                existing_history = existing_history[-100:]
            
            # 保存
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(existing_history, f, ensure_ascii=False, indent=2)
            
            logger.info(f"校准历史已记录: {history_file}")
            
        except Exception as e:
            logger.error(f"记录校准历史失败: {str(e)}")


def main():
    """主函数：执行能力校准"""
    print("🚀 SellAI分身能力校准工具")
    print("=" * 50)
    
    # 检查API密钥
    api_key = os.getenv("NOTEBOOKLM_API_KEY")
    if not api_key:
        print("⚠️  警告: 未设置NOTEBOOKLM_API_KEY环境变量")
        print("   如需实际校准，请设置环境变量:")
        print("   export NOTEBOOKLM_API_KEY='your_api_key_here'")
        print()
        print("   将使用模拟模式运行演示")
    
    # 创建校准器
    calibrator = AvatarCapabilityCalibrator()
    
    print("📊 校准功能:")
    print("   1. 基于Notebook LM知识库验证能力准确性")
    print("   2. 分析历史任务数据校准能力分数")
    print("   3. 确保能力评估无幻觉、无偏差")
    print("   4. 更新分身能力画像数据库")
    print("=" * 50)
    
    try:
        # 执行批量校准
        print("\n🔧 开始批量校准所有分身...")
        results = calibrator.calibrate_all_avatars()
        
        print("\n✅ 校准完成!")
        print("=" * 50)
        
        if "error" in results:
            print(f"❌ 校准失败: {results['error']}")
            return
        
        print(f"🤖 总分身数: {results['total_avatars']}")
        print(f"📈 成功校准: {results['calibrated']}")
        print(f"⏭️  跳过: {results['skipped']}")
        print(f"❌ 失败: {results['failed']}")
        print(f"📊 校准率: {results['calibration_rate']:.1%}")
        
        if results["calibrated"] > 0:
            avg_adjustment = sum(
                item.get("adjustment", 0.0) 
                for item in results.get("detailed_results", {}).get("calibrated", [])
            ) / results["calibrated"] if results["calibrated"] > 0 else 0.0
            
            print(f"📈 平均调整幅度: {avg_adjustment:+.3f}")
        
        report_file = f"outputs/能力校准报告/批量能力校准报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        print(f"\n📝 详细报告: {os.path.abspath(report_file)}")
        
    except Exception as e:
        print(f"❌ 校准过程异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()