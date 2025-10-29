<template>
  <div class="chat">
    <header class="chat-header">
      <h2>Chat as {{ username }}</h2>
    </header>

    <div ref="container" class="messages" v-if="!isLoading">
      <div
        v-for="(msg, index) in messages"
        :key="msg.id ?? index"
        :class="['msg', msg.isUser ? 'user-msg' : 'ai-msg']"
      >
        <div class="meta">
          <span class="who">{{ msg.isUser ? 'You' : 'AI' }}</span>
          <span class="time" v-if="msg.created_at">{{ formatTime(msg.created_at) }}</span>
        </div>
        <div class="bubble">
          <pre class="text-content">{{ msg.text }}</pre>
        </div>
      </div>
    </div>

    <div v-else class="loading">Loading history...</div>

    <form @submit.prevent="send" class="input-row">
      <input
        v-model="message"
        placeholder="Say something..."
        :disabled="isSending"
        @keydown.enter.exact.prevent="send"
      />
      <button :disabled="isSending || !message.trim()">
        {{ isSending ? "Sending..." : "Send" }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";
import axios from "axios";
import { useRoute } from "vue-router";

const route = useRoute();
const username = route.params.username || localStorage.getItem("username") || "";

if (username && !localStorage.getItem("username")) {
  localStorage.setItem("username", username);
}

const message = ref("");
const messages = ref([]);
const isSending = ref(false);
const isLoading = ref(false);
const container = ref(null);

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

async function fetchHistory() {
  isLoading.value = true;
  try {
    const res = await axios.get(`http://localhost:8000/api/chat/${username}/history`);
    // Build interleaved messages (user + ai)
    const pairs = res.data || [];
    const out = [];
    for (const m of pairs) {
      out.push({ id: `u-${m.id}`, isUser: true, text: m.content, created_at: m.created_at });
      out.push({ id: `a-${m.id}`, isUser: false, text: m.response, created_at: m.created_at });
    }
    messages.value = out;
  } catch (err) {
    console.error("Failed to load history", err);
    messages.value = [];
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
}

function scrollToBottom() {
  if (!container.value) return;
  container.value.scrollTop = container.value.scrollHeight;
}

async function send() {
  if (!message.value || isSending.value) return;
  isSending.value = true;
  const text = message.value.trim();

  // Add user message and AI placeholder
  messages.value.push({ id: `u-${Date.now()}`, isUser: true, text, created_at: new Date().toISOString() });
  const aiIndex = messages.value.push({ id: `a-pending-${Date.now()}`, isUser: false, text: "...", created_at: new Date().toISOString() }) - 1;
  message.value = "";
  await nextTick();
  scrollToBottom();

  try {
    const res = await axios.post(`http://localhost:8000/api/chat/${username}`, { message: text });
    // replace placeholder
    messages.value[aiIndex] = {
      id: `a-${res.data.id || Date.now()}`,
      isUser: false,
      text: res.data.response || "(no response)",
      created_at: new Date().toISOString(),
    };
  } catch (err) {
    console.error("Chat error:", err);
    messages.value[aiIndex] = { id: `a-error-${Date.now()}`, isUser: false, text: "Error: failed to get response", created_at: new Date().toISOString() };
    alert("Error sending message. See console for details.");
  } finally {
    isSending.value = false;
    await nextTick();
    scrollToBottom();
  }
}

onMounted(() => {
  if (!username) {
    alert("No username provided. Please login or register.");
    return;
  }
  fetchHistory();
});
</script>

<style scoped>
.chat {
  max-width: 880px;
  margin: 16px auto;
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(180deg,#ffffff,#f7f9fc);
  box-shadow: 0 6px 18px rgba(32,33,36,0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.messages {
  max-height: 64vh;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: transparent;
  border-radius: 8px;
}
.msg {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}
.user-msg {
  align-self: flex-end;
  text-align: right;
}
.ai-msg {
  align-self: flex-start;
  text-align: left;
}
.bubble {
  padding: 10px 12px;
  border-radius: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f1f3f5;
  color: #111827;
  font-size: 0.95rem;
}
.user-msg .bubble {
  background: linear-gradient(90deg,#d1f7d6,#c0f0cc);
}
.meta {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 6px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.input-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.input-row input {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
}
.input-row button {
  padding: 10px 14px;
  border-radius: 8px;
  border: none;
  background: #0ea5e9;
  color: white;
  cursor: pointer;
}
.loading {
  padding: 12px;
  text-align: center;
  color: #666;
}
.text-content {
  margin: 0;
  font-family: inherit;
}
</style>
