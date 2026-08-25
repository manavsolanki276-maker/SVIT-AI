/**
 * SVIT Admin - Page 4: Profile & Settings Controller
 * Handles profile data validation, change password form, and session management.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        lucide.createIcons();
        initPasswordChangeForm();
    });

    function initPasswordChangeForm() {
        const form = document.getElementById('changePasswordForm');
        if (!form) return;

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const currentPass = document.getElementById('currentPassword').value.trim();
            const newPass = document.getElementById('newPassword').value.trim();
            const confirmPass = document.getElementById('confirmPassword').value.trim();

            if (!currentPass || !newPass || !confirmPass) {
                showAdminToast('Please fill in all password fields.', 'error');
                return;
            }

            if (newPass.length < 6) {
                showAdminToast('New password must be at least 6 characters.', 'error');
                return;
            }

            if (newPass !== confirmPass) {
                showAdminToast('New passwords do not match.', 'error');
                return;
            }

            const btn = document.getElementById('savePasswordBtn');
            const spinner = document.getElementById('savePassSpinner');
            if (btn) btn.disabled = true;
            if (spinner) spinner.classList.remove('hidden');

            try {
                // Submit to admin reset password API
                const adminId = form.getAttribute('data-admin-id') || 'me';
                const res = await fetch(`/admin/api/admins/${adminId}/reset-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        current_password: currentPass,
                        new_password: newPass
                    })
                });

                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showAdminToast('Password updated successfully! Please keep it secure.', 'success');
                    form.reset();
                } else {
                    showAdminToast(data.message || 'Failed to update password.', 'error');
                }
            } catch (err) {
                showAdminToast(err.message, 'error');
            } finally {
                if (btn) btn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
            }
        });
    }
})();
