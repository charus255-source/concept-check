'use strict';

const ideas = [
  ['BACKEND_PURPOSE', 'Why does a backend exist?', 'Behind the browser'],
  ['API_REQUEST', 'What does an API call carry?', 'A request’s journey'],
  ['API_AUTH', 'Why must private keys stay off the browser?', 'Keep it secret'],
  ['PERSISTENCE', 'How does an app remember?', 'Make it remember'],
  ['FOREIGN_KEY_MANY_SIDE', 'Why is the foreign key on the many side?', 'Connect the dots'],
  ['EVENT_ROWS', 'Why is each attempt a separate row?', 'A history worth keeping'],
  ['DATA_LOCATION', 'Where should each piece of data live?', 'Everything in its place'],
];
const $ = id => document.getElementById(id);
const state = { idea: 'API_AUTH', gap: null, busy: false, attempts: [], export: [], ready: false,
  assessment: null, assessmentGap: null };
const retryMessage = 'Your second try is saved as practice. Now apply your reasoning to a different case.';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#i-' + name);
  svg.append(use);
  return svg;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(path, {
      ...options, signal: controller.signal, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    let result;
    try { result = await response.json(); }
    catch { throw new Error('The server returned an unexpected response. Please try again.'); }
    if (!response.ok) {
      const error = new Error(typeof result.detail === 'string' ? result.detail : 'Please check your explanation and try again.');
      error.status = response.status;
      throw error;
    }
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('This is taking longer than expected. Check your history before resending.');
    if (error instanceof TypeError) throw new Error('Couldn’t reach Concept Check. Check your connection and try again.');
    throw error;
  } finally { clearTimeout(timeout); }
}

function showError(message) {
  $('error-text').textContent = message;
  $('error').hidden = false;
}

function steps(stage) {
  $('step-explain').classList.toggle('active', stage === 'explain');
  $('step-reflect').classList.toggle('active', stage === 'reflect');
  $('step-retry').classList.toggle('active', stage === 'retry');
  $('composer-hint').textContent = stage === 'reflect'
    ? 'Take your time. What happens, and why?'
    : 'Your own words are the best place to start.';
}

function message(role, text, probeData, pending = false) {
  $('welcome').hidden = true;
  const row = element('article', 'message ' + role);
  const avatar = element('span', 'message-avatar', role === 'user' ? 'Y' : undefined);
  if (role !== 'user') avatar.append(icon('spark'));
  avatar.setAttribute('aria-hidden', 'true');
  const content = element('div', 'message-content');
  content.append(element('div', 'message-name', role === 'user' ? 'You' : 'Concept Check'));
  if (pending) {
    const typing = element('div', 'typing');
    typing.setAttribute('aria-label', state.assessment ? 'Checking your case answer' : 'Thinking through your explanation');
    typing.append(element('span'), element('span'), element('span'));
    content.append(typing);
    content.append(element('div', 'message-note', state.assessment ? 'Checking your answer against the predefined rules…' : 'Finding a question worth asking…'));
  } else if (probeData) {
    content.append(element('div', 'message-body', probeData.recited_sentence ? 'Let’s look a little closer at this part.' : 'Let’s take your reasoning a little further.'));
    if (probeData.recited_sentence) {
      content.append(element('div', 'quote-label', 'In your words'));
      content.append(element('blockquote', '', probeData.recited_sentence));
    }
    content.append(element('div', 'message-question', probeData.follow_up_question));
    content.append(element('div', 'message-note', 'Think it through below. You can challenge the question, too.'));
  } else {
    content.append(element('div', 'message-body', text));
    if (role === 'assistant' && text === retryMessage) {
      content.append(element('div', 'message-note', 'Saved as practice, without a pass/fail judgment.'));
    }
  }
  row.append(avatar, content);
  $('messages').append(row);
  if (!pending) state.export.push({ role, text: probeData
    ? [probeData.recited_sentence, probeData.follow_up_question].filter(Boolean).join('\n\n') : text });
  return row;
}

