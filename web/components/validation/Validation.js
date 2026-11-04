/**
 * Validation Components - OCR Universal
 * Form validation using yup schemas
 */

// Validation helper using yup
class FormValidator {
  constructor(schema = null) {
    this.schema = schema;
    this.errors = new Map();
  }

  // Validate a single field value against a yup schema
  async validateField(fieldName, value, schema = null) {
    const schemaToUse = schema || this.schema;
    if (!schemaToUse) return { valid: true, error: null };

    try {
      await schemaToUse.validateAt(fieldName, { [fieldName]: value }, { abortEarly: false });
      this.errors.delete(fieldName);
      return { valid: true, error: null };
    } catch (err) {
      if (err.name === 'ValidationError') {
        const messages = err.inner.map(e => e.message).filter(Boolean);
        this.errors.set(fieldName, messages.join(' | '));
        return { valid: false, error: messages[0] || 'Validation failed' };
      }
      this.errors.set(fieldName, err.message);
      return { valid: false, error: err.message };
    }
  }

  // Validate entire form data
  async validate(data, schema = null) {
    const schemaToUse = schema || this.schema;
    if (!schemaToUse) return { valid: true, errors: {} };

    try {
      await schemaToUse.validate(data, { abortEarly: false });
      this.errors.clear();
      return { valid: true, errors: {} };
    } catch (err) {
      if (err.name === 'ValidationError') {
        this.errors.clear();
        const validationErrors = {};
        err.inner.forEach(e => {
          if (e.path) {
            this.errors.set(e.path, e.message);
            validationErrors[e.path] = e.message;
          }
        });
        return { valid: false, errors: validationErrors };
      }
      return { valid: false, errors: { _form: err.message } };
    }
  }

  // Check if field has errors
  hasError(fieldName) {
    return this.errors.has(fieldName);
  }

  // Get error for field
  getError(fieldName) {
    return this.errors.get(fieldName) || null;
  }

  // Clear all errors
  clearErrors() {
    this.errors.clear();
  }

  // Clear specific field error
  clearFieldError(fieldName) {
    this.errors.delete(fieldName);
  }

  // Get all errors as object
  getErrors() {
    const result = {};
    this.errors.forEach((error, field) => {
      result[field] = error;
    });
    return result;
  }
}

// Schema builders for common use cases
const SchemaBuilder = {
  // Transit dossier schema
  createTransitSchema() {
    const yup = require('yup');
    return yup.object().shape({
      ref: yup.string()
        .required('La référence est requise')
        .min(3, 'La référence doit contenir au moins 3 caractères')
        .matches(/^TR-\d{4}-\d{6}$/, 'Format invalide (ex: TR-2026-000001)'),
      client: yup.string()
        .required('Le client est requis')
        .min(2, 'Le nom du client doit contenir au moins 2 caractères'),
      navire: yup.string()
        .required('Le navire est requis')
        .min(2, 'Le nom du navire doit contenir au moins 2 caractères'),
      conteneur: yup.string()
        .matches(/^[A-Z]{3}[0-9]{7}$/, 'Format invalide pour le conteneur (ex: MSKU1234567)')
        .optional(),
      blNum: yup.string()
        .required('Le numéro de BL est requis')
        .min(3, 'Le numéro de BL doit contenir au moins 3 caractères'),
      portEmbarq: yup.string()
        .required('Le port d\'embarquement est requis'),
      portDecharg: yup.string()
        .required('Le port de déchargement est requis'),
      dateArrivee: yup.date()
        .required('La date d\'arrivée est requise')
        .typeError('Format de date invalide'),
      documents: yup.array()
        .of(yup.string().required())
        .min(1, 'Au moins un document est requis')
        .required('Les documents sont requis'),
    });
  },

  // Profile schema
  createProfileSchema() {
    const yup = require('yup');
    return yup.object().shape({
      nom: yup.string()
        .required('Le nom est requis')
        .min(2, 'Le nom doit contenir au moins 2 caractères'),
      label: yup.string()
        .required('Le libellé est requis'),
      description: yup.string()
        .min(10, 'La description doit contenir au moins 10 caractères'),
      langue: yup.string()
        .required('La langue est requise')
        .oneOf(['fr', 'en', 'ar'], 'Langue invalide'),
      champs: yup.array()
        .of(
          yup.object().shape({
            nom: yup.string().required('Le nom du champ est requis'),
            label: yup.string().required('Le libellé du champ est requis'),
          })
        )
        .min(1, 'Au moins un champ est requis'),
    });
  },

  // Generic required fields
  createGenericSchema(requiredFields) {
    const yup = require('yup');
    const shape = {};
    requiredFields.forEach(field => {
      shape[field] = yup.string().required(`Le champ ${field} est requis`);
    });
    return yup.object().shape(shape);
  },

  // Email field
  emailSchema() {
    const yup = require('yup');
    return yup.object().shape({
      email: yup.string()
        .required('L\'email est requis')
        .email('Format d\'email invalide'),
    });
  },
};

