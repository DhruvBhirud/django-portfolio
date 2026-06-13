document.addEventListener("DOMContentLoaded", function() {
    fetch('https://cdn.jsdelivr.net/gh/devicons/devicon@latest/devicon.json')
    .then(response => response.json())
    .then(data => {
        const datalist = document.getElementById('devicon-list');
        if (!datalist) return;
        
        data.forEach(icon => {
            if (icon.versions && icon.versions.font && icon.versions.font.length > 0) {
                let version = icon.versions.font.includes('plain') ? 'plain' : icon.versions.font[0];
                let className = `devicon-${icon.name}-${version} colored`;
                let option = document.createElement('option');
                option.value = className;
                // Provide a recognizable display name for the dropdown natively
                option.textContent = icon.name.charAt(0).toUpperCase() + icon.name.slice(1);
                datalist.appendChild(option);
            }
        });
    })
    .catch(error => console.error("Error loading devicon JSON:", error));
});
