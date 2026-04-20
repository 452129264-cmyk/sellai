/**
 * SellAI Frontend - UI Components
 * UI组件渲染函数
 */

// 渲染社媒平台卡片
function renderSocialPlatformCard(platform) {
    const isBound = isPlatformBound(platform.id);
    const account = getBoundAccount(platform.id);
    
    return `
        <div class="platform-card ${isBound ? 'bound' : 'unbound'}" data-platform="${platform.id}">
            <div class="flex items-start justify-between mb-4">
                <div class="flex items-center">
                    <div class="platform-icon bg-gradient-to-br ${platform.bgGradient}" style="color: ${platform.color}">
                        <i class="fab ${platform.icon}"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="font-semibold">${platform.name}</h3>
                        <p class="text-xs text-gray-500">${platform.description}</p>
                    </div>
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-medium ${isBound ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}">
                    ${isBound ? '已绑定' : '未绑定'}
                </span>
            </div>
            
            ${isBound ? `
                <div class="bg-dark-200 rounded-xl p-3 mb-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium">${account.account_name || '已绑定账号'}</p>
                            <p class="text-xs text-gray-500">粉丝: ${account.followers || '--'}</p>
                        </div>
                        <div class="w-8 h-8 rounded-full bg-${platform.color}/20 flex items-center justify-center">
                            <i class="fas fa-check text-green-400"></i>
                        </div>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button onclick="refreshSocialAccount('${platform.id}')" class="flex-1 px-3 py-2 bg-dark-200 hover:bg-dark-100 rounded-lg text-sm transition-colors flex items-center justify-center">
                        <i class="fas fa-sync-alt mr-1"></i>
                        刷新
                    </button>
                    <button onclick="showUnbindSocialConfirm('${platform.id}', '${platform.name}')" class="flex-1 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm transition-colors flex items-center justify-center">
                        <i class="fas fa-unlink mr-1"></i>
                        解绑
                    </button>
                </div>
            ` : `
                <p class="text-sm text-gray-400 mb-4">点击绑定账号，开始跨平台管理</p>
                <button onclick="showBindSocialModal('${platform.id}', '${platform.name}')" class="w-full px-4 py-2 bg-gradient-to-r ${platform.bgGradient} hover:opacity-80 rounded-lg text-sm font-medium transition-opacity flex items-center justify-center" style="color: ${platform.color}">
                    <i class="fas fa-link mr-2"></i>
                    绑定账号
                </button>
            `}
        </div>
    `;
}

