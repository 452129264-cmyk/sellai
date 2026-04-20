#!/usr/bin/env python3
"""
智能知识提取模块

此模块提供从海量业务文档中智能提取结构化知识的能力，
包括自动摘要、关键信息提取、知识图谱构建等功能，
支持从历史任务、市场情报、用户反馈中挖掘价值信息。
"""

import os
import json
import re
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from datetime import datetime
from collections import defaultdict, Counter
import time

# 尝试导入NLP相关库
try:
    import nltk
    NLTK_SUPPORT = True
except ImportError:
    NLTK_SUPPORT = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    SKLEARN_SUPPORT = True
except ImportError:
    SKLEARN_SUPPORT = False

# 配置日志
logger = logging.getLogger(__name__)


class KnowledgeExtractionEngine:
    """
    知识提取引擎
    
    从非结构化文本中提取结构化知识，
    包括实体识别、关系抽取、主题建模等能力。
    """
    
    def __init__(self, language: str = "zh-CN"):
        """
        初始化知识提取引擎
        
        Args:
            language: 目标语言
        """
        self.language = language
        
        # 初始化提取器
        self.summarizer = TextSummarizer(language)
        self.entity_extractor = EntityExtractor(language)
        self.relation_extractor = RelationExtractor(language)
        self.topic_modeler = TopicModeler(language)
        
        logger.info(f"知识提取引擎初始化完成，语言: {language}")
    
    def extract_from_text(self, text: str,
                         extraction_types: List[str] = None) -> Dict[str, Any]:
        """
        从文本中提取知识
        
        Args:
            text: 输入文本
            extraction_types: 提取类型列表
            
        Returns:
            提取的知识结构
        """
        if extraction_types is None:
            extraction_types = ["summary", "entities", "relations", "topics"]
        
        result = {
            "extraction_time": datetime.now().isoformat(),
            "text_length": len(text),
            "extraction_types": extraction_types
        }
        
        try:
            # 预处理文本
            cleaned_text = self._preprocess_text(text)
            
            # 执行各种提取
            if "summary" in extraction_types:
                result["summary"] = self.summarizer.summarize(cleaned_text)
            
            if "entities" in extraction_types:
                entities = self.entity_extractor.extract(cleaned_text)
                result["entities"] = entities
                result["entity_count"] = len(entities)
            
            if "relations" in extraction_types:
                if "entities" in result:
                    relations = self.relation_extractor.extract(
                        cleaned_text, result["entities"]
                    )
                    result["relations"] = relations
                    result["relation_count"] = len(relations)
            
            if "topics" in extraction_types:
                topics = self.topic_modeler.extract_topics(cleaned_text)
                result["topics"] = topics
                result["topic_count"] = len(topics)
            
            # 计算提取质量指标
            result["extraction_quality"] = self._assess_extraction_quality(
                cleaned_text, result
            )
            
            logger.info(f"知识提取完成: 类型={extraction_types}, 实体数={result.get('entity_count', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"知识提取失败: {str(e)}")
            
            error_result = {
                "extraction_time": datetime.now().isoformat(),
                "text_length": len(text),
                "error": str(e),
                "error_type": type(e).__name__,
                "extraction_success": False
            }
            
            return error_result
    
    def batch_extract(self, documents: List[Dict[str, Any]],
                     extraction_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        批量提取文档知识
        
        Args:
            documents: 文档列表，每个文档包含id和content
            extraction_types: 提取类型列表
            
        Returns:
            提取结果列表
        """
        results = []
        
        logger.info(f"开始批量知识提取: {len(documents)} 个文档")
        
        for i, doc in enumerate(documents):
            try:
                doc_id = doc.get("id", f"doc_{i}")
                content = doc.get("content", "")
                
                extraction_result = self.extract_from_text(
                    content, extraction_types
                )
                
                extraction_result["document_id"] = doc_id
                extraction_result["document_title"] = doc.get("title", "")
                
                results.append(extraction_result)
                
                # 进度报告
                if (i + 1) % 10 == 0 or i == len(documents) - 1:
                    logger.info(f"批量提取进度: {i+1}/{len(documents)} ({(i+1)/len(documents)*100:.1f}%)")
            
            except Exception as e:
                logger.error(f"文档提取失败: {doc.get('id', f'index_{i}')}, 错误: {str(e)}")
                
                error_result = {
                    "document_id": doc.get("id", f"doc_{i}"),
                    "error": str(e),
                    "extraction_success": False
                }
                
                results.append(error_result)
        
        logger.info(f"批量知识提取完成: 成功 {len([r for r in results if r.get('extraction_success', False)])}/{len(documents)}")
        
        return results
    
    def build_knowledge_graph(self, extraction_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建知识图谱
        
        Args:
            extraction_results: 提取结果列表
            
        Returns:
            知识图谱结构
        """
        try:
            graph_builder = KnowledgeGraphBuilder()
            knowledge_graph = graph_builder.build(extraction_results)
            
            logger.info(f"知识图谱构建完成: 节点={knowledge_graph.get('node_count', 0)}, 边={knowledge_graph.get('edge_count', 0)}")
            
            return knowledge_graph
            
        except Exception as e:
            logger.error(f"知识图谱构建失败: {str(e)}")
            
            return {
                "error": str(e),
                "build_success": False
            }
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符但保留标点（针对中文）
        if self.language.startswith("zh"):
            # 保留中文标点和常见符号
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；："'《》【】（）\-]', ' ', text)
        else:
            # 英文等其他语言
            text = re.sub(r'[^\w\s.,!?;:"\'()\-]', ' ', text)
        
        return text.strip()
    
    def _assess_extraction_quality(self, text: str, 
                                  extraction_result: Dict[str, Any]) -> Dict[str, float]:
        """评估提取质量"""
        quality_metrics = {}
        
        # 文本覆盖率（提取内容占原文的比例）
        if "summary" in extraction_result:
            summary = extraction_result["summary"]
            if isinstance(summary, dict) and "summary_text" in summary:
                summary_text = summary["summary_text"]
            elif isinstance(summary, str):
                summary_text = summary
            else:
                summary_text = ""
            
            coverage = len(summary_text) / max(len(text), 1)
            quality_metrics["coverage"] = min(1.0, coverage)
        
        # 实体密度
        if "entity_count" in extraction_result:
            entity_density = extraction_result["entity_count"] / max(len(text.split()), 1)
            quality_metrics["entity_density"] = min(1.0, entity_density * 10)  # 标准化
        
        # 关系丰富度
        if "relation_count" in extraction_result and "entity_count" in extraction_result:
            if extraction_result["entity_count"] > 0:
                relation_richness = extraction_result["relation_count"] / extraction_result["entity_count"]
                quality_metrics["relation_richness"] = min(1.0, relation_richness)
        
        # 主题多样性
        if "topic_count" in extraction_result:
            topic_diversity = extraction_result["topic_count"] / 10.0  # 假设最多10个主题
            quality_metrics["topic_diversity"] = min(1.0, topic_diversity)
        
        # 综合质量评分
        if quality_metrics:
            quality_metrics["overall_quality"] = sum(quality_metrics.values()) / len(quality_metrics)
        else:
            quality_metrics["overall_quality"] = 0.5
        
        return quality_metrics


class TextSummarizer:
    """文本摘要生成器"""
    
    def __init__(self, language: str = "zh-CN"):
        self.language = language
        
        # 加载停用词
        self.stopwords = self._load_stopwords()
    
    def summarize(self, text: str, 
                  summary_length: Optional[int] = None) -> Dict[str, Any]:
        """
        生成文本摘要
        
        Args:
            text: 输入文本
            summary_length: 摘要长度（句子数）
            
        Returns:
            摘要结果
        """
        try:
            # 分割句子
            sentences = self._split_sentences(text)
            
            if not sentences:
                return {
                    "summary_text": "",
                    "sentence_count": 0,
                    "compression_ratio": 0.0
                }
            
            # 确定摘要长度
            if summary_length is None:
                # 默认取原文句子数的20%，最少1句，最多5句
                target_sentences = max(1, min(5, int(len(sentences) * 0.2)))
            else:
                target_sentences = min(summary_length, len(sentences))
            
            # 计算句子重要性（简化版TF-IDF）
            sentence_scores = self._score_sentences(sentences)
            
            # 选择最重要的句子
            ranked_sentences = sorted(
                enumerate(sentences),
                key=lambda x: sentence_scores[x[0]],
                reverse=True
            )
            
            selected_indices = [idx for idx, _ in ranked_sentences[:target_sentences]]
            selected_indices.sort()  # 保持原文顺序
            
            summary_sentences = [sentences[idx] for idx in selected_indices]
            summary_text = " ".join(summary_sentences)
            
            result = {
                "summary_text": summary_text,
                "sentence_count": target_sentences,
                "compression_ratio": len(summary_text) / max(len(text), 1),
                "selected_sentences": selected_indices,
                "method": "extractive_summarization"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"文本摘要生成失败: {str(e)}")
            
            return {
                "summary_text": f"摘要生成失败: {str(e)}",
                "error": True
            }
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        if self.language.startswith("zh"):
            # 中文句子分割（基于常见标点）
            sentences = re.split(r'[。！？；\n]+', text)
        else:
            # 英文句子分割
            sentences = re.split(r'[.!?;\n]+', text)
        
        # 清理空白句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _score_sentences(self, sentences: List[str]) -> List[float]:
        """计算句子分数"""
        scores = []
        
        for sentence in sentences:
            # 基于句子长度和关键词密度（简化实现）
            words = sentence.split()
            
            # 长度得分（中等长度的句子通常更重要）
            length_score = min(1.0, len(words) / 30.0)  # 标准化到30词
            
            # 关键词密度（假设数字和大写词是关键词）
            keyword_count = 0
            for word in words:
                if word.isdigit() or (len(word) > 1 and word.isupper()):
                    keyword_count += 1
            
            keyword_density = keyword_count / max(len(words), 1)
            
            # 综合分数
            total_score = 0.6 * length_score + 0.4 * keyword_density
            scores.append(total_score)
        
        return scores
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词"""
        stopwords = set()
        
        # 基础停用词（实际应用中应加载完整的停用词列表）
        if self.language.startswith("zh"):
            stopwords.update(["的", "了", "在", "是", "我", "有", "和", "就", 
                            "不", "人", "都", "一", "一个", "上", "也", "很", 
                            "到", "说", "要", "去", "你", "会", "着", "没有", 
                            "看", "好", "自己", "这"])
        else:
            stopwords.update(["the", "a", "an", "and", "or", "but", "in", 
                            "on", "at", "to", "for", "of", "with", "by"])
        
        return stopwords


class EntityExtractor:
    """实体抽取器"""
    
    def __init__(self, language: str = "zh-CN"):
        self.language = language
        
        # 实体类型定义
        self.entity_types = {
            "person": r"\b(?:[张李王刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文)",
            "organization": r"\b(?:公司|集团|企业|机构|部门|中心|研究院|实验室)\b",
            "location": r"\b(?:中国|美国|日本|韩国|英国|法国|德国|北京|上海|广州|深圳|杭州|成都|重庆|武汉|南京|西安|苏州|天津|郑州|长沙|青岛|沈阳|大连|厦门|福州|昆明|贵阳|南宁|海口|石家庄|太原|呼和浩特|长春|哈尔滨|合肥|南昌|济南|武汉|长沙|广州|南宁|海口|成都|贵阳|昆明|拉萨|西安|兰州|西宁|银川|乌鲁木齐)\b",
            "date": r"\b(?:20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}月\d{1,2}日|昨天|今天|明天|上周|本周|下周|上月|本月|下月|去年|今年|明年)\b",
            "money": r"\b(?:[\$￥€]?\d+(?:\.\d+)?\s*(?:万元?|亿元?|百万|千万|亿|美元?|欧元?|英镑?|日元?))\b",
            "percentage": r"\b(?:\d+(?:\.\d+)?%)\b",
            "product": r"\b(?:iPhone|iPad|MacBook|华为|小米|三星|联想|戴尔|惠普|索尼|松下|佳能|尼康|奔驰|宝马|奥迪|丰田|本田|大众|特斯拉)\b",
            "technology": r"\b(?:AI|人工智能|机器学习|深度学习|大数据|云计算|区块链|物联网|5G|VR|AR|元宇宙|ChatGPT|SellAI)\b"
        }
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """
        抽取实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        entities = []
        
        for entity_type, pattern in self.entity_types.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity_text = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                entity = {
                    "text": entity_text,
                    "type": entity_type,
                    "start": start_pos,
                    "end": end_pos,
                    "confidence": self._calculate_confidence(entity_type, entity_text)
                }
                
                entities.append(entity)
        
        # 去重（基于文本和位置）
        unique_entities = self._deduplicate_entities(entities)
        
        # 添加上下文信息
        enriched_entities = self._enrich_entities(unique_entities, text)
        
        logger.debug(f"实体抽取完成: {len(enriched_entities)} 个实体")
        
        return enriched_entities
    
    def _calculate_confidence(self, entity_type: str, entity_text: str) -> float:
        """计算实体置信度"""
        # 基于实体类型和文本特征
        base_confidences = {
            "person": 0.8,
            "organization": 0.7,
            "location": 0.9,
            "date": 0.85,
            "money": 0.75,
            "percentage": 0.95,
            "product": 0.8,
            "technology": 0.7
        }
        
        base_confidence = base_confidences.get(entity_type, 0.5)
        
        # 根据文本长度调整置信度（较长的实体可能更准确）
        length_factor = min(1.0, len(entity_text) / 20.0)
        
        final_confidence = base_confidence * (0.7 + 0.3 * length_factor)
        
        return max(0.0, min(1.0, final_confidence))
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重实体"""
        seen = set()
        unique_entities = []
        
        for entity in entities:
            key = (entity["text"], entity["start"], entity["end"])
            
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _enrich_entities(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """丰富实体信息"""
        for entity in entities:
            # 添加上下文
            start = max(0, entity["start"] - 20)
            end = min(len(text), entity["end"] + 20)
            entity["context"] = text[start:end]
            
            # 添加词性标注（简化）
            entity["pos_tag"] = self._guess_pos_tag(entity["text"])
        
        return entities
    
    def _guess_pos_tag(self, text: str) -> str:
        """猜测词性标记"""
        # 简化实现，实际应用中应使用NLP库
        if re.search(r"\d", text):
            return "NUM"
        elif text.isupper():
            return "PROPN"  # 专有名词
        elif any(keyword in text for keyword in ["公司", "集团", "企业"]):
            return "NOUN"
        else:
            return "NOUN"


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self, language: str = "zh-CN"):
        self.language = language
        
        # 关系模式定义
        self.relation_patterns = [
            # 人物-组织关系
            (r"(\b\w+\b)\s+(?:在|加入|任职于|就职于)\s+(\b[\w公司集团]+\b)", "works_at"),
            # 组织-地点关系
            (r"(\b[\w公司集团]+\b)\s+(?:位于|坐落于|在)\s+(\b\w+\b)", "located_in"),
            # 产品-公司关系
            (r"(\b\w+\b)\s+(?:是|为)\s+(\b[\w公司集团]+\b)\s+的", "product_of"),
            # 时间-事件关系
            (r"(\b\d{4}年\b)\s+(?:发布|推出|成立)\s+(\b\w+\b)", "happened_in"),
            # 因果关系
            (r"(\b\w+\b)\s+(?:导致|引起|使得)\s+(\b\w+\b)", "causes"),
            # 包含关系
            (r"(\b\w+\b)\s+(?:包含|包括)\s+(\b\w+\b)", "contains"),
        ]
    
    def extract(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        抽取关系
        
        Args:
            text: 输入文本
            entities: 实体列表
            
        Returns:
            关系列表
        """
        relations = []
        
        # 1. 基于模式的关系抽取
        pattern_relations = self._extract_by_patterns(text, entities)
        relations.extend(pattern_relations)
        
        # 2. 基于邻近度的关系抽取
        proximity_relations = self._extract_by_proximity(entities, text)
        relations.extend(proximity_relations)
        
        # 去重
        unique_relations = self._deduplicate_relations(relations)
        
        logger.debug(f"关系抽取完成: {len(unique_relations)} 个关系")
        
        return unique_relations
    
    def _extract_by_patterns(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于模式抽取关系"""
        relations = []
        
        for pattern, relation_type in self.relation_patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                entity1_text = match.group(1)
                entity2_text = match.group(2)
                
                # 查找对应的实体
                entity1 = self._find_entity_by_text(entity1_text, entities)
                entity2 = self._find_entity_by_text(entity2_text, entities)
                
                if entity1 and entity2:
                    relation = {
                        "source": entity1["text"],
                        "source_type": entity1["type"],
                        "target": entity2["text"],
                        "target_type": entity2["type"],
                        "relation": relation_type,
                        "confidence": self._calculate_relation_confidence(
                            relation_type, entity1, entity2, match.group()
                        ),
                        "context": match.group(),
                        "extraction_method": "pattern_based"
                    }
                    
                    relations.append(relation)
        
        return relations
    
    def _extract_by_proximity(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """基于邻近度抽取关系"""
        relations = []
        
        # 按位置排序实体
        sorted_entities = sorted(entities, key=lambda x: x["start"])
        
        for i in range(len(sorted_entities) - 1):
            entity1 = sorted_entities[i]
            entity2 = sorted_entities[i + 1]
            
            # 检查邻近度（在同一句子或相近位置）
            distance = entity2["start"] - entity1["end"]
            
            if distance < 50:  # 50个字符内
                # 提取上下文
                start = max(0, entity1["start"] - 30)
                end = min(len(text), entity2["end"] + 30)
                context = text[start:end]
                
                # 猜测关系类型
                relation_type = self._guess_relation_type(entity1, entity2, context)
                
                if relation_type:
                    relation = {
                        "source": entity1["text"],
                        "source_type": entity1["type"],
                        "target": entity2["text"],
                        "target_type": entity2["type"],
                        "relation": relation_type,
                        "confidence": 0.6,  # 邻近度关系置信度较低
                        "context": context,
                        "extraction_method": "proximity_based"
                    }
                    
                    relations.append(relation)
        
        return relations
    
    def _find_entity_by_text(self, entity_text: str, entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """根据文本查找实体"""
        for entity in entities:
            if entity["text"] == entity_text:
                return entity
        
        return None
    
    def _calculate_relation_confidence(self, relation_type: str,
                                     entity1: Dict[str, Any],
                                     entity2: Dict[str, Any],
                                     context: str) -> float:
        """计算关系置信度"""
        base_confidences = {
            "works_at": 0.8,
            "located_in": 0.85,
            "product_of": 0.75,
            "happened_in": 0.9,
            "causes": 0.7,
            "contains": 0.8
        }
        
        base_confidence = base_confidences.get(relation_type, 0.5)
        
        # 根据实体置信度调整
        entity_confidence = (entity1["confidence"] + entity2["confidence"]) / 2
        
        # 根据上下文清晰度调整
        clarity_score = self._assess_context_clarity(context)
        
        final_confidence = base_confidence * 0.4 + entity_confidence * 0.4 + clarity_score * 0.2
        
        return max(0.0, min(1.0, final_confidence))
    
    def _assess_context_clarity(self, context: str) -> float:
        """评估上下文清晰度"""
        # 检查是否有明确的关系指示词
        relation_indicators = [
            "在", "于", "是", "为", "的", "导致", "引起", "包含", "包括",
            "at", "in", "of", "for", "by", "with"
        ]
        
        indicator_count = sum(1 for indicator in relation_indicators 
                            if indicator in context)
        
        # 基于指示词数量评分
        if indicator_count >= 2:
            return 0.9
        elif indicator_count == 1:
            return 0.7
        else:
            return 0.5
    
    def _guess_relation_type(self, entity1: Dict[str, Any],
                            entity2: Dict[str, Any],
                            context: str) -> Optional[str]:
        """猜测关系类型"""
        # 基于实体类型组合猜测
        entity_types = (entity1["type"], entity2["type"])
        
        type_combinations = {
            ("person", "organization"): "works_at",
            ("organization", "location"): "located_in",
            ("product", "organization"): "product_of",
            ("technology", "organization"): "developed_by",
            ("date", "event"): "happened_in"
        }
        
        # 检查已知类型组合
        if entity_types in type_combinations:
            return type_combinations[entity_types]
        
        # 根据上下文关键词猜测
        context_lower = context.lower()
        
        if any(word in context_lower for word in ["导致", "引起", "使得", "causes"]):
            return "causes"
        elif any(word in context_lower for word in ["包含", "包括", "contains"]):
            return "contains"
        elif any(word in context_lower for word in ["在", "位于", "in", "at"]):
            return "located_in"
        
        return None
    
    def _deduplicate_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重关系"""
        seen = set()
        unique_relations = []
        
        for relation in relations:
            key = (
                relation["source"],
                relation["target"],
                relation["relation"]
            )
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
        
        return unique_relations


class TopicModeler:
    """主题建模器"""
    
    def __init__(self, language: str = "zh-CN"):
        self.language = language
        
        # 预定义主题关键词（针对SellAI业务）
        self.predefined_topics = {
            "ai_technology": ["AI", "人工智能", "机器学习", "深度学习", "算法", "模型"],
            "business_intelligence": ["商业智能", "数据分析", "市场趋势", "竞争分析", "战略规划"],
            "ecommerce": ["电商", "跨境电商", "独立站", "Shopify", "亚马逊", "TikTok"],
            "digital_marketing": ["数字营销", "SEO", "社交媒体", "内容营销", "广告投放"],
            "global_business": ["全球业务", "跨国经营", "国际市场", "本地化", "文化适应"],
            "technology_innovation": ["技术创新", "研发", "产品开发", "技术架构", "系统集成"]
        }
    
    def extract_topics(self, text: str, max_topics: int = 5) -> List[Dict[str, Any]]:
        """
        提取主题
        
        Args:
            text: 输入文本
            max_topics: 最大主题数
            
        Returns:
            主题列表
        """
        topics = []
        
        # 1. 基于预定义主题的匹配
        predefined_results = self._match_predefined_topics(text)
        topics.extend(predefined_results)
        
        # 2. 基于关键词聚类的主题发现（如果支持）
        if SKLEARN_SUPPORT and len(text) > 100:
            try:
                discovered_topics = self._discover_topics_by_clustering(text, max_topics - len(topics))
                topics.extend(discovered_topics)
            except Exception as e:
                logger.warning(f"主题聚类失败: {str(e)}")
        
        # 确保不超过最大主题数
        topics = topics[:max_topics]
        
        # 按置信度排序
        topics.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return topics
    
    def _match_predefined_topics(self, text: str) -> List[Dict[str, Any]]:
        """匹配预定义主题"""
        topics = []
        text_lower = text.lower()
        
        for topic_id, keywords in self.predefined_topics.items():
            # 统计关键词出现情况
            keyword_matches = []
            total_weight = 0
            
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # 计算出现频率
                    matches = re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower)
                    frequency = len(matches)
                    
                    keyword_matches.append({
                        "keyword": keyword,
                        "frequency": frequency
                    })
                    
                    total_weight += frequency
            
            if keyword_matches:
                # 计算置信度
                confidence = min(1.0, total_weight / 10.0)  # 标准化
                
                # 中文特有逻辑：如果包含行业特定词汇，提高置信度
                if self.language.startswith("zh"):
                    industry_terms = ["行业", "市场", "产品", "服务", "客户", "需求"]
                    industry_match = any(term in text for term in industry_terms)
                    if industry_match:
                        confidence = min(1.0, confidence + 0.2)
                
                topic = {
                    "topic_id": topic_id,
                    "topic_name": self._get_topic_name(topic_id),
                    "keywords": keyword_matches,
                    "confidence": confidence,
                    "method": "predefined_matching"
                }
                
                topics.append(topic)
        
        return topics
    
    def _discover_topics_by_clustering(self, text: str, max_new_topics: int) -> List[Dict[str, Any]]:
        """通过聚类发现主题"""
        if max_new_topics <= 0:
            return []
        
        try:
            # 分割段落
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            
            if len(paragraphs) < 3:
                return []  # 文本太短，不进行聚类
            
            # 提取TF-IDF特征
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words=list(self._get_stopwords())
            )
            
            tfidf_matrix = vectorizer.fit_transform(paragraphs)
            feature_names = vectorizer.get_feature_names_out()
            
            # 聚类
            n_clusters = min(max_new_topics, len(paragraphs), 5)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # 提取每个簇的关键词
            discovered_topics = []
            
            for cluster_id in range(n_clusters):
                # 获取属于该簇的文档索引
                cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
                
                if not cluster_indices:
                    continue
                
                # 计算簇内TF-IDF平均值
                cluster_vectors = tfidf_matrix[cluster_indices]
                cluster_mean = cluster_vectors.mean(axis=0).A1
                
                # 获取最重要的特征
                top_indices = cluster_mean.argsort()[-5:][::-1]
                top_keywords = [feature_names[i] for i in top_indices]
                
                # 计算置信度（基于簇内文档的相似度）
                cluster_documents = [paragraphs[i] for i in cluster_indices]
                confidence = self._calculate_cluster_confidence(cluster_documents)
                
                topic = {
                    "topic_id": f"discovered_{cluster_id}",
                    "topic_name": "发现主题: " + ", ".join(top_keywords[:3]),
                    "keywords": [{"keyword": kw, "frequency": 1} for kw in top_keywords],
                    "confidence": confidence,
                    "method": "clustering_discovery"
                }
                
                discovered_topics.append(topic)
            
            return discovered_topics
            
        except Exception as e:
            logger.error(f"主题聚类异常: {str(e)}")
            return []
    
    def _get_topic_name(self, topic_id: str) -> str:
        """获取主题名称"""
        topic_names = {
            "ai_technology": "人工智能技术",
            "business_intelligence": "商业智能分析",
            "ecommerce": "电子商务运营",
            "digital_marketing": "数字营销策略",
            "global_business": "全球业务拓展",
            "technology_innovation": "技术创新研发"
        }
        
        return topic_names.get(topic_id, topic_id)
    
    def _get_stopwords(self) -> Set[str]:
        """获取停用词"""
        stopwords = set()
        
        if self.language.startswith("zh"):
            stopwords.update(["的", "了", "在", "是", "我", "有", "和", "就", 
                            "不", "人", "都", "一", "个", "上", "也", "很"])
        else:
            stopwords.update(["the", "a", "an", "and", "or", "but", "in", 
                            "on", "at", "to", "for", "of", "with", "by"])
        
        return stopwords
    
    def _calculate_cluster_confidence(self, documents: List[str]) -> float:
        """计算聚类置信度"""
        if len(documents) < 2:
            return 0.5
        
        # 基于文档数量和长度估算置信度
        avg_length = sum(len(doc) for doc in documents) / len(documents)
        
        # 文档数量越多，置信度越高（但有限制）
        doc_count_score = min(1.0, len(documents) / 5.0)
        
        # 文档长度适中，置信度较高
        length_score = 0.7 if avg_length > 100 else 0.5
        
        return 0.5 * doc_count_score + 0.5 * length_score


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self):
        # 知识图谱结构
        self.graph = {
            "nodes": {},  # 节点ID -> 节点属性
            "edges": {},  # 边ID -> 边属性
            "node_count": 0,
            "edge_count": 0
        }
        
        # 节点和边的ID生成器
        self.next_node_id = 1
        self.next_edge_id = 1
    
    def build(self, extraction_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建知识图谱
        
        Args:
            extraction_results: 提取结果列表
            
        Returns:
            知识图谱
        """
        try:
            # 重置图谱
            self.graph = {
                "nodes": {},
                "edges": {},
                "node_count": 0,
                "edge_count": 0
            }
            
            # 处理每个提取结果
            for result in extraction_results:
                # 添加实体节点
                if "entities" in result:
                    self._add_entities(result["entities"], result.get("document_id", ""))
                
                # 添加关系边
                if "relations" in result:
                    self._add_relations(result["relations"])
                
                # 添加文档节点
                doc_id = result.get("document_id", "")
                if doc_id:
                    self._add_document_node(doc_id, result)
            
            # 构建节点索引
            self._build_node_index()
            
            # 计算图谱指标
            metrics = self._calculate_graph_metrics()
            
            # 构建最终结果
            knowledge_graph = {
                "graph": self.graph,
                "metrics": metrics,
                "build_time": datetime.now().isoformat(),
                "extraction_count": len(extraction_results)
            }
            
            return knowledge_graph
            
        except Exception as e:
            logger.error(f"知识图谱构建失败: {str(e)}")
            
            return {
                "error": str(e),
                "build_success": False
            }
    
    def _add_entities(self, entities: List[Dict[str, Any]], document_id: str):
        """添加实体节点"""
        for entity in entities:
            # 生成节点ID
            node_id = f"entity_{self.next_node_id}"
            self.next_node_id += 1
            
            # 创建节点
            node = {
                "id": node_id,
                "type": "entity",
                "entity_type": entity.get("type", ""),
                "text": entity.get("text", ""),
                "confidence": entity.get("confidence", 0.5),
                "pos_tag": entity.get("pos_tag", ""),
                "context": entity.get("context", ""),
                "source_document": document_id
            }
            
            # 添加到图谱
            self.graph["nodes"][node_id] = node
            
            # 连接到文档节点
            if document_id:
                edge_id = f"edge_{self.next_edge_id}"
                self.next_edge_id += 1
                edge = {
                    "id": edge_id,
                    "source": document_id,
                    "target": node_id,
                    "relation": "mentions",
                    "confidence": entity.get("confidence", 0.5),
                    "weight": 1.0
                }
                
                self.graph["edges"][edge_id] = edge
    
    def _add_relations(self, relations: List[Dict[str, Any]]):
        """添加关系边"""
        for relation in relations:
            # 查找源节点和目标节点
            source_node = self._find_node_by_text(relation.get("source", ""))
            target_node = self._find_node_by_text(relation.get("target", ""))
            
            if source_node and target_node:
                edge_id = f"edge_{self.next_edge_id}"
                self.next_edge_id += 1
                
                edge = {
                    "id": edge_id,
                    "source": source_node["id"],
                    "target": target_node["id"],
                    "relation": relation.get("relation", ""),
                    "confidence": relation.get("confidence", 0.5),
                    "context": relation.get("context", ""),
                    "extraction_method": relation.get("extraction_method", "")
                }
                
                self.graph["edges"][edge_id] = edge
    
    def _add_document_node(self, doc_id: str, result: Dict[str, Any]):
        """添加文档节点"""
        node_id = f"doc_{doc_id}"
        
        node = {
            "id": node_id,
            "type": "document",
            "title": result.get("document_title", ""),
            "text_length": result.get("text_length", 0),
            "extraction_types": result.get("extraction_types", []),
            "extraction_time": result.get("extraction_time", ""),
            "quality_score": result.get("extraction_quality", {}).get("overall_quality", 0.5)
        }
        
        self.graph["nodes"][node_id] = node
    
    def _find_node_by_text(self, text: str) -> Optional[Dict[str, Any]]:
        """根据文本查找节点"""
        for node_id, node in self.graph["nodes"].items():
            if node.get("type") == "entity" and node.get("text") == text:
                return node
        
        return None
    
    def _build_node_index(self):
        """构建节点索引"""
        self.graph["node_count"] = len(self.graph["nodes"])
        self.graph["edge_count"] = len(self.graph["edges"])
    
    def _calculate_graph_metrics(self) -> Dict[str, float]:
        """计算图谱指标"""
        metrics = {}
        
        nodes = self.graph["nodes"]
        edges = self.graph["edges"]
        
        if nodes:
            # 节点类型分布
            entity_nodes = [n for n in nodes.values() if n.get("type") == "entity"]
            doc_nodes = [n for n in nodes.values() if n.get("type") == "document"]
            
            metrics["entity_node_ratio"] = len(entity_nodes) / len(nodes)
            metrics["document_node_ratio"] = len(doc_nodes) / len(nodes)
            
            # 平均置信度
            if entity_nodes:
                metrics["average_entity_confidence"] = (
                    sum(n.get("confidence", 0.5) for n in entity_nodes) / len(entity_nodes)
                )
            
            # 连通性指标
            if edges and len(nodes) > 1:
                metrics["edge_density"] = len(edges) / (len(nodes) * (len(nodes) - 1) / 2)
                
                # 计算平均度数
                degree_sum = 0
                degree_dict = defaultdict(int)
                
                for edge in edges.values():
                    source = edge["source"]
                    target = edge["target"]
                    
                    degree_dict[source] += 1
                    degree_dict[target] += 1
                    degree_sum += 2
                
                if degree_dict:
                    metrics["average_degree"] = degree_sum / len(degree_dict)
        
        return metrics


# 便捷函数
def create_extraction_engine(language: str = "zh-CN") -> KnowledgeExtractionEngine:
    """
    创建知识提取引擎的便捷函数
    
    Args:
        language: 目标语言
        
    Returns:
        知识提取引擎实例
    """
    return KnowledgeExtractionEngine(language)


if __name__ == "__main__":
    # 模块测试
    print("知识提取模块测试")
    
    # 创建提取引擎
    engine = KnowledgeExtractionEngine()
    
    # 测试文本
    test_text = """
    SellAI系统是领先的全球AI商业合伙人平台，于2023年正式推出。
    该系统集成了人工智能技术、大数据分析和商业智能，帮助企业实现数字化转型。
    目前已在北美、欧洲和亚洲等多个市场成功落地，服务超过1000家企业客户。
    SellAI的核心优势在于其深度学习的算法模型和实时的市场情报分析能力。
    """
    
    # 提取知识
    result = engine.extract_from_text(test_text)
    
    print(f"原始文本长度: {len(test_text)} 字符")
    print(f"摘要: {result.get('summary', {}).get('summary_text', '')[:100]}...")
    print(f"实体数量: {result.get('entity_count', 0)}")
    print(f"关系数量: {result.get('relation_count', 0)}")
    print(f"主题数量: {result.get('topic_count', 0)}")
    print(f"提取质量: {result.get('extraction_quality', {}).get('overall_quality', 0):.2f}")