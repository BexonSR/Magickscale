// =============================================================
// MagickScale - Full App Logic
// Covers: Downscaler, AI Upscaler, Logo Remover tabs
// =============================================================

// =============================================
// GLOBAL STATE
// =============================================
let suffixState = {
    downscaler: '_4k',
    upscaler: '_upscaled',
    logo: '_clean',
    metadata: '_nometa',
    makePermanent: false
};

let fileQueue = [];    // Downscaler queue
let upQueue   = [];    // Upscaler queue
let lrQueue   = [];    // Logo-remover queue
let coQueue   = [];    // Converter queue
let mtQueue   = [];    // Metadata remover queue

let isDsProcessing = false;
let isUpProcessing = false;
let isLrProcessing = false;
let isSlProcessing = false;
let isMeProcessing = false;
let isOlProcessing = false;
let isCoProcessing = false;
let isMtProcessing = false;
let isVdProcessing = false;

let vdQueue   = [];    // Video processor queue

let dsStatusInterval, upStatusInterval, lrStatusInterval;
let slStatusInterval, meStatusInterval, olStatusInterval;
let coStatusInterval, mtStatusInterval;
let vdStatusInterval;

// Store loaded model info for credit display
let loadedModels = [];

// (Removed Gemini Method, as it now always uses Precise Math)

// =============================================
// UTILITY
// =============================================
function formatSize(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function apiCall(endpoint, data = {}) {
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await res.json();
    } catch (e) {
        console.error(`API error [${endpoint}]:`, e);
        return null;
    }
}

async function apiGet(endpoint) {
    try {
        const res = await fetch(endpoint);
        return await res.json();
    } catch (e) {
        console.error(`API GET error [${endpoint}]:`, e);
        return null;
    }
}

// =============================================
// QUEUE ITEM BUILDER (shared)
// =============================================
function buildQueueItem(file, idx, removeFn, processing) {
    const item = document.createElement('div');
    item.className = 'queue-item';

    let statusHtml = '';
    if (file.status === 'processing') {
        const pctStr = (file.percent !== undefined) ? ` (${file.percent}%)` : '...';
        statusHtml = `<div class="item-status status-processing">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg> Processing${pctStr}
        </div>`;
    } else if (file.status === 'completed') {
        const saved = (file.size_saved > 0) ? ` (Saved ${formatSize(file.size_saved)})` : '';
        statusHtml = `<div class="item-status status-completed">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg> Done${saved}
        </div>`;
    } else if (file.status === 'failed') {
        statusHtml = `<div class="item-status status-failed" title="${file.error || 'Failed'}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
            </svg> Failed
        </div>`;
    } else {
        statusHtml = `<div class="item-status status-pending">Pending</div>`;
    }

    const sizeStr = file.metadata ? formatSize(file.metadata.size) : '';
    const resStr  = file.metadata ? `${file.metadata.width}×${file.metadata.height}` : '';
    const metaStr = [resStr, sizeStr].filter(Boolean).join(' · ');

    const removeBtn = (!processing)
        ? `<button class="btn-remove" onclick="${removeFn}(${idx})" title="Remove">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
              </svg>
           </button>`
        : '';

    item.innerHTML = `
        <div style="display:flex; justify-content:space-between; width:100%; position:relative; z-index:1;">
            <div class="item-info">
                <div class="item-name" title="${file.path}">${file.name}</div>
                ${metaStr ? `<div class="item-meta">${metaStr}</div>` : ''}
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                ${statusHtml}
                ${removeBtn}
            </div>
        </div>
        ${(file.status === 'processing' && file.percent !== undefined) 
            ? `<div style="position:absolute; bottom:0; left:0; height:3px; background:linear-gradient(90deg, var(--primary), var(--accent)); width:${file.percent}%; transition:width 0.3s; z-index:0;"></div>`
            : ''}
    `;
    return item;
}

// =============================================
// TAB NAVIGATION
// =============================================
// =============================================
// NAVIGATION & THEME
// =============================================
const dropdownTrigger = document.getElementById('dropdown-trigger-btn');
const dropdownMenu = document.getElementById('dropdown-menu-list');
const dropdownContainer = document.getElementById('custom-tool-dropdown');
const currentToolLabel = document.getElementById('current-tool-label');

if (dropdownTrigger && dropdownMenu) {
    dropdownTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownContainer.classList.toggle('open');
    });
    
    document.addEventListener('click', (e) => {
        if (dropdownContainer && !dropdownContainer.contains(e.target)) {
            dropdownContainer.classList.remove('open');
        }
    });

    const items = dropdownMenu.querySelectorAll('.dropdown-item');
    items.forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.value;
            currentToolLabel.textContent = item.textContent;
            
            items.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            dropdownContainer.classList.remove('open');
            
            document.querySelectorAll('.tab-panel').forEach(p => {
                p.style.display = 'none';
                p.classList.remove('active');
            });
            const panel = document.getElementById('panel-' + tab);
            if (panel) {
                panel.style.display = 'grid';
                panel.classList.add('active');
            }
        });
    });
}

const btnThemeToggle = document.getElementById('btn-theme-toggle');
const btnGlassToggle = document.getElementById('btn-glass-toggle');

// Dynamic range slider gradients
function updateSliders() {
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 100;
        const val = parseFloat(slider.value) || 0;
        const percentage = (val - min) / (max - min) * 100;
        slider.style.background = `linear-gradient(to right, var(--primary) 0%, var(--accent) ${percentage}%, var(--slider-track-bg) ${percentage}%, var(--slider-track-bg) 100%)`;
    });
}

function initSliders() {
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        slider.addEventListener('input', updateSliders);
    });
    updateSliders();
}

function updateThemeIcon() {
    const btn = document.getElementById('btn-theme-toggle');
    if (!btn) return;
    const isLight = document.body.dataset.theme === 'light';
    if (isLight) {
        // Show moon icon in light mode
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    } else {
        // Show sun icon in dark mode
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    }
}

// Load saved theme and glass states
if (localStorage.getItem('theme') === 'light') document.body.dataset.theme = 'light';
if (localStorage.getItem('glass') === 'off') document.body.classList.add('no-glass');

updateThemeIcon();
initSliders();

if (btnThemeToggle) {
    btnThemeToggle.addEventListener('click', () => {
        if (document.body.dataset.theme === 'light') {
            delete document.body.dataset.theme;
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.dataset.theme = 'light';
            localStorage.setItem('theme', 'light');
        }
        updateThemeIcon();
        // Wait a tiny bit for CSS variables to transition if any, and refresh slider background gradients
        setTimeout(updateSliders, 0);
    });
}
if (btnGlassToggle) {
    btnGlassToggle.addEventListener('click', () => {
        document.body.classList.toggle('no-glass');
        localStorage.setItem('glass', document.body.classList.contains('no-glass') ? 'off' : 'on');
    });
}

// =============================================
// DOWNSCALER TAB
// =============================================
const dropZone        = document.getElementById('drop-zone');
const btnAddFiles     = document.getElementById('btn-add-files');
const btnAddFolder    = document.getElementById('btn-add-folder');
const btnClearQueue   = document.getElementById('btn-clear-queue');
const queueList       = document.getElementById('queue-list');
const emptyState      = document.getElementById('empty-state');
const queueCount      = document.getElementById('queue-count');
const btnStart        = document.getElementById('btn-start');
const btnCancel       = document.getElementById('btn-cancel');
const btnBrowseOut    = document.getElementById('btn-browse-out');
const inputOutDir     = document.getElementById('setting-out-dir');
const progressArea    = document.getElementById('progress-area');
const progressText    = document.getElementById('progress-text');
const progressSpeed   = document.getElementById('progress-speed');
const progressBarFill = document.getElementById('progress-bar-fill');
const progressTime    = document.getElementById('progress-time');
const spaceSavedBadge = document.getElementById('space-saved-badge');
const spaceSavedVal   = document.getElementById('space-saved-val');
const settingQuality  = document.getElementById('setting-quality');
const qualityVal      = document.getElementById('quality-val');
const settingFormat   = document.getElementById('setting-format');
const settingMode     = document.getElementById('setting-mode');
const customSizeInputs = document.getElementById('custom-size-inputs');

settingQuality.addEventListener('input', e => { qualityVal.textContent = e.target.value + '%'; });
settingFormat.addEventListener('change', e => {
    const qGroup = document.getElementById('quality-group');
    const disabled = (e.target.value === 'PNG' || e.target.value === 'same');
    qGroup.style.opacity = disabled ? '0.4' : '1';
    settingQuality.disabled = disabled;
});
settingMode.addEventListener('change', e => {
    if (e.target.value === 'custom') {
        customSizeInputs.style.display = 'flex';
    } else {
        customSizeInputs.style.display = 'none';
    }
});

function renderQueue() {
    queueCount.textContent = fileQueue.length;
    if (fileQueue.length === 0) {
        emptyState.style.display = 'flex';
        queueList.style.display = 'none';
        btnClearQueue.style.display = 'none';
        if (!isDsProcessing) btnStart.disabled = true;
        queueList.innerHTML = '';
        return;
    }
    emptyState.style.display = 'none';
    queueList.style.display = 'flex';
    btnClearQueue.style.display = 'inline-flex';
    if (!isDsProcessing) btnStart.disabled = false;
    queueList.innerHTML = '';
    fileQueue.forEach((f, i) => queueList.appendChild(buildQueueItem(f, i, 'removeItem', isDsProcessing)));
}

window.removeItem = idx => { if (!isDsProcessing) { fileQueue.splice(idx, 1); renderQueue(); } };
btnClearQueue.addEventListener('click', () => { if (!isDsProcessing) { fileQueue = []; renderQueue(); } });

