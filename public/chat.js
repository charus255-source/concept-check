'use strict';

const ideas = [
  ['BACKEND_PURPOSE', 'Why does a backend exist?', 'Behind the browser'],
  ['API_REQUEST', 'What does an API call carry?', 'A request’s journey'],
  ['API_AUTH', 'Why must private keys stay off the browser?', 'Keep it secret'],
  ['PERSISTENCE', 'How does an app remember?', 'Make it remember'],
  ['FOREIGN_KEY_MANY_SIDE', 'Why is the foreign key on the many side?', 'Connect the dots'],
  ['EVENT_ROWS', 'Why is each attempt a separate row?', 'A history worth keeping'],
  ['DATA_LOCATION', 'Where should each piece of data live?', 'Everything in its place'],
  ['HTTP_RESPONSE', 'How does an API tell the client what happened?', 'Did it work?'],
  ['REFERENTIAL_INTEGRITY', 'How does the database stop broken links?', 'No orphans'],
  ['RETRY_GAP', 'Why should a retry point to its gap?', 'Close the gap'],
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

// Jump into the typing box only with a mouse. On phones that would pop up the
// keyboard and hide what the learner needs to read; they tap the box when ready.
function softFocus(options) {
  if (matchMedia('(hover: hover) and (pointer: fine)').matches) $('explanation').focus(options);
}

function showError(message) {
  $('error-text').textContent = message;
  $('error').hidden = false;
}

function steps(stage) {
  ['step-explain', 'step-reflect', 'step-retry'].forEach(id => $(id).classList.toggle('done', stage === 'done'));
  $('step-explain').classList.toggle('active', stage === 'explain');
  $('step-reflect').classList.toggle('active', stage === 'reflect');
  $('step-retry').classList.toggle('active', stage === 'retry');
  $('composer-hint').textContent = stage === 'reflect'
    ? 'Take your time. What happens, and why?'
    : stage === 'retry' ? 'Apply what you worked out to the new case.'
    : 'Your own words are the best place to start.';
}

// One clear instruction above the typing box, so the learner always knows what to do next.
function guide(kind) {
  const idea = ideas.find(item => item[0] === state.idea);
  const question = idea[1].charAt(0).toLowerCase() + idea[1].slice(1);
  const text = {
    start: ['Step 1', 'Explain it in your own words below, then press Enter.', `In my own words: ${question}`],
    explain: ['Step 1', 'Now explain the concept in your own words below, then press Enter.', `In my own words: ${question}`],
    reflect: ['Your turn', 'Answer the question above, then press Enter.', 'Type your answer to the question…'],
    case: ['Your turn', 'Solve the case above, then press Enter.', 'Type your answer to the case…'],
    done: ['Finished', 'Your result is saved.', 'Or explain this concept again…'],
  }[kind];
  if (kind === 'done') steps('done');
  $('next-step').replaceChildren(element('b', '', text[0]), document.createTextNode(text[1]));
  if (kind === 'done') {
    // Visible on phones too, where "New conversation" sits inside the menu.
    const next = element('button', 'next-concept', 'Pick another concept →');
    next.type = 'button';
    next.addEventListener('click', () => $('new-chat').click());
    $('next-step').append(next);
  }
  $('explanation').placeholder = text[2];
  $('chat-form').classList.toggle('in-conversation', kind !== 'start');
}

// Start screen shows only concept cards; the typing box appears once a concept is open.
function view() {
  const onWelcome = !$('welcome').hidden;
  document.body.classList.toggle('on-welcome', onWelcome);
  $('current-concept').textContent = onWelcome ? 'Choose a concept'
    : ideas.find(idea => idea[0] === state.idea)[1];
  $('concept-intro').hidden = onWelcome || $('messages').children.length > 0;
}

function message(role, text, probeData, pending = false, custom = null) {
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
  } else if (custom) {
    content.append(custom);
  } else if (probeData) {
    if (probeData.recited_sentence) {
      content.append(element('div', 'quote-label', 'Let’s dig into this sentence'));
      content.append(element('blockquote', '', probeData.recited_sentence));
    }
    content.append(element('div', 'message-question', probeData.follow_up_question));
  } else {
    content.append(element('div', 'message-body', text));
    if (role === 'assistant' && text === retryMessage) {
      content.append(element('div', 'message-note', 'Saved as practice, without a pass/fail judgment.'));
    }
  }
  row.append(avatar, content);
  $('messages').append(row);
  view();
  if (!pending) state.export.push({ role, text: custom ? text : probeData
    ? [probeData.recited_sentence, probeData.follow_up_question].filter(Boolean).join('\n\n') : text });
  return row;
}

function caseCard(phase, question) {
  const card = element('div', 'case-card');
  card.append(element('div', 'label', phase === 'before' ? 'Case · before practice' : phase === 'after' ? 'New case · after practice' : 'Case'));
  card.append(element('p', '', question));
  return card;
}

