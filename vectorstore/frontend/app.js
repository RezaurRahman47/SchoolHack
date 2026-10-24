/**
 * Chemie RAG — Frontend Application
 * Interactive chemistry learning platform with RAG-powered features.
 */

// ═══════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════

const state = {
    currentView: 'chat',
    isLoading: false,
    quizAnswered: {},
    statementsAnswered: {},
    chatHistory: [],
};

// ═══════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChatInput();
    checkStatus();
    loadTopics();
});

async function checkStatus() {
    const indicator = document.getElementById('status-indicator');
    const statusText = indicator.querySelector('.status-text');
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.ready) {
            indicator.classList.add('ready');
            const stats = data.stats;
            statusText.textContent = `${stats.total_chunks} Chunks bereit`;
        } else {
            indicator.classList.add('error');
            statusText.textContent = 'Nicht indexiert — bitte ingest.py ausführen';
        }
    } catch (e) {
        indicator.classList.add('error');
        statusText.textContent = 'Server nicht erreichbar';
    }
}

async function loadTopics() {
    try {
        const res = await fetch('/api/topics');
        const data = await res.json();
        const list = document.getElementById('topic-list');
        if (data.topics && data.topics.length > 0) {
            list.innerHTML = data.topics.map(t =>
                `<button class="topic-chip" onclick="exploreTopic('${escapeHtml(t)}')">${escapeHtml(t)}</button>`
            ).join('');
        }
    } catch (e) {
        // Topics not available yet
    }
}

// ═══════════════════════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════════════════════

function initNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

