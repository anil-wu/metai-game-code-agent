const MessageType = {
  TEXT: "text",
  THINKING: "thinking",
  TOOL_CALL: "tool_call",
  TOOL_RESPONSE: "tool_response",
  ERROR: "error",
  UNKNOWN: "unknown"
};

const MessageTypeConfig = {
  [MessageType.TEXT]: {
    icon: "💬",
    label: "文本",
    color: "#4CAF50",
    expandable: false,
    collapsible: false,
    showContent: true
  },
  [MessageType.THINKING]: {
    icon: "💭",
    label: "思考",
    color: "#888888",
    expandable: true,
    collapsible: true,
    showContent: true
  },
  [MessageType.TOOL_CALL]: {
    icon: "🔧",
    label: "函数调用",
    color: "#2196F3",
    expandable: false,
    collapsible: false,
    showContent: false
  },
  [MessageType.TOOL_RESPONSE]: {
    icon: "📤",
    label: "函数返回",
    color: "#00BCD4",
    expandable: false,
    collapsible: false,
    showContent: false
  },
  [MessageType.ERROR]: {
    icon: "❌",
    label: "错误",
    color: "#F44336",
    expandable: true,
    collapsible: true,
    showContent: true
  },
  [MessageType.UNKNOWN]: {
    icon: "❓",
    label: "未知",
    color: "#757575",
    expandable: true,
    collapsible: true,
    showContent: true
  }
};

function createExpandableMessageCard({ 
  type, 
  title, 
  summary, 
  details, 
  rawData = null,
  timeInfo = "",
  author = "",
  config = null
}) {
  config = config || MessageTypeConfig[type] || MessageTypeConfig[MessageType.UNKNOWN];
  
  const card = document.createElement("div");
  card.className = `msg-card msg-card--${type}`;
  
  const header = document.createElement("div");
  header.className = "msg-card__header";
  
  const icon = document.createElement("span");
  icon.className = "msg-card__icon";
  icon.textContent = config.icon;
  icon.style.color = config.color;
  
  const label = document.createElement("span");
  label.className = "msg-card__label";
  label.textContent = config.label;
  label.style.color = config.color;
  
  const titleEl = document.createElement("span");
  titleEl.className = "msg-card__title";
  titleEl.textContent = title || summary || "";
  
  const meta = document.createElement("span");
  meta.className = "msg-card__meta";
  if (timeInfo) meta.textContent += timeInfo;
  if (author) meta.textContent += (timeInfo ? " " : "") + `[${author}]`;
  
  header.appendChild(icon);
  header.appendChild(label);
  header.appendChild(titleEl);
  if (meta.textContent) header.appendChild(meta);
  
  let content = null;
  
  if (!config.showContent) {
    card.classList.add("msg-card--simple");
    card.appendChild(header);
    return { card, content };
  }
  
  if (config.collapsible && type === MessageType.THINKING) {
    card.classList.add("msg-card--collapsible");
    card.classList.add("msg-card--thinking");
    
    const expandBtn = document.createElement("button");
    expandBtn.className = "msg-card__expand-btn";
    expandBtn.innerHTML = "▶";
    header.appendChild(expandBtn);
    
    content = document.createElement("div");
    content.className = "msg-card__content msg-card__content--thinking";
    content.style.display = "none";
    
    if (details) {
      const detailsEl = document.createElement("pre");
      detailsEl.className = "msg-card__details msg-card__details--thinking";
      detailsEl.textContent = typeof details === "string" ? details : JSON.stringify(details, null, 2);
      content.appendChild(detailsEl);
    }
    
    header.onclick = () => {
      const isExpanded = content.style.display !== "none";
      content.style.display = isExpanded ? "none" : "block";
      expandBtn.innerHTML = isExpanded ? "▶" : "▼";
      card.classList.toggle("msg-card--expanded", !isExpanded);
    };
    
    card.appendChild(header);
    card.appendChild(content);
    return { card, content };
  }
  
  if (type === MessageType.TEXT) {
    card.classList.add("msg-card--text");
    
    if (details) {
      content = document.createElement("div");
      content.className = "msg-card__content msg-card__content--visible";
      const textEl = document.createElement("div");
      textEl.className = "msg-card__text";
      textEl.textContent = details;
      content.appendChild(textEl);
    }
    
    card.appendChild(header);
    if (content) card.appendChild(content);
    return { card, content };
  }
  
  if (config.expandable) {
    card.classList.add("msg-card--expandable");
    
    const expandBtn = document.createElement("button");
    expandBtn.className = "msg-card__expand-btn";
    expandBtn.innerHTML = "▼";
    header.appendChild(expandBtn);
    
    content = document.createElement("div");
    content.className = "msg-card__content";
    content.style.display = "none";
    
    if (details) {
      const detailsEl = document.createElement("pre");
      detailsEl.className = "msg-card__details";
      detailsEl.textContent = typeof details === "string" ? details : JSON.stringify(details, null, 2);
      content.appendChild(detailsEl);
    }
    
    if (rawData) {
      const rawDataBtn = document.createElement("button");
      rawDataBtn.className = "msg-card__raw-btn";
      rawDataBtn.textContent = "📋 查看原始数据";
      rawDataBtn.onclick = () => showDetailsModal(rawData);
      content.appendChild(rawDataBtn);
    }
    
    header.onclick = () => {
      const isExpanded = content.style.display !== "none";
      content.style.display = isExpanded ? "none" : "block";
      expandBtn.innerHTML = isExpanded ? "▼" : "▲";
      card.classList.toggle("msg-card--expanded", !isExpanded);
    };
    
    card.appendChild(header);
    card.appendChild(content);
    return { card, content };
  }
  
  if (details) {
    content = document.createElement("div");
    content.className = "msg-card__content msg-card__content--visible";
    const textEl = document.createElement("div");
    textEl.className = "msg-card__text";
    textEl.textContent = details;
    content.appendChild(textEl);
  }
  
  card.appendChild(header);
  if (content) card.appendChild(content);
  return { card, content };
}