async function addFilesToQueue(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    fileQueue = [...fileQueue, ...newItems];
    renderQueue();
    const result = await apiCall('/api/get-metadata', { files: paths });
    if (result && result.metadata) {
        fileQueue.forEach(item => {
            if (result.metadata[item.path]) {
                item.metadata = result.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderQueue();
    }
}

btnAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files && res.files.length) addFilesToQueue(res.files);
});
btnAddFolder.addEventListener('click', async () => {
    const res = await apiCall('/api/select-folder');
    if (res && res.files && res.files.length) addFilesToQueue(res.files);
});
btnBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) inputOutDir.value = res.folder;
});

btnStart.addEventListener('click', async () => {
    if (fileQueue.length === 0 || isDsProcessing) return;
    const settings = {
        mode:     document.getElementById('setting-mode').value,
        filter:   document.getElementById('setting-filter').value,
        format:   settingFormat.value,
        quality:  parseInt(settingQuality.value),
        out_dir:  inputOutDir.value,
        use_gpu:  document.getElementById('setting-gpu').checked,
        custom_width: parseInt(document.getElementById('setting-custom-width').value) || 1920,
        custom_height: parseInt(document.getElementById('setting-custom-height').value) || 1080,
        suffix:   suffixState.downscaler
    };

    const res = await apiCall('/api/start', { files: fileQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isDsProcessing = true;
        btnStart.style.display = 'none';
        btnCancel.style.display = 'inline-flex';
        progressArea.style.display = 'block';
        btnAddFiles.disabled = true;
        btnAddFolder.disabled = true;
        btnClearQueue.style.display = 'none';
        fileQueue.forEach(f => { f.status = 'pending'; f.size_saved = 0; f.error = ''; });
        startStatusPolling();
    }
});

btnCancel.addEventListener('click', async () => {
    btnCancel.disabled = true;
    btnCancel.textContent = 'Cancelling...';
    await apiCall('/api/cancel');
});

function startStatusPolling() {
    if (dsStatusInterval) clearInterval(dsStatusInterval);
    dsStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/status');
        if (!data) return;
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (fileQueue[i]) {
                    fileQueue[i].status    = s.status;
                    fileQueue[i].size_saved = s.size_saved || 0;
                    fileQueue[i].error     = s.error || '';
                }
            });
            renderQueue();
        }
        const total = fileQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        progressBarFill.style.width = pct + '%';
        progressText.textContent  = `Processing: ${done} / ${total} (${pct}%)`;
        progressSpeed.textContent = data.speed ? `${data.speed} img/s` : '';
        progressTime.textContent  = `Elapsed: ${data.time_elapsed}s`;
        if ((data.total_space_saved || 0) > 0) {
            spaceSavedBadge.style.display = 'inline-flex';
            spaceSavedVal.textContent = formatSize(data.total_space_saved);
        }
        if (!data.processing) { clearInterval(dsStatusInterval); finishDownscaling(); }
    }, 500);
}

function finishDownscaling() {
    isDsProcessing = false;
    btnStart.style.display = 'inline-flex';
    btnCancel.style.display = 'none';
    btnCancel.disabled = false;
    btnCancel.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Cancel`;
    btnAddFiles.disabled = false;
    btnAddFolder.disabled = false;
    renderQueue();
}

renderQueue();

// =============================================
// AI UPSCALER TAB
// =============================================
const btnUpAddFiles    = document.getElementById('btn-up-add-files');
const btnUpClear       = document.getElementById('btn-up-clear');
const upQueueList      = document.getElementById('up-queue-list');
const upEmptyState     = document.getElementById('up-empty-state');
const upQueueCount     = document.getElementById('up-queue-count');
const btnUpStart       = document.getElementById('btn-up-start');
const btnUpCancel      = document.getElementById('btn-up-cancel');
const btnUpBrowseOut   = document.getElementById('btn-up-browse-out');
const upOutDir         = document.getElementById('up-out-dir');
const upProgressArea   = document.getElementById('up-progress-area');
const upProgressText   = document.getElementById('up-progress-text');
const upProgressBar    = document.getElementById('up-progress-bar-fill');
const upProgressTime   = document.getElementById('up-progress-time');
const engineStatusText = document.getElementById('engine-status-text');
const btnDownloadEngine = document.getElementById('btn-download-engine');
const btnResetEngine   = document.getElementById('btn-reset-engine');
const modelSelect      = document.getElementById('up-setting-model');
const modelCredit      = document.getElementById('model-credit');
const upScaleSlider    = document.getElementById('up-scale');
const upScaleVal       = document.getElementById('up-scale-val');
const upScaleHint      = document.getElementById('up-scale-hint');
const gpuDetectStatus  = document.getElementById('gpu-detect-status');
const gpuBadge         = document.getElementById('gpu-badge');

// Scale slider
upScaleSlider.addEventListener('input', () => {
    const v = parseInt(upScaleSlider.value);
    upScaleVal.textContent = v + '×';
    if (v > 4) {
        upScaleHint.textContent = `${v}× = runs 2 passes of 4× each (slower). Best quality.`;
    } else {
        upScaleHint.textContent = `${v}× — single pass. ${v === 4 ? '1080p → 4K' : v === 2 ? '1080p → 2K' : ''}`;
    }
});

modelSelect.addEventListener('change', () => {
    updateSelectedModelDetails();
});


async function checkEngineStatus() {
    engineStatusText.textContent = 'Checking engine...';
    engineStatusText.className = 'engine-status-text';
    const res = await apiCall('/api/upscaler/check-engine');
    if (!res) return;
    if (res.ready) {
        engineStatusText.textContent = '✓ Real-ESRGAN engine ready';
        engineStatusText.className = 'engine-status-text ok';
        btnDownloadEngine.style.display = 'none';
        btnResetEngine.style.display = 'none';
        if (upQueue.length > 0) btnUpStart.disabled = false;
    } else {
        // If we are currently downloading/extracting in background
        const progress = await apiGet('/api/upscaler/download-progress');
        if (progress && (progress.status === 'downloading' || progress.status === 'extracting')) {
            startEngineDownloadPolling();
        } else {
            engineStatusText.textContent = '⚠ Engine not downloaded yet';
            engineStatusText.className = 'engine-status-text missing';
            btnDownloadEngine.style.display = 'inline-flex';
            btnResetEngine.style.display = 'none';
            btnUpStart.disabled = true;
        }
    }
    return res.ready;
}

async function detectGpu() {
    const res = await apiGet('/api/upscaler/detect-gpu');
    if (res && res.nvidia && res.name) {
        gpuDetectStatus.textContent = `✓ Detected: ${res.name}`;
        gpuDetectStatus.style.color = 'var(--success)';
        gpuBadge.textContent = `🎮 ${res.name}`;
        gpuBadge.style.display = 'inline-flex';
        const gpuSelect = document.getElementById('up-gpu-id');
        if (gpuSelect) gpuSelect.value = '0';
    } else {
        gpuDetectStatus.textContent = 'No dedicated GPU found — using GPU 0 (auto)';
        gpuDetectStatus.style.color = 'var(--text-muted)';
    }
}

const selectedModelBox = document.getElementById('selected-model-box');

function updateSelectedModelDetails() {
    const key = modelSelect.value;
    const m = loadedModels.find(x => x.key === key);
    if (!m) {
        selectedModelBox.style.display = 'none';
        return;
    }
    
    selectedModelBox.style.display = 'block';
    let statusText = '';
    let actionBtn = '';
    
    if (m.bundled) {
        statusText = `<span class="model-status" style="color:var(--primary); font-weight:600;">✓ Ready (Built-in)</span>`;
    } else if (m.downloaded) {
        statusText = `<span class="model-status" style="color:var(--success); font-weight:600;">✓ Ready (Downloaded)</span>`;
    } else {
        statusText = `<span class="model-status" style="color:var(--warning); font-weight:600;">⚠ Not Downloaded</span>`;
        actionBtn = `<button class="btn btn-warning btn-sm" style="margin-top: 8px; width: 100%;" onclick="downloadSelectedModel('${m.key}', this)">⬇ Download Model Files</button>`;
    }
    
    selectedModelBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
            <strong style="color:white; font-size:0.9rem;">${m.display.split('(')[0].trim()}</strong>
            <span style="font-size:0.75rem; background:var(--primary); color:white; padding:2px 8px; border-radius:10px; font-weight:600;">${m.scale}× Scale</span>
        </div>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom: 8px;">
            ${m.credit}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem;">
            <span>Status:</span>
            ${statusText}
        </div>
        ${actionBtn}
    `;
}

window.downloadSelectedModel = async (modelKey, btn) => {
    btn.disabled = true;
    btn.textContent = '↻ Downloading model files (~20MB)...';
    const res = await apiCall('/api/upscaler/download-model', { model_key: modelKey });
    if (res && res.success) {
        btn.textContent = '✓ Download Complete';
        btn.style.background = 'rgba(16,185,129,0.1)';
        btn.style.color = 'var(--success)';
        const m = loadedModels.find(x => x.key === modelKey);
        if (m) m.downloaded = true;
        const opt = modelSelect.querySelector(`option[value="${modelKey}"]`);
        if (opt) opt.disabled = false;
        updateSelectedModelDetails();
    } else {
        btn.textContent = '✗ Failed to download. Retry?';
        btn.disabled = false;
    }
};

async function loadModels() {
    const res = await apiGet('/api/upscaler/list-models');
    if (!res || !res.models) return;
    loadedModels = res.models;

    modelSelect.innerHTML = '';
    res.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.key;
        opt.textContent = m.display;
        // Don't disable it so the user can select it and download it via the Get button
        modelSelect.appendChild(opt);
    });

    const first = res.models.find(m => m.downloaded || m.bundled) || res.models[0];
    if (first) {
        modelSelect.value = first.key;
        modelCredit.textContent = '';
        updateSelectedModelDetails();
    }
}

