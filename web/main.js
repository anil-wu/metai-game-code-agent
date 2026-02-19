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
  auth: {
    token: null,
    userId: null,
    email: null,
  },
};

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

function createMessage({ role, text, requestId, rawData = null }) {
  const root = document.createElement("div");
  root.className = `msg msg--${role}`;
  root.dataset.requestId = requestId || "";

  const meta = document.createElement("div");
  meta.className = "meta";

  const pillRole = document.createElement("span");
  pillRole.className = "pill";
  pillRole.textContent = role;

  const pillTime = document.createElement("span");
  pillTime.className = "pill";
  pillTime.textContent = nowLabel();

  meta.appendChild(pillRole);
  meta.appendChild(pillTime);

  if (requestId) {
    const pillReq = document.createElement("span");
    pillReq.className = "pill";
    pillReq.textContent = requestId.slice(0, 8);
    meta.appendChild(pillReq);
  }

  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text || "";

  root.appendChild(meta);
  root.appendChild(body);

  // 如果有原始数据，添加查看详情按钮
  if (rawData) {
    const detailsBtn = document.createElement("button");
    detailsBtn.className = "details-btn";
    detailsBtn.textContent = "📋 详情";
    detailsBtn.onclick = () => showDetailsModal(rawData);
    root.appendChild(detailsBtn);
  }

  el.messages.appendChild(root);
  scrollToBottom();
  return { root, body };
}

// 显示详情弹窗
function showDetailsModal(data) {
  // 创建弹窗遮罩
  const overlay = document.createElement("div");
  overlay.className = "details-overlay";

  // 创建弹窗内容
  const modal = document.createElement("div");
  modal.className = "details-modal";

  // 弹窗头部
  const header = document.createElement("div");
  header.className = "details-header";
  const title = document.createElement("span");
  title.className = "details-title";
  title.textContent = "消息详情";
  const closeBtn = document.createElement("button");
  closeBtn.className = "details-close";
  closeBtn.textContent = "✕";
  closeBtn.onclick = () => overlay.remove();
  header.appendChild(title);
  header.appendChild(closeBtn);

  // 弹窗内容区域
  const content = document.createElement("div");
  content.className = "details-content";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(data, null, 2);
  content.appendChild(pre);

  // 弹窗底部
  const footer = document.createElement("div");
  footer.className = "details-footer";
  const copyBtn = document.createElement("button");
  copyBtn.className = "btn btn--secondary";
  copyBtn.textContent = "📋 复制";
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    copyBtn.textContent = "✓ 已复制";
    setTimeout(() => copyBtn.textContent = "📋 复制", 2000);
  };
  const closeBtn2 = document.createElement("button");
  closeBtn2.className = "btn btn--secondary";
  closeBtn2.textContent = "关闭";
  closeBtn2.onclick = () => overlay.remove();
  footer.appendChild(copyBtn);
  footer.appendChild(closeBtn2);

  modal.appendChild(header);
  modal.appendChild(content);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // 点击遮罩关闭
  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.remove();
  };
}

function sys(text, rawData = null) {
  createMessage({ role: "system", text, rawData });
}

// 辅助函数：获取事件类型
function _getEventType(event) {
  if (!event) return "unknown";

  // 检查是否是 function call
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.function_call) return "function_call";
    if (part.function_response) return "function_response";
  }

  // 检查是否是 agent 切换
  if (event.actions?.transfer_to_agent) return "agent_transfer";

  // 检查是否是错误
  if (event.error_code || event.error_message) return "error";

  // 检查是否是文本内容
  for (const part of parts) {
    if (part.text) return "text";
  }

  return "other";
}

// 辅助函数：提取 function calls（包含参数）
function _extractFunctionCalls(event) {
  const calls = [];
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.function_call) {
      const name = part.function_call.name || "unknown";
      const args = part.function_call.args || {};
      // 格式化参数
      const argStr = Object.keys(args).length > 0
        ? JSON.stringify(args)
        : "()";
      calls.push(`${name}(${argStr})`);
    }
  }
  return calls;
}

// 辅助函数：提取 function responses（包含返回值）
function _extractFunctionResponses(event) {
  const responses = [];
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.function_response) {
      const name = part.function_response.name || "unknown";
      const response = part.function_response.response;
      // 格式化返回值
      let resultStr = "";
      if (response !== undefined) {
        if (typeof response === "object") {
          resultStr = JSON.stringify(response);
        } else {
          resultStr = String(response);
        }
      }
      responses.push(`${name} → ${resultStr || "void"}`);
    }
  }
  return responses;
}

