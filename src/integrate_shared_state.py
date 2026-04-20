"""
集成共享状态库到工作流
修改现有工作流，添加共享状态库调用
"""

import json
import os
import sys
from datetime import datetime

def load_workflow(file_path):
    """加载工作流文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_workflow(workflow, file_path):
    """保存工作流文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"工作流已保存: {file_path}")

def add_shared_state_nodes(workflow):
    """
    在工作流中添加共享状态库相关节点
    
    修改内容:
    1. 在avatar_factory节点中添加分身注册到共享状态库的逻辑
    2. 在data_crawler和intelligence_officer之间添加opportunity_deduplicator节点
    3. 更新相关边的连接
    """
    
    # 1. 修改avatar_factory节点，添加分身注册逻辑
    avatar_factory_index = None
    for i, node in enumerate(workflow['nodes']):
        if node['id'] == 'avatar_factory':
            avatar_factory_index = i
            break
    
    if avatar_factory_index is not None:
        # 获取现有代码
        existing_code = workflow['nodes'][avatar_factory_index]['data']['code']
        
        # 在代码末尾添加共享状态库注册逻辑
        registration_code = '''
// 共享状态库注册逻辑
function registerAvatarToSharedState(avatarConfig) {
    try {
        const fs = require('fs');
        const path = require('path');
        const { execSync } = require('child_process');
        
        // 构建注册数据
        const registrationData = {
            avatar_id: avatarConfig.avatar_id,
            avatar_name: avatarConfig.name || avatarConfig.avatar_name,
            template_id: avatarConfig.metadata?.template_id || avatarConfig.template_id,
            capability_scores: avatarConfig.capability_matrix || avatarConfig.capability_scores || {},
            specialization_tags: avatarConfig.resource_requirements?.tags || 
                                avatarConfig.specialization_tags || [],
            success_rate: 0.0,
            total_tasks_completed: 0,
            current_load: 0,
            last_active: new Date().toISOString(),
            created_at: new Date().toISOString()
        };
        
        // 调用Python脚本来注册分身
        const scriptPath = path.join(__dirname, 'src/shared_state_manager.py');
        const registrationJson = JSON.stringify(registrationData);
        
        // 使用临时文件传递数据
        const tempFile = path.join(__dirname, 'temp/avatar_registration.json');
        fs.writeFileSync(tempFile, registrationJson);
        
        // 执行Python脚本
        const pythonCode = `
import json
import sys
sys.path.append('/app/data/files')
from src.shared_state_manager import get_shared_state_manager

with open('${tempFile}', 'r', encoding='utf-8') as f:
    data = json.load(f)

manager = get_shared_state_manager()
manager.register_or_update_avatar_profile(
    avatar_id=data['avatar_id'],
    avatar_name=data['avatar_name'],
    template_id=data.get('template_id'),
    capability_scores=data.get('capability_scores'),
    specialization_tags=data.get('specialization_tags')
)
print('分身注册成功: ' + data['avatar_id'])
`;
        
        const pythonFile = path.join(__dirname, 'temp/register_avatar.py');
        fs.writeFileSync(pythonFile, pythonCode.replace('${tempFile}', tempFile));
        
        execSync(`python "${pythonFile}"`, { stdio: 'inherit' });
        
        console.log('分身已注册到共享状态库');
        return true;
    } catch (error) {
        console.error('分身注册到共享状态库失败:', error.message);
        return false;
    }
}

// 在分身创建成功后调用注册函数
if (response.success) {
    console.log('正在将分身注册到共享状态库...');
    const registrationSuccess = registerAvatarToSharedState(avatarConfig);
    if (registrationSuccess) {
        response.shared_state_registered = true;
    }
}
'''
        
        # 找到适当的位置插入代码
        # 在return response;之前插入
        if 'return response;' in existing_code:
            # 在return response;之前插入注册逻辑
            parts = existing_code.split('return response;')
            if len(parts) == 2:
                new_code = parts[0] + registration_code + '\n    return response;' + parts[1]
                workflow['nodes'][avatar_factory_index]['data']['code'] = new_code
                print("✓ avatar_factory节点已增强：添加共享状态库注册逻辑")
    
    # 2. 添加商机去重节点 (opportunity_deduplicator)
    deduplicator_node = {
        "id": "opportunity_deduplicator",
        "type": "code",
        "position": {
            "x": 400,
            "y": 900
        },
        "data": {
            "name": "商机去重与分配器",
            "description": "检查新商机是否已处理，去重后分配给合适的分身",
            "code": """// 商机去重与分配器
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 读取原始数据
const rawData = JSON.parse(process.env.INPUT_DATA || '{}');

// 构建商机信息
const opportunityInfo = {
    source_platform: rawData.source || 'unknown',
    original_id: rawData.id || rawData.opportunity_id || '',
    title: rawData.title || '未命名商机'
};

// 调用共享状态库检查去重
try {
    // 构建Python检查脚本
    const pythonCode = `
import sys
sys.path.append('/app/data/files')
from src.shared_state_manager import get_shared_state_manager

source_platform = ${JSON.stringify(opportunityInfo.source_platform)}
original_id = ${JSON.stringify(opportunityInfo.original_id)}
title = ${JSON.stringify(opportunityInfo.title)}

manager = get_shared_state_manager()
is_new, hash_val = manager.check_and_record_opportunity(
    source_platform=source_platform,
    original_id=original_id,
    title=title,
    status='pending'
)

print(JSON.stringify({
    is_new: is_new,
    opportunity_hash: hash_val,
    opportunity_info: opportunityInfo
}))
`;
    
    const pythonFile = path.join(__dirname, 'temp/check_opportunity.py');
    fs.writeFileSync(pythonFile, pythonCode);
    
    // 执行Python脚本
    const result = execSync(`python "${pythonFile}"`, { encoding: 'utf-8' });
    const checkResult = JSON.parse(result.trim());
    
    console.log('商机检查结果:', JSON.stringify(checkResult));
    
    if (checkResult.is_new) {
        // 新商机：寻找合适的分身
        const findAvatarCode = `
import sys
sys.path.append('/app/data/files')
from src.shared_state_manager import get_shared_state_manager

required_capabilities = ['data_crawling', 'financial_analysis']
manager = get_shared_state_manager()
best_avatar = manager.find_best_avatar_for_task(
    required_capabilities=required_capabilities,
    min_score_threshold=0.6
)

# 默认分配给情报官
if not best_avatar:
    best_avatar = 'intelligence_officer'

print(JSON.stringify({
    best_avatar: best_avatar,
    opportunity_hash: ${JSON.stringify(checkResult.opportunity_hash)}
}))
`;
        
        const findAvatarFile = path.join(__dirname, 'temp/find_avatar.py');
        fs.writeFileSync(findAvatarFile, findAvatarCode);
        
        const avatarResult = execSync(`python "${findAvatarFile}"`, { encoding: 'utf-8' });
        const avatarAssignment = JSON.parse(avatarResult.trim());
        
        console.log('任务分配:', JSON.stringify(avatarAssignment));
        
        // 记录任务分配
        const recordAssignmentCode = `
import sys
sys.path.append('/app/data/files')
from src.shared_state_manager import get_shared_state_manager

manager = get_shared_state_manager()
assignment_id = manager.record_task_assignment(
    opportunity_hash=${JSON.stringify(avatarAssignment.opportunity_hash)},
    assigned_avatar=${JSON.stringify(avatarAssignment.best_avatar)},
    priority=2
)

print(JSON.stringify({
    assignment_id: assignment_id,
    message: '任务分配记录成功'
}))
`;
        
        const recordAssignmentFile = path.join(__dirname, 'temp/record_assignment.py');
        fs.writeFileSync(recordAssignmentFile, recordAssignmentCode);
        
        const recordResult = execSync(`python "${recordAssignmentFile}"`, { encoding: 'utf-8' });
        console.log('分配记录:', recordResult.trim());
        
        // 构建传递给情报官的数据
        const processedData = {
            ...rawData,
            _metadata: {
                is_new_opportunity: true,
                opportunity_hash: checkResult.opportunity_hash,
                assigned_to: avatarAssignment.best_avatar,
                assignment_id: JSON.parse(recordResult.trim()).assignment_id,
                processed_at: new Date().toISOString()
            }
        };
        
        return {
            success: true,
            is_new_opportunity: true,
            data: processedData,
            next_node: 'intelligence_officer',
            message: '新商机已去重并分配任务'
        };
        
    } else {
        // 已处理商机，跳过深度分析
        console.log('商机已处理，跳过:', checkResult.opportunity_hash);
        
        return {
            success: true,
            is_new_opportunity: false,
            data: null,
            next_node: null,
            message: '商机已处理，跳过分析'
        };
    }
    
} catch (error) {
    console.error('商机去重处理失败:', error.message);
    
    // 错误时仍传递数据给情报官
    return {
        success: false,
        is_new_opportunity: true,
        data: rawData,
        next_node: 'intelligence_officer',
        error: error.message,
        message: '去重检查失败，仍传递数据'
    };
}
"""
        }
    }
    
    # 添加新节点到工作流
    workflow['nodes'].append(deduplicator_node)
    print("✓ 添加新节点: opportunity_deduplicator (商机去重与分配器)")
    
    # 3. 更新边的连接
    # 找到从data_crawler到intelligence_officer的边
    edge_to_remove = None
    for i, edge in enumerate(workflow['edges']):
        if edge['source'] == 'data_crawler' and edge['target'] == 'intelligence_officer':
            edge_to_remove = i
            break
    
    if edge_to_remove is not None:
        # 移除原有边
        removed_edge = workflow['edges'].pop(edge_to_remove)
        print(f"✓ 移除边: {removed_edge['source']} -> {removed_edge['target']}")
        
        # 添加新边：data_crawler -> opportunity_deduplicator
        workflow['edges'].append({
            "id": "edge_crawler_to_deduplicator",
            "source": "data_crawler",
            "target": "opportunity_deduplicator",
            "data": {
                "condition": "always"
            }
        })
        print("✓ 添加新边: data_crawler -> opportunity_deduplicator")
        
        # 添加新边：opportunity_deduplicator -> intelligence_officer (仅新商机)
        workflow['edges'].append({
            "id": "edge_deduplicator_to_intel_new",
            "source": "opportunity_deduplicator",
            "target": "intelligence_officer",
            "data": {
                "condition": "output.is_new_opportunity == true"
            }
        })
        print("✓ 添加新边: opportunity_deduplicator -> intelligence_officer (新商机条件)")
    
    # 4. 增强intelligence_officer节点的prompt，添加共享状态库集成说明
    for i, node in enumerate(workflow['nodes']):
        if node['id'] == 'intelligence_officer':
            # 在现有prompt中添加共享状态库相关说明
            existing_prompt = node['data']['prompt']
            
            # 添加共享状态库集成说明
            shared_state_section = '''

## 共享状态库集成
系统已集成共享状态库，确保商机处理的去重和高效分配：

1. **去重检查**：新商机进入时已自动检查是否已在 `processed_opportunities` 表中
2. **任务分配**：新商机已自动分配给最适合的分身，并在 `task_assignments` 表中记录
3. **状态更新**：任务完成后需调用共享状态库更新状态和记录成本

## 处理要求
1. 检查输入数据中的 `_metadata.opportunity_hash` 字段
2. 完成任务后，必须调用共享状态库更新任务状态
3. 记录分析过程中产生的成本消耗

## 状态更新代码示例
完成深度分析后，调用以下API更新任务状态：
\`\`\`
POST /shared_state/update_task_status
{
  "assignment_id": "输入数据中的assignment_id",
  "completion_status": "completed",
  "result_summary": "分析完成总结"
}
\`\`\`
'''
            
            # 在现有prompt的合适位置插入
            if '## 输出格式' in existing_prompt:
                parts = existing_prompt.split('## 输出格式')
                new_prompt = parts[0] + shared_state_section + '\n## 输出格式' + parts[1]
                workflow['nodes'][i]['data']['prompt'] = new_prompt
                print("✓ intelligence_officer节点prompt已增强：添加共享状态库集成说明")
            break
    
    # 5. 更新工作流变量，添加共享状态库配置
    if 'variables' in workflow:
        workflow['variables']['shared_state_config'] = {
            "db_path": "data/shared_state/state.db",
            "tables": {
                "processed_opportunities": "已处理商机去重表",
                "task_assignments": "任务分配历史表",
                "avatar_capability_profiles": "分身能力画像表",
                "cost_consumption_logs": "成本消耗记录表"
            },
            "api_endpoints": {
                "check_opportunity": "/shared_state/check_opportunity",
                "assign_task": "/shared_state/assign_task",
                "update_task_status": "/shared_state/update_task_status",
                "record_cost": "/shared_state/record_cost"
            }
        }
        print("✓ 工作流变量已更新：添加shared_state_config")
    
    return workflow

