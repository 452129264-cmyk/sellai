"""
人脸一致性锁定算法配置
"""

import os
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class FaceConsistencyConfig:
    """人脸一致性算法配置"""
    
    # 模型路径配置
    model_dir: str = os.path.join(os.path.dirname(__file__), "models")
    
    # 人脸检测配置
    face_detector_model: str = "retinaface"  # 可选: retinaface, mtcnn, yolov5_face
    detection_confidence: float = 0.95
    min_face_size: int = 40
    
    # 人脸识别配置
    recognition_model: str = "arcface"  # 可选: arcface, facenet, vggface2
    embedding_dim: int = 512
    recognition_threshold: float = 0.3  # 相似度阈值，低于此值认为是不同人
    
    # 一致性锁定配置
    max_face_variance: float = 0.03  # 最大脸部特征差异 < 3%
    reference_face_count: int = 5  # 参考人脸数量
    update_frequency: int = 10  # 每10张更新一次参考特征
    
    # 质量检查配置
    quality_check_enabled: bool = True
    min_face_quality_score: float = 0.8  # 人脸质量评分阈值
    pose_variance_limit: float = 15.0  # 最大姿态变化角度
    
    # 性能配置
    batch_size: int = 8
    device: str = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
    
    # 文件路径配置
    face_id_database: str = os.path.join(model_dir, "face_id_database.db")
    texture_params_path: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data/banana_texture_params/material_params.json"
    )


@dataclass
class TextureParamsConfig:
    """面料纹理参数库配置"""
    
    # 材质类型
    material_types: List[str] = None
    
    # 物理参数
    albedo_range: Tuple[float, float] = (0.1, 0.9)  # 反射率范围
    roughness_range: Tuple[float, float] = (0.1, 0.9)  # 粗糙度范围
    specular_range: Tuple[float, float] = (0.1, 0.8)  # 高光强度范围
    
    # 纹理细节
    normal_map_intensity: float = 1.0  # 法线贴图强度
    displacement_scale: float = 0.05  # 位移贴图缩放
    tessellation_factor: int = 64  # 细分因子
    
    # 物理基础渲染(PBR)参数
    metallic_range: Tuple[float, float] = (0.0, 1.0)  # 金属度范围
    ior_range: Tuple[float, float] = (1.3, 2.5)  # 折射率范围
    subsurface_scattering: bool = True  # 次表面散射
    
    def __post_init__(self):
        if self.material_types is None:
            self.material_types = [
                "denim",  # 牛仔
                "silk",  # 丝绸
                "cotton",  # 棉
                "linen",  # 亚麻
                "wool",  # 羊毛
                "leather",  # 皮革
                "synthetic",  # 合成纤维
                "knit",  # 针织
                "lace",  # 蕾丝
                "velvet",  # 天鹅绒
            ]


# 默认配置实例
face_config = FaceConsistencyConfig()
texture_config = TextureParamsConfig()