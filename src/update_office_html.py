#!/usr/bin/env python3
"""
更新办公室HTML，添加全行业资源浏览面板
"""

import re

def update_office_html(input_file, output_file):
    """更新办公室HTML文件"""
    
    print(f"读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义新的全行业资源面板HTML
    industry_panel_html = '''
                <!-- 全行业资源浏览面板 -->
                <div class="industry-resource-panel" id="industry-resource-panel">
                    <div class="monitor-title">
                        <i class="fas fa-industry"></i> 全行业商业资源库
                    </div>
                    
                    <div class="panel-toolbar">
                        <div class="search-box">
                            <input type="text" id="resource-search" placeholder="搜索资源标题、行业、描述...">
                            <i class="fas fa-search"></i>
                        </div>
                        
                        <div class="filter-section">
                            <div class="filter-group">
                                <label for="filter-industry">行业:</label>
                                <select id="filter-industry">
                                    <option value="">全部行业</option>
                                    <option value="制造业">制造业</option>
                                    <option value="服务业">服务业</option>
                                    <option value="科技">科技</option>
                                    <option value="农业">农业</option>
                                    <option value="零售/电商">零售/电商</option>
                                </select>
                            </div>
                            
                            <div class="filter-group">
                                <label for="filter-resource-type">资源类型:</label>
                                <select id="filter-resource-type">
                                    <option value="">全部类型</option>
                                    <option value="供应链">供应链</option>
                                    <option value="技术合作">技术合作</option>
                                    <option value="商品供应">商品供应</option>
                                    <option value="资金对接">资金对接</option>
                                    <option value="人才匹配">人才匹配</option>
                                </select>
                            </div>
                            
                            <div class="filter-group">
                                <label for="filter-region-scope">地域:</label>
                                <select id="filter-region-scope">
                                    <option value="">全部地域</option>
                                    <option value="本地">本地</option>
                                    <option value="区域">区域</option>
                                    <option value="全国">全国</option>
                                    <option value="全球">全球</option>
                                </select>
                            </div>
                            
                            <div class="filter-group">
                                <label for="filter-direction">供需方向:</label>
                                <select id="filter-direction">
                                    <option value="">全部方向</option>
                                    <option value="supply">供应</option>
                                    <option value="demand">需求</option>
                                    <option value="both">双向</option>
                                </select>
                            </div>
                            
                            <div class="filter-group">
                                <label for="filter-status">状态:</label>
                                <select id="filter-status">
                                    <option value="active">活跃</option>
                                    <option value="pending">待处理</option>
                                    <option value="completed">已完成</option>
                                    <option value="expired">已过期</option>
                                    <option value="archived">已归档</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="action-buttons">
                            <button class="btn btn-outline" id="refresh-resources">
                                <i class="fas fa-sync-alt"></i> 刷新
                            </button>
                            <button class="btn btn-primary" id="create-resource">
                                <i class="fas fa-plus"></i> 添加资源
                            </button>
                        </div>
                    </div>
                    
                    <div class="resource-stats">
                        <div class="stat-card small">
                            <div class="stat-label">总资源数</div>
                            <div class="stat-value" id="stat-total">0</div>
                        </div>
                        <div class="stat-card small">
                            <div class="stat-label">行业分类</div>
                            <div class="stat-value" id="stat-industries">0</div>
                        </div>
                        <div class="stat-card small">
                            <div class="stat-label">活跃资源</div>
                            <div class="stat-value" id="stat-active">0</div>
                        </div>
                        <div class="stat-card small">
                            <div class="stat-label">匹配记录</div>
                            <div class="stat-value" id="stat-matches">0</div>
                        </div>
                    </div>
                    
                    <div class="resource-list-container" id="resource-list-container">
                        <div class="loading-message">
                            <i class="fas fa-spinner fa-spin"></i>
                            <div>正在加载资源数据...</div>
                        </div>
                    </div>
                    
                    <div class="resource-info-footer">
                        <i class="fas fa-info-circle"></i> 全行业商业资源库支持供应链、项目合作、资源匹配、商务联营等非电商场景，覆盖全球所有市场。
                    </div>
                </div>
    '''
    
    # 定义新的CSS样式
    new_css = '''
        /* 全行业资源面板样式 */
        .industry-resource-panel {
            background: #ffffff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid #e8e8e8;
        }
        
        .industry-resource-panel .monitor-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .industry-resource-panel .monitor-title i {
            color: #007aff;
        }
        
        .panel-toolbar {
            margin-bottom: 20px;
        }
        
        .search-box {
            position: relative;
            margin-bottom: 16px;
        }
        
        .search-box input {
            width: 100%;
            padding: 10px 16px 10px 40px;
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            font-size: 14px;
            background: #fafafa;
        }
        
        .search-box i {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: #999;
        }
        
        .filter-section {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .filter-group {
            flex: 1;
            min-width: 120px;
        }
        
        .filter-group label {
            display: block;
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .filter-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            font-size: 13px;
            background: white;
        }
        
        .action-buttons {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }
        
        .resource-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .stat-card.small {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            border: 1px solid #e9ecef;
        }
        
        .stat-card.small .stat-label {
            font-size: 11px;
            color: #6c757d;
            margin-bottom: 4px;
        }
        
        .stat-card.small .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: #333;
        }
        
        .resource-list-container {
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
            background: #fcfcfc;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #eaeaea;
        }
        
        .resource-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid #e0e0e0;
            transition: all 0.2s;
        }
        
        .resource-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: #007aff;
        }
        
        .resource-header {
            margin-bottom: 12px;
        }
        
        .resource-title {
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
        }
        
        .resource-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            font-size: 11px;
        }
        
        .resource-industry, .resource-type, .resource-direction {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            color: #495057;
        }
        
        .resource-status {
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        
        .status-pending {
            background: #fff3cd;
            color: #856404;
        }
        
        .status-completed {
            background: #d1ecf1;
            color: #0c5460;
        }
        
        .status-expired {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status-archived {
            background: #e2e3e5;
            color: #383d41;
        }
        
        .resource-body {
            margin-bottom: 12px;
        }
        
        .resource-description {
            font-size: 13px;
            color: #666;
            line-height: 1.5;
            margin-bottom: 12px;
        }
        
        .resource-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            font-size: 12px;
        }
        
        .detail-item {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #555;
        }
        
        .detail-item i {
            color: #007aff;
            width: 14px;
        }
        
        .resource-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #f0f0f0;
            padding-top: 12px;
        }
        
        .resource-contact {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #666;
        }
        
        .resource-contact i {
            color: #6c757d;
        }
        
        .contact-email {
            color: #007aff;
        }
        
        .resource-actions {
            display: flex;
            gap: 8px;
        }
        
        .btn-action {
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #007aff;
            background: transparent;
            color: #007aff;
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s;
        }
        
        .btn-action:hover {
            background: #007aff;
            color: white;
        }
        
        .btn-action.view-details {
            border-color: #6c757d;
            color: #6c757d;
        }
        
        .btn-action.view-details:hover {
            background: #6c757d;
            color: white;
        }
        
        .loading-message, .no-resources-message {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        
        .loading-message i {
            font-size: 24px;
            margin-bottom: 12px;
            color: #007aff;
        }
        
        .no-resources-message i {
            font-size: 32px;
            margin-bottom: 16px;
            color: #adb5bd;
        }
        
        .subtext {
            font-size: 12px;
            margin-top: 8px;
            color: #adb5bd;
        }
        
        .resource-info-footer {
            margin-top: 16px;
            font-size: 11px;
            color: #6c757d;
            line-height: 1.5;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #007aff;
        }
        
        .resource-info-footer i {
            color: #007aff;
            margin-right: 6px;
        }
    '''
    
    # 找到短视频引流面板的开始位置
    pattern = r'<div class="short-video-panel" id="short-video-panel">'
    match = re.search(pattern, content)
    
    if match:
        print("找到短视频引流面板，准备替换...")
        
        # 找到短视频引流面板的结束位置（查找匹配的闭合div）
        # 简单方法：查找最近的'</div>\n            </div>'模式
        start_pos = match.start()
        
        # 查找'</div>\n            </div>'模式
        end_pattern = r'</div>\s*\n\s*</div>\s*\n\s*</div>\s*\n\s*<div class="panel-content">'
        end_match = re.search(end_pattern, content[start_pos:])
        
        if end_match:
            end_pos = start_pos + end_match.end() - len('</div>\n            </div>\n            </div>\n            <div class="panel-content">')
            
            # 替换内容
            new_content = content[:start_pos] + industry_panel_html + content[end_pos:]
            
            # 在CSS部分添加新样式（在</style>标签前）
            css_pattern = r'</style>'
            css_match = re.search(css_pattern, new_content)
            
            if css_match:
                # 在</style>前插入新CSS
                css_pos = css_match.start()
                new_content = new_content[:css_pos] + new_css + '\n    ' + new_content[css_pos:]
            
            print(f"写入文件: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ 办公室HTML更新完成")
            return True
        else:
            print("❌ 无法找到短视频引流面板的结束位置")
            return False
    else:
        print("❌ 未找到短视频引流面板")
        return False

if __name__ == '__main__':
    input_file = 'outputs/仪表盘/SellAI_办公室_全行业资源版.html'
    output_file = 'outputs/仪表盘/SellAI_办公室_全行业资源版.html'
    
    success = update_office_html(input_file, output_file)
    
    if success:
        print("更新成功")
    else:
        print("更新失败")
        exit(1)