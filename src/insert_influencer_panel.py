#!/usr/bin/env python3
"""
在办公室HTML中插入达人洽谈面板
"""

import sys
import os

def insert_panel():
    input_file = "outputs/仪表盘/SellAI_办公室_流量爆破版.html"
    output_file = "outputs/仪表盘/SellAI_办公室_达人洽谈版.html"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到插入位置：在"seo-optimization-panel"的闭合div之后
    # 查找包含"seo-optimization-panel"的行
    insert_index = -1
    for i, line in enumerate(lines):
        if 'seo-optimization-panel' in line and '</div>' in line:
            # 找到闭合div
            # 我们需要在这个div之后插入
            insert_index = i + 1
            break
    
    if insert_index == -1:
        # 备用方案：在成本构成分析之后
        for i, line in enumerate(lines):
            if '成本构成分析' in line:
                # 找到这个section的结束
                for j in range(i, len(lines)):
                    if '</div>' in lines[j] and j > i + 10:
                        insert_index = j + 1
                        break
                break
    
    if insert_index == -1:
        # 最后方案：在右侧面板内容末尾插入
        for i, line in enumerate(lines):
            if '<div class="right-panel">' in line:
                # 找到对应的闭合div
                depth = 0
                for j in range(i, len(lines)):
                    if '<div' in lines[j] and not '</div>' in lines[j]:
                        depth += 1
                    elif '</div>' in lines[j]:
                        depth -= 1
                        if depth == 0:
                            insert_index = j
                            break
                break
    
    if insert_index == -1:
        print("无法找到插入位置")
        return False
    
    # 达人洽谈面板HTML
    influencer_panel = '''                <!-- 达人洽谈面板 -->
                <div class="influencer-outreach-panel" id="influencer-outreach-panel">
                    <div class="monitor-title">
                        <i class="fas fa-users"></i> 达人洽谈军团
                    </div>
                    
                    <div class="influencer-status-summary">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div>
                                <div style="font-size: 12px; color: #666;">合作名单状态</div>
                                <div style="font-size: 14px; font-weight: 600; color: #34c759;" id="influencer-list-status">就绪</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">响应率</div>
                                <div style="font-size: 14px; font-weight: 600; color: #007aff;" id="influencer-response-rate">--</div>
                            </div>
                        </div>
                        
                        <div style="background: #f0f0f0; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">项目进度</div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                                    <div id="influencer-progress-bar" style="height: 100%; width: 0%; background: #007aff; transition: width 0.3s;"></div>
                                </div>
                                <div style="font-size: 12px; color: #333;" id="influencer-progress-text">0%</div>
                            </div>
                        </div>
                        
                        <div class="influencer-stats-grid">
                            <div class="stat-card">
                                <div class="stat-label">已联系</div>
                                <div class="stat-value" id="influencer-contacted">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">已回复</div>
                                <div class="stat-value" id="influencer-replied">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">谈判中</div>
                                <div class="stat-value" id="influencer-negotiating">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">已签约</div>
                                <div class="stat-value" id="influencer-contracted">0</div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 16px;">
                            <button class="btn btn-primary" id="btn-schedule-campaign" style="width: 100%;">
                                <i class="fas fa-play-circle"></i> 调度合作活动
                            </button>
                            <button class="btn btn-outline" id="btn-check-responses" style="width: 100%; margin-top: 8px;">
                                <i class="fas fa-sync-alt"></i> 检查回复
                            </button>
                        </div>
                        
                        <div style="margin-top: 16px; font-size: 11px; color: #999; line-height: 1.4;">
                            <i class="fas fa-info-circle"></i> 达人洽谈军团自动筛选高潜博主，生成本土化英文话术，批量私信并智能跟进。
                        </div>
                    </div>
                </div>
'''
    
    # 插入新行
    lines.insert(insert_index, influencer_panel)
    
    # 现在需要在CSS中添加样式
    # 找到<style>标签的结束
    style_end_index = -1
    for i, line in enumerate(lines):
        if '<style>' in line:
            for j in range(i, len(lines)):
                if '</style>' in lines[j]:
                    style_end_index = j
                    break
            break
    
    if style_end_index != -1:
        # 插入CSS
        influencer_css = '''        /* 达人洽谈面板样式 */
        .influencer-outreach-panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            margin-top: 20px;
            border: 1px solid #e0e0e0;
        }
        
        .influencer-status-summary {
            background: #ffffff;
            border-radius: 6px;
            padding: 12px;
            border: 1px solid #e0e0e0;
        }
        
        .influencer-stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 12px;
        }
        
        .stat-card {
            background: #f8f9fa;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            border: 1px solid #e0e0e0;
        }
        
        .stat-label {
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .stat-value {
            font-size: 16px;
            font-weight: 700;
            color: #333;
        }
        
        .btn-primary {
            background: #007aff;
            color: white;
            border: none;
        }
        
        .btn-outline {
            background: transparent;
            color: #007aff;
            border: 1px solid #007aff;
        }
'''
        lines.insert(style_end_index, influencer_css)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"达人洽谈面板已成功插入到: {output_file}")
    return True

if __name__ == "__main__":
    success = insert_panel()
    sys.exit(0 if success else 1)