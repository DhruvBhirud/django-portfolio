document.addEventListener("DOMContentLoaded", function() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    function toggleMenu() {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
        
        const isOpen = sidebar.classList.contains('active');
        if (isOpen) {
            menuToggle.innerHTML = '<i class="fas fa-times"></i>';
        } else {
            menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    }
    
    if (menuToggle && sidebar && overlay) {
        menuToggle.addEventListener('click', toggleMenu);
        overlay.addEventListener('click', toggleMenu);
    }
    
    // Close sidebar when links are clicked on mobile
    const navLinks = sidebar.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
                toggleMenu();
            }
        });
    });
    
    // Highlight active menu item
    const currentPath = window.location.pathname;
    sidebar.querySelectorAll('a').forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            if (href === '/admin/') {
                if (currentPath === '/admin/') {
                    link.classList.add('active');
                }
            } else if (href !== '/' && currentPath.startsWith(href)) {
                link.classList.add('active');
            }
        }
    });
});
