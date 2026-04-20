#!/usr/bin/env python3
"""
创建谈判引擎版办公室HTML
基于全行业资源版HTML，添加谈判面板
"""

import os
import re
from datetime import datetime

def load_template_file():
    """加载全行业资源版HTML作为模板"""
    template_path = "outputs/仪表盘/SellAI_办公室_全行业资源版.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def add_negotiation_css(existing_css):
    """添加谈判面板相关CSS样式"""
    negotiation_css = """
    /* AI商务洽谈面板样式 */
    .negotiation-panel {
        background: #ffffff;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e8e8e8;
    }
    
    .negotiation-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .negotiation-title {
        font-size: 18px;
        font-weight: 600;
        color: #333333;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .negotiation-description {
        font-size: 14px;
        color: #666666;
        margin-top: 4px;
    }
    
    .negotiation-status {
        font-size: 12px;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: 500;
    }
    
    .status-in_progress {
        background-color: #e6f7ff;
        color: #1890ff;
        border: 1px solid #91d5ff;
    }
    
    .status-completed {
        background-color: #f6ffed;
        color: #52c41a;
        border: 1px solid #b7eb8f;
    }
    
    .status-pending {
        background-color: #fff7e6;
        color: #fa8c16;
        border: 1px solid #ffd591;
    }
    
    .negotiation-details {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
    }
    
    .party-info {
        background: #fafafa;
        border-radius: 6px;
        padding: 12px;
        border: 1px solid #f0f0f0;
    }
    
    .party-name {
        font-size: 14px;
        font-weight: 600;
        color: #333333;
        margin-bottom: 4px;
    }
    
    .party-industry {
        font-size: 12px;
        color: #666666;
        margin-bottom: 2px;
    }
    
    .party-type {
        font-size: 11px;
        color: #999999;
        background: #f0f0f0;
        padding: 2px 6px;
        border-radius: 10px;
        display: inline-block;
    }
    
    .negotiation-messages-container {
        background: #fafafa;
        border-radius: 6px;
        padding: 16px;
        height: 300px;
        overflow-y: auto;
        margin-bottom: 16px;
        border: 1px solid #f0f0f0;
    }
    
    .negotiation-message {
        margin-bottom: 12px;
        padding: 10px 14px;
        border-radius: 8px;
        max-width: 80%;
        animation: fadeIn 0.3s ease;
    }
    
    .supplier-message {
        background-color: #e6f7ff;
        border: 1px solid #91d5ff;
        margin-right: auto;
        margin-left: 0;
    }
    
    .demand-message {
        background-color: #f6ffed;
        border: 1px solid #b7eb8f;
        margin-left: auto;
        margin-right: 0;
    }
    
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    
    .message-sender {
        font-size: 12px;
        font-weight: 600;
    }
    
    .supplier-message .message-sender {
        color: #1890ff;
    }
    
    .demand-message .message-sender {
        color: #52c41a;
    }
    
    .message-time {
        font-size: 11px;
        color: #999999;
    }
    
    .message-content {
        font-size: 14px;
        color: #333333;
        line-height: 1.5;
    }
    
    .message-type {
        font-size: 10px;
        color: #999999;
        margin-top: 4px;
        text-align: right;
    }
    
    .current-offer-section {
        background: #fff7e6;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 20px;
        border: 1px solid #ffd591;
    }
    
    .offer-title {
        font-size: 14px;
        font-weight: 600;
        color: #d46b08;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .offer-details {
        font-size: 13px;
    }
    
    .offer-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
        padding-bottom: 6px;
        border-bottom: 1px dashed #ffe7ba;
    }
    
    .offer-key {
        color: #666666;
    }
    
    .offer-value {
        color: #333333;
        font-weight: 500;
    }
    
    .negotiation-controls {
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
    }
    
    .new-negotiation-section {
        background: #f6ffed;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 20px;
        border: 1px solid #b7eb8f;
    }
    
    .form-group {
        margin-bottom: 12px;
    }
    
    .form-label {
        display: block;
        font-size: 12px;
        color: #666666;
        margin-bottom: 4px;
    }
    
    .form-select, .form-input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #d9d9d9;
        border-radius: 4px;
        font-size: 14px;
        color: #333333;
        background: #ffffff;
    }
    
    .form-select:focus, .form-input:focus {
        border-color: #40a9ff;
        outline: none;
        box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
    }
    
    .commission-result {
        background: #f9f0ff;
        border-radius: 6px;
        padding: 16px;
        margin-top: 16px;
        border: 1px solid #d3adf7;
        display: none;
    }
    
    .commission-summary h4 {
        font-size: 16px;
        color: #531dab;
        margin-bottom: 12px;
    }
    
    .commission-breakdown {
        font-size: 14px;
    }
    
    .breakdown-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px dashed #d3adf7;
    }
    
    .breakdown-item.total {
        font-weight: 600;
        color: #531dab;
        border-bottom: 2px solid #531dab;
    }
    
    .breakdown-label {
        color: #666666;
    }
    
    .breakdown-value {
        color: #333333;
        font-weight: 500;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .btn-success {
        background-color: #52c41a;
        color: white;
        border: 1px solid #52c41a;
    }
    
    .btn-success:hover {
        background-color: #73d13d;
        border-color: #73d13d;
    }
    
    .btn-warning {
        background-color: #fa8c16;
        color: white;
        border: 1px solid #fa8c16;
    }
    
    .btn-warning:hover {
        background-color: #ffa940;
        border-color: #ffa940;
    }
    """
    
    # 在现有CSS的末尾添加谈判面板CSS
    # 找到</style>标签的位置，在其前面插入
    style_end_pos = existing_css.find('</style>')
    if style_end_pos != -1:
        return existing_css[:style_end_pos] + negotiation_css + existing_css[style_end_pos:]
    else:
        # 如果没有找到</style>标签，直接在末尾添加
        return existing_css + negotiation_css

