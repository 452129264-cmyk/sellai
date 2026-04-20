"""
面料纹理参数管理器
用于管理牛仔/丝绸/棉麻等常见材质的光影反射参数库
确保服装面料纹理/光影超高精细，反射误差<5%
"""

import os
import json
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from .config import texture_config

logger = logging.getLogger(__name__)


class MaterialType(Enum):
    """材质类型枚举"""
    DENIM = "denim"
    SILK = "silk"
    COTTON = "cotton"
    LINEN = "linen"
    WOOL = "wool"
    LEATHER = "leather"
    SYNTHETIC = "synthetic"
    KNIT = "knit"
    LACE = "lace"
    VELVET = "velvet"


@dataclass
class PBRParameters:
    """物理基础渲染参数"""
    albedo: Tuple[float, float, float]  # 基础颜色
    roughness: float  # 粗糙度
    metallic: float  # 金属度
    specular: float  # 高光强度
    ior: float  # 折射率
    subsurface: Dict[str, Any]  # 次表面散射参数


@dataclass
class TextureProperties:
    """纹理属性"""
    weave_pattern: str
    thread_density: float
    yarn_thickness: float
    surface_variance: float
    normal_map_intensity: float
    displacement_scale: float
    reflectance_profile: Dict[str, float]
    special_characteristics: Dict[str, Any]  # 材质特定特性


@dataclass
class MaterialDefinition:
    """材质定义"""
    material_id: str
    name: str
    type: MaterialType
    description: str
    category: str
    subtypes: List[str]
    pbr_params: PBRParameters
    texture_props: TextureProperties
    optical_properties: Dict[str, Any]
    generation_guidelines: Dict[str, Any]
    validation_data: Dict[str, Any]
    
    def __post_init__(self):
        if not self.material_id:
            self.material_id = hashlib.md5(f"{self.type.value}_{self.name}".encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "material_id": self.material_id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "category": self.category,
            "subtypes": self.subtypes,
            "pbr_params": asdict(self.pbr_params),
            "texture_props": asdict(self.texture_props),
            "optical_properties": self.optical_properties,
            "generation_guidelines": self.generation_guidelines,
            "validation_data": self.validation_data
        }


