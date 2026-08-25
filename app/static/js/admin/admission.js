/**
 * SVIT Admin - Page 12: Admission CMS Controller (4 Tabs)
 * 1. Programs & Seats
 * 2. Cutoff & Eligibility
 * 3. Admission Steps / Guidelines
 * 4. Admission Helpdesk & Contact
 */

(function() {
    'use strict';

    const state = {
        activeTab: 'programs',
        search: '',
        items: [],
        pendingDeleteId: null,
        uploadedDocData: null
    };

    let admissionModal = null;
    let deleteModal = null;
    let searchDebounce = null;

    document.addEventListener('DOMContentLoaded', function() {
        const modalEl = document.getElementById('admissionModal');
        const delEl = document.getElementById('admissionDeleteModal');

        if (modalEl) admissionModal = new bootstrap.Modal(modalEl);
        if (delEl) deleteModal = new bootstrap.Modal(delEl);

        bindEvents();
        setupBrochureUpload();
        loadAdmissionData();
    });

    function bindEvents() {
        const tabs = document.querySelectorAll('.adm-nav-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                state.activeTab = tab.getAttribute('data-tab');
                renderTabContent();
            });
        });

        const searchInput = document.getElementById('admissionSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.search = e.target.value.trim().toLowerCase();
                    renderTabContent();
                }, 300);
            });
        }

        const refreshBtn = document.getElementById('refreshAdmissionBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadAdmissionData);

        const createBtn = document.getElementById('openCreateAdmissionModalBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                document.getElementById('admModalTitle').innerText = 'Add Admission Info / Program';
                document.getElementById('admFormRecordId').value = '';
                document.getElementById('admissionForm').reset();
                state.uploadedDocData = null;
                resetDocPreview();
                admissionModal.show();
            });
        }

        const form = document.getElementById('admissionForm');
        if (form) form.addEventListener('submit', handleAdmissionFormSubmit);

        const confirmDeleteBtn = document.getElementById('confirmDeleteAdmBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function setupBrochureUpload() {
        const dropZone = document.getElementById('admBrochureDropZone');
        const fileInput = document.getElementById('admBrochureInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-emerald-500'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-emerald-500'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-emerald-500');
                if (e.dataTransfer.files.length) uploadBrochure(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) uploadBrochure(e.target.files[0]);
            });
        }
    }

    async function uploadBrochure(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'pdf');

        const preview = document.getElementById('admBrochurePreviewContainer');
        if (preview) {
            preview.innerHTML = '<span class="text-xs text-emerald-400">Uploading brochure...</span>';
            preview.classList.remove('hidden');
        }

        try {
            const res = await fetch('/admin/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                state.uploadedDocData = data.file;
                if (preview) {
                    preview.innerHTML = `
                        <div class="flex items-center gap-2 p-2 rounded-lg bg-[#0F172A] border border-emerald-500 text-xs text-white">
                            <i data-lucide="file-text" class="w-4 h-4 text-emerald-400"></i>
                            <span>${data.file.file_name}</span>
                        </div>
                    `;
                    lucide.createIcons();
                }
                showAdminToast('Admission brochure uploaded.', 'success');
            } else {
                showAdminToast(data.message || 'Upload failed.', 'error');
                resetDocPreview();
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
            resetDocPreview();
        }
    }

    function resetDocPreview() {
        const preview = document.getElementById('admBrochurePreviewContainer');
        if (preview) {
            preview.innerHTML = '';
            preview.classList.add('hidden');
        }
    }

    async function loadAdmissionData() {
        const container = document.getElementById('admissionContentArea');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center py-12 text-gray-400 text-xs">
                <div class="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Loading admission CMS database...
            </div>
        `;

        try {
            const res = await fetch('/admin/api/crud/admission?limit=500');
            const data = await res.json();
            if (data.status === 'success') {
                state.items = data.items || [];
                renderTabContent();
            } else {
                container.innerHTML = `<div class="text-center py-6 text-red-400 text-xs">${data.message}</div>`;
            }
        } catch (err) {
            container.innerHTML = `<div class="text-center py-6 text-red-400 text-xs">${err.message}</div>`;
        }
        lucide.createIcons();
    }

    function renderTabContent() {
        const container = document.getElementById('admissionContentArea');
        if (!container) return;

        const countBadge = document.getElementById('admissionCountBadge');
        if (countBadge) countBadge.innerText = `${state.items.length} Entries`;

        const filterItems = state.items.filter(it => {
            if (!state.search) return true;
            return (it.program || '').toLowerCase().includes(state.search) ||
                   (it.title || '').toLowerCase().includes(state.search) ||
                   (it.department || '').toLowerCase().includes(state.search);
        });

        if (state.activeTab === 'programs') {
            renderProgramsTab(filterItems, container);
        } else if (state.activeTab === 'cutoff') {
            renderCutoffTab(filterItems, container);
        } else if (state.activeTab === 'steps') {
            renderStepsTab(filterItems, container);
        } else if (state.activeTab === 'helpdesk') {
            renderHelpdeskTab(filterItems, container);
        }

        lucide.createIcons();
    }

    function renderProgramsTab(items, container) {
        if (items.length === 0) {
            container.innerHTML = `<div class="text-center py-12 text-gray-400 text-xs">No degree programs found.</div>`;
            return;
        }

        container.innerHTML = `
            <div class="table-responsive rounded-2xl bg-[#111827] border border-[#1F2937]">
                <table class="table table-dark-custom mb-0 align-middle">
                    <thead>
                        <tr>
                            <th>PROGRAM / BRANCH</th>
                            <th>DEGREE</th>
                            <th>TOTAL INTAKE</th>
                            <th>DURATION</th>
                            <th>FEES / SEM</th>
                            <th>BROCHURE</th>
                            <th class="text-end">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map(p => `
                            <tr>
                                <td class="font-bold text-white">${p.program || p.title || 'BE Program'}</td>
                                <td class="text-emerald-400 text-xs font-semibold">${p.degree || 'BE'}</td>
                                <td class="text-gray-300 text-xs">${p.seats || p.intake || '120'} Seats</td>
                                <td class="text-gray-300 text-xs">${p.duration || '4 Years'}</td>
                                <td class="text-emerald-300 text-xs font-bold font-mono">₹ ${p.fee || '38,000'}</td>
                                <td>
                                    ${p.file_url ? `
                                        <a href="${p.file_url}" target="_blank" class="text-emerald-400 text-xs font-semibold flex items-center gap-1 text-decoration-none">
                                            <i data-lucide="file-down" class="w-3.5 h-3.5"></i> PDF
                                        </a>
                                    ` : '<span class="text-gray-600 text-xs">-</span>'}
                                </td>
                                <td class="text-end">
                                    <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-gray-300 hover:text-white" onclick="window.editAdmission('${p.id}')">
                                        <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                                    </button>
                                    <button class="p-1.5 rounded-lg bg-[#0F172A] border border-[#1F2937] text-red-400 hover:bg-red-500/20" onclick="window.deleteAdmission('${p.id}')">
                                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    function renderCutoffTab(items, container) {
        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="p-5 rounded-2xl bg-[#111827] border border-[#1F2937] space-y-3">
                    <div class="flex items-center gap-2.5">
                        <i data-lucide="award" class="w-5 h-5 text-emerald-400"></i>
                        <h3 class="text-sm font-bold text-white mb-0">ACPC Cutoff & Merit Ranks</h3>
                    </div>
                    <p class="text-xs text-gray-400 mb-2">General and reserved category Gujarat ACPC closing merit rank bounds.</p>
                    <div class="space-y-2 text-xs">
                        <div class="p-2.5 rounded-xl bg-[#0F172A] border border-[#1F2937] flex justify-between">
                            <span class="text-white font-medium">Computer Engineering</span>
                            <span class="font-mono text-emerald-400 font-bold">Rank: 2,450 - 6,800</span>
                        </div>
                        <div class="p-2.5 rounded-xl bg-[#0F172A] border border-[#1F2937] flex justify-between">
                            <span class="text-white font-medium">Information Technology</span>
                            <span class="font-mono text-emerald-400 font-bold">Rank: 5,200 - 9,400</span>
                        </div>
                        <div class="p-2.5 rounded-xl bg-[#0F172A] border border-[#1F2937] flex justify-between">
                            <span class="text-white font-medium">Electronics & Comm.</span>
                            <span class="font-mono text-emerald-400 font-bold">Rank: 9,000 - 15,000</span>
                        </div>
                    </div>
                </div>

                <div class="p-5 rounded-2xl bg-[#111827] border border-[#1F2937] space-y-3">
                    <div class="flex items-center gap-2.5">
                        <i data-lucide="check-circle" class="w-5 h-5 text-emerald-400"></i>
                        <h3 class="text-sm font-bold text-white mb-0">Eligibility & Board Requirements</h3>
                    </div>
                    <ul class="space-y-2 text-xs text-gray-300 ps-4">
                        <li>Passed 10+2 (Science Stream) with Physics and Maths as compulsory subjects.</li>
                        <li>Minimum 45% aggregate in PCM (40% for SC/ST/SEBC reserved categories).</li>
                        <li>Valid score in GUJCET 2026 or JEE Main 2026.</li>
                        <li>D2D (Direct 2nd Year Diploma to Degree): Passed Diploma Engineering with minimum 45%.</li>
                    </ul>
                </div>
            </div>
        `;
    }

    function renderStepsTab(items, container) {
        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="adm-step-card space-y-2">
                    <div class="adm-step-num">1</div>
                    <h4 class="text-sm font-bold text-white mb-1">Online ACPC Registration</h4>
                    <p class="text-xs text-gray-400 mb-0">Register at gujacpc.admissions.nic.in and upload HSC/GUJCET documents.</p>
                </div>
                <div class="adm-step-card space-y-2">
                    <div class="adm-step-num">2</div>
                    <h4 class="text-sm font-bold text-white mb-1">Choice Filling (SVIT Vasad)</h4>
                    <p class="text-xs text-gray-400 mb-0">Select SVIT Vasad college institute code (041) with your preferred branches.</p>
                </div>
                <div class="adm-step-card space-y-2">
                    <div class="adm-step-num">3</div>
                    <h4 class="text-sm font-bold text-white mb-1">Seat Allotment & Token Fee</h4>
                    <p class="text-xs text-gray-400 mb-0">Upon seat allocation, pay the online admission token fee to freeze allotment.</p>
                </div>
                <div class="adm-step-card space-y-2">
                    <div class="adm-step-num">4</div>
                    <h4 class="text-sm font-bold text-white mb-1">Campus Verification & Onboarding</h4>
                    <p class="text-xs text-gray-400 mb-0">Report to SVIT Vasad Admin Block with original documents to confirm enrollment.</p>
                </div>
            </div>
        `;
    }

    function renderHelpdeskTab(items, container) {
        container.innerHTML = `
            <div class="p-6 rounded-2xl bg-[#111827] border border-[#1F2937] max-w-2xl mx-auto space-y-4">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-2xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center font-bold">
                        <i data-lucide="headphones" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-white mb-0.5">Central Admission Cell & Helpdesk</h3>
                        <p class="text-xs text-gray-400 mb-0">Dedicated guidance counselors for prospective candidates and parents</p>
                    </div>
                </div>

                <div class="space-y-3 text-xs pt-2">
                    <div class="p-3 rounded-xl bg-[#0F172A] border border-[#1F2937] flex items-center justify-between">
                        <span class="text-gray-400">Helpline Phone</span>
                        <span class="text-emerald-400 font-bold font-mono text-sm">+91 (02692) 274489 / 9428612345</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#0F172A] border border-[#1F2937] flex items-center justify-between">
                        <span class="text-gray-400">Admission Inquiry Email</span>
                        <span class="text-white font-medium">admission@svitvasad.ac.in</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#0F172A] border border-[#1F2937] flex items-center justify-between">
                        <span class="text-gray-400">Counseling Location</span>
                        <span class="text-white font-medium">Admin Block, Ground Floor, SVIT Campus</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#0F172A] border border-[#1F2937] flex items-center justify-between">
                        <span class="text-gray-400">Operational Hours</span>
                        <span class="text-gray-300">Monday – Saturday: 09:00 AM – 05:00 PM</span>
                    </div>
                </div>
            </div>
        `;
    }

    async function handleAdmissionFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('admFormRecordId').value;
        const payload = {
            id: recordId || `ADM-${Date.now()}`,
            program: document.getElementById('admProgramInput').value.trim(),
            degree: document.getElementById('admDegreeInput').value,
            department: document.getElementById('admDeptInput').value,
            seats: parseInt(document.getElementById('admSeatsInput').value, 10) || 60,
            duration: document.getElementById('admDurationInput').value,
            fee: document.getElementById('admFeeInput').value.trim(),
            description: document.getElementById('admDescInput').value.trim()
        };

        if (state.uploadedDocData) {
            payload.file_url = state.uploadedDocData.url || state.uploadedDocData.file_url;
        }

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/admission/${recordId}` : '/admin/api/crud/admission';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                admissionModal.hide();
                loadAdmissionData();
            } else {
                showAdminToast(data.message || 'Error saving admission data.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }

    window.editAdmission = function(id) {
        const item = state.items.find(i => String(i.id) === String(id));
        if (!item) return;

        document.getElementById('admModalTitle').innerText = 'Edit Admission Program';
        document.getElementById('admFormRecordId').value = id;
        document.getElementById('admProgramInput').value = item.program || item.title || '';
        document.getElementById('admDegreeInput').value = item.degree || 'BE';
        document.getElementById('admDeptInput').value = item.department || 'Computer Engineering';
        document.getElementById('admSeatsInput').value = item.seats || item.intake || 60;
        document.getElementById('admDurationInput').value = item.duration || '4 Years';
        document.getElementById('admFeeInput').value = item.fee || '';
        document.getElementById('admDescInput').value = item.description || '';

        state.uploadedDocData = item.file_url ? { file_url: item.file_url, file_name: 'Brochure PDF' } : null;
        admissionModal.show();
    };

    window.deleteAdmission = function(id) {
        state.pendingDeleteId = id;
        document.getElementById('deleteAdmTargetId').innerText = id;
        deleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/admission/${state.pendingDeleteId}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message, 'success');
                deleteModal.hide();
                loadAdmissionData();
            } else {
                showAdminToast(data.message || 'Delete failed.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message, 'error');
        }
    }
})();