def add_negotiation_panel(existing_html):
    """在右侧面板中添加谈判面板"""
    
    negotiation_panel_html = """
                <!-- AI自主商务洽谈面板 -->
                <div class="negotiation-panel" id="negotiation-panel">
                    <div class="negotiation-header">
                        <div>
                            <div class="negotiation-title">
                                <i class="fas fa-handshake"></i>
                                <span id="negotiation-title">AI商务洽谈</span>
                            </div>
                            <div class="negotiation-description" id="negotiation-description">
                                支持AI-to-AI自动谈判，集成永久佣金规则
                            </div>
                        </div>
                        <div class="negotiation-status" id="negotiation-status">
                            待开始
                        </div>
                    </div>
                    
                    <div class="negotiation-details">
                        <div class="party-info" id="party-supplier-info">
                            <div class="party-name">供应商</div>
                            <div class="party-industry">选择供应商开始</div>
                            <div class="party-type">supply</div>
                        </div>
                        <div class="party-info" id="party-demand-info">
                            <div class="party-name">需求方</div>
                            <div class="party-industry">选择需求方开始</div>
                            <div class="party-type">demand</div>
                        </div>
                    </div>
                    
                    <div class="negotiation-controls">
                        <select id="negotiation-history-select" class="form-select" style="flex: 1;">
                            <option value="">选择谈判记录...</option>
                        </select>
                        <button class="btn btn-primary" id="calculate-commission">
                            <i class="fas fa-calculator"></i> 计算佣金
                        </button>
                    </div>
                    
                    <div class="negotiation-messages-container" id="negotiation-messages-container">
                        <div id="negotiation-messages">
                            <div class="negotiation-message supplier-message">
                                <div class="message-header">
                                    <span class="message-sender">供应商</span>
                                    <span class="message-time">--:--</span>
                                </div>
                                <div class="message-content">
                                    欢迎使用AI自主商务洽谈引擎！请选择谈判记录或开始新谈判。
                                </div>
                                <div class="message-type">系统消息</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="current-offer-section">
                        <div class="offer-title">
                            <i class="fas fa-file-contract"></i> 当前报价
                        </div>
                        <div id="current-offer-details">
                            <div class="offer-details">
                                <div class="offer-item">
                                    <span class="offer-key">单位价格:</span>
                                    <span class="offer-value">$0.00</span>
                                </div>
                                <div class="offer-item">
                                    <span class="offer-key">货币:</span>
                                    <span class="offer-value">USD</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="new-negotiation-section">
                        <div class="offer-title">
                            <i class="fas fa-plus-circle"></i> 开始新谈判
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="new-negotiation-scenario">谈判场景:</label>
                            <select id="new-negotiation-scenario" class="form-select">
                                <option value="">选择场景...</option>
                                <option value="price_negotiation">价格协商</option>
                                <option value="cooperation_mode">合作方式</option>
                                <option value="terms_modification">条款修改</option>
                                <option value="delivery_timing">交付时间</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="new-negotiation-supplier">供应商ID:</label>
                            <input type="text" id="new-negotiation-supplier" class="form-input" placeholder="输入供应商ID">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="new-negotiation-demand">需求方ID:</label>
                            <input type="text" id="new-negotiation-demand" class="form-input" placeholder="输入需求方ID">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="negotiation-message-input">谈判消息:</label>
                            <input type="text" id="negotiation-message-input" class="form-input" placeholder="输入消息..." disabled>
                        </div>
                        
                        <div style="display: flex; gap: 10px;">
                            <button class="btn btn-success" id="start-negotiation">
                                <i class="fas fa-play"></i> 开始谈判
                            </button>
                            <button class="btn btn-warning" id="send-negotiation-message" disabled>
                                <i class="fas fa-paper-plane"></i> 发送消息
                            </button>
                        </div>
                    </div>
                    
                    <div class="commission-result" id="commission-result">
                        <!-- 佣金计算结果动态显示 -->
                    </div>
                </div>
    """
    
    # 在全行业资源面板后面添加谈判面板
    # 查找全行业资源面板的结束位置
    industry_panel_end = existing_html.find('<!-- 全行业商业资源库扩展验证报告链接 -->')
    
    if industry_panel_end != -1:
        # 在全行业资源面板后插入谈判面板
        before = existing_html[:industry_panel_end]
        after = existing_html[industry_panel_end:]
        
        # 我们需要确保在右侧面板的适当位置插入
        # 先查找右侧面板中industry-resource-panel的位置
        right_panel_start = existing_html.find('<!-- 右侧面板：匹配推荐、全球成本仪表盘、系统控制 -->')
        if right_panel_start != -1:
            # 在industry-resource-panel的div结束后插入
            industry_panel_div_end = existing_html.find('</div>', industry_panel_end)
            if industry_panel_div_end != -1:
                before = existing_html[:industry_panel_div_end + 6]  # +6 for </div>
                after = existing_html[industry_panel_div_end + 6:]
                
                return before + negotiation_panel_html + after
    
    # 如果找不到插入点，直接在全行业资源面板位置替换
    return existing_html.replace(
        '<!-- 全行业商业资源库扩展验证报告链接 -->',
        negotiation_panel_html + '\n<!-- 全行业商业资源库扩展验证报告链接 -->'
    )

