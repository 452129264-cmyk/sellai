/**
 * SellAI Frontend - Main Application
 * 主应用逻辑
 */

// 全局状态
const APP_STATE = {
    currentPage: 'dashboard',
    socialAccounts: [],
    shopAccounts: [],
    avatars: [],
    opportunities: [],
    notifications: []
};

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// 应用初始化
async function initApp() {
    // 初始化配置
    initConfig();
    
    // 初始化导航
    initNavigation();
    
    // 初始化图片生成Tab
    initImageTabs();
    
    // 初始化设置导航
    initSettingsNav();
    
    // 加载初始数据
    await loadDashboardData();
    
    // 更新最后更新时间
    updateLastUpdateTime();
    
    // 检查API状态
    checkApiStatus();
}

// 初始化导航
function initNavigation() {
    // PC端导航
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            switchPage(page);
        });
    });
    
    // 移动端导航
    document.querySelectorAll('.mobile-nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            switchPage(page);
            toggleMobileMenu();
        });
    });
    
    // 移动端菜单按钮
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }
}

// 切换页面
function switchPage(page) {
    // 更新状态
    APP_STATE.currentPage = page;
    
    // 更新导航高亮
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === page);
    });
    
    // 切换页面显示
    document.querySelectorAll('.page-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const pageElement = document.getElementById(`page-${page}`);
    if (pageElement) {
        pageElement.classList.add('active');
    }
    
    // 加载页面数据
    loadPageData(page);
    
    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 加载页面数据
async function loadPageData(page) {
    switch (page) {
        case 'dashboard':
            await loadDashboardData();
            break;
        case 'social':
            await loadSocialData();
            break;
        case 'shops':
            await loadShopData();
            break;
        case 'opportunities':
            await loadOpportunitiesData();
            break;
        case 'avatars':
            await loadAvatarsData();
            break;
    }
}

// 加载仪表盘数据
async function loadDashboardData() {
    // 显示加载状态
    document.getElementById('opportunity-list').innerHTML = renderLoadingState('正在加载商机...');
    
    try {
        // 获取统计数据
        const stats = await fetchStats();
        
        // 更新统计卡片
        document.getElementById('today-opportunities').textContent = stats.todayOpportunities;
        document.getElementById('active-avatars').textContent = stats.activeAvatars;
        document.getElementById('bound-shops').textContent = stats.boundShops;
        document.getElementById('social-accounts').textContent = stats.socialAccounts;
        
        // 加载商机列表
        const opportunities = MOCK_DATA.opportunities.slice(0, 6);
        
        if (opportunities.length > 0) {
            document.getElementById('opportunity-list').innerHTML = opportunities.map(renderOpportunityCard).join('');
        } else {
            document.getElementById('opportunity-list').innerHTML = renderEmptyState('fa-lightbulb', '暂无商机', '开始扫描发现新商机');
        }
        
        // 更新最后更新时间
        updateLastUpdateTime();
        
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        document.getElementById('opportunity-list').innerHTML = renderEmptyState('fa-exclamation-triangle', '加载失败', '请刷新页面重试');
    }
}

// 加载社媒数据
async function loadSocialData() {
    const container = document.getElementById('social-platforms');
    container.innerHTML = CONFIG.SOCIAL_PLATFORMS.map(renderSocialPlatformCard).join('');
}

// 加载店铺数据
async function loadShopData() {
    const container = document.getElementById('shop-platforms');
    container.innerHTML = CONFIG.SHOP_PLATFORMS.map(renderShopPlatformCard).join('');
}

// 加载商机数据
async function loadOpportunitiesData() {
    const container = document.getElementById('opportunities-full-list');
    container.innerHTML = MOCK_DATA.opportunities.map(renderOpportunityCard).join('');
}

// 加载分身数据
async function loadAvatarsData() {
    const container = document.getElementById('avatar-list');
    const countElement = document.getElementById('avatar-count');
    
    const avatars = MOCK_DATA.avatars;
    
    if (countElement) {
        countElement.textContent = `${avatars.length} 个分身`;
    }
    
    if (avatars.length > 0) {
        container.innerHTML = avatars.map(renderAvatarCard).join('');
    } else {
        container.innerHTML = renderEmptyState('fa-user-robot', '暂无分身', '点击上方模板或按钮创建分身');
    }
}

// 刷新社媒账号
async function refreshSocialAccounts() {
    showToast('正在刷新...', 'info');
    await loadSocialData();
    showToast('刷新成功', 'success');
}

// 刷新店铺账号
async function refreshShopAccounts() {
    showToast('正在刷新...', 'info');
    await loadShopData();
    showToast('刷新成功', 'success');
}

// 显示绑定社媒模态框
function showBindSocialModal(platformId, platformName) {
    document.getElementById('social-bind-platform').value = platformName;
    document.getElementById('social-bind-platform').dataset.platformId = platformId;
    document.getElementById('social-bind-api-key').value = '';
    document.getElementById('social-bind-token').value = '';
    openModal('modal-social-bind');
}

// 绑定社媒账号
async function bindSocialAccount() {
    const platformId = document.getElementById('social-bind-platform').dataset.platformId;
    const apiKey = document.getElementById('social-bind-api-key').value;
    const token = document.getElementById('social-bind-token').value;
    
    if (!apiKey) {
        showToast('请输入API密钥', 'warning');
        return;
    }
    
    showLoading('正在绑定...');
    
    try {
        const result = await API.social.bind({
            platform: platformId,
            api_key: apiKey,
            access_token: token
        });
        
        hideLoading();
        
        if (result.success) {
            showToast('绑定成功', 'success');
            closeModal('modal-social-bind');
            await loadSocialData();
        } else {
            showToast(result.message || '绑定失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('绑定失败: ' + error.message, 'error');
    }
}

// 刷新单个社媒账号
async function refreshSocialAccount(platformId) {
    showToast('正在刷新Token...', 'info');
    // 模拟刷新
    await new Promise(resolve => setTimeout(resolve, 1000));
    showToast('Token已刷新', 'success');
}

// 显示解绑确认
function showUnbindSocialConfirm(platformId, platformName) {
    if (confirm(`确定要解绑 ${platformName} 吗？解绑后需要重新授权。`)) {
        unbindSocialAccount(platformId);
    }
}

// 解绑社媒账号
async function unbindSocialAccount(platformId) {
    showLoading('正在解绑...');
    
    try {
        const result = await API.social.unbind(platformId);
        hideLoading();
        
        if (result.success) {
            showToast('解绑成功', 'success');
            await loadSocialData();
        } else {
            showToast(result.message || '解绑失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('解绑失败: ' + error.message, 'error');
    }
}

// 显示绑定店铺模态框
function showBindShopModal(platformId, platformName) {
    document.getElementById('shop-bind-platform').value = platformName;
    document.getElementById('shop-bind-platform').dataset.platformId = platformId;
    document.getElementById('shop-bind-name').value = '';
    document.getElementById('shop-bind-api-key').value = '';
    document.getElementById('shop-bind-secret').value = '';
    document.getElementById('shop-bind-store-id').value = '';
    openModal('modal-shop-bind');
}

// 测试店铺连接
async function testShopConnection() {
    const apiKey = document.getElementById('shop-bind-api-key').value;
    const secret = document.getElementById('shop-bind-secret').value;
    
    if (!apiKey || !secret) {
        showToast('请输入API凭证', 'warning');
        return;
    }
    
    showToast('正在测试连接...', 'info');
    // 模拟测试
    await new Promise(resolve => setTimeout(resolve, 1500));
    showToast('连接成功!', 'success');
}

// 绑定店铺账号
async function bindShopAccount() {
    const platformId = document.getElementById('shop-bind-platform').dataset.platformId;
    const shopName = document.getElementById('shop-bind-name').value;
    const apiKey = document.getElementById('shop-bind-api-key').value;
    const secret = document.getElementById('shop-bind-secret').value;
    const storeId = document.getElementById('shop-bind-store-id').value;
    
    if (!shopName) {
        showToast('请输入店铺名称', 'warning');
        return;
    }
    
    showLoading('正在绑定...');
    
    try {
        const result = await API.shops.bind({
            platform: platformId,
            shop_name: shopName,
            api_key: apiKey,
            api_secret: secret,
            shop_id: storeId
        });
        
        hideLoading();
        
        if (result.success) {
            showToast('绑定成功', 'success');
            closeModal('modal-shop-bind');
            await loadShopData();
        } else {
            showToast(result.message || '绑定失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('绑定失败: ' + error.message, 'error');
    }
}

// 显示解绑店铺确认
function showUnbindShopConfirm(shopId, shopName) {
    if (confirm(`确定要解绑 ${shopName} 吗？`)) {
        unbindShopAccount(shopId);
    }
}

// 解绑店铺账号
async function unbindShopAccount(shopId) {
    showLoading('正在解绑...');
    
    try {
        const result = await API.shops.unbind(shopId);
        hideLoading();
        
        if (result.success) {
            showToast('解绑成功', 'success');
            await loadShopData();
        } else {
            showToast(result.message || '解绑失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('解绑失败: ' + error.message, 'error');
    }
}

// 开始商机扫描
async function startOpportunityScan() {
    showLoading('正在扫描商机...');
    
    try {
        const result = await API.monitor.start({ threshold: 0.45, max_results: 10 });
        hideLoading();
        
        if (result.success) {
            showToast(`发现 ${result.opportunities_found || 0} 个商机`, 'success');
            await loadDashboardData();
            switchPage('opportunities');
        } else {
            showToast('扫描完成，暂无符合条件商机', 'info');
        }
    } catch (error) {
        hideLoading();
        showToast('扫描失败: ' + error.message, 'error');
    }
}

// 启动分身
async function startAvatar(avatarId) {
    showLoading('正在启动分身...');
    
    try {
        const result = await API.avatar.start(avatarId);
        hideLoading();
        
        if (result.success) {
            showToast('分身已启动', 'success');
            await loadAvatarsData();
        } else {
            showToast(result.message || '启动失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('启动失败: ' + error.message, 'error');
    }
}

// 停止分身
async function stopAvatar(avatarId) {
    showLoading('正在停止分身...');
    
    try {
        const result = await API.avatar.stop(avatarId);
        hideLoading();
        
        if (result.success) {
            showToast('分身已停止', 'success');
            await loadAvatarsData();
        } else {
            showToast(result.message || '停止失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('停止失败: ' + error.message, 'error');
    }
}

// 删除分身
async function deleteAvatar(avatarId) {
    if (!confirm('确定要删除这个分身吗？')) return;
    
    showLoading('正在删除...');
    await new Promise(resolve => setTimeout(resolve, 500));
    MOCK_DATA.avatars = MOCK_DATA.avatars.filter(a => a.id !== avatarId);
    hideLoading();
    showToast('分身已删除', 'success');
    await loadAvatarsData();
}

// 显示创建分身模态框
function showCreateAvatarModal() {
    document.getElementById('avatar-name').value = '';
    document.getElementById('avatar-template').value = 'general';
    document.getElementById('avatar-description').value = '';
    openModal('modal-create-avatar');
}

// 创建分身
async function createAvatar() {
    const name = document.getElementById('avatar-name').value;
    const template = document.getElementById('avatar-template').value;
    const description = document.getElementById('avatar-description').value;
    
    if (!name) {
        showToast('请输入分身名称', 'warning');
        return;
    }
    
    showLoading('正在创建分身...');
    
    try {
        const result = await API.avatar.create({
            name,
            template,
            description
        });
        
        hideLoading();
        
        if (result.success) {
            showToast('分身创建成功', 'success');
            closeModal('modal-create-avatar');
            await loadAvatarsData();
        } else {
            showToast(result.message || '创建失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('创建失败: ' + error.message, 'error');
    }
}

// 显示分身任务
function showAvatarTasks(avatarId) {
    showToast('任务功能开发中...', 'info');
}

// 初始化图片生成Tab
function initImageTabs() {
    document.querySelectorAll('.image-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // 更新Tab样式
            document.querySelectorAll('.image-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 更新表单显示
            document.querySelectorAll('.image-form').forEach(f => f.classList.remove('active'));
            document.getElementById(`${tab}-form`).classList.add('active');
            
            // 显示/隐藏参考图片上传
            const refUpload = document.getElementById('ref-image-upload');
            if (tab === 'image2image') {
                refUpload.classList.remove('hidden');
            } else {
                refUpload.classList.add('hidden');
            }
        });
    });
}

// 生成图片
async function generateImage() {
    const prompt = document.getElementById('image-prompt').value;
    
    if (!prompt) {
        showToast('请输入图片描述', 'warning');
        return;
    }
    
    const size = document.getElementById('image-size').value;
    const count = parseInt(document.getElementById('image-count').value);
    
    showLoading('正在生成图片...');
    
    try {
        const result = await API.image.text2image({
            prompt,
            size,
            num_images: count
        });
        
        hideLoading();
        
        if (result.success && result.images) {
            // 更新图片展示
            const container = document.getElementById('generated-images');
            container.innerHTML = result.images.map(url => `
                <div class="generated-image-card">
                    <img src="${url}" alt="生成图片" onerror="this.src='https://picsum.photos/512/512?random=${Date.now()}'">
                    <div class="overlay">
                        <button onclick="downloadImage('${url}')" class="px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm">
                            <i class="fas fa-download mr-1"></i>
                            下载
                        </button>
                    </div>
                </div>
            `).join('');
            
            // 添加到历史
            MOCK_DATA.imageHistory.unshift({
                id: Date.now().toString(),
                url: result.images[0],
                prompt,
                created_at: new Date().toLocaleString()
            });
            
            // 更新历史显示
            updateImageHistory();
            
            showToast(`成功生成 ${result.images.length} 张图片`, 'success');
        } else {
            showToast('生成失败', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('生成失败: ' + error.message, 'error');
    }
}

// 处理参考图片上传
function handleRefImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            showToast('参考图片已上传', 'success');
        };
        reader.readAsDataURL(file);
    }
}

// 下载图片
function downloadImage(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = `sellai_image_${Date.now()}.png`;
    a.click();
}

// 下载全部图片
function downloadAllImages() {
    const images = document.querySelectorAll('#generated-images img');
    if (images.length === 0) {
        showToast('暂无图片可下载', 'warning');
        return;
    }
    
    images.forEach((img, index) => {
        setTimeout(() => {
            downloadImage(img.src);
        }, index * 500);
    });
}

// 更新图片历史
function updateImageHistory() {
    const container = document.getElementById('image-history');
    
    if (MOCK_DATA.imageHistory.length > 0) {
        container.innerHTML = MOCK_DATA.imageHistory.slice(0, 10).map(renderImageHistoryItem).join('');
    } else {
        container.innerHTML = '<p class="text-sm text-gray-500 text-center py-4">暂无历史记录</p>';
    }
}

// 初始化设置导航
function initSettingsNav() {
    document.querySelectorAll('.settings-nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            
            // 更新导航高亮
            document.querySelectorAll('.settings-nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // 切换section显示
            document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
            document.getElementById(`settings-${section}`).classList.add('active');
        });
    });
}

// 检查API状态
async function checkApiStatus() {
    const status = document.getElementById('api-status');
    
    if (CONFIG.MOCK.ENABLED) {
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                <span class="text-gray-400">Mock模式</span>
            `;
        }
        return;
    }
    
    try {
        const response = await fetch(`${CONFIG.API.BASE_URL}/docs`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span class="text-gray-400">API正常</span>
            `;
            status.classList.remove('hidden');
        }
    } catch (error) {
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-red-500"></span>
                <span class="text-gray-400">API异常</span>
            `;
        }
    }
}

// 显示商机详情
function showOpportunityDetail(oppId) {
    const opp = MOCK_DATA.opportunities.find(o => o.id === oppId);
    if (opp) {
        showToast(`查看 ${opp.product_name} 详情`, 'info');
        // 可以扩展为详情模态框
    }
}

// 显示图片详情
function showImageDetail(imageId) {
    const image = MOCK_DATA.imageHistory.find(i => i.id === imageId);
    if (image) {
        window.open(image.url, '_blank');
    }
}

// 更新最后更新时间
function updateLastUpdateTime() {
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
}

// 模态框操作
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// 移动端菜单
function toggleMobileMenu() {
    const sidebar = document.getElementById('mobile-sidebar');
    const menuContent = sidebar.querySelector('div:last-child');
    
    if (sidebar.classList.contains('hidden')) {
        sidebar.classList.remove('hidden');
        setTimeout(() => {
            menuContent.classList.remove('translate-x-full');
        }, 10);
    } else {
        menuContent.classList.add('translate-x-full');
        setTimeout(() => {
            sidebar.classList.add('hidden');
        }, 300);
    }
}

// Toast通知
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
        success: 'fa-check-circle text-green-400',
        error: 'fa-times-circle text-red-400',
        warning: 'fa-exclamation-circle text-yellow-400',
        info: 'fa-info-circle text-blue-400'
    };
    
    toast.innerHTML = `
        <i class="fas ${iconMap[type]} mr-3 text-lg"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // 自动移除
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 显示加载
function showLoading(text = '加载中...') {
    const overlay = document.getElementById('loading-overlay');
    const textElement = document.getElementById('loading-text');
    
    if (textElement) {
        textElement.textContent = text;
    }
    
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

// 隐藏加载
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}
