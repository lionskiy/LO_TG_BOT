/**
 * Admin Administrators section (Phase 5).
 * List, add, refresh, delete service admins. API and main logic remain in app.js.
 */
(function () {
  document.addEventListener('DOMContentLoaded', () => {
    const addBtn = document.getElementById('adminsAddBtn');
    const addForm = document.getElementById('adminsAddForm');
    const cancelBtn = document.getElementById('adminsAddCancel');
    if (addBtn && addForm) {
      addBtn.addEventListener('click', () => {
        addForm.hidden = false;
      });
    }
    if (cancelBtn && addForm) {
      cancelBtn.addEventListener('click', () => {
        addForm.hidden = true;
      });
    }
  });
})();
