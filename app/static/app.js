const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user-row";
  row.innerHTML = `
    <div class="avatar">👤</div>
    <div class="message-bubble user-bubble">
      <div class="message-text">${escapeHtml(text)}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function showTypingIndicator() {
  const id = "typing-" + Date.now();
  const row = document.createElement("div");
  row.className = "message-row agent-row";
  row.id = id;
  row.innerHTML = `
    <div class="avatar">🏨</div>
    <div class="message-bubble agent-bubble">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendAgentMessage(text, toolsCalled = []) {
  const row = document.createElement("div");
  row.className = "message-row agent-row";

  let toolsHtml = "";
  if (toolsCalled && toolsCalled.length > 0) {
    const badges = toolsCalled
      .map(t => `<span class="tool-badge">⚙️ ${escapeHtml(t)}</span>`)
      .join("");
    toolsHtml = `<div class="tool-badge-container">${badges}</div>`;
  }

  row.innerHTML = `
    <div class="avatar">🏨</div>
    <div class="message-bubble agent-bubble">
      <div class="message-text">${formatMessageText(text)}</div>
      ${toolsHtml}
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatMessageText(text) {
  // Simple markdown-like line break and bold formatting
  let formatted = escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>");
  return formatted;
}

async function sendMessage(message) {
  if (!message || !message.trim()) return;
  const cleanMsg = message.trim();

  appendUserMessage(cleanMsg);
  userInput.value = "";
  userInput.disabled = true;
  sendBtn.disabled = true;

  const indicatorId = showTypingIndicator();

  try {
    const response = await fetch("/agent/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message: cleanMsg })
    });

    removeTypingIndicator(indicatorId);

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Network error" }));
      appendAgentMessage("⚠️ Error: " + (err.detail || "Failed to process request."));
      return;
    }

    const data = await response.json();
    appendAgentMessage(data.response, data.tools_called);

  } catch (error) {
    removeTypingIndicator(indicatorId);
    appendAgentMessage("⚠️ Connection error: Could not reach backend server.");
    console.error(error);
  } finally {
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
}

function handleFormSubmit(event) {
  event.preventDefault();
  const val = userInput.value;
  sendMessage(val);
}

function sendPrompt(text) {
  userInput.value = text;
  sendMessage(text);
}
