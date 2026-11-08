/**
 * Toast / Notification System - UniOCR
 * Unified toast/notification system with accessibility support
 */

// Toast Container Component
class ToastContainer extends HTMLElement {
  static get observedAttributes() { return ['position']; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.toasts = [];
    this.position = 'top-right';
    this.maxToasts = 5;
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback() {
    this.render();
  }

  get position() { return this.getAttribute('position') || 'top-right'; }

  set position(val) { this.setAttribute('position', val); }

  render() {
    const positions = {
      'top-right': 'top: 1rem; right: 1rem;',
      'top-left': 'top: 1rem; left: 1rem;',
      'bottom-right': 'bottom: 1rem; right: 1rem;',
      'bottom-left': 'bottom: 1rem; left: 1rem;',
      'top-center': 'top: 1rem; left: 50%; transform: translateX(-50%);',
      'bottom-center': 'bottom: 1rem; left: 50%; transform: translateX(-50%);'
    };

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .toast-container {
          position: fixed;
          ${positions[this.position] || positions['top-right']}
          z-index: 9999;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          pointer-events: none;
          max-width: 360px;
        }
        .toast {
          pointer-events: auto;
          background: var(--surface-base, #fff);
          border: 1px solid var(--neutral-200, #e5e7eb);
          border-radius: var(--r-md, 0.5rem);
          padding: 0.875rem 1rem;
          box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0,0,0,0.1));
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          min-width: 280px;
          max-width: 360px;
          animation: slideIn 0.3s ease-out;
          position: relative;
        }
        .toast.closing { animation: slideOut 0.2s ease-in forwards; }
        @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes slideOut { from { opacity: 1; transform: translateX(0); } to { opacity: 0; transform: translateX(20px); } }
        .toast__icon { flex-shrink: 0; width: 1.25rem; height: 1.25rem; display: flex; align-items: center; justify-content: center; }
        .toast__content { flex: 1; min-width: 0; }
        .toast__title { font-weight: 600; font-size: 0.875rem; color: var(--neutral-900, #111827); margin-bottom: 0.125rem; }
        .toast__message { font-size: 0.8125rem; color: var(--neutral-600, #4b5563); line-height: 1.5; }
        .toast__close { flex-shrink: 0; padding: 0.25rem; color: var(--neutral-400, #9ca3af); background: none; border: none; cursor: pointer; line-height: 1; }
        .toast__close:hover { color: var(--neutral-600, #4b5563); }
        .toast--success { border-left: 4px solid var(--semantic-success, #22c55e); }
        .toast--error { border-left: 4px solid var(--semantic-error, #ef4444); }
        .toast--warning { border-left: 4px solid var(--semantic-warning, #f59e0b); }
        .toast--info { border-left: 4px solid var(--brand-secondary, #0891b2); }
        .toast__progress { position: absolute; bottom: 0; left: 0; height: 3px; background: currentColor; opacity: 0.3; border-radius: 0 0 var(--r-md, 0.5rem) var(--r-md, 0.5rem) 0; animation: progressBar linear forwards; }
        @keyframes progressBar { from { width: 100%; } to { width: 0%; } }
        @media (prefers-reduced-motion: reduce) { .toast { animation: none; } .toast__progress { animation: none; } }
        [data-theme="dark"] .toast { background: var(--surface-base, #1f2937); border-color: var(--neutral-700, #374151); }
      </style>
      <div class="toast-container" id="container" role="region" aria-live="polite" aria-label="Notifications"></div>
    `;
  }

  /**
   * Show a toast notification
   * @param {Object} options
   * @param {string} options.type - 'success' | 'error' | 'warning' | 'info'
   * @param {string} options.title - Toast title
   * @param {string} [options.message] - Optional message
   * @param {number} [options.duration=5000] - Auto-dismiss duration in ms
   * @param {boolean} [options.dismissible=true] - Allow manual dismiss
   * @returns {string} Toast ID
   */
  show({ type = 'info', title, message = '', duration = 5000, dismissible = true } = {}) {
    if (!['success', 'error', 'warning', 'info'].includes(type)) type = 'info';
    duration = Number.isFinite(duration) ? Math.min(60000, Math.max(0, duration)) : 5000;
    const container = this.shadowRoot.getElementById('container');
    if (this.toasts.length >= this.maxToasts) {
      this.remove(this.toasts[0].id);
    }

    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const icons = {
      success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
      error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
      warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="15"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`
    };

    const toastEl = document.createElement('div');
    toastEl.className = `toast toast--${type}`;
    toastEl.dataset.toastId = id;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'polite');
    toastEl.setAttribute('aria-atomic', 'true');

    const progressDuration = duration;
    toastEl.innerHTML = `
      <div class="toast__icon" aria-hidden="true">${icons[type] || icons.info}</div>
      <div class="toast__content">
        <div class="toast__title">${esc(title)}</div>
        ${message ? `<div class="toast__message">${esc(message)}</div>` : ''}
      </div>
      ${dismissible ? `<button class="toast__close" aria-label="Fermer" data-toast-close="${id}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>` : ''}
      <div class="toast__progress" style="animation-duration: ${duration}ms; color: ${getProgressColor(type)};"></div>
    `;

    container.appendChild(toastEl);

    // Track toast
    this.toasts.push({ id, element: toastEl, timeout: null });

    // Auto-dismiss
    if (duration > 0) {
      const timeout = setTimeout(() => this.remove(id), duration);
      this.toasts[this.toasts.length - 1].timeout = timeout;

      // Progress bar animation
      const progressBar = toastEl.querySelector('.toast__progress');
      if (progressBar) {
        progressBar.style.animationDuration = `${duration}ms`;
      }
    }

    // Close button
    if (dismissible) {
      const closeBtn = toastEl.querySelector('[data-toast-close]');
      closeBtn.addEventListener('click', () => this.remove(id));
    }

    // Pause on hover
    toastEl.addEventListener('mouseenter', () => {
      const progressBar = toastEl.querySelector('.toast__progress');
      if (progressBar) progressBar.style.animationPlayState = 'paused';
    });
    toastEl.addEventListener('mouseleave', () => {
      const progressBar = toastEl.querySelector('.toast__progress');
      if (progressBar) progressBar.style.animationPlayState = 'running';
    });

    return id;
  }

  remove(id) {
    const toast = this.toasts.find(t => t.id === id);
    if (!toast) return;

    if (toast.timeout) clearTimeout(toast.timeout);
    toast.element.classList.add('closing');
    toast.element.addEventListener('animationend', () => {
      toast.element.remove();
      this.toasts = this.toasts.filter(t => t.id !== id);
    }, { once: true });
  }

  // Convenience methods
  success(title, message, options) { return this.show({ type: 'success', title, message, ...options }); }
  error(title, message, options) { return this.show({ type: 'error', title, message, ...options }); }
  warning(title, message, options) { return this.show({ type: 'warning', title, message, ...options }); }
  info(title, message, options) { return this.show({ type: 'info', title, message, ...options }); }
}

// Utility functions
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getProgressColor(type) {
  const colors = {
    success: 'var(--semantic-success, #22c55e)',
    error: 'var(--semantic-error, #ef4444)',
    warning: 'var(--semantic-warning, #f59e0b)',
    info: 'var(--brand-secondary, #0891b2)'
  };
  return colors[type] || colors.info;
}

// Register component
if (!customElements.get('ocr-toast-container')) {
  customElements.define('ocr-toast-container', ToastContainer);
}

// Global toast API (for easy use from anywhere)
window.UniOCRToast = {
  success: (title, message, options) => {
    const container = document.querySelector('ocr-toast-container');
    return container?.show({ type: 'success', title, message, ...options });
  },
  error: (title, message, options) => {
    const container = document.querySelector('ocr-toast-container');
    return container?.show({ type: 'error', title, message, ...options });
  },
  warning: (title, message, options) => {
    const container = document.querySelector('ocr-toast-container');
    return container?.show({ type: 'warning', title, message, ...options });
  },
  info: (title, message, options) => {
    const container = document.querySelector('ocr-toast-container');
    return container?.show({ type: 'info', title, message, ...options });
  }
};

// Keep the legacy callable toast(msg, type) API; never replace it with an object.
if (typeof window.toast === 'function') {
  Object.assign(window.toast, window.UniOCRToast);
} else {
  window.toast = Object.assign(function (message, type) {
    const kind = type === 'ok' ? 'success' : type === 'err' ? 'error' : type;
    return document.querySelector('ocr-toast-container')?.show({ title: message, type: kind });
  }, window.UniOCRToast);
}
export { ToastContainer };