// 渲染店铺平台卡片
function renderShopPlatformCard(platform) {
    const isBound = isPlatformBound(platform.id, 'shop');
    const shops = MOCK_DATA.shopAccounts.filter(s => s.platform === platform.id);
    
    return `
        <div class="platform-card ${isBound ? 'bound' : 'unbound'}" data-platform="${platform.id}">
            <div class="flex items-start justify-between mb-4">
                <div class="flex items-center">
                    <div class="platform-icon bg-gradient-to-br ${platform.bgGradient}" style="color: ${platform.color}">
                        <i class="fas ${platform.icon}"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="font-semibold">${platform.name}</h3>
                        <p class="text-xs text-gray-500">${platform.description}</p>
                    </div>
                </div>
                ${isBound ? `
                    <span class="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                        ${shops.length}个店铺
                    </span>
                ` : `
                    <span class="px-2 py-1 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400">
                        未绑定
                    </span>
                `}
            </div>
            
            ${isBound ? `
                <div class="space-y-2 mb-4">
                    ${shops.map(shop => `
                        <div class="bg-dark-200 rounded-xl p-3">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-sm font-medium">${shop.shop_name}</p>
                                    <p class="text-xs text-gray-500">商品: ${shop.products || 0}件</p>
                                </div>
                                <button onclick="showUnbindShopConfirm('${shop.id}', '${shop.shop_name}')" class="p-1.5 hover:bg-dark-100 rounded-lg transition-colors text-red-400">
                                    <i class="fas fa-trash-alt text-sm"></i>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <button onclick="showBindShopModal('${platform.id}', '${platform.name}')" class="w-full px-4 py-2 bg-dark-200 hover:bg-dark-100 rounded-lg text-sm transition-colors flex items-center justify-center">
                    <i class="fas fa-plus mr-2"></i>
                    添加店铺
                </button>
            ` : `
                <p class="text-sm text-gray-400 mb-4">点击添加店铺，实现多店铺统一管理</p>
                <button onclick="showBindShopModal('${platform.id}', '${platform.name}')" class="w-full px-4 py-2 bg-gradient-to-r ${platform.bgGradient} hover:opacity-80 rounded-lg text-sm font-medium transition-opacity flex items-center justify-center" style="color: ${platform.color}">
                    <i class="fas fa-store mr-2"></i>
                    添加店铺
                </button>
            `}
        </div>
    `;
}

// 渲染商机卡片
function renderOpportunityCard(opp) {
    const marginLevel = getMarginLevel(opp.margin);
    
    return `
        <div class="opportunity-card" onclick="showOpportunityDetail('${opp.id}')">
            <div class="flex items-start space-x-3">
                <img src="${opp.image || 'https://picsum.photos/100/100?random=' + opp.id}" alt="${opp.product_name}" class="w-16 h-16 rounded-xl object-cover bg-dark-200">
                <div class="flex-1 min-w-0">
                    <div class="flex items-start justify-between">
                        <h4 class="font-medium text-sm truncate pr-2">${opp.product_name}</h4>
                        <span class="margin-badge ${marginLevel} shrink-0">${opp.margin}%</span>
                    </div>
                    <div class="flex items-center mt-1 text-xs text-gray-400">
                        <span class="px-1.5 py-0.5 bg-dark-200 rounded">${opp.source}</span>
                        <span class="mx-1">•</span>
                        <i class="fas ${getTrendIcon(opp.trend)} text-xs"></i>
                        <span class="ml-1">${getTrendText(opp.trend)}</span>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                        <div class="text-xs">
                            <span class="text-gray-500">成本:</span>
                            <span class="text-white font-medium ml-1">¥${opp.cost_price}</span>
                        </div>
                        <div class="text-xs">
                            <span class="text-gray-500">售价:</span>
                            <span class="text-green-400 font-medium ml-1">¥${opp.sell_price}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 渲染分身卡片
function renderAvatarCard(avatar) {
    const template = CONFIG.AVATAR_TEMPLATES.find(t => t.id === avatar.template) || CONFIG.AVATAR_TEMPLATES[4];
    
    return `
        <div class="avatar-card">
            <div class="flex items-start space-x-3">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br ${template.id === 'tiktok' ? 'from-pink-500/20 to-purple-500/20' : template.id === 'seo' ? 'from-blue-500/20 to-cyan-500/20' : template.id === 'ecommerce' ? 'from-green-500/20 to-emerald-500/20' : template.id === 'negotiation' ? 'from-orange-500/20 to-amber-500/20' : 'from-gray-500/20 to-slate-500/20'}" style="color: ${template.color}">
                    <div class="w-full h-full flex items-center justify-center">
                        <i class="fas ${template.icon}"></i>
                    </div>
                </div>
                <div class="flex-1">
                    <div class="flex items-center justify-between">
                        <h4 class="font-medium">${avatar.name}</h4>
                        <span class="status-indicator ${avatar.status === 'running' ? 'running' : 'stopped'}">
                            <span class="w-1.5 h-1.5 rounded-full mr-1.5 ${avatar.status === 'running' ? 'bg-green-400' : 'bg-gray-400'}"></span>
                            ${avatar.status === 'running' ? '运行中' : '已停止'}
                        </span>
                    </div>
                    <p class="text-xs text-gray-400 mt-0.5">${template.name}</p>
                    <div class="flex items-center mt-2 text-xs text-gray-500">
                        <i class="fas fa-tasks mr-1"></i>
                        <span>已完成 ${avatar.tasks_completed || 0} 个任务</span>
                    </div>
                </div>
            </div>
            <div class="flex space-x-2 mt-4 pt-3 border-t border-gray-700/30">
                ${avatar.status === 'running' ? `
                    <button onclick="stopAvatar('${avatar.id}')" class="flex-1 px-3 py-1.5 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 rounded-lg text-sm transition-colors">
                        <i class="fas fa-pause mr-1"></i>
                        暂停
                    </button>
                ` : `
                    <button onclick="startAvatar('${avatar.id}')" class="flex-1 px-3 py-1.5 bg-green-500/10 hover:bg-green-500/20 text-green-400 rounded-lg text-sm transition-colors">
                        <i class="fas fa-play mr-1"></i>
                        启动
                    </button>
                `}
                <button onclick="showAvatarTasks('${avatar.id}')" class="flex-1 px-3 py-1.5 bg-dark-200 hover:bg-dark-100 rounded-lg text-sm transition-colors">
                    <i class="fas fa-list mr-1"></i>
                    任务
                </button>
                <button onclick="deleteAvatar('${avatar.id}')" class="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm transition-colors">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        </div>
    `;
}

// 渲染通知项
function renderNotificationItem(notification) {
    const iconMap = {
        opportunity: { icon: 'fa-lightbulb', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
        system: { icon: 'fa-cog', color: 'text-blue-400', bg: 'bg-blue-500/20' },
        alert: { icon: 'fa-bell', color: 'text-red-400', bg: 'bg-red-500/20' }
    };
    const icon = iconMap[notification.type] || iconMap.system;
    
    return `
        <div class="flex items-start space-x-3 p-3 bg-dark-200 rounded-xl ${notification.read ? 'opacity-60' : ''}">
            <div class="w-10 h-10 rounded-xl ${icon.bg} flex items-center justify-center shrink-0">
                <i class="fas ${icon.icon} ${icon.color}"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                    <p class="font-medium text-sm">${notification.title}</p>
                    <span class="text-xs text-gray-500">${notification.time}</span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5">${notification.message}</p>
            </div>
            ${!notification.read ? `
                <span class="w-2 h-2 rounded-full bg-primary-500 shrink-0"></span>
            ` : ''}
        </div>
    `;
}

// 渲染图片历史项
function renderImageHistoryItem(item) {
    return `
        <div class="flex items-center space-x-3 p-2 bg-dark-200 rounded-lg hover:bg-dark-100 transition-colors cursor-pointer" onclick="showImageDetail('${item.id}')">
            <img src="${item.thumbnail || item.url}" alt="生成图片" class="w-10 h-10 rounded-lg object-cover">
            <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-400 truncate">${item.prompt}</p>
                <p class="text-xs text-gray-500">${item.created_at}</p>
            </div>
        </div>
    `;
}

// 渲染空状态
function renderEmptyState(icon, title, description) {
    return `
        <div class="empty-state">
            <i class="fas ${icon}"></i>
            <p class="font-medium mt-2">${title}</p>
            <p class="text-sm mt-1">${description}</p>
        </div>
    `;
}

// 渲染加载状态
function renderLoadingState(text = '加载中...') {
    return `
        <div class="flex flex-col items-center justify-center py-12">
            <div class="loading-spinner mb-4"></div>
            <p class="text-gray-400">${text}</p>
        </div>
    `;
}
