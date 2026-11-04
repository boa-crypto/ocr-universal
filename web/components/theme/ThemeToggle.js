/**
 * Theme Toggle - OCR Universal
 * Dark/Light theme switcher with localStorage persistence
 */

class ThemeToggle extends HTMLElement {
  static get observedAttributes() {
    return ['theme', 'storage-key'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.storageKey = 'ocr-universal-theme';
    this.currentTheme = 'dark';
  }

  connectedCallback() {
    this.storageKey = this.getAttribute('storage-key') || this.storageKey;
    this.loadTheme();
    this.render();
    this.bindEvents();
    this.applyTheme(this.currentTheme);
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'theme' && newValue !== oldValue) {
      this.currentTheme = newValue;
      this.applyTheme(newValue);
      this.updateUI();
    }
  }

  loadTheme() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        this.currentTheme = stored;
      } else {
        // Check system preference
        this.currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
    } catch (e) {
      // Fallback if localStorage unavailable
      this.currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
  }

  saveTheme(theme) {
    try {
      localStorage.setItem(this.storageKey, theme);
    } catch (e) {
      // Silently fail if storage unavailable
    }
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
    this.setAttribute('theme', theme);
    this.saveTheme(theme);

    // Dispatch event for other components
    this.dispatchEvent(new CustomEvent('theme-change', {
      detail: { theme },
      bubbles: true,
      composed: true
    }));
  }

  toggleTheme() {
    const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
    this.applyTheme(newTheme);
    this.updateUI();
  }

  updateUI() {
    const toggle = this.shadowRoot.querySelector('.theme-toggle');
    const icon = this.shadowRoot.querySelector('.theme-icon');
    const label = this.shadowRoot.querySelector('.theme-label');

    if (toggle) {
      toggle.setAttribute('aria-pressed', this.currentTheme === 'dark');
      toggle.title = this.currentTheme === 'dark' ? 'Passer au thème clair' : 'Passer au thème sombre';
    }

    if (icon) {
      icon.innerHTML = this.currentTheme === 'dark'
        ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>'
        : '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>';
    }

    if (label) {
      label.textContent = this.currentTheme === 'dark' ? 'Sombre' : 'Clair';
    }
  }

  bindEvents() {
    const toggle = this.shadowRoot.querySelector('.theme-toggle');
    if (toggle) {
      toggle.addEventListener('click', () => this.toggleTheme());
      toggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.toggleTheme();
        }
      });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(this.storageKey)) {
        this.applyTheme(e.matches ? 'dark' : 'light');
        this.updateUI();
      }
    });

    // Keyboard shortcut: 't' key
    document.addEventListener('keydown', (e) => {
      if (e.key === 't' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        if (!activeElement || activeElement.tagName === 'BODY' || activeElement === this) {
          e.preventDefault();
          this.toggleTheme();
        }
      }
    });
  }

  render() {
    const isDark = this.currentTheme === 'dark';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; font-family: var(--font-primary, system-ui); }
        .theme-toggle {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.5rem 0.75rem;
          background: transparent;
          border: 1px solid var(--neutral-300, #d1d5db);
          border-radius: 0.375rem;
          color: var(--neutral-600, #4b5563);
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 150ms ease-out;
          min-height: 40px;
        }
        .theme-toggle:hover:not(:disabled) {
          background: var(--neutral-100, #f3f4f6);
          border-color: var(--neutral-400, #9ca3af);
          color: var(--neutral-800, #1f2937);
        }
        .theme-toggle:focus-visible {
          outline: 2px solid var(--brand-secondary, #0891b2);
          outline-offset: 2px;
        }
        .theme-toggle:disabled { opacity: 0.6; cursor: not-allowed; }
        .theme-icon {
          width: 1.25rem;
          height: 1.25rem;
          stroke: currentColor;
          stroke-width: 1.8;
          fill: none;
          flex-shrink: 0;
        }
        .theme-label { white-space: nowrap; }
        [data-theme="dark"] .theme-toggle {
          border-color: var(--neutral-600, #4b5563);
          color: var(--neutral-400, #9ca3af);
        }
        [data-theme="dark"] .theme-toggle:hover:not(:disabled) {
          background: var(--neutral-800, #1f2937);
          border-color: var(--neutral-500, #6b7280);
          color: var(--neutral-200, #e5e7eb);
        }
        @media (prefers-reduced-motion: reduce) {
          .theme-toggle { transition: background-color 150ms ease-out, border-color 150ms ease-out, color 150ms ease-out; }
        }
      </style>
      <button class="theme-toggle" type="button" aria-pressed="${isDark}" aria-label="${isDark ? 'Passer au thème clair' : 'Passer au thème sombre'}">
        <svg class="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
          ${isDark
            ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>'
            : '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'}
        </svg>
        <span class="theme-label">${isDark ? 'Sombre' : 'Clair'}</span>
      </button>
    `;
  }
}

// Theme Provider - manages theme for the entire app
class ThemeProvider {
  static init(options = {}) {
    const storageKey = options.storageKey || 'ocr-universal-theme';
    const defaultTheme = options.defaultTheme || 'dark';
    const respectSystem = options.respectSystem !== false;

    let currentTheme = defaultTheme;

    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        currentTheme = stored;
      } else if (respectSystem) {
        currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
    } catch (e) {
      if (respectSystem) {
        currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
    }

    document.documentElement.setAttribute('data-theme', currentTheme);

    // Listen for storage changes in other tabs
    window.addEventListener('storage', (e) => {
      if (e.key === storageKey && e.newValue) {
        currentTheme = e.newValue;
        document.documentElement.setAttribute('data-theme', currentTheme);
        document.dispatchEvent(new CustomEvent('theme-change', { detail: { theme: currentTheme } }));
      }
    });

    // Listen for system theme changes
    if (respectSystem) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        try {
          if (!localStorage.getItem(storageKey)) {
            currentTheme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', currentTheme);
            document.dispatchEvent(new CustomEvent('theme-change', { detail: { theme: currentTheme } }));
          }
        } catch (err) {
          currentTheme = e.matches ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', currentTheme);
          document.dispatchEvent(new CustomEvent('theme-change', { detail: { theme: currentTheme } }));
        }
      });
    }

    return {
      getTheme: () => currentTheme,
      setTheme: (theme) => {
        currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        try {
          localStorage.setItem(storageKey, theme);
        } catch (err) {}
        document.dispatchEvent(new CustomEvent('theme-change', { detail: { theme } }));
      },
      toggle: () => {
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        currentTheme = newTheme;
        document.documentElement.setAttribute('data-theme', newTheme);
        try {
          localStorage.setItem(storageKey, newTheme);
        } catch (err) {}
        document.dispatchEvent(new CustomEvent('theme-change', { detail: { theme: newTheme } }));
        return newTheme;
      }
    };
  }
}

// Initialize theme on load
if (typeof document !== 'undefined') {
  // Early initialization to prevent flash
  try {
    const stored = localStorage.getItem('ocr-universal-theme');
    if (stored) {
      document.documentElement.setAttribute('data-theme', stored);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
}

if (!customElements.get('theme-toggle')) customElements.define('theme-toggle', ThemeToggle);

export { ThemeToggle, ThemeProvider };