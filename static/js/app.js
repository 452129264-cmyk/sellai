// 页面路由
function navigateTo(page) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.add('hidden'));
    const target = document.getElementById('page-' + page);
    if (target) target.classList.remove('hidden');
    document.querySelectorAll('.nav-link, .mobile-nav-link').forEach(a => {
        a.classList.toggle('active', a.dataset.page === page);
    });
}

document.querySelectorAll('.nav-link, .mobile-nav-link').forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        navigateTo(a.dataset.page);
        const sidebar = document.getElementById('mobile-sidebar');
        if (sidebar) sidebar.querySelector('div:last-child')?.classList.add('translate-x-full');
    });
});

// ========== 图片生成功能 ==========
async function generateImage() {
    const prompt = document.getElementById('image-prompt')?.value?.trim();
    if (!prompt) {
        alert('请输入图片描述');
        return;
    }
    
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>生成中...';
    btn.disabled = true;
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/v2/bailian/text2image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, num_images: 4 })
        });
        
        const data = await response.json();
        
        if (data.images && data.images.length > 0) {
            // 显示生成的图片
            const container = document.getElementById('generated-images');
            if (container) {
                container.innerHTML = data.images.map((img, i) => `
                    <div class="relative group">
                        <img src="${img.url || img}" class="w-full rounded-lg" alt="生成图片 ${i+1}">
                        <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                            <button onclick="downloadImage('${img.url || img}')" class="bg-white text-gray-800 px-4 py-2 rounded-lg">
                                <i class="fas fa-download mr-2"></i>下载
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            alert('图片生成成功！');
        } else {
            alert('图片生成失败：' + (data.error || '未知错误'));
        }
    } catch (e) {
        console.error('生成图片失败:', e);
        alert('图片生成失败，请检查API配置');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function downloadImage(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sellai-image.png';
    a.click();
}

async function downloadAllImages() {
    const images = document.querySelectorAll('#generated-images img');
    if (images.length === 0) {
        alert('没有可下载的图片');
        return;
    }
    images.forEach((img, i) => {
        setTimeout(() => downloadImage(img.src), i * 500);
    });
    alert(`开始下载 ${images.length} 张图片`);
}

// ========== 商机扫描功能 ==========
async function startOpportunityScan() {
    const btn = event.target;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>扫描中...';
    btn.disabled = true;
    
    try {
        const data = await loadOpportunities();
        console.log('商机扫描结果', data);
        
        if (data && data.opportunities) {
            const container = document.getElementById('opportunity-list');
            if (container) {
                container.innerHTML = data.opportunities.map(opp => `
                    <div class="bg-dark-200 rounded-lg p-4 border border-gray-700">
                        <h4 class="font-medium text-white">${opp.title || opp.product_name}</h4>
                        <p class="text-sm text-gray-400 mt-1">利润率: ${opp.margin || opp.profit_margin}%</p>
                        <p class="text-sm text-gray-400">价格: ¥${opp.price}</p>
                    </div>
                `).join('');
            }
            alert(`发现 ${data.opportunities.length} 个商机！`);
        } else {
            alert('暂无新商机');
        }
    } catch (e) {
        console.error('商机扫描失败:', e);
        alert('商机扫描失败');
    } finally {
        btn.innerHTML = '<i class="fas fa-search mr-2"></i>开始扫描';
        btn.disabled = false;
    }
}

// ========== 分身管理功能 ==========
async function createAvatar() {
    const name = document.getElementById('avatar-name')?.value?.trim();
    if (!name) {
        alert('请输入分身名称');
        return;
    }
    
    const role = document.getElementById('avatar-role')?.value || 'assistant';
    const btn = event.target;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>创建中...';
    btn.disabled = true;
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/v3/marketplace/custom/avatar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, role: role, capabilities: ['chat', 'analysis'] })
        });
        
        const data = await response.json();
        console.log('创建分身', data);
        
        if (data.avatar_id || data.id) {
            alert('分身创建成功！');
            closeModal('modal-create-avatar');
            loadAvatarList();
        } else {
            alert('创建失败：' + (data.error || '未知错误'));
        }
    } catch (e) {
        console.error('创建分身失败:', e);
        alert('创建分身失败');
    } finally {
        btn.innerHTML = '创建分身';
        btn.disabled = false;
    }
}

async function loadAvatarList() {
    try {
        const data = await loadAvatars();
        const container = document.getElementById('avatar-list');
        if (container && data) {
            const avatars = data.avatars || data;
            container.innerHTML = avatars.map(a => `
                <div class="bg-dark-200 rounded-lg p-4 border border-gray-700">
                    <div class="flex items-center justify-between">
                        <div>
                            <h4 class="font-medium text-white">${a.name}</h4>
                            <p class="text-sm text-gray-400">${a.role || a.status}</p>
                        </div>
                        <span class="px-2 py-1 text-xs rounded-full ${a.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}">
                            ${a.status || 'idle'}
                        </span>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('加载分身列表失败:', e);
    }
}

// ========== 社媒绑定功能 ==========
async function bindSocialAccount() {
    const platform = document.getElementById('social-platform')?.value;
    if (!platform) {
        alert('请选择平台');
        return;
    }
    
    try {
        // 获取OAuth URL
        const response = await fetch(CONFIG.API_BASE + `/api/ecommerce/oauth-url/${platform}`);
        const data = await response.json();
        
        if (data.oauth_url) {
            // 打开OAuth授权页面
            window.open(data.oauth_url, '_blank', 'width=600,height=600');
            alert('请在弹出窗口中完成授权');
        } else {
            alert('获取授权链接失败');
        }
    } catch (e) {
        console.error('社媒绑定失败:', e);
        alert('社媒绑定失败，请稍后重试');
    }
}

async function refreshSocialAccounts() {
    const container = document.getElementById('social-accounts-list');
    if (container) {
        container.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    }
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/v3/social/stats');
        const data = await response.json();
        console.log('社媒账号列表', data);
        
        if (container && data.accounts) {
            container.innerHTML = data.accounts.map(a => `
                <div class="bg-dark-200 rounded-lg p-4 border border-gray-700 flex items-center justify-between">
                    <div class="flex items-center">
                        <i class="fab fa-${a.platform} text-2xl mr-3"></i>
                        <div>
                            <h4 class="font-medium text-white">${a.username || a.name}</h4>
                            <p class="text-sm text-gray-400">${a.platform}</p>
                        </div>
                    </div>
                    <span class="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-400">已绑定</span>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('刷新社媒账号失败:', e);
        if (container) {
            container.innerHTML = '<div class="text-center py-4 text-gray-400">暂无绑定账号</div>';
        }
    }
}

// ========== 店铺绑定功能 ==========
async function bindShopAccount() {
    const platform = document.getElementById('shop-platform')?.value;
    const shopName = document.getElementById('shop-name')?.value?.trim();
    
    if (!platform || !shopName) {
        alert('请填写完整信息');
        return;
    }
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/ecommerce/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: platform, shop_name: shopName })
        });
        
        const data = await response.json();
        
        if (data.success || data.shop_id) {
            alert('店铺绑定成功！');
            refreshShopAccounts();
        } else {
            alert('绑定失败：' + (data.error || '未知错误'));
        }
    } catch (e) {
        console.error('店铺绑定失败:', e);
        alert('店铺绑定失败');
    }
}

async function refreshShopAccounts() {
    const container = document.getElementById('shop-accounts-list');
    if (container) {
        container.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    }
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/ecommerce/status');
        const data = await response.json();
        console.log('店铺列表', data);
        
        if (container && data.shops) {
            container.innerHTML = data.shops.map(s => `
                <div class="bg-dark-200 rounded-lg p-4 border border-gray-700 flex items-center justify-between">
                    <div class="flex items-center">
                        <i class="fas fa-store text-2xl mr-3 text-primary-400"></i>
                        <div>
                            <h4 class="font-medium text-white">${s.shop_name}</h4>
                            <p class="text-sm text-gray-400">${s.platform}</p>
                        </div>
                    </div>
                    <span class="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-400">已绑定</span>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('刷新店铺账号失败:', e);
        if (container) {
            container.innerHTML = '<div class="text-center py-4 text-gray-400">暂无绑定店铺</div>';
        }
    }
}

async function testShopConnection() {
    const shopId = document.getElementById('selected-shop-id')?.value;
    if (!shopId) {
        alert('请先选择店铺');
        return;
    }
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/ecommerce/status');
        const data = await response.json();
        
        if (data.connected) {
            alert('连接正常！');
        } else {
            alert('连接失败：' + (data.error || '请检查店铺配置'));
        }
    } catch (e) {
        console.error('连接测试失败:', e);
        alert('连接测试失败');
    }
}

// ========== 设置功能 ==========
async function saveApiSettings() {
    const key = document.getElementById('api-key-input')?.value?.trim();
    
    if (!key) {
        alert('请输入API密钥');
        return;
    }
    
    try {
        const response = await fetch(CONFIG.API_BASE + '/api/v3/security/apikey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key })
        });
        
        const data = await response.json();
        
        if (data.success || data.key_id) {
            alert('API密钥保存成功！');
        } else {
            alert('保存失败：' + (data.error || '未知错误'));
        }
    } catch (e) {
        console.error('保存API设置失败:', e);
        // 本地保存作为备用
        localStorage.setItem('sellai_api_key', key);
        alert('API密钥已本地保存');
    }
}

// ========== 初始化 ==========
window.addEventListener('DOMContentLoaded', () => {
    navigateTo('dashboard');
    
    // 自动加载数据
    setTimeout(() => {
        loadAvatarList();
        refreshSocialAccounts();
        refreshShopAccounts();
    }, 500);
});
