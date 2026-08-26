/**
 * SVIT Admin - Subjects & Curriculum Management Controller (Mobile-First Architecture)
 * Complete Hierarchy: PROGRAM -> DEPARTMENT -> YEAR -> SEMESTER -> SUBJECTS
 * 100% Dynamic Metadata, Live MongoDB Data, Real-Time Calculations, and Full CRUD
 */

(function() {
    'use strict';

    const DEPARTMENT_ICONS = {
        'Computer Engineering': 'code-2',
        'Information Technology': 'laptop',
        'Artificial Intelligence & Machine Learning': 'cpu',
        'Data Science': 'database',
        'Electronics & Communication': 'radio',
        'Mechanical Engineering': 'settings',
        'Civil Engineering': 'hard-hat',
        'Electrical Engineering': 'zap',
        'Automobile Engineering': 'car',
        'Computer Applications': 'terminal'
    };

    const PROGRAM_NAMES = {
        'Diploma': 'Diploma Engineering',
        'BE': 'BE / B.Tech (Degree)',
        'BCA': 'BCA (Computer App)',
        'MCA': 'MCA (Master of App)',
        'ME': 'ME / M.Tech (Master)'
    };

    const PROGRAM_ICONS = {
        'Diploma': 'award',
        'BE': 'graduation-cap',
        'BCA': 'code-2',
        'MCA': 'laptop',
        'ME': 'book-marked'
    };

    const YEAR_LABELS = {
        'FY': 'First Year (FY)',
        'SY': 'Second Year (SY)',
        'TY': 'Third Year (TY)',
        'LY': 'Final Year (LY)'
    };

    const state = {
        selectedProgram: 'Diploma', // 'Diploma', 'BE', 'BCA', 'MCA', 'ME'
        selectedCourse: '',        // '' shows course cards; 'Computer Engineering' shows curriculum
        selectedYear: '',          // '' means all years, or 'FY', 'SY', 'TY', 'LY'
        selectedSemester: '1',     // Active semester tab
        search: '',
        typeFilter: '',            // 'Theory', 'Practical', 'Elective'
        creditsFilter: '',
        allSubjects: [],
        isLoading: false,
        pendingDeleteId: null,
        pendingDeleteDoc: null
    };

    let subjectFormModal = null;
    let subjectDetailsModal = null;
    let subjectDeleteModal = null;
    let mobileFilterModal = null;
    let searchDebounceTimer = null;

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize Bootstrap Modals safely
        const formEl = document.getElementById('subjectFormModal');
        const detailsEl = document.getElementById('subjectDetailsModal');
        const deleteEl = document.getElementById('subjectDeleteModal');
        const filterEl = document.getElementById('subjectMobileFilterModal');

        if (formEl && typeof bootstrap !== 'undefined') subjectFormModal = new bootstrap.Modal(formEl);
        if (detailsEl && typeof bootstrap !== 'undefined') subjectDetailsModal = new bootstrap.Modal(detailsEl);
        if (deleteEl && typeof bootstrap !== 'undefined') subjectDeleteModal = new bootstrap.Modal(deleteEl);
        if (filterEl && typeof bootstrap !== 'undefined') mobileFilterModal = new bootstrap.Modal(filterEl);

        bindEvents();
        loadCurriculumData();
    });

    // =========================================================================
    // 1. EVENT LISTENERS & FILTER BINDINGS
    // =========================================================================

    function bindEvents() {
        // Back to Courses Navigation Button
        const backBtn = document.getElementById('backToCoursesBtn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                state.selectedCourse = '';
                state.selectedYear = '';
                renderCurriculumViews();
            });
        }

        // Live Search Input (Debounced)
        const searchInput = document.getElementById('subjectSearchInput');
        const searchClearBtn = document.getElementById('subjectSearchClearBtn');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                state.search = e.target.value.trim();
                searchClearBtn?.classList.toggle('hidden', !state.search);
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    renderCurriculumViews();
                }, 180);
            });
        }

        if (searchClearBtn) {
            searchClearBtn.addEventListener('click', () => {
                state.search = '';
                if (searchInput) searchInput.value = '';
                searchClearBtn.classList.add('hidden');
                renderCurriculumViews();
            });
        }

        // Exit Search Button
        const exitSearchBtn = document.getElementById('exitSearchBtn');
        if (exitSearchBtn) {
            exitSearchBtn.addEventListener('click', () => {
                state.search = '';
                if (searchInput) searchInput.value = '';
                searchClearBtn?.classList.add('hidden');
                renderCurriculumViews();
            });
        }

        // Desktop Type Filter
        const desktopType = document.getElementById('desktopTypeFilter');
        if (desktopType) {
            desktopType.addEventListener('change', (e) => {
                state.typeFilter = e.target.value;
                renderCurriculumViews();
            });
        }

        // Mobile Filter Drawer Trigger
        const mobileDrawerBtn = document.getElementById('mobileFilterDrawerBtn');
        if (mobileDrawerBtn) {
            mobileDrawerBtn.addEventListener('click', () => {
                syncFilterModalValues();
                if (mobileFilterModal) mobileFilterModal.show();
            });
        }

        // Apply Mobile Filters
        const applyMobileBtn = document.getElementById('mFilterApplyBtn');
        if (applyMobileBtn) {
            applyMobileBtn.addEventListener('click', () => {
                state.selectedProgram = document.getElementById('mFilterProgram')?.value || state.selectedProgram;
                state.selectedCourse = document.getElementById('mFilterDept')?.value || '';
                state.selectedYear = document.getElementById('mFilterYear')?.value || '';
                state.selectedSemester = document.getElementById('mFilterSem')?.value || '1';
                state.typeFilter = document.getElementById('mFilterType')?.value || '';
                state.creditsFilter = document.getElementById('mFilterCredits')?.value || '';

                renderProgramPills();
                if (mobileFilterModal) mobileFilterModal.hide();
                renderCurriculumViews();
            });
        }

        // Reset Mobile Filters
        const resetMobileBtn = document.getElementById('mFilterResetBtn');
        if (resetMobileBtn) {
            resetMobileBtn.addEventListener('click', () => {
                state.selectedCourse = '';
                state.selectedYear = '';
                state.selectedSemester = '1';
                state.typeFilter = '';
                state.creditsFilter = '';
                state.search = '';
                if (searchInput) searchInput.value = '';
                searchClearBtn?.classList.add('hidden');
                renderProgramPills();
                if (mobileFilterModal) mobileFilterModal.hide();
                renderCurriculumViews();
            });
        }

        // Clear All Filter Chips
        const clearChipsBtn = document.getElementById('subjectClearAllChipsBtn');
        if (clearChipsBtn) {
            clearChipsBtn.addEventListener('click', () => {
                state.typeFilter = '';
                state.creditsFilter = '';
                state.selectedYear = '';
                state.search = '';
                if (searchInput) searchInput.value = '';
                searchClearBtn?.classList.add('hidden');
                if (desktopType) desktopType.value = '';
                renderCurriculumViews();
            });
        }

        // Primary Header Add CTA
        const addHeaderBtn = document.getElementById('openAddSubjectModalBtn');
        if (addHeaderBtn) {
            addHeaderBtn.addEventListener('click', () => {
                window.quickAddSubject(state.selectedProgram, state.selectedCourse, state.selectedSemester, state.selectedYear);
            });
        }

        // Course Detail Add CTA
        const addCourseBtn = document.getElementById('addSubjectToActiveCourseBtn');
        if (addCourseBtn) {
            addCourseBtn.addEventListener('click', () => {
                window.quickAddSubject(state.selectedProgram, state.selectedCourse, state.selectedSemester, state.selectedYear);
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refreshSubjectsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadCurriculumData);

        // Subject Form Submission
        const form = document.getElementById('subjectForm');
        if (form) form.addEventListener('submit', handleSubjectFormSubmit);

        // Confirm Delete Button
        const confirmDeleteBtn = document.getElementById('confirmDeleteSubjectBtn');
        if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    function syncFilterModalValues() {
        const mProg = document.getElementById('mFilterProgram');
        if (mProg) mProg.value = state.selectedProgram;

        const mDept = document.getElementById('mFilterDept');
        if (mDept) mDept.value = state.selectedCourse;

        const mYear = document.getElementById('mFilterYear');
        if (mYear) mYear.value = state.selectedYear;

        const mSem = document.getElementById('mFilterSem');
        if (mSem) mSem.value = state.selectedSemester;

        const mType = document.getElementById('mFilterType');
        if (mType) mType.value = state.typeFilter;

        const mCred = document.getElementById('mFilterCredits');
        if (mCred) mCred.value = state.creditsFilter;
    }

    // =========================================================================
    // 2. DATA LOADING & API INTERACTION (Live MongoDB Dataset)
    // =========================================================================

    async function loadCurriculumData() {
        state.isLoading = true;
        renderLoadingSkeletons();

        try {
            const res = await fetch('/admin/api/crud/subjects?limit=1000');
            const data = await res.json();

            if (res.ok && (data.status === 'success' || Array.isArray(data.items))) {
                state.allSubjects = Array.isArray(data.items) ? data.items : [];
                calculateAndRenderCurriculumStats();
                renderProgramPills();
                syncDynamicFilterAndFormDropdowns();
                renderCurriculumViews();
            } else {
                showErrorState(data.message || 'Error retrieving subjects dataset from MongoDB.');
            }
        } catch (err) {
            showErrorState(err.message || 'Network error fetching subjects data.');
        } finally {
            state.isLoading = false;
        }
    }

    function renderLoadingSkeletons() {
        const grid = document.getElementById('coursesCardGrid');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-16 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-7 h-7 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <p class="font-bold text-xs text-[#171D3A] mb-1">Loading Curriculum from MongoDB...</p>
                    <p class="text-[11px] text-[#8C95AD] mb-0">Structuring Academic Programs, Courses &amp; Subjects</p>
                </div>
            `;
        }
    }

    function showErrorState(msg) {
        const grid = document.getElementById('coursesCardGrid');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-10 bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">
                    <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                    <p class="text-xs font-bold mb-1">Failed to Load Curriculum Data</p>
                    <p class="text-[11px] text-red-500 mb-3">${escapeHtml(msg)}</p>
                    <button type="button" class="px-3.5 py-2 rounded-xl bg-white border border-red-200 text-red-700 text-xs font-bold shadow-sm hover:bg-red-100" onclick="location.reload()">
                        Retry
                    </button>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        }
    }

    // =========================================================================
    // 3. STATS & METRICS CALCULATIONS (Live MongoDB Dynamic Counts)
    // =========================================================================

    function calculateAndRenderCurriculumStats() {
        const all = state.allSubjects;

        // Distinct Programs
        const programs = new Set(all.map(s => s.program).filter(Boolean));
        
        // Distinct Courses (Program + Department combinations)
        const courseMap = {};
        all.forEach(s => {
            const prog = s.program || 'Other';
            const dept = s.department || 'General';
            const key = `${prog}__${dept}`;
            if (!courseMap[key]) {
                courseMap[key] = { program: prog, department: dept, subjects: [], semesters: new Set() };
            }
            courseMap[key].subjects.push(s);
            if (s.semester) courseMap[key].semesters.add(String(s.semester));
        });

        // Total Credits Calculation
        let totalCredits = 0;
        all.forEach(s => {
            const c = parseInt(s.credits, 10);
            if (!isNaN(c)) totalCredits += c;
        });

        // Update KPI Elements
        const kpiProg = document.getElementById('kpiProgramsCount');
        if (kpiProg) kpiProg.innerText = `${programs.size || 5}`;

        const kpiCourses = document.getElementById('kpiCoursesCount');
        if (kpiCourses) kpiCourses.innerText = `${Object.keys(courseMap).length || 20}`;

        const kpiSubj = document.getElementById('kpiSubjectsCount');
        if (kpiSubj) kpiSubj.innerText = `${all.length}`;

        const kpiCred = document.getElementById('kpiCreditsCount');
        if (kpiCred) kpiCred.innerText = `${totalCredits.toLocaleString()}`;

        const heroBadge = document.getElementById('heroTotalBadge');
        if (heroBadge) heroBadge.innerText = `${all.length} Subjects`;
    }

    // =========================================================================
    // 4. LEVEL 1: DYNAMIC PROGRAM SELECTOR PILLS
    // =========================================================================

    function renderProgramPills() {
        const container = document.getElementById('programSelectorContainer');
        if (!container) return;

        // Group subjects by Program dynamically
        const programMap = {};
        state.allSubjects.forEach(s => {
            const p = s.program || 'General';
            if (!programMap[p]) {
                programMap[p] = { program: p, courses: new Set(), subjectsCount: 0 };
            }
            if (s.department) programMap[p].courses.add(s.department);
            programMap[p].subjectsCount++;
        });

        const progList = Object.keys(programMap).sort();
        if (!progList.length) return;

        // Verify active selection exists
        if (!progList.some(p => p.toLowerCase() === state.selectedProgram.toLowerCase())) {
            state.selectedProgram = progList[0];
        }

        const progInfo = document.getElementById('programInfoLabel');
        if (progInfo) {
            progInfo.innerText = `${progList.length} Degree Programs Available`;
        }

        container.innerHTML = progList.map(prog => {
            const item = programMap[prog];
            const isActive = prog.toLowerCase() === state.selectedProgram.toLowerCase();
            const iconName = PROGRAM_ICONS[prog] || 'award';
            const title = PROGRAM_NAMES[prog] || prog;
            const courseCount = item.courses.size;
            const subCount = item.subjectsCount;

            return `
                <button type="button" class="program-nav-pill ${isActive ? 'active' : ''}" data-program="${escapeHtml(prog)}" onclick="window.selectProgram('${escapeQuotes(prog)}')">
                    <div class="pill-badge-icon"><i data-lucide="${iconName}" class="w-4 h-4"></i></div>
                    <div class="text-left">
                        <span class="program-title">${escapeHtml(title)}</span>
                        <span class="program-sub">${courseCount} ${courseCount === 1 ? 'Course' : 'Courses'} • ${subCount} Subjects</span>
                    </div>
                </button>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    }

    window.selectProgram = function(prog) {
        state.selectedProgram = prog;
        state.selectedCourse = '';
        state.selectedYear = '';
        state.selectedSemester = '1';
        state.search = '';
        const searchInput = document.getElementById('subjectSearchInput');
        if (searchInput) searchInput.value = '';
        document.getElementById('subjectSearchClearBtn')?.classList.add('hidden');
        renderProgramPills();
        renderCurriculumViews();
    };

    function syncDynamicFilterAndFormDropdowns() {
        const programs = Array.from(new Set(state.allSubjects.map(s => s.program).filter(Boolean))).sort();
        const depts = Array.from(new Set(state.allSubjects.map(s => s.department).filter(Boolean))).sort();

        // Populate Mobile Filter Program Dropdown
        const mProg = document.getElementById('mFilterProgram');
        if (mProg && programs.length) {
            const cur = mProg.value;
            mProg.innerHTML = programs.map(p => `<option value="${escapeHtml(p)}">${escapeHtml(PROGRAM_NAMES[p] || p)}</option>`).join('');
            if (cur && programs.includes(cur)) mProg.value = cur;
            else mProg.value = state.selectedProgram;
        }

        // Populate Mobile Filter Dept Dropdown
        const mDept = document.getElementById('mFilterDept');
        if (mDept && depts.length) {
            const cur = mDept.value;
            mDept.innerHTML = `<option value="">All Departments</option>` + depts.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
            if (cur && depts.includes(cur)) mDept.value = cur;
        }

        // Populate Form Program Dropdown
        const formProg = document.getElementById('formProgram');
        if (formProg && programs.length) {
            const cur = formProg.value;
            formProg.innerHTML = programs.map(p => `<option value="${escapeHtml(p)}">${escapeHtml(PROGRAM_NAMES[p] || p)}</option>`).join('');
            if (cur && programs.includes(cur)) formProg.value = cur;
        }

        // Populate Form Dept Dropdown
        const formDept = document.getElementById('formDepartment');
        if (formDept && depts.length) {
            const cur = formDept.value;
            formDept.innerHTML = depts.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
            if (cur && depts.includes(cur)) formDept.value = cur;
        }
    }

    // =========================================================================
    // 5. MAIN CURRICULUM RENDERING CONTROLLER
    // =========================================================================

    function renderCurriculumViews() {
        updateActiveFilterChips();
        updateActiveFilterBadge();

        const searchSection = document.getElementById('globalSearchResultsSection');
        const hierarchySection = document.getElementById('curriculumHierarchySection');
        const courseGridSec = document.getElementById('courseSelectionContainer');
        const courseDetailSec = document.getElementById('courseDetailSubjectSection');

        // Condition 1: Global Search Mode
        if (state.search) {
            if (searchSection) searchSection.classList.remove('hidden');
            if (hierarchySection) hierarchySection.classList.add('hidden');
            renderSearchResults();
            if (window.lucide) lucide.createIcons();
            return;
        }

        // Normal Hierarchy Mode
        if (searchSection) searchSection.classList.add('hidden');
        if (hierarchySection) hierarchySection.classList.remove('hidden');

        // Condition 2: Course Selection Mode (Level 2)
        if (!state.selectedCourse) {
            if (courseGridSec) courseGridSec.classList.remove('hidden');
            if (courseDetailSec) courseDetailSec.classList.add('hidden');
            renderCoursesGrid();
        } else {
            // Condition 3: Course Detail & Semester Subject Mode (Levels 3 & 4)
            if (courseGridSec) courseGridSec.classList.add('hidden');
            if (courseDetailSec) courseDetailSec.classList.remove('hidden');
            renderCourseDetailAndSubjects();
        }

        if (window.lucide) lucide.createIcons();
    }

    // =========================================================================
    // 6. LEVEL 2: COURSES / DEPARTMENTS GRID RENDERING
    // =========================================================================

    function renderCoursesGrid() {
        const grid = document.getElementById('coursesCardGrid');
        if (!grid) return;

        const titleEl = document.getElementById('courseSectionTitle');
        const subEl = document.getElementById('courseSectionSubtitle');

        const currentProgLabel = PROGRAM_NAMES[state.selectedProgram] || state.selectedProgram;
        if (titleEl) titleEl.innerText = `${currentProgLabel} Courses`;

        // Filter subjects for this program
        const progSubjects = state.allSubjects.filter(s => (s.program || '').toLowerCase() === state.selectedProgram.toLowerCase());

        // Group into distinct courses
        const courses = {};
        progSubjects.forEach(s => {
            const dept = s.department || 'General';
            if (!courses[dept]) {
                courses[dept] = { department: dept, subjects: [], semesters: new Set(), totalCredits: 0 };
            }
            courses[dept].subjects.push(s);
            if (s.semester) courses[dept].semesters.add(String(s.semester));
            const c = parseInt(s.credits, 10);
            if (!isNaN(c)) courses[dept].totalCredits += c;
        });

        const courseList = Object.values(courses).sort((a, b) => a.department.localeCompare(b.department));

        if (subEl) {
            subEl.innerText = `${courseList.length} ${courseList.length === 1 ? 'Course' : 'Courses'} Available`;
        }

        if (!courseList.length) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center mx-auto mb-3 shadow-sm">
                        <i data-lucide="folder-x" class="w-6 h-6"></i>
                    </div>
                    <h4 class="text-sm font-bold text-[#171D3A] mb-1">No Courses Found in ${escapeHtml(state.selectedProgram)}</h4>
                    <p class="text-xs text-[#66708F] mb-4">No subjects are currently registered under the ${escapeHtml(state.selectedProgram)} program.</p>
                    <button type="button" class="btn-primary-custom text-xs font-bold mx-auto py-2.5 px-4" onclick="window.quickAddSubject('${escapeQuotes(state.selectedProgram)}', '', '1')">
                        <i data-lucide="plus" class="w-4 h-4"></i> Add First Subject
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = courseList.map(c => {
            const iconName = DEPARTMENT_ICONS[c.department] || 'book-open';
            const semCount = c.semesters.size;
            const subCount = c.subjects.length;

            return `
                <div class="course-card-item" onclick="window.selectCourse('${escapeQuotes(c.department)}')">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <div class="course-icon-box">
                                <i data-lucide="${iconName}" class="w-5 h-5"></i>
                            </div>
                            <span class="badge-svit-purple text-[11px] font-bold">
                                ${semCount} ${semCount === 1 ? 'Semester' : 'Semesters'}
                            </span>
                        </div>
                        <h4 class="text-sm font-bold text-[#171D3A] mb-1 leading-snug">${escapeHtml(c.department)}</h4>
                        <p class="text-xs text-[#66708F] mb-0">${subCount} Total Subjects • ${c.totalCredits} Credits</p>
                    </div>

                    <div class="pt-3 mt-3 border-t border-[#E1E5F0] flex items-center justify-between text-xs font-bold text-[#8B5CF6]">
                        <span>View Curriculum</span>
                        <i data-lucide="arrow-right" class="w-4 h-4"></i>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.selectCourse = function(department) {
        state.selectedCourse = department;
        state.selectedYear = '';
        state.selectedSemester = '1';
        renderCurriculumViews();
    };

    // =========================================================================
    // 7. LEVEL 3 & 4: PROGRAM -> DEPARTMENT -> YEAR -> SEMESTER -> SUBJECTS
    // =========================================================================

    function renderCourseDetailAndSubjects() {
        const course = state.selectedCourse;
        const prog = state.selectedProgram;

        // Breadcrumbs & Titles
        const bcProg = document.getElementById('bcProgramName');
        if (bcProg) bcProg.innerText = prog;

        const bcCourse = document.getElementById('bcCourseName');
        if (bcCourse) bcCourse.innerText = course;

        const backLabel = document.getElementById('backToCoursesLabel');
        if (backLabel) backLabel.innerText = `← ${prog} Courses`;

        const titleEl = document.getElementById('activeCourseTitle');
        if (titleEl) titleEl.innerText = course;

        // Filter all subjects for this specific Program + Course
        const courseSubjects = state.allSubjects.filter(s => 
            (s.program || '').toLowerCase() === prog.toLowerCase() &&
            (s.department || '').toLowerCase() === course.toLowerCase()
        );

        // Distinct Years in this course
        const yearsSet = new Set(courseSubjects.map(s => s.year).filter(Boolean));
        const sortedYears = ['FY', 'SY', 'TY', 'LY'].filter(y => yearsSet.has(y));

        // Distinct Semesters in this course (optionally filtered by selectedYear)
        let relevantSubjectsForSems = courseSubjects;
        if (state.selectedYear) {
            relevantSubjectsForSems = courseSubjects.filter(s => (s.year || '').toUpperCase() === state.selectedYear.toUpperCase());
        }

        const semsSet = new Set(relevantSubjectsForSems.map(s => String(s.semester)).filter(Boolean));
        const sortedSems = Array.from(semsSet).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));

        if (!sortedSems.length) {
            state.selectedYear = '';
            relevantSubjectsForSems = courseSubjects;
            courseSubjects.forEach(s => { if (s.semester) semsSet.add(String(s.semester)); });
        }

        if (!sortedSems.includes(state.selectedSemester)) {
            state.selectedSemester = sortedSems[0] || '1';
        }

        // Calculate course credits
        let courseCredits = 0;
        courseSubjects.forEach(s => {
            const c = parseInt(s.credits, 10);
            if (!isNaN(c)) courseCredits += c;
        });

        const metaEl = document.getElementById('activeCourseMeta');
        if (metaEl) {
            metaEl.innerText = `${prog} Program • ${courseSubjects.length} Total Subjects • ${courseCredits} Credits`;
        }

        const creditsBadge = document.getElementById('activeCourseCreditsBadge');
        if (creditsBadge) {
            creditsBadge.innerText = `${courseCredits} Total Credits`;
        }

        // Render Level 3A: Year Tabs (FY, SY, TY, LY)
        const yearTabsContainer = document.getElementById('yearTabsContainer');
        if (yearTabsContainer && sortedYears.length > 1) {
            let yearHtml = `
                <button type="button" class="year-tab-pill ${!state.selectedYear ? 'active' : ''}" onclick="window.selectYear('')">
                    <span>All Years</span>
                </button>
            `;
            sortedYears.forEach(y => {
                const count = courseSubjects.filter(s => (s.year || '').toUpperCase() === y).length;
                yearHtml += `
                    <button type="button" class="year-tab-pill ${state.selectedYear === y ? 'active' : ''}" onclick="window.selectYear('${y}')">
                        <span>${escapeHtml(YEAR_LABELS[y] || y)}</span>
                        <span class="text-[10px] opacity-80">(${count})</span>
                    </button>
                `;
            });
            yearTabsContainer.innerHTML = yearHtml;
            document.getElementById('yearSelectorWrapper')?.classList.remove('hidden');
        } else {
            document.getElementById('yearSelectorWrapper')?.classList.add('hidden');
        }

        // Render Level 3B: Semester Navigation Tabs (Swipeable & Touch Friendly)
        const tabsContainer = document.getElementById('semesterTabsContainer');
        if (tabsContainer) {
            tabsContainer.innerHTML = sortedSems.map(sem => {
                const count = relevantSubjectsForSems.filter(s => String(s.semester) === String(sem)).length;
                const sampleSub = relevantSubjectsForSems.find(s => String(s.semester) === String(sem));
                const yearLabel = sampleSub?.year ? ` (${sampleSub.year})` : '';
                const isActive = (String(state.selectedSemester) === String(sem));
                return `
                    <button type="button" class="semester-tab-pill ${isActive ? 'active' : ''}" onclick="window.selectSemester('${escapeQuotes(sem)}')">
                        <span>Semester ${sem}${yearLabel}</span>
                        <span class="sem-badge">${count}</span>
                    </button>
                `;
            }).join('');
        }

        // Filter subjects for Selected Semester
        let semesterSubjects = relevantSubjectsForSems.filter(s => String(s.semester) === String(state.selectedSemester));

        // Apply type and credits filters if active
        if (state.typeFilter) {
            semesterSubjects = semesterSubjects.filter(s => (s.subject_type || '').toLowerCase().includes(state.typeFilter.toLowerCase()));
        }
        if (state.creditsFilter) {
            semesterSubjects = semesterSubjects.filter(s => String(s.credits) === String(state.creditsFilter));
        }

        // Semester Credits Sum
        let semCredits = 0;
        let currentYear = 'FY';
        semesterSubjects.forEach(s => {
            const c = parseInt(s.credits, 10);
            if (!isNaN(c)) semCredits += c;
            if (s.year) currentYear = s.year;
        });

        // Update Mobile Context Card
        const mProg = document.getElementById('mContextProgram');
        if (mProg) mProg.innerText = prog;

        const mDept = document.getElementById('mContextDept');
        if (mDept) mDept.innerText = course;

        const mYearSem = document.getElementById('mContextYearSem');
        if (mYearSem) mYearSem.innerText = `${currentYear} • Semester ${state.selectedSemester}`;

        const mCount = document.getElementById('mContextCount');
        if (mCount) mCount.innerText = `${semesterSubjects.length} ${semesterSubjects.length === 1 ? 'Subject' : 'Subjects'}`;

        const semHeader = document.getElementById('semesterSubjectsHeader');
        if (semHeader) {
            semHeader.innerText = `${currentYear} • Semester ${state.selectedSemester} Subjects (${semesterSubjects.length})`;
        }

        const semCreditSum = document.getElementById('semesterCreditSum');
        if (semCreditSum) {
            semCreditSum.innerText = `Total Semester Credits: ${semCredits}`;
        }

        // Render Subject Cards (Level 4)
        const subjectGrid = document.getElementById('subjectsCardGrid');
        if (!subjectGrid) return;

        if (!semesterSubjects.length) {
            subjectGrid.innerHTML = `
                <div class="col-span-full text-center py-12 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center mx-auto mb-3 shadow-sm">
                        <i data-lucide="book-x" class="w-6 h-6"></i>
                    </div>
                    <h4 class="text-sm font-bold text-[#171D3A] mb-1">No Subjects Found in Semester ${state.selectedSemester}</h4>
                    <p class="text-xs text-[#66708F] mb-4">No subjects match the selected semester or type filters for ${escapeHtml(course)}.</p>
                    <button type="button" class="btn-primary-custom text-xs font-bold mx-auto py-2.5 px-4" onclick="window.quickAddSubject('${escapeQuotes(prog)}', '${escapeQuotes(course)}', '${escapeQuotes(state.selectedSemester)}', '${escapeQuotes(currentYear)}')">
                        <i data-lucide="plus" class="w-4 h-4"></i> Add Subject to Semester ${state.selectedSemester}
                    </button>
                </div>
            `;
            return;
        }

        subjectGrid.innerHTML = semesterSubjects.map(sub => renderSingleSubjectCard(sub)).join('');
    }

    window.selectYear = function(year) {
        state.selectedYear = year;
        renderCurriculumViews();
    };

    window.selectSemester = function(sem) {
        state.selectedSemester = sem;
        renderCurriculumViews();
    };

    // =========================================================================
    // 8. GLOBAL SEARCH RESULTS RENDERING
    // =========================================================================

    function renderSearchResults() {
        const grid = document.getElementById('searchResultsGrid');
        const header = document.getElementById('searchResultsHeader');
        if (!grid) return;

        const q = state.search.toLowerCase();
        let matches = state.allSubjects.filter(s => {
            const name = (s.subject_name || '').toLowerCase();
            const code = (s.subject_code || s.subject_id || '').toLowerCase();
            const dept = (s.department || '').toLowerCase();
            const prog = (s.program || '').toLowerCase();
            const year = (s.year || '').toLowerCase();
            const sem = String(s.semester || '');
            const fac = (s.faculty || '').toLowerCase();
            return name.includes(q) || code.includes(q) || dept.includes(q) || prog.includes(q) || year.includes(q) || sem.includes(q) || fac.includes(q);
        });

        if (state.typeFilter) {
            matches = matches.filter(s => (s.subject_type || '').toLowerCase().includes(state.typeFilter.toLowerCase()));
        }
        if (state.creditsFilter) {
            matches = matches.filter(s => String(s.credits) === String(state.creditsFilter));
        }

        if (header) {
            header.innerText = `Search Results for "${state.search}" (${matches.length} matches)`;
        }

        if (!matches.length) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12 bg-white border border-[#E1E5F0] rounded-2xl p-6 shadow-sm">
                    <div class="w-12 h-12 rounded-2xl bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center mx-auto mb-3 shadow-sm">
                        <i data-lucide="search-x" class="w-6 h-6"></i>
                    </div>
                    <h4 class="text-sm font-bold text-[#171D3A] mb-1">No Subjects Match "${escapeHtml(state.search)}"</h4>
                    <p class="text-xs text-[#66708F] mb-4">Try searching by course name, GTU subject code (e.g. DICO101), or professor name.</p>
                    <button type="button" class="btn-primary-custom text-xs font-bold mx-auto py-2.5 px-4" onclick="document.getElementById('exitSearchBtn')?.click()">
                        Clear Search
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = matches.map(sub => renderSingleSubjectCard(sub, true)).join('');
    }

    function renderSingleSubjectCard(sub, showHierarchyBreadcrumb = false) {
        const type = (sub.subject_type || 'Theory').toLowerCase();
        const isPractical = type.includes('practical') || type.includes('lab');
        const isElective = type.includes('elective');
        const isTheory = !isPractical && !isElective;

        const accentClass = isPractical ? 'is-practical' : (isElective ? 'is-elective' : 'is-theory');
        const badgeTypeClass = isPractical ? 'badge-type-practical' : (isElective ? 'badge-type-elective' : 'badge-type-theory');

        return `
            <div class="subject-item-card ${accentClass}">
                <div>
                    <!-- Top Meta Row: Subject Code, Type Badge, Credits -->
                    <div class="flex items-center justify-between gap-1.5 mb-2">
                        <span class="font-mono text-xs font-bold px-2 py-0.5 rounded-lg bg-[#F8F9FE] border border-[#E1E5F0] text-[#171D3A]">
                            ${escapeHtml(sub.subject_code || sub.subject_id || 'CODE')}
                        </span>
                        <div class="flex items-center gap-1.5 flex-wrap">
                            <span class="${badgeTypeClass}">${escapeHtml(sub.subject_type || 'Theory')}</span>
                            <span class="badge-credits">${escapeHtml(sub.credits || '4')} Credits</span>
                        </div>
                    </div>

                    <!-- Subject Name Title -->
                    <h4 class="text-sm font-bold text-[#171D3A] mb-2 leading-snug line-clamp-2" title="${escapeHtml(sub.subject_name)}">
                        ${escapeHtml(sub.subject_name || 'Academic Subject')}
                    </h4>

                    <!-- Faculty / Hierarchy Context -->
                    <div class="pt-2 border-t border-[#E1E5F0] space-y-1 text-xs text-[#66708F]">
                        ${showHierarchyBreadcrumb ? `
                            <div class="flex items-center gap-1 text-[11px] font-semibold text-[#8B5CF6] truncate">
                                <i data-lucide="layers" class="w-3 h-3 flex-shrink-0"></i>
                                <span class="truncate">${escapeHtml(sub.program || '')} › ${escapeHtml(sub.department || '')} › ${escapeHtml(sub.year || '')} • Sem ${escapeHtml(sub.semester || '')}</span>
                            </div>
                        ` : ''}

                        <div class="flex items-center justify-between text-xs gap-2">
                            <div class="flex items-center gap-1.5 truncate">
                                <div class="w-5 h-5 rounded-full bg-[#E8EBFA] text-[#8B5CF6] flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                                    <i data-lucide="user" class="w-3 h-3"></i>
                                </div>
                                <span class="text-[#171D3A] font-medium truncate">${escapeHtml(sub.faculty || 'Faculty In-Charge')}</span>
                            </div>
                            <span class="text-[11px] text-[#8C95AD] whitespace-nowrap font-medium">${escapeHtml(sub.year || 'FY')} • Sem ${escapeHtml(sub.semester || '1')}</span>
                        </div>
                    </div>
                </div>

                <!-- Card Bottom Touch-Friendly Actions (Min 44px hit targets) -->
                <div class="pt-3 mt-3 border-t border-[#E1E5F0] flex items-center justify-end gap-1.5">
                    <button type="button" class="px-3 py-1.5 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0] text-[#171D3A] text-xs font-semibold hover:bg-[#E8EBFA] min-h-[36px]" onclick="window.viewSubjectDetails('${escapeQuotes(sub.id || sub.subject_id)}')">
                        Details
                    </button>
                    <button type="button" class="px-3 py-1.5 rounded-xl bg-white border border-[#E1E5F0] text-[#8B5CF6] text-xs font-bold hover:bg-[#E8EBFA] min-h-[36px]" onclick="window.editSubject('${escapeQuotes(sub.id || sub.subject_id)}')">
                        Edit
                    </button>
                    <button type="button" class="p-2 rounded-xl bg-white border border-[#E1E5F0] text-[#8C95AD] hover:text-red-600 hover:bg-red-50 min-h-[36px] min-w-[36px] flex items-center justify-center" onclick="window.deleteSubject('${escapeQuotes(sub.id || sub.subject_id)}')">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            </div>
        `;
    }

    function updateActiveFilterChips() {
        const chipsBar = document.getElementById('subjectActiveChipsBar');
        const container = document.getElementById('subjectActiveChipsContainer');
        if (!chipsBar || !container) return;

        const chips = [];

        chips.push({ label: `${state.selectedProgram}`, key: 'program' });
        if (state.selectedCourse) {
            chips.push({ label: `${state.selectedCourse}`, key: 'course', removable: true });
            if (state.selectedYear) {
                chips.push({ label: `Year: ${state.selectedYear}`, key: 'year', removable: true });
            }
            chips.push({ label: `Sem ${state.selectedSemester}`, key: 'semester' });
        }
        if (state.typeFilter) {
            chips.push({ label: `Type: ${state.typeFilter}`, key: 'type', removable: true });
        }
        if (state.creditsFilter) {
            chips.push({ label: `${state.creditsFilter} Credits`, key: 'credits', removable: true });
        }
        if (state.search) {
            chips.push({ label: `Search: "${state.search}"`, key: 'search', removable: true });
        }

        container.innerHTML = chips.map(c => `
            <span class="filter-chip">
                <span>${escapeHtml(c.label)}</span>
                ${c.removable ? `<span class="filter-chip-remove" onclick="window.removeSubjectFilterChip('${c.key}')"><i data-lucide="x" class="w-3 h-3"></i></span>` : ''}
            </span>
        `).join('');

        chipsBar.classList.remove('hidden');
    }

    window.removeSubjectFilterChip = function(key) {
        if (key === 'course') {
            state.selectedCourse = '';
            state.selectedYear = '';
        } else if (key === 'year') {
            state.selectedYear = '';
        } else if (key === 'type') {
            state.typeFilter = '';
            const dt = document.getElementById('desktopTypeFilter');
            if (dt) dt.value = '';
        } else if (key === 'credits') {
            state.creditsFilter = '';
        } else if (key === 'search') {
            state.search = '';
            const searchInput = document.getElementById('subjectSearchInput');
            if (searchInput) searchInput.value = '';
            document.getElementById('subjectSearchClearBtn')?.classList.add('hidden');
        }
        renderCurriculumViews();
    };

    function updateActiveFilterBadge() {
        let count = 0;
        if (state.typeFilter) count++;
        if (state.creditsFilter) count++;
        if (state.selectedYear) count++;
        if (state.search) count++;

        const badge = document.getElementById('mobileActiveFilterCount');
        if (badge) {
            badge.innerText = `${count}`;
            badge.classList.toggle('hidden', count === 0);
        }
    }

    // =========================================================================
    // 9. CRUD OPERATIONS (ADD, EDIT, DELETE, DETAILS)
    // =========================================================================

    window.quickAddSubject = function(program, department, semester, year) {
        document.getElementById('subjectModalTitle').innerText = 'Add Subject';
        document.getElementById('subjectModalSubtitle').innerText = 'Assign subject code, credit distribution, and curriculum mapping';
        document.getElementById('subjectFormSubmitBtn').innerText = 'Save Subject';

        document.getElementById('subjectRecordId').value = '';
        document.getElementById('subjectForm').reset();

        const activeSem = semester || state.selectedSemester || '1';
        let calculatedYear = year || state.selectedYear;
        if (!calculatedYear) {
            const semNum = parseInt(activeSem, 10) || 1;
            calculatedYear = semNum > 6 ? 'LY' : (semNum > 4 ? 'TY' : (semNum > 2 ? 'SY' : 'FY'));
        }

        document.getElementById('formProgram').value = program || state.selectedProgram || 'Diploma';
        document.getElementById('formDepartment').value = department || state.selectedCourse || 'Computer Engineering';
        document.getElementById('formSemester').value = activeSem;
        document.getElementById('formYear').value = calculatedYear;
        document.getElementById('formSubjectType').value = 'Theory';
        document.getElementById('formCredits').value = '4';

        if (subjectFormModal) subjectFormModal.show();
    };

    window.editSubject = function(subjectId) {
        const item = state.allSubjects.find(s => String(s.id || s.subject_id) === String(subjectId));
        if (!item) return;

        document.getElementById('subjectModalTitle').innerText = 'Edit Subject';
        document.getElementById('subjectModalSubtitle').innerText = 'Update academic metadata, credits, or course placement';
        document.getElementById('subjectFormSubmitBtn').innerText = 'Save Changes';

        document.getElementById('subjectRecordId').value = item.id || item.subject_id;
        document.getElementById('formProgram').value = item.program || state.selectedProgram;
        document.getElementById('formDepartment').value = item.department || state.selectedCourse;
        document.getElementById('formYear').value = item.year || 'FY';
        document.getElementById('formSemester').value = item.semester || state.selectedSemester;
        document.getElementById('formSubjectCode').value = item.subject_code || item.subject_id || '';
        document.getElementById('formSubjectName').value = item.subject_name || '';
        document.getElementById('formSubjectType').value = item.subject_type || 'Theory';
        document.getElementById('formCredits').value = item.credits || '4';
        document.getElementById('formFaculty').value = item.faculty || '';
        document.getElementById('formDescription').value = item.description || '';

        if (subjectDetailsModal) subjectDetailsModal.hide();
        if (subjectFormModal) subjectFormModal.show();
    };

    window.viewSubjectDetails = function(subjectId) {
        const item = state.allSubjects.find(s => String(s.id || s.subject_id) === String(subjectId));
        if (!item) return;

        const container = document.getElementById('subjectDetailsContent');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-4 text-xs">
                <!-- Subject Header Card -->
                <div class="p-4 rounded-2xl bg-[#F8F9FE] border border-[#E1E5F0]">
                    <div class="flex items-center justify-between gap-2 mb-2">
                        <span class="font-mono text-xs font-bold px-2.5 py-1 rounded-lg bg-[#E8EBFA] text-[#8B5CF6]">
                            ${escapeHtml(item.subject_code || item.subject_id)}
                        </span>
                        <span class="badge-credits font-bold">${escapeHtml(item.credits || '4')} Credits</span>
                    </div>
                    <h3 class="text-base font-bold text-[#171D3A] mb-1">${escapeHtml(item.subject_name)}</h3>
                    <p class="text-xs text-[#8B5CF6] font-semibold mb-0">${escapeHtml(item.faculty || 'Faculty In-Charge')}</p>
                </div>

                <!-- 2-Column Info Grid -->
                <div class="grid grid-cols-2 gap-2.5">
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Program</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.program)}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Department / Course</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.department)}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Year &amp; Semester</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.year || 'FY')} • Semester ${escapeHtml(item.semester || '1')}</span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-0.5">Subject Type</span>
                        <span class="text-[#171D3A] font-bold text-xs">${escapeHtml(item.subject_type || 'Theory')}</span>
                    </div>
                </div>

                ${item.description ? `
                    <div class="p-3 rounded-xl bg-[#F8F9FE] border border-[#E1E5F0]">
                        <span class="text-[#8C95AD] block text-[10px] uppercase font-bold tracking-wider mb-1">Syllabus / Notes</span>
                        <p class="text-xs text-[#171D3A] mb-0 leading-relaxed">${escapeHtml(item.description)}</p>
                    </div>
                ` : ''}
            </div>
        `;

        const editBtn = document.getElementById('detailsEditBtn');
        if (editBtn) {
            editBtn.onclick = () => window.editSubject(item.id || item.subject_id);
        }

        const delBtn = document.getElementById('detailsDeleteBtn');
        if (delBtn) {
            delBtn.onclick = () => {
                if (subjectDetailsModal) subjectDetailsModal.hide();
                window.deleteSubject(item.id || item.subject_id);
            };
        }

        if (subjectDetailsModal) subjectDetailsModal.show();
        if (window.lucide) lucide.createIcons();
    };

    async function handleSubjectFormSubmit(e) {
        e.preventDefault();
        const recordId = document.getElementById('subjectRecordId').value;
        const payload = {
            program: document.getElementById('formProgram').value,
            department: document.getElementById('formDepartment').value,
            year: document.getElementById('formYear').value,
            semester: document.getElementById('formSemester').value,
            subject_code: document.getElementById('formSubjectCode').value.trim(),
            subject_name: document.getElementById('formSubjectName').value.trim(),
            subject_type: document.getElementById('formSubjectType').value,
            credits: document.getElementById('formCredits').value,
            faculty: document.getElementById('formFaculty').value.trim(),
            description: document.getElementById('formDescription').value.trim()
        };

        const isEdit = Boolean(recordId);
        const url = isEdit ? `/admin/api/crud/subjects/${recordId}` : '/admin/api/crud/subjects';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || (isEdit ? 'Subject updated.' : 'Subject created.'), 'success');
                if (subjectFormModal) subjectFormModal.hide();
                loadCurriculumData();
            } else {
                showAdminToast(data.message || 'Error saving subject.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Network error saving subject.', 'error');
        }
    }

    window.deleteSubject = function(subjectId) {
        const item = state.allSubjects.find(s => String(s.id || s.subject_id) === String(subjectId));
        if (!item) return;

        state.pendingDeleteId = subjectId;
        state.pendingDeleteDoc = item;

        const textEl = document.getElementById('deleteSubjectDetailsText');
        if (textEl) {
            textEl.innerHTML = `Are you sure you want to remove <strong>${escapeHtml(item.subject_name)}</strong> (<span class="font-mono text-[#8B5CF6]">${escapeHtml(item.subject_code || item.subject_id)}</span>) from <strong>${escapeHtml(item.program)} ${escapeHtml(item.department)}</strong> (${escapeHtml(item.year || 'FY')} • Sem ${escapeHtml(item.semester)})?`;
        }

        if (subjectDeleteModal) subjectDeleteModal.show();
    };

    async function handleConfirmDelete() {
        if (!state.pendingDeleteId) return;

        try {
            const res = await fetch(`/admin/api/crud/subjects/${state.pendingDeleteId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showAdminToast(data.message || 'Subject removed.', 'success');
                if (subjectDeleteModal) subjectDeleteModal.hide();
                state.pendingDeleteId = null;
                state.pendingDeleteDoc = null;
                loadCurriculumData();
            } else {
                showAdminToast(data.message || 'Error deleting subject.', 'error');
            }
        } catch (err) {
            showAdminToast(err.message || 'Error deleting subject.', 'error');
        }
    }

    // =========================================================================
    // 10. TOAST UTILITY & HELPERS
    // =========================================================================

    function showAdminToast(msg, type = 'info') {
        if (window.showToast) {
            window.showToast(msg, type);
            return;
        }
        let container = document.getElementById('adminToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'adminToastContainer';
            container.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm pointer-events-none';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        const bg = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-red-600' : 'bg-[#171D3A]');
        toast.className = `${bg} text-white text-xs font-semibold px-4 py-3 rounded-2xl shadow-xl pointer-events-auto flex items-center justify-between gap-3 transition transform duration-200 translate-y-2 opacity-0`;
        toast.innerHTML = `<span>${escapeHtml(msg)}</span><button class="opacity-70 hover:opacity-100">&times;</button>`;

        toast.querySelector('button').onclick = () => toast.remove();
        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-2', 'opacity-0');
        });

        setTimeout(() => {
            toast.classList.add('translate-y-2', 'opacity-0');
            setTimeout(() => toast.remove(), 200);
        }, 3500);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeQuotes(str) {
        if (!str) return '';
        return String(str).replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

})();
