<script setup lang="ts">
defineProps<{
  label?: string;
}>();
</script>

<template>
  <span class="mock-badge" role="status" :title="label || '演示数据，非生产接口'">
    {{ label || '[Mock]' }}
  </span>
</template>

<style scoped>
.mock-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  font-family: var(--font-sans);
  user-select: none;
}
</style>
