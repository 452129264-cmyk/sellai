#!/usr/bin/env python3
"""
电商集成测试
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from banana_ecommerce_integration import (
    EcommerceIntegrationManager,
    EcommerceProduct,
    ProductStatus,
    ProductImage,
    ProductVariant,
    ShopifyAdapter,
    DianfuAdapter
)


class TestProductModels(unittest.TestCase):
    """测试产品模型"""
    
    def test_product_creation(self):
        """测试产品创建"""
        product = EcommerceProduct(
            product_id="test_001",
            title="测试产品",
            description="测试描述",
            product_type="服装",
            vendor="测试供应商",
            status=ProductStatus.DRAFT
        )
        
        self.assertEqual(product.product_id, "test_001")
        self.assertEqual(product.title, "测试产品")
        self.assertEqual(product.status, ProductStatus.DRAFT)
    
    def test_product_to_dict(self):
        """测试产品字典转换"""
        product = EcommerceProduct(
            product_id="test_002",
            title="测试产品2",
            description="测试描述2"
        )
        
        product_dict = product.to_dict()
        
        self.assertIn("product_id", product_dict)
        self.assertIn("title", product_dict)
        self.assertIn("description", product_dict)
        self.assertEqual(product_dict["status"], "draft")
    
    def test_product_from_dict(self):
        """测试从字典创建产品"""
        product_dict = {
            "product_id": "test_003",
            "title": "测试产品3",
            "description": "测试描述3",
            "status": "active",
            "tags": ["tag1", "tag2"]
        }
        
        product = EcommerceProduct.from_dict(product_dict)
        
        self.assertEqual(product.product_id, "test_003")
        self.assertEqual(product.status, ProductStatus.ACTIVE)
        self.assertEqual(product.tags, ["tag1", "tag2"])
    
    def test_product_image(self):
        """测试产品图片"""
        image = ProductImage(
            image_id="img_001",
            url="https://example.com/image.jpg",
            alt_text="测试图片",
            position=1
        )
        
        self.assertEqual(image.image_id, "img_001")
        self.assertEqual(image.alt_text, "测试图片")
        self.assertEqual(image.position, 1)
    
    def test_product_variant(self):
        """测试产品变体"""
        variant = ProductVariant(
            variant_id="var_001",
            sku="TEST-001",
            price=99.99,
            inventory_quantity=50
        )
        
        self.assertEqual(variant.sku, "TEST-001")
        self.assertEqual(variant.price, 99.99)
        self.assertEqual(variant.inventory_quantity, 50)


class TestShopifyAdapter(unittest.TestCase):
    """测试Shopify适配器"""
    
    def setUp(self):
        """测试准备"""
        self.config = {
            "shop_domain": "test-store.myshopify.com",
            "api_version": "2024-01",
            "access_token": "test_token",
            "product_sync": {
                "default_product_type": "服装",
                "default_vendor": "测试供应商"
            }
        }
        
        self.adapter = ShopifyAdapter(self.config)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.adapter.shop_domain, "test-store.myshopify.com")
        self.assertEqual(self.adapter.api_version, "2024-01")
    
    @patch('requests.Session.request')
    def test_test_connection_success(self, mock_request):
        """测试连接测试成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"shop": {"name": "Test Store"}}
        mock_request.return_value = mock_response
        
        success, error = self.adapter.test_connection()
        
        self.assertTrue(success)
        self.assertIsNone(error)
    
    @patch('requests.Session.request')
    def test_test_connection_failure(self, mock_request):
        """测试连接测试失败"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        
        success, error = self.adapter.test_connection()
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    def test_generate_sku(self):
        """测试SKU生成"""
        sku = self.adapter.generate_sku("Test Product Title")
        
        self.assertTrue(sku.startswith("TESTPROD"))
        self.assertGreater(len(sku), 0)
        
        # 测试带变体的SKU
        variant_options = {"颜色": "蓝色", "尺寸": "M"}
        sku_with_variant = self.adapter.generate_sku("Test Product", variant_options)
        
        self.assertIn("_", sku_with_variant)


class TestIntegrationManager(unittest.TestCase):
    """测试集成管理器"""
    
    def setUp(self):
        """测试准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.yaml")
        
        config = {
            "shop_domain": "test.myshopify.com",
            "access_token": "test_token",
            "banana_integration": {"enabled": False}
        }
        
        import yaml
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('banana_ecommerce_integration.integration_manager.ShopifyAdapter.initialize')
    def test_manager_initialization(self, mock_initialize):
        """测试管理器初始化"""
        mock_initialize.return_value = True
        
        manager = EcommerceIntegrationManager(self.config_path)
        
        self.assertIsNotNone(manager)
        self.assertIsNotNone(manager.active_platform)
        
        stats = manager.get_statistics()
        self.assertIn("platforms_available", stats)
    
    def test_generate_product_id(self):
        """测试产品ID生成"""
        manager = EcommerceIntegrationManager(self.config_path)
        
        product_id = manager._generate_product_id("测试产品标题")
        
        self.assertTrue(product_id.startswith("prod_"))
        self.assertGreater(len(product_id), 10)
        
        # 测试相同标题生成不同ID
        id1 = manager._generate_product_id("相同标题")
        id2 = manager._generate_product_id("相同标题")
        
        self.assertNotEqual(id1, id2)  # 时间戳不同
    
    def test_save_product_to_local(self):
        """测试保存产品到本地"""
        manager = EcommerceIntegrationManager(self.config_path)
        
        product = EcommerceProduct(
            product_id="test_save_001",
            title="保存测试产品",
            description="保存测试描述"
        )
        
        filepath = manager._save_product_to_local(product)
        
        self.assertTrue(os.path.exists(filepath))
        
        # 验证文件内容
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["product_id"], "test_save_001")
        self.assertEqual(saved_data["title"], "保存测试产品")


