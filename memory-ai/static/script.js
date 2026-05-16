// --- State Management ---
const state = {
    token: localStorage.getItem('memory_ai_token'),
    activeSection: 'chat',
    isRecording: false
};

// --- DOM Elements ---
const pages = {
    auth: document.getElementById('auth-page'),
    dashboard: document.getElementById('dashboard-page')
};

const sections = {
    chat: document.getElementById('chat-section'),
    legal: document.getElementById('legal-section'),
    memory: document.getElementById('memory-section')
};

const chatElements = {
    messages: document.getElementById('chat-messages'),
    input: document.getElementById('user-input'),
    sendBtn: document.getElementById('send-btn'),
    micBtn: document.getElementById('mic-btn'),
    voiceIndicator: document.getElementById('voice-indicator')
};

const debugElements = {
    retrieved: document.getElementById('debug-retrieved'),
    context: document.getElementById('debug-context'),
    decision: document.getElementById('debug-decision'),
    conflict: document.getElementById('debug-conflict'),
    conflictWrapper: document.getElementById('conflict-wrapper'),
    stored: document.getElementById('debug-stored')
};

const legalElements = {
    text: document.getElementById('legal-text'),
    file: document.getElementById('legal-file'),
    fileName: document.getElementById('file-name'),
    analyzeBtn: document.getElementById('analyze-btn'),
    results: document.getElementById('legal-results'),
    loader: document.getElementById('legal-loader'),
    summary: document.getElementById('legal-summary-text'),
    risks: document.getElementById('legal-risks-list'),
    clauses: document.getElementById('legal-clauses-container')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupNavigation();
    setupEventListeners();
});

// --- Auth Flow ---
function checkAuth() {
    if (state.token === 'authenticated') {
        showPage('dashboard');
        initDashboard();
    } else {
        showPage('auth');
    }
}

async function handleLogin() {
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('auth-error');
    
    // In a real app, this would be a backend call. 
    // Spec says "Validate (frontend)" and use APP_PASSWORD from .env logic
    // We'll simulate a simple check. Usually the USER would set APP_PASSWORD=admin123
    if (password === 'admin123') {
        localStorage.setItem('memory_ai_token', 'authenticated');
        state.token = 'authenticated';
        showPage('dashboard');
        initDashboard();
        showToast('Access Granted. Neural link established.');
    } else {
        errorMsg.style.display = 'block';
        document.getElementById('password').value = '';
    }
}

function handleLogout() {
    localStorage.removeItem('memory_ai_token');
    location.reload();
}

function showPage(pageId) {
    Object.values(pages).forEach(p => p.classList.remove('active'));
    pages[pageId].classList.add('active');
}

// --- Dashboard Logic ---
async function initDashboard() {
    // Check if previous memory exists
    try {
        const res = await fetch('/api/check-memory');
        const data = await res.json();
        if (data.has_memory) {
            document.getElementById('session-modal').style.display = 'flex';
        }
    } catch (e) {
        console.error("Failed to check memory", e);
    }
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-links li');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            switchSection(link.dataset.section);
        });
    });
}

// --- Chat Flow ---
async function sendMessage(isContinue = false) {
    const message = isContinue ? "Start session with recap" : chatElements.input.value.trim();
    if (!message) return;

    if (!isContinue) {
        addChatMessage(message, 'user');
        chatElements.input.value = '';
        chatElements.input.style.height = 'auto';
    }

    setChatLoading(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                continue: isContinue
            })
        });

        const data = await response.json();
        
        if (data.reply) {
            addChatMessage(data.reply, 'bot');
            updateDebugPanel(data.debug, data.conflict);
            
            // If it was a conflict, show a toast
            if (data.conflict) {
                showToast('Memory Conflict Resolved', 'warning');
            }
        } else if (data.error) {
            showToast(data.error, 'error');
        }
    } catch (e) {
        showToast('Connection Refused. Is the backend running?', 'error');
    } finally {
        setChatLoading(false);
    }
}

function addChatMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${sender}`;
    msgDiv.innerHTML = `<div class="msg-content">${text}</div>`;
    chatElements.messages.appendChild(msgDiv);
    chatElements.messages.scrollTop = chatElements.messages.scrollHeight;
}

function updateDebugPanel(debug, conflict) {
    if (!debug) return;

    const fill = (el, val) => {
        if (val && val !== "None" && val !== "") {
            el.textContent = typeof val === 'object' ? JSON.stringify(val, null, 2) : val;
            el.classList.remove('empty');
        } else {
            el.textContent = el.id === 'debug-decision' ? 'Processing...' : 'None';
            el.classList.add('empty');
        }
    };

    fill(debugElements.retrieved, debug.memory_retrieved);
    fill(debugElements.context, debug.context_used);
    fill(debugElements.decision, debug.decision);
    fill(debugElements.stored, debug.stored_memory);

    if (conflict) {
        debugElements.conflictWrapper.style.display = 'block';
        debugElements.conflict.textContent = conflict;
    } else {
        debugElements.conflictWrapper.style.display = 'none';
    }
}

function setChatLoading(isLoading) {
    chatElements.sendBtn.disabled = isLoading;
    chatElements.input.disabled = isLoading;
    if (isLoading) {
        chatElements.sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    } else {
        chatElements.sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        chatElements.input.focus();
    }
}

// --- Legal Analyzer ---
async function analyzeLegal() {
    const text = legalElements.text.value.trim();
    const file = legalElements.file.files[0];

    if (!text && !file) {
        showToast('Please provide text or upload a PDF', 'error');
        return;
    }

    legalElements.loader.style.display = 'flex';
    legalElements.results.style.display = 'none';

    try {
        let response;
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            response = await fetch('/api/analyze-legal', {
                method: 'POST',
                body: formData
            });
        } else {
            response = await fetch('/api/analyze-legal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
        }

        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            displayLegalResults(data);
        }
    } catch (e) {
        showToast('Analysis failed', 'error');
    } finally {
        legalElements.loader.style.display = 'none';
    }
}

function displayLegalResults(data) {
    legalElements.summary.textContent = data.summary;
    
    legalElements.risks.innerHTML = data.risks.map(r => `<li>${r}</li>`).join('');
    
    legalElements.clauses.innerHTML = data.clauses.map(c => `
        <div class="clause-item">
            <h4>${c.title}</h4>
            <p>${c.content}</p>
        </div>
    `).join('');
    
    legalElements.results.style.display = 'block';
}

// --- Voice Flow (Web Speech API) ---
function toggleVoice() {
    if (!('webkitSpeechRecognition' in window)) {
        showToast('Speech recognition not supported in this browser.', 'error');
        return;
    }

    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

let recognition;
function startRecording() {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        state.isRecording = true;
        chatElements.micBtn.classList.add('active');
        chatElements.voiceIndicator.classList.add('active');
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatElements.input.value = transcript;
        autoResizeInput();
    };

    recognition.onerror = () => stopRecording();
    recognition.onend = () => stopRecording();

    recognition.start();
}

function stopRecording() {
    state.isRecording = false;
    chatElements.micBtn.classList.remove('active');
    chatElements.voiceIndicator.classList.remove('active');
    if (recognition) recognition.stop();
}

// --- Utils & Event Listeners ---
function setupEventListeners() {
    const addListener = (id, event, callback) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, callback);
    };

    // Auth
    addListener('login-btn', 'click', handleLogin);
    addListener('password', 'keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
    addListener('logout-btn', 'click', handleLogout);

    // Chat
    if (chatElements.sendBtn) chatElements.sendBtn.addEventListener('click', () => sendMessage());
    if (chatElements.input) {
        chatElements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        chatElements.input.addEventListener('input', autoResizeInput);
    }

    // Voice
    if (chatElements.micBtn) chatElements.micBtn.addEventListener('click', toggleVoice);

    // Legal
    addListener('analyze-btn', 'click', analyzeLegal);
    const fileEl = document.getElementById('legal-file');
    if (fileEl) {
        fileEl.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                const nameEl = document.getElementById('file-name');
                if (nameEl) nameEl.textContent = e.target.files[0].name;
            }
        });
    }

    // Modal
    addListener('session-yes', 'click', (e) => {
        e.preventDefault();
        const modal = document.getElementById('session-modal');
        if (modal) modal.style.display = 'none';
        sendMessage(true);
    });
    addListener('session-no', 'click', (e) => {
        e.preventDefault();
        const modal = document.getElementById('session-modal');
        if (modal) modal.style.display = 'none';
        showToast('Started fresh session.');
    });
}

function autoResizeInput() {
    chatElements.input.style.height = 'auto';
    chatElements.input.style.height = chatElements.input.scrollHeight + 'px';
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = message;
    
    if (type === 'error') toast.style.borderLeftColor = 'var(--error)';
    if (type === 'warning') toast.style.borderLeftColor = '#e3b341';

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// --- Memory Manager Functions ---
let memoryNetwork = null;

async function fetchMemories() {
    try {
        const response = await fetch('/api/memories');
        const data = await response.json();
        renderMemoryList(data);
        renderMemoryGraph(data);
        updateMemoryStats(data);
    } catch (e) {
        showToast('Failed to load memories', 'error');
    }
}

function updateMemoryStats(data) {
    const total = (data.facts?.length || 0) + (data.preferences?.length || 0) + (data.goals?.length || 0);
    document.getElementById('stat-total').textContent = total;
    
    let totalImp = 0;
    let count = 0;
    Object.values(data).forEach(cat => {
        cat.forEach(m => {
            totalImp += m.importance || 0.5;
            count++;
        });
    });
    
    const avg = count > 0 ? (totalImp / count).toFixed(2) : "0.0";
    document.getElementById('stat-priority').textContent = avg;
}

function renderMemoryList(data) {
    const list = document.getElementById('memory-list');
    list.innerHTML = '';
    
    const categories = ['facts', 'preferences', 'goals'];
    categories.forEach(cat => {
        (data[cat] || []).forEach(m => {
            const card = document.createElement('div');
            card.className = 'mem-item-card';
            const badgeClass = cat === 'facts' ? 'badge-fact' : (cat === 'preferences' ? 'badge-pref' : 'badge-goal');
            const impPercent = (m.importance || 0.5) * 100;
            
            card.innerHTML = `
                <span class="mem-badge ${badgeClass}">${cat.slice(0, -1)}</span>
                <div class="mem-content">${m.content}</div>
                <div class="importance-bar"><div class="importance-fill" style="width: ${impPercent}%"></div></div>
                <div class="mem-meta">
                    <span><i class="far fa-clock"></i> ${new Date(m.timestamp).toLocaleDateString()}</span>
                    <span><i class="fas fa-eye"></i> ${m.access_count || 0}</span>
                </div>
                <div class="mem-actions">
                    <button class="btn-icon" onclick="deleteMemory('${cat}', '${m.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                </div>
            `;
            list.appendChild(card);
        });
    });
}

function renderMemoryGraph(data) {
    const container = document.getElementById('memory-graph');
    const nodes = [];
    const edges = [];
    
    // Core node
    nodes.push({ id: 'user', label: 'User Context', color: '#58a6ff', font: { color: 'white' } });
    
    const categories = ['facts', 'preferences', 'goals'];
    categories.forEach(cat => {
        const catId = 'cat-' + cat;
        nodes.push({ id: catId, label: cat.toUpperCase(), color: '#151c31', font: { color: 'white' } });
        edges.push({ from: 'user', to: catId });
        
        (data[cat] || []).forEach((m, idx) => {
            const mId = 'm-' + cat + '-' + idx;
            nodes.push({ 
                id: mId, 
                label: m.content.length > 20 ? m.content.slice(0, 20) + '...' : m.content,
                title: m.content,
                color: '#0a0f1e',
                font: { size: 10, color: '#8b949e' }
            });
            edges.push({ from: catId, to: mId });
        });
    });

    const graphData = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    const options = {
        physics: { enabled: true, stabilization: true },
        nodes: { shape: 'dot', size: 16 },
        edges: { color: '#30363d', arrows: { to: { enabled: false } } }
    };
    
    if (memoryNetwork) memoryNetwork.destroy();
    memoryNetwork = new vis.Network(container, graphData, options);
}

async function deleteMemory(cat, id) {
    if (!confirm('Forget this memory forever?')) return;
    try {
        const response = await fetch(`/api/memories/${cat}/${id}`, { method: 'DELETE' });
        const res = await response.json();
        if (res.success) {
            showToast('Memory forgotten.');
            fetchMemories();
        }
    } catch (e) {
        showToast('Failed to delete memory', 'error');
    }
}

async function optimizeMemory() {
    const btn = document.getElementById('optimize-memory-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Optimizing...';
    
    try {
        const response = await fetch('/api/memories/optimize', { method: 'POST' });
        const res = await response.json();
        if (res.success) {
            showToast('Memory optimized & consolidated!');
            fetchMemories();
        }
    } catch (e) {
        showToast('Optimization failed', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> Optimize Brain';
    }
}

// Global Nav setup update
function switchSection(sectionId) {
    if (sectionId === 'memory') fetchMemories();
    
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId + '-section').classList.add('active');
    
    document.querySelectorAll('.nav-links li').forEach(li => {
        li.classList.toggle('active', li.dataset.section === sectionId);
    });
}

// Add shortcut listeners
document.addEventListener('keydown', (e) => {
    // Ctrl + K to clear
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        chatElements.messages.innerHTML = '';
        showToast('Chat cleared');
    }
    // Ctrl + M for memory manager
    if (e.ctrlKey && e.key === 'm') {
        e.preventDefault();
        switchSection('memory');
    }
});

// Final Init hooks
document.getElementById('optimize-memory-btn').addEventListener('click', optimizeMemory);
// Navigation listeners are now handled in setupNavigation()