let engineDownloadInterval = null;

btnResetEngine.addEventListener('click', async () => {
    if (engineDownloadInterval) clearInterval(engineDownloadInterval);
    btnResetEngine.disabled = true;
    await apiCall('/api/upscaler/reset-engine-state');
    btnResetEngine.disabled = false;
    btnDownloadEngine.disabled = false;
    btnDownloadEngine.textContent = '⬇ Download Engine';
    checkEngineStatus();
});

function startEngineDownloadPolling() {
    if (engineDownloadInterval) clearInterval(engineDownloadInterval);
    btnDownloadEngine.disabled = true;
    btnDownloadEngine.textContent = '↻ Connecting...';
    btnResetEngine.style.display = 'inline-flex';
    
    engineDownloadInterval = setInterval(async () => {
        const res = await apiGet('/api/upscaler/download-progress');
        if (!res) return;
        
        if (res.status === 'downloading') {
            const pct = res.percent || 0;
            btnDownloadEngine.textContent = `⬇ Downloading (${pct}%)`;
        } else if (res.status === 'extracting') {
            btnDownloadEngine.textContent = `📦 Extracting engine...`;
        } else if (res.status === 'completed') {
            clearInterval(engineDownloadInterval);
            btnResetEngine.style.display = 'none';
            await checkEngineStatus();
            await loadModels();
        } else if (res.status === 'failed') {
            clearInterval(engineDownloadInterval);
            btnResetEngine.style.display = 'none';
            engineStatusText.textContent = `Download failed: ${res.error || 'Unknown error'}`;
            engineStatusText.className = 'engine-status-text missing';
            btnDownloadEngine.disabled = false;
            btnDownloadEngine.textContent = '⬇ Retry Download';
        }
    }, 500);
}

btnDownloadEngine.addEventListener('click', async () => {
    btnDownloadEngine.disabled = true;
    btnDownloadEngine.textContent = '↻ Starting...';
    const res = await apiCall('/api/upscaler/download-engine');
    if (res && res.status === 'started') {
        startEngineDownloadPolling();
    } else {
        engineStatusText.textContent = 'Failed to trigger engine download.';
        btnDownloadEngine.disabled = false;
        btnDownloadEngine.textContent = '⬇ Retry Download';
    }
});


function renderUpQueue() {
    upQueueCount.textContent = upQueue.length;
    if (upQueue.length === 0) {
        upEmptyState.style.display = 'flex';
        upQueueList.style.display = 'none';
        btnUpClear.style.display = 'none';
        upQueueList.innerHTML = '';
        if (!isUpProcessing) btnUpStart.disabled = true;
        return;
    }
    upEmptyState.style.display = 'none';
    upQueueList.style.display = 'flex';
    btnUpClear.style.display = 'inline-flex';
    upQueueList.innerHTML = '';
    upQueue.forEach((f, i) => upQueueList.appendChild(buildQueueItem(f, i, 'removeUpItem', isUpProcessing)));
    checkEngineStatus().then(ready => {
        if (!isUpProcessing && ready) btnUpStart.disabled = false;
    });
}

window.removeUpItem = idx => { if (!isUpProcessing) { upQueue.splice(idx, 1); renderUpQueue(); } };
btnUpClear.addEventListener('click', () => { if (!isUpProcessing) { upQueue = []; renderUpQueue(); } });

btnUpAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (!res || !res.files) return;
    const newItems = res.files.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    upQueue = [...upQueue, ...newItems];
    renderUpQueue();
    const meta = await apiCall('/api/get-metadata', { files: res.files });
    if (meta && meta.metadata) {
        upQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderUpQueue();
    }
});

btnUpBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) upOutDir.value = res.folder;
});

btnUpStart.addEventListener('click', async () => {
    if (upQueue.length === 0 || isUpProcessing) return;
    const settings = {
        model:   modelSelect.value,
        format:  document.getElementById('up-setting-format').value,
        scale:   parseInt(upScaleSlider.value),
        gpu_id:  parseInt(document.getElementById('up-gpu-id').value),
        tta:     document.getElementById('up-tta').checked,
        out_dir: upOutDir.value,
        suffix:  suffixState.upscaler
    };
    const res = await apiCall('/api/upscaler/start', { files: upQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isUpProcessing = true;
        btnUpStart.style.display = 'none';
        btnUpCancel.style.display = 'inline-flex';
        upProgressArea.style.display = 'block';
        btnUpAddFiles.disabled = true;
        btnUpClear.style.display = 'none';
        upQueue.forEach(f => { f.status = 'pending'; f.error = ''; });
        startUpPolling();
    }
});

btnUpCancel.addEventListener('click', async () => {
    btnUpCancel.disabled = true;
    btnUpCancel.textContent = 'Cancelling...';
    await apiCall('/api/upscaler/cancel');
});

function startUpPolling() {
    if (upStatusInterval) clearInterval(upStatusInterval);
    upStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/upscaler/status');
        if (!data) return;
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (upQueue[i]) { 
                    upQueue[i].status = s.status; 
                    upQueue[i].error = s.error || ''; 
                    upQueue[i].percent = s.percent;
                }
            });
            upQueueList.innerHTML = '';
            upQueue.forEach((f, i) => upQueueList.appendChild(buildQueueItem(f, i, 'removeUpItem', true)));
        }
        const total = upQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        upProgressBar.style.width = pct + '%';
        upProgressText.textContent = `Upscaling: ${done} / ${total} (${pct}%)`;
        upProgressTime.textContent = `Elapsed: ${data.time_elapsed}s`;
        if (!data.processing) { clearInterval(upStatusInterval); finishUpscaling(); }
    }, 500);
}

function finishUpscaling() {
    isUpProcessing = false;
    btnUpStart.style.display = 'inline-flex';
    btnUpCancel.style.display = 'none';
    btnUpCancel.disabled = false;
    btnUpCancel.textContent = 'Cancel';
    btnUpAddFiles.disabled = false;
    renderUpQueue();
}

// =============================================
// LOGO REMOVER TAB
// =============================================
const btnLrAddFiles  = document.getElementById('btn-lr-add-files');
const btnLrAddFolder = document.getElementById('btn-lr-add-folder');
const btnLrClear     = document.getElementById('btn-lr-clear');
const lrQueueList    = document.getElementById('lr-queue-list');
const lrEmptyState   = document.getElementById('lr-empty-state');
const lrQueueCount   = document.getElementById('lr-queue-count');
const btnLrStart     = document.getElementById('btn-lr-start');
const btnLrCancel    = document.getElementById('btn-lr-cancel');
const btnLrBrowseOut = document.getElementById('btn-lr-browse-out');
const lrOutDir       = document.getElementById('lr-out-dir');
const lrProgressArea = document.getElementById('lr-progress-area');
const lrProgressText = document.getElementById('lr-progress-text');
const lrProgressBar  = document.getElementById('lr-progress-bar-fill');
const lrProgressTime = document.getElementById('lr-progress-time');
const lrMethodSelect = document.getElementById('lr-method');
const lrManualPosGroup = document.getElementById('lr-manual-pos-group');
const lrManualSizeGroup = document.getElementById('lr-manual-size-group');

lrMethodSelect.addEventListener('change', () => {
    const isGemini = lrMethodSelect.value === 'gemini';
    lrManualPosGroup.style.display = isGemini ? 'none' : 'block';
    lrManualSizeGroup.style.display = isGemini ? 'none' : 'block';
});

// Manual size slider
const lrSizeSlider = document.getElementById('lr-size');
const lrSizeVal    = document.getElementById('lr-size-val');
lrSizeSlider.addEventListener('input', () => { lrSizeVal.textContent = lrSizeSlider.value + '%'; });

function renderLrQueue() {
    lrQueueCount.textContent = lrQueue.length;
    if (lrQueue.length === 0) {
        lrEmptyState.style.display = 'flex';
        lrQueueList.style.display = 'none';
        btnLrClear.style.display = 'none';
        lrQueueList.innerHTML = '';
        btnLrStart.disabled = true;
        
        return;
    }
    lrEmptyState.style.display = 'none';
    lrQueueList.style.display = 'flex';
    btnLrClear.style.display = 'inline-flex';
    if (!isLrProcessing) {
        btnLrStart.disabled = false;
        
    }
    lrQueueList.innerHTML = '';
    lrQueue.forEach((f, i) => lrQueueList.appendChild(buildQueueItem(f, i, 'removeLrItem', isLrProcessing)));
}

window.removeLrItem = idx => { if (!isLrProcessing) { lrQueue.splice(idx, 1); renderLrQueue(); } };
btnLrClear.addEventListener('click', () => { if (!isLrProcessing) { lrQueue = []; renderLrQueue(); } });

async function addLrFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    lrQueue = [...lrQueue, ...newItems];
    renderLrQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        lrQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderLrQueue();
    }
}

btnLrAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files) addLrFiles(res.files);
});
btnLrAddFolder.addEventListener('click', async () => {
    const res = await apiCall('/api/select-folder');
    if (res && res.files) addLrFiles(res.files);
});
btnLrBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) lrOutDir.value = res.folder;
});

async function startLogoRemoval(settings) {
    const res = await apiCall('/api/logo-remover/start', {
        files: lrQueue.map(f => f.path), settings
    });
    if (res && res.status === 'started') {
        isLrProcessing = true;
        btnLrStart.style.display = 'none';
        
        btnLrCancel.style.display = 'inline-flex';
        lrProgressArea.style.display = 'block';
        btnLrAddFiles.disabled = true;
        btnLrAddFolder.disabled = true;
        btnLrClear.style.display = 'none';
        lrQueue.forEach(f => { f.status = 'pending'; f.error = ''; });
        startLrPolling();
    }
}