function switchView(viewName) {
    // Update nav
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.nav-btn[data-view="${viewName}"]`).classList.add('active');

    // Update views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');

    state.currentView = viewName;
}

// ═══════════════════════════════════════════════════════════
//  CHAT
// ═══════════════════════════════════════════════════════════

function initChatInput() {
    const input = document.getElementById('chat-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChat();
        }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
}

function askSuggestion(text) {
    document.getElementById('chat-input').value = text;
    sendChat();
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question || state.isLoading) return;

    state.isLoading = true;
    input.value = '';
    input.style.height = 'auto';

    // Remove welcome message
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user message
    addChatMessage(question, 'user');

    // Show thinking indicator
    const thinkingId = addThinkingMessage();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const answer = typeof data.answer === 'string' ? data.answer.trim() : '';

        // Add bot response
        addChatMessage(answer || 'Keine Antwort erhalten.', 'bot', data.sources, data.images);

    } catch (e) {
        addChatMessage('Der Chemie-Tutor ist gerade nicht erreichbar. Bitte versuche es in einem Moment noch einmal.', 'bot');
        showToast('Fehler bei der Verbindung zum Server', 'error');
    } finally {
        removeThinkingMessage(thinkingId);
        state.isLoading = false;
    }
}

function addChatMessage(text, sender, sources = [], images = []) {
    const messages = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;

    const avatar = sender === 'bot' ? '🧪' : '👤';
    const formattedText = formatMarkdown(text);

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const tags = sources.map(s =>
            `<span class="source-tag">📄 Seite ${escapeHtml(String(s.page ?? ''))}${s.chapter ? ' — ' + escapeHtml(s.chapter) : ''}</span>`
        ).join('');
        sourcesHtml = `<div class="msg-sources">${tags}</div>`;
    }

    // Render relevant images from the textbook
    let imagesHtml = '';
    if (images && images.length > 0) {
        const imgCards = images.map((img, i) => {
            const captionRaw = img.caption
                ? String(img.caption)
                : `Abbildung aus dem Schulbuch (Seite ${img.page})`;
            const captionHtml = escapeHtml(captionRaw);
            const captionAttr = captionHtml.replace(/"/g, '&quot;');
            const captionJs = escapeAttr(captionRaw);
            const urlHtml = escapeHtml(img.url || '').replace(/"/g, '&quot;');
            const urlJs = escapeAttr(img.url || '');
            return `
                <div class="msg-image-card" onclick="openImageLightbox('${urlJs}', '${captionJs}')"
                     title="Klicken zum Vergrößern">
                    <img src="${urlHtml}" alt="${captionAttr}" loading="lazy"
                         onerror="this.closest('.msg-image-card').style.display='none'" />
                    <div class="msg-image-caption">
                        <span>📷 ${captionHtml}</span>
                        <span class="img-relevance">S. ${escapeHtml(String(img.page || ''))}</span>
                    </div>
                </div>`;
        }).join('');
        imagesHtml = `<div class="msg-images">
            <div class="msg-images-label">📚 Relevante Abbildungen aus dem Schulbuch</div>
            <div class="msg-images-grid">${imgCards}</div>
        </div>`;
    }

    msg.innerHTML = `
        <div class="msg-avatar">${avatar}</div>
        <div class="msg-content">${formattedText}${imagesHtml}${sourcesHtml}</div>
    `;

    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
}

function openImageLightbox(url, caption) {
    // Create or reuse lightbox overlay
    let lb = document.getElementById('img-lightbox');
    if (!lb) {
        lb = document.createElement('div');
        lb.id = 'img-lightbox';
        lb.className = 'lightbox-overlay';
        lb.innerHTML = `
            <div class="lightbox-backdrop" onclick="closeLightbox()"></div>
            <div class="lightbox-inner">
                <button class="lightbox-close" onclick="closeLightbox()">✕</button>
                <img id="lightbox-img" src="" alt="" />
                <div id="lightbox-caption" class="lightbox-caption"></div>
            </div>`;
        document.body.appendChild(lb);
    }
    document.getElementById('lightbox-img').src = url;
    document.getElementById('lightbox-caption').textContent = caption;
    lb.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lb = document.getElementById('img-lightbox');
    if (lb) lb.classList.remove('active');
    document.body.style.overflow = '';
}

function addThinkingMessage() {
    const messages = document.getElementById('chat-messages');
    const id = 'thinking-' + Date.now();
    const msg = document.createElement('div');
    msg.className = 'chat-msg bot';
    msg.id = id;
    msg.innerHTML = `
        <div class="msg-avatar">🧪</div>
        <div class="msg-content">
            <div class="thinking-dots">
                <span style="animation: blink 1.4s infinite 0s">●</span>
                <span style="animation: blink 1.4s infinite 0.2s">●</span>
                <span style="animation: blink 1.4s infinite 0.4s">●</span>
                <span style="color: var(--text-muted); margin-left: 8px; font-size: 0.82rem">Suche im Schulbuch...</span>
            </div>
        </div>
    `;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
    return id;
}

function removeThinkingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ═══════════════════════════════════════════════════════════
//  QUIZ
// ═══════════════════════════════════════════════════════════

async function generateQuiz() {
    const topic = document.getElementById('quiz-topic').value.trim();
    const count = parseInt(document.getElementById('quiz-count').value) || 5;

    showLoading('Quiz wird generiert...');
    state.quizAnswered = {};

    try {
        const res = await fetch('/api/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic || null, num_questions: count }),
        });
        const data = await res.json();
        hideLoading();

        if (data.error && (!data.questions || data.questions.length === 0)) {
            showToast(data.error, 'error');
            return;
        }

        renderQuiz(data);
        showToast(`Quiz "${data.title}" erstellt!`, 'success');

    } catch (e) {
        hideLoading();
        showToast('Fehler beim Erstellen des Quiz', 'error');
    }
}

function renderQuiz(quiz) {
    const area = document.getElementById('quiz-area');

    let html = '';
    quiz.questions.forEach((q, idx) => {
        const optionsHtml = q.options.map((opt, optIdx) => {
            const letter = String.fromCharCode(65 + optIdx);
            // Remove leading letter prefix if present (e.g., "A) ")
            const cleanOpt = opt.replace(/^[A-D]\)\s*/, '');
            return `
                <div class="quiz-option" id="quiz-opt-${idx}-${letter}"
                     onclick="selectQuizAnswer(${idx}, '${letter}', '${escapeAttr(q.correct_answer)}')">
                    <span class="option-letter">${letter}</span>
                    <span>${escapeHtml(cleanOpt)}</span>
                </div>
            `;
        }).join('');

        html += `
            <div class="quiz-card" id="quiz-card-${idx}">
                <div class="quiz-number">${idx + 1}</div>
                <div class="quiz-question">${escapeHtml(q.question)}</div>
                <div class="quiz-options">${optionsHtml}</div>
                <div class="quiz-explanation" id="quiz-exp-${idx}">
                    <strong>Erklärung:</strong> ${escapeHtml(q.explanation || '')}
                    ${q.page_reference ? `<br><em>📄 Seite ${q.page_reference}</em>` : ''}
                </div>
            </div>
        `;
    });

    html += `<div class="quiz-score" id="quiz-score-area"></div>`;
    area.innerHTML = html;
}

function selectQuizAnswer(questionIdx, selected, correct) {
    if (state.quizAnswered[questionIdx]) return;
    state.quizAnswered[questionIdx] = selected;

    const isCorrect = selected.toUpperCase() === correct.toUpperCase();

    // Mark selected option
    const selectedEl = document.getElementById(`quiz-opt-${questionIdx}-${selected}`);
    selectedEl.classList.add('selected', isCorrect ? 'correct' : 'incorrect');

    // If wrong, show correct answer
    if (!isCorrect) {
        const correctEl = document.getElementById(`quiz-opt-${questionIdx}-${correct.toUpperCase()}`);
        if (correctEl) correctEl.classList.add('show-correct');
    }

    // Disable all options
    const card = document.getElementById(`quiz-card-${questionIdx}`);
    card.querySelectorAll('.quiz-option').forEach(opt => opt.classList.add('disabled'));

    // Show explanation
    document.getElementById(`quiz-exp-${questionIdx}`).classList.add('visible');

    // Check if all answered
    const totalQuestions = document.querySelectorAll('.quiz-card').length;
    if (Object.keys(state.quizAnswered).length === totalQuestions) {
        showQuizScore(totalQuestions);
    }
}

function showQuizScore(total) {
    const correct = Object.entries(state.quizAnswered).filter(([idx, sel]) => {
        const correctEl = document.querySelector(`#quiz-card-${idx} .quiz-option.show-correct, #quiz-card-${idx} .quiz-option.selected.correct`);
        return document.querySelector(`#quiz-card-${idx} .quiz-option.selected.correct`) !== null;
    }).length;

    const scoreArea = document.getElementById('quiz-score-area');
    const percentage = Math.round((correct / total) * 100);
    let emoji = '🎉';
    if (percentage < 50) emoji = '📚';
    else if (percentage < 80) emoji = '👍';

    scoreArea.innerHTML = `
        <div style="font-size: 2rem; margin-bottom: 8px">${emoji}</div>
        <div class="score-value">${correct}/${total}</div>
        <div class="score-label">${percentage}% richtig</div>
    `;
    scoreArea.style.display = 'block';
}

