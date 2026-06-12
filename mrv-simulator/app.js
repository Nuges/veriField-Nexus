/**
 * VeriField Nexus — Test Environment
 * Core Application Logic & Verification Engine Simulator
 */

// =============================================================================
// 1. Initial State & Seed Data Setup
// =============================================================================

const STORAGE_KEY = 'verifield_nexus_installations';

// Helper to get formatted timestamps relative to current time
const getRelativeDateISO = (daysAgo, hoursOffset = 12) => {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  date.setHours(date.getHours() - hoursOffset);
  return date.toISOString();
};

const DEFAULT_INSTALLATIONS = [
  {
    id: 'mrv-uuid-cookstove-001',
    type: 'cookstove',
    lat: -1.2921,
    lon: 36.8219,
    timestamp: getRelativeDateISO(2, 4), // 2 days ago
    imageHash: 'img_cookstove_001',
    imageName: 'cookstove_nairobi_01.jpg',
    notes: 'High-efficiency biomass cookstove deployed in rural community center near Nairobi, Kenya.',
    trustScore: 95,
    status: 'Verified',
    payloadHash: 'sha256_b7f8e32901a5d6c8f9b204c3e8a1d7f0e2b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8',
    onChain: {
      signature: '5xKzN5b89FjQYpWRsE9JtC5n2s9xK1wEd4vH7c3b2a1n8d9j0k2l3m4n5p6q7r8s9t',
      blockHeight: 204812503,
      slot: 204812509,
      timestamp: getRelativeDateISO(2, 3.8) // anchored slightly after
    }
  },
  {
    id: 'mrv-uuid-solar-002',
    type: 'solar',
    lat: 9.0765,
    lon: 7.3986,
    timestamp: getRelativeDateISO(1, 2), // 1 day ago
    imageHash: 'img_solar_001',
    imageName: 'solar_clinic_abuja.jpg',
    notes: '10kW Solar PV array with battery storage at local healthcare facility in Abuja, Nigeria.',
    trustScore: 90,
    status: 'Pending',
    payloadHash: 'sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    onChain: null
  },
  {
    id: 'mrv-uuid-hybrid-003',
    type: 'hybrid',
    lat: 28.6139,
    lon: 77.2090,
    timestamp: getRelativeDateISO(0, 8), // Today, 8 hours ago
    imageHash: 'img_hybrid_001',
    imageName: 'hybrid_grid_delhi.jpg',
    notes: 'Solar-diesel hybrid system power unit. Setup complete, battery backup online.',
    trustScore: 70,
    status: 'Pending',
    payloadHash: 'sha256_09f2d1e8c9b3a4f6d7e8b9a0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0',
    onChain: null
  },
  {
    id: 'mrv-uuid-cookstove-duplicate-test',
    type: 'cookstove',
    lat: -1.2915, // Very close to Nairobi installation
    lon: 36.8210,
    timestamp: getRelativeDateISO(0, 1), // Today, 1 hour ago
    imageHash: 'img_cookstove_001', // Duplicate Hash of Cookstove 001!
    imageName: 'cookstove1_copy.jpg',
    notes: 'Secondary biomass stove unit capture in Nairobi district.',
    trustScore: 40, // Should fail image uniqueness check
    status: 'Flagged',
    payloadHash: 'sha256_f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9',
    onChain: null
  }
];

// Initialize local database
function getInstallations() {
  const data = localStorage.getItem(STORAGE_KEY);
  if (!data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_INSTALLATIONS));
    return [...DEFAULT_INSTALLATIONS];
  }
  try {
    return JSON.parse(data);
  } catch (e) {
    console.error('Failed to parse localStorage installations, resetting to seed data', e);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_INSTALLATIONS));
    return [...DEFAULT_INSTALLATIONS];
  }
}

function saveInstallations(installations) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(installations));
}

// Global Application State
let installations = getInstallations();
let selectedInstId = null;
let activeRole = 'agent'; // Default role
let activeTab = 'dashboard'; // Default tab
let map = null;
let markers = [];
let submissionsChart = null;

// Mock file upload current state
let selectedImageHash = '';
let selectedImageName = '';

// =============================================================================
// 2. DOM Elements & References
// =============================================================================