btnLrStart.addEventListener('click', async () => {
    if (lrQueue.length === 0 || isLrProcessing) return;
    const method = lrMethodSelect.value;
    await startLogoRemoval({
        gemini_mode: method === 'gemini',
        position:    document.getElementById('lr-position').value,
        size_pct:    parseInt(lrSizeSlider.value),
        method:      method,
        out_dir:     lrOutDir.value,
        suffix:      suffixState.logo
    });
});

btnLrCancel.addEventListener('click', async () => {
    btnLrCancel.disabled = true;
    btnLrCancel.textContent = 'Cancelling...';
    await apiCall('/api/logo-remover/cancel');
});

function startLrPolling() {
    if (lrStatusInterval) clearInterval(lrStatusInterval);
    lrStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/logo-remover/status');
        if (!data) return;
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (lrQueue[i]) { lrQueue[i].status = s.status; lrQueue[i].error = s.error || ''; }
            });
            renderLrQueue();
        }
        const total = lrQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        lrProgressBar.style.width = pct + '%';
        lrProgressText.textContent = `Processing: ${done} / ${total} (${pct}%)`;
        lrProgressTime.textContent = `Elapsed: ${data.time_elapsed}s`;
        if (!data.processing) { clearInterval(lrStatusInterval); finishLrProcessing(); }
    }, 500);
}

function finishLrProcessing() {
    isLrProcessing = false;
    btnLrStart.style.display = 'inline-flex';
    
    btnLrCancel.style.display = 'none';
    btnLrCancel.disabled = false;
    btnLrCancel.textContent = 'Cancel';
    btnLrAddFiles.disabled = false;
    btnLrAddFolder.disabled = false;
    renderLrQueue();
}

// =============================================
// IMAGE SLICER TAB
// =============================================
let slicerQueue = [];

const btnSlAddFiles = document.getElementById('btn-sl-add-files');
const btnSlClear = document.getElementById('btn-sl-clear');
const slQueueList = document.getElementById('sl-queue-list');
const slEmptyState = document.getElementById('sl-empty-state');
const slQueueCount = document.getElementById('sl-queue-count');
const btnSlStart = document.getElementById('btn-sl-start');
const btnSlCancel = document.getElementById('btn-sl-cancel');
const btnSlBrowseOut = document.getElementById('btn-sl-browse-out');
const slOutDir = document.getElementById('sl-out-dir');
const slProgressArea = document.getElementById('sl-progress-area');
const slProgressText = document.getElementById('sl-progress-text');
const slProgressBar = document.getElementById('sl-progress-bar-fill');
const slModeSelect = document.getElementById('sl-mode');
const slGridOptions = document.getElementById('sl-grid-options');
const slSteamOptions = document.getElementById('sl-steam-options');

slModeSelect.addEventListener('change', () => {
    if (slModeSelect.value === 'grid') {
        slGridOptions.style.display = 'block';
        slSteamOptions.style.display = 'none';
    } else {
        slGridOptions.style.display = 'none';
        slSteamOptions.style.display = 'block';
    }
});

function renderSlQueue() {
    slQueueCount.textContent = slicerQueue.length;
    if (slicerQueue.length === 0) {
        slEmptyState.style.display = 'flex';
        slQueueList.style.display = 'none';
        btnSlClear.style.display = 'none';
        document.getElementById('btn-sl-download-zip').style.display = 'none';
        slQueueList.innerHTML = '';
        if (!isSlProcessing) btnSlStart.disabled = true;
        return;
    }
    slEmptyState.style.display = 'none';
    slQueueList.style.display = 'flex';
    btnSlClear.style.display = 'inline-flex';
    document.getElementById('btn-sl-download-zip').style.display = 'inline-flex';
    if (!isSlProcessing) btnSlStart.disabled = false;
    slQueueList.innerHTML = '';
    slicerQueue.forEach((f, i) => slQueueList.appendChild(buildQueueItem(f, i, 'removeSlItem', isSlProcessing)));
}

window.removeSlItem = idx => { if (!isSlProcessing) { slicerQueue.splice(idx, 1); renderSlQueue(); } };
btnSlClear.addEventListener('click', () => { if (!isSlProcessing) { slicerQueue = []; renderSlQueue(); } });

async function addSlFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    slicerQueue = [...slicerQueue, ...newItems];
    renderSlQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        slicerQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderSlQueue();
    }
}

btnSlAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files) addSlFiles(res.files);
});

btnSlBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) slOutDir.value = res.folder;
});

btnSlStart.addEventListener('click', async () => {
    if (slicerQueue.length === 0 || isSlProcessing) return;
    const settings = {
        slice_mode: slModeSelect.value,
        grid_cols: parseInt(document.getElementById('sl-grid-cols').value) || 2,
        grid_rows: parseInt(document.getElementById('sl-grid-rows').value) || 1,
        steam_x_mid: parseInt(document.getElementById('sl-steam-x-mid').value) || 508,
        steam_x_side: parseInt(document.getElementById('sl-steam-x-side').value) || 1022,
        steam_y: parseInt(document.getElementById('sl-steam-y').value) || 0,
        steam_h: parseInt(document.getElementById('sl-steam-h').value) || 600,
        steam_mid_slices: parseInt(document.getElementById('sl-steam-mid-slices').value) || 1,
        steam_side_slices: parseInt(document.getElementById('sl-steam-side-slices').value) || 1,
        out_dir: slOutDir.value
    };
    const res = await apiCall('/api/slicer/start', { files: slicerQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isSlProcessing = true;
        btnSlStart.style.display = 'none';
        document.getElementById('btn-sl-download-zip').style.display = 'none';
        btnSlCancel.style.display = 'inline-flex';
        slProgressArea.style.display = 'block';
        btnSlAddFiles.disabled = true;
        btnSlClear.style.display = 'none';
        slicerQueue.forEach(f => { f.status = 'pending'; f.error = ''; });
        startSlPolling();
    }
});

function getSlSettings() {
    return {
        slice_mode: slModeSelect.value,
        grid_cols: parseInt(document.getElementById('sl-grid-cols').value) || 2,
        grid_rows: parseInt(document.getElementById('sl-grid-rows').value) || 1,
        steam_x_mid: parseInt(document.getElementById('sl-steam-x-mid').value) || 508,
        steam_x_side: parseInt(document.getElementById('sl-steam-x-side').value) || 1022,
        steam_y: parseInt(document.getElementById('sl-steam-y').value) || 0,
        steam_h: parseInt(document.getElementById('sl-steam-h').value) || 600,
        steam_mid_slices: parseInt(document.getElementById('sl-steam-mid-slices').value) || 1,
        steam_side_slices: parseInt(document.getElementById('sl-steam-side-slices').value) || 1,
        out_dir: slOutDir.value
    };
}

document.getElementById('btn-sl-preview').addEventListener('click', async () => {
    if (slicerQueue.length === 0) {
        alert("Please select at least one image first.");
        return;
    }
    const btn = document.getElementById('btn-sl-preview');
    const loading = document.getElementById('sl-preview-loading');
    const gallery = document.getElementById('sl-preview-gallery');
    const text = document.getElementById('sl-preview-text');
    
    btn.disabled = true;
    loading.style.display = 'flex';
    gallery.innerHTML = '';
    gallery.style.display = 'none';
    text.style.display = 'none';
    
    const settings = getSlSettings();
    const res = await apiCall('/api/slicer/preview', { files: [slicerQueue[0].path], settings });
    
    loading.style.display = 'none';
    btn.disabled = false;
    
    if (res && res.images) {
        gallery.style.display = 'flex';
        res.images.forEach(img => {
            const el = document.createElement('img');
            el.src = img.data;
            el.style.maxHeight = '200px';
            el.style.objectFit = 'contain';
            el.title = img.name;
            gallery.appendChild(el);
        });
    } else {
        text.style.display = 'block';
        text.textContent = 'Preview failed: ' + (res ? res.error : 'Unknown error');
    }
});

document.getElementById('btn-sl-download-zip').addEventListener('click', async () => {
    if (slicerQueue.length === 0) return;
    const btn = document.getElementById('btn-sl-download-zip');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.textContent = 'Generating ZIP...';
    
    const settings = getSlSettings();
    const res = await apiCall('/api/slicer/download-zip', { files: slicerQueue.map(f => f.path), settings });
    
    btn.disabled = false;
    btn.innerHTML = originalText;
    
    if (res && res.zip) {
        const a = document.createElement('a');
        a.href = res.zip;
        a.download = res.filename || 'slices.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        alert("Failed to generate ZIP: " + (res ? res.error : "Unknown error"));
    }
});

btnSlCancel.addEventListener('click', async () => {
    btnSlCancel.disabled = true;
    btnSlCancel.textContent = 'Cancelling...';
    await apiCall('/api/slicer/cancel');
});

function startSlPolling() {
    if (slStatusInterval) clearInterval(slStatusInterval);
    slStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/slicer/status');
        if (!data) return;
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (slicerQueue[i]) { slicerQueue[i].status = s.status; slicerQueue[i].error = s.error || ''; }
            });
            renderSlQueue();
        }
        const total = slicerQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        slProgressBar.style.width = pct + '%';
        slProgressText.textContent = `Slicing: ${done} / ${total} (${pct}%)`;
        if (!data.processing) { clearInterval(slStatusInterval); finishSlProcessing(); }
    }, 500);
}

function finishSlProcessing() {
    isSlProcessing = false;
    btnSlStart.style.display = 'inline-flex';
    document.getElementById('btn-sl-download-zip').style.display = 'inline-flex';
    btnSlCancel.style.display = 'none';
    btnSlCancel.disabled = false;
    btnSlCancel.textContent = 'Cancel';
    btnSlAddFiles.disabled = false;
    btnSlClear.style.display = 'inline-flex';
    renderSlQueue();
}

