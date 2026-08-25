/**
 * SVIT Admin - Page 19: Library Overview Controller
 * Telemetry summary for central library operations.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        lucide.createIcons();
        loadLibraryOverviewStats();
    });

    async function loadLibraryOverviewStats() {
        try {
            // Fetch total books count
            const booksRes = await fetch('/admin/api/crud/library_books?limit=1');
            const booksData = await booksRes.json();
            const totalBooks = (booksData.status === 'success') ? booksData.total : 0;
            const booksEl = document.getElementById('libStatTotalBooks');
            if (booksEl) booksEl.innerText = totalBooks > 0 ? `${totalBooks}` : '0';

            // Fetch library members count
            const memRes = await fetch('/admin/api/crud/library_members?limit=1');
            const memData = await memRes.json();
            const totalMembers = (memData.status === 'success') ? memData.total : 0;
            const memEl = document.getElementById('libStatMembers');
            if (memEl) memEl.innerText = `${totalMembers}`;

            // Fetch active loans & overdue
            const loanRes = await fetch('/admin/api/crud/library_issue_return?limit=1000');
            const loanData = await loanRes.json();
            if (loanData.status === 'success' && loanData.items) {
                const today = new Date().toISOString().split('T')[0];
                const activeLoans = loanData.items.filter(l => l.status !== 'Returned');
                const overdueLoans = activeLoans.filter(l => l.due_date && l.due_date < today);

                const issuedEl = document.getElementById('libStatIssued');
                if (issuedEl) issuedEl.innerText = `${activeLoans.length} Books`;

                const overdueEl = document.getElementById('libStatOverdue');
                if (overdueEl) overdueEl.innerText = `${overdueLoans.length}`;
            }
        } catch (err) {
            console.error('Error fetching library stats:', err);
        }
    }
})();
