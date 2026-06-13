document.addEventListener("DOMContentLoaded", function() {
    function createCustomDropdown(select) {
        if (!select || select.dataset.customized) return;
        select.dataset.customized = 'true';
        
        select.style.display = 'none';
        
        const customDropdown = document.createElement('div');
        customDropdown.className = 'custom-dropdown';
        
        const selected = document.createElement('div');
        selected.className = 'custom-dropdown-selected';
        const initialText = select.options.length > 0 && select.selectedIndex >= 0 ? select.options[select.selectedIndex].text : '';
        selected.innerHTML = `${initialText} <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>`;
        
        const optionsList = document.createElement('ul');
        optionsList.className = 'custom-dropdown-options';
        
        Array.from(select.options).forEach(opt => {
            const li = document.createElement('li');
            li.textContent = opt.text;
            li.dataset.value = opt.value;
            if (opt.selected) li.className = 'active';
            
            li.addEventListener('click', function(e) {
                selected.innerHTML = `${this.textContent} <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>`;
                Array.from(optionsList.querySelectorAll('li')).forEach(l => l.classList.remove('active'));
                this.classList.add('active');
                
                select.value = this.dataset.value;
                select.dispatchEvent(new Event('change'));
                
                customDropdown.classList.remove('open');
                e.stopPropagation();
            });
            optionsList.appendChild(li);
        });
        
        select.addEventListener('change', function() {
            const currentSelected = Array.from(select.options).find(opt => opt.selected);
            if (currentSelected) {
                selected.innerHTML = `${currentSelected.text} <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>`;
                Array.from(optionsList.querySelectorAll('li')).forEach(l => {
                    l.classList.toggle('active', l.dataset.value === currentSelected.value);
                });
            }
        });
        
        selected.addEventListener('click', function(e) {
            document.querySelectorAll('.custom-dropdown.open').forEach(d => {
                if (d !== customDropdown) d.classList.remove('open');
            });
            customDropdown.classList.toggle('open');
            e.stopPropagation();
        });
        
        customDropdown.appendChild(selected);
        customDropdown.appendChild(optionsList);
        
        select.parentNode.insertBefore(customDropdown, select);
        
        // Clean up "entries per page" text node to have better spacing
        const nextNode = customDropdown.nextSibling;
        if (nextNode && nextNode.nodeType === Node.TEXT_NODE && nextNode.textContent.includes('entries per page')) {
            nextNode.textContent = ' entries per page';
        }
        
        document.addEventListener('click', function(e) {
            if (!customDropdown.contains(e.target)) {
                customDropdown.classList.remove('open');
            }
        });
    }

    const tables = document.querySelectorAll(".datatable");
    
    tables.forEach(table => {
        const dt = new simpleDatatables.DataTable(table, {
            searchable: true,
            fixedHeight: true,
            perPage: 10,
        });

        // DataTable initializes synchronously, apply styling to the generated select
        const wrapper = table.closest('.dataTable-wrapper') || table.parentNode.closest('.dataTable-wrapper');
        if (wrapper) {
            const select = wrapper.querySelector('.dataTable-selector');
            createCustomDropdown(select);
        }
    });
});