// =============================================
// IMAGE MERGER TAB
// =============================================
let mergerQueue = [];

const btnMeAddFiles = document.getElementById('btn-me-add-files');
const btnMeClear = document.getElementById('btn-me-clear');
const meQueueList = document.getElementById('me-queue-list');
const meEmptyState = document.getElementById('me-empty-state');
const meQueueCount = document.getElementById('me-queue-count');
const btnMeStart = document.getElementById('btn-me-start');
const btnMeCancel = document.getElementById('btn-me-cancel');
const btnMeBrowseOut = document.getElementById('btn-me-browse-out');
const meOutPath = document.getElementById('me-out-path');
const meProgressArea = document.getElementById('me-progress-area');
const meProgressText = document.getElementById('me-progress-text');
const meProgressBar  = document.getElementById('me-progress-bar-fill');
const meModeSelect = document.getElementById('me-mode');
const meGridOptions = document.getElementById('me-grid-options');

meModeSelect.addEventListener('change', () => {
    if (meModeSelect.value === 'grid') {
        meGridOptions.style.display = 'block';
    } else {
        meGridOptions.style.display = 'none';
    }
});

function renderMeQueue() {
    meQueueCount.textContent = mergerQueue.length;
    if (mergerQueue.length === 0) {
        meEmptyState.style.display = 'flex';
        meQueueList.style.display = 'none';
        btnMeClear.style.display = 'none';
        meQueueList.innerHTML = '';
        if (!isMeProcessing) btnMeStart.disabled = true;
        return;
    }
    meEmptyState.style.display = 'none';
    meQueueList.style.display = 'flex';
    btnMeClear.style.display = 'inline-flex';
    if (!isMeProcessing && meOutPath.value) btnMeStart.disabled = false;
    meQueueList.innerHTML = '';
    mergerQueue.forEach((f, i) => meQueueList.appendChild(buildQueueItem(f, i, 'removeMeItem', isMeProcessing)));
}

window.removeMeItem = idx => { if (!isMeProcessing) { mergerQueue.splice(idx, 1); renderMeQueue(); } };
btnMeClear.addEventListener('click', () => { if (!isMeProcessing) { mergerQueue = []; renderMeQueue(); } });

async function addMeFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    mergerQueue = [...mergerQueue, ...newItems];
    renderMeQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        mergerQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderMeQueue();
    }
}

btnMeAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files) addMeFiles(res.files);
});

btnMeBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-file');
    if (res && res.file) {
        meOutPath.value = res.file;
        if (mergerQueue.length > 0 && !isMeProcessing) btnMeStart.disabled = false;
    }
});

btnMeStart.addEventListener('click', async () => {
    if (mergerQueue.length === 0 || !meOutPath.value || isMeProcessing) return;
    const settings = {
        files: mergerQueue.map(f => f.path),
        out_path: meOutPath.value,
        merge_mode: meModeSelect.value,
        grid_cols: parseInt(document.getElementById('me-grid-cols').value) || 2,
        grid_rows: parseInt(document.getElementById('me-grid-rows').value) || 2
    };
    const res = await apiCall('/api/merger/start', { settings });
    if (res && res.status === 'started') {
        isMeProcessing = true;
        btnMeStart.style.display = 'none';
        btnMeCancel.style.display = 'inline-flex';
        meProgressArea.style.display = 'block';
        btnMeAddFiles.disabled = true;
        btnMeClear.style.display = 'none';
        startMePolling();
    }
});

btnMeCancel.addEventListener('click', async () => {
    btnMeCancel.disabled = true;
    btnMeCancel.textContent = 'Cancelling...';
    await apiCall('/api/merger/cancel');
});

function startMePolling() {
    if (meStatusInterval) clearInterval(meStatusInterval);
    meProgressBar.style.width = '0%';
    meStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/merger/status');
        if (!data) return;
        if (data.queue && data.queue[0]) {
            const status = data.queue[0].status;
            let pct = 0;
            let statusText = 'Merging...';
            if (status === 'completed') {
                pct = 100;
                statusText = 'Success!';
            } else if (status === 'failed') {
                pct = 100;
                statusText = 'Failed: ' + data.queue[0].error;
            } else {
                pct = 50;
                statusText = 'Merging...';
            }
            meProgressBar.style.width = pct + '%';
            meProgressText.textContent = `Status: ${statusText} (${pct}%)`;
        }
        if (!data.processing) { clearInterval(meStatusInterval); finishMeProcessing(); }
    }, 500);
}

function finishMeProcessing() {
    isMeProcessing = false;
    btnMeStart.style.display = 'inline-flex';
    btnMeCancel.style.display = 'none';
    btnMeCancel.disabled = false;
    btnMeCancel.textContent = 'Cancel';
    btnMeAddFiles.disabled = false;
    renderMeQueue();
}

// =============================================
// IMAGE OVERLAY TAB
// =============================================
const btnOlSelectBase = document.getElementById('btn-ol-select-base');
const btnOlSelectOverlay = document.getElementById('btn-ol-select-overlay');
const btnOlBrowseOut = document.getElementById('btn-ol-browse-out');
const btnOlStart = document.getElementById('btn-ol-start');
const btnOlCancel = document.getElementById('btn-ol-cancel');

const olBasePath = document.getElementById('ol-base-path');
const olOverlayPath = document.getElementById('ol-overlay-path');
const olOutPath = document.getElementById('ol-out-path');

const olScaleSlider = document.getElementById('ol-scale');
const olScaleVal = document.getElementById('ol-scale-val');
const olOpacitySlider = document.getElementById('ol-opacity');
const olOpacityVal = document.getElementById('ol-opacity-val');
const olProgressArea = document.getElementById('ol-progress-area');
const olProgressText = document.getElementById('ol-progress-text');
const olProgressBar  = document.getElementById('ol-progress-bar-fill');

olScaleSlider.addEventListener('input', e => {
    const scaleType = document.querySelector('input[name="ol-scale-type"]:checked').value;
    olScaleVal.textContent = e.target.value + (scaleType === 'percent' ? '%' : 'px');
});

document.querySelectorAll('input[name="ol-scale-type"]').forEach(r => {
    r.addEventListener('change', () => {
        const scaleType = r.value;
        olScaleSlider.min = scaleType === 'percent' ? '5' : '10';
        olScaleSlider.max = scaleType === 'percent' ? '300' : '8192';
        olScaleSlider.value = scaleType === 'percent' ? '100' : '500';
        olScaleVal.textContent = olScaleSlider.value + (scaleType === 'percent' ? '%' : 'px');
    });
});

olOpacitySlider.addEventListener('input', e => { olOpacityVal.textContent = e.target.value + '%'; });

function checkOlInputs() {
    if (olBasePath.value && olOverlayPath.value && olOutPath.value && !isOlProcessing) {
        btnOlStart.disabled = false;
    } else {
        btnOlStart.disabled = true;
    }
}

const btnOlPreview = document.getElementById('btn-ol-preview');
const olPreviewImg = document.getElementById('ol-preview-img');
const olPreviewText = document.getElementById('ol-preview-text');
const olPreviewLoading = document.getElementById('ol-preview-loading');

btnOlPreview.addEventListener('click', async () => {
    if (!olBasePath.value || !olOverlayPath.value) {
        alert('Please select both a base image and an overlay image first.');
        return;
    }
    
    olPreviewLoading.style.display = 'flex';
    
    const settings = {
        base_img: olBasePath.value,
        overlay_img: olOverlayPath.value,
        gravity: document.getElementById('ol-gravity').value,
        offset_x: parseInt(document.getElementById('ol-offset-x').value) || 0,
        offset_y: parseInt(document.getElementById('ol-offset-y').value) || 0,
        opacity: parseInt(olOpacitySlider.value) || 100,
        scale: parseFloat(olScaleSlider.value) || 100,
        scale_type: document.querySelector('input[name="ol-scale-type"]:checked').value
    };
    
    const res = await apiCall('/api/overlay/preview', { settings });
    olPreviewLoading.style.display = 'none';
    
    if (res && res.image) {
        olPreviewImg.src = res.image;
        olPreviewImg.style.display = 'block';
        olPreviewText.style.display = 'none';
    } else if (res && res.error) {
        alert('Preview error: ' + res.error);
    }
});

btnOlSelectBase.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files && res.files[0]) {
        olBasePath.value = res.files[0];
        checkOlInputs();
    }
});

btnOlSelectOverlay.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files && res.files[0]) {
        olOverlayPath.value = res.files[0];
        checkOlInputs();
    }
});

btnOlBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-file');
    if (res && res.file) {
        olOutPath.value = res.file;
        checkOlInputs();
    }
});

btnOlStart.addEventListener('click', async () => {
    if (!olBasePath.value || !olOverlayPath.value || !olOutPath.value || isOlProcessing) return;
    const settings = {
        base_img: olBasePath.value,
        overlay_img: olOverlayPath.value,
        out_path: olOutPath.value,
        gravity: document.getElementById('ol-gravity').value,
        offset_x: parseInt(document.getElementById('ol-offset-x').value) || 0,
        offset_y: parseInt(document.getElementById('ol-offset-y').value) || 0,
        opacity: parseInt(olOpacitySlider.value),
        scale: parseFloat(olScaleSlider.value),
        scale_type: document.querySelector('input[name="ol-scale-type"]:checked').value
    };
    
    const res = await apiCall('/api/overlay/start', { settings });
    if (res && res.status === 'started') {
        isOlProcessing = true;
        btnOlStart.style.display = 'none';
        btnOlCancel.style.display = 'inline-flex';
        olProgressArea.style.display = 'block';
        btnOlSelectBase.disabled = true;
        btnOlSelectOverlay.disabled = true;
        startOlPolling();
    }
});