def add_negotiation_script(existing_html):
    """添加谈判面板JavaScript脚本"""
    
    # 创建脚本引用
    script_tag = '\n        <script src="src/negotiation_panel.js"></script>'
    
    # 在Chart.js脚本后面添加
    chartjs_pos = existing_html.find('https://cdn.jsdelivr.net/npm/chart.js')
    if chartjs_pos != -1:
        # 找到</script>标签结束位置
        script_end = existing_html.find('</script>', chartjs_pos)
        if script_end != -1:
            insert_pos = script_end + 9  # +9 for </script>
            return existing_html[:insert_pos] + script_tag + existing_html[insert_pos:]
    
    # 如果找不到，在body结束前添加
    body_end = existing_html.find('</body>')
    if body_end != -1:
        return existing_html[:body_end] + script_tag + existing_html[body_end:]
    
    return existing_html + script_tag

def update_tab_container(existing_html):
    """在中央面板添加谈判选项卡"""
    
    # 查找现有选项卡容器
    tab_container_pattern = r'<div class="tab-container">\s*<div class="tab active" data-tab="chat">聊天</div>\s*<div class="tab" data-tab="workspace">工作台</div>\s*<div class="tab" data-tab="collaboration">协同进度</div>\s*<div class="tab" data-tab="opportunities">商机</div>\s*</div>'
    
    match = re.search(tab_container_pattern, existing_html, re.DOTALL)
    if match:
        # 在商机选项卡后添加谈判选项卡
        updated_tabs = match.group(0).replace(
            '<div class="tab" data-tab="opportunities">商机</div>',
            '<div class="tab" data-tab="opportunities">商机</div>\n                <div class="tab" data-tab="negotiation">商务洽谈</div>'
        )
        
        # 替换原来的选项卡容器
        return existing_html[:match.start()] + updated_tabs + existing_html[match.end():]
    
    return existing_html

