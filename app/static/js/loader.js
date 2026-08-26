/**
 * SVIT AI Assistant — Premium Global & Inline Loader Controller
 * Component: SVITLoader
 * Clean minimal loader with SVIT Logo & Animated SVIT AI Brand Text.
 * Supports automatic lifecycle during API data loading.
 */

(function (window, document) {
    'use strict';

    const LOADER_ID = 'svit-global-loader';

    let loaderEl = null;
    let failsafeTimer = null;
    let hideTimer = null;
    let isInitialized = false;
    let activeApiRequests = 0;

    function getLoaderElement() {
        if (!loaderEl) {
            loaderEl = document.getElementById(LOADER_ID);
        }
        return loaderEl;
    }

    function ensureLoaderMarkup() {
        if (getLoaderElement()) return;

        const loader = document.createElement('div');
        loader.id = LOADER_ID;
        loader.className = 'svit-global-loader is-hidden';
        loader.style.display = 'none';
        loader.setAttribute('role', 'status');
        loader.setAttribute('aria-live', 'polite');
        loader.setAttribute('aria-label', 'SVIT AI Loading');

        loader.innerHTML = `
            <div class="svit-loader-stage">
                <div class="svit-loader-logo-wrapper">
                    <img src="/static/logo/svit%20logo%20u.png" alt="SVIT Logo" class="svit-loader-logo-img" onerror="this.style.display='none'">
                </div>
                <div class="svit-loader-branding">
                    <h1 class="svit-loader-title">
                        <span class="svit-brand-animated" aria-label="SVIT AI">
                            <span class="svit-brand-word svit-word-svit" aria-hidden="true">
                                <span class="svit-char" style="--char-idx: 0;">S</span>
                                <span class="svit-char" style="--char-idx: 1;">V</span>
                                <span class="svit-char" style="--char-idx: 2;">I</span>
                                <span class="svit-char" style="--char-idx: 3;">T</span>
                            </span>
                            <span class="svit-brand-space" aria-hidden="true">&nbsp;</span>
                            <span class="svit-brand-word svit-word-ai" aria-hidden="true">
                                <span class="svit-char svit-char-accent" style="--char-idx: 4;">A</span>
                                <span class="svit-char svit-char-accent" style="--char-idx: 5;">I</span>
                            </span>
                        </span>
                    </h1>
                </div>
            </div>
        `;

        if (document.body) {
            document.body.prepend(loader);
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                document.body.prepend(loader);
            });
        }
        loaderEl = loader;
    }

    /**
     * Shows the global loader screen on demand
     * @param {number} [timeoutMs=3500] - Optional custom failsafe timeout in ms
     */
    function show(timeoutMs) {
        ensureLoaderMarkup();
        const el = getLoaderElement();
        if (!el) return;

        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }

        if (failsafeTimer) {
            clearTimeout(failsafeTimer);
        }

        el.style.display = 'flex';
        el.style.pointerEvents = 'auto';
        void el.offsetHeight;
        el.classList.remove('is-hidden');
        el.classList.add('is-active');
        el.setAttribute('aria-hidden', 'false');

        const limit = typeof timeoutMs === 'number' ? timeoutMs : 3500;
        failsafeTimer = setTimeout(() => {
            hide(0);
        }, limit);
    }

    /**
     * Hides the global loader screen immediately
     * @param {number} [delayMs=0] - Delay before fade out
     */
    function hide(delayMs) {
        const el = getLoaderElement();
        if (!el) return;

        if (failsafeTimer) {
            clearTimeout(failsafeTimer);
            failsafeTimer = null;
        }

        const delay = typeof delayMs === 'number' ? delayMs : 0;

        hideTimer = setTimeout(() => {
            el.classList.remove('is-active');
            el.classList.add('is-hidden');
            el.setAttribute('aria-hidden', 'true');
            el.style.pointerEvents = 'none';
            el.style.display = 'none';
        }, delay);
    }

    function setLoading(isLoading) {
        if (isLoading) {
            show();
        } else {
            hide(0);
        }
    }

    /**
     * Renders inline SVIT animated branding for tables and cards
     */
    function renderInline() {
        return `
            <div class="svit-inline-loader flex flex-col items-center justify-center p-3">
                <div class="svit-loader-logo-wrapper" style="width: 46px; height: 46px; min-width: 46px; min-height: 46px; margin-bottom: 8px; border-radius: 12px; padding: 5px;">
                    <img src="/static/logo/svit%20logo%20u.png" alt="SVIT Logo" class="svit-loader-logo-img" onerror="this.style.display='none'">
                </div>
                <div class="svit-loader-branding">
                    <span class="svit-brand-animated" aria-label="SVIT AI">
                        <span class="svit-brand-word svit-word-svit" aria-hidden="true">
                            <span class="svit-char" style="--char-idx: 0;">S</span>
                            <span class="svit-char" style="--char-idx: 1;">V</span>
                            <span class="svit-char" style="--char-idx: 2;">I</span>
                            <span class="svit-char" style="--char-idx: 3;">T</span>
                        </span>
                        <span class="svit-brand-space" aria-hidden="true">&nbsp;</span>
                        <span class="svit-brand-word svit-word-ai" aria-hidden="true">
                            <span class="svit-char svit-char-accent" style="--char-idx: 4;">A</span>
                            <span class="svit-char svit-char-accent" style="--char-idx: 5;">I</span>
                        </span>
                    </span>
                </div>
            </div>
        `;
    }

    /**
     * Intercepts API fetch calls to automatically show/hide SVITLoader during data loading
     */
    function enableAutoApiLoader() {
        if (!window.fetch || window._svitFetchIntercepted) return;
        window._svitFetchIntercepted = true;

        const originalFetch = window.fetch;
        window.fetch = function () {
            const args = arguments;
            const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
            
            // Auto-display loader for admin CRUD and data API calls
            const isApi = url.includes('/admin/api/') || url.includes('/api/crud/');
            
            if (isApi) {
                activeApiRequests++;
                if (activeApiRequests === 1) {
                    show(4000);
                }
            }

            return originalFetch.apply(this, args)
                .finally(() => {
                    if (isApi) {
                        activeApiRequests = Math.max(0, activeApiRequests - 1);
                        if (activeApiRequests === 0) {
                            hide(80);
                        }
                    }
                });
        };
    }

    /**
     * Checks if the student just logged in and displays the loader during the login -> chat page transition
     */
    function checkLoginTransition() {
        try {
            const isTransitioning = sessionStorage.getItem('svit_student_just_logged_in');
            if (isTransitioning === 'true') {
                const path = window.location.pathname;
                // If on student chat/home page, show loader during transition then smoothly hide
                if (path === '/' || path === '/student/chat' || path === '/chat' || path === '') {
                    show(4000);
                    setTimeout(() => {
                        hide(350);
                        sessionStorage.removeItem('svit_student_just_logged_in');
                    }, 900);
                } else if (path.includes('/login') || path.includes('/auth/login')) {
                    // Still on login (e.g. error or refresh), clear and hide
                    sessionStorage.removeItem('svit_student_just_logged_in');
                    hide(0);
                }
            }
        } catch (e) {}
    }

    function init() {
        if (isInitialized) return;
        isInitialized = true;

        const el = getLoaderElement();
        if (el) {
            el.classList.remove('is-active');
            el.classList.add('is-hidden');
            el.style.display = 'none';
        }

        enableAutoApiLoader();
        checkLoginTransition();
    }

    // Initialize immediately
    init();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    }

    window.SVITLoader = {
        show: show,
        hide: hide,
        setLoading: setLoading,
        renderInline: renderInline,
        init: init
    };

})(window, document);
