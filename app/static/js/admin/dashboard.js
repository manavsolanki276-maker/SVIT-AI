/**
 * SVIT Admin - Page 1: Dashboard Controller
 * Real-time Chart.js telemetry, date formatting, and live counter refreshes.
 * Single Premium Light SVIT Theme Palette
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
    const loader = document.getElementById('chartLoader');
    if (loader) {
        loader.classList.add('is-hidden');
        loader.style.display = 'none';
    }
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Lavender-Purple gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(139, 92, 246, 0.22)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

    try {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {
                        label: 'Campus Activity & Queries',
                        data: [145, 210, 185, 290, 360, 310, 420],
                        borderColor: '#8B5CF6',
                        backgroundColor: gradient,
                        borderWidth: 2.5,
                        tension: 0.35,
                        fill: true,
                        pointBackgroundColor: '#8B5CF6',
                        pointBorderColor: '#FFFFFF',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Active System Users',
                        data: [95, 140, 160, 210, 260, 230, 305],
                        borderColor: '#16A34A',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [4, 4],
                        tension: 0.35,
                        pointBackgroundColor: '#16A34A',
                        pointBorderColor: '#FFFFFF',
                        pointBorderWidth: 2,
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
                        labels: { color: '#66708F', font: { size: 11, family: 'Inter', weight: '600' }, usePointStyle: true, boxWidth: 6 }
                    },
                    tooltip: {
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E1E5F0',
                        borderWidth: 1,
                        titleColor: '#171D3A',
                        bodyColor: '#66708F',
                        padding: 10,
                        cornerRadius: 10,
                        boxShadow: '0 4px 20px rgba(23, 29, 58, 0.1)'
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8C95AD', font: { size: 10, family: 'Inter' } }
                    },
                    y: {
                        grid: { color: '#E1E5F0' },
                        ticks: { color: '#8C95AD', font: { size: 10, family: 'Inter' } }
                    }
                }
            }
        });
    } catch (e) {
        console.error('[SVIT Dashboard] Chart init error:', e);
    }
}
