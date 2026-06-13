document.addEventListener("DOMContentLoaded", function() {
    const tables = document.querySelectorAll(".datatable");
    
    tables.forEach(table => {
        const dt = new simpleDatatables.DataTable(table, {
            searchable: true,
            fixedHeight: true,
            perPage: 10,
        });

        dt.on('datatable.init', function() {
            const wrapper = table.closest('.dataTable-wrapper');
            const select = wrapper.querySelector('.dataTable-selector');
            if (!select || select.dataset.customized) return;
            select.dataset.customized = 'true';
            
            // Hide native select
            select.style.display = 'none';
            
            // Create custom dropdown container
            const customDropdown = document.createElement('div');
            customDropdown.className = 'custom-dropdown';
            customDropdown.style.display = 'inline-block';
            customDropdown.style.verticalAlign = 'middle';
            customDropdown.style.marginRight = '8px';
            
            // Create selected display
            const selected = document.createElement('div');
            selected.className = 'custom-dropdown-selected';
            selected.innerHTML = `${select.options[select.selectedIndex].text} <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>`;
            
            // Create options list
            const optionsList = document.createElement('ul');
            optionsList.className = 'custom-dropdown-options';
            
            Array.from(select.options).forEach(opt => {
                const li = document.createElement('li');
                li.textContent = opt.text;
                li.dataset.value = opt.value;
                if (opt.selected) li.className = 'active';
                
                li.addEventListener('click', function(e) {
                    selected.innerHTML = `${this.textContent} <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>`;
                    
                    // Update active class
                    Array.from(optionsList.querySelectorAll('li')).forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Update native select and trigger change
                    select.value = this.dataset.value;
                    select.dispatchEvent(new Event('change'));
                    
                    customDropdown.classList.remove('open');
                    e.stopPropagation();
                });
                optionsList.appendChild(li);
            });
            
            selected.addEventListener('click', function(e) {
                // Close other open dropdowns
                document.querySelectorAll('.custom-dropdown.open').forEach(d => {
                    if (d !== customDropdown) d.classList.remove('open');
                });
                customDropdown.classList.toggle('open');
                e.stopPropagation();
            });
            
            customDropdown.appendChild(selected);
            customDropdown.appendChild(optionsList);
            
            // Insert custom dropdown before native select
            select.parentNode.insertBefore(customDropdown, select);
            
            // Re-label text node next to select if it exists
            const nextNode = customDropdown.nextSibling;
            if (nextNode && nextNode.nodeType === Node.TEXT_NODE && nextNode.textContent.trim() === 'entries per page') {
                nextNode.textContent = ' entries per page';
            }
            
            // Close when clicking outside
            document.addEventListener('click', function(e) {
                if (!customDropdown.contains(e.target)) {
                    customDropdown.classList.remove('open');
                }
            });
        });
    });
});