function scrollToLatest() {
  requestAnimationFrame(() => window.scrollTo({ top: document.documentElement.scrollHeight,
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
}

function closeNavigation() {
  $('sidebar').classList.remove('open');
  $('overlay').hidden = true;
  $('menu').setAttribute('aria-expanded', 'false');
}

function updateHistory() {
  const visited = [...new Set(state.attempts.map(row => row.idea_id))].filter(id => ideas.some(idea => idea[0] === id));
  $('history-count').textContent = visited.length;
  if (!visited.length) return;
  $('history-nav').replaceChildren();
  for (const id of visited.reverse()) {
    const button = element('button', 'history-item' + (id === state.idea ? ' selected' : ''));
    button.append(icon('chat'), element('span', '', ideas.find(idea => idea[0] === id)[2]));
    button.addEventListener('click', () => selectIdea(id, true));
    $('history-nav').append(button);
  }
}

function selectIdea(id, restore = false) {
  if (state.busy) return;
  state.idea = id;
  state.gap = null;
  state.assessment = null;
  state.assessmentGap = null;
  $('assessment-actions').hidden = true;
  $('fresh-case').textContent = 'Try a fresh case';
  state.export = [];
  $('concept').value = id;
  $('messages').replaceChildren();
  $('welcome').hidden = false;
  $('error').hidden = true;
  steps('explain');
  const idea = ideas.find(item => item[0] === id);
  $('explanation').placeholder = `In my own words: ${idea[1].charAt(0).toLowerCase() + idea[1].slice(1)}…`;
  if (restore) {
    const rows = state.attempts.filter(row => row.idea_id === id);
    for (const row of rows) {
      if (typeof row.passed === 'boolean') {
        message('assistant', 'Practice case: ' + row.case_question);
      }
      message('user', row.learner_response);
      if (typeof row.passed === 'boolean') {
        message('assistant', row.passed ? 'PASS — the documented case checks were met.' : 'WRONG — the documented checks were not all met, or the answer contained conflicting advice.');
        state.gap = null;
        state.assessmentGap = null;
      } else if (row.probe) {
        message('assistant', '', { recited_sentence: row.recited_sentence, follow_up_question: row.probe.follow_up_question });
        state.gap = row.probe.id;
        state.assessmentGap = null;
      } else if (row.gap_id) {
        message('assistant', retryMessage);
        state.gap = null;
        state.assessmentGap = row.gap_id;
      } else {
        message('assistant', 'This explanation was saved, but its follow-up is unavailable. Start a new explanation to continue.');
        state.gap = null;
      }
    }
    steps(state.gap ? 'reflect' : rows.length ? 'retry' : 'explain');
    $('assessment-actions').hidden = state.assessmentGap === null;
  }
  updateHistory();
  closeNavigation();
  $('explanation').focus({ preventScroll: true });
  if (restore) scrollToLatest();
}

function setBusy(busy) {
  state.busy = busy;
  $('send').disabled = busy;
  $('concept').disabled = busy;
  $('new-chat').disabled = busy;
  $('baseline-case').disabled = busy;
  $('fresh-case').disabled = busy;
  $('explanation').readOnly = busy;
  $('send').setAttribute('aria-label', busy ? 'Waiting for Concept Check' : 'Send explanation');
  $('chat-form').setAttribute('aria-busy', String(busy));
  document.querySelectorAll('.topic-card').forEach(button => button.disabled = busy);
}

$('concept').replaceChildren(...ideas.map(([id, title]) => {
  const option = element('option', '', title);
  option.value = id;
  return option;
}));
$('concept').value = state.idea;
$('concept').addEventListener('change', event => selectIdea(event.target.value, true));
document.querySelectorAll('[data-idea]').forEach(button => button.addEventListener('click', () => selectIdea(button.dataset.idea, true)));
$('new-chat').addEventListener('click', () => {
  selectIdea(state.idea);
  $('explanation').value = '';
  $('explanation').dispatchEvent(new Event('input'));
  window.scrollTo({ top: 0 });
});

async function ensureSession() {
  if (!state.ready) {
    await api('/api/session', { method: 'POST', body: '{}' });
    state.ready = true;
  }
}

async function requestAssessment(gapId) {
  if (state.busy) return;
  setBusy(true);
  $('error').hidden = true;
  try {
    await ensureSession();
    const result = await api('/api/assessment/case', { method: 'POST', body: JSON.stringify({
      idea_id: state.idea, gap_id: gapId,
    }) });
    state.assessment = result;
    state.assessmentGap = gapId;
    state.gap = null;
    $('assessment-actions').hidden = true;
    message('assistant', (result.phase === 'before' ? 'Before you practice, try this case:\n\n' : 'Apply your reasoning to this different case:\n\n') + result.case_question);
    $('explanation').value = '';
    $('explanation').placeholder = 'Work through this case in your own words…';
    $('composer-hint').textContent = 'Python will apply the predefined case checks. Groq does not grade.';
    $('explanation').dispatchEvent(new Event('input'));
    scrollToLatest();
  } catch (error) {
    showError(error.message);
    if (error.status === 401) state.ready = false;
    if (gapId !== null || state.assessment) {
      $('assessment-actions').hidden = false;
      $('fresh-case').textContent = 'Request a case again';
    }
  } finally {
    setBusy(false);
    $('explanation').focus({ preventScroll: true });
  }
}

$('baseline-case').addEventListener('click', () => { void requestAssessment(null); });
$('fresh-case').addEventListener('click', () => { void requestAssessment(state.assessmentGap); });
$('dismiss-error').addEventListener('click', () => $('error').hidden = true);
$('menu').addEventListener('click', () => {
  const open = $('sidebar').classList.toggle('open');
  $('overlay').hidden = !open;
  $('menu').setAttribute('aria-expanded', String(open));
});
$('overlay').addEventListener('click', closeNavigation);
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeNavigation(); });
$('explanation').addEventListener('input', () => {
  $('character-count').textContent = `${$('explanation').value.length.toLocaleString()} / 6,000`;
  $('explanation').style.height = 'auto';
  $('explanation').style.height = Math.min($('explanation').scrollHeight, 190) + 'px';
});
$('explanation').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!state.busy) $('chat-form').requestSubmit();
  }
});

