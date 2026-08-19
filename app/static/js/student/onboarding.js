document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons Safely
    if (window.lucide) {
        lucide.createIcons();
    }

    // 2. Profile Photo Instant Preview JS
    const photoInput = document.getElementById('profile_photo_input');
    const avatarPreview = document.getElementById('avatar-preview');
    const headerAvatar = document.getElementById('header-avatar');

    if (photoInput) {
        photoInput.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    // Update both main preview image & top header avatar preview
                    if (avatarPreview) avatarPreview.src = event.target.result;
                    if (headerAvatar) headerAvatar.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 3. Interactive Skills Tags Input
    const tagInput = document.getElementById('skill-input');
    const tagsWrapper = document.getElementById('tags-wrapper');
    const hiddenSkillsInput = document.getElementById('hidden-skills-input');

    if (tagInput && tagsWrapper && hiddenSkillsInput) {
        // Parse initial value safely (filters out empty/whitespace elements)
        let skillsList = hiddenSkillsInput.value
            ? hiddenSkillsInput.value.split(',').map(s => s.trim()).filter(Boolean)
            : [];

        function updateSkillsHiddenField() {
            hiddenSkillsInput.value = skillsList.join(',');
        }

        // Handle adding skills on Enter key press
        tagInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const newSkill = tagInput.value.trim();

                if (newSkill && !skillsList.includes(newSkill)) {
                    skillsList.push(newSkill);

                    // Create Tag HTML Element
                    const newTag = document.createElement('span');
                    newTag.className = 'skill-tag';
                    newTag.innerHTML = `${newSkill} <i data-lucide="x" class="remove-tag"></i>`;

                    // Insert tag right before the text input element
                    tagsWrapper.insertBefore(newTag, tagInput);
                    tagInput.value = '';

                    updateSkillsHiddenField();

                    // Re-render Lucide icons for newly inserted 'x' button
                    if (window.lucide) {
                        lucide.createIcons();
                    }
                }
            }
        });

        // Handle removing skills when clicking 'X'
        tagsWrapper.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('.remove-tag');
            if (removeBtn) {
                const tagElement = removeBtn.closest('.skill-tag');
                if (tagElement) {
                    // Extract tag name excluding icon text/markup
                    const skillName = tagElement.firstChild.textContent.trim();

                    skillsList = skillsList.filter(s => s !== skillName);
                    tagElement.remove();
                    updateSkillsHiddenField();
                }
            }
        });
    }
});