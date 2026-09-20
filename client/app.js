'use strict';
const configs = {
  graos: {path: 'graos', filter: 'processo'},
  metodos: {path: 'metodos', filter: 'moagem'},
  degustacoes: {path: 'degustacoes', filter: 'grao_id'},
};
const state = Object.fromEntries(Object.keys(configs).map(key => [key, {items: [], online: false, last: null, query: null}]));
const money = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'});
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

async function request(url, options = {}, timeout = 2500) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {...options, signal: controller.signal});
    if (!response.ok) {
      let message = `Serviço indisponível (HTTP ${response.status}).`;
      try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch {}
      throw new Error(message);
    }
    return await response.json();
  } finally { clearTimeout(timer); }
}

function render(key) {
  const panel = document.querySelector(`#panel-${key}`);
  const data = state[key];
  const status = panel.querySelector('.status');
  status.className = `status ${data.online ? 'online' : 'offline'}`;
  status.textContent = data.online ? '● Disponível' : '● Indisponível';
  panel.classList.toggle('stale', !data.online);
  const currentFilter = document.querySelector(`#filtro-${key}`).value;
  const sameFilter = currentFilter === data.query;
  panel.querySelector('.freshness').textContent = data.online
    ? `${data.items.length} registros · Atualizado às ${data.last.toLocaleTimeString('pt-BR')}`
    : `${data.last && sameFilter ? `Dados anteriores de ${data.last.toLocaleTimeString('pt-BR')}. ` : ''}Nova tentativa automática em 5 s.`;
  const cards = panel.querySelector('.cards');
  if (!sameFilter || !data.items.length) {
    cards.innerHTML = `<p class="empty">${data.online ? 'Nenhum registro para este filtro.' : 'Aguardando conexão com o serviço.'}</p>`;
    return;
  }
  cards.innerHTML = data.items.map(item => {
    let body;
    if (key === 'graos') {
      body = `<h4>${escapeHTML(item.nome)}</h4><p>${escapeHTML(item.origem.regiao)} · ${escapeHTML(item.origem.pais)}<br>${escapeHTML(item.variedade)} · ${escapeHTML(item.processo)}</p><div class="tags">${item.notas_sensoriais.map(tag => `<span class="tag">${escapeHTML(tag)}</span>`).join('')}</div><div class="card-bottom"><span>${money.format(item.preco_kg)} / kg</span><span>${item.sacas_estoque} sacas</span></div>`;
    } else if (key === 'metodos') {
      body = `<h4>${escapeHTML(item.nome)}</h4><p>Moagem ${escapeHTML(item.moagem)} · proporção ${escapeHTML(item.proporcao)}</p><div class="tags"><span class="tag">${item.temperatura_c} °C</span><span class="tag">${item.tempo_segundos} segundos</span></div>`;
    } else {
      const grain = state.graos.items.find(g => g.id === item.grao_id);
      const method = state.metodos.items.find(m => m.id === item.metodo_id);
      body = `<h4>${escapeHTML(grain?.nome || `Grão #${item.grao_id}`)}</h4><p>${escapeHTML(method?.nome || `Método #${item.metodo_id}`)} · ${new Date(item.data).toLocaleDateString('pt-BR')}<br>${escapeHTML(item.comentario)}</p><div class="tags"><span class="tag">Acidez ${item.avaliacao.acidez}/5</span><span class="tag">Corpo ${item.avaliacao.corpo}/5</span><span class="tag">Doçura ${item.avaliacao.docura}/5</span></div><div class="card-bottom"><span class="score">${item.nota_final.toFixed(1)} <small>/ 10</small></span></div>`;
    }
    return `<article class="card">${body}<button class="detail-button" data-id="${item.id}" type="button">Ver detalhes ↗</button></article>`;
  }).join('');
}

// Um ciclo independente por serviço; falhas nunca interrompem os outros ciclos.
async function poll(key) {
  const config = configs[key];
  const filter = document.querySelector(`#filtro-${key}`).value;
  const query = new URLSearchParams();
  if (filter) query.set(config.filter, filter);
  try {
    const items = await request(`/api/${key}/${config.path}?${query}`);
    state[key] = {items, online: true, last: new Date(), query: filter};
  } catch {
    state[key].online = false;
  } finally {
    render(key);
    if (key !== 'degustacoes' && state.degustacoes.last) render('degustacoes');
    setTimeout(() => poll(key), 5000);
  }
}

