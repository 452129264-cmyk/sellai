#!/usr/bin/env python3
"""
在办公室HTML中插入短视频引流面板
"""

import sys
import os

def insert_panel():
    input_file = "outputs/仪表盘/SellAI_办公室_达人洽谈版.html"
    output_file = "outputs/仪表盘/SellAI_办公室_短视频引流版.html"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到插入位置：在"influencer-outreach-panel"的闭合div之后
    insert_index = -1
    for i, line in enumerate(lines):
        if 'influencer-outreach-panel' in line and '</div>' in line:
            # 找到完整的闭合div
            # 我们需要在这个div之后插入
            insert_index = i + 1
            break
    
    if insert_index == -1:
        # 备用方案：在SEO优化面板之后
        for i, line in enumerate(lines):
            if 'seo-optimization-panel' in line and '</div>' in line:
                insert_index = i + 1
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
    
    # 短视频引流面板HTML
    short_video_panel = '''                <!-- 短视频引流面板 -->
                <div class="short-video-panel" id="short-video-panel">
                    <div class="monitor-title">
                        <i class="fas fa-video"></i> 短视频引流军团
                    </div>
                    
                    <div class="short-video-status-summary">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div>
                                <div style="font-size: 12px; color: #666;">视频生成状态</div>
                                <div style="font-size: 14px; font-weight: 600; color: #34c759;" id="video-generation-status">就绪</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">发布成功率</div>
                                <div style="font-size: 14px; font-weight: 600; color: #007aff;" id="video-publish-success-rate">--</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">平均点击率</div>
                                <div style="font-size: 14px; font-weight: 600; color: #5856d6;" id="average-ctr">--</div>
                            </div>
                        </div>
                        
                        <div style="background: #f0f0f0; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">引流效果概览</div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                                    <div id="video-progress-bar" style="height: 100%; width: 0%; background: #007aff; transition: width 0.3s;"></div>
                                </div>
                                <div style="font-size: 12px; color: #333;" id="video-progress-text">0%</div>
                            </div>
                        </div>
                        
                        <div class="short-video-stats-grid">
                            <div class="stat-card">
                                <div class="stat-label">已生成视频</div>
                                <div class="stat-value" id="videos-generated">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">已发布平台</div>
                                <div class="stat-value" id="platforms-published">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">总观看量</div>
                                <div class="stat-value" id="total-views">0</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">引流点击</div>
                                <div class="stat-value" id="total-clicks">0</div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 16px;">
                            <button class="btn btn-primary" id="btn-generate-videos" style="width: 100%;">
                                <i class="fas fa-play-circle"></i> 生成AI视频
                            </button>
                            <button class="btn btn-outline" id="btn-distribute-videos" style="width: 100%; margin-top: 8px;">
                                <i class="fas fa-share-alt"></i> 分发到平台
                            </button>
                            <button class="btn btn-outline" id="btn-analyze-performance" style="width: 100%; margin-top: 8px;">
                                <i class="fas fa-chart-line"></i> 分析引流效果
                            </button>
                        </div>
                        
                        <div style="margin-top: 16px; font-size: 11px; color: #999; line-height: 1.4;">
                            <i class="fas fa-info-circle"></i> 短视频引流军团自动生成黑人模特牛仔穿搭AI视频，分发到TikTok、YouTube、Instagram、小红书四平台，挂载独立站外链，实时追踪引流效果。
                        </div>
                    </div>
                </div>
'''
    
    # 插入新行
    lines.insert(insert_index, short_video_panel)
    
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
        short_video_css = '''        /* 短视频引流面板样式 */
        .short-video-panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            margin-top: 20px;
            border: 1px solid #e0e0e0;
        }
        
        .short-video-status-summary {
            background: #ffffff;
            border-radius: 6px;
            padding: 12px;
            border: 1px solid #e0e0e0;
        }
        
        .short-video-stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 12px;
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
        lines.insert(style_end_index, short_video_css)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"短视频引流面板已成功插入到: {output_file}")
    return True

if __name__ == "__main__":
    success = insert_panel()
    sys.exit(0 if success else 1)