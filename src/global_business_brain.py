#!/usr/bin/env python3
"""
全域商业大脑核心模块
整合全行业商业资源库、跨SellAI网络协议、AI自主商务洽谈引擎，
提供统一的全球市场分析、趋势识别、机会评估和资源匹配能力。
支持跨实例协同逻辑，确保所有SellAI保持一致的全球市场认知。
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import hashlib
import logging
from enum import Enum
import sys
import os

# 添加路径以便导入其他模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入相关模块
try:
    from src.industry_resource_importer import IndustryResourceImporter
    HAS_INDUSTRY_RESOURCE = True
except ImportError:
    HAS_INDUSTRY_RESOURCE = False
    logging.warning("industry_resource_importer 模块未找到，相关功能将受限")

try:
    from src.sellai_network_client import SellAINetworkClient
    HAS_NETWORK_CLIENT = True
except ImportError:
    HAS_NETWORK_CLIENT = False
    logging.warning("sellai_network_client 模块未找到，跨实例协同功能将受限")

try:
    from src.ai_negotiation_engine import AINegotiationEngine
    HAS_NEGOTIATION_ENGINE = True
except ImportError:
    HAS_NEGOTIATION_ENGINE = False
    logging.warning("ai_negotiation_engine 模块未找到，谈判评估功能将受限")

try:
    from src.shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    logging.warning("shared_state_manager 模块未找到，状态管理功能将受限")

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MarketDimension(Enum):
    """市场分析维度"""
    ECONOMIC = "economic"  # 经济指标
    INDUSTRY = "industry"  # 行业趋势
    COMPETITIVE = "competitive"  # 竞争格局
    CONSUMER = "consumer"  # 消费者行为
    TECHNOLOGICAL = "technological"  # 技术发展
    REGULATORY = "regulatory"  # 政策法规
    SUPPLY_CHAIN = "supply_chain"  # 供应链状况
    FINANCIAL = "financial"  # 财务指标


class OpportunityRiskLevel(Enum):
    """机会风险评估等级"""
    VERY_LOW = "very_low"  # 风险极低
    LOW = "low"           # 风险低
    MEDIUM = "medium"     # 风险中等
    HIGH = "high"         # 风险高
    VERY_HIGH = "very_high"  # 风险极高


class GlobalBusinessBrain:
    """全域商业大脑核心类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化全域商业大脑
        
        Args:
            config: 配置字典，包含：
                - db_path: 数据库路径（默认: "data/shared_state/state.db"）
                - node_id: 本节点ID
                - enable_network: 是否启用网络协同
                - network_config: 网络客户端配置
                - analysis_period: 分析周期（天，默认: 30）
        """
        self.config = config or {}
        self.db_path = self.config.get('db_path', 'data/shared_state/state.db')
        self.node_id = self.config.get('node_id', 'default_node')
        self.enable_network = self.config.get('enable_network', False)
        self.analysis_period = self.config.get('analysis_period', 30)  # 默认分析30天数据
        
        # 初始化组件
        self._init_components()
        
        # 认知状态
        self.cognition_baseline = None
        self.market_insights = {}
        self.collaborative_assessments = {}
        
        logger.info(f"全域商业大脑初始化完成，节点ID: {self.node_id}")
    
    def _init_components(self):
        """初始化各功能组件"""
        # 行业资源导入器
        if HAS_INDUSTRY_RESOURCE:
            self.resource_importer = IndustryResourceImporter(self.db_path)
        else:
            self.resource_importer = None
            
        # 共享状态管理器
        if HAS_SHARED_STATE:
            self.state_manager = SharedStateManager(self.db_path)
        else:
            self.state_manager = None
            
        # AI谈判引擎
        if HAS_NEGOTIATION_ENGINE:
            self.negotiation_engine = AINegotiationEngine(self.db_path)
        else:
            self.negotiation_engine = None
            
        # 网络客户端（如果启用）
        self.network_client = None
        if self.enable_network and HAS_NETWORK_CLIENT:
            network_config = self.config.get('network_config', {
                'node_id': self.node_id,
                'api_key_id': 'key_default',
                'api_secret': 'secret_default',
                'coordinator_url': 'https://coordinator.sellai.network',
                'default_timeout': 30,
                'max_retries': 3
            })
            self.network_client = SellAINetworkClient(network_config)
    
    def generate_global_market_analysis(self, 
                                      regions: List[str] = None,
                                      industries: List[str] = None,
                                      dimensions: List[MarketDimension] = None) -> Dict[str, Any]:
        """
        生成全球市场分析报告
        
        Args:
            regions: 地区列表，如["north_america", "europe", "asia"]
            industries: 行业列表，如["manufacturing", "retail_ecommerce", "technology"]
            dimensions: 分析维度列表
            
        Returns:
            结构化分析报告
        """
        logger.info(f"开始生成全球市场分析报告，区域: {regions}, 行业: {industries}")
        
        # 设置默认值
        if regions is None:
            regions = ["global"]  # 默认全球分析
        if industries is None:
            industries = ["all"]  # 默认所有行业
        if dimensions is None:
            dimensions = [dim for dim in MarketDimension]
        
        # 收集分析数据
        analysis_data = self._collect_analysis_data(regions, industries)
        
        # 按维度分析
        dimension_analysis = {}
        for dimension in dimensions:
            dimension_analysis[dimension.value] = self._analyze_by_dimension(
                analysis_data, dimension
            )
        
        # 识别关键趋势
        key_trends = self._identify_key_trends(dimension_analysis)
        
        # 评估市场机会
        market_opportunities = self._assess_market_opportunities(
            analysis_data, dimension_analysis
        )
        
        # 生成风险预警
        risk_alerts = self._generate_risk_alerts(dimension_analysis)
        
        # 构建报告
        report = {
            "report_id": f"market_analysis_{int(time.time())}_{self.node_id}",
            "generated_at": datetime.now().isoformat(),
            "generated_by": self.node_id,
            "scope": {
                "regions": regions,
                "industries": industries,
                "dimensions": [dim.value for dim in dimensions],
                "analysis_period_days": self.analysis_period
            },
            "executive_summary": {
                "overall_market_health": self._calculate_market_health_score(dimension_analysis),
                "key_trends_count": len(key_trends),
                "opportunities_count": len(market_opportunities),
                "risk_alerts_count": len(risk_alerts),
                "recommendations": self._generate_recommendations(key_trends, market_opportunities, risk_alerts)
            },
            "dimension_analysis": dimension_analysis,
            "key_trends": key_trends,
            "market_opportunities": market_opportunities,
            "risk_alerts": risk_alerts,
            "data_summary": {
                "total_resources_analyzed": analysis_data.get('total_resources', 0),
                "time_range": analysis_data.get('time_range', {}),
                "data_sources": analysis_data.get('data_sources', [])
            }
        }
        
        logger.info(f"全球市场分析报告生成完成，ID: {report['report_id']}")
        return report
    
    def _collect_analysis_data(self, regions: List[str], industries: List[str]) -> Dict[str, Any]:
        """收集分析所需数据"""
        data = {
            'resources': [],
            'market_insights': [],
            'negotiation_history': [],
            'supply_chain_data': [],
            'consumer_data': [],
            'total_resources': 0,
            'time_range': {},
            'data_sources': []
        }
        
        try:
            # 从行业资源库获取数据
            if self.resource_importer:
                conn = self.resource_importer.connect()
                cursor = conn.cursor()
                
                # 构建查询条件
                conditions = []
                params = []
                
                # 时间范围条件 - 使用正确的列名
                start_date = datetime.now() - timedelta(days=self.analysis_period)
                conditions.append("created_at >= ?")
                params.append(start_date.isoformat())
                
                # 地区条件
                if regions and "global" not in regions:
                    region_conditions = []
                    for region in regions:
                        # 注意：实际列名可能需要调整
                        region_conditions.append("region_scope LIKE ?")
                        params.append(f"%{region}%")
                    if region_conditions:
                        conditions.append(f"({' OR '.join(region_conditions)})")
                
                # 行业条件
                if industries and "all" not in industries:
                    industry_conditions = []
                    for industry in industries:
                        industry_conditions.append("industry_path LIKE ?")
                        params.append(f"%{industry}%")
                    if industry_conditions:
                        conditions.append(f"({' OR '.join(industry_conditions)})")
                
                # 执行查询
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                query = f"""
                    SELECT resource_id as id, 
                           resource_title as title, 
                           resource_description as description,
                           industry_path,
                           resource_type,
                           region_scope,
                           direction,
                           quality_score,
                           relevance_score,
                           status,
                           created_at
                    FROM industry_resources 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT 1000
                """
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    resource = dict(row)
                    data['resources'].append(resource)
                
                data['total_resources'] = len(data['resources'])
                data['time_range'] = {
                    'start': start_date.isoformat(),
                    'end': datetime.now().isoformat(),
                    'days': self.analysis_period
                }
                data['data_sources'].append('industry_resources')
                
                self.resource_importer.close()
            
            # 从共享状态库获取其他数据
            if self.state_manager:
                # 这里可以添加从其他表获取数据的逻辑
                pass
                
        except Exception as e:
            logger.error(f"收集分析数据时出错: {e}")
        
        return data
    
    def _analyze_by_dimension(self, data: Dict[str, Any], dimension: MarketDimension) -> Dict[str, Any]:
        """按维度分析数据"""
        analysis = {
            'dimension': dimension.value,
            'indicators': {},
            'trends': [],
            'insights': [],
            'score': 0.0,
            'confidence': 0.0
        }
        
        try:
            if dimension == MarketDimension.ECONOMIC:
                analysis.update(self._analyze_economic_dimension(data))
            elif dimension == MarketDimension.INDUSTRY:
                analysis.update(self._analyze_industry_dimension(data))
            elif dimension == MarketDimension.COMPETITIVE:
                analysis.update(self._analyze_competitive_dimension(data))
            elif dimension == MarketDimension.CONSUMER:
                analysis.update(self._analyze_consumer_dimension(data))
            elif dimension == MarketDimension.TECHNOLOGICAL:
                analysis.update(self._analyze_technological_dimension(data))
            elif dimension == MarketDimension.REGULATORY:
                analysis.update(self._analyze_regulatory_dimension(data))
            elif dimension == MarketDimension.SUPPLY_CHAIN:
                analysis.update(self._analyze_supply_chain_dimension(data))
            elif dimension == MarketDimension.FINANCIAL:
                analysis.update(self._analyze_financial_dimension(data))
                
        except Exception as e:
            logger.error(f"分析维度 {dimension.value} 时出错: {e}")
            analysis['insights'].append(f"分析过程中出现错误: {str(e)}")
        
        return analysis
    
    def _analyze_economic_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析经济维度"""
        result = {
            'indicators': {
                'growth_trend': 'stable',
                'inflation_risk': 'low',
                'market_liquidity': 'high'
            },
            'trends': [
                {'trend': 'global_growth_moderation', 'strength': 0.7, 'impact': 'medium'},
                {'trend': 'regional_divergence', 'strength': 0.6, 'impact': 'high'}
            ],
            'insights': [
                '全球经济呈现温和增长态势，主要经济体表现分化',
                '通胀压力整体可控，但需关注供应链因素'
            ],
            'score': 0.75,
            'confidence': 0.8
        }
        return result
    
    def _analyze_industry_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析行业维度"""
        # 基于实际资源数据分析行业趋势
        resources = data.get('resources', [])
        
        # 行业分布统计
        industry_distribution = {}
        for resource in resources:
            industry_path = resource.get('industry_path', '')
            if industry_path:
                # 简化处理：取第一个行业分类
                industry = industry_path.split('>')[0].strip() if '>' in industry_path else industry_path
                industry_distribution[industry] = industry_distribution.get(industry, 0) + 1
        
        # 识别热门行业
        hot_industries = []
        if industry_distribution:
            sorted_industries = sorted(industry_distribution.items(), key=lambda x: x[1], reverse=True)
            hot_industries = [ind for ind, count in sorted_industries[:3]]
        
        result = {
            'indicators': {
                'industry_concentration': 'medium',
                'innovation_activity': 'high',
                'entry_barriers': 'varies'
            },
            'trends': [
                {'trend': 'digital_transformation_acceleration', 'strength': 0.85, 'impact': 'high'},
                {'trend': 'sustainability_focus', 'strength': 0.75, 'impact': 'medium'},
                {'trend': 'supply_chain_resilience', 'strength': 0.7, 'impact': 'high'}
            ],
            'insights': [
                f'热门行业: {", ".join(hot_industries) if hot_industries else "数据不足"}',
                '数字化转型持续深入，各行业积极拥抱新技术',
                '可持续发展成为行业竞争新维度'
            ],
            'score': 0.8,
            'confidence': 0.85
        }
        return result
    
    def _analyze_competitive_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析竞争维度"""
        result = {
            'indicators': {
                'market_concentration': 'medium',
                'competitive_intensity': 'high',
                'differentiation_level': 'medium'
            },
            'trends': [
                {'trend': 'platform_economy_expansion', 'strength': 0.8, 'impact': 'high'},
                {'trend': 'ecosystem_competition', 'strength': 0.75, 'impact': 'high'},
                {'trend': 'niche_market_proliferation', 'strength': 0.65, 'impact': 'medium'}
            ],
            'insights': [
                '平台经济模式持续扩张，生态竞争成为主流',
                '细分市场机会增多，专业化竞争加剧',
                '跨界竞争日益普遍，行业边界模糊化'
            ],
            'score': 0.7,
            'confidence': 0.75
        }
        return result
    
    def _analyze_consumer_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析消费者维度"""
        result = {
            'indicators': {
                'consumer_confidence': 'stable',
                'spending_power': 'growing',
                'preference_volatility': 'increasing'
            },
            'trends': [
                {'trend': 'experience_economy_growth', 'strength': 0.8, 'impact': 'high'},
                {'trend': 'personalization_demand', 'strength': 0.85, 'impact': 'high'},
                {'trend': 'conscious_consumption', 'strength': 0.7, 'impact': 'medium'}
            ],
            'insights': [
                '消费者更加注重体验和价值，而非单纯的产品功能',
                '个性化需求强烈，定制化服务成为竞争优势',
                '可持续和道德消费意识增强，影响购买决策'
            ],
            'score': 0.8,
            'confidence': 0.8
        }
        return result
    
    def _analyze_technological_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析技术维度"""
        result = {
            'indicators': {
                'innovation_rate': 'high',
                'adoption_speed': 'accelerating',
                'disruption_potential': 'high'
            },
            'trends': [
                {'trend': 'generative_ai_proliferation', 'strength': 0.9, 'impact': 'very_high'},
                {'trend': 'edge_computing_adoption', 'strength': 0.75, 'impact': 'high'},
                {'trend': 'quantum_computing_progress', 'strength': 0.6, 'impact': 'medium'}
            ],
            'insights': [
                '生成式AI技术快速普及，正在重构多个行业',
                '边缘计算与物联网结合，推动实时决策能力',
                '量子计算虽处早期，但战略意义重大'
            ],
            'score': 0.85,
            'confidence': 0.9
        }
        return result
    
    def _analyze_regulatory_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析政策法规维度"""
        result = {
            'indicators': {
                'regulatory_complexity': 'high',
                'compliance_requirements': 'increasing',
                'policy_stability': 'medium'
            },
            'trends': [
                {'trend': 'data_privacy_regulations', 'strength': 0.85, 'impact': 'high'},
                {'trend': 'esg_reporting_requirements', 'strength': 0.8, 'impact': 'high'},
                {'trend': 'digital_taxation_frameworks', 'strength': 0.7, 'impact': 'medium'}
            ],
            'insights': [
                '数据隐私法规全球趋严，合规成本显著增加',
                'ESG报告要求成为企业运营必备项',
                '数字经济税收框架逐步完善，影响跨国运营'
            ],
            'score': 0.7,
            'confidence': 0.8
        }
        return result
    
    def _analyze_supply_chain_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析供应链维度"""
        result = {
            'indicators': {
                'supply_chain_resilience': 'improving',
                'logistics_costs': 'elevated',
                'inventory_levels': 'optimizing'
            },
            'trends': [
                {'trend': 'nearshoring_acceleration', 'strength': 0.75, 'impact': 'high'},
                {'trend': 'digital_supply_chain_adoption', 'strength': 0.8, 'impact': 'high'},
                {'trend': 'circular_economy_integration', 'strength': 0.65, 'impact': 'medium'}
            ],
            'insights': [
                '供应链近岸化趋势明显，区域供应链网络重构',
                '数字化供应链工具提升透明度和响应速度',
                '循环经济理念逐步融入供应链设计'
            ],
            'score': 0.75,
            'confidence': 0.8
        }
        return result
    
    def _analyze_financial_dimension(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析财务维度"""
        result = {
            'indicators': {
                'profitability_pressure': 'medium',
                'capital_accessibility': 'adequate',
                'valuation_levels': 'reasonable'
            },
            'trends': [
                {'trend': 'esg_investing_growth', 'strength': 0.8, 'impact': 'high'},
                {'trend': 'fintech_disruption', 'strength': 0.85, 'impact': 'high'},
                {'trend': 'crypto_asset_integration', 'strength': 0.6, 'impact': 'medium'}
            ],
            'insights': [
                'ESG因素成为投资决策关键考量',
                '金融科技持续颠覆传统金融服务模式',
                '数字资产与传统金融体系加速融合'
            ],
            'score': 0.75,
            'confidence': 0.8
        }
        return result
    
    def _identify_key_trends(self, dimension_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别关键趋势"""
        key_trends = []
        
        # 从各维度分析中提取趋势
        for dim_name, analysis in dimension_analysis.items():
            trends = analysis.get('trends', [])
            for trend in trends:
                # 筛选强度较高、影响较大的趋势
                if trend.get('strength', 0) >= 0.7 and trend.get('impact') in ['high', 'very_high']:
                    key_trend = {
                        'trend_id': f"trend_{int(time.time())}_{len(key_trends)}",
                        'name': trend['trend'],
                        'dimension': dim_name,
                        'strength': trend['strength'],
                        'impact': trend['impact'],
                        'description': self._get_trend_description(trend['trend']),
                        'implications': self._get_trend_implications(trend['trend']),
                        'identified_at': datetime.now().isoformat()
                    }
                    key_trends.append(key_trend)
        
        # 按强度排序
        key_trends.sort(key=lambda x: x['strength'], reverse=True)
        
        # 限制数量
        return key_trends[:10]
    
    def _get_trend_description(self, trend_name: str) -> str:
        """获取趋势描述"""
        descriptions = {
            'digital_transformation_acceleration': '企业数字化转型进程显著加快，数字技术渗透到各行业核心业务流程',
            'generative_ai_proliferation': '生成式AI技术快速普及，从内容创作扩展到产品设计、代码生成等多个领域',
            'experience_economy_growth': '消费者从购买产品转向购买体验，体验价值成为竞争关键',
            'nearshoring_acceleration': '供应链布局向消费市场靠近，减少对远距离供应链的依赖',
            'esg_investing_growth': '环境、社会和治理因素成为投资决策的重要考量',
            'platform_economy_expansion': '平台商业模式持续扩张，连接多方参与者创造网络效应',
            'data_privacy_regulations': '全球数据隐私保护法规日益严格，影响企业数据收集和使用',
            'sustainability_focus': '可持续发展理念深入企业战略，绿色转型成为行业趋势',
            'supply_chain_resilience': '企业加强供应链韧性建设，应对不确定性风险',
            'conscious_consumption': '消费者更加关注产品背后的道德、环境和社会影响'
        }
        return descriptions.get(trend_name, '趋势描述暂缺')
    
    def _get_trend_implications(self, trend_name: str) -> List[str]:
        """获取趋势影响"""
        implications_map = {
            'digital_transformation_acceleration': [
                '传统企业必须加快数字化改造以避免被淘汰',
                '数字化人才需求激增，人才竞争加剧',
                '数据安全和隐私保护成为数字化进程的关键挑战'
            ],
            'generative_ai_proliferation': [
                '内容创作、设计、编程等领域的工作方式将被重塑',
                '企业需要建立AI治理框架，确保负责任地使用AI',
                'AI技能成为职场重要竞争力'
            ],
            'experience_economy_growth': [
                '企业需要从产品思维转向体验思维',
                '个性化、沉浸式体验成为差异化竞争点',
                '体验设计和用户旅程优化能力变得至关重要'
            ]
        }
        return implications_map.get(trend_name, ['影响分析待补充'])
    
    def _assess_market_opportunities(self, 
                                   data: Dict[str, Any], 
                                   dimension_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估市场机会"""
        opportunities = []
        
        # 基于数据分析识别机会
        resources = data.get('resources', [])
        
        # 机会识别逻辑
        # 1. 高增长行业
        # 2. 供需失衡领域
        # 3. 技术变革带来的新需求
        # 4. 政策支持方向
        
        # 示例机会（实际应根据数据分析动态生成）
        sample_opportunities = [
            {
                'name': '生成式AI企业应用服务',
                'description': '为企业提供定制化的生成式AI解决方案，提升运营效率和创新能力',
                'target_industries': ['制造业', '服务业', '科技'],
                'target_regions': ['north_america', 'europe', 'asia'],
                'growth_potential': 0.85,
                'competitive_intensity': 0.7,
                'entry_barriers': 0.6,
                'estimated_market_size': '500亿美元',
                'time_horizon': '1-3年'
            },
            {
                'name': '可持续供应链解决方案',
                'description': '帮助企业实现供应链绿色转型，满足ESG要求和消费者期待',
                'target_industries': ['制造业', '零售_ecommerce', '物流运输'],
                'target_regions': ['global'],
                'growth_potential': 0.8,
                'competitive_intensity': 0.6,
                'entry_barriers': 0.7,
                'estimated_market_size': '300亿美元',
                'time_horizon': '2-5年'
            },
            {
                'name': '跨境数字营销服务',
                'description': '为出海企业提供本土化数字营销服务，提升海外市场竞争力',
                'target_industries': ['零售_ecommerce', '科技', '服务业'],
                'target_regions': ['southeast_asia', 'middle_east', 'latin_america'],
                'growth_potential': 0.75,
                'competitive_intensity': 0.65,
                'entry_barriers': 0.55,
                'estimated_market_size': '200亿美元',
                'time_horizon': '1-2年'
            }
        ]
        
        for i, opp_data in enumerate(sample_opportunities):
            opportunity = {
                'opportunity_id': f"opp_{int(time.time())}_{i}",
                'name': opp_data['name'],
                'description': opp_data['description'],
                'target_industries': opp_data['target_industries'],
                'target_regions': opp_data['target_regions'],
                'assessment': {
                    'growth_potential': opp_data['growth_potential'],
                    'competitive_intensity': opp_data['competitive_intensity'],
                    'entry_barriers': opp_data['entry_barriers'],
                    'overall_score': self._calculate_opportunity_score(opp_data),
                    'risk_level': self._assess_opportunity_risk(opp_data),
                    'recommendation': self._generate_opportunity_recommendation(opp_data)
                },
                'estimated_market_size': opp_data['estimated_market_size'],
                'time_horizon': opp_data['time_horizon'],
                'identified_at': datetime.now().isoformat(),
                'supporting_insights': self._get_supporting_insights(opp_data, dimension_analysis)
            }
            opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_opportunity_score(self, opportunity_data: Dict[str, Any]) -> float:
        """计算机会综合得分"""
        growth = opportunity_data.get('growth_potential', 0.5)
        competition = 1.0 - opportunity_data.get('competitive_intensity', 0.5)  # 竞争越激烈，得分越低
        barriers = 1.0 - opportunity_data.get('entry_barriers', 0.5)  # 进入壁垒越高，得分越低
        
        # 加权计算：增长潜力权重最高
        return (growth * 0.5 + competition * 0.3 + barriers * 0.2)
    
    def _assess_opportunity_risk(self, opportunity_data: Dict[str, Any]) -> str:
        """评估机会风险等级"""
        score = self._calculate_opportunity_score(opportunity_data)
        
        if score >= 0.8:
            return OpportunityRiskLevel.VERY_LOW.value
        elif score >= 0.7:
            return OpportunityRiskLevel.LOW.value
        elif score >= 0.6:
            return OpportunityRiskLevel.MEDIUM.value
        elif score >= 0.5:
            return OpportunityRiskLevel.HIGH.value
        else:
            return OpportunityRiskLevel.VERY_HIGH.value
    
    def _generate_opportunity_recommendation(self, opportunity_data: Dict[str, Any]) -> str:
        """生成机会建议"""
        score = self._calculate_opportunity_score(opportunity_data)
        risk = self._assess_opportunity_risk(opportunity_data)
        
        if risk in [OpportunityRiskLevel.VERY_LOW.value, OpportunityRiskLevel.LOW.value]:
            return "积极投入，建立先发优势"
        elif risk == OpportunityRiskLevel.MEDIUM.value:
            return "谨慎试点，验证商业模式"
        else:
            return "深入研究，等待更好时机"
    
    def _get_supporting_insights(self, 
                               opportunity_data: Dict[str, Any], 
                               dimension_analysis: Dict[str, Any]) -> List[str]:
        """获取支持性洞察"""
        insights = []
        
        # 基于机会属性和维度分析生成支持性洞察
        target_industries = opportunity_data.get('target_industries', [])
        target_regions = opportunity_data.get('target_regions', [])
        
        # 示例洞察
        if '生成式AI' in opportunity_data['name']:
            tech_analysis = dimension_analysis.get('technological', {})
            if tech_analysis.get('score', 0) > 0.7:
                insights.append('生成式AI技术成熟度较高，市场接受度快速提升')
        
        if '可持续' in opportunity_data['name']:
            regulatory_analysis = dimension_analysis.get('regulatory', {})
            if regulatory_analysis.get('score', 0) > 0.6:
                insights.append('ESG法规要求趋严，推动可持续供应链需求增长')
        
        return insights
    
    def _generate_risk_alerts(self, dimension_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成风险预警"""
        alerts = []
        
        # 基于维度分析识别风险
        for dim_name, analysis in dimension_analysis.items():
            score = analysis.get('score', 0)
            if score < 0.6:  # 得分较低表明风险较高
                alert = {
                    'alert_id': f"alert_{int(time.time())}_{len(alerts)}",
                    'risk_type': dim_name,
                    'risk_level': 'high' if score < 0.5 else 'medium',
                    'description': f'{dim_name}维度分析显示潜在风险，得分: {score:.2f}',
                    'trigger_factors': self._identify_risk_factors(dim_name, analysis),
                    'recommended_actions': self._generate_risk_mitigation_actions(dim_name),
                    'generated_at': datetime.now().isoformat()
                }
                alerts.append(alert)
        
        return alerts
    
    def _identify_risk_factors(self, dimension: str, analysis: Dict[str, Any]) -> List[str]:
        """识别风险因素"""
        factors_map = {
            'economic': ['增长放缓', '通胀压力', '汇率波动'],
            'regulatory': ['政策不确定性', '合规成本上升', '监管趋严'],
            'supply_chain': ['供应链中断', '物流成本上升', '库存压力']
        }
        return factors_map.get(dimension, ['风险因素分析待补充'])
    
    def _generate_risk_mitigation_actions(self, dimension: str) -> List[str]:
        """生成风险缓解措施"""
        actions_map = {
            'economic': ['多元化市场布局', '成本控制优化', '现金流管理加强'],
            'regulatory': ['合规团队建设', '政策监测机制', '法律顾问咨询'],
            'supply_chain': ['供应商多元化', '库存策略优化', '物流网络冗余']
        }
        return actions_map.get(dimension, ['风险缓释措施待制定'])
    
    def _calculate_market_health_score(self, dimension_analysis: Dict[str, Any]) -> float:
        """计算市场健康综合得分"""
        total_score = 0
        dimension_count = 0
        
        for dim_name, analysis in dimension_analysis.items():
            score = analysis.get('score', 0)
            confidence = analysis.get('confidence', 0)
            
            # 加权计算，考虑置信度
            weighted_score = score * confidence
            total_score += weighted_score
            dimension_count += 1
        
        if dimension_count == 0:
            return 0.5  # 默认中等
        
        return total_score / dimension_count
    
    def _generate_recommendations(self, 
                                key_trends: List[Dict[str, Any]], 
                                opportunities: List[Dict[str, Any]], 
                                risk_alerts: List[Dict[str, Any]]) -> List[str]:
        """生成总体建议"""
        recommendations = []
        
        # 基于趋势、机会和风险生成建议
        if key_trends:
            strong_trends = [t for t in key_trends if t.get('strength', 0) >= 0.8]
            if strong_trends:
                trend_names = ", ".join([t['name'] for t in strong_trends[:3]])
                recommendations.append(f"把握强劲趋势: {trend_names}")
        
        if opportunities:
            high_score_opps = [o for o in opportunities if o['assessment']['overall_score'] >= 0.8]
            if high_score_opps:
                opp_names = ", ".join([o['name'] for o in high_score_opps[:3]])
                recommendations.append(f"重点关注高价值机会: {opp_names}")
        
        if risk_alerts:
            high_risk_alerts = [a for a in risk_alerts if a['risk_level'] == 'high']
            if high_risk_alerts:
                risk_types = ", ".join([a['risk_type'] for a in high_risk_alerts[:3]])
                recommendations.append(f"加强风险管理，特别是: {risk_types}")
        
        # 默认建议
        if not recommendations:
            recommendations = [
                "保持市场敏感度，持续监测关键指标变化",
                "建立灵活的组织架构，快速响应市场变化",
                "加强创新投入，把握技术变革机遇"
            ]
        
        return recommendations
    
    def sync_cognition_baseline(self, baseline_data: Dict[str, Any]) -> bool:
        """
        同步认知基线
        
        Args:
            baseline_data: 认知基线数据
            
        Returns:
            同步是否成功
        """
        try:
            self.cognition_baseline = baseline_data
            logger.info(f"认知基线同步成功，版本: {baseline_data.get('version')}")
            return True
        except Exception as e:
            logger.error(f"同步认知基线失败: {e}")
            return False
    
    def submit_market_insight(self, insight_data: Dict[str, Any]) -> str:
        """
        提交市场洞察
        
        Args:
            insight_data: 市场洞察数据
            
        Returns:
            洞察ID
        """
        insight_id = f"insight_{int(time.time())}_{self.node_id}_{len(self.market_insights)}"
        insight_data['insight_id'] = insight_id
        insight_data['submitted_at'] = datetime.now().isoformat()
        
        self.market_insights[insight_id] = insight_data
        
        # 如果启用网络协同，可广播给其他节点
        if self.enable_network and self.network_client:
            # 这里可以添加网络广播逻辑
            pass
        
        logger.info(f"市场洞察提交成功，ID: {insight_id}")
        return insight_id
    
    def initiate_collaborative_assessment(self, opportunity_data: Dict[str, Any]) -> str:
        """
        发起协同评估
        
        Args:
            opportunity_data: 商业机会数据
            
        Returns:
            评估ID
        """
        assessment_id = f"collab_assess_{int(time.time())}_{self.node_id}_{len(self.collaborative_assessments)}"
        
        assessment = {
            'assessment_id': assessment_id,
            'opportunity': opportunity_data,
            'initiated_by': self.node_id,
            'initiated_at': datetime.now().isoformat(),
            'participants': [self.node_id],  # 初始参与者
            'status': 'initiated',
            'results': [],
            'created_at': datetime.now().isoformat()
        }
        
        self.collaborative_assessments[assessment_id] = assessment
        
        # 如果启用网络协同，可邀请其他节点参与
        if self.enable_network and self.network_client:
            # 这里可以添加邀请其他节点的逻辑
            pass
        
        logger.info(f"协同评估发起成功，ID: {assessment_id}")
        return assessment_id
    
    def export_analysis_report(self, report_data: Dict[str, Any], format: str = 'json') -> str:
        """
        导出分析报告
        
        Args:
            report_data: 分析报告数据
            format: 导出格式（json, markdown, html）
            
        Returns:
            导出内容
        """
        if format == 'json':
            return json.dumps(report_data, ensure_ascii=False, indent=2)
        elif format == 'markdown':
            return self._convert_to_markdown(report_data)
        elif format == 'html':
            return self._convert_to_html(report_data)
        else:
            logger.warning(f"不支持的导出格式: {format}，默认使用JSON")
            return json.dumps(report_data, ensure_ascii=False, indent=2)
    
    def _convert_to_markdown(self, report_data: Dict[str, Any]) -> str:
        """将报告转换为Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# 全球市场分析报告")
        lines.append(f"报告ID: {report_data.get('report_id', '未知')}")
        lines.append(f"生成时间: {report_data.get('generated_at', '未知')}")
        lines.append(f"生成节点: {report_data.get('generated_by', '未知')}")
        lines.append("")
        
        # 执行摘要
        exec_summary = report_data.get('executive_summary', {})
        lines.append("## 执行摘要")
        lines.append(f"- **市场健康度**: {exec_summary.get('overall_market_health', 0):.2f}/1.0")
        lines.append(f"- **关键趋势**: {exec_summary.get('key_trends_count', 0)} 个")
        lines.append(f"- **市场机会**: {exec_summary.get('opportunities_count', 0)} 个")
        lines.append(f"- **风险预警**: {exec_summary.get('risk_alerts_count', 0)} 个")
        lines.append("")
        
        lines.append("### 主要建议")
        for rec in exec_summary.get('recommendations', []):
            lines.append(f"- {rec}")
        lines.append("")
        
        # 关键趋势
        key_trends = report_data.get('key_trends', [])
        if key_trends:
            lines.append("## 关键趋势")
            for trend in key_trends[:5]:  # 显示前5个
                lines.append(f"### {trend.get('name', '未知趋势')}")
                lines.append(f"- **强度**: {trend.get('strength', 0):.2f}")
                lines.append(f"- **影响**: {trend.get('impact', '未知')}")
                lines.append(f"- **描述**: {trend.get('description', '')}")
                lines.append("")
        
        # 市场机会
        opportunities = report_data.get('market_opportunities', [])
        if opportunities:
            lines.append("## 市场机会评估")
            for opp in opportunities[:5]:  # 显示前5个
                lines.append(f"### {opp.get('name', '未知机会')}")
                lines.append(f"- **综合得分**: {opp['assessment'].get('overall_score', 0):.2f}")
                lines.append(f"- **风险等级**: {opp['assessment'].get('risk_level', '未知')}")
                lines.append(f"- **建议**: {opp['assessment'].get('recommendation', '')}")
                lines.append(f"- **市场规模**: {opp.get('estimated_market_size', '未知')}")
                lines.append(f"- **时间窗口**: {opp.get('time_horizon', '未知')}")
                lines.append("")
        
        # 风险预警
        risk_alerts = report_data.get('risk_alerts', [])
        if risk_alerts:
            lines.append("## 风险预警")
            for alert in risk_alerts[:5]:  # 显示前5个
                lines.append(f"### {alert.get('risk_type', '未知风险')}")
                lines.append(f"- **风险等级**: {alert.get('risk_level', '未知')}")
                lines.append(f"- **触发因素**: {', '.join(alert.get('trigger_factors', []))}")
                lines.append(f"- **建议措施**: {', '.join(alert.get('recommended_actions', []))}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _convert_to_html(self, report_data: Dict[str, Any]) -> str:
        """将报告转换为HTML格式"""
        # 简化的HTML转换
        markdown_content = self._convert_to_markdown(report_data)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全球市场分析报告 - {report_data.get('report_id', '未知')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .executive-summary {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 20px; margin: 20px 0; }}
        .opportunity-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; background: white; }}
        .risk-alert {{ border: 1px solid #e74c3c; border-radius: 8px; padding: 15px; margin: 15px 0; background: #ffeaea; }}
        .score-badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-weight: bold; margin-right: 10px; }}
        .score-high {{ background: #2ecc71; color: white; }}
        .score-medium {{ background: #f39c12; color: white; }}
        .score-low {{ background: #e74c3c; color: white; }}
        .metadata {{ font-size: 14px; color: #7f8c8d; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="metadata">
            报告ID: {report_data.get('report_id', '未知')} | 
            生成时间: {report_data.get('generated_at', '未知')} | 
            生成节点: {report_data.get('generated_by', '未知')}
        </div>
        
        <div class="executive-summary">
            <h2>执行摘要</h2>
            <p><strong>市场健康度:</strong> {report_data.get('executive_summary', {}).get('overall_market_health', 0):.2f}/1.0</p>
            <p><strong>主要建议:</strong></p>
            <ul>
"""
        
        for rec in report_data.get('executive_summary', {}).get('recommendations', []):
            html += f"<li>{rec}</li>\n"
        
        html += """            </ul>
        </div>
        
        <div id="content">
            <!-- 内容将通过JavaScript动态渲染 -->
        </div>
    </div>
    
    <script>
        // 简化的Markdown转HTML渲染
        const markdownContent = `""" + markdown_content.replace('`', '\\`').replace('\\', '\\\\') + """`;
        
        function renderMarkdown(md) {
            // 简单的Markdown转换
            let html = md
                .replace(/^# (.+)$/gm, '<h1>$1</h1>')
                .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                .replace(/^### (.+)$/gm, '<h3>$1</h3>')
                .replace(/^- (.+)$/gm, '<li>$1</li>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            
            // 包裹列表项
            html = html.replace(/<li>(.+?)<br>/g, '<ul><li>$1</li></ul>');
            
            return html;
        }
        
        document.getElementById('content').innerHTML = renderMarkdown(markdownContent);
    </script>
</body>
</html>"""
        
        return html


def main():
    """主函数，用于测试"""
    print("全域商业大脑测试程序")
    print("=" * 50)
    
    # 配置
    config = {
        'node_id': 'test_node',
        'enable_network': False,
        'analysis_period': 30
    }
    
    # 初始化商业大脑
    brain = GlobalBusinessBrain(config)
    
    # 生成市场分析报告
    print("正在生成全球市场分析报告...")
    report = brain.generate_global_market_analysis(
        regions=["north_america", "europe", "asia"],
        industries=["manufacturing", "retail_ecommerce", "technology"]
    )
    
    # 输出报告摘要
    print(f"报告ID: {report['report_id']}")
    print(f"生成时间: {report['generated_at']}")
    print(f"市场健康度: {report['executive_summary']['overall_market_health']:.2f}/1.0")
    print(f"识别趋势: {len(report['key_trends'])} 个")
    print(f"评估机会: {len(report['market_opportunities'])} 个")
    print(f"风险预警: {len(report['risk_alerts'])} 个")
    
    # 导出报告
    json_report = brain.export_analysis_report(report, 'json')
    markdown_report = brain.export_analysis_report(report, 'markdown')
    
    print(f"\nJSON报告长度: {len(json_report)} 字符")
    print(f"Markdown报告长度: {len(markdown_report)} 字符")
    
    # 保存报告
    import os
    os.makedirs('outputs/商业大脑', exist_ok=True)
    
    with open(f"outputs/商业大脑/{report['report_id']}.json", 'w', encoding='utf-8') as f:
        f.write(json_report)
    
    with open(f"outputs/商业大脑/{report['report_id']}.md", 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"\n报告已保存至 outputs/商业大脑/ 目录")
    print("测试完成！")


if __name__ == "__main__":
    main()