btnOlCancel.addEventListener('click', async () => {
    btnOlCancel.disabled = true;
    btnOlCancel.textContent = 'Cancelling...';
    await apiCall('/api/overlay/cancel');
});

function startOlPolling() {
    if (olStatusInterval) clearInterval(olStatusInterval);
    olProgressBar.style.width = '0%';
    olStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/overlay/status');
        if (!data) return;
        if (data.queue && data.queue[0]) {
            const status = data.queue[0].status;
            let pct = 0;
            let statusText = 'Compositing...';
            if (status === 'completed') {
                pct = 100;
                statusText = 'Success!';
            } else if (status === 'failed') {
                pct = 100;
                statusText = 'Failed: ' + data.queue[0].error;
            } else {
                pct = 50;
                statusText = 'Compositing...';
            }
            olProgressBar.style.width = pct + '%';
            olProgressText.textContent = `Status: ${statusText} (${pct}%)`;
        }
        if (!data.processing) { clearInterval(olStatusInterval); finishOlProcessing(); }
    }, 500);
}

function finishOlProcessing() {
    isOlProcessing = false;
    btnOlStart.style.display = 'inline-flex';
    btnOlCancel.style.display = 'none';
    btnOlCancel.disabled = false;
    btnOlCancel.textContent = 'Cancel';
    btnOlSelectBase.disabled = false;
    btnOlSelectOverlay.disabled = false;
    checkOlInputs();
}

// =============================================
// FORMAT CONVERTER TAB
// =============================================
const btnCoAddFiles = document.getElementById('btn-co-add-files');
const btnCoClear = document.getElementById('btn-co-clear');
const coQueueList = document.getElementById('co-queue-list');
const coEmptyState = document.getElementById('co-empty-state');
const coQueueCount = document.getElementById('co-queue-count');
const btnCoStart = document.getElementById('btn-co-start');
const btnCoCancel = document.getElementById('btn-co-cancel');
const btnCoBrowseOut = document.getElementById('btn-co-browse-out');
const coOutDir = document.getElementById('co-out-dir');
const coProgressArea = document.getElementById('co-progress-area');
const coProgressText = document.getElementById('co-progress-text');
const coProgressBar = document.getElementById('co-progress-bar-fill');
const coFormatSelect = document.getElementById('co-format');
const coQualitySlider = document.getElementById('co-quality');
const coQualityVal = document.getElementById('co-quality-val');

coQualitySlider.addEventListener('input', e => { coQualityVal.textContent = e.target.value + '%'; });

coFormatSelect.addEventListener('change', e => {
    const qGroup = document.getElementById('co-quality-group');
    const disabled = (e.target.value === 'PNG');
    qGroup.style.opacity = disabled ? '0.4' : '1';
    coQualitySlider.disabled = disabled;
});

function renderCoQueue() {
    coQueueCount.textContent = coQueue.length;
    if (coQueue.length === 0) {
        coEmptyState.style.display = 'flex';
        coQueueList.style.display = 'none';
        btnCoClear.style.display = 'none';
        coQueueList.innerHTML = '';
        if (!isCoProcessing) btnCoStart.disabled = true;
        return;
    }
    coEmptyState.style.display = 'none';
    coQueueList.style.display = 'flex';
    btnCoClear.style.display = 'inline-flex';
    if (!isCoProcessing) btnCoStart.disabled = false;
    coQueueList.innerHTML = '';
    coQueue.forEach((f, i) => coQueueList.appendChild(buildQueueItem(f, i, 'removeCoItem', isCoProcessing)));
}

window.removeCoItem = idx => { if (!isCoProcessing) { coQueue.splice(idx, 1); renderCoQueue(); } };
btnCoClear.addEventListener('click', () => { if (!isCoProcessing) { coQueue = []; renderCoQueue(); } });

async function addCoFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    coQueue = [...coQueue, ...newItems];
    renderCoQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        coQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderCoQueue();
    }
}

btnCoAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files) addCoFiles(res.files);
});

btnCoBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) coOutDir.value = res.folder;
});

btnCoStart.addEventListener('click', async () => {
    if (coQueue.length === 0 || isCoProcessing) return;
    const settings = {
        format: coFormatSelect.value,
        quality: parseInt(coQualitySlider.value),
        out_dir: coOutDir.value
    };
    const res = await apiCall('/api/converter/start', { files: coQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isCoProcessing = true;
        btnCoStart.style.display = 'none';
        btnCoCancel.style.display = 'inline-flex';
        coProgressArea.style.display = 'block';
        btnCoAddFiles.disabled = true;
        btnCoClear.style.display = 'none';
        coQueue.forEach(f => { f.status = 'pending'; f.error = ''; });
        startCoPolling();
    }
});

btnCoCancel.addEventListener('click', async () => {
    btnCoCancel.disabled = true;
    btnCoCancel.textContent = 'Cancelling...';
    await apiCall('/api/converter/cancel');
});

function startCoPolling() {
    if (coStatusInterval) clearInterval(coStatusInterval);
    coStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/converter/status');
        if (!data) return;
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (coQueue[i]) {
                    coQueue[i].status = s.status;
                    coQueue[i].size_saved = s.size_saved || 0;
                    coQueue[i].error = s.error || '';
                }
            });
            renderCoQueue();
        }
        const total = coQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        coProgressBar.style.width = pct + '%';
        coProgressText.textContent = `Converting: ${done} / ${total} (${pct}%)`;
        if (!data.processing) { clearInterval(coStatusInterval); finishCoProcessing(); }
    }, 500);
}

function finishCoProcessing() {
    isCoProcessing = false;
    btnCoStart.style.display = 'inline-flex';
    btnCoCancel.style.display = 'none';
    btnCoCancel.disabled = false;
    btnCoCancel.textContent = 'Cancel';
    btnCoAddFiles.disabled = false;
    renderCoQueue();
}

/* ==========================================================================
   METADATA REMOVER
   ========================================================================== */
const mtQueueCount   = document.getElementById('mt-queue-count');
const mtEmptyState   = document.getElementById('mt-empty-state');
const mtQueueList    = document.getElementById('mt-queue-list');
const btnMtAddFiles  = document.getElementById('btn-mt-add-files');
const btnMtAddFolder = document.getElementById('btn-mt-add-folder');
const btnMtClear     = document.getElementById('btn-mt-clear');

const btnMtStart     = document.getElementById('btn-mt-start');
const btnMtCancel    = document.getElementById('btn-mt-cancel');
const btnMtBrowseOut = document.getElementById('btn-mt-browse-out');
const mtOutDir       = document.getElementById('mt-out-dir');
const mtSuffix       = document.getElementById('mt-suffix');

const mtProgressArea = document.getElementById('mt-progress-area');
const mtProgressText = document.getElementById('mt-progress-text');
const mtProgressBar  = document.getElementById('mt-progress-bar-fill');
const mtProgressTime = document.getElementById('mt-progress-time');

function renderMtQueue() {
    mtQueueCount.textContent = mtQueue.length;
    if (mtQueue.length === 0) {
        mtEmptyState.style.display = 'flex';
        mtQueueList.style.display = 'none';
        btnMtClear.style.display = 'none';
        mtQueueList.innerHTML = '';
        btnMtStart.disabled = true;
        return;
    }
    mtEmptyState.style.display = 'none';
    mtQueueList.style.display = 'flex';
    btnMtClear.style.display = 'inline-flex';
    if (!isMtProcessing) btnMtStart.disabled = false;
    mtQueueList.innerHTML = '';
    mtQueue.forEach((f, i) => mtQueueList.appendChild(buildQueueItem(f, i, 'removeMtItem', isMtProcessing)));
}

window.removeMtItem = idx => { if (!isMtProcessing) { mtQueue.splice(idx, 1); renderMtQueue(); } };
btnMtClear.addEventListener('click', () => { if (!isMtProcessing) { mtQueue = []; renderMtQueue(); } });

async function addMtFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    mtQueue = [...mtQueue, ...newItems];
    renderMtQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        mtQueue.forEach(item => {
            if (meta.metadata[item.path]) {
                item.metadata = meta.metadata[item.path];
                item.name = item.metadata.name || item.name;
            }
        });
        renderMtQueue();
    }
}

btnMtAddFiles.addEventListener('click', async () => {
    const res = await apiCall('/api/select-files');
    if (res && res.files) addMtFiles(res.files);
});
btnMtAddFolder.addEventListener('click', async () => {
    const res = await apiCall('/api/select-folder');
    if (res && res.files) addMtFiles(res.files);
});
btnMtBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) mtOutDir.value = res.folder;
});

btnMtStart.addEventListener('click', async () => {
    if (mtQueue.length === 0 || isMtProcessing) return;
    const res = await apiCall('/api/metadata-remover/start', {
        files: mtQueue.map(f => f.path),
        settings: {
            out_dir: mtOutDir.value,
            suffix:  mtSuffix.value
        }
    });
    if (res && res.status === 'started') {
        isMtProcessing = true;
        btnMtStart.style.display = 'none';
        btnMtCancel.style.display = 'inline-flex';
        mtProgressArea.style.display = 'block';
        btnMtAddFiles.disabled = true;
        btnMtAddFolder.disabled = true;
        btnMtClear.style.display = 'none';
        mtQueue.forEach(f => { f.status = 'pending'; f.error = ''; f.size_saved = 0; });
        startMtPolling();
    }
});

btnMtCancel.addEventListener('click', async () => {
    btnMtCancel.disabled = true;
    btnMtCancel.textContent = 'Cancelling...';
    await apiCall('/api/metadata-remover/cancel');
});