$('chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (state.busy) return;
  const explanation = $('explanation').value.trim();
  if (explanation.length < (state.assessment ? 1 : 10)) {
    showError(state.assessment ? 'Write your answer to the case.' : 'Give us a little more to think about—at least 10 characters.');
    $('explanation').focus();
    return;
  }
  $('error').hidden = true;
  setBusy(true);
  const userRow = message('user', explanation);
  const pending = message('assistant', '', null, true);
  scrollToLatest();
  let succeeded = false;
  let nextAssessmentGap = null;
  try {
    await ensureSession();
    const assessing = state.assessment;
    const result = await api(assessing ? '/api/assessment/answer' : '/api/check', {
      method: 'POST', body: JSON.stringify(assessing
        ? { challenge: assessing.challenge, answer: explanation }
        : { idea_id: state.idea, explanation, gap_id: state.gap }),
    });
    pending.remove();
    if (assessing) {
      state.assessment = null;
      const missing = result.checks.filter(check => !check.met).map(check => '• ' + check.feedback);
      if (result.contradictions.length) missing.push('• Your answer also contains conflicting advice.');
      message('assistant', result.message + (missing.length ? '\n\n' + missing.join('\n') : '') +
        '\n\nThis result reflects the documented text checks; they may miss valid paraphrases.');
      message('assistant', assessing.phase === 'before'
        ? 'Now explain the concept in your own words. We’ll explore one follow-up before a different case.'
        : 'Your case answer and its result are saved. You can explore another concept.');
      steps('explain');
    } else if (result.stage === 'retry') {
      message('assistant', result.message);
      state.gap = null;
      state.assessmentGap = result.gap_id;
      nextAssessmentGap = result.gap_id;
      $('assessment-actions').hidden = false;
      steps('retry');
    } else {
      message('assistant', '', result);
      state.gap = result.gap_id;
      state.assessmentGap = null;
      $('assessment-actions').hidden = true;
      steps('reflect');
    }
    succeeded = true;
    $('explanation').value = '';
    $('explanation').placeholder = state.gap ? 'Here’s what I think would happen…' : 'Try another explanation, or explore a different concept…';
    $('explanation').dispatchEvent(new Event('input'));
    // History is a separate read: it must not hold the composer in its busy state.
    void refreshHistory();
    scrollToLatest();
  } catch (error) {
    pending.remove();
    userRow.remove();
    state.export.pop();
    showError(error.message);
    if (error.status === 401) state.ready = false;
    if (error.status === 409 && state.assessment) {
      $('assessment-actions').hidden = false;
      $('fresh-case').textContent = 'Request a case again';
    }
    if (!$('messages').children.length) $('welcome').hidden = false;
  } finally {
    setBusy(false);
    $('explanation').focus({ preventScroll: succeeded });
  }
  // Selection has its own error handling: a saved retry must never be resubmitted
  // merely because requesting the next case failed. Release busy before entering.
  if (succeeded && nextAssessmentGap !== null) await requestAssessment(nextAssessmentGap);
});

$('export').addEventListener('click', () => {
  if (!state.export.length) { showError('Start a conversation first, then download your notes here.'); return; }
  const title = ideas.find(idea => idea[0] === state.idea)[1];
  const text = '# Concept Check\n\n' + title + '\n\n' + state.export.map(row =>
    (row.role === 'user' ? 'You' : 'Concept Check') + '\n' + row.text).join('\n\n---\n\n');
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
  const anchor = element('a');
  anchor.href = url;
  anchor.download = 'concept-check-notes.txt';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

function showHistoryError(error) {
  const notice = element('div', 'empty-history');
  notice.setAttribute('role', 'status');
  notice.append(element('p', '', 'History could not load. You can still start a new practice session.'));
  notice.append(element('p', '', error.message));
  const retry = element('button', 'history-item', 'Retry history');
  retry.type = 'button';
  retry.addEventListener('click', () => { void refreshHistory(); });
  notice.append(retry);
  // Keep any previously loaded conversations accessible during a refresh failure.
  $('history-error')?.remove();
  notice.id = 'history-error';
  $('history-nav').append(notice);
}

async function refreshHistory(restore = false) {
  try {
    const result = await api('/api/history');
    $('history-error')?.remove();
    state.attempts = result.attempts;
    updateHistory();
    // Do not replace an in-progress conversation if the initial request was slow.
    if (!restore || state.busy || state.export.length) return;
    const latest = state.attempts.at(-1);
    if (latest && ideas.some(idea => idea[0] === latest.idea_id)) selectIdea(latest.idea_id, true);
  } catch (error) {
    // A first-time visitor has no cookie yet; only session creation establishes readiness.
    if (error.status !== 401) showHistoryError(error);
  }
}
void refreshHistory(true);