// Validation Component for UI integration
class ValidationField extends HTMLElement {
  static get observedAttributes() {
    return ['name', 'error', 'touched', 'helper'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.validator = null;
    this.fieldName = null;
  }

  connectedCallback() {
    this.parseAttributes();
    this.render();
    this.bindEvents();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'error') {
      this.error = newValue;
      this.render();
    }
    if (name === 'touched') {
      this.touched = newValue === 'true';
      this.render();
    }
  }

  parseAttributes() {
    this.fieldName = this.getAttribute('name');
    this.error = this.getAttribute('error') || null;
    this.touched = this.hasAttribute('touched');
    this.helper = this.getAttribute('helper') || null;
  }

  bindEvents() {
    const input = this.shadowRoot.querySelector('.validation-input');
    if (input) {
      input.addEventListener('blur', () => {
        this.touched = true;
        this.render();
      });
      input.addEventListener('input', () => {
        if (this.touched && this.error) {
          this.error = null;
          this.render();
        }
      });
    }
  }

  setValidator(validator, fieldName) {
    this.validator = validator;
    this.fieldName = fieldName;
  }

  validate(value) {
    if (!this.validator || !this.fieldName) return true;
    return !this.validator.hasError(this.fieldName);
  }

  render() {
    const error = this.error;
    const touched = this.touched;
    const helper = this.helper;
    const showError = touched && error;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; margin-bottom: 1rem; font-family: var(--font-primary, system-ui); }
        .validation-field { display: flex; flex-direction: column; gap: 0.25rem; }
        .validation-input {
          width: 100%;
          padding: 0.625rem 0.875rem;
          font-size: 0.875rem;
          color: var(--neutral-800, #1f2937);
          background: var(--surface-base, #fff);
          border: 1px solid var(--neutral-300, #d1d5db);
          border-radius: 0.375rem;
          transition: all 150ms ease-out;
        }
        .validation-input:focus { outline: none; border-color: var(--brand-secondary, #0891b2); box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1); }
        .validation-input.error { border-color: var(--semantic-error, #ef4444); }
        .validation-input.error:focus { box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1); }
        .validation-input:disabled { background: var(--neutral-100, #f3f4f6); color: var(--neutral-500, #6b7280); cursor: not-allowed; }
        .validation-label { font-size: 0.875rem; font-weight: 500; color: var(--neutral-700, #374151); }
        .validation-label.required::after { content: ' *'; color: var(--semantic-error, #ef4444); }
        .validation-error { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--semantic-error, #ef4444); animation: slideDown 0.2s ease-out; }
        .validation-helper { font-size: 0.75rem; color: var(--neutral-500, #6b7280); }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        [data-theme="dark"] .validation-label { color: var(--neutral-300, #d1d5db); }
        [data-theme="dark"] .validation-input { color: var(--neutral-100, #f3f4f6); background: var(--neutral-800, #1f2937); border-color: var(--neutral-600, #4b5563); }
        [data-theme="dark"] .validation-input:disabled { background: var(--neutral-900, #111827); }
        [data-theme="dark"] .validation-helper { color: var(--neutral-400, #9ca3af); }
        @media (pointer: coarse) { .validation-input { min-height: 44px; } }
      </style>
      <div class="validation-field">
        <slot name="label"></slot>
        <div class="input-wrapper">
          <slot></slot>
        </div>
        ${showError ? `<div class="validation-error">✕ ${error}</div>` : ''}
        ${helper && !showError ? `<div class="validation-helper">${helper}</div>` : ''}
      </div>
    `;
  }
}

// Integration with existing form components
function attachValidator(formElement, validator) {
  const fields = formElement.querySelectorAll('[data-validate]');
  fields.forEach(field => {
    const fieldName = field.dataset.validate;
    const validationEl = field.closest('.validation-field, form-input, form-select');
    if (validationEl) {
      validationEl.setValidator(validator, fieldName);
    }
  });
}

// Debounce helper for real-time validation
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// Auto-validate on input
function autoValidate(element, validator, fieldName, delay = 300) {
  const debouncedValidate = debounce((value) => {
    validator.validateField(fieldName, value).then(result => {
      const fieldEl = element.closest('.validation-field, form-input, form-select');
      if (fieldEl) {
        fieldEl.error = result.error;
        fieldEl.setAttribute('touched', 'true');
      }
    });
  }, delay);

  element.addEventListener('input', (e) => debouncedValidate(e.target.value));
}

// Register components
if (!customElements.get('validation-field')) customElements.define('validation-field', ValidationField);

export { FormValidator, SchemaBuilder, ValidationField, attachValidator, autoValidate, debounce };