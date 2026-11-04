/**
 * Form Components - OCR Universal
 * Reusable form components with validation support
 */

// Base Input Component
class FormInput extends HTMLElement {
  static get observedAttributes() {
    return ['label', 'type', 'placeholder', 'value', 'name', 'required', 'disabled', 'error', 'help', 'icon'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.input = this.shadowRoot.querySelector('input, textarea, select');
    if (this.input) {
      this.input.addEventListener('input', () => this.handleInput());
      this.input.addEventListener('blur', () => this.validate());
      this.input.addEventListener('focus', () => this.clearError());
    }
  }

  attributeChangedCallback() {
    if (this.input) this.render();
  }

  handleInput() {
    this.value = this.input.value;
    this.dispatchEvent(new CustomEvent('form-input-change', {
      detail: { name: this.name, value: this.value },
      bubbles: true,
      composed: true
    }));
  }

  validate() {
    if (this.required && !this.value?.trim()) {
      this.setError(this.getAttribute('data-required-message') || 'Ce champ est requis');
      return false;
    }
    if (this.inputType === 'email' && this.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value)) {
      this.setError('Format d\'email invalide');
      return false;
    }
    if (this.minLength && this.value?.length < this.minLength) {
      this.setError(`Minimum ${this.minLength} caractères requis`);
      return false;
    }
    if (this.pattern && this.value && !new RegExp(this.pattern).test(this.value)) {
      this.setError(this.getAttribute('data-pattern-message') || 'Format invalide');
      return false;
    }
    this.clearError();
    return true;
  }

  setError(message) {
    this.error = message;
    this.render();
    this.dispatchEvent(new CustomEvent('form-input-error', {
      detail: { name: this.name, error: message },
      bubbles: true,
      composed: true
    }));
  }

  clearError() {
    this.error = null;
    const errorEl = this.shadowRoot.querySelector('.form-error');
    if (errorEl) errorEl.remove();
    this.input?.classList.remove('error');
  }

  get name() { return this.getAttribute('name') || ''; }
  get value() { return this.getAttribute('value') || ''; }
  set value(v) { this.setAttribute('value', v || ''); }
  get required() { return this.hasAttribute('required'); }
  get inputType() { return this.getAttribute('data-type') || 'text'; }
  get minLength() { return parseInt(this.getAttribute('minlength') || '0'); }
  get pattern() { return this.getAttribute('pattern') || ''; }
  get error() { return this.getAttribute('error') || null; }
  set error(v) { v ? this.setAttribute('error', v) : this.removeAttribute('error'); }

