// =============================================================
// MagickScale - Full App Logic
// Covers: Downscaler, AI Upscaler, Logo Remover tabs
// =============================================================

// =============================================
// GLOBAL STATE
// =============================================
let fileQueue = [];    // Downscaler queue
let upQueue   = [];    // Upscaler queue
let lrQueue   = [];    // Logo-remover queue

let isProcessing    = false;
let isUpProcessing  = false;
let isLrProcessing  = false;

let statusInterval   = null;
let upStatusInterval = null;
let lrStatusInterval = null;

// Store loaded model info for credit display
let loadedModels = [];

// Active Gemini method selection
let geminiMethod = 'blur';

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
        statusHtml = `<div class="item-status status-processing">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg> Processing...
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
        <div class="item-info">
            <div class="item-name" title="${file.path}">${file.name}</div>
            ${metaStr ? `<div class="item-meta">${metaStr}</div>` : ''}
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            ${statusHtml}
            ${removeBtn}
        </div>`;
    return item;
}

// =============================================
// TAB NAVIGATION
// =============================================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
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
        if (!isProcessing) btnStart.disabled = true;
        queueList.innerHTML = '';
        return;
    }
    emptyState.style.display = 'none';
    queueList.style.display = 'flex';
    btnClearQueue.style.display = 'inline-flex';
    if (!isProcessing) btnStart.disabled = false;
    queueList.innerHTML = '';
    fileQueue.forEach((f, i) => queueList.appendChild(buildQueueItem(f, i, 'removeItem', isProcessing)));
}

window.removeItem = idx => { if (!isProcessing) { fileQueue.splice(idx, 1); renderQueue(); } };
btnClearQueue.addEventListener('click', () => { if (!isProcessing) { fileQueue = []; renderQueue(); } });

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
    if (fileQueue.length === 0 || isProcessing) return;
    const settings = {
        mode:     document.getElementById('setting-mode').value,
        filter:   document.getElementById('setting-filter').value,
        format:   settingFormat.value,
        quality:  parseInt(settingQuality.value),
        out_dir:  inputOutDir.value,
        use_gpu:  document.getElementById('setting-gpu').checked,
        custom_width: parseInt(document.getElementById('setting-custom-width').value) || 1920,
        custom_height: parseInt(document.getElementById('setting-custom-height').value) || 1080
    };

    const res = await apiCall('/api/start', { files: fileQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isProcessing = true;
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
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(async () => {
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
        progressBarFill.style.width = total > 0 ? ((done / total) * 100) + '%' : '0%';
        progressText.textContent  = `Processing: ${done} / ${total}`;
        progressSpeed.textContent = data.speed ? `${data.speed} img/s` : '';
        progressTime.textContent  = `Elapsed: ${data.time_elapsed}s`;
        if ((data.total_space_saved || 0) > 0) {
            spaceSavedBadge.style.display = 'inline-flex';
            spaceSavedVal.textContent = formatSize(data.total_space_saved);
        }
        if (!data.processing) { clearInterval(statusInterval); finishDownscaling(); }
    }, 500);
}

function finishDownscaling() {
    isProcessing = false;
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
        out_dir: upOutDir.value
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
                if (upQueue[i]) { upQueue[i].status = s.status; upQueue[i].error = s.error || ''; }
            });
            upQueueList.innerHTML = '';
            upQueue.forEach((f, i) => upQueueList.appendChild(buildQueueItem(f, i, 'removeUpItem', true)));
        }
        const total = upQueue.length, done = data.total_processed || 0;
        upProgressBar.style.width = total > 0 ? ((done / total) * 100) + '%' : '0%';
        upProgressText.textContent = `Upscaling: ${done} / ${total}`;
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
const btnGeminiApply = document.getElementById('btn-gemini-apply');
const gemSizeSlider  = document.getElementById('gem-size');
const gemSizeVal     = document.getElementById('gem-size-val');

// Gemini size slider
gemSizeSlider.addEventListener('input', () => { gemSizeVal.textContent = gemSizeSlider.value + '%'; });

// Gemini method selection
document.querySelectorAll('.gemini-method-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.gemini-method-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        geminiMethod = btn.dataset.method;
    });
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
        btnGeminiApply.disabled = true;
        return;
    }
    lrEmptyState.style.display = 'none';
    lrQueueList.style.display = 'flex';
    btnLrClear.style.display = 'inline-flex';
    if (!isLrProcessing) {
        btnLrStart.disabled = false;
        btnGeminiApply.disabled = false;
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
        btnGeminiApply.style.display = 'none';
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
    await startLogoRemoval({
        gemini_mode: false,
        position:    document.getElementById('lr-position').value,
        size_pct:    parseInt(lrSizeSlider.value),
        method:      document.getElementById('lr-method').value,
        out_dir:     lrOutDir.value
    });
});

