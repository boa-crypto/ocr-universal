/**
 * Maritime Icons - OCR Universal
 * SVG icon set for maritime/logistics theme
 * Icons: Ship, Container, Bill of Lading (BL), BAD (Break Bulk/Air/Document)
 */

const MaritimeIcons = {
  // Ship/Vessel icon
  ship: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-ship">
      <path d="M2 20h20"/>
      <path d="M4 20V8c0-2.2 1.8-4 4-4h8c2.2 0 4 1.8 4 4v12"/>
      <path d="M12 4v4"/>
      <path d="M8 16h8"/>
      <path d="M10 20v-4"/>
      <path d="M14 20v-4"/>
    </svg>
  `,

  // Container icon
  container: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-container">
      <rect x="3" y="5" width="18" height="16" rx="2"/>
      <path d="M7 5v16"/>
      <path d="M17 5v16"/>
      <path d="M3 9h18"/>
      <path d="M3 13h18"/>
      <rect x="7" y="7" width="10" height="4" rx="1" fill="currentColor" opacity="0.2"/>
    </svg>
  `,

  // Bill of Lading (BL) icon
  billOfLading: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-bl">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <line x1="10" y1="9" x2="8" y2="9"/>
      <path d="M10 13h6" stroke-width="2" stroke="currentColor" opacity="0.8"/>
    </svg>
  `,

  // BAD (Break Bulk / Air / Document) icon
  bad: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-bad">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
      <rect x="7" y="15" width="10" height="4" rx="1"/>
      <line x1="12" y1="15" x2="12" y2="19"/>
    </svg>
  `,

  // Anchor icon
  anchor: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-anchor">
      <circle cx="12" cy="5" r="3"/>
      <line x1="12" y1="8" x2="12" y2="21"/>
      <path d="M5 12A7 7 0 0 1 19 12"/>
      <path d="M8 17h8"/>
      <path d="M10 19h4"/>
    </svg>
  `,

  // Port/Harbor icon
  port: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-port">
      <path d="M2 20h20"/>
      <path d="M6 20V10a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10"/>
      <path d="M10 4v4"/>
      <path d="M14 4v4"/>
      <rect x="8" y="2" width="8" height="4" rx="1"/>
      <circle cx="12" cy="14" r="2" fill="currentColor" opacity="0.3"/>
    </svg>
  `,

  // Crane icon
  crane: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-crane">
      <path d="M4 20h16"/>
      <path d="M8 20V4"/>
      <path d="M16 20V4"/>
      <path d="M4 4h16"/>
      <path d="M8 4l-2 4h4l-2 4"/>
      <path d="M16 4l2 4h-4l2 4"/>
      <line x1="8" y1="12" x2="16" y2="12"/>
      <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.3"/>
    </svg>
  `,

  // Compass icon
  compass: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-compass">
      <circle cx="12" cy="12" r="10"/>
      <polygon points="12 2 13.5 7 12 7"/>
      <polygon points="12 22 10.5 17 12 17"/>
      <polygon points="2 12 7 10.5 7 12"/>
      <polygon points="22 12 17 13.5 17 12"/>
      <circle cx="12" cy="12" r="3"/>
      <circle cx="12" cy="12" r="1.5" fill="currentColor" opacity="0.3"/>
    </svg>
  `,

  // Wave icon
  wave: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-wave">
      <path d="M2 13c4.5-4 11-4 15.5 0s5.5 6 10 0"/>
      <path d="M2 17c4.5-3 11-3 15.5 0s5.5 4.5 10 0"/>
      <path d="M2 9c4.5 4 11 4 15.5 0s5.5-6 10 0"/>
    </svg>
  `,

  // Lighthouse icon
  lighthouse: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-lighthouse">
      <path d="M12 2v6"/>
      <path d="M12 18v4"/>
      <path d="M6 20h12"/>
      <path d="M8 14h8"/>
      <path d="M10 8h4"/>
      <path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>
      <circle cx="12" cy="12" r="1" fill="currentColor" opacity="0.5"/>
    </svg>
  `,

  // Cargo/Pallet icon
  cargo: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-cargo">
      <rect x="4" y="6" width="16" height="14" rx="2"/>
      <path d="M8 6v14"/>
      <path d="M16 6v14"/>
      <path d="M4 10h16"/>
      <path d="M4 16h16"/>
      <path d="M8 2v4"/>
      <path d="M16 2v4"/>
      <rect x="6" y="8" width="8" height="4" rx="1" fill="currentColor" opacity="0.2"/>
    </svg>
  `,

  // Customs icon
  customs: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-customs">
      <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
      <path d="M12 6v6l4 2"/>
      <path d="M9 14l3-3 3 3"/>
      <circle cx="12" cy="12" r="3" fill="currentColor" opacity="0.2"/>
    </svg>
  `,

  // Manifest/Document list icon
  manifest: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-manifest">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <line x1="10" y1="9" x2="8" y2="9"/>
      <line x1="14" y1="13" x2="14" y2="17" stroke-width="2" stroke="currentColor" opacity="0.8"/>
    </svg>
  `,

  // Shipping line/Route icon
  route: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-route">
      <circle cx="6" cy="18" r="3" fill="currentColor" opacity="0.3"/>
      <circle cx="18" cy="6" r="3" fill="currentColor" opacity="0.3"/>
      <path d="M9 15c3-3 8-3 11 0" stroke-dasharray="5,5"/>
      <path d="M6 18l12-12" stroke-dasharray="5,5"/>
      <polyline points="6 18 9 15 12 18 15 15 18 18" fill="none"/>
    </svg>
  `,

  // Temperature controlled (Reefer) icon
  reefer: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-reefer">
      <rect x="4" y="5" width="16" height="16" rx="2"/>
      <path d="M8 5v16"/>
      <path d="M16 5v16"/>
      <path d="M4 9h16"/>
      <path d="M4 14h16"/>
      <path d="M12 17v-10"/>
      <path d="M10 9h4"/>
      <path d="M10 15h4"/>
      <circle cx="12" cy="12" r="3" stroke-width="2" stroke="currentColor" opacity="0.5"/>
    </svg>
  `,

  // Dangerous goods icon
  dangerousGoods: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-dangerous">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  `,

  // Truck icon (for inland transport)
  truck: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-truck">
      <path d="M5 18h14"/>
      <path d="M5 14h14"/>
      <path d="M15 18v-6H7v6"/>
      <circle cx="7" cy="18" r="2"/>
      <circle cx="17" cy="18" r="2"/>
      <path d="M3 14h2"/>
      <path d="M20 10V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4"/>
    </svg>
  `,

  // Train icon (for rail transport)
  train: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-train">
      <path d="M2 17h20"/>
      <path d="M6 13v4"/>
      <path d="M10 13v4"/>
      <path d="M14 13v4"/>
      <path d="M18 13v4"/>
      <rect x="4" y="5" width="16" height="10" rx="2"/>
      <circle cx="7" cy="17" r="2"/>
      <circle cx="17" cy="17" r="2"/>
      <path d="M7 9h10" stroke-width="2" stroke="currentColor" opacity="0.5"/>
    </svg>
  `,

  // Air freight icon
  airFreight: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="maritime-icon maritime-air">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
      <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
      <line x1="12" y1="22.08" x2="12" y2="12"/>
    </svg>
  `,
};

// Icon sizes
const ICON_SIZES = {
  xs: '16px',
  sm: '20px',
  md: '24px',
  lg: '32px',
  xl: '40px',
};

// Create icon element
function createIcon(name, size = 'md', className = '') {
  const svg = MaritimeIcons[name];
  if (!svg) {
    console.warn(`Maritime icon "${name}" not found`);
    return MaritimeIcons.container; // fallback
  }

  const sizeValue = ICON_SIZES[size] || ICON_SIZES.md;
  return svg.replace(
    '<svg ',
    `<svg width="${sizeValue}" height="${sizeValue}" `
  ).replace(
    'class="maritime-icon',
    `class="maritime-icon maritime-${name} ${className}"`
  );
}

// Register as custom element for easy use
class MaritimeIcon extends HTMLElement {
  static get observedAttributes() {
    return ['name', 'size', 'color'];
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

  get name() { return this.getAttribute('name') || 'container'; }
  get size() { return this.getAttribute('size') || 'md'; }
  get color() { return this.getAttribute('color') || 'currentColor'; }

  render() {
    const svg = MaritimeIcons[this.name] || MaritimeIcons.container;
    const sizeValue = ICON_SIZES[this.size] || ICON_SIZES.md;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; }
        .maritime-icon { width: ${sizeValue}; height: ${sizeValue}; color: ${this.color}; flex-shrink: 0; }
      </style>
      ${svg}
    `;
  }
}

// Create a sprite sheet for all icons
function createSpriteSheet() {
  const symbols = Object.entries(MaritimeIcons).map(([name, svg]) => {
    const symbol = svg.replace('<svg ', '<symbol ').replace('</svg>', '</symbol>');
    return symbol.replace('viewBox="0 0 24 24"', `id="icon-${name}" viewBox="0 0 24 24"`);
  }).join('\n');

  return `<svg xmlns="http://www.w3.org/2000/svg" style="display:none">${symbols}</svg>`;
}

// Inject sprite sheet on load
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    const spriteSheet = createSpriteSheet();
    document.body.insertAdjacentHTML('afterbegin', spriteSheet);
  });
}

if (!customElements.get('maritime-icon')) customElements.define('maritime-icon', MaritimeIcon);

export { MaritimeIcons, createIcon, createSpriteSheet, MaritimeIcon, ICON_SIZES };