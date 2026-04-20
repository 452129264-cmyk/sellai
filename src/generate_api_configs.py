#!/usr/bin/env python3
"""
API配置文档生成脚本
为依赖外部API的服务生成配置文档和一键导入脚本
"""

import os
import json
from datetime import datetime

def generate_api_configs():
    """生成API配置文档"""
    print("=== API配置文档生成 ===")
    print(f"生成时间: {datetime.now()}")
    
    # 创建输出目录
    output_dir = "docs/API配置"
    os.makedirs(output_dir, exist_ok=True)
    
    # API服务列表（基于八大能力和Sora2接入）
    api_services = [
        {
            "name": "Firecrawl全域爬虫",
            "provider": "Firecrawl",
            "description": "7×24小时抓取全球全行业商业风口、赛道红利、供应链底价、各国政策规则、多元赚钱情报",
            "required_api_key": True,
            "endpoint_example": "https://api.firecrawl.dev/v1/scrape",
            "config_template": {
                "api_key": "YOUR_FIRECRAWL_API_KEY",
                "base_url": "https://api.firecrawl.dev",
                "timeout_seconds": 300,
                "retry_count": 3
            },
            "usage_example": {
                "method": "POST",
                "url": "https://api.firecrawl.dev/v1/scrape",
                "headers": {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                "body": {
                    "url": "https://example.com",
                    "format": "markdown",
                    "options": {
                        "onlyMainContent": True
                    }
                }
            },
            "notes": "当前环境网络限制：SSL证书不兼容、代理失效、国际网站防火墙阻止"
        },
        {
            "name": "DeepL全域多语种润色",
            "provider": "DeepL",
            "description": "适配全球各国母语口语、商业俚语、本地化谈判/投放/宣传文案",
            "required_api_key": True,
            "endpoint_example": "https://api.deepl.com/v2/translate",
            "config_template": {
                "api_key": "YOUR_DEEPL_API_KEY",
                "base_url": "https://api.deepl.com",
                "timeout_seconds": 30,
                "retry_count": 2
            },
            "usage_example": {
                "method": "POST",
                "url": "https://api.deepl.com/v2/translate",
                "headers": {
                    "Authorization": "DeepL-Auth-Key {api_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                "body": {
                    "text": "Hello, world!",
                    "target_lang": "ZH",
                    "source_lang": "EN"
                }
            },
            "notes": "需要稳定的国际网络连接，当前环境可能无法稳定访问"
        },
        {
            "name": "OpenAI Sora2视频生成",
            "provider": "OpenAI",
            "description": "电影级带货视频生成，支持9:16竖屏、1080×1920分辨率、15秒时长、Cinematic Ultra HD画质",
            "required_api_key": True,
            "endpoint_example": "https://api.openai.com/v1/video/generations",
            "config_template": {
                "api_key": "YOUR_OPENAI_API_KEY",
                "organization": "YOUR_ORG_ID",
                "base_url": "https://api.openai.com",
                "timeout_seconds": 120,
                "retry_count": 3
            },
            "usage_example": {
                "method": "POST",
                "url": "https://api.openai.com/v1/video/generations",
                "headers": {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                    "OpenAI-Organization": "{organization}"
                },
                "body": {
                    "model": "sora-2.0",
                    "prompt": "A cinematic video of a model wearing denim jacket",
                    "size": "1080x1920",
                    "duration": 15,
                    "quality": "hd"
                }
            },
            "notes": "任务137预配置参数：OpenAI Video兼容协议，需要配置API密钥后使用"
        },
        {
            "name": "Notebook LM永久记忆",
            "provider": "Google Notebook LM",
            "description": "全球独立思考大脑的永久记忆与知识底座，承载所有历史任务、全球市场情报、业务数据",
            "required_api_key": True,
            "endpoint_example": "https://notebooklm.googleapis.com/v1/models",
            "config_template": {
                "api_key": "YOUR_GOOGLE_API_KEY",
                "project_id": "YOUR_GOOGLE_CLOUD_PROJECT_ID",
                "base_url": "https://notebooklm.googleapis.com",
                "timeout_seconds": 60,
                "retry_count": 2
            },
            "notes": "需要Google Cloud项目配置，当前环境可能无法稳定连接"
        }
    ]
    
    # 生成每个API服务的配置文档
    generated_files = []
    
    for service in api_services:
        service_name = service["name"]
        file_name = f"{service_name.replace(' ', '_')}_配置文档.md"
        file_path = os.path.join(output_dir, file_name)
        
        # 构建Markdown内容
        content = f"""# {service_name} API配置文档

## 基本信息
- **服务提供商**: {service["provider"]}
- **描述**: {service["description"]}
- **是否需要API密钥**: {'是' if service["required_api_key"] else '否'}
- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 配置模板
```json
{json.dumps(service["config_template"], indent=2, ensure_ascii=False)}
```

## 使用示例
"""
        
        if "usage_example" in service:
            content += f"""```json
{json.dumps(service["usage_example"], indent=2, ensure_ascii=False)}
```

**说明**: 将 `{{api_key}}` 替换为你的实际API密钥。
"""
        else:
            content += "无具体使用示例，请参考官方文档。\n"
        
        content += f"""
## 端点信息
- **示例端点**: `{service["endpoint_example"]}`

## 注意事项
{service["notes"]}

## 故障排除
1. **连接失败**: 检查网络环境，确保可以访问国际网站
2. **SSL证书错误**: 更新系统根证书或使用 `verify=False`（仅测试环境）
3. **API密钥无效**: 确认API密钥有足够权限和余额
4. **超时问题**: 适当增加 `timeout_seconds` 参数值

## 相关资源
- 官方文档: 请访问提供商官方网站
- 帮助支持: 联系提供商技术支持
"""
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        generated_files.append(file_path)
        print(f"✅ 生成: {file_name}")
    
    # 生成一键导入脚本
    script_path = os.path.join(output_dir, "一键导入API配置.py")
    script_content = '''#!/usr/bin/env python3
"""
API配置一键导入脚本
自动读取配置文档并生成配置对象
"""

import os
import json
import sys

def import_api_configs(config_dir: str = "."):
    """导入API配置"""
    print("=== API配置导入 ===")
    
    # 读取所有配置文档
    config_files = [f for f in os.listdir(config_dir) if f.endswith('_配置文档.md')]
    
    if not config_files:
        print("⚠️  未找到配置文档")
        return {}
    
    configs = {}
    
    for config_file in config_files:
        file_path = os.path.join(config_dir, config_file)
        
        try:
            # 从Markdown文件中提取JSON配置
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找配置模板部分
            import re
            pattern = r'```json\\n(.*?)\\n```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            if matches:
                config_json = matches[0]
                config_data = json.loads(config_json)
                
                # 生成服务名（从文件名提取）
                service_name = config_file.replace('_配置文档.md', '').replace('_', ' ')
                configs[service_name] = config_data
                
                print(f"✅ 导入: {service_name}")
            else:
                print(f"⚠️  跳过: {config_file} (未找到JSON配置)")
                
        except Exception as e:
            print(f"❌ 导入失败 {config_file}: {e}")
    
    print(f"\\n导入完成，共导入 {len(configs)} 个API配置")
    return configs

if __name__ == "__main__":
    # 默认使用当前目录
    config_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    if not os.path.exists(config_dir):
        print(f"❌ 目录不存在: {config_dir}")
        sys.exit(1)
    
    configs = import_api_configs(config_dir)
    
    # 输出配置摘要
    if configs:
        print("\\n=== 配置摘要 ===")
        for name, config in configs.items():
            print(f"• {name}: {len(config)}个参数")
    
    # 保存为JSON文件
    output_path = "api_configs.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)
    
    print(f"\\n配置已保存到: {output_path}")
'''
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    generated_files.append(script_path)
    print(f"✅ 生成: 一键导入API配置.py")
    
    # 生成网络环境适配建议文档
    advice_path = os.path.join(output_dir, "网络环境适配建议.md")
    advice_content = f"""# 网络环境适配建议

## 当前环境诊断
基于任务133-135的连续失败，诊断当前运行环境存在以下网络层限制：

### 主要问题
1. **SSL证书不兼容**: 无法与部分国际API服务建立安全连接
2. **代理失效**: 代理服务器配置问题导致连接超时
3. **国际网站防火墙阻止**: 部分国际网站无法访问
4. **网络不稳定**: 连接时断时续，影响API调用成功率

### 影响范围
- 所有依赖外部网络调用的能力模块无法稳定运行：
  - Firecrawl全域爬虫
  - DeepL多语种翻译
  - Multilingual原创检测
  - 智能风控合规系统
  - OpenAI Sora2视频生成
  - Notebook LM永久记忆

## 适配策略

### 短期方案（立即实施）
1. **聚焦核心可运行模块**:
   - 暂停依赖外部API的服务
   - 确保本地处理、数据同步等核心模块正常工作
   
2. **API配置文档化**:
   - 为无法连接的服务生成独立配置文档
   - 待用户配置密钥后自动恢复使用
   
3. **简化集成范围**:
   - 仅保留可访问平台（如Amazon、Google Trends）
   - 基于实际网络可达性选择性启用平台

### 中期方案（环境优化）
1. **网络环境升级**:
   - 在具备正常国际网络访问能力的环境中部署系统
   - 配置稳定的代理服务器和SSL证书
   
2. **连接优化**:
   - 实现网络连接诊断与自动修复机制
   - 针对SSL错误更新根证书或配置信任链

### 长期方案（架构优化）
1. **混合架构设计**:
   - 本地处理 + 云端API调用的混合模式
   - 智能路由：根据网络状态自动选择可用服务
   
2. **多区域部署**:
   - 在不同地区部署镜像服务
   - 根据用户地理位置选择最优接入点

## 实施步骤

### 第一步：状态清理（已完成）
- 标记异常任务为失败状态
- 清理阻塞队列
- 保留用户明确要求的任务（如Sora2接入）

### 第二步：链路校验（进行中）
- 测试SellAI与OpenClaw自动触发链路
- 验证核心调度器功能

### 第三步：环境适配（当前步骤）
1. 调整外部API调用策略
2. 生成API配置文档
3. 创建一键导入脚本

### 第四步：报告生成
1. 汇总重启前后状态对比
2. 记录链路测试结果
3. 提供网络适配建议

## 注意事项
1. **安全性**: 妥善保管API密钥，避免泄露
2. **成本控制**: 监控API调用频率，避免超额费用
3. **合规性**: 确保API使用符合服务条款和法律法规
4. **容错性**: 实现优雅降级，确保核心功能可用

## 监控指标
1. **连接成功率**: 目标 ≥90%
2. **响应时间**: 平均 <5秒
3. **错误率**: 目标 <5%
4. **可用性**: 目标 99.9%

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(advice_path, 'w', encoding='utf-8') as f:
        f.write(advice_content)
    
    generated_files.append(advice_path)
    print(f"✅ 生成: 网络环境适配建议.md")
    
    # 生成汇总报告
    summary_path = os.path.join(output_dir, "API配置汇总报告.md")
    summary_content = f"""# API配置汇总报告

## 概览
- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **服务数量**: {len(api_services)}
- **输出目录**: `{output_dir}`
- **文件总数**: {len(generated_files)}

## 服务列表
"""
    
    for i, service in enumerate(api_services, 1):
        summary_content += f"""
### {i}. {service['name']}
- **提供商**: {service['provider']}
- **描述**: {service['description']}
- **状态**: {'需要API密钥' if service['required_api_key'] else '无需密钥'}
- **配置文档**: `{service['name'].replace(' ', '_')}_配置文档.md`
"""
    
    summary_content += f"""
## 生成文件
"""
    
    for file_path in generated_files:
        file_name = os.path.basename(file_path)
        summary_content += f"- `{file_name}`\n"
    
    summary_content += f"""
## 使用说明

### 1. 配置API密钥
1. 访问各服务提供商的官方网站
2. 注册账号并申请API密钥
3. 复制密钥到对应的配置模板中

### 2. 导入配置
使用一键导入脚本快速加载配置：
```bash
python3 一键导入API配置.py
```

### 3. 环境检查
1. 确保网络环境可以访问国际网站
2. 配置SSL证书（如有需要）
3. 测试基础连接性

### 4. 故障排除
参考各服务的配置文档中的「故障排除」章节。

## 后续步骤
1. **测试连接**: 验证各API服务的可用性
2. **集成到系统**: 将配置集成到SellAI调度器
3. **监控告警**: 设置连接监控和自动告警
4. **定期更新**: 定期检查配置的有效性

---
*此报告自动生成，配置详情请查看各服务的独立文档。*
"""
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"✅ 生成: API配置汇总报告.md")
    
    print(f"\n=== 生成完成 ===")
    print(f"共生成 {len(generated_files)} 个文件到 {output_dir}/")
    print("\n下一步：")
    print("1. 将API配置文档提供给用户")
    print("2. 用户配置密钥后，系统可自动调用外部服务")
    print("3. 继续执行任务137（Sora2接入）")
    
    return generated_files

if __name__ == "__main__":
    generate_api_configs()