btnGeminiApply.addEventListener('click', async () => {
    if (lrQueue.length === 0 || isLrProcessing) return;
    await startLogoRemoval({
        gemini_mode: true,
        position:    'bottom_right',
        size_pct:    parseInt(gemSizeSlider.value),
        method:      geminiMethod,
        out_dir:     lrOutDir.value
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
        lrProgressBar.style.width = total > 0 ? ((done / total) * 100) + '%' : '0%';
        lrProgressText.textContent = `Processing: ${done} / ${total}`;
        lrProgressTime.textContent = `Elapsed: ${data.time_elapsed}s`;
        if (!data.processing) { clearInterval(lrStatusInterval); finishLrProcessing(); }
    }, 500);
}

function finishLrProcessing() {
    isLrProcessing = false;
    btnLrStart.style.display = 'inline-flex';
    btnGeminiApply.style.display = 'inline-flex';
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
let isSlProcessing = false;
let slStatusInterval = null;

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
        slProgressBar.style.width = total > 0 ? ((done / total) * 100) + '%' : '0%';
        slProgressText.textContent = `Slicing: ${done} / ${total}`;
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
let isMeProcessing = false;
let meStatusInterval = null;

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
    meStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/merger/status');
        if (!data) return;
        if (data.queue && data.queue[0]) {
            meProgressText.textContent = `Status: ${data.queue[0].status === 'completed' ? 'Success!' : data.queue[0].status === 'failed' ? 'Failed: ' + data.queue[0].error : 'Merging...'}`;
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
let isOlProcessing = false;
let olStatusInterval = null;

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
    olStatusInterval = setInterval(async () => {
        const data = await apiGet('/api/overlay/status');
        if (!data) return;
        if (data.queue && data.queue[0]) {
            olProgressText.textContent = `Status: ${data.queue[0].status === 'completed' ? 'Success!' : data.queue[0].status === 'failed' ? 'Failed: ' + data.queue[0].error : 'Compositing...'}`;
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
let converterQueue = [];
let isCoProcessing = false;
let coStatusInterval = null;

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
    coQueueCount.textContent = converterQueue.length;
    if (converterQueue.length === 0) {
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
    converterQueue.forEach((f, i) => coQueueList.appendChild(buildQueueItem(f, i, 'removeCoItem', isCoProcessing)));
}

window.removeCoItem = idx => { if (!isCoProcessing) { converterQueue.splice(idx, 1); renderCoQueue(); } };
btnCoClear.addEventListener('click', () => { if (!isCoProcessing) { converterQueue = []; renderCoQueue(); } });

async function addCoFiles(paths) {
    if (!paths || paths.length === 0) return;
    const newItems = paths.map(p => ({
        path: p, name: p.split(/[\\\/]/).pop(),
        status: 'pending', metadata: null, size_saved: 0, error: ''
    }));
    converterQueue = [...converterQueue, ...newItems];
    renderCoQueue();
    const meta = await apiCall('/api/get-metadata', { files: paths });
    if (meta && meta.metadata) {
        converterQueue.forEach(item => {
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
    if (converterQueue.length === 0 || isCoProcessing) return;
    const settings = {
        format: coFormatSelect.value,
        quality: parseInt(coQualitySlider.value),
        out_dir: coOutDir.value
    };
    const res = await apiCall('/api/converter/start', { files: converterQueue.map(f => f.path), settings });
    if (res && res.status === 'started') {
        isCoProcessing = true;
        btnCoStart.style.display = 'none';
        btnCoCancel.style.display = 'inline-flex';
        coProgressArea.style.display = 'block';
        btnCoAddFiles.disabled = true;
        btnCoClear.style.display = 'none';
        converterQueue.forEach(f => { f.status = 'pending'; f.error = ''; });
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
                if (converterQueue[i]) {
                    converterQueue[i].status = s.status;
                    converterQueue[i].size_saved = s.size_saved || 0;
                    converterQueue[i].error = s.error || '';
                }
            });
            renderCoQueue();
        }
        const total = converterQueue.length, done = data.total_processed || 0;
        coProgressBar.style.width = total > 0 ? ((done / total) * 100) + '%' : '0%';
        coProgressText.textContent = `Converting: ${done} / ${total}`;
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

// =============================================
// INIT — runs when DOM is ready
// =============================================
document.addEventListener('DOMContentLoaded', () => {
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

    // Upscaler init (runs in background)
    checkEngineStatus();
    detectGpu();
    loadModels();
});

