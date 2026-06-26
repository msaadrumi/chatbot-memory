const API_BASE = "/api";

let conversations = [];
let activeConvId = null;
let isSending = false;

const $ = id => document.getElementById(id);

const messagesContainer = $("messages");
const welcomeEl = $("welcome");
const inputEl = $("messageInput");
const sendBtn = $("sendBtn");
const typingIndicator = $("typingIndicator");
const statsBtn = $("statsBtn");
const statsModal = $("statsModal");
const closeStatsBtn = $("closeStatsBtn");
const micBtn = $("micBtn");
const loginPrompt = $("loginPrompt");
const chatView = $("chatView");
const inputArea = $("inputArea");
const googleSignInBtn = $("googleSignInBtn");
const userBadge = $("userBadge");
const badgeAvatar = $("badgeAvatar");
const badgeName = $("badgeName");
const menuBtn = $("menuBtn");
const sidebar = $("sidebar");
const userAvatar = $("userAvatar");
const userName = $("userName");
const userEmail = $("userEmail");
const conversationList = $("conversationList");
const newChatSidebarBtn = $("newChatSidebarBtn");
const logoutBtn = $("logoutBtn");
const googleSignInPrompt = $("googleSignInPrompt");

menuBtn?.addEventListener("click", () => {
  sidebar?.classList.toggle("hidden");
});

initOffline();

async function initOffline() {
  googleSignInBtn?.classList.add("hidden");
  if (googleSignInPrompt) googleSignInPrompt.classList.add("hidden");
  userBadge?.classList.remove("hidden");
  if (badgeName) badgeName.textContent = "Local User";
  if (userName) userName.textContent = "Local User";
  if (userEmail) userEmail.textContent = "offline mode";

  loginPrompt?.classList.add("hidden");
  chatView?.classList.remove("hidden");
  inputArea?.classList.remove("hidden");

  await loadConversations();
  if (conversations.length > 0) {
    loadConversation(conversations[0].id);
  } else {
    startNewChat();
  }
}

logoutBtn?.addEventListener("click", () => {
  conversations = [];
  activeConvId = null;
  messagesContainer.innerHTML = "";
  initOffline();
});

function renderConversations() {
  if (!conversationList) return;
  conversationList.innerHTML = "";
  for (const conv of conversations) {
    const el = document.createElement("div");
    el.className = "conv-item" + (conv.id === activeConvId ? " active" : "");
    el.textContent = conv.title || "New Chat";
    el.addEventListener("click", () => loadConversation(conv.id));
    conversationList.appendChild(el);
  }
}

async function loadConversations() {
  try {
    const res = await fetch(`${API_BASE}/conversations`);
    if (res.ok) {
      const data = await res.json();
      conversations = data.conversations || [];
    }
  } catch {}
}

async function loadConversation(convId) {
  try {
    const res = await fetch(`${API_BASE}/conversations/${convId}`);
    if (!res.ok) throw new Error("Failed to load");
    const data = await res.json();
    activeConvId = convId;
    messagesContainer.innerHTML = "";
    if (welcomeEl) welcomeEl.style.display = "none";
    for (const msg of data.messages) {
      if (msg.role === "user" || msg.role === "assistant") {
        addMessage(msg.content, msg.role);
      }
    }
    renderConversations();
  } catch {
    showError("Could not load conversation");
  }
}

