#!/usr/bin/env python3
"""
更新办公室HTML，添加Buddy系统交互面板
"""

import re

def update_office_buddy(input_file, output_file):
    """
    更新办公室HTML，在监控面板后添加Buddy系统交互面板
    
    Args:
        input_file: 输入HTML文件路径
        output_file: 输出HTML文件路径
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找监控面板的结束位置
    # 监控面板结束后是成本估算面板
    monitor_end_pattern = r'(\s*</div>\s*\n\s*</div>\s*\n\s*<div class="cost-panel">)'
    
    # Buddy交互面板HTML
    buddy_panel = '''
                </div>
                
                <div class="buddy-panel">
                    <div class="panel-title" style="font-size: 14px; margin-bottom: 12px;">Buddy智能伙伴</div>
                    
                    <div class="buddy-status">
                        <div class="buddy-status-item">
                            <span class="buddy-status-label">服务状态:</span>
                            <span class="buddy-status-value status-success" id="buddy-service-status">运行中</span>
                        </div>
                        <div class="buddy-status-item">
                            <span class="buddy-status-label">用户情绪:</span>
                            <span class="buddy-status-value" id="buddy-user-mood">专注</span>
                        </div>
                        <div class="buddy-status-item">
                            <span class="buddy-status-label">今日交互:</span>
                            <span class="buddy-status-value" id="buddy-today-interactions">5</span>
                        </div>
                        <div class="buddy-status-item">
                            <span class="buddy-status-label">最后活动:</span>
                            <span class="buddy-status-value" id="buddy-last-active">刚刚</span>
                        </div>
                    </div>
                    
                    <div class="buddy-interaction">
                        <div class="buddy-message" id="buddy-current-message">
                            <div class="message-content">
                                <div class="message-sender">Buddy伙伴</div>
                                <div class="message-text" id="buddy-message-text">今天的工作进展如何？有什么我可以帮忙的吗？</div>
                                <div class="message-time" id="buddy-message-time">10:25</div>
                            </div>
                        </div>
                        
                        <div class="buddy-response">
                            <div class="response-title" id="buddy-response-title">你的回应：</div>
                            <textarea class="response-input" id="buddy-response-input" 
                                      placeholder="请输入你的回应..." rows="2"></textarea>
                            <div class="response-actions">
                                <div class="mood-selection">
                                    <span class="mood-label">当前情绪:</span>
                                    <div class="mood-buttons">
                                        <button class="mood-btn mood-happy" data-mood="happy" title="快乐">😊</button>
                                        <button class="mood-btn mood-neutral" data-mood="neutral" title="中性">😐</button>
                                        <button class="mood-btn mood-stressed" data-mood="stressed" title="压力">😫</button>
                                        <button class="mood-btn mood-tired" data-mood="tired" title="疲劳">😴</button>
                                        <button class="mood-btn mood-focused" data-mood="focused" title="专注">🎯</button>
                                        <button class="mood-btn mood-creative" data-mood="creative" title="创造">✨</button>
                                    </div>
                                </div>
                                <div class="action-buttons">
                                    <button class="btn btn-sm" id="buddy-skip-btn">跳过</button>
                                    <button class="btn btn-sm btn-primary" id="buddy-send-btn">发送回应</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="buddy-suggestions">
                            <div class="suggestions-title">今日建议</div>
                            <div class="suggestion-list" id="buddy-suggestion-list">
                                <div class="suggestion-item">
                                    <div class="suggestion-icon">💡</div>
                                    <div class="suggestion-content">
                                        <div class="suggestion-title">番茄工作法</div>
                                        <div class="suggestion-desc">专注工作25分钟，休息5分钟，提高效率</div>
                                    </div>
                                </div>
                                <div class="suggestion-item">
                                    <div class="suggestion-icon">💧</div>
                                    <div class="suggestion-content">
                                        <div class="suggestion-title">保持水分</div>
                                        <div class="suggestion-desc">记得每小时喝一杯水，保持精力充沛</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="buddy-controls">
                        <div class="control-title">Buddy设置</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 12px;">启用交互</span>
                            <label class="switch">
                                <input type="checkbox" id="buddy-enable-switch" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 12px;">情感识别</span>
                            <label class="switch">
                                <input type="checkbox" id="buddy-emotion-switch" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px;">个性化建议</span>
                            <label class="switch">
                                <input type="checkbox" id="buddy-suggestion-switch" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
    '''
    
    # 替换模式
    if re.search(monitor_end_pattern, content):
        # 替换监控面板结束标签，插入Buddy面板
        new_content = re.sub(
            monitor_end_pattern, 
            buddy_panel + r'\1',  # 在监控面板结束后插入Buddy面板，然后保留原来的成本面板
            content,
            flags=re.DOTALL
        )
        
        # 添加CSS样式
        css_styles = '''
        /* Buddy系统样式 */
        .buddy-panel {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .buddy-status {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 16px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        
        .buddy-status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
        }
        
        .buddy-status-label {
            color: #666;
        }
        
        .buddy-status-value {
            font-weight: 500;
        }
        
        .buddy-interaction {
            margin-bottom: 16px;
        }
        
        .buddy-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            color: white;
        }
        
        .message-content {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .message-sender {
            font-size: 10px;
            opacity: 0.8;
        }
        
        .message-text {
            font-size: 13px;
            margin: 4px 0;
        }
        
        .message-time {
            font-size: 10px;
            opacity: 0.8;
            text-align: right;
        }
        
        .buddy-response {
            margin-bottom: 12px;
        }
        
        .response-title {
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .response-input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
            resize: vertical;
            margin-bottom: 8px;
        }
        
        .response-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .response-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .mood-selection {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 8px;
        }
        
        .mood-label {
            font-size: 11px;
            color: #666;
            margin-bottom: 2px;
        }
        
        .mood-buttons {
            display: flex;
            gap: 4px;
            justify-content: space-between;
        }
        
        .mood-btn {
            flex: 1;
            padding: 6px 4px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 14px;
            text-align: center;
            transition: all 0.2s;
        }
        
        .mood-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .mood-btn.active {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.1);
        }
        
        .action-buttons {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }
        
        .buddy-suggestions {
            margin-top: 16px;
            padding: 12px;
            background: #f0f7ff;
            border-radius: 6px;
        }
        
        .suggestions-title {
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 8px;
            color: #667eea;
        }
        
        .suggestion-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .suggestion-item {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            padding: 8px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e3e8f0;
        }
        
        .suggestion-icon {
            font-size: 16px;
        }
        
        .suggestion-content {
            flex: 1;
        }
        
        .suggestion-title {
            font-size: 11px;
            font-weight: 500;
            margin-bottom: 2px;
        }
        
        .suggestion-desc {
            font-size: 10px;
            color: #666;
        }
        
        .buddy-controls {
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        '''
        
        # 将CSS样式插入到head标签中
        head_end_pattern = r'(</head>)'
        if re.search(head_end_pattern, new_content):
            new_content = re.sub(
                head_end_pattern,
                '<style>' + css_styles + '</style>' + r'\1',
                new_content
            )
        
        # 添加JavaScript功能
        js_code = '''
        // Buddy系统交互功能
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化Buddy面板
            initBuddySystem();
            
            // Buddy系统状态变量
            const buddyState = {
                enabled: true,
                emotionRecognition: true,
                suggestionsEnabled: true,
                userMood: 'focused',
                lastActive: new Date(),
                todayInteractions: 5,
                currentMessage: {
                    text: '今天的工作进展如何？有什么我可以帮忙的吗？',
                    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'})
                }
            };
            
            // 初始化Buddy系统
            function initBuddySystem() {
                // 更新显示状态
                updateBuddyDisplay();
                
                // 绑定事件
                bindBuddyEvents();
                
                console.log('Buddy系统初始化完成');
            }
            
            // 更新Buddy显示
            function updateBuddyDisplay() {
                // 更新服务状态
                document.getElementById('buddy-service-status').textContent = 
                    buddyState.enabled ? '运行中' : '已暂停';
                
                // 更新用户情绪
                document.getElementById('buddy-user-mood').textContent = 
                    getMoodDisplayName(buddyState.userMood);
                
                // 更新今日交互数
                document.getElementById('buddy-today-interactions').textContent = 
                    buddyState.todayInteractions;
                
                // 更新最后活动时间
                document.getElementById('buddy-last-active').textContent = 
                    formatLastActive(buddyState.lastActive);
                
                // 更新当前消息
                document.getElementById('buddy-message-text').textContent = 
                    buddyState.currentMessage.text;
                document.getElementById('buddy-message-time').textContent = 
                    buddyState.currentMessage.time;
            }
            
            // 获取情绪显示名称
            function getMoodDisplayName(mood) {
                const moodNames = {
                    'happy': '快乐',
                    'neutral': '中性',
                    'stressed': '压力',
                    'tired': '疲劳',
                    'focused': '专注',
                    'creative': '创造',
                    'unknown': '未知'
                };
                return moodNames[mood] || '未知';
            }
            
            // 格式化最后活动时间
            function formatLastActive(lastActive) {
                const now = new Date();
                const diffMs = now - lastActive;
                const diffMinutes = Math.floor(diffMs / (1000 * 60));
                
                if (diffMinutes < 1) return '刚刚';
                if (diffMinutes < 60) return diffMinutes + '分钟前';
                
                const diffHours = Math.floor(diffMinutes / 60);
                if (diffHours < 24) return diffHours + '小时前';
                
                const diffDays = Math.floor(diffHours / 24);
                return diffDays + '天前';
            }
            
            // 绑定Buddy事件
            function bindBuddyEvents() {
                // 启用/禁用开关
                const enableSwitch = document.getElementById('buddy-enable-switch');
                if (enableSwitch) {
                    enableSwitch.checked = buddyState.enabled;
                    enableSwitch.addEventListener('change', function(e) {
                        buddyState.enabled = e.target.checked;
                        updateBuddyDisplay();
                        
                        if (buddyState.enabled) {
                            console.log('Buddy交互已启用');
                            showBuddyMessage('交互已重新启用！欢迎回来。');
                        } else {
                            console.log('Buddy交互已禁用');
                        }
                    });
                }
                
                // 情感识别开关
                const emotionSwitch = document.getElementById('buddy-emotion-switch');
                if (emotionSwitch) {
                    emotionSwitch.checked = buddyState.emotionRecognition;
                    emotionSwitch.addEventListener('change', function(e) {
                        buddyState.emotionRecognition = e.target.checked;
                        console.log('情感识别：' + (buddyState.emotionRecognition ? '启用' : '禁用'));
                    });
                }
                
                // 个性化建议开关
                const suggestionSwitch = document.getElementById('buddy-suggestion-switch');
                if (suggestionSwitch) {
                    suggestionSwitch.checked = buddyState.suggestionsEnabled;
                    suggestionSwitch.addEventListener('change', function(e) {
                        buddyState.suggestionsEnabled = e.target.checked;
                        console.log('个性化建议：' + (buddyState.suggestionsEnabled ? '启用' : '禁用'));
                    });
                }
                
                // 情绪按钮
                const moodButtons = document.querySelectorAll('.mood-btn');
                moodButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        const mood = this.getAttribute('data-mood');
                        
                        // 移除所有按钮的active类
                        moodButtons.forEach(btn => btn.classList.remove('active'));
                        // 为当前按钮添加active类
                        this.classList.add('active');
                        
                        buddyState.userMood = mood;
                        updateBuddyDisplay();
                        
                        console.log('用户情绪更新为：' + mood);
                    });
                });
                
                // 发送回应按钮
                const sendBtn = document.getElementById('buddy-send-btn');
                if (sendBtn) {
                    sendBtn.addEventListener('click', function() {
                        const responseInput = document.getElementById('buddy-response-input');
                        const responseText = responseInput.value.trim();
                        
                        if (!responseText) {
                            alert('请输入回应内容');
                            return;
                        }
                        
                        // 处理用户回应
                        processBuddyResponse(responseText);
                        
                        // 清空输入框
                        responseInput.value = '';
                        
                        // 显示确认消息
                        alert('回应已发送！Buddy会记住你的反馈。');
                    });
                }
                
                // 跳过按钮
                const skipBtn = document.getElementById('buddy-skip-btn');
                if (skipBtn) {
                    skipBtn.addEventListener('click', function() {
                        console.log('当前Buddy交互已跳过');
                        showBuddyMessage('好的，如果你有其他需要，随时告诉我。');
                    });
                }
                
                // 响应输入框键盘事件
                const responseInput = document.getElementById('buddy-response-input');
                if (responseInput) {
                    responseInput.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' && e.ctrlKey) {
                            e.preventDefault();
                            document.getElementById('buddy-send-btn').click();
                        }
                    });
                }
            }
            
            // 处理Buddy回应
            function processBuddyResponse(responseText) {
                // 更新交互计数
                buddyState.todayInteractions++;
                
                // 更新最后活动时间
                buddyState.lastActive = new Date();
                
                // 根据回应内容更新情绪状态（简化版）
                const positiveWords = ['好', '不错', '很棒', '开心', '顺利'];
                const negativeWords = ['不好', '困难', '压力', '累', '问题'];
                
                let detectedMood = buddyState.userMood;
                
                for (const word of positiveWords) {
                    if (responseText.includes(word)) {
                        detectedMood = 'happy';
                        break;
                    }
                }
                
                if (detectedMood === buddyState.userMood) {
                    for (const word of negativeWords) {
                        if (responseText.includes(word)) {
                            detectedMood = 'stressed';
                            break;
                        }
                    }
                }
                
                buddyState.userMood = detectedMood;
                
                // 生成新消息（简化版）
                const messages = [
                    '谢谢分享！我会根据你的反馈提供更合适的建议。',
                    '明白了，我会记住你的感受，并提供更适合的帮助。',
                    '收到你的回应，我会调整我的建议来更好地支持你。',
                    '感谢反馈！我一直在学习如何更好地为你服务。'
                ];
                
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                buddyState.currentMessage = {
                    text: randomMessage,
                    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'})
                };
                
                // 更新显示
                updateBuddyDisplay();
                
                console.log('Buddy回应处理完成：', {
                    response: responseText,
                    newMood: buddyState.userMood,
                    newMessage: buddyState.currentMessage
                });
            }
            
            // 显示Buddy消息
            function showBuddyMessage(message) {
                buddyState.currentMessage = {
                    text: message,
                    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'})
                };
                updateBuddyDisplay();
            }
            
            // 模拟定期Buddy交互
            setInterval(() => {
                if (buddyState.enabled) {
                    // 更新最后活动时间
                    buddyState.lastActive = new Date();
                    
                    // 定期生成新消息（根据时间和用户状态）
                    const hour = new Date().getHours();
                    const messages = getMessagesByHour(hour, buddyState.userMood);
                    
                    if (messages.length > 0) {
                        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                        buddyState.currentMessage = {
                            text: randomMessage,
                            time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'})
                        };
                        updateBuddyDisplay();
                    }
                }
            }, 5 * 60 * 1000); // 每5分钟更新一次
            
            // 根据小时和情绪获取消息
            function getMessagesByHour(hour, mood) {
                const messages = [];
                
                if (hour >= 6 && hour < 9) {
                    // 早晨
                    messages.push('早上好！今天有什么计划吗？');
                    messages.push('新的一天开始了，准备好迎接挑战了吗？');
                } else if (hour >= 9 && hour < 12) {
                    // 上午
                    messages.push('上午的工作进展如何？需要我帮忙整理思路吗？');
                    messages.push('要不要试试番茄工作法来提高上午的效率？');
                } else if (hour >= 12 && hour < 14) {
                    // 中午
                    messages.push('午餐时间到了，记得好好吃饭休息一下。');
                    messages.push('建议中午短暂休息15-20分钟，下午更有精神。');
                } else if (hour >= 14 && hour < 17) {
                    // 下午
                    messages.push('下午容易犯困，起来走动一下会好很多。');
                    messages.push('需要我为你推荐一些下午提神的方法吗？');
                } else if (hour >= 17 && hour < 19) {
                    // 傍晚
                    messages.push('今天辛苦了！总结一下今天的收获吧。');
                    messages.push('工作接近尾声，记得整理今天的成果。');
                } else if (hour >= 19 && hour < 22) {
                    // 晚上
                    messages.push('晚上是学习和放松的好时间。');
                    messages.push('记得合理安排晚上的时间，保持工作生活平衡。');
                }
                
                return messages;
            }
            
            // 初始化完成后，立即开始第一次交互
            setTimeout(() => {
                if (buddyState.enabled) {
                    showBuddyMessage('欢迎来到SellAI办公室！我是你的Buddy伙伴，会随时关注你的状态并提供帮助。');
                }
            }, 2000);
        });
        '''
        
        # 将JavaScript代码插入到现有JavaScript代码之前
        body_end_pattern = r'(\s*</script>\s*\n\s*</body>)'
        if re.search(body_end_pattern, new_content):
            new_content = re.sub(
                body_end_pattern,
                js_code + r'\1',
                new_content
            )
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 办公室HTML更新完成，Buddy面板已添加")
        print(f"   输入文件: {input_file}")
        print(f"   输出文件: {output_file}")
        
        return True
    else:
        print("❌ 未找到监控面板的结束位置")
        return False

if __name__ == "__main__":
    input_file = "outputs/仪表盘/SellAI_办公室.html"
    output_file = "outputs/仪表盘/SellAI_办公室_升级版.html"
    
    success = update_office_buddy(input_file, output_file)
    
    if success:
        # 复制一份作为备份
        import shutil
        backup_file = "outputs/仪表盘/SellAI_办公室_backup.html"
        shutil.copy2(input_file, backup_file)
        print(f"✅ 原始文件已备份到: {backup_file}")
        
        # 用更新后的文件替换原始文件
        shutil.copy2(output_file, input_file)
        print(f"✅ 原始文件已更新为包含Buddy面板的版本")
    else:
        print("❌ 更新失败")