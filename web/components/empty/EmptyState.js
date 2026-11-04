/**
 * Empty State Components - UniOCR
 * Reusable empty state components for lists and containers
 */

// Empty State Component
class EmptyState extends HTMLElement {
  static get observedAttributes() {
    return ['icon', 'title', 'description', 'action-text', 'action-href'];
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

  get icon() { return this.getAttribute('icon') || '📄'; }
  get title() { return this.getAttribute('title') || 'Aucun élément'; }
  get description() { return this.getAttribute('description') || 'Aucun élément à afficher'; }
  get actionText() { return this.getAttribute('action-text') || ''; }
  get actionHref() { return this.getAttribute('action-href') || ''; }

  render() {
    const actionHtml = this.actionText && this.actionHref
      ? `<a href="${this.actionHref}" class="empty-state__action">${this.escape(this.actionText)}</a>`
      : '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .empty-state {
          padding: var(--space-2xl, 3rem);
          text-align: center;
          color: var(--neutral-500, #6b7280);
          background: var(--surface-base, #fff);
          border: 1px solid var(--neutral-200, #e5e7eb);
          border-radius: var(--r-lg, 0.75rem);
        }
        [data-theme="dark"] .empty-state {
          background: var(--surface-raised, #1f2937);
          border-color: var(--neutral-700, #374151);
        }
        .empty-state__icon {
          font-size: 3rem;
          line-height: 1;
          margin-bottom: var(--space-md);
          display: block;
        }
        .empty-state__title {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--neutral-900, #111827);
          margin-bottom: var(--space-xs);
        }
        [data-theme="dark"] .empty-state__title {
          color: var(--neutral-100, #f3f4f6);
        }
        .empty-state__description {
          font-size: 0.875rem;
          color: var(--neutral-500, #6b7280);
          margin-bottom: var(--space-lg);
        }
        .empty-state__action {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.5rem 1rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--brand-secondary, #0891b2);
          background: color-mix(in srgb, var(--brand-secondary, #0891b2) 10%, transparent);
          border-radius: var(--r-md, 0.5rem);
          text-decoration: none;
          transition: background 0.2s ease, color 0.2s ease;
        }
        .empty-state__action:hover {
          background: color-mix(in srgb, var(--brand-secondary, #0891b2) 20%, transparent);
          color: var(--brand-primary, #0e7490);
        }
      </style>
      <div class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">${this.escape(this.icon)}</div>
        <div class="empty-state__title">${this.escape(this.title)}</div>
        <div class="empty-state__description">${this.escape(this.description)}</div>
        ${actionHtml}
      </style>
      <div class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">${this.escape(this.icon)}</div>
        <div class="empty-state__title">${this.escape(this.title)}</div>
        <div class="empty-state__description">${this.escape(this.description)}</div>
        ${this.actionText && this.actionHref ? `<a href="${this.escape(this.actionHref)}" class="empty-state__action">${this.escape(this.actionText)}</a>` : ''}
      </div>
    `;
  }

  escape(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"');
  }
}

// Loading State Component
class LoadingState extends HTMLElement {
  static get observedAttributes() { return ['message', 'size']; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() { this.render(); }
  attributeChangedCallback() { this.render(); }

  get message() { return this.getAttribute('message') || 'Chargement…'; }
  get size() { return this.getAttribute('size') || 'md'; }

  render() {
    const sizes = { xs: '16px', sm: '20px', md: '24px', lg: '32px', xl: '48px', xxl: '64px' };
    const size = sizes[this.size] || sizes.md;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: flex; align-items: center; justify-content: center; gap: 0.5rem; flex-direction: column; padding: var(--space-xl); }
        .loading-spinner {
          width: ${size};
          height: ${size};
          border: 3px solid var(--neutral-200, #e5e7eb);
          border-top-color: var(--brand-secondary, #0891b2);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-message { font-size: 0.875rem; color: var(--neutral-500, #6b7280); }
        [data-theme="dark"] .loading-spinner { border-color: var(--neutral-700, #374151); border-top-color: var(--brand-secondary, #0891b2); }
        @media (prefers-reduced-motion: reduce) { .loading-spinner { animation-duration: 0.01ms; } }
      </style>
      <div role="status" aria-live="polite" aria-label="${this.escape(this.message)}">
        <div class="loading-spinner" aria-hidden="true"></div>
        <span class="loading-message">${this.escape(this.message)}</span>
      </div>
    `;
  }

  escape(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"');
  }
}

// Error State Component
class ErrorState extends HTMLElement {
  static get observedAttributes() { return ['title', 'message', 'action-text', 'action-callback']; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() { this.render(); }
  attributeChangedCallback() { this.render(); }

  get title() { return this.getAttribute('title') || 'Erreur'; }
  get message() { return this.getAttribute('message') || 'Une erreur est survenue'; }
  get actionText() { return this.getAttribute('action-text') || ''; }
  get actionCallback() { return this.getAttribute('action-callback') || ''; }

  render() {
    const actionHtml = this.actionText
      ? `<button class="error-state__action" type="button">${this.escape(this.actionText)}</button>`
      : '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .error-state {
          padding: var(--space-xl);
          text-align: center;
          color: var(--semantic-error, #ef4444);
          background: color-mix(in srgb, var(--semantic-error, #ef4444) 10%, transparent);
          border: 1px solid var(--semantic-error, #ef4444);
          border-radius: var(--r-lg, 0.75rem);
        }
        [data-theme="dark"] .error-state {
          background: color-mix(in srgb, var(--semantic-error, #ef4444) 15%, transparent);
          border-color: var(--semantic-error, #ef4444);
        }
        .error-state__icon {
          font-size: 2.5rem;
          margin-bottom: var(--space-md);
          display: block;
        }
        .error-state__title {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--semantic-error, #ef4444);
          margin-bottom: var(--space-xs);
        }
        .error-state__message {
          font-size: 0.875rem;
          color: var(--neutral-600, #4b5563);
          margin-bottom: var(--space-lg);
        }
        .error-state__action {
          padding: 0.5rem 1rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: #fff;
          background: var(--semantic-error, #ef4444);
          border: none;
          border-radius: var(--r-md, 0.5rem);
          cursor: pointer;
        }
        .error-state__action:hover {
          filter: brightness(0.9);
        }
      </style>
      <div class="error-state" role="alert">
        <div class="error-state__icon" aria-hidden="true">⚠️</div>
        <div class="error-state__title">${this.escape(this.title)}</div>
        <div class="error-state__message">${this.escape(this.message)}</div>
        ${actionHtml}
      </div>
    `;

    // L'action est branchée ici : un `onclick` composé depuis un attribut
    // exécutait du texte arbitraire (injection de script).
    const bouton = this.shadowRoot.querySelector('.error-state__action');
    if (bouton) {
      bouton.addEventListener('click', () => {
        const nom = (this.actionCallback || '').trim();
        const fn = nom ? window[nom] : null;
        if (typeof fn === 'function') fn();
        else this.dispatchEvent(new CustomEvent('retry'));
      });
    }
  }

  escape(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"');
  }
}

// Register components
if (!customElements.get('ocr-empty-state')) customElements.define('ocr-empty-state', EmptyState);
if (!customElements.get('ocr-loading-state')) customElements.define('ocr-loading-state', LoadingState);
if (!customElements.get('ocr-error-state')) customElements.define('ocr-error-state', ErrorState);

export { EmptyState, LoadingState, ErrorState };