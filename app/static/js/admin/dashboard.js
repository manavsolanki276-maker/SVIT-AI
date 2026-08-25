/**
 * SVIT Admin - Page 1: Dashboard Controller
 * Real-time Chart.js telemetry, date formatting, and live counter refreshes.
 */

document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});

function initDashboard() {
    lucide.createIcons();
    displayCurrentDate();
    initAnalyticsChart();
}

function displayCurrentDate() {
    const dateEl = document.getElementById('currentDateDisplay');
    if (dateEl) {
        const options = { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' };
        dateEl.innerText = new Date().toLocaleDateString('en-US', options);
    }
}

function initAnalyticsChart() {
    const canvas = document.getElementById('overviewChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [
                {
                    label: 'Campus Activity & Queries',
                    data: [145, 210, 185, 290, 360, 310, 420],
                    borderColor: '#6366F1',
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                    pointBackgroundColor: '#6366F1',
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Active System Users',
                    data: [95, 140, 160, 210, 260, 230, 305],
                    borderColor: '#10B981',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [4, 4],
                    tension: 0.35,
                    pointBackgroundColor: '#10B981',
                    pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#9CA3AF', font: { size: 11, family: 'Inter' }, usePointStyle: true, boxWidth: 6 }
                },
                tooltip: {
                    backgroundColor: '#1E293B',
                    borderColor: '#334155',
                    borderWidth: 1,
                    titleColor: '#F8FAFC',
                    bodyColor: '#94A3B8',
                    padding: 10,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#6B7280', font: { size: 10, family: 'Inter' } }
                },
                y: {
                    grid: { color: '#1F2937' },
                    ticks: { color: '#6B7280', font: { size: 10, family: 'Inter' } }
                }
            }
        }
    });
}
