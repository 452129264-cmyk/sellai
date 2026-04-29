"""
跨SellAI网络数据同步模块
实现增量数据同步、冲突解决和跨实例资源检索功能。
"""

import json
import sqlite3
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Tuple, Union
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SyncDomain(Enum):
    """同步域枚举"""
    INDUSTRY_RESOURCES = 'industry_resources'
    RESOURCE_CATEGORIES = 'resource_categories'
    MATCHING_CRITERIA = 'matching_criteria'
    AVATAR_PROFILES = 'avatar_profiles'
    USER_PREFERENCES = 'user_preferences'


class SyncMode(Enum):
    """同步模式枚举"""
    FULL = 'full'
    INCREMENTAL = 'incremental'


class ConflictResolutionStrategy(Enum):
    """冲突解决策略枚举"""
    LAST_WRITE_WINS = 'last_write_wins'
    SOURCE_PRIORITY = 'source_priority'
    MANUAL = 'manual'


@dataclass
class SyncToken:
    """同步令牌"""
    domain: str
    last_sync_time: str  # ISO格式时间戳
    processed_ids: List[str]  # 上次同步已处理的ID列表
    version: int = 1
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'domain': self.domain,
            'last_sync_time': self.last_sync_time,
            'processed_ids': self.processed_ids,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SyncToken':
        """从字典创建"""
        return cls(
            domain=data['domain'],
            last_sync_time=data['last_sync_time'],
            processed_ids=data.get('processed_ids', []),
            version=data.get('version', 1)
        )
    
    def encode(self) -> str:
        """编码为字符串"""
        data = self.to_dict()
        json_str = json.dumps(data, separators=(',', ':'))
        return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    @classmethod
    def decode(cls, encoded_str: str) -> 'SyncToken':
        """从字符串解码"""
        json_str = base64.b64decode(encoded_str).decode('utf-8')
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ResourceFilter:
    """资源过滤器"""
    resource_type: Optional[List[int]] = None
    region_scope: Optional[List[int]] = None
    direction: Optional[str] = None
    updated_since: Optional[str] = None  # ISO格式时间戳
    min_quality_score: Optional[float] = None
    max_results: int = 100
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {'max_results': self.max_results}
        if self.resource_type:
            result['resource_type'] = self.resource_type
        if self.region_scope:
            result['region_scope'] = self.region_scope
        if self.direction:
            result['direction'] = self.direction
        if self.updated_since:
            result['updated_since'] = self.updated_since
        if self.min_quality_score is not None:
            result['min_quality_score'] = self.min_quality_score
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResourceFilter':
        """从字典创建"""
        return cls(
            resource_type=data.get('resource_type'),
            region_scope=data.get('region_scope'),
            direction=data.get('direction'),
            updated_since=data.get('updated_since'),
            min_quality_score=data.get('min_quality_score'),
            max_results=data.get('max_results', 100)
        )


