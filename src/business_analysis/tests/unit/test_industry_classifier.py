"""
行业分类器单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from datetime import datetime

from business_analysis.engine.industry_classifier import IndustryClassifier
from business_analysis.models.data_models import IndustryLevel, GrowthTrend, RiskLevel, CompetitionLevel


class TestIndustryClassifier:
    """行业分类器测试类"""
    
    @pytest.fixture
    def classifier(self):
        """创建行业分类器实例"""
        return IndustryClassifier()
    
    def test_initialization(self, classifier):
        """测试初始化"""
        assert classifier is not None
        assert len(classifier.categories) > 0
        assert len(classifier.profiles) > 0
    
    def test_get_category(self, classifier):
        """测试获取行业分类"""
        # 测试存在的一级行业
        category = classifier.get_category("information_technology")
        assert category is not None
        assert category.id == "information_technology"
        assert category.level == IndustryLevel.PRIMARY
        
        # 测试不存在的行业
        category = classifier.get_category("nonexistent_industry")
        assert category is None
    
    def test_get_profile(self, classifier):
        """测试获取行业画像"""
        # 测试存在的一级行业画像
        profile = classifier.get_profile("information_technology")
        assert profile is not None
        assert profile.industry_id == "information_technology"
        assert isinstance(profile.avg_gross_margin, float)
        assert isinstance(profile.growth_rate, float)
        
        # 测试不存在的行业画像
        profile = classifier.get_profile("nonexistent_industry")
        assert profile is None
    
    def test_search_categories(self, classifier):
        """测试搜索行业分类"""
        # 搜索特定关键词
        results = classifier.search_categories("software")
        assert isinstance(results, list)
        
        # 搜索不存在的关键词
        results = classifier.search_categories("nonexistentkeyword")
        assert len(results) == 0
    
    def test_get_primary_categories(self, classifier):
        """测试获取一级行业"""
        primary_categories = classifier.get_primary_categories()
        assert isinstance(primary_categories, list)
        assert len(primary_categories) >= 20  # 至少20个一级行业
        
        # 验证所有都是一级行业
        for category in primary_categories:
            assert category.level == IndustryLevel.PRIMARY
    
    def test_get_secondary_categories(self, classifier):
        """测试获取二级行业"""
        secondary_categories = classifier.get_secondary_categories()
        assert isinstance(secondary_categories, list)
        assert len(secondary_categories) >= 100  # 至少100个二级行业
        
        # 验证所有都是二级行业
        for category in secondary_categories:
            assert category.level == IndustryLevel.SECONDARY
    
    def test_get_children(self, classifier):
        """测试获取子行业"""
        # 获取一级行业的子行业
        children = classifier.get_children("information_technology")
        assert isinstance(children, list)
        
        # 验证子行业级别
        for child in children:
            assert child.level == IndustryLevel.SECONDARY
            assert child.parent_id == "information_technology"
    
    def test_get_category_tree(self, classifier):
        """测试获取行业分类树"""
        tree = classifier.get_category_tree()
        assert isinstance(tree, dict)
        
        # 验证树结构
        for industry_id, data in tree.items():
            assert "category" in data
            assert "children" in data
            assert isinstance(data["children"], list)
    
    def test_update_profile(self, classifier):
        """测试更新行业画像"""
        industry_id = "information_technology"
        
        # 获取原始画像
        original_profile = classifier.get_profile(industry_id)
        assert original_profile is not None
        
        # 更新数据
        update_data = {
            "avg_gross_margin": 70.0,
            "growth_rate": 20.0
        }
        
        success = classifier.update_profile(industry_id, **update_data)
        assert success
        
        # 验证更新
        updated_profile = classifier.get_profile(industry_id)
        assert updated_profile is not None
        assert updated_profile.avg_gross_margin == 70.0
        assert updated_profile.growth_rate == 20.0
        
        # 验证更新时间
        assert updated_profile.last_updated > original_profile.last_updated
    
    def test_update_profile_invalid_industry(self, classifier):
        """测试更新不存在的行业画像"""
        success = classifier.update_profile(
            "nonexistent_industry",
            avg_gross_margin=70.0
        )
        assert not success
    
    def test_profile_validation(self, classifier):
        """测试行业画像验证"""
        # 测试百分比验证
        profiles = list(classifier.profiles.values())
        for profile in profiles:
            assert -100 <= profile.avg_gross_margin <= 100
            assert -100 <= profile.avg_net_margin <= 100
            assert -100 <= profile.growth_rate <= 100
            
            # 测试分数验证
            assert 1 <= profile.capital_intensity <= 10
            assert 1 <= profile.technology_threshold <= 10
    
    def test_profile_data_integrity(self, classifier):
        """测试行业画像数据完整性"""
        profiles = list(classifier.profiles.values())
        for profile in profiles:
            # 验证必要字段存在
            assert hasattr(profile, 'industry_id')
            assert hasattr(profile, 'period')
            assert hasattr(profile, 'avg_gross_margin')
            assert hasattr(profile, 'growth_trend')
            assert hasattr(profile, 'last_updated')
            
            # 验证数据类型
            assert isinstance(profile.industry_id, str)
            assert isinstance(profile.period, str)
            assert isinstance(profile.avg_gross_margin, float)
            assert isinstance(profile.growth_trend, GrowthTrend)
            assert isinstance(profile.last_updated, datetime)
    
    def test_export_data(self, classifier, tmp_path):
        """测试导出数据"""
        export_dir = tmp_path / "export"
        
        # 执行导出
        export_files = classifier.export_data(str(export_dir))
        
        # 验证导出文件存在
        assert "categories" in export_files
        assert "profiles" in export_files
        
        # 验证文件内容
        import json
        with open(export_files["categories"], 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
            assert isinstance(categories_data, list)
            assert len(categories_data) == len(classifier.categories)
        
        with open(export_files["profiles"], 'r', encoding='utf-8') as f:
            profiles_data = json.load(f)
            assert isinstance(profiles_data, list)
            assert len(profiles_data) == len(classifier.profiles)
    
    def test_profile_consistency(self, classifier):
        """测试行业画像一致性"""
        # 验证所有行业都有对应的画像
        for industry_id in classifier.categories.keys():
            profile = classifier.get_profile(industry_id)
            assert profile is not None, f"行业 {industry_id} 没有对应的画像"
            
            # 验证画像ID与行业ID一致
            assert profile.industry_id == industry_id