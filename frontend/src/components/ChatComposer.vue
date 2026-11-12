<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  placeholder: {
    type: String,
    default: '输入消息，Enter 发送',
  },
  hintLeft: {
    type: String,
    default: 'Enter 发送 · Shift + Enter 换行',
  },
  hintRight: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['send'])

const text = ref('')
const textarea = ref(null)

function resize() {
  const element = textarea.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 150)}px`
}

watch(text, () => nextTick(resize))

function submit() {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  nextTick(resize)
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="composer">
    <div class="composer-box">
      <textarea
        ref="textarea"
        v-model="text"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        @keydown="onKeydown"
      />
      <button
        class="send-btn"
        :disabled="disabled || !text.trim()"
        aria-label="发送"
        @click="submit"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 19V5" />
          <path d="m5 12 7-7 7 7" />
        </svg>
      </button>
    </div>
    <div class="composer-hint">
      <span>{{ hintLeft }}</span>
      <span>{{ hintRight }}</span>
    </div>
  </div>
</template>