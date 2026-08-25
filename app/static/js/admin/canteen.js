/**
 * SVIT Admin - Page 23: Canteen Overview Controller
 * Overview statistics and operational status.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        lucide.createIcons();
        loadCanteenOverviewStats();
    });

    async function loadCanteenOverviewStats() {
        try {
            const res = await fetch('/admin/api/crud/canteen?limit=1');
            const data = await res.json();
            const total = (data.status === 'success') ? data.total : 0;
            const el = document.getElementById('canteenStatMenuItems');
            if (el) el.innerText = total > 0 ? `${total} Dishes` : '0 Dishes';
        } catch (err) {
            console.error('Error fetching canteen stats:', err);
        }
    }
})();
