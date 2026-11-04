/**
 * Loading Components - OCR Universal
 * Spinners, skeletons, and loading states for critical areas
 */

// Spinner Component
class Spinner extends HTMLElement {
  static get observedAttributes() {
    return ['size', 'color', 'type', 'label'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback() {
    this.render();
  }

  get size() {
    const sizes = { xs: '16px', sm: '20px', md: '24px', lg: '32px', xl: '48px', xxl: '64px' };
    return sizes[this.getAttribute('size')] || sizes.md;
  }

  get color() { return this.getAttribute('color') || 'var(--brand-secondary, #0891b2)'; }
  get type() { return this.getAttribute('type') || 'circular'; }
  get label() { return this.getAttribute('label') || 'Chargement'; }

  render() {
    const size = this.size;
    const color = this.color;
    const type = this.type;

    let spinnerHtml = '';
    if (type === 'circular' || type === 'circle') {
      spinnerHtml = `
        <svg width="${size}" height="${size}" viewBox="0 0 50 50">
          <circle cx="25" cy="25" r="20" fill="none" stroke="${color}" stroke-width="4" stroke-opacity="0.25"/>
          <circle cx="25" cy="25" r="20" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-dasharray="125 100" transform="rotate(-90 25 25)">
            <animateTransform attributeName="transform" type="rotate" dur="0.8s" repeatCount="indefinite"/>
          </circle>
        </svg>`;
    } else if (type === 'dots') {
      spinnerHtml = `<div class="dots-spinner"><span></span><span></span><span></span></div>`;
    } else if (type === 'linear') {
      spinnerHtml = `
        <svg width="${size}" height="${size}" viewBox="0 0 50 50">
          ${[0, 90, 180, 270].map(angle => `<line x1="25" y1="5" x2="25" y2="15" stroke="${color}" stroke-width="4" stroke-linecap="round">
            <animateTransform attributeName="transform" type="rotate" from="${angle} 25 25" to="${angle + 360} 25 25" dur="0.8s" repeatCount="indefinite"/>
          </line>`).join('')}
        </svg>`;
    } else if (type === 'bars') {
      spinnerHtml = `<div class="bars-spinner"><div></div><div></div><div></div><div></div><div></div></div>`;
    } else if (type === 'wave') {
      spinnerHtml = `<div class="wave-spinner"><span></span><span></span><span></span><span></span><span></span></div>`;
    }

    const labelHtml = this.hasAttribute('label') ? `<span class="loading-label">${this.label}</span>` : '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; }
        @keyframes dots-bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
        @keyframes bar-scale { 0%, 80%, 100% { transform: scaleY(0.4); } 40% { transform: scaleY(1); } }
        @keyframes wave { 0%, 100% { transform: scaleY(0.5); } 50% { transform: scaleY(1); } }
        .dots-spinner { display: flex; gap: 0.375rem; align-items: center; width: ${size}; height: ${size}; }
        .dots-spinner span { width: 0.75rem; height: 0.75rem; background: ${color}; border-radius: 50%; display: block; animation: dots-bounce 1.2s ease-in-out infinite; }
        .bars-spinner { display: flex; gap: 0.25rem; align-items: flex-end; width: ${size}; height: ${size}; }
        .bars-spinner div { width: 0.5rem; height: 100%; background: ${color}; animation: bar-scale 1s ease-in-out infinite; }
        .bars-spinner div:nth-child(2) { animation-delay: 0.1s; }
        .bars-spinner div:nth-child(3) { animation-delay: 0.2s; }
        .bars-spinner div:nth-child(4) { animation-delay: 0.3s; }
        .bars-spinner div:nth-child(5) { animation-delay: 0.4s; }
        .wave-spinner { display: flex; gap: 0.25rem; align-items: center; width: ${size}; height: ${size}; }
        .wave-spinner span { width: 0.375rem; height: 100%; background: ${color}; border-radius: 0.1875rem; animation: wave 1.2s ease-in-out infinite; }
        .wave-spinner span:nth-child(2) { animation-delay: 0.1s; }
        .wave-spinner span:nth-child(3) { animation-delay: 0.2s; }
        .wave-spinner span:nth-child(4) { animation-delay: 0.3s; }
        .wave-spinner span:nth-child(5) { animation-delay: 0.4s; }
        .loading-label { font-size: 0.875rem; color: var(--neutral-500, #6b7280); white-space: nowrap; }
        @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; } }
      </style>
      ${spinnerHtml}${labelHtml}
    `;
  }
}

// Skeleton Component
class Skeleton extends HTMLElement {
  static get observedAttributes() {
    return ['width', 'height', 'shape', 'animate'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() { this.render(); }
  attributeChangedCallback() { this.render(); }

  get width() { return this.getAttribute('width') || '100%'; }
  get height() { return this.getAttribute('height') || '1rem'; }
  get shape() { return this.getAttribute('shape') || 'rect'; }
  get animate() { return !this.hasAttribute('no-animate'); }

  render() {
    const shapeClass = this.shape === 'circle' ? 'skeleton-circle' : 'skeleton-block';
    const animClass = this.animate ? 'skeleton-animating' : '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; overflow: hidden; }
        .skeleton { display: block; width: ${this.width}; height: ${this.height}; background: linear-gradient(90deg, var(--neutral-200, #e5e7eb) 25%, var(--neutral-300, #d1d5db) 50%, var(--neutral-200, #e5e7eb) 75%); background-size: 200% 100%; }
        .skeleton-block { border-radius: 0.375rem; }
        .skeleton-circle { border-radius: 50%; }
        .skeleton-animating { animation: shimmer 1.5s ease-in-out infinite; }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        [data-theme="dark"] .skeleton { background: linear-gradient(90deg, var(--neutral-700, #374151) 25%, var(--neutral-600, #4b5563) 50%, var(--neutral-700, #374151) 75%); background-size: 200% 100%; }
        @media (prefers-reduced-motion: reduce) { .skeleton-animating { animation: none; opacity: 0.6; } }
      </style>
      <span class="skeleton ${shapeClass} ${animClass}"></span>
    `;
  }
}

// Skeleton Card Component
class SkeletonCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: 'open' }); }
  connectedCallback() { this.render(); }
  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .skeleton-card { background: var(--surface-base, #fff); border: 1px solid var(--neutral-200, #e5e7eb); border-radius: 0.5rem; padding: 1.25rem; }
        [data-theme="dark"] .skeleton-card { background: var(--surface-raised, #1f2937); border-color: var(--neutral-700, #374151); }
      </style>
      <div class="skeleton-card"><slot></slot></div>
    `;
  }
}

// Page Loading Overlay
class PageLoader extends HTMLElement {
  static get observedAttributes() { return ['message']; }
  constructor() { super(); this.attachShadow({ mode: 'open' }); this.message = 'Chargement...'; }
  connectedCallback() { this.render(); this.showLoader(); }
  attributeChangedCallback(name, oldValue, newValue) { if (name === 'message') this.message = newValue; }

  showLoader() { this.querySelector('.loader-overlay')?.classList.remove('hidden'); }
  hideLoader() { this.querySelector('.loader-overlay')?.classList.add('hidden'); }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; position: relative; min-height: 100px; }
        .loader-overlay { position: absolute; inset: 0; background: rgba(var(--surface-base-rgb, 255,255,255), 0.85); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 1rem; z-index: 100; border-radius: inherit; }
        .loader-overlay.hidden { display: none; }
        .loader-message { font-size: 0.875rem; color: var(--neutral-500, #6b7280); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .loader-overlay:not(.hidden) { animation: fadeIn 0.2s ease-out; }
        [data-theme="dark"] .loader-overlay { background: rgba(17, 24, 39, 0.85); }
      </style>
      <div class="loader-overlay" role="status" aria-live="polite">
        <div class="loader-content">
          <spinner size="xl" color="var(--brand-secondary, #0891b2)"></spinner>
          <div class="loader-message">${this.message}</div>
        </div>
      </div>
      <slot></slot>
    `;
  }
}

// Progress Bar Component
class ProgressBar extends HTMLElement {
  static get observedAttributes() { return ['value', 'max', 'label', 'show-text', 'indeterminate']; }
  constructor() { super(); this.attachShadow({ mode: 'open' }); }
  connectedCallback() { this.render(); }
  attributeChangedCallback() { this.render(); }

  get value() { return parseFloat(this.getAttribute('value') || '0'); }
  get max() { return parseFloat(this.getAttribute('max') || '100'); }
  get label() { return this.getAttribute('label') || ''; }
  get showText() { return this.hasAttribute('show-text'); }
  get indeterminate() { return this.hasAttribute('indeterminate'); }

  render() {
    const percentage = this.indeterminate ? 100 : Math.min(100, Math.max(0, (this.value / this.max) * 100));
    const text = this.showText ? `${Math.round(percentage)}%` : '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; width: 100%; }
        .progress-container { width: 100%; background: var(--neutral-200, #e5e7eb); border-radius: 9999px; overflow: hidden; height: 0.5rem; position: relative; }
        .progress-bar { height: 100%; background: var(--brand-secondary, #0891b2); border-radius: 9999px; transition: width 0.3s ease-out; position: relative; overflow: hidden; }
        .progress-bar.indeterminate { width: 40% !important; animation: indeterminate 1.5s infinite ease-in-out; background: linear-gradient(90deg, transparent, var(--brand-secondary, #0891b2), transparent); }
        @keyframes indeterminate { 0% { margin-left: -40%; } 100% { margin-left: 100%; } }
        .progress-label { font-size: 0.75rem; color: var(--neutral-500, #6b7280); margin-top: 0.375rem; text-align: center; }
        [data-theme="dark"] .progress-container { background: var(--neutral-700, #374151); }
        [data-theme="dark"] .progress-label { color: var(--neutral-400, #9ca3af); }
      </style>
      <div class="progress-container" role="progressbar" aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100" aria-label="${this.label || 'Progression'}">
        <div class="progress-bar ${this.indeterminate ? 'indeterminate' : ''}" style="width: ${percentage}%"></div>
      </div>
      ${this.showText ? `<div class="progress-label">${text}</div>` : ''}
    `;
  }
}

// Error Boundary
class LoadingBoundary extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: 'open' }); }
  connectedCallback() { this.render(); }
  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .loading-boundary { min-height: 100px; }
        .error-state { padding: 2rem; text-align: center; color: var(--semantic-error, #ef4444); }
      </style>
      <div class="loading-boundary"><slot></slot></div>
    `;
  }
}

// Register all components
if (!customElements.get('ocr-spinner')) customElements.define('ocr-spinner', Spinner);
if (!customElements.get('ocr-skeleton')) customElements.define('ocr-skeleton', Skeleton);
if (!customElements.get('ocr-skeleton-card')) customElements.define('ocr-skeleton-card', SkeletonCard);
if (!customElements.get('ocr-page-loader')) customElements.define('ocr-page-loader', PageLoader);
if (!customElements.get('ocr-progress-bar')) customElements.define('ocr-progress-bar', ProgressBar);
if (!customElements.get('ocr-loading-boundary')) customElements.define('ocr-loading-boundary', LoadingBoundary);

export { Spinner, Skeleton, SkeletonCard, PageLoader, ProgressBar, LoadingBoundary };