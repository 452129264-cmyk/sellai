/**
 * SellAI Frontend - Mock Data
 * 模拟数据用于离线预览
 */

const MOCK_DATA = {
    // 统计数据
    stats: {
        todayOpportunities: 12,
        activeAvatars: 2,
        boundShops: 3,
        socialAccounts: 4
    },
    
    // 社媒账号
    socialAccounts: [
        {
            id: '1',
            platform: 'tiktok',
            account_name: 'Fashion Trends',
            status: 'active',
            followers: '125.6K',
            bound_at: '2024-01-15T10:30:00Z'
        },
        {
            id: '2',
            platform: 'instagram',
            account_name: 'Style Hub Official',
            status: 'active',
            followers: '89.2K',
            bound_at: '2024-01-10T08:00:00Z'
        },
        {
            id: '3',
            platform: 'xiaohongshu',
            account_name: '种草小能手',
            status: 'active',
            followers: '45.8K',
            bound_at: '2024-02-01T14:20:00Z'
        }
    ],
    
    // 店铺账号
    shopAccounts: [
        {
            id: '1',
            platform: 'shopify',
            shop_name: 'My Fashion Store',
            shop_id: 'shop_001',
            status: 'active',
            products: 156,
            bound_at: '2024-01-05T09:00:00Z'
        },
        {
            id: '2',
            platform: 'amazon',
            shop_name: 'Global Goods',
            shop_id: 'amazon_001',
            status: 'active',
            products: 89,
            bound_at: '2024-01-08T11:30:00Z'
        },
        {
            id: '3',
            platform: 'shopee',
            shop_name: '东南亚精选',
            shop_id: 'shopee_001',
            status: 'active',
            products: 234,
            bound_at: '2024-01-20T16:00:00Z'
        }
    ],
    
    // 商机列表
    opportunities: [
        {
            id: 'opp_001',
            product_name: '无线蓝牙耳机 Pro',
            category: 'electronics',
            source: 'alibaba',
            cost_price: 28.50,
            sell_price: 89.00,
            margin: 68.0,
            platform: 'Amazon',
            trend: 'up',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=10'
        },
        {
            id: 'opp_002',
            product_name: '智能手表 Fitness Band',
            category: 'electronics',
            source: 'alibaba',
            cost_price: 35.00,
            sell_price: 129.00,
            margin: 72.9,
            platform: 'Shopee',
            trend: 'up',
            competition: 'low',
            image: 'https://picsum.photos/200/200?random=11'
        },
        {
            id: 'opp_003',
            product_name: '便携式加湿器 USB',
            category: 'home',
            source: 'aliexpress',
            cost_price: 8.50,
            sell_price: 28.00,
            margin: 69.6,
            platform: 'Amazon',
            trend: 'stable',
            competition: 'high',
            image: 'https://picsum.photos/200/200?random=12'
        },
        {
            id: 'opp_004',
            product_name: '瑜伽健身服套装',
            category: 'sports',
            source: 'alibaba',
            cost_price: 15.00,
            sell_price: 49.00,
            margin: 69.4,
            platform: 'TikTok Shop',
            trend: 'up',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=13'
        },
        {
            id: 'opp_005',
            product_name: '迷你筋膜枪',
            category: 'sports',
            source: 'alibaba',
            cost_price: 22.00,
            sell_price: 69.00,
            margin: 68.1,
            platform: 'Shopee',
            trend: 'up',
            competition: 'low',
            image: 'https://picsum.photos/200/200?random=14'
        },
        {
            id: 'opp_006',
            product_name: 'LED化妆镜 带灯光',
            category: 'beauty',
            source: 'alibaba',
            cost_price: 12.00,
            sell_price: 38.00,
            margin: 68.4,
            platform: 'Etsy',
            trend: 'stable',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=15'
        },
        {
            id: 'opp_007',
            product_name: '儿童益智玩具套装',
            category: 'toys',
            source: 'alibaba',
            cost_price: 18.00,
            sell_price: 55.00,
            margin: 67.3,
            platform: 'Amazon',
            trend: 'up',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=16'
        },
        {
            id: 'opp_008',
            product_name: '旅行收纳包套装',
            category: 'fashion',
            source: 'aliexpress',
            cost_price: 6.50,
            sell_price: 22.00,
            margin: 70.5,
            platform: 'Shopee',
            trend: 'stable',
            competition: 'high',
            image: 'https://picsum.photos/200/200?random=17'
        },
        {
            id: 'opp_009',
            product_name: '多功能厨房小工具',
            category: 'home',
            source: 'alibaba',
            cost_price: 4.50,
            sell_price: 18.00,
            margin: 75.0,
            platform: 'TikTok Shop',
            trend: 'up',
            competition: 'low',
            image: 'https://picsum.photos/200/200?random=18'
        },
        {
            id: 'opp_010',
            product_name: '男士运动背包',
            category: 'fashion',
            source: 'alibaba',
            cost_price: 20.00,
            sell_price: 65.00,
            margin: 69.2,
            platform: 'Shopee',
            trend: 'stable',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=19'
        },
        {
            id: 'opp_011',
            product_name: '无线充电器 15W快充',
            category: 'electronics',
            source: 'alibaba',
            cost_price: 9.00,
            sell_price: 32.00,
            margin: 71.9,
            platform: 'Amazon',
            trend: 'up',
            competition: 'high',
            image: 'https://picsum.photos/200/200?random=20'
        },
        {
            id: 'opp_012',
            product_name: '防晒霜 SPF50+ 户外',
            category: 'beauty',
            source: 'alibaba',
            cost_price: 3.50,
            sell_price: 15.00,
            margin: 76.7,
            platform: 'Shopee',
            trend: 'up',
            competition: 'medium',
            image: 'https://picsum.photos/200/200?random=21'
        }
    ],
    
    // 通知列表
    notifications: [
        {
            id: '1',
            type: 'opportunity',
            title: '发现高毛利商机',
            message: '无线蓝牙耳机 Pro 毛利达 68%',
            time: '5分钟前',
            read: false
        },
        {
            id: '2',
            type: 'system',
            title: '分身运行通知',
            message: 'TikTok专家 分身已开始运行',
            time: '30分钟前',
            read: false
        },
        {
            id: '3',
            type: 'alert',
            title: '平台绑定成功',
            message: 'Instagram 账号绑定成功',
            time: '2小时前',
            read: true
        }
    ],
    
    // 分身列表
    avatars: [
        {
            id: 'avatar_001',
            name: 'TikTok运营助手',
            template: 'tiktok',
            status: 'running',
            tasks_completed: 156,
            created_at: '2024-01-10T10:00:00Z',
            last_active: '2024-03-10T14:30:00Z'
        },
        {
            id: 'avatar_002',
            name: '选品分析师',
            template: 'ecommerce',
            status: 'running',
            tasks_completed: 89,
            created_at: '2024-01-15T09:00:00Z',
            last_active: '2024-03-10T14:25:00Z'
        },
        {
            id: 'avatar_003',
            name: 'SEO优化专家',
            template: 'seo',
            status: 'stopped',
            tasks_completed: 234,
            created_at: '2024-02-01T11:00:00Z',
            last_active: '2024-03-09T18:00:00Z'
        }
    ],
    
    // 商机分析结果
    opportunityAnalysis: {
        product_name: '',
        suggested_price: 0,
        target_platform: 'Amazon',
        competition_level: 'medium',
        pricing_strategy: 'premium',
        keywords: ['wireless', 'bluetooth', 'earphones', 'noise-canceling'],
        similar_products: 45,
        monthly_sales_estimate: '2,000-5,000 units',
        recommendation: '建议定价在 $79-99 区间，毛利率可达 65-72%'
    },
    
    // 图片生成历史
    imageHistory: []
};

