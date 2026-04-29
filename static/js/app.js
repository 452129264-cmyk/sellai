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

// 占位函数，防止 onclick 报错
async function generateImage() { alert('图片生成功能即将上线'); }
async function downloadAllImages() { alert('批量下载功能即将上线'); }
async function startOpportunityScan() {
    const data = await loadOpportunities();
    console.log('商机扫描结果', data);
}
async function createAvatar() {
    const name = document.getElementById('avatar-name')?.value?.trim();
    if (!name) return alert('请输入分身名称');
    const data = await sendMessage('1', `创建分身: ${name}`);
    console.log('创建分身', data);
    closeModal('modal-create-avatar');
}
async function bindSocialAccount() { alert('社媒绑定功能即将上线'); }
async function refreshSocialAccounts() { alert('刷新社媒账号'); }
async function bindShopAccount() { alert('店铺绑定功能即将上线'); }
async function refreshShopAccounts() { alert('刷新店铺账号'); }
async function testShopConnection() { alert('连接测试功能即将上线'); }
async function saveApiSettings() {
    const key = document.getElementById('api-key-input')?.value;
    console.log('保存 API 设置', key);
    alert('设置已保存');
}

// 初始化
window.addEventListener('DOMContentLoaded', () => {
    navigateTo('dashboard');
});
