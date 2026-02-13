const el = {
  status: document.getElementById("status"),
  authStatus: document.getElementById("authStatus"),
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  wsUrl: document.getElementById("wsUrl"),
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

function scrollToBottom() {
  el.messages.scrollTop = el.messages.scrollHeight;
}

function createMessage({ role, text, requestId }) {
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
    pillReq.textContent = requestId;
    meta.appendChild(pillReq);
  }

  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text || "";

  root.appendChild(meta);
  root.appendChild(body);
  el.messages.appendChild(root);
  scrollToBottom();
  return { root, body };
}

function sys(text) {
  createMessage({ role: "system", text });
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

  updateAuthButtons();
  if (state.auth.token) {
    const suffix = state.auth.token.slice(-6);
    setAuthStatus("connected", `Logged In • …${suffix}`);
  } else {
    setAuthStatus("disconnected", "Not Logged In");
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

async function fetchUserProfile() {
  if (!state.auth.token) return null;
  try {
    const { res, data, text } = await apiJson("/api/v1/admin/profile", { method: "GET" });
    if (!res.ok) {
      const detail = data?.message || data?.msg || text || `HTTP ${res.status}`;
      sys(`获取用户信息失败：${detail}`);
      return null;
    }
    return data;
  } catch (e) {
    sys(`获取用户信息请求失败：${e?.message || String(e)}`);
    return null;
  }
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
  const profile = await fetchUserProfile();
  if (profile && profile.id != null) {
    setAuth({
      token: state.auth.token,
      userId: profile.id,
      email: state.auth.email,
    });
  }
  await fetchAvailableAgents();
}

async function login() {
  const baseUrl = getApiBaseUrl();
  const email = el.email.value.trim();
  const password = el.password.value;
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
  if (!token) {
    sys("请先登录获取 token，再连接 WebSocket");
    state.connected = false;
    state.connecting = false;
    setStatus("disconnected", "Disconnected");
    updateButtons();
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
    sys(`已连接：${baseUrl}`);
    if (token) {
      try {
        ws.send(
          JSON.stringify({
            type: "auth",
            token,
            project_id: projectId,
            user_id: el.userId.value.trim() || null,
          })
        );
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

  ws.onmessage = (ev) => {
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
      }
      sys("Token 已发送到服务器");
      return;
    }

    if (type === "task_update") {
      const requestId = msg.request_id;
      const status = msg.status;
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

    if (type === "error") {
      const rid = msg.request_id ? ` (${msg.request_id})` : "";
      const detail = msg.message || msg.error || "unknown_error";
      sys(`错误${rid}：${detail}`);
      return;
    }
  };
}

function disconnect() {
  if (!state.ws) return;
  try {
    state.ws.close();
  } catch {}
}

function sendText(text) {
  if (!canSend()) return;
  const trimmed = text.trim();
  if (!trimmed) return;

  const requestId = nextRequestId();
  const payload = {
    type: "message",
    user_id: el.userId.value.trim() || "default",
    session_id: el.sessionId.value.trim() || "default",
    request_id: requestId,
    text: trimmed,
  };

  createMessage({ role: "user", text: trimmed, requestId });
  state.ws.send(JSON.stringify(payload));
}

function init() {
  el.apiBaseUrl.value = localStorage.getItem("apiBaseUrl") || "https://localhost:8890";
  const savedEmail = localStorage.getItem("apiEmail");
  el.email.value = savedEmail && savedEmail !== "abluysky@gmail.com" ? savedEmail : "Test@sparkx.come";
  el.password.value = "111";
  el.wsUrl.value = localStorage.getItem("wsUrl") || "ws://127.0.0.1:8001/ws";
  el.userId.value = localStorage.getItem("userId") || "u1";
  el.sessionId.value = localStorage.getItem("sessionId") || "s1";
  el.projectId.value = localStorage.getItem("projectId") || "";
  el.projectIdOut.value = el.projectId.value;

  el.apiBaseUrl.addEventListener("change", () => localStorage.setItem("apiBaseUrl", getApiBaseUrl()));
  el.email.addEventListener("change", () => localStorage.setItem("apiEmail", el.email.value.trim()));

  el.wsUrl.addEventListener("change", () => localStorage.setItem("wsUrl", el.wsUrl.value.trim()));
  el.userId.addEventListener("change", () => localStorage.setItem("userId", el.userId.value.trim()));
  el.sessionId.addEventListener("change", () => localStorage.setItem("sessionId", el.sessionId.value.trim()));
  el.projectId.addEventListener("change", () => {
    const value = el.projectId.value.trim();
    localStorage.setItem("projectId", value);
    el.projectIdOut.value = value;
  });

  el.loginBtn.addEventListener("click", () => login());
  el.logoutBtn.addEventListener("click", () => logout());

  el.connectBtn.addEventListener("click", () => connect());
  el.disconnectBtn.addEventListener("click", () => disconnect());

  el.composer.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = el.text.value;
    el.text.value = "";
    sendText(text);
    el.text.focus();
  });

  const existingToken = localStorage.getItem("apiToken");
  const existingUserId = localStorage.getItem("apiUserId");
  if (existingToken) {
    setAuth({
      token: existingToken,
      userId: existingUserId != null ? Number(existingUserId) : null,
      email: el.email.value.trim() || null,
    });
    refreshAfterAuth();
  } else {
    setAuth({ token: null, userId: null, email: el.email.value.trim() || null });
  }

  setStatus("disconnected", "Disconnected");
  updateButtons();

  if (state.auth.token) connect();
}

init();
