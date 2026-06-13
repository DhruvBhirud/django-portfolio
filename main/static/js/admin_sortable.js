document.addEventListener("DOMContentLoaded", function() {
    const sortableLists = document.querySelectorAll('.sortable-list');
    
    sortableLists.forEach(function(el) {
        const reorderUrl = el.getAttribute('data-reorder-url');
        
        let handleClass = '.fa-grip-vertical';
        if (el.querySelector('.handle')) {
            handleClass = '.handle';
        }

        Sortable.create(el, {
            handle: handleClass,
            animation: 150,
            onEnd: function (evt) {
                var activeOrder = [];
                el.querySelectorAll('[data-id]').forEach(function(row) {
                    activeOrder.push(row.getAttribute('data-id'));
                });
                
                if (!reorderUrl) return;

                fetch(reorderUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(activeOrder)
                })
                .then(response => {
                    if (response.headers.get('content-type')?.includes('application/json')) {
                        return response.json().then(data => ({ ok: response.ok, data }));
                    }
                    return { ok: response.ok, data: {} };
                })
                .then(result => {
                    if (!result.ok || (result.data.status && result.data.status !== 'success')) {
                        console.error("Error saving sort order", result);
                        alert("Failed to save reordered list.");
                    }
                })
                .catch(error => {
                    console.error("Fetch error:", error);
                    alert("Error saving sort order.");
                });
            }
        });
    });
});
