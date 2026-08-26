/**
 * SVIT AI — Single Master Theme & Brand Animation Manager
 * Unified Premium Theme for Student + Admin Portals
 * There is only ONE theme (Light SVIT Theme).
 */

(function (window, document) {
    'use strict';

    // Clear any obsolete dark mode preference from localStorage
    try {
        localStorage.removeItem('svit_theme');
        localStorage.removeItem('svit_admin_theme');
        localStorage.setItem('svit_theme', 'light');
        localStorage.setItem('svit_admin_theme', 'light');
    } catch (e) {}

    function enforceSingleTheme() {
        const root = document.documentElement;
        if (!root) return;

        root.classList.remove('dark');
        root.classList.add('light');
        root.setAttribute('data-theme', 'light');
        root.setAttribute('data-admin-theme', 'light');
        root.dataset.theme = 'light';
        root.dataset.adminTheme = 'light';

        if (document.body) {
            document.body.classList.remove('dark', 'dark-mode');
            document.body.classList.add('light-mode');
        }
    }

    /**
     * Initializes the SVIT AI sequential character brand text reveal
     * S -> V -> I -> T -> [pause] -> A -> I
     */
    function initBrandTextAnimation(root) {
        // Respect accessibility preference
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const scope = root || document;
        const selector = '[data-svit-brand], .svit-brand-auto, .sidebar-brand h3, .brand-info h3, .mobile-brand-name, .settings-brand span, .portal-brand span';
        const brandElements = scope.querySelectorAll(selector);

        brandElements.forEach(el => {
            if (el.dataset.brandAnimated === 'true' || el.querySelector('.svit-brand-animated')) {
                return;
            }

            const rawText = el.textContent.trim();
            if (/^SVIT(\s+AI)?(\s+Assistant|\s+Settings)?$/i.test(rawText)) {
                const wrapper = document.createElement('span');
                wrapper.className = 'svit-brand-animated';
                wrapper.setAttribute('aria-label', rawText);

                const hasAi = /AI/i.test(rawText);
                const hasAssistant = /Assistant/i.test(rawText);
                const hasSettings = /Settings/i.test(rawText);

                let innerHTML = `
                    <span class="svit-brand-word svit-word-svit" aria-hidden="true">
                        <span class="svit-char" style="--char-idx: 0;">S</span>
                        <span class="svit-char" style="--char-idx: 1;">V</span>
                        <span class="svit-char" style="--char-idx: 2;">I</span>
                        <span class="svit-char" style="--char-idx: 3;">T</span>
                    </span>
                `;

                if (hasAi) {
                    innerHTML += `
                        <span class="svit-brand-space" aria-hidden="true">&nbsp;</span>
                        <span class="svit-brand-word svit-word-ai" aria-hidden="true">
                            <span class="svit-char svit-char-accent" style="--char-idx: 4;">A</span>
                            <span class="svit-char svit-char-accent" style="--char-idx: 5;">I</span>
                        </span>
                    `;
                }

                if (hasAssistant) {
                    innerHTML += `<span class="svit-brand-space" aria-hidden="true">&nbsp;</span><span class="svit-brand-suffix" aria-hidden="true">Assistant</span>`;
                } else if (hasSettings) {
                    innerHTML += `<span class="svit-brand-space" aria-hidden="true">&nbsp;</span><span class="svit-brand-suffix" aria-hidden="true">Settings</span>`;
                }

                wrapper.innerHTML = innerHTML;
                el.innerHTML = '';
                el.appendChild(wrapper);
                el.dataset.brandAnimated = 'true';
            }
        });
    }

    // Run immediately and on DOM load
    enforceSingleTheme();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            enforceSingleTheme();
            initBrandTextAnimation();
        });
    } else {
        initBrandTextAnimation();
    }

    // Safe API stubs to maintain backwards compatibility without dark mode
    window.svitTheme = {
        getTheme: function () { return 'light'; },
        setTheme: function () { enforceSingleTheme(); },
        toggleTheme: function () { enforceSingleTheme(); },
        initTheme: function () { enforceSingleTheme(); }
    };

    window.setTheme = function () { enforceSingleTheme(); };
    window.setAdminTheme = function () { enforceSingleTheme(); };
    window.applyTheme = function () { enforceSingleTheme(); };
    window.initTheme = function () { enforceSingleTheme(); };
    window.initSVITBrandAnimation = initBrandTextAnimation;

})(window, document);
