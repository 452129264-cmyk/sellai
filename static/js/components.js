function toggleMobileMenu() {
    const sidebar = document.getElementById('mobile-sidebar');
    if (!sidebar) return;
    const inner = sidebar.querySelector('div:last-child');
    if (inner) inner.classList.toggle('translate-x-full');
}

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function showCreateAvatarModal() { openModal('modal-create-avatar'); }

function toggleApiKeyVisibility() {
    const input = document.getElementById('api-key-input');
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}