function resultCard(result) {
  const kind = result.status === 'PASS' ? 'pass' : result.met && !result.contradictions.length ? 'almost' : 'notyet';
  const card = element('div', 'result-card ' + kind);
  const head = element('div', 'result-head');
  head.append(element('span', 'result-badge', { pass: 'Pass', almost: 'Almost there', notyet: 'Not yet' }[kind]));
  head.append(element('span', 'result-title', result.message));
  card.append(head);
  const meter = element('div', 'meter');
  meter.setAttribute('aria-hidden', 'true');
  result.checks.forEach(check => meter.append(element('i', check.met ? 'on' : '')));
  card.append(meter);
  const body = element('div', 'result-body');
  const got = result.checks.filter(check => check.met);
  const missing = result.checks.filter(check => !check.met);
  if (got.length) {
    body.append(element('h3', '', 'What you got right'));
    const list = element('ul');
    got.forEach(check => { const item = element('li', 'got'); item.append(icon('check'), element('span', '', check.feedback)); list.append(item); });
    body.append(list);
  }
  if (missing.length || result.contradictions.length) {
    body.append(element('h3', '', 'Still missing'));
    const list = element('ul');
    missing.forEach(check => list.append(element('li', 'missing', check.feedback)));
    if (result.contradictions.length) list.append(element('li', 'conflict', 'Part of your answer gives advice that would break this case.'));
    body.append(list);
  }
  if (result.status !== 'PASS') {
    body.append(element('p', 'result-note', 'The checks can miss a correct answer written in unusual words. If you think yours is right, tell your trainer.'));
  }
  card.append(body);
  return card;
}

function exportText(result) {
  const right = result.checks.filter(check => check.met).map(check => '✓ ' + check.feedback);
  const missing = result.checks.filter(check => !check.met).map(check => '• ' + check.feedback);
  return [result.message, right.length ? 'What you got right:\n' + right.join('\n') : '',
    missing.length ? 'Still missing:\n' + missing.join('\n') : ''].filter(Boolean).join('\n\n');
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
    button.addEventListener('click', () => selectIdea(id, true, true));
    $('history-nav').append(button);
  }
}

function selectIdea(id, restore = false, open = false) {
  if (state.busy) return;
  let restoredRows = 0;
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
  $('current-concept').textContent = idea[1];
  $('intro-title').textContent = idea[1];
  document.querySelectorAll('.topic-card').forEach(card => card.classList.toggle('selected', card.dataset.idea === id));
  if (restore) {
    const rows = state.attempts.filter(row => row.idea_id === id);
    for (const row of rows) {
      if (typeof row.passed === 'boolean') {
        message('assistant', 'Case: ' + row.case_question, null, false, caseCard('', row.case_question));
      }
      message('user', row.learner_response);
      if (typeof row.passed === 'boolean') {
        if (row.result) message('assistant', exportText(row.result), null, false, resultCard(row.result));
        else message('assistant', row.passed ? 'Pass. All the ideas for this case were covered.'
          : 'Not yet. This answer was checked with an older version of the rules, so the details are not available.');
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
    restoredRows = rows.length;
    $('assessment-actions').hidden = state.assessmentGap === null;
  }
  if (open) $('welcome').hidden = true;
  view();
  guide(state.gap ? 'reflect' : restoredRows ? 'done' : 'start');
  updateHistory();
  closeNavigation();
  softFocus({ preventScroll: true });
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
ideas.forEach(([id, question, title], index) => {
  const card = element('button', 'topic-card');
  card.type = 'button';
  card.dataset.idea = id;
  const text = element('span', 'topic-text');
  text.append(element('strong', '', title), element('span', '', question));
  card.append(element('span', 'topic-number', String(index + 1).padStart(2, '0')), text, icon('chevron'));
  card.addEventListener('click', () => { selectIdea(id, true, true); softFocus(); window.scrollTo({ top: 0 }); });
  $('topic-grid').append(card);
});
$('current-concept').textContent = ideas.find(idea => idea[0] === state.idea)[1];
guide('start');
view();
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
    message('assistant', 'Case: ' + result.case_question, null, false, caseCard(result.phase, result.case_question));
    $('explanation').value = '';
    guide('case');
    $('composer-hint').textContent = 'Python checks your answer. The AI never grades.';
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
    softFocus({ preventScroll: true });
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
// Phones: keep the typing box in view when the keyboard opens.
$('explanation').addEventListener('focus', () => {
  setTimeout(() => $('chat-form').scrollIntoView({ block: 'end', behavior: 'smooth' }), 300);
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
    if (assessing && result.status === 'QUESTION') {
      // A clarifying question: not graded, the case stays open.
      message('assistant', result.message);
    } else if (assessing) {
      state.assessment = null;
      message('assistant', exportText(result), null, false, resultCard(result));
      if (assessing.phase === 'before') {
        message('assistant', 'Now explain the concept in your own words. We’ll ask one follow-up, then give you a different case.');
      }
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
    guide(state.assessment ? 'case' : state.gap ? 'reflect' : assessing ? (assessing.phase === 'before' ? 'explain' : 'done') : 'explain');
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
    view();
  } finally {
    setBusy(false);
    if (succeeded) softFocus({ preventScroll: true }); else $('explanation').focus();
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