const elements = {
  // Navigation & Header
  navItems: document.querySelectorAll('.nav-item'),
  panes: document.querySelectorAll('.pane'),
  viewTitle: document.getElementById('view-title'),
  viewDescription: document.getElementById('view-description'),
  roleBtns: document.querySelectorAll('.role-btn'),
  themeToggle: document.getElementById('theme-toggle'),
  btnNavCapture: document.getElementById('btn-nav-capture'),

  // KPIs
  kpiTotal: document.getElementById('kpi-total'),
  kpiVerified: document.getElementById('kpi-verified'),
  kpiVerifiedPercentage: document.getElementById('kpi-verified-percentage'),
  kpiFlagged: document.getElementById('kpi-flagged'),
  kpiFlaggedText: document.getElementById('kpi-flagged-text'),
  kpiAvgTrust: document.getElementById('kpi-avg-trust'),
  kpiAvgTrustFill: document.getElementById('kpi-avg-trust-fill'),

  // Filters & Logs
  tableSearch: document.getElementById('table-search'),
  filterType: document.getElementById('filter-type'),
  filterStatus: document.getElementById('filter-status'),
  btnExportCsv: document.getElementById('btn-export-csv'),
  mrvTableBody: document.getElementById('mrv-table-body'),

  // Field Capture Form
  fieldCaptureForm: document.getElementById('field-capture-form'),
  captureUuid: document.getElementById('capture-uuid'),
  captureTime: document.getElementById('capture-time'),
  captureLat: document.getElementById('capture-lat'),
  captureLon: document.getElementById('capture-lon'),
  btnGpsDetect: document.getElementById('btn-gps-detect'),
  uploadDropzone: document.getElementById('upload-dropzone'),
  captureFile: document.getElementById('capture-file'),
  selectedFileBanner: document.getElementById('selected-file-banner'),
  selectedFileName: document.getElementById('selected-file-name'),
  selectedFileHash: document.getElementById('selected-file-hash'),
  btnRemoveFile: document.getElementById('btn-remove-file'),
  mockImgItems: document.querySelectorAll('.mock-img-item'),
  captureNotes: document.getElementById('capture-notes'),
  btnSubmitCapture: document.getElementById('btn-submit-capture'),

  // Verification Rules Testbed
  verificationInspectorEmpty: document.getElementById('verification-inspector-empty'),
  verificationInspectorContent: document.getElementById('verification-inspector-content'),
  inspectInstId: document.getElementById('inspect-inst-id'),
  inspectInstType: document.getElementById('inspect-inst-type'),
  inspectGaugeFill: document.getElementById('inspect-gauge-fill'),
  inspectTrustScore: document.getElementById('inspect-trust-score'),
  checkUnique: document.getElementById('check-unique'),
  checkUniqueDesc: document.getElementById('check-unique-desc'),
  checkGps: document.getElementById('check-gps'),
  checkGpsDesc: document.getElementById('check-gps-desc'),
  checkCompleteness: document.getElementById('check-completeness'),
  checkCompletenessDesc: document.getElementById('check-completeness-desc'),
  inspectStatusBanner: document.getElementById('inspect-status-banner'),
  inspectStatusBadge: document.getElementById('inspect-status-badge'),
  btnInspectorReplay: document.getElementById('btn-inspector-replay'),
  btnInspectorAnchor: document.getElementById('btn-inspector-anchor'),

  // On-Chain Ledger
  ledgerTableBody: document.getElementById('ledger-table-body'),

  // Slide drawer
  sideDrawer: document.getElementById('side-drawer'),
  drawerOverlay: document.getElementById('drawer-overlay'),
  btnCloseDrawer: document.getElementById('btn-close-drawer'),
  drawerTitle: document.getElementById('drawer-title'),
  drawerBadgeType: document.getElementById('drawer-badge-type'),
  drawerStatus: document.getElementById('drawer-status'),
  drawerTrustScore: document.getElementById('drawer-trust-score'),
  drawerCo2: document.getElementById('drawer-co2'),
  drawerUuid: document.getElementById('drawer-uuid'),
  drawerHash: document.getElementById('drawer-hash'),
  drawerGps: document.getElementById('drawer-gps'),
  drawerTime: document.getElementById('drawer-time'),
  drawerNotes: document.getElementById('drawer-notes'),
  drawerAuditTimeline: document.getElementById('drawer-audit-timeline'),
  drawerTxSig: document.getElementById('drawer-tx-sig'),
  drawerBlockHeight: document.getElementById('drawer-block-height'),
  drawerTxTime: document.getElementById('drawer-tx-time'),
  drawerBlockchainSection: document.getElementById('drawer-blockchain-section'),
  drawerBtnReplay: document.getElementById('drawer-btn-replay'),
  drawerBtnAction: document.getElementById('drawer-btn-action')
};

// =============================================================================
// 3. UI Helpers: Toasts, Roles, Themes, Navigation
// =============================================================================

// Toast Notifications System
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-message">${message}</span>
    <button class="toast-close">✕</button>
  `;
  container.appendChild(toast);

  // Close event
  toast.querySelector('.toast-close').addEventListener('click', () => {
    toast.remove();
  });

  // Auto remove
  setTimeout(() => {
    toast.classList.add('toast-fadeout');
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.position = 'fixed';
  container.style.bottom = '24px';
  container.style.right = '24px';
  container.style.display = 'flex';
  container.style.flexDirection = 'column';
  container.style.gap = '8px';
  container.style.zIndex = '9999';
  document.body.appendChild(container);

  // Add baseline styles to document head
  const style = document.createElement('style');
  style.textContent = `
    .toast {
      background: var(--color-card);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 12px 18px;
      color: var(--color-text-primary);
      box-shadow: var(--shadow-lg);
      font-size: 12.5px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-width: 280px;
      max-width: 400px;
      animation: toastIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border-left: 4px solid var(--color-primary);
      transition: all 0.3s ease;
    }
    .toast-success { border-left-color: var(--color-success); }
    .toast-error { border-left-color: var(--color-error); }
    .toast-warning { border-left-color: var(--color-warning); }
    .toast-close {
      background: none;
      border: none;
      color: var(--color-text-muted);
      cursor: pointer;
      font-size: 11px;
    }
    .toast-close:hover { color: var(--color-text-primary); }
    .toast-fadeout { opacity: 0; transform: translateY(8px); }
    @keyframes toastIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
  return container;
}

// Theme Toggle
function initTheme() {
  const savedTheme = localStorage.getItem('nexus_theme') || 'dark';
  document.body.className = savedTheme === 'dark' ? 'dark-theme' : 'light-theme';

  elements.themeToggle.addEventListener('click', () => {
    const isDark = document.body.classList.contains('dark-theme');
    if (isDark) {
      document.body.classList.remove('dark-theme');
      document.body.classList.add('light-theme');
      localStorage.setItem('nexus_theme', 'light');
      showToast('Switched to Light Theme', 'info');
    } else {
      document.body.classList.remove('light-theme');
      document.body.classList.add('dark-theme');
      localStorage.setItem('nexus_theme', 'dark');
      showToast('Switched to Dark Theme', 'info');
    }
    // Redraw chart to update axis colors
    if (submissionsChart) {
      initChart();
    }
  });
}

// Role Switching
function initRoles() {
  elements.roleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.roleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeRole = btn.getAttribute('data-role');
      applyRolePrivileges();
      showToast(`Active Role: ${btn.textContent}`, 'info');
    });
  });
}

function applyRolePrivileges() {
  // Hide or disable fields according to role
  if (activeRole === 'viewer') {
    // Hide Field Capture navigation
    elements.btnNavCapture.style.display = 'none';
    // If on capture form, force switch back to dashboard
    if (activeTab === 'capture') {
      switchTab('dashboard');
    }
    // Disable Admin Verification / On Chain Actions
    elements.btnInspectorAnchor.style.display = 'none';
    elements.drawerBtnAction.style.display = 'none';
  } else if (activeRole === 'agent') {
    elements.btnNavCapture.style.display = 'flex';
    // Agent can capture but cannot verify/anchor
    elements.btnInspectorAnchor.style.display = 'none';
    elements.drawerBtnAction.style.display = 'none';
  } else {
    // Verifier Admin
    elements.btnNavCapture.style.display = 'flex';
    // Admin has full access to verify and anchor
    elements.btnInspectorAnchor.style.display = 'inline-flex';
    elements.drawerBtnAction.style.display = 'inline-flex';
  }

  // Refresh current table to toggle availability of actions
  renderDashboardTable();
  if (selectedInstId) {
    updateDrawerUI(selectedInstId);
  }
}