function startMtPolling() {
    if (mtStatusInterval) clearInterval(mtStatusInterval);
    mtStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/metadata-remover/status');
        if (!data) return;
        
        if (data.queue) {
            data.queue.forEach((s, i) => {
                if (mtQueue[i]) { 
                    mtQueue[i].status = s.status; 
                    mtQueue[i].error = s.error || '';
                    if (s.size_saved) mtQueue[i].size_saved = s.size_saved;
                }
            });
            renderMtQueue();
        }
        
        const total = mtQueue.length, done = data.total_processed || 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        mtProgressBar.style.width = pct + '%';
        mtProgressText.textContent = `Stripping: ${done}/${total} (${pct}%)`;
        mtProgressTime.textContent = `${data.time_elapsed || 0}s`;
        
        if (!data.processing) {
            clearInterval(mtStatusInterval);
            isMtProcessing = false;
            btnMtStart.style.display = 'inline-flex';
            btnMtCancel.style.display = 'none';
            btnMtCancel.disabled = false;
            btnMtCancel.textContent = 'Cancel';
            btnMtAddFiles.disabled = false;
            btnMtAddFolder.disabled = false;
            renderMtQueue();
        }
    }, 1000);
}

// =============================================
// Hook into HTMLSelectElement value setter to sync custom dropdowns
const originalSelectValueSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
Object.defineProperty(HTMLSelectElement.prototype, 'value', {
    set: function(val) {
        originalSelectValueSetter.call(this, val);
        this.dispatchEvent(new CustomEvent('selectvaluechanged'));
    }
});

function initCustomSelects() {
    document.querySelectorAll('select.custom-select').forEach(select => {
        if (select.dataset.customInitialized) return;
        select.dataset.customInitialized = 'true';

        // Hide the native select
        select.style.display = 'none';

        // Create container wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-container';
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);

        // Create trigger button
        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        wrapper.appendChild(trigger);

        // Create options menu
        const menu = document.createElement('div');
        menu.className = 'custom-select-options';
        wrapper.appendChild(menu);

        function updateTriggerText() {
            const selectedOpt = select.options[select.selectedIndex];
            trigger.innerHTML = `
                <span>${selectedOpt ? selectedOpt.textContent : ''}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="select-arrow-icon"><polyline points="6 9 12 15 18 9"/></svg>
            `;
        }

        function rebuildOptions() {
            menu.innerHTML = '';
            Array.from(select.options).forEach(opt => {
                const item = document.createElement('div');
                item.className = 'custom-select-option';
                if (opt.value === select.value) {
                    item.classList.add('active');
                }
                item.textContent = opt.textContent;
                item.dataset.value = opt.value;

                item.addEventListener('click', (e) => {
                    e.stopPropagation();
                    select.value = opt.value;
                    select.dispatchEvent(new Event('change'));
                    closeAllCustomSelects();
                });

                menu.appendChild(item);
            });
            updateTriggerText();
        }

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = wrapper.classList.contains('open');
            closeAllCustomSelects();
            if (!isOpen) {
                wrapper.classList.add('open');
            }
        });

        select.addEventListener('change', () => {
            updateTriggerText();
            menu.querySelectorAll('.custom-select-option').forEach(item => {
                if (item.dataset.value === select.value) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        });

        select.addEventListener('selectvaluechanged', () => {
            updateTriggerText();
            menu.querySelectorAll('.custom-select-option').forEach(item => {
                if (item.dataset.value === select.value) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        });

        const observer = new MutationObserver(() => {
            rebuildOptions();
        });
        observer.observe(select, { childList: true });

        rebuildOptions();
    });
}

function closeAllCustomSelects() {
    document.querySelectorAll('.custom-select-container').forEach(w => {
        w.classList.remove('open');
    });
}

document.addEventListener('click', closeAllCustomSelects);

// =============================================
// INIT — runs when DOM is ready
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    initCustomSelects();
    renderQueue();
    renderUpQueue();
    renderLrQueue();
    renderSlQueue();
    renderMeQueue();
    renderCoQueue();

    // Custom downscaler resolution toggling
    const settingMode = document.getElementById('setting-mode');
    const customSizeInputs = document.getElementById('custom-size-inputs');
    if (settingMode && customSizeInputs) {
        settingMode.addEventListener('change', () => {
            customSizeInputs.style.display = settingMode.value === 'custom' ? 'flex' : 'none';
        });
    }

    // Initialize active panel based on select value
    const toolSelect = document.getElementById('tool-select');
    if (toolSelect) {
        document.querySelectorAll('.tab-panel').forEach(p => {
            p.style.display = 'none';
            p.classList.remove('active');
        });
        const panel = document.getElementById('panel-' + toolSelect.value);
        if (panel) {
            panel.style.display = 'grid';
            panel.classList.add('active');
        }
    }

    // Upscaler init (runs in background)
    checkEngineStatus();
    detectGpu();
    loadModels();
    
    // Settings panel init
    initSettingsPanel();
});

// =============================================
// SETTINGS PANEL & APPLICATION CONTROL
// =============================================
function initSettingsPanel() {
    const inputDs = document.getElementById('settings-suffix-downscaler');
    const inputUp = document.getElementById('settings-suffix-upscaler');
    const inputLr = document.getElementById('settings-suffix-logo');
    const inputMt = document.getElementById('settings-suffix-metadata');
    const inputMtTab = document.getElementById('mt-suffix');
    const togglePermanent = document.getElementById('settings-suffix-permanent-toggle');
    const btnKill = document.getElementById('btn-kill-app');
    const btnKillFloating = document.getElementById('btn-kill-app-floating');

    if (!inputDs || !inputUp || !inputLr || !inputMt || !inputMtTab || !togglePermanent || !btnKill) return;

    // Load from localStorage or defaults
    const savedDs = localStorage.getItem('suffix_downscaler') || '_4k';
    const savedUp = localStorage.getItem('suffix_upscaler') || '_upscaled';
    const savedLr = localStorage.getItem('suffix_logo') || '_clean';
    const savedMt = localStorage.getItem('suffix_metadata') || '_nometa';
    const savedPerm = localStorage.getItem('suffix_make_permanent') === 'true';

    // Initialize session state
    suffixState.downscaler = savedDs;
    suffixState.upscaler = savedUp;
    suffixState.logo = savedLr;
    suffixState.metadata = savedMt;
    suffixState.makePermanent = savedPerm;

    // Populate inputs in UI
    inputDs.value = suffixState.downscaler;
    inputUp.value = suffixState.upscaler;
    inputLr.value = suffixState.logo;
    inputMt.value = suffixState.metadata;
    inputMtTab.value = suffixState.metadata;
    togglePermanent.checked = suffixState.makePermanent;

    // Dynamically update output folder input placeholders
    function updatePlaceholders() {
        const dsOut = document.getElementById('setting-out-dir');
        if (dsOut) dsOut.placeholder = `Same folder (adds ${suffixState.downscaler})`;

        const upOut = document.getElementById('up-out-dir');
        if (upOut) upOut.placeholder = `Same folder (adds ${suffixState.upscaler})`;

        const lrOut = document.getElementById('lr-out-dir');
        if (lrOut) lrOut.placeholder = `Same folder (adds ${suffixState.logo})`;
    }
    updatePlaceholders();

    // Helper to persist to localStorage if permanent option is enabled
    function saveSuffix(key, val) {
        if (suffixState.makePermanent) {
            localStorage.setItem('suffix_' + key, val);
        }
    }

    // Toggle permanent change
    togglePermanent.addEventListener('change', () => {
        suffixState.makePermanent = togglePermanent.checked;
        localStorage.setItem('suffix_make_permanent', suffixState.makePermanent);
        
        // If checked, write all current suffixes to localStorage immediately
        if (suffixState.makePermanent) {
            localStorage.setItem('suffix_downscaler', suffixState.downscaler);
            localStorage.setItem('suffix_upscaler', suffixState.upscaler);
            localStorage.setItem('suffix_logo', suffixState.logo);
            localStorage.setItem('suffix_metadata', suffixState.metadata);
        }
    });

    // Inputs value change event listeners
    inputDs.addEventListener('input', () => {
        suffixState.downscaler = inputDs.value;
        saveSuffix('downscaler', inputDs.value);
        updatePlaceholders();
    });
    inputUp.addEventListener('input', () => {
        suffixState.upscaler = inputUp.value;
        saveSuffix('upscaler', inputUp.value);
        updatePlaceholders();
    });
    inputLr.addEventListener('input', () => {
        suffixState.logo = inputLr.value;
        saveSuffix('logo', inputLr.value);
        updatePlaceholders();
    });
    inputMt.addEventListener('input', () => {
        suffixState.metadata = inputMt.value;
        saveSuffix('metadata', inputMt.value);
        inputMtTab.value = inputMt.value;
    });
    inputMtTab.addEventListener('input', () => {
        suffixState.metadata = inputMtTab.value;
        saveSuffix('metadata', inputMtTab.value);
        inputMt.value = inputMtTab.value;
    });

    // Custom Models Folder configuration
    const inputModelsPath = document.getElementById('settings-models-path');
    const btnBrowseModelsPath = document.getElementById('btn-browse-models-path');
    const btnClearModelsPath = document.getElementById('btn-clear-models-path');

    if (inputModelsPath && btnBrowseModelsPath && btnClearModelsPath) {
        // Load initial setting
        apiCall('/api/settings/get').then(settings => {
            if (settings && settings.custom_models_path) {
                inputModelsPath.value = settings.custom_models_path;
            }
        });

        // Browse click
        btnBrowseModelsPath.addEventListener('click', async () => {
            const res = await apiCall('/api/settings/browse-folder');
            if (res && res.folder) {
                inputModelsPath.value = res.folder;
                await apiCall('/api/settings/save', { custom_models_path: res.folder });
                await loadModels(); // Refresh upscaler models dropdown
            }
        });

        // Clear click
        btnClearModelsPath.addEventListener('click', async () => {
            inputModelsPath.value = '';
            await apiCall('/api/settings/save', { custom_models_path: '' });
            await loadModels(); // Refresh upscaler models dropdown
        });
    }

    // Clean Kill Functionality
    const killModal = document.getElementById('kill-modal');
    const btnKillConfirm = document.getElementById('btn-kill-confirm');
    const btnKillCancel = document.getElementById('btn-kill-cancel');

    function triggerKillApp() {
        if (killModal) {
            killModal.classList.add('active');
        }
    }

    if (btnKillCancel && killModal) {
        btnKillCancel.addEventListener('click', () => {
            killModal.classList.remove('active');
        });
    }

    if (btnKillConfirm && killModal) {
        btnKillConfirm.addEventListener('click', async () => {
            killModal.classList.remove('active');

            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.inset = '0';
            overlay.style.background = 'rgba(4, 4, 10, 0.95)';
            overlay.style.zIndex = '99999';
            overlay.style.display = 'flex';
            overlay.style.flexDirection = 'column';
            overlay.style.alignItems = 'center';
            overlay.style.justifyContent = 'center';
            overlay.style.gap = '20px';
            overlay.style.color = 'white';
            overlay.innerHTML = `
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2" class="spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                <h2 style="font-weight: 600;">MagickScale is shutting down...</h2>
                <p style="color: var(--text-muted); font-size: 0.9rem;">The Python server has been stopped. You can safely close this window.</p>
            `;
            document.body.appendChild(overlay);

            try {
                await apiCall('/api/kill-app');
            } catch(e) {
                console.error("Error calling kill-app:", e);
            }

            setTimeout(() => {
                window.close();
                window.location.href = "about:blank";
            }, 1000);
        });
    }

    btnKill.addEventListener('click', triggerKillApp);
    if (btnKillFloating) {
        btnKillFloating.addEventListener('click', triggerKillApp);
    }
}

