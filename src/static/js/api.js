/**
 * Simple API utility for handling AJAX requests
 * Keeps things simple and direct - no page jumps!
 */

/**
 * Submit a form via AJAX and handle the response
 * @param {HTMLFormElement} form - The form to submit
 * @param {Object} options - Optional callbacks and config
 * @returns {Promise}
 */
async function submitForm(form, options = {}) {
    const formData = new FormData(form);
    const action = form.getAttribute('action') || form.action;
    const method = form.getAttribute('method') || form.method || 'POST';
    
    try {
        const response = await fetch(action, {
            method: method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            if (options.onSuccess) {
                options.onSuccess(data);
            }
        } else {
            showMessage(data.message, 'error');
            if (options.onError) {
                options.onError(data);
            }
        }
        
        return data;
    } catch (error) {
        console.error('Form submission error:', error);
        showMessage('An error occurred. Please try again.', 'error');
        if (options.onError) {
            options.onError(error);
        }
        throw error;
    }
}

/**
 * Make a POST request to an endpoint
 * @param {string} url - The endpoint URL
 * @param {Object} data - Optional data to send
 * @param {Object} options - Optional callbacks
 * @returns {Promise}
 */
async function postRequest(url, data = {}, options = {}) {
    const formData = new FormData();
    Object.keys(data).forEach(key => {
        formData.append(key, data[key]);
    });
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            if (options.onSuccess) {
                options.onSuccess(result);
            }
        } else {
            showMessage(result.message, 'error');
            if (options.onError) {
                options.onError(result);
            }
        }
        
        return result;
    } catch (error) {
        console.error('Request error:', error);
        showMessage('An error occurred. Please try again.', 'error');
        if (options.onError) {
            options.onError(error);
        }
        throw error;
    }
}

/**
 * Show a message to the user (flash message style)
 * @param {string} message - The message to display
 * @param {string} type - Message type: 'success', 'error', 'info', 'warning'
 */
function showMessage(message, type = 'info') {
    // Remove any existing messages
    const existing = document.querySelector('.flash-message-dynamic');
    if (existing) {
        existing.remove();
    }
    
    // Create new message element
    const messageEl = document.createElement('div');
    messageEl.className = `flash-message-dynamic flash-${type}`;
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? 'var(--accent-primary, #4CAF50)' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        border-radius: 4px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
        font-weight: 600;
    `;
    
    // Add animation keyframes if not already added
    if (!document.getElementById('flash-animation-styles')) {
        const style = document.createElement('style');
        style.id = 'flash-animation-styles';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(messageEl);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        messageEl.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => messageEl.remove(), 300);
    }, 5000);
}

/**
 * Setup form to submit via AJAX
 * @param {string|HTMLFormElement} formSelector - Form selector or element
 * @param {Object} options - Optional callbacks and config
 */
function setupAjaxForm(formSelector, options = {}) {
    const form = typeof formSelector === 'string' 
        ? document.querySelector(formSelector) 
        : formSelector;
    
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        await submitForm(form, options);
        
        // Reset form if specified
        if (options.resetOnSuccess !== false) {
            form.reset();
        }
        
        // Close modal if specified
        if (options.closeModal) {
            const modalId = options.closeModal;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('active');
            }
        }
    });
}

/**
 * Remove an element from DOM with optional animation
 * @param {HTMLElement} element - Element to remove
 * @param {boolean} animate - Whether to animate removal
 */
function removeElement(element, animate = true) {
    if (!element) return;
    
    if (animate) {
        element.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
        element.style.opacity = '0';
        element.style.transform = 'scale(0.9)';
        setTimeout(() => element.remove(), 300);
    } else {
        element.remove();
    }
}

/**
 * Update text content of an element
 * @param {string} selector - Element selector
 * @param {string} content - New content
 */
function updateContent(selector, content) {
    const element = document.querySelector(selector);
    if (element) {
        element.textContent = content;
    }
}
