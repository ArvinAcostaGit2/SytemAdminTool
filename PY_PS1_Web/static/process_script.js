    // ============================================
    // Global State Management
    // ============================================
    const state = {
        selectedUsers: new Set(),
        allUsers: [],
        selectedUserDetails: [],
        currentResetUser: null,
        currentUnlockUser: null
    };

    let ALL_CREDENTIALS = [];
    let currentCredentials = {};

    // ============================================
    // DOM Elements
    // ============================================
    const elements = {
        // Form elements
        searchForm: document.getElementById('searchForm'),
        searchButton: document.getElementById('searchButton'),
        searchNames: document.getElementById('searchNames'),
        programDropdown: document.getElementById('programDropdown'),
        dcIPInput: document.getElementById('dcIP'),
        usernameInput: document.getElementById('username'),
        passwordInput: document.getElementById('password'),
        
        // UI elements
        loadingOverlay: document.getElementById('loadingOverlay'),
        resultsSection: document.getElementById('resultsSection'),
        resultsTableBody: document.getElementById('resultsTableBody'),
        totalUsersCount: document.getElementById('totalUsersCount'),
        errorAlert: document.getElementById('errorAlert'),
        errorMessage: document.getElementById('errorMessage'),
        selectAllCheckbox: document.getElementById('selectAllCheckbox'),
        actionButtons: document.getElementById('actionButtons'),
        selectedCount: document.getElementById('selectedCount'),
        clearSelectionBtn: document.getElementById('clearSelectionBtn'),
        
        // Bulk disable modal
        bulkDisableBtn: document.getElementById('bulkDisableBtn'),
        ticketNumberInput: document.getElementById('ticketNumber'),
        proceedDisableBtn: document.getElementById('proceedDisableBtn'),
        modalUserCount: document.getElementById('modalUserCount'),
        modalUserList: document.getElementById('modalUserList'),
        
        // Reset password modal
        resetPasswordModal: document.getElementById('resetPasswordModal'),
        resetPasswordUsername: document.getElementById('resetPasswordUsername'),
        resetPasswordReference: document.getElementById('resetPasswordReference'),
        temporaryPasswordCheck: document.getElementById('temporaryPasswordCheck'),
        newPasswordInput: document.getElementById('newPasswordInput'),
        togglePasswordBtn: document.getElementById('togglePasswordBtn'),
        togglePasswordIcon: document.getElementById('togglePasswordIcon'),
        proceedResetPasswordBtn: document.getElementById('proceedResetPasswordBtn'),
        
        // Unlock modal
        unlockConfirmModal: document.getElementById('unlockConfirmModal'),
        unlockUsername: document.getElementById('unlockUsername'),
        unlockReference: document.getElementById('unlockReference'),
        proceedUnlockBtn: document.getElementById('proceedUnlockBtn')
    };

    // Bootstrap Modal Instances
    let disableModal;
    let resetPasswordModal;
    let unlockConfirmModal;

    // ============================================
    // Utility Functions
    // ============================================

    function showLoading() {
        elements.loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        elements.loadingOverlay.style.display = 'none';
    }

    function showError(message) {
        elements.errorMessage.innerHTML = message;
        elements.errorAlert.style.display = 'block';
        setTimeout(() => {
            elements.errorAlert.style.display = 'none';
        }, 10000);
    }

    function hideError() {
        elements.errorAlert.style.display = 'none';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || 'N/A';
        return div.innerHTML;
    }

    // ============================================
    // Credentials Management
    // ============================================

    async function initCredentialDropdown() {
        showLoading();
        try {
            const response = await fetch('/api/credentials');
            if (!response.ok) throw new Error('Failed to fetch credentials from server');
            
            ALL_CREDENTIALS = await response.json();
            
            ALL_CREDENTIALS.forEach(cred => {
                const option = document.createElement('option');
                option.value = cred.Program;
                option.textContent = cred.Program;
                elements.programDropdown.appendChild(option);
            });

            elements.programDropdown.addEventListener('change', handleProgramChange);
            
        } catch (error) {
            console.error("Error initializing credentials:", error);
            showError(`Credential initialization failed: ${error.message}`);
        } finally {
            hideLoading();
        }
    }

    function handleProgramChange() {
        const selectedProgram = elements.programDropdown.value;
        
        if (!selectedProgram) {
            elements.dcIPInput.value = '';
            elements.usernameInput.value = '';
            elements.passwordInput.value = '';
            return;
        }
        
        const selectedCred = ALL_CREDENTIALS.find(cred => cred.Program === selectedProgram);

        if (selectedCred) {
            elements.dcIPInput.value = selectedCred.DomainControllerIP || '';
            elements.usernameInput.value = selectedCred.DomainUsername || '';
            elements.passwordInput.value = selectedCred.DomainPassword || '';
        }
    }

    // ============================================
    // Selection Management
    // ============================================

    function updateSelectedCount() {
        const count = state.selectedUsers.size;
        elements.selectedCount.textContent = `${count} user${count !== 1 ? 's' : ''} selected`;
        elements.bulkDisableBtn.disabled = count === 0;
        elements.actionButtons.style.display = count > 0 ? 'block' : 'none';
    }

    function handleCheckboxChange(event) {
        const checkbox = event.target;
        const samAccountName = checkbox.dataset.sam;

        if (checkbox.checked) {
            state.selectedUsers.add(samAccountName);
        } else {
            state.selectedUsers.delete(samAccountName);
        }

        updateSelectedCount();
        updateSelectAllCheckbox();
    }

    function updateSelectAllCheckbox() {
        const activeCheckboxes = document.querySelectorAll('.user-checkbox:not(:disabled)');
        const checkedCount = document.querySelectorAll('.user-checkbox:checked').length;

        if (activeCheckboxes.length === 0) {
            elements.selectAllCheckbox.indeterminate = false;
            elements.selectAllCheckbox.checked = false;
        } else {
            elements.selectAllCheckbox.checked = checkedCount === activeCheckboxes.length;
            elements.selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < activeCheckboxes.length;
        }
    }

    elements.selectAllCheckbox.addEventListener('change', function () {
        const activeCheckboxes = document.querySelectorAll('.user-checkbox:not(:disabled)');

        activeCheckboxes.forEach(checkbox => {
            checkbox.checked = elements.selectAllCheckbox.checked;
            const sam = checkbox.dataset.sam;
            if (elements.selectAllCheckbox.checked) {
                state.selectedUsers.add(sam);
            } else {
                state.selectedUsers.delete(sam);
            }
        });

        updateSelectedCount();
    });

    elements.clearSelectionBtn.addEventListener('click', function () {
        document.querySelectorAll('.user-checkbox:checked').forEach(cb => cb.checked = false);
        state.selectedUsers.clear();
        elements.selectAllCheckbox.checked = false;
        elements.selectAllCheckbox.indeterminate = false;
        updateSelectedCount();
    });

    // ============================================
    // Reset Password Modal
    // ============================================

    window.resetPass = function(samAccountName) {
        state.currentResetUser = samAccountName;
        elements.resetPasswordUsername.textContent = samAccountName;
        elements.resetPasswordReference.value = '';
        elements.newPasswordInput.value = '';
        elements.temporaryPasswordCheck.checked = true;
        elements.proceedResetPasswordBtn.disabled = true;
        
        resetPasswordModal.show();
    }

    // Password visibility toggle
    elements.togglePasswordBtn.addEventListener('click', function() {
        const type = elements.newPasswordInput.type === 'password' ? 'text' : 'password';
        elements.newPasswordInput.type = type;
        
        if (type === 'text') {
            elements.togglePasswordIcon.classList.remove('bi-eye');
            elements.togglePasswordIcon.classList.add('bi-eye-slash');
        } else {
            elements.togglePasswordIcon.classList.remove('bi-eye-slash');
            elements.togglePasswordIcon.classList.add('bi-eye');
        }
    });

    // Validate reset password inputs
    function validateResetPasswordInputs() {
        const reference = elements.resetPasswordReference.value.trim();
        const password = elements.newPasswordInput.value.trim();
        elements.proceedResetPasswordBtn.disabled = !reference || !password;
    }

    elements.resetPasswordReference.addEventListener('input', validateResetPasswordInputs);
    elements.newPasswordInput.addEventListener('input', validateResetPasswordInputs);

    // Proceed with password reset
    elements.proceedResetPasswordBtn.addEventListener('click', async function() {
        const reference = elements.resetPasswordReference.value.trim();
        const newPassword = elements.newPasswordInput.value.trim();
        const isTemporary = elements.temporaryPasswordCheck.checked;

        if (!reference || !newPassword) {
            alert('❌ Please fill in all required fields!');
            return;
        }

        resetPasswordModal.hide();
        showLoading();

        const credentials = {
            dcIP: elements.dcIPInput.value.trim(),
            username: elements.usernameInput.value.trim(),
            password: elements.passwordInput.value,
        };

        try {
            if (!credentials.dcIP || !credentials.username || !credentials.password) {
                throw new Error("Credentials missing. Please select a program or enter details.");
            }

            const response = await fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    domain_controller_ip: credentials.dcIP,
                    username: credentials.username,
                    password: credentials.password,
                    sam_account_name: state.currentResetUser,
                    new_password: newPassword,
                    is_temporary: isTemporary,
                    reference: reference
                })
            });

            const result = await response.json();

            if (!response.ok) throw new Error(result.detail || 'Password reset failed');

            alert(result.success
                ? `✅ Password reset successful for: ${state.currentResetUser}\n${isTemporary ? 'User must change password at next logon.' : 'Permanent password set.'}`
                : `❌ Password reset failed: ${result.message}`
            );

        } catch (err) {
            showError(`Password reset operation failed: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // ============================================
    // Unlock Account Modal
    // ============================================

    window.unlockUser = function(samAccountName) {
        state.currentUnlockUser = samAccountName;
        elements.unlockUsername.textContent = samAccountName;
        elements.unlockReference.value = '';
        elements.proceedUnlockBtn.disabled = true;
        
        unlockConfirmModal.show();
    }

    // Validate unlock inputs
    elements.unlockReference.addEventListener('input', function() {
        const reference = elements.unlockReference.value.trim();
        elements.proceedUnlockBtn.disabled = !reference;
    });

    // Proceed with unlock
    elements.proceedUnlockBtn.addEventListener('click', async function() {
        const reference = elements.unlockReference.value.trim();

        if (!reference) {
            alert('❌ Reference/Ticket number is required!');
            return;
        }

        unlockConfirmModal.hide();
        showLoading();

        const credentials = {
            dcIP: elements.dcIPInput.value.trim(),
            username: elements.usernameInput.value.trim(),
            password: elements.passwordInput.value,
        };

        try {
            if (!credentials.dcIP || !credentials.username || !credentials.password) {
                throw new Error("Credentials missing. Please select a program or enter details.");
            }

            const response = await fetch('/api/unlock-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    domain_controller_ip: credentials.dcIP,
                    username: credentials.username,
                    password: credentials.password,
                    sam_account_name: state.currentUnlockUser,
                    reference: reference
                })
            });

            const result = await response.json();

            if (!response.ok) throw new Error(result.detail || 'Unlock failed');

            alert(result.success
                ? `✅ Successfully unlocked: ${state.currentUnlockUser}`
                : `❌ Unlock failed: ${result.message}`
            );

            if (result.success) {
                const row = document.querySelector(`tr[data-sam="${state.currentUnlockUser}"]`);
                if (row) {
                    const lockedCell = row.querySelector('td:nth-child(11)');
                    if (lockedCell) {
                        lockedCell.innerHTML = '<span class="badge bg-secondary">Not Locked</span>';
                    }
                    const unlockBtn = row.querySelector('.btn-unlock');
                    if (unlockBtn) unlockBtn.remove();
                }
            }

        } catch (err) {
            showError(`Unlock operation failed: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // ============================================
    // Bulk Disable Functionality
    // ============================================

    elements.bulkDisableBtn.addEventListener('click', function() {
        if (state.selectedUsers.size === 0) {
            alert('⚠️ No users selected. Please select at least one user to disable.');
            return;
        }

        state.selectedUserDetails = state.allUsers.filter(user => 
            state.selectedUsers.has(user.SamAccountName)
        );

        elements.modalUserCount.textContent = state.selectedUserDetails.length;
        
        const userListHTML = `
            <strong>Users to be disabled:</strong>
            <ul class="mt-2">
                ${state.selectedUserDetails.map(user => 
                    `<li><strong>${escapeHtml(user.Name)}</strong> (${escapeHtml(user.SamAccountName)})</li>`
                ).join('')}
            </ul>
        `;
        elements.modalUserList.innerHTML = userListHTML;

        disableModal.show();
    });

    elements.ticketNumberInput.addEventListener('input', function() {
        const ticketValue = this.value.trim();
        elements.proceedDisableBtn.disabled = ticketValue === '';
    });

    elements.proceedDisableBtn.addEventListener('click', async function() {
        const ticketNumber = elements.ticketNumberInput.value.trim();

        if (!ticketNumber) {
            alert('❌ Ticket number is required!');
            return;
        }

        disableModal.hide();
        showLoading();
        
        const submissionCredentials = {
            dcIP: elements.dcIPInput.value.trim(),
            username: elements.usernameInput.value.trim(),
            password: elements.passwordInput.value,
        };

        try {
            const response = await fetch('/api/bulk-disable-users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    domain_controller_ip: submissionCredentials.dcIP,
                    username: submissionCredentials.username,
                    password: submissionCredentials.password,
                    user_accounts: Array.from(state.selectedUsers),
                    ticket_number: ticketNumber,
                    user_details: state.selectedUserDetails
                })
            });

            const result = await response.json();

            if (!response.ok) throw new Error(result.detail || 'Bulk disable failed');

            let message = `✅ Bulk Disable Complete:\n\n`;
            message += `Ticket Number: ${ticketNumber}\n`;
            message += `Total: ${result.total}\n`;
            message += `Succeeded: ${result.succeeded}\n`;
            message += `Failed: ${result.failed}\n\n`;

            if (result.failed > 0) {
                message += `Failed accounts:\n`;
                result.results
                    .filter(r => !r.success)
                    .forEach(r => {
                        message += `• ${r.user}: ${r.error}\n`;
                    });
            }

            alert(message);

            result.results.forEach(r => {
                if (r.success) {
                    const row = document.querySelector(`tr[data-sam="${r.user}"]`);
                    if (row) {
                        const statusCell = row.querySelector('td:nth-child(9)');
                        if (statusCell) {
                            statusCell.innerHTML = '<span class="badge bg-danger">Disabled</span>';
                        }
                        const checkbox = row.querySelector('.user-checkbox');
                        if (checkbox) {
                            checkbox.checked = false;
                            checkbox.disabled = true;
                            checkbox.title = 'Disabled accounts cannot be selected';
                        }
                        state.selectedUsers.delete(r.user);
                    }
                }
            });

            updateSelectedCount();
            updateSelectAllCheckbox();

        } catch (err) {
            showError(`Bulk disable operation failed: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // ============================================
    // Search Functionality
    // ============================================

    async function performSearch() {
        hideError();
        
        const dcIP = elements.dcIPInput.value.trim();
        const username = elements.usernameInput.value.trim();
        const password = elements.passwordInput.value;
        const rawSearchInput = elements.searchNames.value.trim();

        if (rawSearchInput.length === 0) {
            showError('Please enter at least one line of search data.');
            return;
        }

        if (!dcIP || !username || !password) {
            showError('Please fill in all credential fields (DC IP, Username, and Password).');
            return;
        }
        
        currentCredentials = { dcIP, username, password };

        const payload = {
            domain_controller_ip: dcIP,
            username: username,
            password: password,
            raw_search_input: rawSearchInput 
        };

        showLoading();

        try {
            const response = await fetch('/api/search-users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Server error');
            }

            if (data.errors && data.errors.length > 0) {
                const list = data.errors.map(e => `<li>${escapeHtml(e)}</li>`).join('');
                showError(`<strong>Partial failures:</strong><ul class="mb-0 mt-2">${list}</ul>`);
            }

            renderResults(data.users || []);
            
        } catch (err) {
            showError(`<strong>Connection/Search Failed:</strong> ${err.message}`);
            console.error(err);
        } finally {
            hideLoading();
        }
    }

    elements.searchButton.addEventListener('click', performSearch);

    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            performSearch();
        }
    });

    // ============================================
    // Render Results
    // ============================================

    function renderResults(users) {
        elements.resultsTableBody.innerHTML = '';
        state.allUsers = users;
        state.selectedUsers.clear();
        updateSelectedCount();

        if (users.length === 0) {
            elements.resultsTableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center text-muted py-5">
                        <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                        <p class="mt-3 mb-0">No users found matching your search criteria</p>
                    </td>
                </tr>`;
            elements.totalUsersCount.textContent = '0 users found';
            elements.resultsSection.style.display = 'block';
            return;
        }

        users.forEach(user => {
            const isDisabled = user.IsDisabled;
            const isLocked = user.IsLocked;

            const statusBadge = isDisabled
                ? '<span class="badge bg-danger">Disabled</span>'
                : '<span class="badge bg-success">Active</span>';

            const lockedBadge = isLocked
                ? '<span class="badge bg-warning text-dark badge-locked">Locked Out</span>'
                : '<span class="badge bg-secondary">Not Locked</span>';

            const canSelect = !isDisabled;
            
            // Reset Password button - always visible for active accounts
            const resetPasswordButton = !isDisabled
                ? `<button class="btn btn-sm btn-primary btn-resetpass" onclick="resetPass('${user.SamAccountName}')">
                        <i class="bi bi-arrow-clockwise"></i> Reset
                   </button>`
                : '<span class="text-muted">-</span>';

            // Unlock button - only visible for locked AND active accounts
            const unlockButton = isLocked && !isDisabled
                ? `<button class="btn btn-sm btn-warning btn-unlock" onclick="unlockUser('${user.SamAccountName}')">
                        <i class="bi bi-unlock"></i> Unlock
                   </button>`
                : '';

            const checkboxHtml = canSelect
                ? `<input type="checkbox" class="form-check-input user-checkbox" data-sam="${user.SamAccountName}">`
                : `<input type="checkbox" class="form-check-input" disabled title="Disabled accounts cannot be selected">`;

            const row = document.createElement('tr');
            row.dataset.sam = user.SamAccountName;
            
            row.innerHTML = `
                <td class="checkbox-col text-center">${checkboxHtml}</td>
                <td>${escapeHtml(user.CustomField1)}</td>
                <td>${escapeHtml(user.CustomField2)}</td>
                <td>${escapeHtml(user.CustomField4)}</td>
                <td>${escapeHtml(user.CustomField3)}</td>
                <td><strong>${escapeHtml(user.Name)}</strong></td>
                <td><code>${escapeHtml(user.SamAccountName)}</code></td>
                <td>${escapeHtml(user.UserPrincipalName)}</td>
                <td>${statusBadge}</td>
                <td>${resetPasswordButton}</td>
                <td>${lockedBadge}</td>
                <td>${unlockButton}</td>
            `;

            elements.resultsTableBody.appendChild(row);
        });

        document.querySelectorAll('.user-checkbox:not(:disabled)').forEach(cb => {
            cb.addEventListener('change', handleCheckboxChange);
        });

        elements.totalUsersCount.textContent = `${users.length} user${users.length !== 1 ? 's' : ''} found`;
        elements.resultsSection.style.display = 'block';
        updateSelectAllCheckbox();
        elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // ============================================
    // Initialize Application
    // ============================================

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize Bootstrap modals
        disableModal = new bootstrap.Modal(document.getElementById('disableConfirmModal'));
        resetPasswordModal = new bootstrap.Modal(document.getElementById('resetPasswordModal'));
        unlockConfirmModal = new bootstrap.Modal(document.getElementById('unlockConfirmModal'));
        
        // Initialize credentials dropdown
        initCredentialDropdown();

        // Reset modal states when closed
        document.getElementById('disableConfirmModal').addEventListener('hidden.bs.modal', function() {
            elements.ticketNumberInput.value = '';
            elements.proceedDisableBtn.disabled = true;
        });

        document.getElementById('resetPasswordModal').addEventListener('hidden.bs.modal', function() {
            elements.resetPasswordReference.value = '';
            elements.newPasswordInput.value = '';
            elements.temporaryPasswordCheck.checked = true;
            elements.newPasswordInput.type = 'password';
            elements.togglePasswordIcon.classList.remove('bi-eye-slash');
            elements.togglePasswordIcon.classList.add('bi-eye');
        });

        document.getElementById('unlockConfirmModal').addEventListener('hidden.bs.modal', function() {
            elements.unlockReference.value = '';
            elements.proceedUnlockBtn.disabled = true;
        });
    });