// =============================================
// VIDEO PROCESSOR TAB
// =============================================
const btnVdAddFiles    = document.getElementById('btn-vd-add-files');
const btnVdAddFolder   = document.getElementById('btn-vd-add-folder');
const btnVdClear       = document.getElementById('btn-vd-clear');
const vdQueueList      = document.getElementById('vd-queue');
const vdEmptyState     = document.getElementById('vd-empty');
const vdQueueCount     = document.getElementById('vd-queue-count');
const btnVdStart       = document.getElementById('btn-vd-start');
const btnVdCancel      = document.getElementById('btn-vd-cancel');
const vdProgressArea   = document.getElementById('vd-progress-area');
const vdProgressText   = document.getElementById('vd-progress-text');
const vdProgressTime   = document.getElementById('vd-progress-time');
const vdProgressBar    = document.getElementById('vd-progress-bar-fill');
const vdModeSelect     = document.getElementById('vd-mode');
const vdFpsSlider      = document.getElementById('vd-fps');
const vdFpsVal         = document.getElementById('vd-fps-val');
const vdHwAccel        = document.getElementById('vd-hwaccel');
const vdOutDir         = document.getElementById('vd-out-dir');
const btnVdBrowseOut   = document.getElementById('btn-vd-browse-out');

// FPS slider live label
vdFpsSlider.addEventListener('input', () => {
    vdFpsVal.textContent = vdFpsSlider.value;
});

// Mode switch: show/hide fps slider for frames→video
vdModeSelect.addEventListener('change', () => {
    const fpsGroup = document.getElementById('vd-fps-group');
    fpsGroup.style.display = 'block'; // Always shown – used for both modes
});

function buildVdQueueItem(item, idx) {
    const div = document.createElement('div');
    div.className = 'queue-item';
    let statusHtml = '';
    if (item.status === 'processing') {
        statusHtml = `<div class="item-status status-processing">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Processing...
        </div>`;
    } else if (item.status === 'completed') {
        statusHtml = `<div class="item-status status-completed">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Done
        </div>`;
    } else if (item.status === 'failed') {
        statusHtml = `<div class="item-status status-failed" title="${item.error || 'Failed'}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Failed
        </div>`;
    } else {
        statusHtml = `<div class="item-status status-pending">Pending</div>`;
    }
    const removeBtn = !isVdProcessing
        ? `<button class="remove-btn" onclick="removeVdItem(${idx})" title="Remove">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
           </button>` : '';
    div.innerHTML = `
        <div class="item-info">
            <div class="item-name" title="${item.path}">${item.name}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            ${statusHtml}
            ${removeBtn}
        </div>`;
    return div;
}

window.removeVdItem = idx => {
    if (!isVdProcessing) { vdQueue.splice(idx, 1); renderVdQueue(); }
};

function renderVdQueue() {
    vdQueueCount.textContent = vdQueue.length;
    if (vdQueue.length === 0) {
        vdEmptyState.style.display = 'flex';
        vdQueueList.style.display = 'none';
        btnVdClear.style.display = 'none';
        if (!isVdProcessing) btnVdStart.disabled = true;
        vdQueueList.innerHTML = '';
        return;
    }
    vdEmptyState.style.display = 'none';
    vdQueueList.style.display = 'flex';
    btnVdClear.style.display = 'inline-flex';
    if (!isVdProcessing) btnVdStart.disabled = false;
    vdQueueList.innerHTML = '';
    vdQueue.forEach((item, i) => vdQueueList.appendChild(buildVdQueueItem(item, i)));
}

btnVdClear.addEventListener('click', () => {
    if (!isVdProcessing) { vdQueue = []; renderVdQueue(); }
});

async function addVdItems(paths) {
    if (!paths || !paths.length) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(), status: 'pending', error: ''
    }));
    vdQueue = [...vdQueue, ...newItems];
    renderVdQueue();
}

btnVdAddFiles.addEventListener('click', async () => {
    // For video-to-frames: pick video files; for frames-to-video: pick image files
    const mode = vdModeSelect.value;
    const res = await apiCall('/api/select-files', {
        file_types: mode === 'video_to_frames'
            ? [['Video files', '*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.ts']]
            : [['Image files', '*.png *.jpg *.jpeg *.bmp *.tiff *.webp']]
    });
    if (res && res.files && res.files.length) addVdItems(res.files);
});

btnVdAddFolder.addEventListener('click', async () => {
    const mode = vdModeSelect.value;
    const res = await apiCall('/api/select-folder', {
        file_types: mode === 'video_to_frames'
            ? [['Video files', '*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.ts']]
            : [['Image files', '*.png *.jpg *.jpeg *.bmp *.tiff *.webp']]
    });
    if (res && res.files && res.files.length) addVdItems(res.files);
});

btnVdBrowseOut.addEventListener('click', async () => {
    const res = await apiCall('/api/select-out-folder');
    if (res && res.folder) vdOutDir.value = res.folder;
});

let vdStartTime = null;

btnVdStart.addEventListener('click', async () => {
    if (vdQueue.length === 0 || isVdProcessing) return;
    isVdProcessing = true;
    vdStartTime = Date.now();
    btnVdStart.style.display = 'none';
    btnVdCancel.style.display = 'inline-flex';
    btnVdAddFiles.disabled = true;
    btnVdAddFolder.disabled = true;
    vdProgressArea.style.display = 'block';
    vdProgressBar.style.width = '0%';
    vdProgressText.textContent = 'Starting...';

    const settings = {
        mode:     vdModeSelect.value,
        fps:      parseInt(vdFpsSlider.value),
        hwaccel:  vdHwAccel.checked,
        out_dir:  vdOutDir.value || '',
        files:    vdQueue.map(f => f.path)
    };

    await apiCall('/api/process', { tool: 'video', settings });
    pollVdStatus();
});

btnVdCancel.addEventListener('click', async () => {
    await apiCall('/api/cancel', { tool: 'video' });
    btnVdCancel.disabled = true;
    btnVdCancel.textContent = 'Cancelling...';
});

function pollVdStatus() {
    vdStatusInterval = setInterval(async () => {
        const st = await apiGet('/api/status?tool=video');
        if (!st) return;

        // Update queue item statuses
        if (st.items) {
            st.items.forEach((it, i) => {
                if (vdQueue[i]) {
                    vdQueue[i].status = it.status;
                    vdQueue[i].error  = it.error || '';
                }
            });
            renderVdQueue();
        }

        // Progress bar
        const pct = st.total > 0 ? Math.round((st.done / st.total) * 100) : 0;
        vdProgressBar.style.width = pct + '%';
        const elapsed = ((Date.now() - vdStartTime) / 1000).toFixed(1);
        vdProgressTime.textContent = elapsed + 's';
        vdProgressText.textContent = `${st.status_text || 'Processing...'} (${st.done || 0}/${st.total || 0}) (${pct}%)`;

        if (st.state === 'idle') {
            clearInterval(vdStatusInterval);
            isVdProcessing = false;
            vdProgressBar.style.width = '100%';
            vdProgressText.textContent = st.cancelled ? 'Cancelled.' : `Done! ${st.done} item(s) processed.`;
            btnVdStart.style.display = 'inline-flex';
            btnVdCancel.style.display = 'none';
            btnVdCancel.disabled = false;
            btnVdCancel.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Cancel`;
            btnVdAddFiles.disabled = false;
            btnVdAddFolder.disabled = false;
            renderVdQueue();
        }
    }, 1000);
}

// Re-wire DOMContentLoaded to also call renderVdQueue
document.addEventListener('DOMContentLoaded', () => {
    renderVdQueue();
});

// Fullscreen support on keydown F11
document.addEventListener('keydown', (e) => {
    if (e.key === 'F11') {
        e.preventDefault();
        if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_fullscreen) {
            window.pywebview.api.toggle_fullscreen();
        }
    }
});


