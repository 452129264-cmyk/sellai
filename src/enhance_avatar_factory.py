#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分身工厂节点增强脚本
为SellAI工作流的分身工厂节点添加垂直模板加载功能
"""

import json
import os
import sys

def load_workflow(file_path):
    """加载工作流JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_workflow(workflow, file_path):
    """保存工作流JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    print(f"✅ 工作流已保存: {file_path}")

def find_node_by_id(workflow, node_id):
    """根据ID查找节点"""
    for node in workflow.get('nodes', []):
        if node.get('id') == node_id:
            return node
    return None

def enhance_avatar_factory_code():
    """返回增强后的分身工厂节点代码"""
    return '''// 分身创建处理器 - 增强版（支持垂直模板）
const fs = require('fs');
const path = require('path');

// 读取请求数据
const requestData = JSON.parse(process.env.REQUEST_BODY || '{}');

// 垂直模板加载逻辑
function loadTemplate(templateId) {
    const templateDir = path.join(__dirname, '../outputs/分身模板库');
    
    // 映射template_id到文件名
    const templateMap = {
        'vertical_001': '牛仔品类选品分身.json',
        'vertical_002': 'TikTok爆款内容分身.json',
        'vertical_003': '独立站运营分身.json',
        'vertical_004': '亚马逊广告优化分身.json',
        'vertical_005': '政府补贴申报分身.json',
        'vertical_006': 'AI工具评测分身.json',
        'vertical_007': '跨境电商物流优化分身.json',
        'vertical_008': '社交媒体广告投放分身.json',
        'vertical_009': '网红KOL对接分身.json',
        'vertical_010': '海外仓库存管理分身.json'
    };
    
    const fileName = templateMap[templateId];
    if (!fileName) {
        throw new Error('模板ID无效: ' + templateId);
    }
    
    const filePath = path.join(templateDir, fileName);
    if (!fs.existsSync(filePath)) {
        throw new Error('模板文件不存在: ' + filePath);
    }
    
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
}

// 合并模板配置与自定义参数
function mergeConfig(template, customizations) {
    const config = JSON.parse(JSON.stringify(template));
    
    // 更新persona_config
    if (customizations.persona) {
        Object.assign(config.persona_config, customizations.persona);
    }
    
    // 更新task_configurations参数
    if (customizations.task_parameters && config.task_configurations.length > 0) {
        Object.assign(config.task_configurations[0].parameters, customizations.task_parameters);
    }
    
    // 更新resource_requirements
    if (customizations.resources) {
        Object.assign(config.resource_requirements, customizations.resources);
    }
    
    return config;
}

try {
    // 检查是否使用垂直模板
    const useVerticalTemplate = requestData.use_vertical_template || false;
    const templateId = requestData.template_id;
    const customizations = requestData.customizations || {};
    
    let avatarConfig;
    
    if (useVerticalTemplate && templateId) {
        // 加载垂直模板
        console.log('正在加载垂直模板: ' + templateId);
        const template = loadTemplate(templateId);
        
        // 合并自定义配置
        avatarConfig = mergeConfig(template, customizations);
        
        // 生成唯一ID
        const avatarId = 'vertical_' + templateId + '_' + Date.now() + '_' + 
                         Math.random().toString(36).substr(2, 4);
        avatarConfig.avatar_id = avatarId;
        
        // 添加创建元数据
        avatarConfig.metadata = {
            created_at: new Date().toISOString(),
            last_active: new Date().toISOString(),
            template_id: templateId,
            template_name: template.template_name,
            total_conversations: 0,
            success_rate: 0
        };
        
        console.log('垂直分身配置生成完成: ' + avatarId);
    } else {
        // 传统创建逻辑（兼容旧版）
        console.log('使用传统分身创建逻辑');
        const avatarId = 'avatar_' + Date.now() + '_' + 
                         Math.random().toString(36).substr(2, 9);
        
        avatarConfig = {
            avatar_id: avatarId,
            name: requestData.name || '未命名分身',
            persona_config: requestData.persona_config || {
                role: 'AI合伙人',
                personality: '专业高效',
                expertise: ['通用技能'],
                communication_style: '友好直接'
            },
            task_configurations: requestData.task_configurations || [],
            capability_matrix: requestData.capability_matrix || {
                data_crawling: false,
                business_matching: false,
                content_creation: false,
                account_operation: false,
                financial_analysis: false
            },
            resource_requirements: requestData.resource_requirements || {
                preferred_platforms: [],
                target_regions: [],
                profit_margin_threshold: 30,
                investment_range: ['$100', '$10000']
            },
            collaboration_protocol: requestData.collaboration_protocol || {
                can_initiate_chat: true,
                can_receive_tasks: true,
                preferred_partners: [],
                notification_channels: ['wechat', 'email']
            },
            metadata: {
                created_at: new Date().toISOString(),
                last_active: new Date().toISOString(),
                total_conversations: 0,
                success_rate: 0
            }
        };
    }
    
    // 读取现有分身配置
    const configPath = path.join(__dirname, 'temp/avatars_config.json');
    let existingConfig = { avatars: {}, last_updated: '', total_count: 0 };
    
    if (fs.existsSync(configPath)) {
        const content = fs.readFileSync(configPath, 'utf8');
        existingConfig = JSON.parse(content);
    }
    
    // 添加新分身
    if (!existingConfig.avatars) existingConfig.avatars = {};
    existingConfig.avatars[avatarConfig.avatar_id] = avatarConfig;
    existingConfig.last_updated = new Date().toISOString();
    existingConfig.total_count = Object.keys(existingConfig.avatars).length;
    
    // 保存配置
    fs.writeFileSync(configPath, JSON.stringify(existingConfig, null, 2));
    
    // 返回成功响应
    const response = {
        success: true,
        avatar_id: avatarConfig.avatar_id,
        message: '分身创建成功',
        config: avatarConfig,
        is_vertical: useVerticalTemplate && templateId ? true : false
    };
    
    console.log(JSON.stringify(response));
    return response;
    
} catch (error) {
    // 错误处理
    const errorResponse = {
        success: false,
        message: '分身创建失败: ' + error.message,
        error_details: error.stack
    };
    
    console.error(JSON.stringify(errorResponse));
    return errorResponse;
}
'''

def main():
    """主函数"""
    # 文件路径
    input_file = "outputs/工作流/SellAI_OpenClow_完整版.json"
    output_file = "outputs/工作流/SellAI_无限分身_升级版.json"
    
    print("🚀 开始增强分身工厂节点...")
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ 输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 加载工作流
    print(f"📥 加载工作流: {input_file}")
    workflow = load_workflow(input_file)
    
    # 查找分身工厂节点
    avatar_factory_node = find_node_by_id(workflow, "avatar_factory")
    if not avatar_factory_node:
        print("❌ 未找到分身工厂节点 (id: avatar_factory)")
        sys.exit(1)
    
    print("✅ 找到分身工厂节点")
    
    # 更新节点代码
    avatar_factory_node['data']['code'] = enhance_avatar_factory_code()
    avatar_factory_node['data']['description'] = "增强版分身工厂，支持垂直模板加载与参数合并"
    
    print("✅ 分身工厂节点代码已更新")
    
    # 保存增强版工作流
    save_workflow(workflow, output_file)
    
    # 生成更新说明
    update_notes = f"""
