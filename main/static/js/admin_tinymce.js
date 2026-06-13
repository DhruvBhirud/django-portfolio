document.addEventListener('DOMContentLoaded', function() {
    const editors = document.querySelectorAll('.rich-text-editor');
    editors.forEach(textarea => {
        const uploadUrl = textarea.getAttribute('data-upload-url');
        tinymce.init({
            target: textarea,
            plugins: 'image link media table code lists',
            toolbar: 'undo redo | blocks | bold italic | alignleft aligncenter alignright | bullist numlist | link image | code',
            images_upload_url: uploadUrl || '',
            automatic_uploads: true,
            height: 600,
            content_style: 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 16px; line-height: 1.6; }'
        });
    });
});
