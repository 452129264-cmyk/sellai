"""
DeepSeek API 客户端
用于预测性记忆推理、商机分析等
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeepSeekMessage:
    """消息结构"""
    role: str  # system, user, assistant
    content: str


class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, config):
        """
        初始化客户端
        
        Args:
            config: DeepSeekConfig 实例
        """
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.timeout = config.timeout
        
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式返回
            
        Returns:
            API响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("DeepSeek API 请求超时")
            raise TimeoutError("DeepSeek API 请求超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API 请求失败: {e}")
            raise
    
    def chat_simple(self, user_message: str, system_prompt: str = "") -> str:
        """
        简单聊天接口
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            
        Returns:
            助手回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        response = self.chat(messages)
        return response["choices"][0]["message"]["content"]
    
    def analyze_json(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        结构化分析（返回JSON）
        
        Args:
            text: 待分析文本
            schema: 期望的JSON结构
            
        Returns:
            解析后的JSON对象
        """
        system_prompt = f"""你是一个数据分析助手。请分析用户输入并返回JSON格式的结果。
期望的JSON结构:
{json.dumps(schema, ensure_ascii=False, indent=2)}

只返回JSON，不要有其他内容。"""
        
        response = self.chat_simple(text, system_prompt)
        
        # 尝试解析JSON
        try:
            # 去除可能的markdown代码块标记
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError:
            logger.warning(f"JSON解析失败: {response[:100]}...")
            return {"error": "JSON解析失败", "raw": response}
    
    # ============================================================
    # 预测性记忆专用接口
    # ============================================================
    
    def extract_patterns(self, experience_text: str) -> Dict[str, Any]:
        """
        从经验中提取模式
        
        Args:
            experience_text: 经验描述文本
            
        Returns:
            提取的模式
        """
        schema = {
            "causal_patterns": [
                {"cause": "原因", "effect": "结果", "confidence": "置信度0-1"}
            ],
            "decision_patterns": [
                {"context": "场景", "decision": "决策", "outcome": "结果", "success": "是否成功"}
            ],
            "emotional_signals": {
                "sentiment": "情感倾向",
                "intensity": "强度0-1"
            }
        }
        return self.analyze_json(experience_text, schema)
    
    def predict_outcome(
        self,
        context: Dict[str, Any],
        possible_actions: List[str]
    ) -> Dict[str, Any]:
        """
        预测行动结果
        
        Args:
            context: 当前上下文
            possible_actions: 可能的行动列表
            
        Returns:
            预测结果
        """
        prompt = f"""基于以下上下文，预测每个行动的可能结果:

上下文:
{json.dumps(context, ensure_ascii=False, indent=2)}

可能的行动:
{json.dumps(possible_actions, ensure_ascii=False, indent=2)}

请返回JSON格式:
{{
    "predictions": [
        {{
            "action": "行动",
            "success_probability": "成功概率0-1",
            "expected_outcome": "预期结果",
            "risks": ["风险列表"],
            "recommendation_score": "推荐分数0-10"
        }}
    ],
    "best_action": "最佳行动",
    "reasoning": "推理过程"
}}"""
        
        response = self.chat_simple(prompt)
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            return json.loads(response.strip())
        except:
            return {"error": "预测解析失败", "raw": response}
    
    def generate_insight(self, memory_data: List[Dict]) -> str:
        """
        从记忆数据生成洞察
        
        Args:
            memory_data: 记忆数据列表
            
        Returns:
            洞察文本
        """
        prompt = f"""基于以下记忆数据，生成有价值的商业洞察:

记忆数据:
{json.dumps(memory_data[:10], ensure_ascii=False, indent=2)}

请生成:
1. 关键趋势发现
2. 潜在机会
3. 风险提示
4. 行动建议"""
        
        return self.chat_simple(prompt)


# ============================================================
# 便捷函数
# ============================================================

def get_deepseek_client() -> DeepSeekClient:
    """获取DeepSeek客户端实例"""
    from .config import api_config
    return DeepSeekClient(api_config.deepseek)
