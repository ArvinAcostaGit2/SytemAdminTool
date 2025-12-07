

        // Populate dropdown on page load
        function loadCredentials() {
            const dropdown = document.getElementById('programDropdown');
            dropdown.innerHTML = '<option selected value="">-- Select a Program --</option>';
            
            credentialsData.forEach((cred, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = cred.Program;
                dropdown.appendChild(option);
            });
        }

        // Enable/Disable dropdown based on NT Account
        function checkNTAccountAndToggleDropdown() {
            const ntAccount = document.getElementById('ntAccount').value.trim();
            const dropdown = document.getElementById('programDropdown');
            
            if (ntAccount) {
                dropdown.disabled = false;
            } else {
                dropdown.disabled = true;
                dropdown.value = '';
            }
        }

        // Update fields when dropdown changes
        function updateFieldsFromDropdown() {
            const dropdown = document.getElementById('programDropdown');
            const selectedIndex = dropdown.value;
            
            if (selectedIndex !== '') {
                const selectedCred = credentialsData[selectedIndex];
                const ntAccount = document.getElementById('ntAccount').value.trim();
                
                // Update DC IP
                document.getElementById('dcIP').value = selectedCred.DomainControllerIP;
                
                // Extract domain prefix from DomainUsername (e.g., "DOMAIN\\demo_user" -> "DOMAIN")
                const domainPrefix = selectedCred.DomainUsername.split('\\')[0];
                
                // Combine domain prefix with NT Account
                if (ntAccount) {
                    document.getElementById('username').value = `${domainPrefix}\\${ntAccount}`;
                }
                
                // Update password
                document.getElementById('password').value = selectedCred.DomainPassword;
            } else {
                // Clear fields if no selection
                document.getElementById('dcIP').value = '';
                document.getElementById('username').value = '';
                document.getElementById('password').value = '';
            }
        }

        // Update username when NT Account changes
        function updateUsernameFromNTAccount() {
            const dropdown = document.getElementById('programDropdown');
            const selectedIndex = dropdown.value;
            const ntAccount = document.getElementById('ntAccount').value.trim();
            
            if (selectedIndex !== '' && ntAccount) {
                const selectedCred = credentialsData[selectedIndex];
                const domainPrefix = selectedCred.DomainUsername.split('\\')[0];
                document.getElementById('username').value = `${domainPrefix}\\${ntAccount}`;
            } else {
                document.getElementById('username').value = '';
            }
            
            checkNTAccountAndToggleDropdown();
        }

        // Clear all fields
        function clearAllFields() {
            document.getElementById('searchNames').value = '';
            document.getElementById('ntAccount').value = '';
            document.getElementById('dcIP').value = '';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            document.getElementById('programDropdown').value = '';
            document.getElementById('programDropdown').disabled = true;
            
            // Hide results section if visible
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('errorAlert').style.display = 'none';
        }

        // Toggle Domain Password Visibility
        function toggleDomainPasswordVisibility() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.getElementById('toggleDomainPasswordIcon');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.classList.remove('bi-eye');
                toggleIcon.classList.add('bi-eye-slash');
            } else {
                passwordInput.type = 'password';
                toggleIcon.classList.remove('bi-eye-slash');
                toggleIcon.classList.add('bi-eye');
            }
        }
        
        // Event Listeners
        document.addEventListener('DOMContentLoaded', function() {
            // Load credentials immediately
            loadCredentials();
            
            // NT Account input change
            document.getElementById('ntAccount').addEventListener('input', updateUsernameFromNTAccount);
            
            // Program dropdown change
            document.getElementById('programDropdown').addEventListener('change', updateFieldsFromDropdown);
            
            // Clear All button
            document.getElementById('clearAllBtn').addEventListener('click', function() {
                if (confirm('Are you sure you want to clear all fields? This will reset the form.')) {
                    clearAllFields();
                }
            });

            // Toggle Domain Password visibility
            document.getElementById('toggleDomainPasswordBtn').addEventListener('click', toggleDomainPasswordVisibility);

        });
