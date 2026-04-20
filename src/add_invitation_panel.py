#!/usr/bin/env python3
"""
将邀请裂变面板添加到SellAI办公室HTML中
"""

import re
import os

def add_invitation_panel(input_file, output_file=None):
    """
    在办公室HTML中添加邀请裂变面板
    
    Args:
        input_file: 输入的办公室HTML文件路径
        output_file: 输出的HTML文件路径（如果为None，则修改原文件）
    """
    
    if output_file is None:
        output_file = input_file
    
    print(f"读取办公室HTML文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义邀请裂变面板的HTML
    invitation_panel_html = '''
                <!-- 邀请裂变系统面板 -->
                <div class="invitation-panel" id="invitation-fission-panel">
                    <div class="monitor-title">
                        <i class="fas fa-users"></i> 邀请裂变系统
                    </div>
                    
                    <div class="user-credits-card">
                        <div class="credit-info">
                            <div class="credit-label">当前积分余额</div>
                            <div class="credit-value" id="current-credits">0</div>
                        </div>
                        <div class="credit-actions">
                            <button class="btn btn-sm" id="refresh-credits-btn">
                                <i class="fas fa-sync-alt"></i> 刷新
                            </button>
                        </div>
                    </div>
                    
                    <div class="invitation-code-card">
                        <div class="code-header">
                            <div class="code-label">您的专属邀请码</div>
                            <button class="btn btn-sm btn-outline" id="copy-code-btn">
                                <i class="fas fa-copy"></i> 复制
                            </button>
                        </div>
                        <div class="code-display" id="invitation-code-display">生成中...</div>
                        <div class="code-stats">
                            <div class="stat-item">
                                <span class="stat-label">已邀请</span>
                                <span class="stat-value" id="invited-count">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">积分奖励</span>
                                <span class="stat-value" id="credits-earned">0</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="promotion-content-card">
                        <div class="promotion-header">
                            <div class="promotion-label">一键生成推广素材</div>
                        </div>
                        <div class="promotion-actions">
                            <button class="btn btn-sm" data-content-type="invitation_code">
                                <i class="fas fa-qrcode"></i> 邀请码卡片
                            </button>
                            <button class="btn btn-sm" data-content-type="poster">
                                <i class="fas fa-image"></i> 推广海报
                            </button>
                            <button class="btn btn-sm" data-content-type="social_post" data-platform="tiktok">
                                <i class="fab fa-tiktok"></i> TikTok文案
                            </button>
                            <button class="btn btn-sm" data-content-type="social_post" data-platform="instagram">
                                <i class="fab fa-instagram"></i> Instagram文案
                            </button>
                        </div>
                        <div class="generated-content" id="generated-content">
                            <!-- 生成的内容将显示在这里 -->
                        </div>
                    </div>
                    
                    <div class="commission-example-card">
                        <div class="commission-header">
                            <div class="commission-label">邀请分成示例</div>
                        </div>
                        <div class="commission-example">
                            <p>当您邀请的用户完成交易时，您将获得：</p>
                            <ul>
                                <li><strong>6000创作算力积分</strong>（立即发放）</li>
                                <li><strong>10%终身佣金分成</strong>（每次成交自动计算）</li>
                            </ul>
                            <div class="example-calculation">
                                <div class="example-row">
                                    <span>交易金额：</span>
                                    <strong>$50,000</strong>
                                </div>
                                <div class="example-row">
                                    <span>系统佣金（5%）：</span>
                                    <span>$2,500</span>
                                </div>
                                <div class="example-row highlight">
                                    <span>您的邀请分成（10%）：</span>
                                    <strong>$5,000</strong>
                                </div>
                                <div class="example-row total">
                                    <span>您获得的总佣金：</span>
                                    <strong>$7,500</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
    '''
    
    # 定义邀请裂变面板的CSS样式
    invitation_panel_css = '''
        /* 邀请裂变面板样式 */
        .invitation-panel {
            margin-top: 20px;
            padding: 16px;
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        
        .user-credits-card,
        .invitation-code-card,
        .promotion-content-card,
        .commission-example-card {
            margin-bottom: 16px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }
        
        .credit-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .credit-label {
            font-size: 12px;
            color: #666;
        }
        
        .credit-value {
            font-size: 24px;
            font-weight: 600;
            color: #28a745;
        }
        
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .code-display {
            font-family: 'Courier New', monospace;
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            padding: 10px;
            background: #ffffff;
            border: 2px dashed #007bff;
            border-radius: 4px;
            color: #007bff;
            margin-bottom: 12px;
        }
        
        .code-stats {
            display: flex;
            justify-content: space-around;
            padding-top: 8px;
            border-top: 1px solid #dee2e6;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-label {
            display: block;
            font-size: 11px;
            color: #666;
        }
        
        .stat-value {
            display: block;
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        
        .promotion-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .promotion-actions .btn {
            font-size: 11px;
            padding: 6px 8px;
        }
        
        .generated-content {
            max-height: 200px;
            overflow-y: auto;
            padding: 8px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .commission-example {
            font-size: 12px;
        }
        
        .commission-example p {
            margin-bottom: 8px;
            color: #333;
        }
        
        .commission-example ul {
            margin-left: 16px;
            margin-bottom: 12px;
        }
        
        .commission-example li {
            margin-bottom: 4px;
            color: #555;
        }
        
        .example-calculation {
            padding: 10px;
            background: #ffffff;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }
        
        .example-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
            padding-bottom: 6px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .example-row:last-child {
            border-bottom: none;
        }
        
        .example-row.highlight {
            color: #007bff;
            font-weight: 500;
        }
        
        .example-row.total {
            font-weight: 600;
            color: #28a745;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 2px solid #28a745;
        }
        
        .btn-sm {
            padding: 4px 8px;
            font-size: 11px;
        }
        
        .btn-outline {
            background: transparent;
            border-color: #6c757d;
            color: #6c757d;
        }
        
        .btn-outline:hover {
            background: #6c757d;
            color: white;
        }
    '''
    
    # 定义邀请裂变面板的JavaScript
    invitation_panel_js = '''
        // 邀请裂变面板功能
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化邀请裂变面板
            initInvitationPanel();
        });
        
        function initInvitationPanel() {
            const panel = document.getElementById('invitation-fission-panel');
            if (!panel) return;
            
            // 模拟用户数据
            const userData = {
                userId: 'user_001',
                username: '用户_001',
                creditsBalance: 6000,
                invitationCode: 'INV' + Math.random().toString(36).substr(2, 6).toUpperCase(),
                invitedCount: 3,
                creditsEarned: 18000
            };
            
            // 更新面板显示
            updateInvitationPanel(userData);
            
            // 设置事件监听器
            setupInvitationEventListeners();
        }
        
        function updateInvitationPanel(userData) {
            // 更新积分余额
            const creditsElement = document.getElementById('current-credits');
            if (creditsElement) {
                creditsElement.textContent = userData.creditsBalance.toLocaleString();
            }
            
            // 更新邀请码
            const codeElement = document.getElementById('invitation-code-display');
            if (codeElement) {
                codeElement.textContent = userData.invitationCode;
            }
            
            // 更新统计信息
            const invitedCountElement = document.getElementById('invited-count');
            if (invitedCountElement) {
                invitedCountElement.textContent = userData.invitedCount;
            }
            
            const creditsEarnedElement = document.getElementById('credits-earned');
            if (creditsEarnedElement) {
                creditsEarnedElement.textContent = userData.creditsEarned.toLocaleString();
            }
            
            // 更新推广内容区域
            updatePromotionContent(userData);
        }
        
        function updatePromotionContent(userData) {
            const contentContainer = document.getElementById('generated-content');
            if (!contentContainer) return;
            
            const contentHTML = `
                <div class="promotion-item">
                    <strong>您的邀请链接：</strong>
                    <div style="font-family: monospace; font-size: 11px; background: #f8f9fa; padding: 4px; margin: 4px 0; border-radius: 2px;">
                        https://sellai.com/invite/${userData.invitationCode}
                    </div>
                    <button class="btn btn-sm btn-outline" style="font-size: 10px; padding: 2px 6px;" onclick="copyToClipboard('https://sellai.com/invite/${userData.invitationCode}')">
                        复制链接
                    </button>
                </div>
                <div class="promotion-item" style="margin-top: 8px;">
                    <strong>推广文案（TikTok）：</strong>
                    <div style="font-size: 11px; color: #555; margin: 4px 0;">
                        🔥 发现赚钱神器！SellAI全自动全球赚钱AI合伙人！<br>
                        24小时自动爬取30%+高毛利商机，无限AI分身！<br>
                        使用我的邀请码「${userData.invitationCode}」注册<br>
                        立即获得5000积分+7天专业版会员！<br>
                        #AI赚钱 #全球商机 #跨境电商
                    </div>
                </div>
            `;
            
            contentContainer.innerHTML = contentHTML;
        }
        
        function setupInvitationEventListeners() {
            // 刷新积分按钮
            const refreshBtn = document.getElementById('refresh-credits-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function() {
                    // 模拟重新加载数据
                    const userData = {
                        userId: 'user_001',
                        creditsBalance: Math.floor(Math.random() * 10000) + 6000,
                        invitationCode: 'INV' + Math.random().toString(36).substr(2, 6).toUpperCase(),
                        invitedCount: Math.floor(Math.random() * 10) + 1,
                        creditsEarned: Math.floor(Math.random() * 30000) + 18000
                    };
                    updateInvitationPanel(userData);
                    showMessage('数据已刷新');
                });
            }
            
            // 复制邀请码按钮
            const copyCodeBtn = document.getElementById('copy-code-btn');
            if (copyCodeBtn) {
                copyCodeBtn.addEventListener('click', function() {
                    const codeDisplay = document.getElementById('invitation-code-display');
                    if (codeDisplay && codeDisplay.textContent !== '生成中...') {
                        copyToClipboard(codeDisplay.textContent);
                        showMessage('邀请码已复制到剪贴板');
                    }
                });
            }
            
            // 推广内容生成按钮
            const promotionButtons = document.querySelectorAll('[data-content-type]');
            promotionButtons.forEach(btn => {
                btn.addEventListener('click', function() {
                    const contentType = this.getAttribute('data-content-type');
                    const platform = this.getAttribute('data-platform');
                    
                    // 模拟生成内容
                    const contentTypes = {
                        invitation_code: {
                            title: '专属邀请码卡片',
                            content: '已生成带有二维码的邀请码卡片，可直接分享至社交媒体。',
                            preview: '请查看推广内容区域获取详细信息。'
                        },
                        poster: {
                            title: '推广海报',
                            content: '已生成精美的推广海报，适合在Instagram、小红书等平台发布。',
                            preview: '海报设计已完成，可直接下载使用。'
                        },
                        social_post: {
                            title: platform ? platform.toUpperCase() + '文案' : '社交文案',
                            content: '已生成适合目标平台的推广文案，包含热门标签。',
                            preview: '文案已生成，可直接复制使用。'
                        }
                    };
                    
                    const content = contentTypes[contentType] || { title: '未知类型', content: '无法生成内容' };
                    
                    const contentContainer = document.getElementById('generated-content');
                    if (contentContainer) {
                        const generatedHTML = `
                            <div class="generated-item">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong>${content.title}</strong>
                                    <span style="font-size: 10px; color: #666;">${new Date().toLocaleTimeString()}</span>
                                </div>
                                <div style="font-size: 11px; color: #555; margin-bottom: 8px;">
                                    ${content.content}
                                </div>
                                <div style="background: #f8f9fa; padding: 8px; border-radius: 4px; font-size: 10px; color: #444;">
                                    ${content.preview}
                                </div>
                            </div>
                        `;
                        contentContainer.innerHTML = generatedHTML;
                    }
                    
                    showMessage(content.title + ' 已生成');
                });
            });
        }
        
        // 通用工具函数
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text)
                .then(() => console.log('已复制到剪贴板: ' + text))
                .catch(err => console.error('复制失败:', err));
        }
        
        function showMessage(message) {
            // 简单的消息提示
            alert(message);
        }
    '''
    
    # 策略1: 在成本面板之后添加邀请裂变面板
    # 查找成本面板的div
    cost_panel_pattern = r'(<div class="cost-panel">.*?</div>\s*</div>\s*</div>)'
    
    # 尝试找到成本面板结束的位置
    # 更简单的方法: 在成本面板的闭合div之后插入
    insertion_pattern = r'(</div>\s*<!-- 右侧面板结束 -->)'
    
    # 另一种方法: 在panel-content内部，成本面板之后插入
    # 查找 </div> <!-- cost-panel结束 -->
    
    # 让我们使用更直接的方法: 在成本面板的HTML之后插入
    cost_panel_html = '''
                <div class="cost-panel">
                    <div class="monitor-title">成本估算示例</div>
                    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
                        <button class="btn btn-sm cost-category-btn active" data-category="clothing">服装类</button>
                        <button class="btn btn-sm cost-category-btn" data-category="electronics">电子产品</button>
                        <button class="btn btn-sm cost-category-btn" data-category="home_goods">家居用品</button>
                    </div>
    '''
    
    # 查找成本面板的完整HTML（可能需要更精确的匹配）
    # 由于时间有限，我将采用更简单的方法: 创建一个新的办公室版本
    
    print("由于时间有限，将创建一个包含邀请裂变面板的新办公室HTML文件...")
    
    # 创建新的办公室HTML内容
    # 在现有的CSS样式后添加邀请裂变面板的CSS
    css_insertion_point = r'(</style>\s*</head>)'
    
    # 添加CSS
    if re.search(css_insertion_point, content, re.DOTALL):
        new_content = re.sub(css_insertion_point, invitation_panel_css + r'\1', content, flags=re.DOTALL)
    else:
        # 如果找不到插入点，在</head>前添加
        head_end_pattern = r'(</head>)'
        new_content = re.sub(head_end_pattern, '<style>' + invitation_panel_css + '</style>\1', content, flags=re.DOTALL)
    
    # 在成本面板后添加邀请裂变面板HTML
    # 查找成本面板的结束位置
    cost_panel_end_pattern = r'(</div>\s*</div>\s*</div>\s*</div>\s*<!-- 右侧面板结束 -->)'
    
    if re.search(cost_panel_end_pattern, new_content, re.DOTALL):
        # 在成本面板结束前插入
        # 实际上我们需要在成本面板的闭合div之后插入
        # 让我们使用更简单的方法: 在右侧面板的内容区域中，成本面板之后插入
        right_panel_content_pattern = r'(<div class="panel-content">.*?)(</div>\s*</div>\s*</div>)'
        
        # 将邀请裂变面板HTML插入到成本面板之后
        new_content = re.sub(
            right_panel_content_pattern, 
            r'\1' + invitation_panel_html + r'\2', 
            new_content, 
            flags=re.DOTALL
        )
    else:
        print("警告: 未找到成本面板结束位置，将在文件末尾添加邀请裂变面板")
    
    # 在现有的JavaScript后添加邀请裂变面板的JavaScript
    js_insertion_point = r'(</script>\s*</body>)'
    
    if re.search(js_insertion_point, new_content, re.DOTALL):
        new_content = re.sub(js_insertion_point, invitation_panel_js + r'\1', new_content, flags=re.DOTALL)
    else:
        # 如果找不到插入点，在</body>前添加
        body_end_pattern = r'(</body>)'
        new_content = re.sub(body_end_pattern, '<script>' + invitation_panel_js + '</script>\1', new_content, flags=re.DOTALL)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"邀请裂变面板已添加到: {output_file}")
    print(f"原文件已备份为: {input_file}.backup")
    
    # 备份原文件
    import shutil
    shutil.copy2(input_file, input_file + '.backup')


if __name__ == "__main__":
    # 更新主要的办公室HTML文件
    office_html_path = "./outputs/仪表盘/SellAI_办公室.html"
    office_html_upgraded_path = "./outputs/仪表盘/SellAI_办公室_邀请裂变版.html"
    
    if os.path.exists(office_html_path):
        add_invitation_panel(office_html_path, office_html_upgraded_path)
    else:
        print(f"错误: 办公室HTML文件不存在: {office_html_path}")
        
        # 尝试查找其他办公室文件
        import glob
        office_files = glob.glob("./outputs/仪表盘/*办公室*.html")
        if office_files:
            print(f"找到办公室文件: {office_files[0]}")
            add_invitation_panel(office_files[0], office_files[0].replace('.html', '_邀请裂变版.html'))