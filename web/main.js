import { 
  MessageType, 
  MessageTypeConfig, 
  ChatManager,
  createExpandableMessageCard,
  createPartMessageCard,
  createEventMessageCard,
  showDetailsModal,
  formatTimeInfo,
  parseContentByType
} from './chat.js';

const el = {
  status: document.getElementById("status"),
  authStatus: document.getElementById("authStatus"),
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  userEmail: document.getElementById("userEmail"),
  wsUrl: document.getElementById("wsUrl"),
  wsUrlText: document.getElementById("wsUrlText"),
  userId: document.getElementById("userId"),
  sessionId: document.getElementById("sessionId"),
  projectId: document.getElementById("projectId"),
  projectIdOut: document.getElementById("projectIdOut"),
  connectBtn: document.getElementById("connectBtn"),
  disconnectBtn: document.getElementById("disconnectBtn"),
  messages: document.getElementById("messages"),
  composer: document.getElementById("composer"),
  text: document.getElementById("text"),
  sendBtn: document.getElementById("sendBtn"),
  modeSelect: document.getElementById("modeSelect"),
  runModeSelect: document.getElementById("runModeSelect"),
  buildVersionsList: document.getElementById("buildVersionsList"),
  refreshBuildVersionsBtn: document.getElementById("refreshBuildVersionsBtn"),
  statUserId: document.getElementById("statUserId"),
  statSessionId: document.getElementById("statSessionId"),
  statProjectId: document.getElementById("statProjectId"),
};

const state = {
  ws: null,
  connected: false,
  connecting: false,
  pendingByRequestId: new Map(),
  availableAgents: [],
  currentMode: "agent",
  runMode: "stream",
  auth: {
    token: null,
    userId: null,
    email: null,
  },
};

let chatManager = null;

function nowLabel() {
  const d = new Date();
  return d.toLocaleTimeString();
}

function setStatus(mode, text) {
  el.status.classList.remove("status--connected", "status--disconnected", "status--connecting");
  if (mode === "connected") el.status.classList.add("status--connected");
  if (mode === "disconnected") el.status.classList.add("status--disconnected");
  if (mode === "connecting") el.status.classList.add("status--connecting");
  el.status.textContent = text;
}

function setAuthStatus(mode, text) {
  el.authStatus.classList.remove("status--connected", "status--disconnected", "status--connecting");
  if (mode === "connected") el.authStatus.classList.add("status--connected");
  if (mode === "disconnected") el.authStatus.classList.add("status--disconnected");
  if (mode === "connecting") el.authStatus.classList.add("status--connecting");
  el.authStatus.textContent = text;
}

function updateStats() {
  const uid = el.userId.value.trim();
  const sid = el.sessionId.value.trim();
  const pid = el.projectId.value.trim();
  
  el.statUserId.textContent = uid ? uid.slice(0, 8) : "-";
  el.statSessionId.textContent = sid ? sid.slice(0, 16) : "-";
  el.statProjectId.textContent = pid ? pid.slice(0, 8) : "-";
}

function scrollToBottom() {
  el.messages.scrollTop = el.messages.scrollHeight;
}

function sys(text, rawData = null) {
  chatManager.sys(text, rawData);
}

