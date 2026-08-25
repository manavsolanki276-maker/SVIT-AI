/**
 * SVIT Admin - Page 3: Roles & Permissions Matrix Controller
 * Interactive RBAC matrix visualizer, role filtering, and operation simulation.
 */

(function() {
    'use strict';

    const MODULES = [
        { key: 'students', label: 'Students', icon: 'users', category: 'academic' },
        { key: 'faculty', label: 'Faculty', icon: 'user-check', category: 'academic' },
        { key: 'timetable', label: 'Timetable', icon: 'calendar', category: 'academic' },
        { key: 'subjects', label: 'Subjects', icon: 'book', category: 'academic' },
        { key: 'rooms', label: 'Rooms & Campus', icon: 'map-pin', category: 'academic' },
        { key: 'placements', label: 'Placements', icon: 'briefcase', category: 'academic' },
        { key: 'academic_documents', label: 'Academic Documents (RAG)', icon: 'file-text', category: 'academic', hasUpload: true },
        { key: 'admission', label: 'Admission Info & Docs', icon: 'graduation-cap', category: 'admission', hasUpload: true, hasPublish: true },
        { key: 'notices', label: 'Notices & Announcements', icon: 'megaphone', category: 'notices', hasUpload: true, hasPublish: true },
        { key: 'events', label: 'College Events (Cultural/Tech)', icon: 'party-popper', category: 'events', hasUpload: true, hasPublish: true },
        { key: 'transport', label: 'Buses, Routes & Timings', icon: 'bus', category: 'bus', hasUpload: true },
        { key: 'library_books', label: 'Library Books & Members', icon: 'book-open', category: 'library', hasUpload: true },
        { key: 'library_issue_return', label: 'Issue / Return Records', icon: 'arrow-left-right', category: 'library' },
        { key: 'canteen', label: 'Canteen Menu & Food Items', icon: 'utensils', category: 'canteen', hasUpload: true },
        { key: 'sports', label: 'Sports & Grounds', icon: 'trophy', category: 'sports', hasUpload: true },
        { key: 'sports_events', label: 'Sports Tournaments', icon: 'medal', category: 'sports', hasUpload: true, hasPublish: true },
        { key: 'admin_management', label: 'Admin Accounts Management', icon: 'shield-check', category: 'super_admin' }
    ];

    const ROLE_RULES = {
        'super_admin': {
            name: 'Super Administrator',
            badge: 'Full Access',
            desc: 'Unrestricted master control across all administrative modules, credentials, RAG pipeline, and system configurations.',
            allowedCategories: ['*']
        },
        'academic_admin': {
            name: 'Academic Administrator',
            badge: 'Academic Scope',
            desc: 'Authority over students, professors, departmental timetable schedules, curriculum subjects, room allocations, placement drives, and academic PDF indexing.',
            allowedCategories: ['academic']
        },
        'admission_admin': {
            name: 'Admission Administrator',
            badge: 'Admissions Scope',
            desc: 'Manages program seat matrices, cutoff merit brochures, admission counselling circulars, and helpline directories.',
            allowedCategories: ['admission']
        },
        'notice_admin': {
            name: 'Notice & Announcement Admin',
            badge: 'Circulars & Alerts',
            desc: 'Publishes campus-wide urgent weather advisories, holiday circulars, class cancellations, and emergency push alerts.',
            allowedCategories: ['notices']
        },
        'event_admin': {
            name: 'College Event Administrator',
            badge: 'Cultural & Tech Fests',
            desc: 'Organizes tech hackathons, annual cultural fests, seminars, and club workshops. Explicitly restricted from Sports.',
            allowedCategories: ['events']
        },
        'bus_admin': {
            name: 'Bus & Transport Admin',
            badge: 'Transit Fleet',
            desc: 'Controls college bus fleets, route stops, departure timings, and driver contact assignments.',
            allowedCategories: ['bus']
        },
        'library_admin': {
            name: 'Central Library Admin',
            badge: 'Library & Catalog',
            desc: 'Manages library book accession catalog, card memberships, lending transactions, overdue returns, and reading hall guidelines.',
            allowedCategories: ['library']
        },
        'canteen_admin': {
            name: 'Canteen & Cafeteria Admin',
            badge: 'Food & Menu',
            desc: 'Manages daily breakfast/lunch menus, food item pricing, vegetarian classifications, and stall operational timings.',
            allowedCategories: ['canteen']
        },
        'sports_admin': {
            name: 'Sports & Athletics Admin',
            badge: 'Athletics & Grounds',
            desc: 'Coordinates inter-departmental tournaments, cricket grounds, indoor sports arenas, and athletic meets. Explicitly restricted from General Events.',
            allowedCategories: ['sports']
        }
    };

    let selectedRole = 'super_admin';

    document.addEventListener('DOMContentLoaded', function() {
        initMatrix();
    });

    function initMatrix() {
        lucide.createIcons();
        bindRoleButtons();
        renderRoleDetails(selectedRole);
        renderMatrixTable(selectedRole);
    }

    function bindRoleButtons() {
        const buttons = document.querySelectorAll('.role-pill-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedRole = btn.getAttribute('data-role');
                renderRoleDetails(selectedRole);
                renderMatrixTable(selectedRole);
            });
        });
    }

    function renderRoleDetails(roleKey) {
        const role = ROLE_RULES[roleKey];
        if (!role) return;

        const titleEl = document.getElementById('selectedRoleTitle');
        const descEl = document.getElementById('selectedRoleDesc');
        const badgeEl = document.getElementById('selectedRoleBadge');

        if (titleEl) titleEl.innerText = role.name;
        if (descEl) descEl.innerText = role.desc;
        if (badgeEl) badgeEl.innerText = role.badge;
    }

    function isAllowed(roleKey, modCategory, action) {
        if (roleKey === 'super_admin') return true;
        const role = ROLE_RULES[roleKey];
        if (!role) return false;

        const hasCatAccess = role.allowedCategories.includes(modCategory);
        if (!hasCatAccess) return false;

        // All standard operations within allowed category are granted
        return true;
    }

    function renderMatrixTable(roleKey) {
        const tbody = document.getElementById('matrixTableBody');
        if (!tbody) return;

        tbody.innerHTML = MODULES.map(mod => {
            const canView = isAllowed(roleKey, mod.category, 'view');
            const canCreate = isAllowed(roleKey, mod.category, 'create');
            const canEdit = isAllowed(roleKey, mod.category, 'edit');
            const canDelete = isAllowed(roleKey, mod.category, 'delete');
            const canUpload = mod.hasUpload ? isAllowed(roleKey, mod.category, 'upload') : null;
            const canPublish = mod.hasPublish ? isAllowed(roleKey, mod.category, 'publish') : null;

            return `
                <tr>
                    <td>
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                                <i data-lucide="${mod.icon}" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-xs font-bold text-white mb-0">${mod.label}</p>
                                <span class="text-[10px] text-gray-500 font-mono">${mod.key}</span>
                            </div>
                        </div>
                    </td>
                    <td class="text-center">${canView ? permCheckIcon() : permCrossIcon()}</td>
                    <td class="text-center">${canCreate ? permCheckIcon() : permCrossIcon()}</td>
                    <td class="text-center">${canEdit ? permCheckIcon() : permCrossIcon()}</td>
                    <td class="text-center">${canDelete ? permCheckIcon() : permCrossIcon()}</td>
                    <td class="text-center">${canUpload === null ? '<span class="text-gray-600 text-xs">-</span>' : (canUpload ? permCheckIcon() : permCrossIcon())}</td>
                    <td class="text-center">${canPublish === null ? '<span class="text-gray-600 text-xs">-</span>' : (canPublish ? permCheckIcon() : permCrossIcon())}</td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    }

    function permCheckIcon() {
        return `<span class="perm-badge-allowed" title="Allowed"><i data-lucide="check" class="w-3.5 h-3.5"></i></span>`;
    }

    function permCrossIcon() {
        return `<span class="perm-badge-denied" title="Denied"><i data-lucide="x" class="w-3.5 h-3.5"></i></span>`;
    }
})();
