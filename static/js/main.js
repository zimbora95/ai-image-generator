document.getElementById('style-category').addEventListener('change', function() {
    const category = this.value;
    fetch('/get_styles', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ category: category })
    })
    .then(response => response.json())
    .then(data => {
        const styleSelect = document.getElementById('style');
        styleSelect.innerHTML = ''; // Clear existing options
        for (const style in data) {
            const option = document.createElement('option');
            option.value = style;
            option.textContent = style;
            styleSelect.appendChild(option);
        }
    })
    .catch(error => console.error('Error fetching styles:', error));
}); 