/**
 * SellAI Frontend - Configuration
 * 应用配置文件
 */

const CONFIG = {
    // API配置
    API: {
        // 主API地址 (v3.2.0)
        PRIMARY: 'https://genuine-insight-production-15b4.up.railway.app',
        // 备用API地址 (v2.4.0)
        BACKUP: 'https://sellai-production-8397.up.railway.app',
        // 当前使用的API
        BASE_URL: '',
        // API版本
        VERSION: 'v2.4.0',
        // 超时时间(ms)
        TIMEOUT: 30000,
        // 重试次数
        RETRY: 3
    },
    
    // Mock模式配置
    MOCK: {
        ENABLED: false,  // 关闭Mock模式，使用真实API
        DELAY: 500      // 模拟API延迟(ms)
    },
    
    // 支持的社媒平台
    SOCIAL_PLATFORMS: [
        {
            id: 'facebook',
            name: 'Facebook',
            icon: 'fa-facebook',
            color: '#1877F2',
            bgGradient: 'from-blue-500/20 to-blue-600/10',
            description: '全球最大的社交网络'
        },
        {
            id: 'tiktok',
            name: 'TikTok',
            icon: 'fa-tiktok',
            color: '#ffffff',
            bgGradient: 'from-pink-500/20 to-purple-600/10',
            description: '短视频社交平台'
        },
        {
            id: 'instagram',
            name: 'Instagram',
            icon: 'fa-instagram',
            color: '#E4405F',
            bgGradient: 'from-pink-500/20 to-yellow-500/10',
            description: '图片社交分享平台'
        },
        {
            id: 'xiaohongshu',
            name: '小红书',
            icon: 'fa-book-open',
            color: '#FF2442',
            bgGradient: 'from-red-500/20 to-pink-600/10',
            description: '生活方式分享社区'
        },
        {
            id: 'weibo',
            name: '微博',
            icon: 'fa-weibo',
            color: '#E6162D',
            bgGradient: 'from-red-500/20 to-orange-500/10',
            description: '中文社交媒体平台'
        },
        {
            id: 'douyin',
            name: '抖音',
            icon: 'fa-music',
            color: '#00F2EA',
            bgGradient: 'from-cyan-500/20 to-blue-500/10',
            description: '字节跳动短视频平台'
        },
        {
            id: 'kuaishou',
            name: '快手',
            icon: 'fa-video',
            color: '#FF4906',
            bgGradient: 'from-orange-500/20 to-red-500/10',
            description: '短视频社交平台'
        }
    ],
    
    // 支持的电商平台
    SHOP_PLATFORMS: [
        {
            id: 'taobao',
            name: '淘宝',
            icon: 'fa-shopping-bag',
            color: '#FF5000',
            bgGradient: 'from-orange-500/20 to-red-500/10',
            description: '阿里巴巴C2C平台'
        },
        {
            id: 'pinduoduo',
            name: '拼多多',
            icon: 'fa-layer-group',
            color: '#E9232C',
            bgGradient: 'from-red-500/20 to-pink-500/10',
            description: '社交电商平台'
        },
        {
            id: 'douyin_shop',
            name: '抖音小店',
            icon: 'fa-store',
            color: '#00F2EA',
            bgGradient: 'from-cyan-500/20 to-blue-500/10',
            description: '抖音电商平台'
        },
        {
            id: 'shopify',
            name: 'Shopify',
            icon: 'fa-shopping-cart',
            color: '#96BF48',
            bgGradient: 'from-green-500/20 to-emerald-500/10',
            description: '跨境电商独立站平台'
        },
        {
            id: 'shopee',
            name: 'Shopee',
            icon: 'fa-sun',
            color: '#EE4D2D',
            bgGradient: 'from-orange-500/20 to-yellow-500/10',
            description: '东南亚电商平台'
        },
        {
            id: 'amazon',
            name: 'Amazon',
            icon: 'fa-amazon',
            color: '#FF9900',
            bgGradient: 'from-yellow-500/20 to-orange-500/10',
            description: '全球电商巨头'
        }
    ],
    
    // 分身模板
    AVATAR_TEMPLATES: [
        {
            id: 'tiktok',
            name: 'TikTok专家',
            icon: 'fa-tiktok',
            color: '#ff0050',
            skills: ['短视频创作', '热点分析', '内容策划', '账号运营']
        },
        {
            id: 'seo',
            name: 'SEO大师',
            icon: 'fa-search',
            color: '#4285f4',
            skills: ['关键词优化', '搜索引擎策略', '流量分析', '内容SEO']
        },
        {
            id: 'ecommerce',
            name: '电商专家',
            icon: 'fa-chart-line',
            color: '#34a853',
            skills: ['选品分析', '定价策略', '市场调研', '竞品分析']
        },
        {
            id: 'negotiation',
            name: '达人谈判',
            icon: 'fa-handshake',
            color: '#f59e0b',
            skills: ['KOL对接', '商务洽谈', '合作方案', '合同审核']
        },
        {
            id: 'general',
            name: '通用助手',
            icon: 'fa-robot',
            color: '#8b5cf6',
            skills: ['多场景支持', '日常辅助', '智能问答', '任务管理']
        }
    ],
    
    // 图片生成尺寸
    IMAGE_SIZES: [
        { value: '1024x1024', label: '1:1 正方形', ratio: '1:1' },
        { value: '1024x1792', label: '9:16 竖版', ratio: '9:16' },
        { value: '1792x1024', label: '16:9 横版', ratio: '16:9' }
    ],
    
    // 商品分类
    CATEGORIES: [
        { value: 'electronics', label: '电子产品' },
        { value: 'fashion', label: '服装鞋包' },
        { value: 'home', label: '家居用品' },
        { value: 'beauty', label: '美妆护肤' },
        { value: 'sports', label: '运动户外' },
        { value: 'toys', label: '母婴玩具' },
        { value: 'food', label: '食品饮料' },
        { value: 'books', label: '图书文具' }
    ],
    
    // 数据源
    DATA_SOURCES: [
        { value: 'alibaba', label: 'Alibaba', country: '全球' },
        { value: 'amazon', label: 'Amazon', country: '美国' },
        { value: 'ebay', label: 'eBay', country: '全球' },
        { value: 'etsy', label: 'Etsy', country: '美国' },
        { value: 'aliexpress', label: 'AliExpress', country: '全球' },
        { value: 'tiktok_shop', label: 'TikTok Shop', country: '东南亚' },
        { value: 'shopee', label: 'Shopee', country: '东南亚' }
    ]
};

