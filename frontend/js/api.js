/**
 * SellAI Frontend - API Module
 * API请求封装
 */

const API = {
    // 认证相关
    auth: {
        async register(data) {
            return request('/api/auth/register', { method: 'POST', body: data });
        },
        async login(data) {
            return request('/api/auth/login', { method: 'POST', body: data });
        },
        async profile() {
            return request('/api/auth/profile');
        }
    },
    
    // 社媒账号管理
    social: {
        async list() {
            return request('/api/social/accounts');
        },
        async bind(data) {
            return request('/api/social/bind', { method: 'POST', body: data });
        },
        async unbind(platform) {
            return request(`/api/social/unbind/${platform}`, { method: 'DELETE' });
        }
    },
    
    // 店铺管理
    shops: {
        async list() {
            return request('/api/shops');
        },
        async bind(data) {
            return request('/api/shops/bind', { method: 'POST', body: data });
        },
        async unbind(shopId) {
            return request(`/api/shops/unbind/${shopId}`, { method: 'DELETE' });
        }
    },
    
    // 商机监控
    monitor: {
        async start(data) {
            return request('/api/monitor/active', { method: 'POST', body: data });
        },
        async notifications(params = {}) {
            return request('/api/monitor/notifications', { params });
        }
    },
    
    // 商机分析
    analysis: {
        async opportunity(data) {
            return request('/api/analysis/opportunity', { method: 'POST', body: data });
        }
    },
    
    // 图片生成
    image: {
        async text2image(data) {
            return request('/api/image/text2image', { method: 'POST', body: data });
        },
        async image2image(data) {
            return request('/api/image/image2image', { method: 'POST', body: data });
        }
    },
    
    // 分身系统
    avatar: {
        async list() {
            return request('/api/v2/avatar/list');
        },
        async create(data) {
            return request('/api/v2/avatar/create', { method: 'POST', body: data });
        },
        async start(id, data) {
            return request(`/api/v2/avatar/start`, { method: 'POST', body: { avatar_id: id, ...data } });
        },
        async stop(id) {
            return request(`/api/v2/avatar/stop`, { method: 'POST', body: { avatar_id: id } });
        }
    }
};

// 核心请求函数
async function request(endpoint, options = {}) {
    const { method = 'GET', body = null, params = {} } = options;
    
    // Mock模式
    if (CONFIG.MOCK.ENABLED) {
        return mockRequest(endpoint, method, body);
    }
    
    // 构建URL
    let url = `${CONFIG.API.BASE_URL}${endpoint}`;
    
    // 添加查询参数
    if (Object.keys(params).length > 0) {
        const searchParams = new URLSearchParams(params);
        url += `?${searchParams.toString()}`;
    }
    
    // 构建请求头
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // 添加Token (如果存在)
    const token = localStorage.getItem('sellai_token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 构建请求配置
    const config = {
        method,
        headers,
        signal: AbortSignal.timeout(CONFIG.API.TIMEOUT)
    };
    
    // 添加请求体
    if (body && method !== 'GET') {
        config.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(url, config);
        
        // 检查HTTP状态
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new ApiError(error.message || `HTTP ${response.status}`, response.status);
        }
        
        return await response.json();
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new ApiError('请求超时', 408);
        }
        throw error;
    }
}

// API错误类
class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

