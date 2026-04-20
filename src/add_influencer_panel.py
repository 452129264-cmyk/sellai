#!/usr/bin/env python3
"""
在办公室HTML中添加达人洽谈面板
"""

import re
import os
import sys

def add_influencer_panel(input_file: str, output_file: str):
    """在SEO优化面板后添加达人洽谈面板"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到SEO优化面板的结束位置
    # 搜索</div> <!-- SEO优化面板结束？实际上需要找到正确的闭合div
    # 更简单的方法：在成本构成分析div后插入新面板
    
    # 查找 "成本构成分析" 部分的结束
    # 模式匹配：<div class="cost-breakdown"> ... </div>
    # 但需要确保插入在正确位置
    
    # 替代方案：在"seo-optimization-panel"的闭合div后插入
    
    # 找到seo-optimization-panel的开始和结束
    panel_pattern = r'(<div class="seo-optimization-panel" id="seo-optimization-panel">.*?</div>\s*</div>)'
    
    # 使用非贪婪匹配
    match = re.search(panel_pattern, content, re.DOTALL)
    
    if not match:
        print("未找到SEO优化面板，尝试其他方法...")
        # 在右侧面板内容末尾插入
        right_panel_pattern = r'(<div class="right-panel">.*?)(</div>\s*</div>\s*</div>\s*</div>)'
        match = re.search(right_panel_pattern, content, re.DOTALL)
        
        if match:
            before = match.group(1)
            after = match.group(2)
            
            # 创建达人洽谈面板HTML
            influencer_panel = '''
                <!-- 达人洽谈面板 -->
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
            
            # 插入新面板
            new_content = before + influencer_panel + after
            
            # 还需要在CSS中添加样式
            # 找到<style>标签的结束位置
            style_pattern = r'(<style>.*?)(</style>)'
            style_match = re.search(style_pattern, content, re.DOTALL)
            
            if style_match:
                style_before = style_match.group(1)
                style_after = style_match.group(2)
                
                # 添加达人洽谈面板样式
                influencer_css = '''
                    /* 达人洽谈面板样式 */
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
                
                new_style = style_before + influencer_css + style_after
                new_content = new_content.replace(style_before + style_after, new_style)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"达人洽谈面板已添加到: {output_file}")
            return True
    
    print("添加达人洽谈面板失败")
    return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使用方法: python add_influencer_panel.py <输入文件> <输出文件>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        sys.exit(1)
    
    add_influencer_panel(input_file, output_file)