// 辅助函数：提取文本内容
function _extractText(event) {
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.text) return part.text;
  }
  return "";
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
  // 移除末尾的斜杠
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

  // 更新用户邮箱显示
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
  
  // 调试日志
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

    const type = msg.type;
    if (type === "pong") return;
    if (type === "auth_ok") {
      const pid = typeof msg.project_id === "string" ? msg.project_id : "";
      if (pid) {
        el.projectIdOut.value = pid;
        el.projectId.value = pid;
        localStorage.setItem("projectId", pid);
        updateStats();
        // WebSocket 认证成功后获取构建版本
        await fetchBuildVersions();
      }
      sys("Token 已发送到服务器");
      return;
    }

    if (type === "task_update") {
      const requestId = msg.request_id;
      const status = msg.status;
      const event = msg.event;
      const elapsedMs = msg.elapsed_ms;
      const eventTimestamp = msg.event_timestamp;

      // 显示所有事件详情（用于调试分析）
      if (event) {
        const eventType = _getEventType(event);
        const eventAuthor = event.author || "unknown";
        const timeInfo = elapsedMs !== undefined ? `[${elapsedMs}ms]` : "";
        const eventTime = eventTimestamp ? new Date(eventTimestamp).toLocaleTimeString() : "";

        // 构建事件描述
        let eventDesc = "";
        if (eventType === "function_call") {
          const calls = _extractFunctionCalls(event);
          eventDesc = `🔧 调用工具: ${calls.join(", ")}`;
        } else if (eventType === "function_response") {
          const responses = _extractFunctionResponses(event);
          eventDesc = `✅ 工具返回: ${responses.join(", ")}`;
        } else if (eventType === "agent_transfer") {
          const transfer = event.actions?.transfer_to_agent;
          eventDesc = `🔄 切换到 Agent: ${transfer || "unknown"}`;
        } else if (eventType === "text") {
          const text = _extractText(event);
          if (text) eventDesc = `💬 ${text}`;
        } else if (eventType === "error") {
          eventDesc = `❌ 错误: ${event.error_message || event.error_code || "unknown"}`;
        } else {
          eventDesc = `📦 ${eventType}`;
        }

        if (eventDesc) {
          // 构建完整的原始数据对象
          const rawData = {
            type: msg.type,
            request_id: requestId,
            status: status,
            event: event,
            elapsed_ms: elapsedMs,
            event_timestamp: eventTimestamp,
            server_time: msg.server_time
          };
          sys(`${timeInfo} [${eventAuthor}] ${eventDesc}`, rawData);
        }
      }

      if (status === "start") {
        const node = createMessage({ role: "assistant", text: "", requestId });
        state.pendingByRequestId.set(requestId, node);
        return;
      }
      if (status === "done") {
        state.pendingByRequestId.delete(requestId);
        return;
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

    // 兜底：展示原始消息
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
    user_id: el.userId.value.trim() || undefined,
    session_id: el.sessionId.value.trim() || undefined,
  };
  state.ws.send(JSON.stringify(payload));
  createMessage({ role: "user", text, requestId });
}

// 默认配置
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
    // 首次加载，使用默认值
    el.apiBaseUrl.value = DEFAULT_API_BASE_URL;
    localStorage.setItem("apiBaseUrl", DEFAULT_API_BASE_URL);
  }

  const savedWsUrl = localStorage.getItem("wsUrl");
  if (savedWsUrl) {
    el.wsUrl.value = savedWsUrl;
    el.wsUrlText.textContent = savedWsUrl;
  } else {
    // 首次加载，使用默认值
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
    // 首次加载，使用默认邮箱
    el.email.value = DEFAULT_EMAIL;
    localStorage.setItem("email", DEFAULT_EMAIL);
  }

  const savedPassword = localStorage.getItem("password");
  if (savedPassword) {
    el.password.value = savedPassword;
  } else {
    // 首次加载，使用默认密码
    el.password.value = DEFAULT_PASSWORD;
    localStorage.setItem("password", DEFAULT_PASSWORD);
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

  // 监听输入变化，保存到 localStorage
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
}

function init() {
  console.log("init called");
  restoreFromStorage();
  bindEvents();
  updateButtons();
  updateAuthButtons();

  // 添加初始系统消息
  sys("Agent Chat 已就绪");
  sys("请先登录，然后连接 WebSocket");
  console.log("init completed");
}

// 确保 DOM 加载完成后再初始化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