// Navigation Tabs switching
function initNavigation() {
  elements.navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabName = item.getAttribute('data-tab');
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  activeTab = tabName;

  // Update nav buttons active state
  elements.navItems.forEach(item => {
    if (item.getAttribute('data-tab') === tabName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Update display panes
  elements.panes.forEach(pane => {
    if (pane.id === `pane-${tabName}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // Invalidate Leaflet Map Size when returning to dashboard
  if (tabName === 'dashboard') {
    if (map) {
      setTimeout(() => {
        map.invalidateSize();
      }, 100);
    }
    renderDashboardTable();
    updateKPIs();
  }

  // Handle Form preparation
  if (tabName === 'capture') {
    prepareCaptureForm();
  }

  // Handle Ledger loading
  if (tabName === 'ledger') {
    renderLedgerTable();
  }

  // Update Header Title/Description based on tab
  updateHeaderInfo(tabName);
}

function updateHeaderInfo(tabName) {
  const titles = {
    dashboard: {
      title: 'MRV Control Center',
      desc: 'Monitor and verify clean climate asset installations in real-time.'
    },
    capture: {
      title: 'Field Installation Capture',
      desc: 'Register telemetry and capture photographic evidence for clean energy assets.'
    },
    verification: {
      title: 'MRV Verification Engine',
      desc: 'Configure compliance criteria, review trust score weights, and replay verification rules.'
    },
    ledger: {
      title: 'Solana On-Chain Ledger',
      desc: 'Inspect verified asset anchoring logs and transaction proofs.'
    }
  };

  const info = titles[tabName] || titles.dashboard;
  elements.viewTitle.textContent = info.title;
  elements.viewDescription.textContent = info.desc;
}

// =============================================================================
// 4. Map & Chart Analytics Integration
// =============================================================================

function initMap() {
  if (map) return;

  // Initialize Leaflet Map centered globally
  map = L.map('map', {
    zoomControl: true,
    minZoom: 1.5,
    maxBoundsViscosity: 1.0
  }).setView([15.0, 30.0], 2);

  // Set OpenStreetMap standard tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // Add markers
  renderMapMarkers();
}

function renderMapMarkers() {
  // Clear old markers
  markers.forEach(m => map.removeLayer(m));
  markers = [];

  installations.forEach(inst => {
    if (inst.lat && inst.lon) {
      let statusColor = 'var(--color-warning)'; // Pending / Yellow
      if (inst.status.toLowerCase() === 'verified') {
        statusColor = 'var(--color-success)'; // Green
      } else if (inst.status.toLowerCase() === 'flagged') {
        statusColor = 'var(--color-error)'; // Red
      }

      const marker = L.circleMarker([inst.lat, inst.lon], {
        radius: 8,
        fillColor: statusColor,
        color: '#ffffff',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.85
      }).addTo(map);

      // Create Popup template
      const popupContent = `
        <div style="font-family: Inter, sans-serif; font-size: 12px; line-height: 1.4;">
          <h4 style="margin: 0 0 4px; font-weight: 700; color: #111;">${inst.type.toUpperCase()} Module</h4>
          <span style="font-size: 10px; color:#777; font-family: monospace;">UUID: ${inst.id.substring(0, 14)}...</span>
          <div style="margin: 8px 0 4px;">
            <strong>Trust Score:</strong> ${inst.trustScore}%
          </div>
          <div>
            <strong>Status:</strong> <span style="font-weight: 600; color:${statusColor}">${inst.status}</span>
          </div>
          <button class="btn btn-secondary btn-sm" style="width:100%; padding: 4px; margin-top: 8px;" onclick="openDrawer('${inst.id}')">Inspect Asset</button>
        </div>
      `;
      marker.bindPopup(popupContent);
      markers.push(marker);
    }
  });
}

function initChart() {
  const ctx = document.getElementById('submissions-chart');
  if (!ctx) return;

  // Destroy old chart to allow updates
  if (submissionsChart) {
    submissionsChart.destroy();
  }

  // Get date strings for last 7 days
  const dates = [];
  const dateLabels = [];
  const submissionsByDate = {};

  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    dates.push(dateStr);

    const parts = dateStr.split('-');
    dateLabels.push(`${parts[1]}/${parts[2]}`); // MM/DD

    submissionsByDate[dateStr] = { verified: 0, flagged: 0, pending: 0 };
  }

  // Populate data
  installations.forEach(inst => {
    const instDate = inst.timestamp.split('T')[0];
    if (submissionsByDate[instDate]) {
      const status = inst.status.toLowerCase();
      if (status === 'verified') {
        submissionsByDate[instDate].verified++;
      } else if (status === 'flagged') {
        submissionsByDate[instDate].flagged++;
      } else {
        submissionsByDate[instDate].pending++;
      }
    }
  });

  const verifiedData = dates.map(d => submissionsByDate[d].verified);
  const flaggedData = dates.map(d => submissionsByDate[d].flagged);
  const pendingData = dates.map(d => submissionsByDate[d].pending);

  // Setup theme-adaptive colors
  const isDark = document.body.classList.contains('dark-theme');
  const textColor = isDark ? '#a7b6c2' : '#4a5568';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)';

  submissionsChart = new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: dateLabels,
      datasets: [
        {
          label: 'Verified',
          data: verifiedData,
          backgroundColor: '#10b981', // Emerald
          borderRadius: 4
        },
        {
          label: 'Flagged',
          data: flaggedData,
          backgroundColor: '#ef4444', // Red
          borderRadius: 4
        },
        {
          label: 'Pending',
          data: pendingData,
          backgroundColor: '#f59e0b', // Orange
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { color: textColor, font: { family: 'Inter', size: 10 } }
        },
        y: {
          stacked: true,
          grid: { color: gridColor },
          ticks: { color: textColor, font: { family: 'Inter', size: 10 }, stepSize: 1 }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: textColor, font: { family: 'Inter', size: 11, weight: '500' } }
        }
      }
    }
  });
}

// =============================================================================
// 5. Dashboard Table & KPIs Rendering
// =============================================================================

function updateKPIs() {
  const total = installations.length;
  const verified = installations.filter(i => i.status.toLowerCase() === 'verified').length;
  const flagged = installations.filter(i => i.status.toLowerCase() === 'flagged').length;

  // Compute average trust score
  const avgTrust = total > 0 
    ? Math.round(installations.reduce((acc, curr) => acc + curr.trustScore, 0) / total) 
    : 0;

  // Render values
  elements.kpiTotal.textContent = total;
  elements.kpiVerified.textContent = verified;
  elements.kpiFlagged.textContent = flagged;
  elements.kpiAvgTrust.textContent = `${avgTrust}%`;
  elements.kpiAvgTrustFill.style.width = `${avgTrust}%`;

  // Verification success rate
  const successRate = total > 0 ? Math.round((verified / total) * 100) : 0;
  elements.kpiVerifiedPercentage.textContent = `${successRate}% approval rate`;
  elements.kpiFlaggedText.textContent = `${flagged} Low trust / duplicates`;
}

function renderDashboardTable() {
  const searchTerm = elements.tableSearch.value.toLowerCase().trim();
  const selectedType = elements.filterType.value;
  const selectedStatus = elements.filterStatus.value;

  // Filter installations list
  const filtered = installations.filter(inst => {
    // Search filter
    const matchesSearch = 
      inst.id.toLowerCase().includes(searchTerm) ||
      inst.notes.toLowerCase().includes(searchTerm) ||
      inst.type.toLowerCase().includes(searchTerm) ||
      (inst.imageName && inst.imageName.toLowerCase().includes(searchTerm));

    // Module type filter
    const matchesType = selectedType === 'all' || inst.type === selectedType;

    // Status filter
    const matchesStatus = selectedStatus === 'all' || inst.status.toLowerCase() === selectedStatus;

    return matchesSearch && matchesType && matchesStatus;
  });

  // Sort: Newest submissions first
  filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  // Render table rows
  elements.mrvTableBody.innerHTML = '';

  if (filtered.length === 0) {
    elements.mrvTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center" style="padding: 40px; text-align: center; color: var(--color-text-muted);">
          No MRV registry records found matching filters.
        </td>
      </tr>
    `;
    return;
  }

  filtered.forEach(inst => {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';

    // Format coordinates
    const coordsStr = `Lat: ${inst.lat.toFixed(4)}, Lon: ${inst.lon.toFixed(4)}`;

    // Format capture date/time
    const date = new Date(inst.timestamp);
    const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

    // Trust badge
    let trustClass = 'trust-high';
    if (inst.trustScore < 50) trustClass = 'trust-low';
    else if (inst.trustScore < 75) trustClass = 'trust-mid';

    // Type badge
    let typeLabel = 'Cookstove';
    if (inst.type === 'solar') typeLabel = 'Solar Power';
    else if (inst.type === 'hybrid') typeLabel = 'Hybrid Energy';

    // Status badge
    let statusClass = 'status-pending';
    if (inst.status.toLowerCase() === 'verified') statusClass = 'status-verified';
    else if (inst.status.toLowerCase() === 'flagged') statusClass = 'status-flagged';

    tr.innerHTML = `
      <td><span class="value code" style="font-family: monospace; font-weight: 600;">${inst.id.substring(0, 14)}...</span></td>
      <td><span class="badge type-${inst.type}">${typeLabel}</span></td>
      <td><span class="text-muted" style="font-size: 11.5px;">${coordsStr}</span></td>
      <td><span>${dateStr}</span></td>
      <td><span class="badge-trust ${trustClass}">${inst.trustScore}%</span></td>
      <td><span class="badge ${statusClass}">${inst.status}</span></td>
      <td class="text-right">
        <button class="btn btn-secondary btn-sm btn-inspect-row" data-id="${inst.id}">Inspect</button>
      </td>
    `;

    // Row clicks opens the side details drawer
    tr.addEventListener('click', (e) => {
      // Don't trigger if clicked on the inspect button specifically, as we handle it
      if (e.target.classList.contains('btn-inspect-row')) return;
      openDrawer(inst.id);
    });

    // Inspect button handler
    tr.querySelector('.btn-inspect-row').addEventListener('click', (e) => {
      e.stopPropagation();
      openDrawer(inst.id);
    });

    elements.mrvTableBody.appendChild(tr);
  });
}

// =============================================================================
// 6. Field Data Capture Module Logic
// =============================================================================

function generateUUID() {
  return 'mrv-uuid-' + Math.random().toString(36).substring(2, 11) + '-' + Math.random().toString(36).substring(2, 11);
}

function calculatePayloadHash(record) {
  // Simulates a SHA-256 calculation
  const inputStr = `${record.id}-${record.type}-${record.lat}-${record.lon}-${record.timestamp}-${record.imageHash}-${record.notes}`;
  let hash = 0;
  for (let i = 0; i < inputStr.length; i++) {
    const char = inputStr.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  const randPart = Math.random().toString(16).substring(2, 10);
  return 'sha256_' + hex + randPart + 'e1a2f3c4b5d6f8901a5d6c8f9b204c3e8a1d7f';
}

function prepareCaptureForm() {
  elements.captureUuid.value = generateUUID();
  elements.captureTime.value = new Date().toLocaleString();

  // Clear GPS inputs (unless already filled)
  if (!elements.captureLat.value && !elements.captureLon.value) {
    elements.captureLat.value = '';
    elements.captureLon.value = '';
  }

  // Clear note
  elements.captureNotes.value = '';

  // Clear mock file selections
  resetFileSelection();
}

function resetFileSelection() {
  selectedImageHash = '';
  selectedImageName = '';
  elements.captureFile.value = '';
  elements.selectedFileBanner.classList.add('hidden');
  elements.mockImgItems.forEach(item => item.style.borderColor = 'var(--color-border)');
}

// Bind File Selection & Dropzone Interactions
function initFormInteractions() {
  // Dropzone click triggers input click
  elements.uploadDropzone.addEventListener('click', (e) => {
    // Avoid triggering if clicked on the quick mock options container
    if (e.target.closest('.mock-images-container')) return;
    elements.captureFile.click();
  });

  // Handle file select
  elements.captureFile.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      handleUploadedFile(file.name);
    }
  });

  // Drag & drop handlers
  elements.uploadDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.uploadDropzone.style.borderColor = 'var(--color-primary)';
  });

  elements.uploadDropzone.addEventListener('dragleave', () => {
    elements.uploadDropzone.style.borderColor = 'var(--color-border)';
  });

  elements.uploadDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.uploadDropzone.style.borderColor = 'var(--color-border)';
    const file = e.dataTransfer.files[0];
    if (file) {
      handleUploadedFile(file.name);
    }
  });

  // Remove File Button
  elements.btnRemoveFile.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileSelection();
  });

  // Quick Test Mock image select
  elements.mockImgItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();

      // Clear other mock image borders
      elements.mockImgItems.forEach(b => {
        b.style.borderColor = 'var(--color-border)';
        b.style.backgroundColor = 'var(--color-surface)';
      });

      // Style active mock image item
      item.style.borderColor = 'var(--color-primary)';
      item.style.backgroundColor = 'var(--color-primary-glow)';

      selectedImageHash = item.getAttribute('data-hash');
      selectedImageName = item.textContent.replace(/[^\x20-\x7E]/g, '').trim(); // Clean emoji chars if any
      if (!selectedImageName) {
        selectedImageName = item.querySelector('span:last-child').textContent;
      }

      elements.selectedFileName.textContent = selectedImageName;
      elements.selectedFileHash.textContent = `SHA-256: ${selectedImageHash}`;
      elements.selectedFileBanner.classList.remove('hidden');
    });
  });

  // Auto Detect GPS Button
  elements.btnGpsDetect.addEventListener('click', () => {
    if ('geolocation' in navigator) {
      elements.btnGpsDetect.disabled = true;
      elements.btnGpsDetect.textContent = 'Locating...';

      navigator.geolocation.getCurrentPosition(
        (position) => {
          elements.captureLat.value = position.coords.latitude.toFixed(6);
          elements.captureLon.value = position.coords.longitude.toFixed(6);
          elements.btnGpsDetect.disabled = false;
          elements.btnGpsDetect.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
            Auto Detect GPS
          `;
          showToast('GPS coordinates successfully captured.', 'success');
        },
        (error) => {
          console.warn('Geolocation error, generating mock coordinate:', error.message);
          
          // Generate a plausible mock coordinate in East Africa (Kenya/Ethiopia region)
          const mockLat = (-1.29 + (Math.random() - 0.5) * 0.1).toFixed(6);
          const mockLon = (36.82 + (Math.random() - 0.5) * 0.1).toFixed(6);
          
          elements.captureLat.value = mockLat;
          elements.captureLon.value = mockLon;
          
          elements.btnGpsDetect.disabled = false;
          elements.btnGpsDetect.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
            Auto Detect GPS
          `;
          showToast('Geolocation declined. Plotted mock coordinate.', 'warning');
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
      );
    } else {
      showToast('Geolocation not supported by this browser.', 'error');
    }
  });

  // Handle Form Submission
  elements.fieldCaptureForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const selectedType = document.querySelector('input[name="installation-type"]:checked').value;
    const lat = parseFloat(elements.captureLat.value);
    const lon = parseFloat(elements.captureLon.value);
    const notes = elements.captureNotes.value.trim();
    const uuid = elements.captureUuid.value;

    // Validate image presence
    if (!selectedImageHash) {
      showToast('Photo evidence is required for MRV capture verification.', 'error');
      return;
    }

    if (isNaN(lat) || isNaN(lon)) {
      showToast('Valid GPS coordinates are required.', 'error');
      return;
    }

    // 1. Construct new installation object
    const newRecord = {
      id: uuid,
      type: selectedType,
      lat: lat,
      lon: lon,
      timestamp: new Date().toISOString(),
      imageHash: selectedImageHash,
      imageName: selectedImageName,
      notes: notes,
      onChain: null
    };

    // 2. Execute Verification Engine to compute Trust Score
    const verification = runAutomatedVerificationRules(newRecord);
    newRecord.trustScore = verification.trustScore;
    
    // Status Logic: If Trust Score < 70, flag automatically. Otherwise start as Pending
    newRecord.status = verification.trustScore < 70 ? 'Flagged' : 'Pending';
    newRecord.payloadHash = calculatePayloadHash(newRecord);

    // 3. Persist to localStorage
    installations.push(newRecord);
    saveInstallations(installations);

    // 4. Update UI Dashboard & Map
    renderMapMarkers();
    updateKPIs();
    initChart();
    renderDashboardTable();

    // 5. Success Message & navigate back
    showToast(`Telemetry captured successfully. Auto-Calculated Trust Rating: ${newRecord.trustScore}%`, newRecord.status === 'Flagged' ? 'warning' : 'success');
    switchTab('dashboard');
  });
}