function createPartMessageCard(part, { timeInfo = "", author = "", rawData = null, partIndex = 0 }) {
  const partType = part.message_type || "unknown";
  let type = MessageType.UNKNOWN;
  if (partType === "error") type = MessageType.ERROR;
  else if (partType === "function_call") type = MessageType.TOOL_CALL;
  else if (partType === "function_response") type = MessageType.TOOL_RESPONSE;
  else if (partType === "thinking") type = MessageType.THINKING;
  else if (partType === "message") type = MessageType.TEXT;
  
  const config = MessageTypeConfig[type];
  
  let title = "";
  let summary = "";
  let details = "";
  
  switch (type) {
    case MessageType.TEXT:
      const text = part.text || "";
      title = config.label;
      summary = text.slice(0, 50);
      details = text;
      break;
      
    case MessageType.THINKING:
      title = config.label;
      summary = config.label + "...";
      details = part.text || "";
      break;
      
    case MessageType.TOOL_CALL:
      const fc = part.function_call || {};
      const fcName = fc.name || "unknown";
      title = `${config.icon} ${config.label}: ${fcName}`;
      summary = fcName;
      details = "";
      break;
      
    case MessageType.TOOL_RESPONSE:
      const fr = part.function_response || {};
      const frName = fr.name || "unknown";
      title = `${config.icon} ${config.label}: ${frName}`;
      summary = frName;
      details = "";
      break;
      
    case MessageType.ERROR:
      const errMsg = part.error_message || `Error code: ${part.error_code}` || "Unknown error";
      title = config.label;
      summary = errMsg.slice(0, 50);
      details = errMsg;
      break;
      
    case MessageType.UNKNOWN:
    default:
      title = config.label;
      summary = "未知消息类型";
      details = JSON.stringify(part, null, 2);
      break;
  }
  
  return createExpandableMessageCard({
    type,
    title,
    summary,
    details,
    rawData,
    timeInfo,
    author,
    config
  });
}