class DataSyncManager:
    """数据同步管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self._init_sync_tables()
    
    def _init_sync_tables(self):
        """初始化同步相关表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 同步状态表，记录每个域与每个节点的同步状态
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                node_id TEXT NOT NULL,
                last_sync_token TEXT,
                last_sync_time TIMESTAMP,
                total_synced_count INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(domain, node_id)
            )
        """)
        
        # 冲突记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                local_version TEXT,
                remote_version TEXT,
                conflict_data TEXT NOT NULL,  -- JSON格式的冲突详情
                resolution_strategy TEXT,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 跨实例匹配缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cross_instance_matches (
                match_cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_signature TEXT NOT NULL,  -- 查询签名
                source_node_id TEXT NOT NULL,
                match_results TEXT NOT NULL,  -- JSON格式的匹配结果
                match_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(query_signature, source_node_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def sync_resources(self, sync_domain: str = 'industry_resources',
                      filters: Optional[Dict] = None,
                      limit: int = 100,
                      offset: int = 0,
                      sync_mode: str = 'incremental',
                      last_sync_token: Optional[str] = None) -> Dict:
        """
        同步资源数据
        
        Args:
            sync_domain: 同步域
            filters: 过滤条件字典
            limit: 每批数量
            offset: 偏移量
            sync_mode: 同步模式（full/incremental）
            last_sync_token: 上次同步令牌
            
        Returns:
            同步结果字典
        """
        try:
            # 解析过滤器
            filter_obj = ResourceFilter.from_dict(filters or {})
            
            # 根据同步模式获取数据
            if sync_mode == 'full':
                resources, total_count = self._get_resources_full(
                    sync_domain, filter_obj, limit, offset
                )
                sync_token = self._generate_sync_token(sync_domain, resources)
            else:
                resources, total_count = self._get_resources_incremental(
                    sync_domain, filter_obj, limit, offset, last_sync_token
                )
                sync_token = self._generate_sync_token(sync_domain, resources, last_sync_token)
            
            # 转换为API格式
            formatted_resources = [
                self._format_resource_for_sync(resource, sync_domain)
                for resource in resources
            ]
            
            return {
                'success': True,
                'sync_domain': sync_domain,
                'sync_token': sync_token.encode() if sync_token else None,
                'resources': formatted_resources,
                'total_count': total_count,
                'has_more': (offset + limit) < total_count,
                'next_offset': offset + limit if (offset + limit) < total_count else None
            }
            
        except Exception as e:
            logger.error(f"同步资源失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'sync_domain': sync_domain,
                'resources': [],
                'total_count': 0,
                'sync_token': None
            }
    
    def _get_resources_full(self, sync_domain: str, filters: ResourceFilter,
                           limit: int, offset: int) -> Tuple[List[Dict], int]:
        """获取全量资源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        query = f"SELECT * FROM {sync_domain} WHERE 1=1"
        params = []
        
        if filters.resource_type:
            placeholders = ','.join('?' * len(filters.resource_type))
            query += f" AND resource_type IN ({placeholders})"
            params.extend(filters.resource_type)
        
        if filters.region_scope:
            placeholders = ','.join('?' * len(filters.region_scope))
            query += f" AND region_scope IN ({placeholders})"
            params.extend(filters.region_scope)
        
        if filters.direction:
            query += " AND direction = ?"
            params.append(filters.direction)
        
        if filters.updated_since:
            query += " AND updated_at >= ?"
            params.append(filters.updated_since)
        
        if filters.min_quality_score is not None:
            query += " AND quality_score >= ?"
            params.append(filters.min_quality_score)
        
        # 获取总数
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)', 1)
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 获取数据
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        resources = []
        for row in rows:
            resource = dict(zip([col[0] for col in cursor.description], row))
            resources.append(resource)
        
        conn.close()
        return resources, total_count
    
    def _get_resources_incremental(self, sync_domain: str, filters: ResourceFilter,
                                  limit: int, offset: int, 
                                  last_sync_token: Optional[str]) -> Tuple[List[Dict], int]:
        """获取增量资源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 解析上次同步令牌
        last_sync_time = None
        processed_ids = []
        
        if last_sync_token:
            try:
                token = SyncToken.decode(last_sync_token)
                last_sync_time = token.last_sync_time
                processed_ids = token.processed_ids
            except Exception:
                logger.warning(f"无效的同步令牌: {last_sync_token}")
        
        # 构建查询
        query = f"SELECT * FROM {sync_domain} WHERE 1=1"
        params = []
        
        # 时间过滤：获取上次同步后更新的记录
        if last_sync_time:
            query += " AND updated_at > ?"
            params.append(last_sync_time)
        
        # 应用其他过滤器
        if filters.resource_type:
            placeholders = ','.join('?' * len(filters.resource_type))
            query += f" AND resource_type IN ({placeholders})"
            params.extend(filters.resource_type)
        
        if filters.region_scope:
            placeholders = ','.join('?' * len(filters.region_scope))
            query += f" AND region_scope IN ({placeholders})"
            params.extend(filters.region_scope)
        
        if filters.direction:
            query += " AND direction = ?"
            params.append(filters.direction)
        
        if filters.min_quality_score is not None:
            query += " AND quality_score >= ?"
            params.append(filters.min_quality_score)
        
        # 排除已处理的ID（如果有）
        if processed_ids:
            placeholders = ','.join('?' * len(processed_ids))
            query += f" AND resource_id NOT IN ({placeholders})"
            params.extend(processed_ids)
        
        # 获取总数
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)', 1)
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 获取数据
        query += " ORDER BY updated_at ASC LIMIT ? OFFSET ?"  # 按时间升序确保顺序
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        resources = []
        for row in rows:
            resource = dict(zip([col[0] for col in cursor.description], row))
            resources.append(resource)
        
        conn.close()
        return resources, total_count
    
    def _generate_sync_token(self, domain: str, resources: List[Dict],
                            last_token: Optional[str] = None) -> SyncToken:
        """生成同步令牌"""
        # 获取最新的更新时间
        latest_time = None
        if resources:
            latest_times = [r.get('updated_at') for r in resources if r.get('updated_at')]
            if latest_times:
                latest_time = max(latest_times)
        
        if not latest_time:
            latest_time = datetime.now(timezone.utc).isoformat()
        
        # 获取资源ID列表
        resource_ids = [str(r.get('resource_id', '')) for r in resources]
        
        # 合并上次已处理的ID
        processed_ids = []
        if last_token:
            try:
                token = SyncToken.decode(last_token)
                processed_ids = token.processed_ids
            except Exception:
                pass
        
        # 去重
        all_ids = list(set(processed_ids + resource_ids))
        
        return SyncToken(
            domain=domain,
            last_sync_time=latest_time,
            processed_ids=all_ids[:1000],  # 限制大小
            version=1
        )
    
    def _format_resource_for_sync(self, resource: Dict, domain: str) -> Dict:
        """格式化资源用于同步"""
        # 基本字段映射
        formatted = {}
        
        if domain == 'industry_resources':
            # industry_resources表的字段映射
            field_mapping = {
                'resource_id': 'resource_id',
                'resource_title': 'resource_title',
                'resource_description': 'resource_description',
                'resource_type': 'resource_type',
                'industry_path': 'industry_path',
                'region_scope': 'region_scope',
                'country_code': 'country_code',
                'cooperation_mode': 'cooperation_mode',
                'budget_range': 'budget_range',
                'timeline': 'timeline',
                'direction': 'direction',
                'status': 'status',
                'quality_score': 'quality_score',
                'source_platform': 'source_platform',
                'source_url': 'source_url',
                'source_id': 'source_id',
                'contact_name': 'contact_name',
                'contact_email': 'contact_email',
                'contact_phone': 'contact_phone',
                'contact_company': 'contact_company',
                'created_by_avatar': 'created_by_avatar',
                'last_updated_by_avatar': 'last_updated_by_avatar',
                'viewed_count': 'viewed_count',
                'matched_count': 'matched_count',
                'expires_at': 'expires_at',
                'created_at': 'created_at',
                'updated_at': 'updated_at'
            }
            
            for src_field, dst_field in field_mapping.items():
                if src_field in resource:
                    value = resource[src_field]
                    # 处理JSON字段
                    if isinstance(value, str) and (
                        src_field in ['industry_path', 'budget_range', 'timeline', 
                                     'region_details'] or
                        (src_field.startswith('{') and src_field.endswith('}'))
                    ):
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    
                    formatted[dst_field] = value
        
        elif domain == 'resource_categories':
            # resource_categories表的字段映射
            field_mapping = {
                'category_id': 'category_id',
                'category_type': 'category_type',
                'category_code': 'category_code',
                'category_name': 'category_name',
                'description': 'description',
                'parent_category_id': 'parent_category_id',
                'metadata': 'metadata',
                'created_at': 'created_at',
                'updated_at': 'updated_at'
            }
            
            for src_field, dst_field in field_mapping.items():
                if src_field in resource:
                    formatted[dst_field] = resource[src_field]
        
        # 添加版本信息
        formatted['_version'] = 1
        formatted['_sync_domain'] = domain
        
        return formatted
    
    def receive_resources(self, resources: List[Dict], source_node_id: str,
                         conflict_strategy: str = 'last_write_wins') -> Dict:
        """
        接收来自其他节点的资源数据，处理冲突
        
        Args:
            resources: 资源列表
            source_node_id: 源节点ID
            conflict_strategy: 冲突解决策略
            
        Returns:
            处理结果
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'conflicts': 0,
            'errors': 0
        }
        
        for resource in resources:
            try:
                domain = resource.get('_sync_domain', 'industry_resources')
                resource_id = resource.get('resource_id')
                
                if not resource_id:
                    stats['errors'] += 1
                    continue
                
                # 检查本地是否存在
                cursor.execute(f"SELECT * FROM {domain} WHERE resource_id = ?", (resource_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # 存在冲突，需要解决
                    stats['conflicts'] += 1
                    resolution = self._resolve_conflict(
                        existing, resource, source_node_id, conflict_strategy
                    )
                    
                    if resolution['action'] == 'update':
                        # 更新记录
                        self._update_resource(conn, cursor, domain, resource_id, resource)
                        stats['updated'] += 1
                        
                        # 记录冲突
                        self._log_conflict(conn, cursor, domain, resource_id,
                                         existing, resource, resolution)
                    else:
                        stats['skipped'] += 1
                else:
                    # 插入新记录
                    self._insert_resource(conn, cursor, domain, resource)
                    stats['inserted'] += 1
                    
            except Exception as e:
                logger.error(f"处理资源失败: {e}", exc_info=True)
                stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'stats': stats,
            'message': f"处理完成: {stats['inserted']}新增, {stats['updated']}更新, "
                      f"{stats['skipped']}跳过, {stats['conflicts']}冲突, "
                      f"{stats['errors']}错误"
        }
    
    def _resolve_conflict(self, existing: sqlite3.Row, incoming: Dict,
                         source_node_id: str, strategy: str) -> Dict:
        """解决数据冲突"""
        existing_dict = dict(existing)
        
        # 策略：最后写入优先
        if strategy == 'last_write_wins':
            existing_time = existing_dict.get('updated_at')
            incoming_time = incoming.get('updated_at')
            
            if existing_time and incoming_time:
                # 比较时间戳
                if incoming_time > existing_time:
                    return {'action': 'update', 'reason': 'incoming newer'}
                else:
                    return {'action': 'skip', 'reason': 'existing newer'}
            else:
                # 无法比较，默认更新
                return {'action': 'update', 'reason': 'default update'}
        
        # 策略：源节点优先
        elif strategy == 'source_priority':
            # 假设源节点数据更可信
            return {'action': 'update', 'reason': 'source priority'}
        
        # 策略：手动解决
        elif strategy == 'manual':
            # 记录冲突，等待人工解决
            return {'action': 'skip', 'reason': 'manual resolution required'}
        
        # 默认：最后写入优先
        else:
            return {'action': 'update', 'reason': 'default strategy'}
    
    def _update_resource(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor,
                        domain: str, resource_id: Union[int, str], resource: Dict):
        """更新资源记录"""
        if domain == 'industry_resources':
            # 构建UPDATE语句
            fields = []
            params = []
            
            for field in ['resource_title', 'resource_description', 'resource_type',
                         'industry_path', 'region_scope', 'country_code', 'cooperation_mode',
                         'budget_range', 'timeline', 'direction', 'status', 'quality_score',
                         'source_platform', 'source_url', 'source_id', 'contact_name',
                         'contact_email', 'contact_phone', 'contact_company',
                         'last_updated_by_avatar', 'viewed_count', 'matched_count',
                         'expires_at', 'updated_at']:
                if field in resource:
                    value = resource[field]
                    # 处理JSON字段
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    
                    fields.append(f"{field} = ?")
                    params.append(value)
            
            # 添加更新时间
            if 'updated_at' not in resource:
                fields.append("updated_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
            
            params.append(resource_id)
            
            query = f"UPDATE {domain} SET {', '.join(fields)} WHERE resource_id = ?"
            cursor.execute(query, params)
    
    def _insert_resource(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor,
                        domain: str, resource: Dict):
        """插入资源记录"""
        if domain == 'industry_resources':
            # 构建INSERT语句
            fields = []
            placeholders = []
            params = []
            
            for field in ['resource_id', 'resource_title', 'resource_description',
                         'resource_type', 'industry_path', 'region_scope', 'country_code',
                         'cooperation_mode', 'budget_range', 'timeline', 'direction',
                         'status', 'quality_score', 'source_platform', 'source_url',
                         'source_id', 'contact_name', 'contact_email', 'contact_phone',
                         'contact_company', 'created_by_avatar', 'last_updated_by_avatar',
                         'viewed_count', 'matched_count', 'expires_at', 'created_at',
                         'updated_at']:
                if field in resource:
                    value = resource[field]
                    # 处理JSON字段
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    
                    fields.append(field)
                    placeholders.append('?')
                    params.append(value)
            
            # 确保必要字段存在
            if 'created_at' not in resource:
                fields.append('created_at')
                placeholders.append('?')
                params.append(datetime.now(timezone.utc).isoformat())
            
            if 'updated_at' not in resource:
                fields.append('updated_at')
                placeholders.append('?')
                params.append(datetime.now(timezone.utc).isoformat())
            
            query = f"INSERT INTO {domain} ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, params)
    
    def _log_conflict(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor,
                     domain: str, resource_id: Union[int, str],
                     existing: sqlite3.Row, incoming: Dict, resolution: Dict):
        """记录冲突"""
        conflict_data = {
            'domain': domain,
            'resource_id': resource_id,
            'existing_data': dict(existing),
            'incoming_data': incoming,
            'resolution': resolution,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        cursor.execute("""
            INSERT INTO sync_conflicts 
            (domain, resource_id, local_version, remote_version, conflict_data, resolution_strategy)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            domain,
            str(resource_id),
            json.dumps(dict(existing), ensure_ascii=False),
            json.dumps(incoming, ensure_ascii=False),
            json.dumps(conflict_data, ensure_ascii=False),
            resolution.get('reason', 'unknown')
        ))
    
    def find_cross_instance_matches(self, query_resource: Dict,
                                   min_score: float = 0.7,
                                   max_results: int = 20) -> List[Dict]:
        """
        查找跨实例匹配的资源
        
        Args:
            query_resource: 查询资源描述
            min_score: 最小匹配分数
            max_results: 最大返回结果数
            
        Returns:
            匹配结果列表
        """
        try:
            # 从查询资源中提取匹配条件
            match_conditions = self._extract_match_conditions(query_resource)
            
            # 在本地数据库中查找匹配
            matches = self._find_local_matches(match_conditions, min_score, max_results)
            
            # 格式化结果
            formatted_matches = []
            for match in matches:
                score = self._calculate_match_score(match_conditions, match)
                if score >= min_score:
                    formatted_matches.append({
                        'resource': match,
                        'match_score': score,
                        'match_reason': self._generate_match_reason(match_conditions, match),
                        'source_node_id': 'local'  # 实际应为节点ID
                    })
            
            # 按匹配分数排序
            formatted_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return formatted_matches[:max_results]
            
        except Exception as e:
            logger.error(f"查找匹配失败: {e}", exc_info=True)
            return []
    
    def _extract_match_conditions(self, query_resource: Dict) -> Dict:
        """从查询资源中提取匹配条件"""
        conditions = {}
        
        # 提取基本条件
        if 'resource_type' in query_resource:
            conditions['resource_type'] = query_resource['resource_type']
        
        if 'industry_path' in query_resource:
            conditions['industry_path'] = query_resource['industry_path']
        
        if 'region_scope' in query_resource:
            conditions['region_scope'] = query_resource['region_scope']
        
        if 'direction' in query_resource:
            conditions['direction'] = query_resource['direction']
        
        # 提取预算范围
        if 'budget_range' in query_resource:
            conditions['budget_range'] = query_resource['budget_range']
        
        # 提取时间线
        if 'timeline' in query_resource:
            conditions['timeline'] = query_resource['timeline']
        
        return conditions
    
    def _find_local_matches(self, conditions: Dict, min_score: float, 
                           max_results: int) -> List[Dict]:
        """在本地查找匹配资源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        query = "SELECT * FROM industry_resources WHERE status = 'active'"
        params = []
        
        # 方向匹配：查询需求则匹配供应，反之亦然
        if 'direction' in conditions:
            query_direction = conditions['direction']
            target_direction = 'supply' if query_direction == 'demand' else 'demand'
            query += " AND direction = ?"
            params.append(target_direction)
        
        # 资源类型匹配
        if 'resource_type' in conditions:
            query += " AND resource_type = ?"
            params.append(conditions['resource_type'])
        
        # 地域范围匹配
        if 'region_scope' in conditions:
            # 简单匹配：相同地域或全球范围
            query += " AND (region_scope = ? OR region_scope = 1)"  # 假设1是全球
            params.append(conditions['region_scope'])
        
        # 质量分数筛选
        query += " AND quality_score >= ?"
        params.append(min_score)
        
        # 限制结果数
        query += " LIMIT ?"
        params.append(max_results * 3)  # 获取更多用于评分
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典
        resources = []
        for row in rows:
            resource = dict(zip([col[0] for col in cursor.description], row))
            
            # 解析JSON字段
            for field in ['industry_path', 'budget_range', 'timeline', 'region_details']:
                if field in resource and isinstance(resource[field], str):
                    try:
                        resource[field] = json.loads(resource[field])
                    except:
                        pass
            
            resources.append(resource)
        
        conn.close()
        return resources
    
    def _calculate_match_score(self, conditions: Dict, resource: Dict) -> float:
        """计算匹配分数"""
        score = 0.0
        total_weight = 0
        
        # 1. 方向匹配（权重：0.3）
        if 'direction' in conditions and 'direction' in resource:
            query_dir = conditions['direction']
            resource_dir = resource['direction']
            
            # 需求对供应，供应对需求
            if (query_dir == 'demand' and resource_dir == 'supply') or \
               (query_dir == 'supply' and resource_dir == 'demand'):
                score += 0.3
                total_weight += 0.3
        
        # 2. 资源类型匹配（权重：0.2）
        if 'resource_type' in conditions and 'resource_type' in resource:
            if conditions['resource_type'] == resource['resource_type']:
                score += 0.2
                total_weight += 0.2
        
        # 3. 行业路径匹配（权重：0.2）
        if 'industry_path' in conditions and 'industry_path' in resource:
            query_path = conditions['industry_path']
            resource_path = resource['industry_path']
            
            if isinstance(query_path, list) and isinstance(resource_path, list):
                # 计算共同分类
                common = len(set(query_path) & set(resource_path))
                total_categories = len(set(query_path) | set(resource_path))
                
                if total_categories > 0:
                    industry_score = (common / total_categories) * 0.2
                    score += industry_score
                    total_weight += 0.2
        
        # 4. 预算范围匹配（权重：0.15）
        if 'budget_range' in conditions and 'budget_range' in resource:
            query_budget = conditions['budget_range']
            resource_budget = resource['budget_range']
            
            if isinstance(query_budget, dict) and isinstance(resource_budget, dict):
                # 简化匹配：检查预算重叠
                query_min = query_budget.get('min', 0)
                query_max = query_budget.get('max', float('inf'))
                resource_min = resource_budget.get('min', 0)
                resource_max = resource_budget.get('max', float('inf'))
                
                if query_max >= resource_min and resource_max >= query_min:
                    # 有重叠
                    budget_score = 0.15
                    score += budget_score
                    total_weight += 0.15
        
        # 5. 质量分数加成（权重：0.15）
        if 'quality_score' in resource:
            quality = resource['quality_score'] or 0.0
            quality_score = quality * 0.15
            score += quality_score
            total_weight += 0.15
        
        # 归一化分数
        if total_weight > 0:
            normalized_score = score / total_weight
        else:
            normalized_score = 0.0
        
        return round(min(normalized_score, 1.0), 4)
    
    def _generate_match_reason(self, conditions: Dict, resource: Dict) -> str:
        """生成匹配原因描述"""
        reasons = []
        
        # 方向匹配
        if 'direction' in conditions and 'direction' in resource:
            query_dir = conditions['direction']
            resource_dir = resource['direction']
            
            if (query_dir == 'demand' and resource_dir == 'supply'):
                reasons.append("供需匹配（需求↔供应）")
            elif (query_dir == 'supply' and resource_dir == 'demand'):
                reasons.append("供需匹配（供应↔需求）")
        
        # 资源类型匹配
        if 'resource_type' in conditions and 'resource_type' in resource:
            if conditions['resource_type'] == resource['resource_type']:
                reasons.append("资源类型一致")
        
        # 地域匹配
        if 'region_scope' in conditions and 'region_scope' in resource:
            if conditions['region_scope'] == resource['region_scope']:
                reasons.append("地域范围匹配")
        
        # 质量分数
        if 'quality_score' in resource and resource['quality_score'] >= 0.8:
            reasons.append("高质量资源")
        
        if not reasons:
            return "基于综合评分匹配"
        
        return "；".join(reasons)
    
    def update_sync_status(self, domain: str, node_id: str,
                          sync_token: Optional[str] = None,
                          synced_count: int = 0,
                          error: Optional[str] = None):
        """更新同步状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_status 
            (domain, node_id, last_sync_token, last_sync_time, total_synced_count, last_error, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
        """, (domain, node_id, sync_token, synced_count, error))
        
        conn.commit()
        conn.close()


# 辅助函数
import base64

def calculate_resource_hash(resource: Dict) -> str:
    """计算资源哈希值，用于去重"""
    # 创建可哈希的字符串表示
    resource_str = json.dumps(resource, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(resource_str.encode('utf-8')).hexdigest()


def create_default_sync_manager() -> DataSyncManager:
    """创建默认的数据同步管理器"""
    return DataSyncManager("data/shared_state/state.db")


# 测试代码
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 简单测试
    manager = create_default_sync_manager()
    
    # 测试同步功能
    filters = {
        'resource_type': [1, 2],
        'direction': 'supply',
        'max_results': 10
    }
    
    result = manager.sync_resources(
        sync_domain='industry_resources',
        filters=filters,
        limit=5
    )
    
    print(f"同步结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 测试匹配功能
    query_resource = {
        'resource_type': 1,
        'direction': 'demand',
        'industry_path': [1, 10],
        'budget_range': {'currency': 'USD', 'min': 10000, 'max': 50000}
    }
    
    matches = manager.find_cross_instance_matches(
        query_resource=query_resource,
        min_score=0.6,
        max_results=5
    )
    
    print(f"\n找到 {len(matches)} 个匹配:")
    for i, match in enumerate(matches):
        print(f"  {i+1}. 分数: {match['match_score']:.3f} - {match['resource'].get('resource_title', '无标题')}")