def add_shared_state_edges(workflow):
    """添加与共享状态库相关的边连接"""
    
    # 确保opportunity_deduplicator节点存在
    deduplicator_exists = any(node['id'] == 'opportunity_deduplicator' for node in workflow['nodes'])
    
    if deduplicator_exists:
        print("✓ opportunity_deduplicator节点已存在")
    else:
        print("⚠ opportunity_deduplicator节点不存在，将不添加相关边")
        return workflow
    
    return workflow

def main():
    """主函数"""
    print("开始集成共享状态库到工作流...")
    
    # 输入和输出文件路径
    input_file = "outputs/工作流/SellAI_无限分身_升级版.json"
    output_file = "outputs/工作流/SellAI_无限分身_升级版_with_shared_state.json"
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 加载工作流
    print(f"加载工作流: {input_file}")
    workflow = load_workflow(input_file)
    
    # 添加共享状态库节点
    print("添加共享状态库相关节点...")
    workflow = add_shared_state_nodes(workflow)
    
    # 添加相关边连接
    print("更新边连接...")
    workflow = add_shared_state_edges(workflow)
    
    # 更新工作流描述
    workflow['description'] = "100%复刻OpenClow体验的24小时全自动全球赚钱AI合伙人，支持无限分身创建、专属办公室界面、社交智能匹配、共享状态库"
    workflow['version'] = "2.1"
    
    # 保存工作流
    save_workflow(workflow, output_file)
    
    print("\n集成完成!")
    print(f"新工作流文件: {output_file}")
    print("主要修改:")
    print("  1. avatar_factory节点增强: 添加分身注册到共享状态库逻辑")
    print("  2. 新增opportunity_deduplicator节点: 商机去重与任务分配")
    print("  3. 更新data_crawler到intelligence_officer的数据流")
    print("  4. intelligence_officer节点prompt增强: 添加共享状态库集成说明")
    print("  5. 工作流变量添加shared_state_config配置")

if __name__ == "__main__":
    main()