function createEventMessageCard(event, { timeInfo = "", author = "", rawData = null }) {
  const type = _getEventType(event);
  const config = MessageTypeConfig[type];
  
  let title = "";
  let summary = "";
  let details = "";
  
  switch (type) {
    case MessageType.TEXT:
      summary = _extractText(event).slice(0, 50);
      details = _extractText(event);
      break;
      
    case MessageType.THINKING:
      summary = "思考中...";
      details = _extractThinking(event);
      break;
      
    case MessageType.TOOL_CALL:
      const calls = _extractFunctionCalls(event);
      summary = calls.join(", ").slice(0, 50) || "调用工具";
      details = calls.join("\n");
      break;
      
    case MessageType.TOOL_RESPONSE:
      const responses = _extractFunctionResponses(event);
      summary = responses.join(", ").slice(0, 50) || "工具返回";
      details = responses.join("\n");
      break;
      
    case MessageType.ERROR:
      summary = _extractError(event).slice(0, 50);
      details = _extractError(event);
      break;
      
    case MessageType.UNKNOWN:
    default:
      summary = "未知消息类型";
      details = JSON.stringify(event, null, 2);
      break;
  }
  
  return createExpandableMessageCard({
    type,
    title,
    summary,
    details,
    rawData,
    timeInfo,
    author
  });
}

function showDetailsModal(data) {
  const overlay = document.createElement("div");
  overlay.className = "details-overlay";

  const modal = document.createElement("div");
  modal.className = "details-modal";

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

  const content = document.createElement("div");
  content.className = "details-content";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(data, null, 2);
  content.appendChild(pre);

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

  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.remove();
  };
}

function _getEventType(event) {
  if (!event) return MessageType.UNKNOWN;

  if (event.message_type) {
    const serverType = event.message_type;
    if (serverType === "error") return MessageType.ERROR;
    if (serverType === "function_call") return MessageType.TOOL_CALL;
    if (serverType === "function_response") return MessageType.TOOL_RESPONSE;
    if (serverType === "thinking") return MessageType.THINKING;
    if (serverType === "message") return MessageType.TEXT;
  }

  const content = event.content || {};
  const parts = content.parts || [];

  if (event.error_code || event.error_message) return MessageType.ERROR;

  for (const part of parts) {
    if (part.function_call) return MessageType.TOOL_CALL;
  }

  for (const part of parts) {
    if (part.function_response) return MessageType.TOOL_RESPONSE;
  }

  for (const part of parts) {
    const text = part.text;
    const thought = part.thought;
    if (text && thought) return MessageType.THINKING;
  }

  for (const part of parts) {
    const text = part.text;
    const thought = part.thought;
    if (text && !thought) return MessageType.TEXT;
  }

  return MessageType.UNKNOWN;
}

function _extractFunctionCalls(event) {
  const calls = [];
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.function_call) {
      const name = part.function_call.name || "unknown";
      const args = part.function_call.args || {};
      const argStr = Object.keys(args).length > 0
        ? JSON.stringify(args)
        : "()";
      calls.push(`${name}(${argStr})`);
    }
  }
  return calls;
}