for (const key of Object.keys(configs)) {
  poll(key);
  document.querySelector(`#filtro-${key}`).addEventListener('change', () => {
    document.querySelector(`#panel-${key} .freshness`).textContent = 'Filtro será aplicado na próxima atualização…';
  });
  document.querySelector(`#panel-${key} .cards`).addEventListener('click', async event => {
    const button = event.target.closest('[data-id]');
    if (!button) return;
    const dialog = document.querySelector('#detail');
    const content = document.querySelector('#detail-content');
    content.textContent = 'Consultando serviço…';
    dialog.showModal();
    try {
      const record = await request(`/api/${key}/${configs[key].path}/${button.dataset.id}`);
      content.textContent = JSON.stringify(record, null, 2);
    } catch { content.textContent = 'Este serviço está indisponível. Os outros painéis continuam funcionando.'; }
  });
}
document.querySelector('#close-detail').addEventListener('click', () => document.querySelector('#detail').close());

let history = [];
let chatBusy = false;
let cooldownUntil = 0;
const COOLDOWN_MS = 15000;
function formatMarkdown(text) {
  // Escapa HTML para segurança
  const div = document.createElement('div');
  div.textContent = text;
  let html = div.innerHTML;

  // Formata negrito
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Formata listas simples com * ou -
  html = html.replace(/^(?:\s*)(?:-|\*)\s+(.*)/gm, '• $1');
  // Formata quebras de linha
  html = html.replace(/\n/g, '<br>');
  
  return html;
}

function addMessage(text, kind) {
  const node = document.createElement('div');
  node.className = `message ${kind}-message`;
  node.innerHTML = formatMarkdown(text);
  const messages = document.querySelector('#messages');
  messages.append(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}
function startCooldown(button) {
  cooldownUntil = Date.now() + COOLDOWN_MS;
  button.disabled = true;
  const tick = () => {
    const remaining = Math.ceil((cooldownUntil - Date.now()) / 1000);
    if (remaining > 0) {
      button.textContent = `Aguarde ${remaining}s`;
      setTimeout(tick, 500);
    } else {
      button.disabled = chatBusy;
      button.textContent = 'Enviar ↗';
    }
  };
  tick();
}
async function chatStatus() {
  const node = document.querySelector('#chat-status');
  try {
    const status = await request('/api/chat/health');
    node.textContent = status.configured ? '● Pronto para conversar' : 'Configure GEMINI_API_KEY';
  } catch { node.textContent = 'Chat indisponível'; }
  setTimeout(chatStatus, 10000);
}
chatStatus();
document.querySelector('#chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  const input = document.querySelector('#question');
  const message = input.value.trim();
  if (!message || chatBusy || Date.now() < cooldownUntil) return;
  chatBusy = true;
  const button = event.target.querySelector('button');
  button.disabled = true;
  button.textContent = 'Consultando…';
  addMessage(message, 'user');
  input.value = '';
  let isRateLimited = false;
  try {
    const result = await request('/api/chat/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, history})}, 90000);
    const node = addMessage(result.answer, 'assistant');
    if (result.tools_used.length) {
      const trace = document.createElement('span');
      trace.className = 'tool-trace';
      trace.textContent = `Consultas MCP: ${result.tools_used.join(' · ')}`;
      node.append(trace);
    }
    history = [...history, {role:'user', content:message}, {role:'assistant', content:result.answer}].slice(-12);
  } catch (error) {
    const msg = error.name === 'AbortError' ? 'Tempo de resposta excedido. Tente novamente.' : error.message;
    isRateLimited = /cota|limite|rate|429|503|indisponível/i.test(msg);
    addMessage(msg, 'error');
    input.value = message;
  } finally {
    chatBusy = false;
    startCooldown(button);
    if (isRateLimited) cooldownUntil = Date.now() + COOLDOWN_MS * 2;
  }
});
document.querySelectorAll('.suggestions button').forEach(button => button.addEventListener('click', () => {
  document.querySelector('#question').value = button.textContent;
  document.querySelector('#question').focus();
}));