📋 分身工厂节点增强完成

**增强功能：**
1. ✅ 垂直模板加载：支持从 `outputs/分身模板库/` 加载10个专业领域模板
2. ✅ 参数合并：自动合并模板基础配置与用户自定义参数
3. ✅ 智能ID生成：根据模板类型生成有意义的唯一ID
4. ✅ 错误处理：完善的异常捕获与错误信息返回

**模板支持：**
- vertical_001: 牛仔品类选品分身
- vertical_002: TikTok爆款内容分身
- vertical_003: 独立站运营分身
- vertical_004: 亚马逊广告优化分身
- vertical_005: 政府补贴申报分身
- vertical_006: AI工具评测分身
- vertical_007: 跨境电商物流优化分身
- vertical_008: 社交媒体广告投放分身
- vertical_009: 网红KOL对接分身
- vertical_010: 海外仓库存管理分身

**使用方法：**
在创建分身请求中添加以下字段：
```json
{{
  "use_vertical_template": true,
  "template_id": "vertical_001",
  "customizations": {{
    "persona": {{"role": "牛仔专家"}},
    "task_parameters": {{"target_margin_min": 40}},
    "resources": {{"target_regions": ["US"]}}
  }}
}}
```

**文件位置：**
- 增强版工作流：{output_file}
- 垂直模板库：outputs/分身模板库/
- 操作手册：docs/无限分身操作手册.md
"""
    
    print(update_notes)
    
    # 保存更新说明
    notes_file = "docs/分身工厂节点增强说明.md"
    with open(notes_file, 'w', encoding='utf-8') as f:
        f.write(update_notes)
    
    print(f"📝 更新说明已保存: {notes_file}")

if __name__ == "__main__":
    main()