// Mock请求处理
async function mockRequest(endpoint, method, body) {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, CONFIG.MOCK.DELAY));
    
    // 根据端点返回模拟数据
    if (endpoint === '/api/social/accounts') {
        return MOCK_DATA.socialAccounts;
    }
    
    if (endpoint === '/api/social/bind' && method === 'POST') {
        const newAccount = {
            id: Date.now().toString(),
            platform: body.platform,
            account_name: body.account_name || '模拟账号',
            status: 'active',
            bound_at: new Date().toISOString()
        };
        MOCK_DATA.socialAccounts.push(newAccount);
        return { success: true, account: newAccount };
    }
    
    if (endpoint.startsWith('/api/social/unbind/') && method === 'DELETE') {
        const platform = endpoint.split('/').pop();
        MOCK_DATA.socialAccounts = MOCK_DATA.socialAccounts.filter(a => a.platform !== platform);
        return { success: true };
    }
    
    if (endpoint === '/api/shops') {
        return MOCK_DATA.shopAccounts;
    }
    
    if (endpoint === '/api/shops/bind' && method === 'POST') {
        const newShop = {
            id: Date.now().toString(),
            platform: body.platform,
            shop_name: body.shop_name || '模拟店铺',
            shop_id: body.shop_id || `SHOP_${Date.now()}`,
            status: 'active',
            bound_at: new Date().toISOString()
        };
        MOCK_DATA.shopAccounts.push(newShop);
        return { success: true, shop: newShop };
    }
    
    if (endpoint.startsWith('/api/shops/unbind/') && method === 'DELETE') {
        const shopId = endpoint.split('/').pop();
        MOCK_DATA.shopAccounts = MOCK_DATA.shopAccounts.filter(s => s.id !== shopId);
        return { success: true };
    }
    
    if (endpoint === '/api/monitor/active' && method === 'POST') {
        // 模拟商机扫描
        const threshold = body?.threshold || 0.6;
        const opportunities = MOCK_DATA.opportunities.filter(o => o.margin >= threshold);
        return {
            success: true,
            opportunities_found: opportunities.length,
            threshold: threshold,
            data: opportunities.slice(0, 3)
        };
    }
    
    if (endpoint === '/api/monitor/notifications') {
        return { notifications: MOCK_DATA.notifications };
    }
    
    if (endpoint === '/api/analysis/opportunity' && method === 'POST') {
        const product = body?.product_name || '未知商品';
        const analysis = MOCK_DATA.opportunityAnalysis;
        return {
            ...analysis,
            product_name: product,
            suggested_price: Math.floor(Math.random() * 500) + 50
        };
    }
    
    if (endpoint === '/api/image/text2image' && method === 'POST') {
        const mockImages = [
            'https://picsum.photos/512/512?random=1',
            'https://picsum.photos/512/512?random=2',
            'https://picsum.photos/512/512?random=3',
            'https://picsum.photos/512/512?random=4'
        ];
        return {
            success: true,
            images: mockImages.slice(0, body?.num_images || 1),
            prompt: body?.prompt
        };
    }
    
    if (endpoint === '/api/v2/avatar/list') {
        return { avatars: MOCK_DATA.avatars };
    }
    
    if (endpoint === '/api/v2/avatar/create' && method === 'POST') {
        const newAvatar = {
            id: `avatar_${Date.now()}`,
            name: body?.name || '新分身',
            template: body?.template || 'general',
            status: 'stopped',
            created_at: new Date().toISOString()
        };
        MOCK_DATA.avatars.push(newAvatar);
        return { success: true, avatar: newAvatar };
    }
    
    if (endpoint === '/api/v2/avatar/start' && method === 'POST') {
        const avatarId = body?.avatar_id;
        const avatar = MOCK_DATA.avatars.find(a => a.id === avatarId);
        if (avatar) {
            avatar.status = 'running';
        }
        return { success: true, status: 'running' };
    }
    
    if (endpoint === '/api/v2/avatar/stop' && method === 'POST') {
        const avatarId = body?.avatar_id;
        const avatar = MOCK_DATA.avatars.find(a => a.id === avatarId);
        if (avatar) {
            avatar.status = 'stopped';
        }
        return { success: true, status: 'stopped' };
    }
    
    // 默认返回成功
    return { success: true };
}

// 获取统计数据
async function fetchStats() {
    if (CONFIG.MOCK.ENABLED) {
        return {
            todayOpportunities: MOCK_DATA.stats.todayOpportunities,
            activeAvatars: MOCK_DATA.avatars.filter(a => a.status === 'running').length,
            boundShops: MOCK_DATA.shopAccounts.length,
            socialAccounts: MOCK_DATA.socialAccounts.length
        };
    }
    
    try {
        const [socialRes, shopsRes, avatarsRes] = await Promise.all([
            API.social.list(),
            API.shops.list(),
            API.avatar.list()
        ]);
        
        return {
            todayOpportunities: MOCK_DATA.stats.todayOpportunities, // 从商机列表计算
            activeAvatars: avatarsRes.avatars?.filter(a => a.status === 'running').length || 0,
            boundShops: shopsRes.shops?.length || 0,
            socialAccounts: socialRes.accounts?.length || 0
        };
    } catch (error) {
        console.error('Failed to fetch stats:', error);
        return MOCK_DATA.stats;
    }
}
