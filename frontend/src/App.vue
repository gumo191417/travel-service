<script setup>
import { onMounted, ref, watch } from 'vue'

const theme = ref(
  localStorage.getItem('travel-theme') || 'light'
)

function applyTheme() {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('travel-theme', theme.value)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

watch(theme, applyTheme)
onMounted(applyTheme)
</script>

<template>
  <div class="app">
    <header class="topbar">
      <router-link class="brand" to="/">
        <span class="brand-mark">✳</span>
        <span>
          <span class="brand-name">Travel Desk</span>
          <span class="brand-sub">旅游智能客服</span>
        </span>
      </router-link>

      <nav class="nav">
        <router-link to="/">用户对话</router-link>
        <router-link to="/agent">客服工作台</router-link>
      </nav>

      <span class="spacer" />
      <span class="topbar-note">Vue 3 · ElevenLabs UI 风格</span>

      <button
        class="btn icon-btn"
        :title="theme === 'dark' ? '切换到浅色' : '切换到深色'"
        @click="toggleTheme"
      >
        <svg
          v-if="theme === 'dark'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        >
          <circle cx="12" cy="12" r="4" />
          <path
            d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
          />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      </button>
    </header>

    <router-view />
  </div>
</template>