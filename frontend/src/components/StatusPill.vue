<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: '' },
  label: { type: String, default: '' },
})

const labels = {
  pending: '待接入',
  taken: '处理中',
  closed: '已关闭',
  online: '自动应答',
  human: '人工接管',
}

const text = computed(
  () => props.label || labels[props.status] || props.status
)
</script>

<template>
  <span class="pill" :class="status">{{ text }}</span>
</template>