def add_negotiation_tab_content(existing_html):
    """添加谈判选项卡内容"""
    
    negotiation_tab_content = """
            <div id="negotiation-tab" class="tab-content">
                <div class="panel-title" style="margin-bottom: 20px;">AI自主商务洽谈中心</div>
                
                <div class="negotiation-center">
                    <div class="negotiation-intro">
                        <h3><i class="fas fa-robot"></i> AI-to-AI自动谈判系统</h3>
                        <p>本系统支持AI分身之间的自动商务谈判，包括价格协商、条款修改、合作方式确定等场景。</p>
                        
                        <div class="feature-grid">
                            <div class="feature-card">
                                <div class="feature-icon">
                                    <i class="fas fa-comments-dollar"></i>
                                </div>
                                <div class="feature-title">智能报价</div>
                                <div class="feature-desc">基于市场行情自动生成合理报价</div>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">
                                    <i class="fas fa-balance-scale"></i>
                                </div>
                                <div class="feature-title">条款协商</div>
                                <div class="feature-desc">自动协商付款条件、交付时间等</div>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">
                                    <i class="fas fa-handshake"></i>
                                </div>
                                <div class="feature-title">合作模式</div>
                                <div class="feature-desc">确定独家/非独家合作方式</div>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">
                                    <i class="fas fa-percentage"></i>
                                </div>
                                <div class="feature-title">佣金计算</div>
                                <div class="feature-desc">自动计算永久统一佣金规则</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="negotiation-quick-actions">
                        <h4>快速开始</h4>
                        <div class="action-buttons">
                            <button class="btn btn-primary" id="quick-start-price-negotiation">
                                <i class="fas fa-tags"></i> 开始价格谈判
                            </button>
                            <button class="btn btn-primary" id="quick-start-cooperation">
                                <i class="fas fa-users"></i> 合作方式协商
                            </button>
                            <button class="btn btn-primary" id="quick-review-history">
                                <i class="fas fa-history"></i> 查看历史谈判
                            </button>
                        </div>
                    </div>
                    
                    <div class="negotiation-stats">
                        <h4>谈判统计</h4>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value" id="total-negotiations">0</div>
                                <div class="stat-label">总谈判数</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="success-rate">0%</div>
                                <div class="stat-label">成功率</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="avg-duration">0h</div>
                                <div class="stat-label">平均时长</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="total-commission">$0</div>
                                <div class="stat-label">总佣金</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
    """
    
    # 在商机选项卡内容后添加
    opportunities_tab_end = existing_html.find('</div>', existing_html.find('id="opportunities-tab"'))
    
    if opportunities_tab_end != -1:
        insert_pos = opportunities_tab_end + 6  # +6 for </div>
        return existing_html[:insert_pos] + negotiation_tab_content + existing_html[insert_pos:]
    
    return existing_html

def create_negotiation_office():
    """创建谈判引擎版办公室HTML"""
    
    print("创建谈判引擎版办公室HTML...")
    
    # 加载模板
    html = load_template_file()
    
    print("  添加谈判面板CSS样式...")
    # 添加CSS样式
    html = add_negotiation_css(html)
    
    print("  添加谈判面板HTML结构...")
    # 添加谈判面板
    html = add_negotiation_panel(html)
    
    print("  更新选项卡容器...")
    # 更新选项卡
    html = update_tab_container(html)
    html = add_negotiation_tab_content(html)
    
    print("  添加JavaScript脚本...")
    # 添加脚本
    html = add_negotiation_script(html)
    
    # 更新标题
    html = html.replace(
        'SellAI 办公室 升级版 - 全球赚钱AI合伙人',
        'SellAI 办公室 谈判引擎版 - AI自主商务洽谈中心'
    )
    
    # 保存文件
    output_path = "outputs/仪表盘/SellAI_办公室_谈判引擎版.html"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  文件已保存: {output_path}")
    print("创建完成!")
    
    return output_path

if __name__ == "__main__":
    create_negotiation_office()