#!/usr/bin/env python3
"""
SellAI v3.0.0 - 行业资源导入
Industry Resource Importer
整合各行业数据资源

功能：
- 行业数据导入
- 资源分类管理
- 数据清洗
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    DATASET = "dataset"
    API = "api"
    DOCUMENT = "document"
    TEMPLATE = "template"
    MODEL = "model"


class Industry(Enum):
    ECOMMERCE = "ecommerce"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    MANUFACTURING = "manufacturing"
    MEDIA = "media"
    RETAIL = "retail"
    TRAVEL = "travel"


@dataclass
class Resource:
    resource_id: str
    name: str
    description: str
    industry: Industry
    resource_type: ResourceType
    source: str
    url: Optional[str] = None
    data_format: str = "json"
    size: int = 0
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    imported_at: str = field(default_factory=lambda: datetime.now().isoformat())


class IndustryResourceImporter:
    """行业资源导入器"""
    
    def __init__(self, db_path: str = "data/shared_state/industry_resources.db"):
        self.db_path = db_path
        self.resources: Dict[str, Resource] = {}
        self.categories: Dict[str, List[str]] = {}
        self._ensure_data_dir()
        self._init_default_resources()
        logger.info("行业资源导入器初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_default_resources(self):
        defaults = [
            Resource(
                resource_id="res_ecom_001",
                name="电商产品分类数据",
                description="标准化电商产品分类",
                industry=Industry.ECOMMERCE,
                resource_type=ResourceType.DATASET,
                source="官方",
                tags=["分类", "产品", "标准化"]
            ),
            Resource(
                resource_id="res_ecom_002",
                name="Shopify API文档",
                description="Shopify REST API完整文档",
                industry=Industry.ECOMMERCE,
                resource_type=ResourceType.API,
                source="Shopify",
                tags=["API", "Shopify", "集成"]
            )
        ]
        for r in defaults:
            self.resources[r.resource_id] = r
    
    def import_resource(self, name: str, description: str,
                       industry: Industry, resource_type: ResourceType,
                       source: str, **kwargs) -> Resource:
        resource_id = f"res_{uuid.uuid4().hex[:8]}"
        resource = Resource(
            resource_id=resource_id,
            name=name,
            description=description,
            industry=industry,
            resource_type=resource_type,
            source=source,
            **kwargs
        )
        self.resources[resource_id] = resource
        logger.info(f"导入资源: {resource_id} - {name}")
        return resource
    
    def search_resources(self, industry: Optional[Industry] = None,
                        resource_type: Optional[ResourceType] = None,
                        query: Optional[str] = None) -> List[Resource]:
        results = list(self.resources.values())
        
        if industry:
            results = [r for r in results if r.industry == industry]
        if resource_type:
            results = [r for r in results if r.resource_type == resource_type]
        if query:
            q = query.lower()
            results = [r for r in results if q in r.name.lower() or q in r.description.lower()]
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": "IndustryResourceImporter",
            "total_resources": len(self.resources),
            "by_industry": {i.value: len([r for r in self.resources.values() if r.industry == i])
                          for i in Industry}
        }


__all__ = ["IndustryResourceImporter", "Resource", "ResourceType", "Industry"]