// ═══════════════════════════════════════════════════════════
//  FLASHCARDS
// ═══════════════════════════════════════════════════════════

async function generateFlashcards() {
    const topic = document.getElementById('fc-topic').value.trim();
    const count = parseInt(document.getElementById('fc-count').value) || 8;

    showLoading('Lernkarten werden erstellt...');

    try {
        const res = await fetch('/api/flashcards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic || null, num_cards: count }),
        });
        const data = await res.json();
        hideLoading();

        if (data.error && (!data.cards || data.cards.length === 0)) {
            showToast(data.error, 'error');
            return;
        }

        renderFlashcards(data);
        showToast(`${data.cards.length} Lernkarten erstellt!`, 'success');

    } catch (e) {
        hideLoading();
        showToast('Fehler beim Erstellen der Lernkarten', 'error');
    }
}

function renderFlashcards(data) {
    const area = document.getElementById('flashcard-area');

    const html = data.cards.map((card, idx) => {
        const diffClass = (card.difficulty || 'mittel').toLowerCase();
        const tags = (card.tags || []).map(t => `<span class="fc-tag">${escapeHtml(t)}</span>`).join('');

        return `
            <div class="flashcard" onclick="this.classList.toggle('flipped')">
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <span class="fc-difficulty ${diffClass}">${escapeHtml(card.difficulty || 'Mittel')}</span>
                        <div class="fc-front-text">${escapeHtml(card.front)}</div>
                        <span class="fc-hint">Klicken zum Umdrehen</span>
                    </div>
                    <div class="flashcard-back">
                        <div class="fc-back-text">${escapeHtml(card.back)}</div>
                        ${tags ? `<div class="fc-tags">${tags}</div>` : ''}
                        ${card.page_reference ? `<span class="fc-hint">📄 Seite ${card.page_reference}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    area.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════
//  STATEMENTS (Richtig/Falsch)
// ═══════════════════════════════════════════════════════════

async function generateStatements() {
    const topic = document.getElementById('stmt-topic').value.trim();
    const count = parseInt(document.getElementById('stmt-count').value) || 6;

    showLoading('Aussagen werden generiert...');
    state.statementsAnswered = {};

    try {
        const res = await fetch('/api/statements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic || null, num_statements: count }),
        });
        const data = await res.json();
        hideLoading();

        if (data.error && (!data.statements || data.statements.length === 0)) {
            showToast(data.error, 'error');
            return;
        }

        renderStatements(data);
        showToast(`${data.statements.length} Aussagen erstellt!`, 'success');

    } catch (e) {
        hideLoading();
        showToast('Fehler beim Erstellen der Aussagen', 'error');
    }
}

let _statementsData = null;

function renderStatements(data) {
    _statementsData = data;
    const area = document.getElementById('statements-area');

    const html = data.statements.map((s, idx) => {
        return `
            <div class="statement-card" id="stmt-card-${idx}">
                <div class="statement-text">${escapeHtml(s.statement)}</div>
                <div class="statement-actions">
                    <button class="stmt-btn richtig" id="stmt-true-${idx}"
                            onclick="answerStatement(${idx}, true, ${s.is_true})">
                        ✓ Richtig
                    </button>
                    <button class="stmt-btn falsch" id="stmt-false-${idx}"
                            onclick="answerStatement(${idx}, false, ${s.is_true})">
                        ✗ Falsch
                    </button>
                </div>
                <div class="statement-feedback" id="stmt-feedback-${idx}"></div>
            </div>
        `;
    }).join('');

    area.innerHTML = html + `<div class="stmt-score" id="stmt-score-area"></div>`;
}

function answerStatement(idx, userAnswer, correct) {
    if (state.statementsAnswered[idx] !== undefined) return;
    state.statementsAnswered[idx] = userAnswer;

    const isCorrect = userAnswer === correct;
    const stmt = _statementsData.statements[idx];

    // Highlight buttons
    const trueBtn = document.getElementById(`stmt-true-${idx}`);
    const falseBtn = document.getElementById(`stmt-false-${idx}`);

    if (userAnswer) {
        trueBtn.classList.add('selected', isCorrect ? 'correct' : 'incorrect');
    } else {
        falseBtn.classList.add('selected', isCorrect ? 'correct' : 'incorrect');
    }

    trueBtn.classList.add('disabled');
    falseBtn.classList.add('disabled');

    // Show feedback
    const feedback = document.getElementById(`stmt-feedback-${idx}`);
    feedback.className = `statement-feedback visible ${isCorrect ? 'correct' : 'incorrect'}`;

    if (isCorrect) {
        feedback.innerHTML = `✓ Richtig! ${escapeHtml(stmt.explanation || '')}`;
    } else {
        feedback.innerHTML = `✗ Falsch! ${escapeHtml(stmt.explanation || '')}
            ${stmt.correction ? `<br><strong>Korrektur:</strong> ${escapeHtml(stmt.correction)}` : ''}`;
    }

    // Check completion
    const total = _statementsData.statements.length;
    if (Object.keys(state.statementsAnswered).length === total) {
        showStatementsScore(total);
    }
}

function showStatementsScore(total) {
    const correct = Object.values(state.statementsAnswered).filter((ans, i) => {
        return ans === _statementsData.statements[Object.keys(state.statementsAnswered)[i]]?.is_true;
    }).length;

    // Recalculate properly
    let correctCount = 0;
    for (const [idx, userAnswer] of Object.entries(state.statementsAnswered)) {
        if (userAnswer === _statementsData.statements[idx].is_true) {
            correctCount++;
        }
    }

    const scoreArea = document.getElementById('stmt-score-area');
    const percentage = Math.round((correctCount / total) * 100);
    let emoji = '🎉';
    if (percentage < 50) emoji = '📚';
    else if (percentage < 80) emoji = '👍';

    scoreArea.innerHTML = `
        <div style="font-size: 2rem; margin-bottom: 8px">${emoji}</div>
        <div class="score-value">${correctCount}/${total}</div>
        <div class="score-label">${percentage}% richtig</div>
    `;
    scoreArea.classList.add('visible');
}

// ═══════════════════════════════════════════════════════════
//  EXPLORE
// ═══════════════════════════════════════════════════════════

async function exploreTopic(topic) {
    if (!topic) {
        topic = document.getElementById('explore-topic').value.trim();
    }
    if (!topic) {
        showToast('Bitte ein Thema eingeben', 'info');
        return;
    }

    // If called from nav, switch to explore view
    if (state.currentView !== 'explore') {
        switchView('explore');
    }

    document.getElementById('explore-topic').value = topic;
    showLoading(`"${topic}" wird erforscht...`);

    try {
        const res = await fetch('/api/explore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic }),
        });
        const data = await res.json();
        hideLoading();

        const resultArea = document.getElementById('explore-result');
        const formattedContent = formatMarkdown(data.summary);

        let sourcesHtml = '';
        if (data.sources && data.sources.length > 0) {
            const tags = data.sources.map(s =>
                `<span class="source-tag">📄 Seite ${s.page}${s.chapter ? ' — ' + escapeHtml(s.chapter) : ''}</span>`
            ).join('');
            sourcesHtml = `<div class="explore-sources">${tags}</div>`;
        }

        resultArea.innerHTML = `
            <div class="explore-content">
                ${formattedContent}
                ${sourcesHtml}
            </div>
        `;

    } catch (e) {
        hideLoading();
        showToast('Fehler beim Erforschen des Themas', 'error');
    }
}

// ═══════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════

function showLoading(text = 'Wird generiert...') {
    state.isLoading = true;
    const overlay = document.getElementById('loading-overlay');
    document.getElementById('loading-text').textContent = text;
    overlay.classList.add('active');
}

function hideLoading() {
    state.isLoading = false;
    document.getElementById('loading-overlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('leaving');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function adjustCount(inputId, delta) {
    const input = document.getElementById(inputId);
    const min = parseInt(input.min) || 1;
    const max = parseInt(input.max) || 20;
    let val = parseInt(input.value) + delta;
    input.value = Math.max(min, Math.min(max, val));
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    return String(text || '')
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\r/g, '\\r')
        .replace(/\n/g, '\\n');
}

function formatMarkdown(text) {
    if (!text) return '';

    // Basic markdown formatting
    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold and italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Inline code
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');

    // Chemical subscripts: H₂O style already in text — keep as-is

    // Lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li>.+<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Paragraphs (double newlines)
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*<(h[1-3]|ul|ol)/g, '<$1');
    html = html.replace(/<\/(h[1-3]|ul|ol)>\s*<\/p>/g, '</$1>');

    return html;
}