async function startNewChat() {
  try {
    const res = await fetch(`${API_BASE}/conversations`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create");
    const data = await res.json();
    activeConvId = data.conversation_id;
    messagesContainer.innerHTML = "";
    if (welcomeEl) welcomeEl.style.display = "block";
    const conv = { id: data.conversation_id, title: "New Chat" };
    conversations.unshift(conv);
    renderConversations();
    inputEl?.focus();
  } catch {
    showError("Could not create conversation");
  }
}

newChatSidebarBtn?.addEventListener("click", startNewChat);

inputEl?.addEventListener("input", () => {
  sendBtn.disabled = !inputEl.value.trim();
});

inputEl?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn?.addEventListener("click", sendMessage);
statsBtn?.addEventListener("click", showStats);
closeStatsBtn?.addEventListener("click", () => statsModal?.classList.add("hidden"));
statsModal?.addEventListener("click", (e) => {
  if (e.target === statsModal) statsModal?.classList.add("hidden");
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition && micBtn) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onresult = (e) => {
    const transcript = e.results[e.results.length - 1][0].transcript;
    if (e.results[e.results.length - 1].isFinal) {
      inputEl.value = transcript;
      sendBtn.disabled = false;
      sendMessage();
    }
  };

  recognition.onend = () => {
    micBtn.classList.remove("listening");
    isListening = false;
    inputEl?.focus();
  };

  recognition.onerror = (e) => {
    micBtn.classList.remove("listening");
    isListening = false;
    if (e.error === "not-allowed") {
      showError("Microphone access denied. Allow mic permission and try again.");
    } else if (e.error === "no-speech") {
      showError("No speech detected. Try again.");
    } else if (e.error === "audio-capture") {
      showError("No microphone found. Check your audio device.");
    }
  };

  micBtn.addEventListener("click", async () => {
    if (isListening) {
      recognition.stop();
      micBtn.classList.remove("listening");
      isListening = false;
      return;
    }
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      recognition.start();
      micBtn.classList.add("listening");
      isListening = true;
    } catch (err) {
      micBtn.classList.remove("listening");
      isListening = false;
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        showError("Microphone access denied. Allow mic permission and try again.");
      } else {
        showError("Microphone not available. Check your audio device.");
      }
    }
  });
} else if (micBtn) {
  micBtn.style.opacity = "0.2";
  micBtn.style.cursor = "not-allowed";
  micBtn.title = "Voice input not supported in this browser";
}

async function sendMessage() {
  const text = inputEl?.value.trim();
  if (!text || isSending) return;

  if (text === "/new") {
    await startNewChat();
    return;
  }

  if (text === "/history") {
    await showStats();
    if (inputEl) { inputEl.value = ""; sendBtn.disabled = true; }
    return;
  }

  if (inputEl) inputEl.value = "";
  sendBtn.disabled = true;
  isSending = true;

  if (welcomeEl) welcomeEl.style.display = "none";
  addMessage(text, "user");

  typingIndicator?.classList.remove("hidden");
  scrollToBottom();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: activeConvId }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Error ${res.status}`);
    }

    const data = await res.json();
    activeConvId = data.conversation_id;

    typingIndicator?.classList.add("hidden");
    addMessage(data.reply, "assistant");
    refreshConversations();
  } catch (err) {
    typingIndicator?.classList.add("hidden");
    showError(err.message);
  }

  isSending = false;
  inputEl?.focus();
}

async function refreshConversations() {
  try {
    const res = await fetch(`${API_BASE}/conversations`);
    if (res.ok) {
      const data = await res.json();
      conversations = data.conversations;
      renderConversations();
    }
  } catch {}
}

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "U" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "assistant") {
    bubble.innerHTML = formatMarkdown(text);
  } else {
    bubble.textContent = text;
  }

  div.appendChild(avatar);
  div.appendChild(bubble);
  messagesContainer?.appendChild(div);
  scrollToBottom();
}

function formatMarkdown(text) {
  let html = escapeHtml(text);

  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  const blocks = html.split(/\n\n+/);
  const result = blocks.map((block) => {
    block = block.trim();
    if (!block) return "";
    if (block.startsWith("<pre>") || block.startsWith("<code>")) {
      return block;
    }
    block = block.replace(/^#{3}\s+(.+)$/gm, "<b>$1</b>");
    block = block.replace(/^#{2}\s+(.+)$/gm, "<b>$1</b>");
    block = block.replace(/^#{1}\s+(.+)$/gm, "<b>$1</b>");
    block = block.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    block = block.replace(/\*(.+?)\*/g, "<i>$1</i>");
    block = block.replace(/^- (.+)$/gm, "• $1");
    block = block.replace(/^\d+\.\s+(.+)$/gm, (m, c) => c);
    return `<p>${block}</p>`;
  }).join("");

  return result;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function showStats() {
  if (!activeConvId) {
    showError("No active conversation");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/conversations/${activeConvId}`);
    if (!res.ok) throw new Error("No stats available");
    const data = await res.json();
    const msgs = data.messages || [];
    const userMsgs = msgs.filter(m => m.role === "user" || m.role === "assistant");
    if ($("statMessages")) $("statMessages").textContent = userMsgs.length;
    if ($("statTokens")) $("statTokens").textContent = "~" + (userMsgs.length * 50);
    if ($("statMaxTokens")) $("statMaxTokens").textContent = "4000";
    statsModal?.classList.remove("hidden");
  } catch {
    showError("Could not load stats");
  }
}

function showError(msg) {
  const toast = document.createElement("div");
  toast.className = "error-toast";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function scrollToBottom() {
  const chatArea = $("chatArea");
  if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
}