function _extractFunctionResponses(event) {
  const responses = [];
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    if (part.function_response) {
      const name = part.function_response.name || "unknown";
      const response = part.function_response.response;
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

function _extractText(event) {
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    const text = part.text;
    const thought = part.thought;
    if (text && !thought) return text;
  }
  return "";
}

function _extractThinking(event) {
  const content = event.content || {};
  const parts = content.parts || [];
  for (const part of parts) {
    const text = part.text;
    const thought = part.thought;
    if (text && thought) return text;
  }
  return "";
}

function _extractError(event) {
  if (event.error_message) return event.error_message;
  if (event.error_code) return `Error code: ${event.error_code}`;
  return "Unknown error";
}

function formatTimeInfo(serverTime, elapsedMs) {
  if (!serverTime) {
    return elapsedMs !== undefined ? `[${elapsedMs}ms]` : "";
  }
  const date = new Date(serverTime);
  const timeStr = date.toLocaleTimeString();
  return elapsedMs !== undefined ? `${timeStr} [${elapsedMs}ms]` : timeStr;
}

function parseContentByType(messageType, content) {
  switch (messageType) {
    case "function_call":
      try {
        return { function_call: JSON.parse(content) };
      } catch {
        return { function_call: { name: "unknown", args: {} } };
      }
    case "function_response":
      try {
        return { function_response: JSON.parse(content) };
      } catch {
        return { function_response: { name: "unknown", response: content } };
      }
    case "thinking":
      return { text: content, thought: true };
    case "message":
    case "text":
      return { text: content };
    case "error":
      return { error_message: content };
    default:
      return {};
  }
}

class ChatManager {
  constructor(messagesContainer) {
    this.messagesContainer = messagesContainer;
    this.streamingGroups = new Map();
    this.messageBuffers = new Map();
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  createMessage({ role, text, requestId, rawData = null }) {
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
    pillTime.textContent = this._nowLabel();

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

    if (rawData) {
      const detailsBtn = document.createElement("button");
      detailsBtn.className = "details-btn";
      detailsBtn.textContent = "📋 详情";
      detailsBtn.onclick = () => showDetailsModal(rawData);
      root.appendChild(detailsBtn);
    }

    this.messagesContainer.appendChild(root);
    this.scrollToBottom();
    return { root, body };
  }

  sys(text, rawData = null) {
    this.createMessage({ role: "system", text, rawData });
  }

  handleStreamingPart(requestId, part, { timeInfo = "", author = "", rawData = null, partIndex = 0 }) {
    const partType = part.message_type || "unknown";
    const isTextMessage = partType === "message";

    let group = this.streamingGroups.get(requestId);

    if (!group) {
      group = this._createStreamingGroup(requestId, author, timeInfo);
      this.streamingGroups.set(requestId, group);
      this.messagesContainer.appendChild(group.container);
      this._startStreamingGroupTimeout(requestId);
    }

    if (isTextMessage && part.text) {
      this._appendStreamingText(group, part.text);
    } else {
      const { card } = createPartMessageCard(part, { timeInfo, author, rawData, partIndex });
      group.content.appendChild(card);
    }

    group.lastUpdateTime = Date.now();
    this.scrollToBottom();
  }

  handleEventMessage(event) {
    const { 
      request_id, 
      message_type, 
      content, 
      message_id, 
      author, 
      server_time, 
      elapsed_ms 
    } = event;
    
    if (message_type === "completed") {
      this._finalizeStreamingGroup(message_id);
      this.messageBuffers.clear();
      return;
    }
    
    const timeInfo = formatTimeInfo(server_time, elapsed_ms);
    
    if (message_type === "message" || message_type === "thinking") {
      this._handleTextMessage(message_id, content, author, timeInfo, event);
    } else {
      this._handleNonTextMessage(message_id, message_type, content, author, timeInfo, event);
    }
  }

  _handleTextMessage(messageId, content, author, timeInfo, rawData) {
    let group = this.streamingGroups.get(messageId);
    
    if (!group) {
      group = this._createStreamingGroup(messageId, author, timeInfo);
      this.streamingGroups.set(messageId, group);
      this.messagesContainer.appendChild(group.container);
      this._startStreamingGroupTimeout(messageId);
    }
    
    this._updateStreamingText(group, content);
    group.lastUpdateTime = Date.now();
    this.scrollToBottom();
  }

  _handleNonTextMessage(messageId, messageType, content, author, timeInfo, rawData) {
    let group = this.streamingGroups.get(messageId);
    
    if (!group) {
      group = this._createStreamingGroup(messageId, author, timeInfo);
      this.streamingGroups.set(messageId, group);
      this.messagesContainer.appendChild(group.container);
      this._startStreamingGroupTimeout(messageId);
    }
    
    const part = {
      message_type: messageType,
      ...parseContentByType(messageType, content)
    };
    
    const { card } = createPartMessageCard(part, { timeInfo, author, rawData });
    group.content.appendChild(card);
    
    group.lastUpdateTime = Date.now();
    this.scrollToBottom();
  }

  _createStreamingGroup(messageId, author, timeInfo) {
    const container = document.createElement("div");
    container.className = "msg-group msg-group--streaming";
    container.dataset.messageId = messageId;
    
    const header = document.createElement("div");
    header.className = "msg-group__header";
    
    const authorEl = document.createElement("span");
    authorEl.className = "msg-group__author";
    authorEl.textContent = author;
    
    const metaEl = document.createElement("span");
    metaEl.className = "msg-group__meta";
    metaEl.textContent = timeInfo;
    
    const indicator = document.createElement("span");
    indicator.className = "streaming-indicator";
    indicator.innerHTML = "<span></span><span></span><span></span>";
    
    header.appendChild(authorEl);
    header.appendChild(metaEl);
    header.appendChild(indicator);
    
    const content = document.createElement("div");
    content.className = "msg-group__content";
    
    const textContainer = document.createElement("div");
    textContainer.className = "streaming-text-container";
    
    content.appendChild(textContainer);
    container.appendChild(header);
    container.appendChild(content);
    
    return {
      container,
      content,
      textContainer,
      textBuffer: "",
      lastUpdateTime: Date.now(),
      messageId
    };
  }

  _updateStreamingText(group, text) {
    let textEl = group.textContainer.querySelector(".streaming-text");
    if (!textEl) {
      textEl = document.createElement("div");
      textEl.className = "streaming-text";
      group.textContainer.appendChild(textEl);
    }
    
    textEl.textContent = text;
    
    const indicator = group.container.querySelector(".streaming-indicator");
    if (indicator) {
      indicator.classList.add("active");
    }
  }

  _appendStreamingText(group, text) {
    group.textBuffer += text;
    this._updateStreamingText(group, group.textBuffer);
  }

  _finalizeStreamingGroup(messageId) {
    const group = this.streamingGroups.get(messageId);
    if (group) {
      group.container.classList.remove("msg-group--streaming");
      group.container.classList.add("msg-group--completed");
      
      const indicator = group.container.querySelector(".streaming-indicator");
      if (indicator) {
        indicator.remove();
      }
      
      if (group.checkInterval) {
        clearInterval(group.checkInterval);
      }
      
      this.streamingGroups.delete(messageId);
    }
  }

  _startStreamingGroupTimeout(messageId, timeoutMs = 2000) {
    const group = this.streamingGroups.get(messageId);
    if (!group) return;
    
    if (group.checkInterval) {
      clearInterval(group.checkInterval);
    }
    
    group.checkInterval = setInterval(() => {
      const now = Date.now();
      if (now - group.lastUpdateTime > timeoutMs) {
        this._finalizeStreamingGroup(messageId);
      }
    }, 500);
  }

  _nowLabel() {
    const d = new Date();
    return d.toLocaleTimeString();
  }

  clear() {
    this.messagesContainer.innerHTML = "";
    this.streamingGroups.clear();
    this.messageBuffers.clear();
  }
}

export { 
  MessageType, 
  MessageTypeConfig, 
  ChatManager,
  createExpandableMessageCard,
  createPartMessageCard,
  createEventMessageCard,
  showDetailsModal,
  formatTimeInfo,
  parseContentByType,
  _getEventType,
  _extractFunctionCalls,
  _extractFunctionResponses,
  _extractText,
  _extractThinking,
  _extractError
};