function handleUploadedFile(fileName) {
  // Generate a simulated SHA-256 for user uploaded files
  let nameHash = 0;
  for (let i = 0; i < fileName.length; i++) {
    nameHash = ((nameHash << 5) - nameHash) + fileName.charCodeAt(i);
    nameHash |= 0;
  }
  selectedImageHash = 'img_user_' + Math.abs(nameHash).toString(16).substring(0, 8);
  selectedImageName = fileName;

  elements.selectedFileName.textContent = selectedImageName;
  elements.selectedFileHash.textContent = `SHA-256: ${selectedImageHash}`;
  elements.selectedFileBanner.classList.remove('hidden');
}

// Harversine Distance Formula
function getDistanceKM(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// =============================================================================
// 7. Verification Engine Core System
// =============================================================================

function runAutomatedVerificationRules(record) {
  let score = 0;
  let duplicateImageFlag = false;
  let gpsJumpFlag = false;
  let gpsJumpDistance = 0;

  // RULE 1: Uniqueness check (50% score weight)
  // Scan database for identical image hashes
  const duplicate = installations.find(inst => 
    inst.id !== record.id && 
    inst.imageHash === record.imageHash
  );
  if (duplicate) {
    duplicateImageFlag = true;
  } else {
    score += 50; // Uniqueness adds 50 points
  }

  // RULE 2: GPS Drift Jump check (30% score weight)
  // Check if any other records submitted within the last 15 minutes (900s) are > 1km away
  const MAX_DRIFT_KM = 1.0;
  const TIME_WINDOW_SEC = 900; 

  const currentTimestampStr = record.timestamp;
  const currentTimestamp = new Date(currentTimestampStr).getTime();

  const gpsAnomalies = installations.filter(inst => {
    if (inst.id === record.id || !inst.lat || !inst.lon) return false;
    const timeDiffSeconds = Math.abs(currentTimestamp - new Date(inst.timestamp).getTime()) / 1000;
    
    if (timeDiffSeconds < TIME_WINDOW_SEC) {
      const distance = getDistanceKM(record.lat, record.lon, inst.lat, inst.lon);
      if (distance > MAX_DRIFT_KM) {
        gpsJumpDistance = distance;
        return true;
      }
    }
    return false;
  });

  if (gpsAnomalies.length > 0) {
    gpsJumpFlag = true;
  } else {
    score += 30; // GPS integrity adds 30 points
  }

  // RULE 3: Completeness Check (20% score weight)
  let completenessScore = 0;
  // Has photo evidence: +10 pts
  if (record.imageHash) {
    completenessScore += 10;
  }
  // Has detailed notes: +10 pts
  if (record.notes && record.notes.trim().length >= 10) {
    completenessScore += 10;
  } else if (record.notes && record.notes.trim().length > 0) {
    completenessScore += 5; // Partial credit
  }

  score += completenessScore;

  return {
    trustScore: score,
    duplicateImage: duplicateImageFlag,
    gpsJump: gpsJumpFlag,
    gpsDistance: gpsJumpDistance,
    completeness: completenessScore
  };
}

// Replay verification simulation with visual scans
function runVerificationReplayAnimation(record) {
  // Switch to Verification Tab
  switchTab('verification');
  selectedInstId = record.id;

  // Make inspector content visible and empty state hidden
  elements.verificationInspectorEmpty.classList.add('hidden');
  elements.verificationInspectorContent.classList.remove('hidden');

  // Reset Inspector display state to scanning/pending
  elements.inspectInstId.textContent = `UUID: ${record.id}`;
  
  let typeLabel = 'Clean Cooking';
  if (record.type === 'solar') typeLabel = 'Solar Power';
  else if (record.type === 'hybrid') typeLabel = 'Hybrid Energy';
  elements.inspectInstType.textContent = typeLabel;
  elements.inspectInstType.className = `badge type-${record.type}`;

  elements.inspectTrustScore.textContent = '0%';
  elements.inspectGaugeFill.style.strokeDashoffset = '125.6';
  elements.inspectGaugeFill.style.stroke = 'var(--color-primary)';

  // Reset check cards styling
  resetInspectorCheckCard(elements.checkUnique, 'Image Uniqueness Check', 'Scanning registry database...');
  resetInspectorCheckCard(elements.checkGps, 'GPS Drift Check', 'Analyzing geolocation telemetry...');
  resetInspectorCheckCard(elements.checkCompleteness, 'Completeness Check', 'Validating field notes & payload signatures...');

  elements.inspectStatusBanner.style.opacity = '0.5';
  elements.inspectStatusBadge.textContent = 'COMPUTING...';
  elements.inspectStatusBadge.className = 'badge status-pending';

  // Disable action buttons while playing animation
  elements.btnInspectorReplay.disabled = true;
  elements.btnInspectorAnchor.disabled = true;

  // Execute rules logic
  const verification = runAutomatedVerificationRules(record);

  // Phase 1: Uniqueness Check (after 600ms)
  setTimeout(() => {
    if (verification.duplicateImage) {
      setInspectorCheckCardResult(elements.checkUnique, 'failed', '✕', 'Uniqueness Check Failed', 'Duplicate photographic signature detected in database!');
    } else {
      setInspectorCheckCardResult(elements.checkUnique, 'passed', '✓', 'Uniqueness Check Passed', 'Asset photograph signature is verified unique.');
    }
  }, 600);

  // Phase 2: GPS Drift Check (after 1200ms)
  setTimeout(() => {
    if (verification.gpsJump) {
      setInspectorCheckCardResult(elements.checkGps, 'failed', '✕', 'GPS Drift Check Failed', `Impossible location variance detected! Drifted ${verification.gpsDistance.toFixed(2)}km.`);
    } else {
      setInspectorCheckCardResult(elements.checkGps, 'passed', '✓', 'GPS Drift Check Passed', 'Coordinates match temporal feasibility boundaries.');
    }
  }, 1200);

  // Phase 3: Completeness Check (after 1800ms)
  setTimeout(() => {
    if (verification.completeness === 20) {
      setInspectorCheckCardResult(elements.checkCompleteness, 'passed', '✓', 'Completeness Check Passed', 'Telemetry and evidence description parameters are fully completed.');
    } else if (verification.completeness >= 10) {
      setInspectorCheckCardResult(elements.checkCompleteness, 'warning', '⚠', 'Completeness Warning', 'Notes field is too short (<10 chars). Minimal context provided.');
    } else {
      setInspectorCheckCardResult(elements.checkCompleteness, 'failed', '✕', 'Completeness Check Failed', 'Incomplete telemetry submission. Missing vital metadata.');
    }
  }, 1800);

  // Phase 4: Final Gauge & Trust Score Animate (after 2400ms)
  setTimeout(() => {
    // Enable buttons
    elements.btnInspectorReplay.disabled = false;
    
    // Check role to enable anchor
    if (activeRole === 'verifier' && !record.onChain) {
      elements.btnInspectorAnchor.disabled = false;
    }

    // Gauge Animate
    let currentCount = 0;
    const targetScore = verification.trustScore;
    const interval = setInterval(() => {
      if (currentCount >= targetScore) {
        clearInterval(interval);
        elements.inspectTrustScore.textContent = `${targetScore}%`;
      } else {
        currentCount++;
        elements.inspectTrustScore.textContent = `${currentCount}%`;
      }
    }, 12);

    const gaugeOffset = 125.6 - (targetScore / 100) * 125.6;
    elements.inspectGaugeFill.style.strokeDashoffset = gaugeOffset;

    // Apply color based on score
    if (targetScore >= 75) {
      elements.inspectGaugeFill.style.stroke = 'var(--color-success)';
    } else if (targetScore >= 50) {
      elements.inspectGaugeFill.style.stroke = 'var(--color-warning)';
    } else {
      elements.inspectGaugeFill.style.stroke = 'var(--color-error)';
    }

    // Update Status Banner
    elements.inspectStatusBanner.style.opacity = '1';
    
    if (record.onChain) {
      elements.inspectStatusBadge.textContent = 'ANCHORED';
      elements.inspectStatusBadge.className = 'badge status-verified';
    } else if (targetScore >= 70) {
      elements.inspectStatusBadge.textContent = 'PASS (PENDING ANCHOR)';
      elements.inspectStatusBadge.className = 'badge status-pending';
    } else {
      elements.inspectStatusBadge.textContent = 'FAIL (FLAGGED)';
      elements.inspectStatusBadge.className = 'badge status-flagged';
    }
  }, 2400);
}

function resetInspectorCheckCard(cardEl, title, message) {
  cardEl.className = 'check-result-card';
  cardEl.querySelector('span').textContent = '○';
  cardEl.querySelector('h5').textContent = title;
  cardEl.querySelector('p').textContent = message;
}

function setInspectorCheckCardResult(cardEl, resultClass, iconChar, title, message) {
  cardEl.className = `check-result-card ${resultClass}`;
  cardEl.querySelector('span').textContent = iconChar;
  cardEl.querySelector('h5').textContent = title;
  cardEl.querySelector('p').textContent = message;
}

// Bind Inspector Events
function initInspectorEvents() {
  elements.btnInspectorReplay.addEventListener('click', () => {
    if (!selectedInstId) return;
    const record = installations.find(i => i.id === selectedInstId);
    if (record) {
      runVerificationReplayAnimation(record);
    }
  });

  elements.btnInspectorAnchor.addEventListener('click', () => {
    if (!selectedInstId) return;
    anchorOnSolana(selectedInstId);
  });
}

// =============================================================================
// 8. Solana On-Chain Anchoring Layer (Simulated)
// =============================================================================

function generateBase58(length = 44) {
  const chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function anchorOnSolana(instId) {
  const recordIndex = installations.findIndex(i => i.id === instId);
  if (recordIndex === -1) return;

  const record = installations[recordIndex];
  if (record.onChain) {
    showToast('Asset signature is already anchored on-chain.', 'warning');
    return;
  }

  // Generate mock Solana Block metadata
  const blockHeight = Math.floor(200000000 + Math.random() * 10000000);
  const slot = blockHeight + Math.floor(Math.random() * 8) + 1;
  const signature = generateBase58(88); // 88 base58 string standard signature

  // Anchor
  record.onChain = {
    signature: signature,
    blockHeight: blockHeight,
    slot: slot,
    timestamp: new Date().toISOString()
  };
  record.status = 'Verified'; // Verified status signifies passing verification + anchored

  installations[recordIndex] = record;
  saveInstallations(installations);

  // Success Updates
  showToast('Solana anchor broadcast completed. Slot verified.', 'success');

  // Reload current views
  updateKPIs();
  renderMapMarkers();
  renderDashboardTable();
  
  // Refresh detail views
  updateDrawerUI(instId);
  
  // If verifying on Verification tab, update inspector state
  if (activeTab === 'verification' && selectedInstId === instId) {
    runVerificationReplayAnimation(record);
  }
}

// =============================================================================
// 9. Side Drawer Inspector Module
// =============================================================================

function openDrawer(instId) {
  selectedInstId = instId;
  updateDrawerUI(instId);
  elements.sideDrawer.classList.add('open');
}
window.openDrawer = openDrawer;

function closeDrawer() {
  elements.sideDrawer.classList.remove('open');
}

function updateDrawerUI(instId) {
  const record = installations.find(i => i.id === instId);
  if (!record) return;

  // Title & Type
  elements.drawerTitle.textContent = `${record.type.toUpperCase()} Telemetry`;
  
  let typeLabel = 'Clean Cooking';
  if (record.type === 'solar') typeLabel = 'Solar Power';
  else if (record.type === 'hybrid') typeLabel = 'Hybrid Energy';
  elements.drawerBadgeType.textContent = typeLabel;
  elements.drawerBadgeType.className = `badge type-${record.type}`;

  // Trust score & status
  elements.drawerTrustScore.textContent = `${record.trustScore}%`;
  elements.drawerStatus.textContent = record.status;
  elements.drawerStatus.className = record.status.toLowerCase() === 'verified' 
    ? 'text-green' 
    : (record.status.toLowerCase() === 'flagged' ? 'text-red' : 'text-warning');

  // CO2 reduction estimate
  // Per year estimates: cookstove = 2.5t, solar = 1.8t, hybrid = 3.2t
  let co2Val = '2.5 t';
  if (record.type === 'solar') co2Val = '1.8 t';
  else if (record.type === 'hybrid') co2Val = '3.2 t';
  elements.drawerCo2.textContent = co2Val;

  // Meta details
  elements.drawerUuid.textContent = record.id;
  elements.drawerHash.textContent = record.payloadHash || 'N/A';
  elements.drawerGps.textContent = `${record.lat.toFixed(6)}, ${record.lon.toFixed(6)}`;
  
  const date = new Date(record.timestamp);
  elements.drawerTime.textContent = date.toLocaleString();
  elements.drawerNotes.textContent = record.notes || 'No description notes provided by field agent.';

  // Construct Audit timeline logs
  elements.drawerAuditTimeline.innerHTML = '';
  
  // Item 1: Submission
  addTimelineItem('Telemetry Received', `Payload metadata structured and saved in local MRV registry. Evidence File: ${record.imageName || 'N/A'} (Image Hash: ${record.imageHash})`, 'passed');

  // Run a quick rules check for display logs
  const checks = runAutomatedVerificationRules(record);

  // Item 2: Image Uniqueness
  if (checks.duplicateImage) {
    addTimelineItem('Duplicate check failed', 'Warning: Photographic evidence signature matches existing anchored assets! Flagged credit fraud.', 'failed');
  } else {
    addTimelineItem('Uniqueness Verified', 'Automated search completes with zero matching image records in registry.', 'passed');
  }

  // Item 3: GPS drift
  if (checks.gpsJump) {
    addTimelineItem('GPS Drift Violation', `Alert: Location variance check failed! Jump of ${checks.gpsDistance.toFixed(2)}km from previous entry is temporally impossible.`, 'failed');
  } else {
    addTimelineItem('GPS Coordinates Authenticated', 'Temporal speed variance is within standard 1.0 km boundaries.', 'passed');
  }

  // Item 4: Completeness
  if (checks.completeness === 20) {
    addTimelineItem('Completeness verified', 'Required metadata parameters, notes, and photographic hashes are complete.', 'passed');
  } else {
    addTimelineItem('Incomplete telemetry metadata', 'Warning: Notes field provides low environmental context (<10 chars).', 'failed');
  }

  // Blockchain details
  if (record.onChain) {
    elements.drawerBlockchainSection.style.display = 'block';
    elements.drawerTxSig.textContent = record.onChain.signature.substring(0, 24) + '...';
    elements.drawerTxSig.title = record.onChain.signature;
    elements.drawerBlockHeight.textContent = record.onChain.blockHeight.toLocaleString();
    
    const txTime = new Date(record.onChain.timestamp);
    elements.drawerTxTime.textContent = txTime.toLocaleString();

    // Hide anchoring action button
    elements.drawerBtnAction.style.display = 'none';
  } else {
    elements.drawerBlockchainSection.style.display = 'none';

    // Show action button only for admin Verifier role
    if (activeRole === 'verifier') {
      elements.drawerBtnAction.style.display = 'inline-flex';
      elements.drawerBtnAction.textContent = 'Anchor On-Chain';
    } else {
      elements.drawerBtnAction.style.display = 'none';
    }
  }
}

function addTimelineItem(title, description, status) {
  const li = document.createElement('li');
  li.className = `timeline-item ${status}`;
  li.innerHTML = `
    <h5>${title}</h5>
    <p>${description}</p>
  `;
  elements.drawerAuditTimeline.appendChild(li);
}

function initDrawerEvents() {
  elements.btnCloseDrawer.addEventListener('click', closeDrawer);
  elements.drawerOverlay.addEventListener('click', closeDrawer);

  // Replay verification from drawer
  elements.drawerBtnReplay.addEventListener('click', () => {
    if (!selectedInstId) return;
    const record = installations.find(i => i.id === selectedInstId);
    if (record) {
      closeDrawer();
      runVerificationReplayAnimation(record);
    }
  });

  // Verify & Anchor from drawer
  elements.drawerBtnAction.addEventListener('click', () => {
    if (!selectedInstId) return;
    anchorOnSolana(selectedInstId);
  });
}

// =============================================================================
// 10. On-Chain Ledger View Rendering
// =============================================================================

function renderLedgerTable() {
  const anchored = installations.filter(i => i.onChain);

  elements.ledgerTableBody.innerHTML = '';

  if (anchored.length === 0) {
    elements.ledgerTableBody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center" style="padding: 40px; text-align: center; color: var(--color-text-muted);">
          No environmental assets anchored on the simulated Solana ledger. Navigate to the Verifier role to anchor verified assets.
        </td>
      </tr>
    `;
    return;
  }

  anchored.forEach(inst => {
    const tr = document.createElement('tr');
    
    const txTime = new Date(inst.onChain.timestamp);
    const timeStr = `${txTime.toLocaleDateString()} ${txTime.toLocaleTimeString()}`;

    tr.innerHTML = `
      <td><span class="value code" style="font-family: monospace; font-weight: 600;">${inst.id.substring(0, 14)}...</span></td>
      <td><span class="value code text-blue" style="font-family: monospace; font-size: 11.5px;" title="${inst.onChain.signature}">${inst.onChain.signature.substring(0, 20)}...</span></td>
      <td><span>${inst.onChain.blockHeight.toLocaleString()}</span></td>
      <td><span>${inst.onChain.slot.toLocaleString()}</span></td>
      <td><span>${timeStr}</span></td>
      <td><span class="badge status-verified">Anchored (Simulated)</span></td>
    `;
    elements.ledgerTableBody.appendChild(tr);
  });
}

// =============================================================================
// 11. CSV Export Utility
// =============================================================================

function initExportCSV() {
  elements.btnExportCsv.addEventListener('click', () => {
    if (installations.length === 0) {
      showToast('No MRV registry logs available for export.', 'error');
      return;
    }

    let csvContent = 'data:text/csv;charset=utf-8,';
    
    // Headers
    csvContent += 'Installation ID,Module Type,Latitude,Longitude,Capture Timestamp,Trust Rating,Status,Solana Tx Signature,Simulated Block Height,Payload Hash\n';

    // Rows
    installations.forEach(inst => {
      const txSig = inst.onChain ? inst.onChain.signature : 'Not Anchored';
      const block = inst.onChain ? inst.onChain.blockHeight : 'N/A';
      
      const row = `"${inst.id}","${inst.type}",${inst.lat},${inst.lon},"${inst.timestamp}",${inst.trustScore},"${inst.status}","${txSig}","${block}","${inst.payloadHash}"`;
      csvContent += row + '\n';
    });

    // Download trigger
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'verifield_nexus_mrv_registry_export.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast('CSV registry download started successfully.', 'success');
  });
}

// =============================================================================
// 12. App Initialization Orchestrator
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize core systems
  initTheme();
  initRoles();
  initNavigation();
  
  // 2. Initialize Leaflet Map and Analytics Chart
  setTimeout(() => {
    initMap();
    initChart();
  }, 100);

  // 3. Render Dashboard list table and KPIs
  renderDashboardTable();
  updateKPIs();

  // 4. Bind Form & Inspector Events
  initFormInteractions();
  initInspectorEvents();
  initDrawerEvents();
  
  // 5. Bind Filters & Export events
  elements.tableSearch.addEventListener('input', renderDashboardTable);
  elements.filterType.addEventListener('change', renderDashboardTable);
  elements.filterStatus.addEventListener('change', renderDashboardTable);
  initExportCSV();

  // 6. Setup default role display layout
  applyRolePrivileges();

  // 7. Success log
  console.log('VeriField Nexus MRV Simulator Core initialized.');
});