class TestMockImageGeneration(unittest.TestCase):
    """测试模拟图片生成"""
    
    def setUp(self):
        """测试准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_mock_image_file(self):
        """测试创建模拟图片文件"""
        from banana_ecommerce_integration.integration_manager import EcommerceIntegrationManager
        
        manager = EcommerceIntegrationManager()
        
        image_path = os.path.join(self.temp_dir, "test_image.txt")
        manager._create_mock_image_file(image_path, "测试产品")
        
        self.assertTrue(os.path.exists(image_path))
        
        with open(image_path, 'r') as f:
            content = f.read()
        
        self.assertIn("测试产品", content)


class TestConfigLoader(unittest.TestCase):
    """测试配置加载"""
    
    def setUp(self):
        """测试准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        from banana_ecommerce_integration.utils.config_loader import create_default_config
        
        config = create_default_config()
        
        self.assertIn("shop_domain", config)
        self.assertIn("product_sync", config)
        self.assertIn("banana_integration", config)
        
        # 验证必需字段
        self.assertEqual(config["product_sync"]["default_vendor"], "Banana生图AI")
        self.assertTrue(config["banana_integration"]["enabled"])
    
    def test_merge_configs(self):
        """测试配置合并"""
        from banana_ecommerce_integration.utils.config_loader import merge_configs
        
        base_config = {
            "field1": "value1",
            "nested": {"a": 1, "b": 2}
        }
        
        override_config = {
            "field1": "new_value1",
            "nested": {"b": 3, "c": 4}
        }
        
        merged = merge_configs(base_config, override_config)
        
        self.assertEqual(merged["field1"], "new_value1")
        self.assertEqual(merged["nested"]["a"], 1)  # 保持原值
        self.assertEqual(merged["nested"]["b"], 3)  # 被覆盖
        self.assertEqual(merged["nested"]["c"], 4)  # 新增


class TestProductValidation(unittest.TestCase):
    """测试产品验证"""
    
    def setUp(self):
        """测试准备"""
        self.config = {
            "image_upload": {
                "allowed_formats": ["jpg", "png"]
            }
        }
    
    def test_valid_product(self):
        """测试有效产品"""
        from banana_ecommerce_integration.base import EcommercePlatform
        
        adapter = EcommercePlatform(self.config)
        
        product = EcommerceProduct(
            product_id="test_001",
            title="测试产品",
            description="测试描述"
        )
        
        # 添加模拟图片
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"mock image data")
            image_path = f.name
        
        product.add_image(ProductImage(
            image_id="img_001",
            url="file://" + image_path,
            local_path=image_path
        ))
        
        is_valid, error = adapter.validate_product(product)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # 清理
        os.unlink(image_path)
    
    def test_invalid_product_missing_title(self):
        """测试无效产品：缺少标题"""
        from banana_ecommerce_integration.base import EcommercePlatform
        
        adapter = EcommercePlatform(self.config)
        
        product = EcommerceProduct(
            product_id="test_001",
            title="",
            description="测试描述"
        )
        
        is_valid, error = adapter.validate_product(product)
        
        self.assertFalse(is_valid)
        self.assertIn("标题", error)
    
    def test_invalid_product_no_images(self):
        """测试无效产品：无图片"""
        from banana_ecommerce_integration.base import EcommercePlatform
        
        adapter = EcommercePlatform(self.config)
        
        product = EcommerceProduct(
            product_id="test_001",
            title="测试产品",
            description="测试描述"
        )
        
        is_valid, error = adapter.validate_product(product)
        
        self.assertFalse(is_valid)
        self.assertIn("图片", error)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProductModels)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestShopifyAdapter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegrationManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMockImageGeneration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigLoader))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestProductValidation))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)