class TextureParamsManager:
    """面料纹理参数管理器"""
    
    def __init__(self, config: TextureParamsConfig = None):
        self.config = config or texture_config
        self.params_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data/banana_texture_params/material_params.json"
        )
        self.materials: Dict[str, MaterialDefinition] = {}
        self._load_material_params()
        logger.info(f"面料纹理参数管理器初始化完成，加载材质: {len(self.materials)} 种")
    
    def _load_material_params(self):
        """加载材质参数"""
        try:
            with open(self.params_file, 'r', encoding='utf-8') as f:
                params_data = json.load(f)
            
            # 解析材质数据
            materials_data = params_data.get("materials", {})
            
            for material_key, material_data in materials_data.items():
                try:
                    material_def = self._parse_material_data(material_key, material_data)
                    self.materials[material_key] = material_def
                    logger.debug(f"加载材质: {material_def.name} ({material_key})")
                except Exception as e:
                    logger.error(f"解析材质 {material_key} 失败: {str(e)}")
            
            logger.info(f"成功加载 {len(self.materials)} 种材质参数")
            
        except FileNotFoundError:
            logger.warning(f"材质参数文件不存在: {self.params_file}")
            # 创建默认材质
            self._create_default_materials()
        except json.JSONDecodeError as e:
            logger.error(f"材质参数文件JSON格式错误: {str(e)}")
            self._create_default_materials()
        except Exception as e:
            logger.error(f"加载材质参数失败: {str(e)}")
            self._create_default_materials()
    
    def _parse_material_data(self, material_key: str, 
                            material_data: Dict[str, Any]) -> MaterialDefinition:
        """解析材质数据"""
        # PBR参数
        pbr_data = material_data.get("pbr_parameters", {})
        pbr_params = PBRParameters(
            albedo=tuple(pbr_data.get("albedo", [0.5, 0.5, 0.5])),
            roughness=pbr_data.get("roughness", 0.5),
            metallic=pbr_data.get("metallic", 0.0),
            specular=pbr_data.get("specular", 0.5),
            ior=pbr_data.get("ior", 1.5),
            subsurface=pbr_data.get("subsurface", {})
        )
        
        # 纹理属性
        texture_data = material_data.get("texture_properties", {})
        texture_props = TextureProperties(
            weave_pattern=texture_data.get("weave_pattern", "plain_weave"),
            thread_density=texture_data.get("thread_density", 20.0),
            yarn_thickness=texture_data.get("yarn_thickness", 0.2),
            surface_variance=texture_data.get("surface_variance", 0.15),
            normal_map_intensity=texture_data.get("normal_map_intensity", 0.5),
            displacement_scale=texture_data.get("displacement_scale", 0.01),
            reflectance_profile=texture_data.get("reflectance_profile", {}),
            special_characteristics=texture_data.get("special_characteristics", {})
        )
        
        # 确定材质类型
        material_type = MaterialType.DENIM
        try:
            material_type = MaterialType(material_key)
        except ValueError:
            # 尝试从名称推断
            material_name = material_data.get("name", "").lower()
            for mt in MaterialType:
                if mt.value in material_name or mt.value == material_key:
                    material_type = mt
                    break
        
        return MaterialDefinition(
            material_id=f"{material_key}_{hashlib.md5(material_key.encode()).hexdigest()[:8]}",
            name=material_data.get("name", material_key),
            type=material_type,
            description=material_data.get("description", ""),
            category=material_data.get("category", "unknown"),
            subtypes=material_data.get("subtypes", []),
            pbr_params=pbr_params,
            texture_props=texture_props,
            optical_properties=material_data.get("optical_properties", {}),
            generation_guidelines=material_data.get("generation_guidelines", {}),
            validation_data={
                "reflection_error_limit": material_data.get("optical_properties", {}).get("reflection_error_limit", 0.05),
                "test_cases": 20
            }
        )
    
    def _create_default_materials(self):
        """创建默认材质库"""
        logger.info("创建默认材质库")
        
        # 牛仔布
        denim = MaterialDefinition(
            material_id="denim_001",
            name="牛仔布",
            type=MaterialType.DENIM,
            description="传统棉质牛仔布，具有独特纹理和靛蓝染色效果",
            category="woven_fabric",
            subtypes=["raw_denim", "stretch_denim", "selvedge_denim"],
            pbr_params=PBRParameters(
                albedo=(0.08, 0.12, 0.25),
                roughness=0.7,
                metallic=0.05,
                specular=0.35,
                ior=1.45,
                subsurface={"enabled": False}
            ),
            texture_props=TextureProperties(
                weave_pattern="twill",
                thread_density=14.5,
                yarn_thickness=0.35,
                surface_variance=0.25,
                normal_map_intensity=0.8,
                displacement_scale=0.03,
                reflectance_profile={
                    "diffuse_reflectance": 0.85,
                    "specular_reflectance": 0.15,
                    "fresnel_at_0_deg": 0.05,
                    "fresnel_at_90_deg": 0.25
                },
                special_characteristics={
                    "wear_patterns": {
                        "fading_intensity": 0.4,
                        "whiskering_depth": 0.15
                    }
                }
            ),
            optical_properties={
                "absorption_coefficient": [0.9, 0.95, 0.98],
                "scattering_coefficient": [0.1, 0.15, 0.2],
                "anisotropy": 0.3,
                "reflection_error_limit": 0.045
            },
            generation_guidelines={
                "required_details": ["stitching", "selvedge_id", "twill_lines"],
                "avoid_artifacts": ["uniform_blue", "plastic_look"]
            },
            validation_data={
                "reflection_error_limit": 0.045,
                "test_cases": 20
            }
        )
        
        # 丝绸
        silk = MaterialDefinition(
            material_id="silk_001",
            name="丝绸",
            type=MaterialType.SILK,
            description="天然蛋白质纤维，具有光泽、柔软和独特的光学特性",
            category="protein_fiber",
            subtypes=["charmeuse", "chiffon", "crepe_de_chine"],
            pbr_params=PBRParameters(
                albedo=(0.9, 0.88, 0.82),
                roughness=0.15,
                metallic=0.0,
                specular=0.85,
                ior=1.54,
                subsurface={"enabled": True}
            ),
            texture_props=TextureProperties(
                weave_pattern="plain_weave",
                thread_density=40.0,
                yarn_thickness=0.02,
                surface_variance=0.08,
                normal_map_intensity=0.3,
                displacement_scale=0.005,
                reflectance_profile={
                    "diffuse_reflectance": 0.4,
                    "specular_reflectance": 0.6,
                    "fresnel_at_0_deg": 0.1,
                    "fresnel_at_90_deg": 0.9
                },
                special_characteristics={
                    "sheen_characteristics": {
                        "sheen_intensity": 0.85,
                        "sheen_roughness": 0.25
                    }
                }
            ),
            optical_properties={
                "absorption_coefficient": [0.1, 0.15, 0.2],
                "scattering_coefficient": [0.8, 0.82, 0.85],
                "anisotropy": 0.8,
                "reflection_error_limit": 0.035
            },
            generation_guidelines={
                "required_details": ["subtle_sheen", "soft_draping", "light_transmission"],
                "avoid_artifacts": ["plastic_shine", "uniform_reflection"]
            },
            validation_data={
                "reflection_error_limit": 0.035,
                "test_cases": 20
            }
        )
        
        # 棉布
        cotton = MaterialDefinition(
            material_id="cotton_001",
            name="棉布",
            type=MaterialType.COTTON,
            description="天然植物纤维，透气、吸湿、柔软",
            category="cellulose_fiber",
            subtypes=["canvas", "corduroy", "flannel", "jersey"],
            pbr_params=PBRParameters(
                albedo=(0.92, 0.91, 0.89),
                roughness=0.4,
                metallic=0.0,
                specular=0.25,
                ior=1.52,
                subsurface={"enabled": True}
            ),
            texture_props=TextureProperties(
                weave_pattern="plain_weave",
                thread_density=20.0,
                yarn_thickness=0.25,
                surface_variance=0.15,
                normal_map_intensity=0.5,
                displacement_scale=0.01,
                reflectance_profile={
                    "diffuse_reflectance": 0.95,
                    "specular_reflectance": 0.05,
                    "fresnel_at_0_deg": 0.02,
                    "fresnel_at_90_deg": 0.15
                },
                special_characteristics={
                    "nap_characteristics": {
                        "has_nap": True,
                        "nap_length": 0.02
                    }
                }
            ),
            optical_properties={
                "absorption_coefficient": [0.05, 0.07, 0.1],
                "scattering_coefficient": [0.9, 0.92, 0.95],
                "anisotropy": 0.4,
                "reflection_error_limit": 0.04
            },
            generation_guidelines={
                "required_details": ["fiber_texture", "weave_pattern", "natural_irregularities"],
                "avoid_artifacts": ["flat_surface", "synthetic_look"]
            },
            validation_data={
                "reflection_error_limit": 0.04,
                "test_cases": 20
            }
        )
        
        self.materials = {
            "denim": denim,
            "silk": silk,
            "cotton": cotton
        }
    
    def get_material(self, material_key: str) -> Optional[MaterialDefinition]:
        """获取指定材质"""
        return self.materials.get(material_key)
    
    def get_all_materials(self) -> Dict[str, MaterialDefinition]:
        """获取所有材质"""
        return self.materials.copy()
    
    def validate_reflection_error(self, generated_image: np.ndarray,
                                 reference_image: np.ndarray,
                                 material_type: MaterialType) -> Dict[str, Any]:
        """
        验证反射误差是否在5%以内
        
        Args:
            generated_image: 生成的图像
            reference_image: 参考图像
            material_type: 材质类型
            
        Returns:
            验证结果
        """
        try:
            # 确保图像尺寸一致
            if generated_image.shape != reference_image.shape:
                generated_resized = cv2.resize(generated_image, 
                                              (reference_image.shape[1], reference_image.shape[0]))
            else:
                generated_resized = generated_image
            
            # 转换为灰度图像
            gray_gen = cv2.cvtColor(generated_resized, cv2.COLOR_RGB2GRAY)
            gray_ref = cv2.cvtColor(reference_image, cv2.COLOR_RGB2GRAY)
            
            # 计算反射差异（使用均方误差）
            mse = np.mean((gray_gen - gray_ref) ** 2)
            max_pixel = 255.0
            error_percentage = (mse / (max_pixel ** 2)) * 100
            
            # 获取材质的误差限制
            material = self.get_material(material_type.value)
            error_limit = 5.0  # 默认5%
            if material and "reflection_error_limit" in material.optical_properties:
                error_limit = material.optical_properties["reflection_error_limit"] * 100
            
            # 检查是否通过
            passed = error_percentage <= error_limit
            
            result = {
                "passed": passed,
                "error_percentage": float(error_percentage),
                "error_limit": float(error_limit),
                "mse": float(mse),
                "material_type": material_type.value,
                "message": f"反射误差: {error_percentage:.2f}% {'≤' if passed else '>'} {error_limit:.2f}%"
            }
            
            logger.info(f"材质 {material_type.value} 反射误差验证: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"反射误差验证失败: {str(e)}")
            return {
                "passed": False,
                "error_percentage": 100.0,
                "error_limit": 5.0,
                "error": str(e),
                "message": f"验证失败: {str(e)}"
            }
    
    def generate_material_prompt(self, material_type: MaterialType,
                                context: str = "") -> str:
        """
        生成材质特定的提示词
        
        Args:
            material_type: 材质类型
            context: 上下文信息（如服装类型、场景等）
            
        Returns:
            优化的提示词
        """
        material = self.get_material(material_type.value)
        if not material:
            return f"{context}, realistic fabric texture"
        
        # 获取生成指南
        guidelines = material.generation_guidelines
        
        # 构建提示词
        prompt_parts = []
        
        if context:
            prompt_parts.append(context)
        
        # 添加材质描述
        prompt_parts.append(f"{material.name} fabric")
        
        # 添加所需细节
        if "required_details" in guidelines:
            details = guidelines["required_details"]
            if details:
                detail_str = ", ".join(details[:3])
                prompt_parts.append(f"showing {detail_str}")
        
        # 添加纹理特性
        texture_props = material.texture_props
        if texture_props.weave_pattern and texture_props.weave_pattern != "varies_by_subtype":
            prompt_parts.append(f"with {texture_props.weave_pattern} weave pattern")
        
        # 添加光学特性
        if material.optical_properties.get("anisotropy", 0) > 0.6:
            prompt_parts.append("with subtle anisotropic highlights")
        
        # 添加推荐提示词
        if "recommended_prompts" in guidelines and guidelines["recommended_prompts"]:
            recommended = guidelines["recommended_prompts"][0]
            if recommended and len(prompt_parts) < 3:
                # 如果提示词较短，使用推荐提示词
                return recommended
        
        full_prompt = ", ".join(prompt_parts)
        
        # 确保提示词质量
        quality_suffix = ", professional photography, detailed texture, high resolution"
        return full_prompt + quality_suffix
    
    def save_material_params(self):
        """保存材质参数到文件"""
        try:
            os.makedirs(os.path.dirname(self.params_file), exist_ok=True)
            
            output_data = {
                "metadata": {
                    "description": "面料纹理参数库 - 用于Banana生图内核强制质量锁死",
                    "version": "1.0.0",
                    "created_at": "2026-04-04T22:45:00Z",
                    "updated_at": datetime.now().isoformat(),
                    "total_materials": len(self.materials)
                },
                "materials": {}
            }
            
            for key, material in self.materials.items():
                output_data["materials"][key] = material.to_dict()
            
            with open(self.params_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"材质参数已保存到: {self.params_file}")
            
        except Exception as e:
            logger.error(f"保存材质参数失败: {str(e)}")
    
    def add_custom_material(self, material_def: MaterialDefinition):
        """添加自定义材质"""
        key = material_def.type.value
        self.materials[key] = material_def
        logger.info(f"添加自定义材质: {material_def.name} ({key})")
        
        # 自动保存更新
        self.save_material_params()