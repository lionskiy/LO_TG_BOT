/**
 * Admin Administrators section (Phase 5).
 * List, add, delete service admins. API and main logic remain in app.js.
 * Form is always visible; "+ Добавить" button removed.
 */
(function () {
  document.addEventListener('DOMContentLoaded', () => {
    const cancelBtn = document.getElementById('adminsAddCancel');
    const inputEl = document.getElementById('serviceAdminTelegramId');
    if (cancelBtn && inputEl) {
      cancelBtn.addEventListener('click', () => {
        inputEl.value = '';
      });
    }
  });
})();