  render() {
    const label = this.getAttribute('label') || '';
    const placeholder = this.getAttribute('placeholder') || '';
    const help = this.getAttribute('help') || '';
    const icon = this.getAttribute('icon') || '';
    const error = this.error;
    const disabled = this.hasAttribute('disabled');
    const required = this.required;

    const inputHtml = this.renderInput();

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; margin-bottom: 1rem; font-family: var(--font-primary, system-ui); }
        .form-group { display: flex; flex-direction: column; gap: 0.375rem; }
        .form-label { font-size: 0.875rem; font-weight: 500; color: var(--neutral-700, #374151); }
        .form-label .required { color: var(--semantic-error, #ef4444); margin-left: 0.25rem; }
        .input-wrapper { position: relative; display: flex; align-items: center; }
        .input-icon { position: absolute; left: 0.75rem; color: var(--neutral-400, #9ca3af); pointer-events: none; width: 1.25rem; height: 1.25rem; }
        .form-input {
          width: 100%;
          padding: 0.625rem 0.875rem;
          font-size: 0.875rem;
          color: var(--neutral-800, #1f2937);
          background: var(--surface-base, #fff);
          border: 1px solid var(--neutral-300, #d1d5db);
          border-radius: 0.375rem;
          transition: all 150ms ease-out;
        }
        .form-input:focus { outline: none; border-color: var(--brand-secondary, #0891b2); box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1); }
        .form-input:disabled { background: var(--neutral-100, #f3f4f6); color: var(--neutral-500, #6b7280); cursor: not-allowed; }
        .form-input.has-icon { padding-left: 2.5rem; }
        .form-input.error { border-color: var(--semantic-error, #ef4444); }
        .form-input.error:focus { box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1); }
        .form-error { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--semantic-error, #ef4444); }
        .form-error::before { content: '✕'; font-weight: 700; font-size: 0.7rem; }
        .form-help { font-size: 0.75rem; color: var(--neutral-500, #6b7280); }
        [data-theme="dark"] .form-label { color: var(--neutral-300, #d1d5db); }
        [data-theme="dark"] .form-input { color: var(--neutral-100, #f3f4f6); background: var(--neutral-800, #1f2937); border-color: var(--neutral-600, #4b5563); }
        [data-theme="dark"] .form-input:disabled { background: var(--neutral-900, #111827); }
        @media (pointer: coarse) { .form-input { min-height: 44px; } }
      </style>
      <div class="form-group">
        ${label ? `<label class="form-label">${label}${required ? '<span class="required">*</span>' : ''}</label>` : ''}
        <div class="input-wrapper">
          ${icon ? `<svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><use href="#icon-${icon}"/></svg>` : ''}
          ${inputHtml}
        </div>
        ${error ? `<div class="form-error">${error}</div>` : ''}
        ${help && !error ? `<div class="form-help">${help}</div>` : ''}
      </div>
    `;
  }

  renderInput() {
    const placeholder = this.getAttribute('placeholder') || '';
    const value = this.value;
    const disabled = this.hasAttribute('disabled');
    const hasIcon = !!this.getAttribute('icon');
    const error = this.error;

    if (this.inputType === 'textarea') {
      return `<textarea class="form-input ${hasIcon ? 'has-icon' : ''} ${error ? 'error' : ''}" placeholder="${placeholder}" ${disabled ? 'disabled' : ''} rows="${this.getAttribute('rows') || 4}">${value}</textarea>`;
    }
    if (this.inputType === 'select') {
      const options = this.innerHTML || '';
      return `<select class="form-input ${hasIcon ? 'has-icon' : ''} ${error ? 'error' : ''}" ${disabled ? 'disabled' : ''}>${options}</select>`;
    }
    return `<input type="${this.inputType}" class="form-input ${hasIcon ? 'has-icon' : ''} ${error ? 'error' : ''}" placeholder="${placeholder}" value="${value}" ${disabled ? 'disabled' : ''} ${this.required ? 'required' : ''} ${this.minLength ? `minlength="${this.minLength}"` : ''} ${this.pattern ? `pattern="${this.pattern}"` : ''}>`;
  }
}

// Select Component
class FormSelect extends FormInput {
  constructor() {
    super();
    this.setAttribute('data-type', 'select');
  }

  connectedCallback() {
    super.connectedCallback();
    this.shadowRoot.querySelector('select')?.addEventListener('change', (e) => {
      this.value = e.target.value;
      this.handleInput();
    });
  }
}

// Textarea Component
class FormTextarea extends FormInput {
  constructor() {
    super();
    this.setAttribute('data-type', 'textarea');
  }
}

// Checkbox Component
class FormCheckbox extends HTMLElement {
  static get observedAttributes() {
    return ['label', 'name', 'value', 'checked', 'required', 'disabled', 'error'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.checkbox = this.shadowRoot.querySelector('input');
    this.checkbox?.addEventListener('change', () => this.handleChange());
  }

  handleChange() {
    this.checked = this.checkbox.checked;
    this.value = this.checkbox.checked ? (this.getAttribute('value') || 'on') : '';
    this.dispatchEvent(new CustomEvent('form-input-change', {
      detail: { name: this.name, value: this.value, checked: this.checked },
      bubbles: true,
      composed: true
    }));
  }

  get name() { return this.getAttribute('name') || ''; }
  get value() { return this.getAttribute('value') || 'on'; }
  get checked() { return this.hasAttribute('checked'); }
  set checked(v) { v ? this.setAttribute('checked', '') : this.removeAttribute('checked'); }
  get required() { return this.hasAttribute('required'); }

  render() {
    const label = this.getAttribute('label') || '';
    const error = this.getAttribute('error') || '';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; margin-bottom: 0.75rem; font-family: var(--font-primary, system-ui); }
        .checkbox-wrapper { display: inline-flex; align-items: flex-start; gap: 0.625rem; cursor: pointer; }
        .checkbox-input {
          appearance: none;
          width: 1.25rem;
          height: 1.25rem;
          border: 2px solid var(--neutral-400, #9ca3af);
          border-radius: 0.25rem;
          background: var(--surface-base, #fff);
          cursor: pointer;
          transition: all 150ms ease-out;
          flex-shrink: 0;
          margin-top: 0.125rem;
        }
        .checkbox-input:checked {
          background: var(--brand-secondary, #0891b2);
          border-color: var(--brand-secondary, #0891b2);
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='white' d='M10 3L4.5 8.5 2 6'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: center;
        }
        .checkbox-input:focus-visible { outline: 2px solid var(--brand-secondary, #0891b2); outline-offset: 2px; }
        .checkbox-label { font-size: 0.875rem; color: var(--neutral-700, #374151); line-height: 1.5; }
        .checkbox-wrapper:has(.checkbox-input:disabled) .checkbox-label { color: var(--neutral-500, #6b7280); cursor: not-allowed; }
        .checkbox-error { font-size: 0.75rem; color: var(--semantic-error, #ef4444); margin-top: 0.25rem; margin-left: 1.875rem; }
        [data-theme="dark"] .checkbox-label { color: var(--neutral-300, #d1d5db); }
        [data-theme="dark"] .checkbox-input { background: var(--neutral-800, #1f2937); border-color: var(--neutral-600, #4b5563); }
      </style>
      <div class="checkbox-wrapper">
        <input type="checkbox" class="checkbox-input" name="${this.name}" ${this.checked ? 'checked' : ''} ${this.required ? 'required' : ''} ${this.hasAttribute('disabled') ? 'disabled' : ''}>
        <label class="checkbox-label">${label}</label>
      </div>
      ${error ? `<div class="checkbox-error">${error}</div>` : ''}
    `;
  }
}

// Radio Group Component
class FormRadioGroup extends HTMLElement {
  static get observedAttributes() {
    return ['label', 'name', 'required', 'error', 'orientation'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.options = [];
  }

  connectedCallback() {
    this.parseOptions();
    this.render();
    this.shadowRoot.querySelectorAll('input[name]').forEach(input => {
      input.addEventListener('change', () => this.handleChange(input));
    });
  }

  parseOptions() {
    this.options = Array.from(this.querySelectorAll('option')).map(opt => ({
      value: opt.value,
      label: opt.textContent,
      disabled: opt.hasAttribute('disabled')
    }));
  }

  handleChange(input) {
    this.value = input.value;
    this.dispatchEvent(new CustomEvent('form-input-change', {
      detail: { name: this.name, value: this.value },
      bubbles: true,
      composed: true
    }));
  }

  get name() { return this.getAttribute('name') || ''; }
  get value() { return this.getAttribute('value') || ''; }
  set value(v) { this.setAttribute('value', v); this.render(); }
  get required() { return this.hasAttribute('required'); }
  get error() { return this.getAttribute('error') || ''; }

  render() {
    const label = this.getAttribute('label') || '';
    const error = this.error;
    const orientation = this.getAttribute('orientation') || 'vertical';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; margin-bottom: 1rem; font-family: var(--font-primary, system-ui); }
        .radio-group { display: flex; flex-direction: ${orientation === 'horizontal' ? 'row' : 'column'}; gap: ${orientation === 'horizontal' ? '1.5rem' : '0.625rem'}; }
        .radio-wrapper { display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; }
        .radio-input {
          appearance: none;
          width: 1.25rem;
          height: 1.25rem;
          border: 2px solid var(--neutral-400, #9ca3af);
          border-radius: 50%;
          background: var(--surface-base, #fff);
          cursor: pointer;
          transition: all 150ms ease-out;
          flex-shrink: 0;
        }
        .radio-input:checked {
          border-color: var(--brand-secondary, #0891b2);
          background: radial-gradient(circle, var(--brand-secondary, #0891b2) 40%, transparent 40%);
        }
        .radio-input:focus-visible { outline: 2px solid var(--brand-secondary, #0891b2); outline-offset: 2px; }
        .radio-input:disabled { cursor: not-allowed; opacity: 0.5; }
        .radio-label { font-size: 0.875rem; color: var(--neutral-700, #374151); }
        .radio-error { font-size: 0.75rem; color: var(--semantic-error, #ef4444); margin-top: 0.5rem; }
        [data-theme="dark"] .radio-label { color: var(--neutral-300, #d1d5db); }
        [data-theme="dark"] .radio-input { background: var(--neutral-800, #1f2937); border-color: var(--neutral-600, #4b5563); }
      </style>
      <fieldset class="form-group">
        ${label ? `<legend class="form-label">${label}${this.required ? '<span class="required">*</span>' : ''}</legend>` : ''}
        <div class="radio-group">
          ${this.options.map(opt => `
            <label class="radio-wrapper">
              <input type="radio" class="radio-input" name="${this.name}" value="${opt.value}" ${this.value === opt.value ? 'checked' : ''} ${opt.disabled ? 'disabled' : ''} ${this.required ? 'required' : ''}>
              <span class="radio-label">${opt.label}</span>
            </label>
          `).join('')}
        </div>
        ${error ? `<div class="radio-error">${error}</div>` : ''}
      </fieldset>
    `;
  }
}

// Form Container Component
class FormContainer extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.fields = new Map();
    this.errors = new Map();
  }

  connectedCallback() {
    this.render();
    this.form = this.shadowRoot.querySelector('form');
    this.form?.addEventListener('submit', (e) => this.handleSubmit(e));
    this.scanFields();
  }

  scanFields() {
    const fieldElements = this.querySelectorAll('form-input, form-select, form-textarea, form-checkbox, form-radio-group');
    fieldElements.forEach(el => {
      this.fields.set(el.name, el);
      el.addEventListener('form-input-change', (e) => {
        this.fields.set(e.detail.name, el);
      });
    });
  }

  handleSubmit(e) {
    e.preventDefault();
    const isValid = this.validateAll();
    if (isValid) {
      const formData = this.getFormData();
      this.dispatchEvent(new CustomEvent('form-submit', {
        detail: { data: formData },
        bubbles: true,
        composed: true
      }));
    }
  }

  validateAll() {
    let isValid = true;
    this.fields.forEach((field, name) => {
      if (field.validate && !field.validate()) {
        isValid = false;
      }
    });
    return isValid;
  }

  getFormData() {
    const data = {};
    this.fields.forEach((field, name) => {
      if (field.type === 'checkbox') {
        data[name] = field.checked;
      } else {
        data[name] = field.value;
      }
    });
    return data;
  }

  setFieldError(name, message) {
    const field = this.fields.get(name);
    if (field && field.setError) {
      field.setError(message);
    }
    this.errors.set(name, message);
  }

  clearErrors() {
    this.fields.forEach(field => {
      if (field.clearError) field.clearError();
    });
    this.errors.clear();
  }

  reset() {
    this.fields.forEach(field => {
      if (field.type === 'checkbox') {
        field.checked = false;
      } else {
        field.value = '';
      }
      if (field.clearError) field.clearError();
    });
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--font-primary, system-ui); }
        form { display: flex; flex-direction: column; gap: 1rem; }
        .form-actions { display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
      </style>
      <form novalidate>
        <slot></slot>
        <div class="form-actions">
          <slot name="actions"></slot>
        </div>
      </form>
    `;
  }
}

// Register components
if (!customElements.get('form-input')) customElements.define('form-input', FormInput);
if (!customElements.get('form-select')) customElements.define('form-select', FormSelect);
if (!customElements.get('form-textarea')) customElements.define('form-textarea', FormTextarea);
if (!customElements.get('form-checkbox')) customElements.define('form-checkbox', FormCheckbox);
if (!customElements.get('form-radio-group')) customElements.define('form-radio-group', FormRadioGroup);
if (!customElements.get('form-container')) customElements.define('form-container', FormContainer);

export { FormInput, FormSelect, FormTextarea, FormCheckbox, FormRadioGroup, FormContainer };