// 生成随机ID
function generateId(prefix = 'id') {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// 获取平台信息
function getPlatformInfo(platformId, type = 'social') {
    const platforms = type === 'social' ? CONFIG.SOCIAL_PLATFORMS : CONFIG.SHOP_PLATFORMS;
    return platforms.find(p => p.id === platformId) || null;
}

// 检查平台是否已绑定
function isPlatformBound(platformId, type = 'social') {
    if (type === 'social') {
        return MOCK_DATA.socialAccounts.some(a => a.platform === platformId);
    } else {
        return MOCK_DATA.shopAccounts.some(s => s.platform === platformId);
    }
}

// 获取绑定的账号
function getBoundAccount(platformId, type = 'social') {
    if (type === 'social') {
        return MOCK_DATA.socialAccounts.find(a => a.platform === platformId);
    } else {
        return MOCK_DATA.shopAccounts.find(s => s.platform === platformId);
    }
}

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// 格式化相对时间
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return formatDate(dateString);
}

// 获取毛利等级
function getMarginLevel(margin) {
    if (margin >= 60) return 'high';
    if (margin >= 40) return 'medium';
    return 'low';
}

// 获取毛利颜色
function getMarginColor(margin) {
    if (margin >= 60) return '#22c55e';
    if (margin >= 40) return '#facc15';
    return '#fb923c';
}

// 获取趋势图标
function getTrendIcon(trend) {
    switch (trend) {
        case 'up': return 'fa-arrow-up text-green-400';
        case 'down': return 'fa-arrow-down text-red-400';
        default: return 'fa-minus text-gray-400';
    }
}

// 获取趋势文本
function getTrendText(trend) {
    switch (trend) {
        case 'up': return '上升趋势';
        case 'down': return '下降趋势';
        default: return '平稳';
    }
}