// 初始化配置
function initConfig() {
    // 从localStorage读取API配置
    const savedConfig = localStorage.getItem('sellai_config');
    if (savedConfig) {
        try {
            const parsed = JSON.parse(savedConfig);
            if (parsed.baseUrl) {
                CONFIG.API.BASE_URL = parsed.baseUrl;
            }
            if (parsed.mockMode !== undefined) {
                CONFIG.MOCK.ENABLED = parsed.mockMode;
            }
        } catch (e) {
            console.error('Failed to parse saved config:', e);
        }
    }
    
    // 如果没有设置API地址，尝试自动检测
    if (!CONFIG.API.BASE_URL) {
        // 如果是本地访问，使用本地API
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            CONFIG.API.BASE_URL = `http://${window.location.hostname}:${window.location.port || '8000'}`;
        } else {
            // 否则使用备用API
            CONFIG.API.BASE_URL = CONFIG.API.BACKUP;
        }
    }
    
    // 更新Mock模式切换
    const mockToggle = document.getElementById('mock-mode-toggle');
    if (mockToggle) {
        mockToggle.checked = CONFIG.MOCK.ENABLED;
        mockToggle.addEventListener('change', (e) => {
            CONFIG.MOCK.ENABLED = e.target.checked;
            saveConfig();
            showToast(CONFIG.MOCK.ENABLED ? 'Mock模式已开启' : 'Mock模式已关闭', 'info');
        });
    }
}

// 保存配置到localStorage
function saveConfig() {
    localStorage.setItem('sellai_config', JSON.stringify({
        baseUrl: CONFIG.API.BASE_URL,
        mockMode: CONFIG.MOCK.ENABLED
    }));
}

// 保存API设置
function saveApiSettings() {
    const apiUrl = document.querySelector('#settings-api input[type="text"]')?.value;
    const apiKey = document.querySelector('#settings-api input[type="password"]')?.value;
    const mockMode = document.getElementById('mock-mode-toggle')?.checked;
    
    if (apiUrl) {
        CONFIG.API.BASE_URL = apiUrl;
    }
    if (mockMode !== undefined) {
        CONFIG.MOCK.ENABLED = mockMode;
    }
    
    saveConfig();
    showToast('API设置已保存', 'success');
    
    // 测试API连接
    testApiConnection();
}

// 测试API连接
async function testApiConnection() {
    try {
        const status = document.getElementById('api-status');
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span>
                <span class="text-gray-400">测试中...</span>
            `;
        }
        
        const response = await fetch(`${CONFIG.API.BASE_URL}/docs`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span class="text-gray-400">API正常</span>
            `;
        }
        showToast('API连接成功', 'success');
    } catch (error) {
        const status = document.getElementById('api-status');
        if (status) {
            status.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-red-500"></span>
                <span class="text-gray-400">API异常</span>
            `;
        }
        showToast('API连接失败，请检查地址', 'error');
    }
}

// API密钥可见性切换
function toggleApiKeyVisibility() {
    const input = document.getElementById('api-key-input');
    const icon = input.nextElementSibling.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', initConfig);