function nextRequestId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `r_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function canSend() {
  return state.connected && state.ws && state.ws.readyState === WebSocket.OPEN;
}

function updateButtons() {
  el.connectBtn.disabled = state.connected || state.connecting;
  el.disconnectBtn.disabled = !state.connected && !state.connecting;
  el.sendBtn.disabled = !canSend();
}

function updateAuthButtons() {
  const loggedIn = Boolean(state.auth.token);
  el.loginBtn.disabled = loggedIn;
  el.logoutBtn.disabled = !loggedIn;
}

function normalizeBaseUrl(url) {
  const trimmed = String(url || "").trim();
  if (!trimmed) return "";
  return trimmed.replace(/\/+$/, "");
}

function getApiBaseUrl() {
  return normalizeBaseUrl(el.apiBaseUrl.value);
}

function setAuth(auth) {
  state.auth.token = auth?.token || null;
  state.auth.userId = auth?.userId ?? null;
  state.auth.email = auth?.email ?? null;
  if (state.auth.token) localStorage.setItem("apiToken", state.auth.token);
  else localStorage.removeItem("apiToken");

  if (state.auth.userId != null) localStorage.setItem("apiUserId", String(state.auth.userId));
  else localStorage.removeItem("apiUserId");

  if (state.auth.email) localStorage.setItem("apiEmail", String(state.auth.email));
  else localStorage.removeItem("apiEmail");

  el.userEmail.textContent = state.auth.email || "Test@sparkx.com";

  updateAuthButtons();
  if (state.auth.token) {
    const suffix = state.auth.token.slice(-6);
    setAuthStatus("connected", `Logged In …${suffix}`);
  } else {
    setAuthStatus("disconnected", "Not Logged In");
  }

  if (state.auth.userId != null) {
    const uid = String(state.auth.userId);
    el.userId.value = uid;
    localStorage.setItem("userId", uid);
    updateStats();
  }
}

function authHeaderValue() {
  if (!state.auth.token) return null;
  return `Bearer ${state.auth.token}`;
}

async function apiJson(path, init) {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) throw new Error("缺少 API Base URL");

  const headers = new Headers(init?.headers || {});
  const authValue = authHeaderValue();
  if (authValue) headers.set("Authorization", authValue);

  const res = await fetch(`${baseUrl}${path}`, { ...(init || {}), headers });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  console.log("apiJson", path, init, res, data, text);
  return { res, data, text };
}

async function fetchAvailableAgents() {
  if (!state.auth.token) return [];
  try {
    const { res, data, text } = await apiJson("/api/v1/agents?page=1&pageSize=200", { method: "GET" });
    if (!res.ok) {
      const detail = data?.message || data?.msg || text || `HTTP ${res.status}`;
      sys(`获取可用 agents 失败：${detail}`);
      return [];
    }
    const list = Array.isArray(data?.list) ? data.list : [];
    state.availableAgents = list;
    sys(`可用 agents（${list.length}）：${list.map((x) => x?.name).filter(Boolean).join("、")}`);
    return list;
  } catch (e) {
    sys(`获取可用 agents 请求失败：${e?.message || String(e)}`);
    return [];
  }
}

async function refreshAfterAuth() {
  await fetchAvailableAgents();
  await fetchBuildVersions();
}

async function fetchBuildVersions() {
  if (!state.auth.token) return;
  const projectId = el.projectId.value.trim();
  if (!projectId) {
    renderBuildVersions([]);
    return;
  }
  try {
    const { res, data, text } = await apiJson(`/api/v1/projects/${projectId}/build-versions?page=1&pageSize=50`, { method: "GET" });
    if (!res.ok) {
      const detail = data?.message || data?.msg || text || `HTTP ${res.status}`;
      sys(`获取构建版本失败：${detail}`);
      renderBuildVersions([]);
      return;
    }
    const list = Array.isArray(data?.list) ? data.list : [];
    renderBuildVersions(list);
  } catch (e) {
    sys(`获取构建版本请求失败：${e?.message || String(e)}`);
    renderBuildVersions([]);
  }
}

function renderBuildVersions(list) {
  if (!el.buildVersionsList) return;
  if (!list || list.length === 0) {
    el.buildVersionsList.innerHTML = '<div class="build-version-empty">暂无构建版本 There is no build version yet</div>';
    return;
  }
  const html = list.map((item) => {
    const name = item.description ? item.description.substring(0, 50) : `构建版本 #${item.buildVersionId}`;
    const desc = item.description || "无描述";
    const createdAt = item.createdAt || "";
    return `
      <div class="build-version-item" data-id="${item.buildVersionId}">
        <div class="build-version-name">${escapeHtml(name)}</div>
        <div class="build-version-desc" title="${escapeHtml(desc)}">${escapeHtml(desc)}</div>
        <div class="build-version-meta">
          <span>ID: ${item.buildVersionId}</span>
          <span>Manifest: ${item.softwareManifestId}</span>
          <span>${escapeHtml(createdAt)}</span>
        </div>
      </div>
    `;
  }).join("");
  el.buildVersionsList.innerHTML = html;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function login() {
  const baseUrl = getApiBaseUrl();
  const email = el.email.value.trim();
  const password = el.password.value;
  
  console.log("login debug:", { baseUrl, email, apiBaseUrlValue: el.apiBaseUrl?.value });
  
  if (!baseUrl || !email || !password) {
    sys("登录信息不完整");
    return;
  }

  setAuthStatus("connecting", "Logging In...");
  updateAuthButtons();

  try {
    const res = await fetch(`${baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        loginType: "email",
        email,
        password,
      }),
    });

    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }

    if (!res.ok) {
      const detail = data?.message || data?.msg || text || `HTTP ${res.status}`;
      setAuthStatus("disconnected", "Not Logged In");
      sys(`登录失败：${detail}`);
      return;
    }

    const token = data?.token;
    if (typeof token !== "string" || !token) {
      setAuthStatus("disconnected", "Not Logged In");
      sys("登录失败：未返回 token");
      return;
    }

    const apiUserId = data?.userId ?? null;
    setAuth({ token, userId: apiUserId, email });
    sys("登录成功");
    await refreshAfterAuth();
  } catch (e) {
    setAuthStatus("disconnected", "Not Logged In");
    sys(`登录请求失败：${e?.message || String(e)}`);
  }
}

function logout() {
  setAuth({ token: null, userId: null, email: el.email.value.trim() || null });
  sys("已退出登录");
}

function connect() {
  const baseUrl = el.wsUrl.value.trim();
  if (!baseUrl) return;
  const token = state.auth.token;
  const projectId = el.projectId.value.trim();
  const authUserId = state.auth.userId != null ? String(state.auth.userId) : null;
  console.log("connect() called - projectId:", projectId, "el.projectId.value:", el.projectId.value);
  if (!token) {
    sys("请先登录获取 token，再连接 WebSocket");
    state.connected = false;
    state.connecting = false;
    setStatus("disconnected", "Disconnected");
    updateButtons();
    return;
  }
  if (!authUserId) {
    sys("登录未返回 userId，无法连接 WebSocket");
    return;
  }

  if (state.ws) {
    try {
      state.ws.close();
    } catch {}
    state.ws = null;
  }

  state.connecting = true;
  setStatus("connecting", "Connecting...");
  updateButtons();

  let url = baseUrl;
  if (token) {
    try {
      const u = new URL(baseUrl);
      u.searchParams.set("token", token);
      url = u.toString();
    } catch {}
  }

  const ws = new WebSocket(url);
  state.ws = ws;

  ws.onopen = () => {
    state.connected = true;
    state.connecting = false;
    setStatus("connected", "Connected");
    updateButtons();
    updateStats();
    sys(`已连接：${baseUrl}`);
    if (token) {
      try {
        const authMsg = {
          type: "auth",
          token,
          project_id: projectId,
          user_id: authUserId,
        };
        console.log("Sending auth message:", authMsg);
        ws.send(JSON.stringify(authMsg));
        if (state.currentMode !== "agent") {
          const modeMsg = {
            type: "mode",
            mode: state.currentMode,
          };
          ws.send(JSON.stringify(modeMsg));
        }
      } catch {}
    }
  };

  ws.onclose = () => {
    state.connected = false;
    state.connecting = false;
    setStatus("disconnected", "Disconnected");
    updateButtons();
    sys("连接已断开");
  };

  ws.onerror = () => {
    sys("连接发生错误");
  };

  ws.onmessage = async (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      sys(`收到非 JSON：${String(ev.data).slice(0, 200)}`);
      return;
    }

    console.log("Received message------>>:", msg);
    const type = msg.type;
    if (type === "pong") return;
    if (type === "auth_ok") {
      const pid = typeof msg.project_id === "string" ? msg.project_id : "";
      if (pid) {
        el.projectIdOut.value = pid;
        el.projectId.value = pid;
        localStorage.setItem("projectId", pid);
        updateStats();
        await fetchBuildVersions();
      }
      sys("Token 已发送到服务器");
      return;
    }

    if (type === "mode_ok") {
      const mode = msg.mode || "agent";
      sys(`模式已切换为: ${mode === "skill" ? "Skill" : "Agent"}`);
      return;
    }

    if (type === "event") {
      if (msg.message_type !== undefined) {
        chatManager.handleEventMessage(msg);
        return;
      }
      
      const requestId = msg.request_id;
      const eventType = msg.event_type;
      const parts = msg.parts || [];
      const elapsedMs = msg.elapsed_ms;
      const author = msg.author || "unknown";

      if (eventType === "streaming") {
        const timeInfo = elapsedMs !== undefined ? `[${elapsedMs}ms]` : "";
        
        parts.forEach((part, partIndex) => {
          const rawData = {
            type: msg.type,
            request_id: requestId,
            event_type: eventType,
            part: part,
            author: author,
            elapsed_ms: elapsedMs,
            server_time: msg.server_time
          };
          
          chatManager.handleStreamingPart(requestId, part, {
            timeInfo,
            author: author,
            rawData,
            partIndex
          });
        });
      } else if (eventType === "completed") {
        chatManager._finalizeStreamingGroup(requestId);
        
        if (parts.length > 0) {
          const timeInfo = elapsedMs !== undefined ? `[${elapsedMs}ms]` : "";
          parts.forEach((part, partIndex) => {
            const rawData = {
              type: msg.type,
              request_id: requestId,
              event_type: eventType,
              part: part,
              author: author,
              elapsed_ms: elapsedMs,
              server_time: msg.server_time
            };
            
            chatManager.handleStreamingPart(requestId, part, {
              timeInfo,
              author: author,
              rawData,
              partIndex
            });
          });
          chatManager._finalizeStreamingGroup(requestId);
        }
      } else if (eventType === "error") {
        chatManager._finalizeStreamingGroup(requestId);
        const errorMsg = msg.error || "Unknown error";
        sys(`错误: ${errorMsg}`);
      }
      return;
    }

    if (type === "part") {
      const requestId = msg.request_id;
      const part = msg.part;
      const elapsedMs = msg.elapsed_ms;
      const eventTimestamp = msg.event_timestamp;
      const author = msg.author || "unknown";

      if (part) {
        const timeInfo = elapsedMs !== undefined ? `[${elapsedMs}ms]` : "";
        
        const rawData = {
          type: msg.type,
          request_id: requestId,
          part: part,
          author: author,
          elapsed_ms: elapsedMs,
          event_timestamp: eventTimestamp,
          server_time: msg.server_time
        };
        
        chatManager.handleStreamingPart(requestId, part, {
          timeInfo,
          author: author,
          rawData,
          partIndex: msg.part_index || 0
        });
      }
      return;
    }

    if (type === "message") {
      const requestId = msg.request_id;
      const node = state.pendingByRequestId.get(requestId);
      if (!node) return;
      const t = typeof msg.text === "string" ? msg.text : "";
      node.body.textContent += t;
      scrollToBottom();
      return;
    }

    sys(`收到消息：${JSON.stringify(msg).slice(0, 200)}`);
  };
}

function disconnect() {
  if (state.ws) {
    try {
      state.ws.close();
    } catch {}
    state.ws = null;
  }
  state.connected = false;
  state.connecting = false;
  setStatus("disconnected", "Disconnected");
  updateButtons();
}

function send(text) {
  if (!canSend()) return;
  const requestId = nextRequestId();
  const payload = {
    type: "message",
    request_id: requestId,
    text,
    mode: state.currentMode,
    run_mode: state.runMode || "stream",
    user_id: el.userId.value.trim() || undefined,
    session_id: el.sessionId.value.trim() || undefined,
  };
  state.ws.send(JSON.stringify(payload));
  chatManager.createMessage({ role: "user", text, requestId });
}

function sendModeChange(mode) {
  if (!canSend()) return;
  const payload = {
    type: "mode",
    mode,
  };
  state.ws.send(JSON.stringify(payload));
  sys(`已切换到 ${mode === "skill" ? "Skill" : "Agent"} 模式`);
}

const DEFAULT_API_BASE_URL = "https://localhost:8890";
const DEFAULT_WS_URL = "ws://127.0.0.1:8001/ws";
const DEFAULT_EMAIL = "Test@sparkx.com";
const DEFAULT_PASSWORD = "111";

function restoreFromStorage() {
  const apiToken = localStorage.getItem("apiToken");
  const apiUserId = localStorage.getItem("apiUserId");
  const apiEmail = localStorage.getItem("apiEmail");
  if (apiToken) {
    setAuth({ token: apiToken, userId: apiUserId, email: apiEmail });
  }

  const savedApiBaseUrl = localStorage.getItem("apiBaseUrl");
  if (savedApiBaseUrl) {
    el.apiBaseUrl.value = savedApiBaseUrl;
  } else {
    el.apiBaseUrl.value = DEFAULT_API_BASE_URL;
    localStorage.setItem("apiBaseUrl", DEFAULT_API_BASE_URL);
  }

  const savedWsUrl = localStorage.getItem("wsUrl");
  if (savedWsUrl) {
    el.wsUrl.value = savedWsUrl;
    el.wsUrlText.textContent = savedWsUrl;
  } else {
    el.wsUrl.value = DEFAULT_WS_URL;
    el.wsUrlText.textContent = DEFAULT_WS_URL;
    localStorage.setItem("wsUrl", DEFAULT_WS_URL);
  }

  const savedUserId = localStorage.getItem("userId");
  if (savedUserId) el.userId.value = savedUserId;

  const savedSessionId = localStorage.getItem("sessionId");
  if (savedSessionId) el.sessionId.value = savedSessionId;

  const savedProjectId = localStorage.getItem("projectId");
  if (savedProjectId) {
    el.projectId.value = savedProjectId;
    el.projectIdOut.value = savedProjectId;
  }

  const savedEmail = localStorage.getItem("email");
  if (savedEmail) {
    el.email.value = savedEmail;
  } else {
    el.email.value = DEFAULT_EMAIL;
    localStorage.setItem("email", DEFAULT_EMAIL);
  }

  const savedPassword = localStorage.getItem("password");
  if (savedPassword) {
    el.password.value = savedPassword;
  } else {
    el.password.value = DEFAULT_PASSWORD;
    localStorage.setItem("password", DEFAULT_PASSWORD);
  }

  const savedMode = localStorage.getItem("agentMode");
  if (savedMode && (savedMode === "agent" || savedMode === "skill")) {
    state.currentMode = savedMode;
    el.modeSelect.value = savedMode;
  }

  const savedRunMode = localStorage.getItem("runMode");
  if (savedRunMode && (savedRunMode === "stream" || savedRunMode === "async")) {
    state.runMode = savedRunMode;
    if (el.runModeSelect) el.runModeSelect.value = savedRunMode;
  }

  updateStats();
}

function bindEvents() {
  console.log("bindEvents called, loginBtn:", el.loginBtn);
  
  if (el.loginBtn) {
    el.loginBtn.addEventListener("click", (e) => {
      console.log("Login button clicked");
      login();
    });
  } else {
    console.error("loginBtn not found!");
  }
  
  if (el.logoutBtn) el.logoutBtn.addEventListener("click", logout);
  if (el.connectBtn) el.connectBtn.addEventListener("click", connect);
  if (el.disconnectBtn) el.disconnectBtn.addEventListener("click", disconnect);
  if (el.refreshBuildVersionsBtn) el.refreshBuildVersionsBtn.addEventListener("click", fetchBuildVersions);

  el.composer.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = el.text.value.trim();
    if (!text) return;
    send(text);
    el.text.value = "";
  });

  el.apiBaseUrl.addEventListener("change", () => {
    localStorage.setItem("apiBaseUrl", el.apiBaseUrl.value);
  });

  el.wsUrl.addEventListener("change", () => {
    localStorage.setItem("wsUrl", el.wsUrl.value);
    el.wsUrlText.textContent = el.wsUrl.value || "ws://127.0.0.1:8001/ws";
  });

  el.userId.addEventListener("change", () => {
    localStorage.setItem("userId", el.userId.value);
    updateStats();
  });

  el.sessionId.addEventListener("change", () => {
    localStorage.setItem("sessionId", el.sessionId.value);
    updateStats();
  });

  el.projectId.addEventListener("change", () => {
    localStorage.setItem("projectId", el.projectId.value);
    updateStats();
  });

  el.email.addEventListener("change", () => {
    localStorage.setItem("email", el.email.value);
  });

  el.password.addEventListener("change", () => {
    localStorage.setItem("password", el.password.value);
  });

  el.modeSelect.addEventListener("change", () => {
    const newMode = el.modeSelect.value;
    state.currentMode = newMode;
    localStorage.setItem("agentMode", newMode);
    if (state.connected) {
      sendModeChange(newMode);
    }
  });

  if (el.runModeSelect) {
    el.runModeSelect.addEventListener("change", () => {
      const newRunMode = el.runModeSelect.value;
      state.runMode = newRunMode;
      localStorage.setItem("runMode", newRunMode);
    });
  }
}

function init() {
  console.log("init called");
  
  chatManager = new ChatManager(el.messages);
  
  restoreFromStorage();
  bindEvents();
  updateButtons();
  updateAuthButtons();

  sys("Agent Chat 已就绪");
  sys("请先登录，然后连接 WebSocket");
  console.log("init completed");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
