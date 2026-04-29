"""
短视频引流军团 - 多平台分发管道
支持TikTok、YouTube、Instagram、小红书四平台的视频自动上传、外链挂载、元数据设置
集成到现有无限分身体系，与Memory V2认证记忆系统同步
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

# 导入现有系统模块
try:
    from src.shared_state_manager import SharedStateManager
    from src.memory_v2_indexer import MemoryV2Indexer
    SHARED_STATE_AVAILABLE = True
except ImportError:
    SHARED_STATE_AVAILABLE = False
    print("警告: 共享状态模块不可用，使用模拟模式")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlatformDistributor:
    """多平台分发器基类"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.api_client = None
        self.upload_config = {}
        self.initialized = False
        
    def initialize(self, api_key: Optional[str] = None, 
                   api_secret: Optional[str] = None,
                   access_token: Optional[str] = None) -> bool:
        """
        初始化平台API客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥
            access_token: 访问令牌
        
        Returns:
            初始化是否成功
        """
        try:
            # 在实际部署中，这里会初始化真实的API客户端
            # 示例：self.api_client = TikTokAPI(api_key, api_secret, access_token)
            
            self.upload_config = {
                "max_file_size": "100MB",
                "supported_formats": [".mp4", ".mov"],
                "max_duration": 60,  # 秒
                "max_resolution": "4K"
            }
            
            # 模拟API密钥验证
            if api_key:
                self.api_client = f"{self.platform_name}_simulated_client"
                self.initialized = True
                logger.info(f"{self.platform_name} API客户端初始化成功")
            else:
                logger.warning(f"{self.platform_name} 缺少API密钥，使用模拟模式")
                self.initialized = True  # 模拟模式下也标记为已初始化
            
            return True
            
        except Exception as e:
            logger.error(f"{self.platform_name} API客户端初始化失败: {e}")
            self.initialized = False
            return False
    
    def upload_video(self, video_path: str, 
                     metadata: Dict[str, Any],
                     callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        上传视频到平台
        
        Args:
            video_path: 视频文件路径
            metadata: 元数据（标题、描述、标签等）
            callback_url: 回调URL（用于上传状态通知）
        
        Returns:
            上传结果字典
        """
        if not self.initialized:
            return {
                "success": False,
                "error": f"{self.platform_name} 分发器未初始化",
                "platform": self.platform_name
            }
        
        # 验证视频文件
        if not os.path.exists(video_path):
            return {
                "success": False,
                "error": f"视频文件不存在: {video_path}",
                "platform": self.platform_name
            }
        
        try:
            logger.info(f"开始上传视频到 {self.platform_name}: {video_path}")
            
            # 模拟上传过程
            file_size = os.path.getsize(video_path)
            video_hash = self._calculate_file_hash(video_path)
            
            # 模拟上传时间（基于文件大小）
            upload_time = max(3, min(30, file_size / (1024 * 1024)))  # 3-30秒
            
            # 在实际部署中，这里会调用平台API
            # 示例：response = self.api_client.upload_video(video_path, metadata)
            
            # 生成模拟响应
            video_id = f"{self.platform_name}_{int(time.time())}_{hashlib.md5(video_path.encode()).hexdigest()[:8]}"
            
            result = {
                "success": True,
                "platform": self.platform_name,
                "video_id": video_id,
                "video_url": f"https://{self.platform_name}.com/video/{video_id}",
                "upload_time": upload_time,
                "file_size": file_size,
                "file_hash": video_hash,
                "metadata_applied": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加外链挂载结果
            if metadata.get("external_link"):
                result["external_link_added"] = True
                result["external_link"] = metadata["external_link"]
            
            logger.info(f"视频上传成功到 {self.platform_name}: {video_id}")
            return result
            
        except Exception as e:
            logger.error(f"视频上传到 {self.platform_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "platform": self.platform_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并优化平台元数据
        
        Args:
            metadata: 原始元数据
        
        Returns:
            验证后的元数据
        """
        validated = metadata.copy()
        
        # 平台特定规则
        platform_rules = {
            "tiktok": {
                "max_title_length": 150,
                "max_description_length": 2200,
                "max_hashtags": 10
            },
            "youtube_shorts": {
                "max_title_length": 100,
                "max_description_length": 5000,
                "max_tags": 15
            },
            "instagram_reels": {
                "max_caption_length": 2200,
                "max_hashtags": 30
            },
            "xiaohongshu": {
                "max_title_length": 20,
                "max_content_length": 1000,
                "max_tags": 10
            }
        }
        
        rules = platform_rules.get(self.platform_name, {})
        
        # 标题长度限制
        if "title" in validated and "max_title_length" in rules:
            validated["title"] = validated["title"][:rules["max_title_length"]]
        
        # 描述长度限制
        if "description" in validated and "max_description_length" in rules:
            validated["description"] = validated["description"][:rules["max_description_length"]]
        
        # 标签数量限制
        if "hashtags" in validated and "max_hashtags" in rules:
            validated["hashtags"] = validated["hashtags"][:rules["max_hashtags"]]
        
        return validated
    
    def generate_platform_metadata(self, 
                                   video_template: Dict[str, Any],
                                   product_info: Dict[str, Any],
                                   external_link: str) -> Dict[str, Any]:
        """
        生成平台特定元数据
        
        Args:
            video_template: 视频模板信息
            product_info: 产品信息
            external_link: 外部链接（Shopify店铺URL）
        
        Returns:
            平台优化元数据
        """
        base_metadata = {
            "title": f"{product_info.get('product_name', 'Vintage Denim Jacket')} | {video_template.get('scene_name', 'Fashion Showcase')}",
            "description": self._generate_description(video_template, product_info, external_link),
            "hashtags": self._generate_hashtags(video_template, product_info),
            "external_link": external_link,
            "visibility": "public",
            "allow_comments": True,
            "allow_duet": True,
            "allow_stitch": True,
            "publish_date": "now",
            "category": "fashion",
            "language": "en"
        }
        
        return self.validate_metadata(base_metadata)
    
    def _generate_description(self, 
                              video_template: Dict[str, Any],
                              product_info: Dict[str, Any],
                              external_link: str) -> str:
        """生成平台描述"""
        features = "\n".join([f"• {feature}" for feature in product_info.get("key_features", [])])
        
        description = f"""{video_template.get('description', 'Fashion showcase')}

{features}

Shop now: {external_link}

#{product_info.get('product_name', 'denimjacket').replace(' ', '')} #fashion #streetwear #ootd
"""
        
        return description.strip()
    
    def _generate_hashtags(self, 
                           video_template: Dict[str, Any],
                           product_info: Dict[str, Any]) -> List[str]:
        """生成平台标签"""
        base_tags = [
            "denimjacket",
            "vintagefashion",
            "streetwear",
            "fashion",
            "style",
            "ootd",
            "mensfashion" if product_info.get("target_gender") == "male" else "womensfashion",
            "denim",
            "jacket",
            "fashionhaul"
        ]
        
        # 添加场景特定标签
        scene_tags = {
            "indoor_studio": ["studio", "photography", "professional"],
            "street_urban": ["streetstyle", "urban", "city"],
            "lifestyle_casual": ["lifestyle", "casual", "dailywear"],
            "active_dynamic": ["activewear", "movement", "dynamic"],
            "artistic_conceptual": ["art", "conceptual", "creative"]
        }
        
        scene_key = video_template.get("scene_key", "")
        if scene_key in scene_tags:
            base_tags.extend(scene_tags[scene_key])
        
        # 平台特定标签
        platform_tags = {
            "tiktok": ["fyp", "foryou", "foryoupage", "tiktokfashion"],
            "youtube_shorts": ["shorts", "youtubeshorts", "shortsvideo"],
            "instagram_reels": ["reels", "reelsvideo", "instagramreels"],
            "xiaohongshu": ["小红书", "穿搭", "种草"]
        }
        
        if self.platform_name in platform_tags:
            base_tags.extend(platform_tags[self.platform_name])
        
        # 去重并限制数量
        return list(dict.fromkeys(base_tags))[:20]

class TikTokDistributor(PlatformDistributor):
    """TikTok分发器"""
    
    def __init__(self):
        super().__init__("tiktok")
        self.platform_specific_config = {
            "trending_sounds": True,
            "duet_enabled": True,
            "stitch_enabled": True,
            "commercial_content": False,
            "age_restriction": False
        }
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """TikTok特定元数据验证"""
        validated = super().validate_metadata(metadata)
        
        # TikTok特定规则
        if "description" in validated:
            # 添加话题标签格式
            if "hashtags" in validated:
                hashtag_text = " ".join([f"#{tag}" for tag in validated["hashtags"]])
                validated["description"] = f"{validated['description']}\n\n{hashtag_text}"
                # 移除单独的hashtags字段，因为已合并到描述中
                validated.pop("hashtags", None)
        
        return validated

class YouTubeShortsDistributor(PlatformDistributor):
    """YouTube Shorts分发器"""
    
    def __init__(self):
        super().__init__("youtube_shorts")
        self.platform_specific_config = {
            "shorts_shelf": True,
            "end_screen": True,
            "cards_enabled": False,
            "monetization": True
        }
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """YouTube Shorts特定元数据验证"""
        validated = super().validate_metadata(metadata)
        
        # YouTube SEO优化
        if "title" in validated:
            # 添加相关关键词
            keywords = ["denim jacket", "vintage fashion", "try on haul", "fashion review"]
            if not any(keyword.lower() in validated["title"].lower() for keyword in keywords):
                validated["title"] = f"{validated['title']} | Denim Jacket Review"
        
        return validated

class InstagramReelsDistributor(PlatformDistributor):
    """Instagram Reels分发器"""
    
    def __init__(self):
        super().__init__("instagram_reels")
        self.platform_specific_config = {
            "shopping_tags": True,
            "branded_content": True,
            "collaborators": False,
            "location_tag": True
        }
    
    def generate_platform_metadata(self, 
                                   video_template: Dict[str, Any],
                                   product_info: Dict[str, Any],
                                   external_link: str) -> Dict[str, Any]:
        """Instagram Reels特定元数据生成"""
        base_metadata = super().generate_platform_metadata(video_template, product_info, external_link)
        
        # Instagram特定字段
        base_metadata.update({
            "location": {
                "name": "New York, NY",
                "id": "nyc_location_id"
            },
            "user_tags": [],  # 可标记相关用户
            "product_tags": [
                {
                    "product_name": product_info.get("product_name", "Vintage Denim Jacket"),
                    "product_price": product_info.get("price", "$89.99"),
                    "product_url": external_link
                }
            ],
            "music": {
                "audio_name": "Trending Urban Beat",
                "artist": "Unknown Artist"
            }
        })
        
        return base_metadata

class XiaohongshuDistributor(PlatformDistributor):
    """小红书分发器"""
    
    def __init__(self):
        super().__init__("xiaohongshu")
        self.platform_specific_config = {
            "chinese_required": True,
            "detailed_review": True,
            "price_transparency": True,
            "authenticity_verification": True
        }
    
    def generate_platform_metadata(self, 
                                   video_template: Dict[str, Any],
                                   product_info: Dict[str, Any],
                                   external_link: str) -> Dict[str, Any]:
        """小红书特定元数据生成"""
        # 生成中文描述
        chinese_features = "\n".join([
            "• 750g重磅复古牛仔夹克",
            "• 经典卡车司机版型",
            "• 做旧水洗工艺",
            "• 加固缝线，耐用性强",
            "• 内衬棉质面料，穿着舒适"
        ])
        
        base_metadata = {
            "title": f"这款复古牛仔夹克太值得入手了！{product_info.get('product_name', '')}",
            "content": f"""今天给大家分享一款超有质感的复古牛仔夹克！

{chinese_features}

上身效果真的绝了，不管是搭配T恤还是卫衣都特别好看。材质厚实但不硬，秋冬季节穿正合适。

店铺链接：{external_link}

#牛仔夹克 #复古穿搭 #秋冬穿搭 #美式复古 #购物分享
""",
            "external_link": external_link,
            "tags": ["牛仔夹克", "复古穿搭", "秋冬穿搭", "美式复古", "购物分享"],
            "price": product_info.get("price", "¥699"),
            "rating": 5.0,
            "authenticity": "正品保证",
            "language": "zh"
        }
        
        return self.validate_metadata(base_metadata)

class MultiPlatformDistributor:
    """多平台分发管理器"""
    
    def __init__(self):
        self.distributors = {
            "tiktok": TikTokDistributor(),
            "youtube_shorts": YouTubeShortsDistributor(),
            "instagram_reels": InstagramReelsDistributor(),
            "xiaohongshu": XiaohongshuDistributor()
        }
        
        # 初始化共享状态和记忆系统
        if SHARED_STATE_AVAILABLE:
            self.shared_state = SharedStateManager()
            self.memory_indexer = MemoryV2Indexer()
        else:
            self.shared_state = None
            self.memory_indexer = None
        
        self.upload_history = []
        self.active_campaigns = {}
    
    def initialize_all(self, platform_credentials: Dict[str, Dict[str, str]]) -> Dict[str, bool]:
        """
        初始化所有平台分发器
        
        Args:
            platform_credentials: 平台凭据字典
        
        Returns:
            各平台初始化状态
        """
        results = {}
        
        for platform, credentials in platform_credentials.items():
            if platform in self.distributors:
                distributor = self.distributors[platform]
                success = distributor.initialize(**credentials)
                results[platform] = success
            else:
                results[platform] = False
                logger.warning(f"未知平台: {platform}")
        
        return results
    
    def distribute_video(self, 
                        video_path: str,
                        video_template: Dict[str, Any],
                        product_info: Dict[str, Any],
                        external_link: str,
                        target_platforms: Optional[List[str]] = None,
                        campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """
        分发视频到多个平台
        
        Args:
            video_path: 视频文件路径
            video_template: 视频模板信息
            product_info: 产品信息
            external_link: 外部链接
            target_platforms: 目标平台列表，None表示所有平台
            campaign_id: 营销战役ID
        
        Returns:
            分发结果汇总
        """
        if target_platforms is None:
            target_platforms = list(self.distributors.keys())
        
        campaign_id = campaign_id or f"campaign_{int(time.time())}"
        
        # 记录分发开始
        distribution_record = {
            "campaign_id": campaign_id,
            "video_path": video_path,
            "template": video_template.get("scene_key", "unknown"),
            "product": product_info.get("product_name", "unknown"),
            "target_platforms": target_platforms,
            "start_time": datetime.now().isoformat(),
            "results": {},
            "success_count": 0,
            "failure_count": 0
        }
        
        logger.info(f"开始分发视频战役 {campaign_id} 到 {len(target_platforms)} 个平台")
        
        # 分发到各平台
        for platform in target_platforms:
            if platform not in self.distributors:
                logger.error(f"不支持的平台: {platform}")
                distribution_record["results"][platform] = {
                    "success": False,
                    "error": f"不支持的平台"
                }
                distribution_record["failure_count"] += 1
                continue
            
            distributor = self.distributors[platform]
            
            # 生成平台特定元数据
            metadata = distributor.generate_platform_metadata(
                video_template, product_info, external_link
            )
            
            # 上传视频
            result = distributor.upload_video(video_path, metadata)
            distribution_record["results"][platform] = result
            
            if result.get("success"):
                distribution_record["success_count"] += 1
                
                # 记录到共享状态
                self._record_distribution(campaign_id, platform, result)
            else:
                distribution_record["failure_count"] += 1
        
        # 完成记录
        distribution_record["end_time"] = datetime.now().isoformat()
        distribution_record["total_count"] = len(target_platforms)
        
        self.upload_history.append(distribution_record)
        
        # 保存分发记录到记忆系统
        if self.memory_indexer:
            self._save_to_memory_v2(distribution_record)
        
        logger.info(f"视频分发战役 {campaign_id} 完成: "
                   f"{distribution_record['success_count']} 成功, "
                   f"{distribution_record['failure_count']} 失败")
        
        return distribution_record
    
    def _record_distribution(self, 
                            campaign_id: str,
                            platform: str,
                            result: Dict[str, Any]):
        """记录分发结果到共享状态"""
        if not self.shared_state:
            return
        
        record = {
            "campaign_id": campaign_id,
            "platform": platform,
            "video_id": result.get("video_id"),
            "video_url": result.get("video_url"),
            "upload_time": result.get("upload_time"),
            "file_size": result.get("file_size"),
            "metadata": result.get("metadata_applied", {}),
            "timestamp": result.get("timestamp", datetime.now().isoformat())
        }
        
        try:
            self.shared_state.add_record("video_distribution_log", record)
        except Exception as e:
            logger.error(f"记录分发结果到共享状态失败: {e}")
    
    def _save_to_memory_v2(self, distribution_record: Dict[str, Any]):
        """保存分发记录到Memory V2认证记忆系统"""
        if not self.memory_indexer:
            return
        
        memory_data = {
            "type": "video_distribution_campaign",
            "campaign_id": distribution_record["campaign_id"],
            "video_template": distribution_record["template"],
            "product": distribution_record["product"],
            "platform_results": distribution_record["results"],
            "summary": {
                "success_count": distribution_record["success_count"],
                "failure_count": distribution_record["failure_count"],
                "total_count": distribution_record["total_count"]
            },
            "timestamps": {
                "start": distribution_record["start_time"],
                "end": distribution_record["end_time"]
            }
        }
        
        try:
            success = self.memory_indexer.index_memory(
                memory_data,
                category="marketing_campaign",
                tags=["video_distribution", "short_video", "cross_platform"]
            )
            
            if success:
                logger.info(f"分发记录已保存到Memory V2: {distribution_record['campaign_id']}")
            else:
                logger.warning(f"分发记录保存到Memory V2失败: {distribution_record['campaign_id']}")
                
        except Exception as e:
            logger.error(f"保存到Memory V2时出错: {e}")
    
    def get_distribution_stats(self) -> Dict[str, Any]:
        """获取分发统计信息"""
        total_campaigns = len(self.upload_history)
        
        if total_campaigns == 0:
            return {
                "total_campaigns": 0,
                "total_videos_distributed": 0,
                "success_rate": 0.0,
                "platform_breakdown": {}
            }
        
        total_videos = sum(record.get("total_count", 0) for record in self.upload_history)
        total_success = sum(record.get("success_count", 0) for record in self.upload_history)
        
        # 平台细分统计
        platform_stats = {}
        for platform in self.distributors.keys():
            platform_success = 0
            platform_total = 0
            
            for record in self.upload_history:
                if platform in record.get("results", {}):
                    platform_total += 1
                    if record["results"][platform].get("success"):
                        platform_success += 1
            
            if platform_total > 0:
                platform_stats[platform] = {
                    "success_rate": platform_success / platform_total,
                    "total_attempts": platform_total,
                    "success_count": platform_success
                }
        
        return {
            "total_campaigns": total_campaigns,
            "total_videos_distributed": total_videos,
            "success_rate": total_success / total_videos if total_videos > 0 else 0.0,
            "success_count": total_success,
            "failure_count": total_videos - total_success,
            "platform_breakdown": platform_stats,
            "last_campaign": self.upload_history[-1]["campaign_id"] if self.upload_history else None
        }
    
    def export_distribution_report(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """导出分发战役报告"""
        for record in self.upload_history:
            if record["campaign_id"] == campaign_id:
                return record
        
        return None

# 实用函数
def create_distributor() -> MultiPlatformDistributor:
    """创建多平台分发器实例"""
    return MultiPlatformDistributor()

def load_platform_credentials(config_file: str = "config/platform_credentials.json") -> Dict[str, Dict[str, str]]:
    """
    从配置文件加载平台凭据
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        平台凭据字典
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载平台凭据失败: {e}")
    
    # 返回示例配置
    return {
        "tiktok": {
            "api_key": "your_tiktok_api_key",
            "api_secret": "your_tiktok_api_secret",
            "access_token": "your_tiktok_access_token"
        },
        "youtube_shorts": {
            "api_key": "your_youtube_api_key",
            "access_token": "your_youtube_access_token"
        },
        "instagram_reels": {
            "api_key": "your_instagram_api_key",
            "access_token": "your_instagram_access_token"
        },
        "xiaohongshu": {
            "api_key": "your_xiaohongshu_api_key",
            "access_token": "your_xiaohongshu_access_token"
        }
    }

# 示例使用
if __name__ == "__main__":
    print("短视频引流军团 - 多平台分发管道")
    print("=" * 50)
    
    # 创建分发器
    distributor = create_distributor()
    
    # 加载平台凭据（实际使用中需要真实凭据）
    credentials = load_platform_credentials()
    
    # 初始化所有平台
    init_results = distributor.initialize_all(credentials)
    print(f"平台初始化结果: {init_results}")
    
    # 示例视频分发
    video_template = {
        "scene_key": "street_urban",
        "scene_name": "街头实拍潮流版",
        "description": "城市街头环境展示日常穿搭"
    }
    
    product_info = {
        "product_name": "750g American Vintage Denim Jacket",
        "key_features": [
            "Heavyweight 750g premium denim",
            "Authentic vintage wash and distressing",
            "Reinforced stitching and durable construction"
        ],
        "price": "$89.99",
        "target_gender": "unisex"
    }
    
    external_link = "https://shopify-store.com/products/750g-vintage-denim-jacket"
    
    # 注意：这里使用模拟视频路径，实际使用需要真实视频文件
    video_path = "temp/generated_videos/street_urban_1.mp4"
    
    print(f"\n示例分发配置:")
    print(f"视频模板: {video_template['scene_name']}")
    print(f"产品: {product_info['product_name']}")
    print(f"外部链接: {external_link}")
    
    # 在实际部署中，取消注释以下代码
    # distribution_result = distributor.distribute_video(
    #     video_path=video_path,
    #     video_template=video_template,
    #     product_info=product_info,
    #     external_link=external_link,
    #     target_platforms=["tiktok", "instagram_reels"]  # 选择部分平台
    # )
    
    # 显示模拟结果
    print("\n模拟分发完成")
    print("实际使用时，需:")
    print("1. 配置各平台API凭据")
    print("2. 提供真实的视频文件路径")
    print("3. 调用distribute_video方法")