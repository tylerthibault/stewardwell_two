/* Modal Toggle JavaScript */
function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.toggle('active');
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}

// Copy to clipboard functionality
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Optional: Add visual feedback
    });
}

// PIN input validation for kid login
document.addEventListener('DOMContentLoaded', function() {
    const pinInputs = document.querySelectorAll('input[name="pin"]');
    pinInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    });

    // Also handle single PIN input validation (for kid quick login page)
    const pinInput = document.querySelector('input[type="password"][name="pin"]');
    if (pinInput) {
        pinInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    }
});
