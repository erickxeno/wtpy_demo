<template>
  <aside class="workspace-nav">
    <div class="nav-title">策略列表</div>
    <ul class="nav-list">
      <li
        v-for="ws in workspaces"
        :key="ws"
        class="nav-item"
        :class="{ active: ws === current }"
        @click="$emit('select', ws)"
      >
        <span class="ws-dot"></span>
        {{ ws }}
      </li>
      <li v-if="!workspaces.length" class="nav-empty">无策略</li>
    </ul>
  </aside>
</template>

<script setup>
defineProps({
  workspaces: { type: Array, default: () => [] },
  current: { type: String, default: '' }
})
defineEmits(['select'])
</script>

<style scoped>
.workspace-nav {
  width: 200px;
  min-height: 100%;
  background: #16213e;
  border-right: 1px solid #2d2d44;
  flex-shrink: 0;
}
.nav-title {
  padding: 14px 16px 8px;
  font-size: 10px;
  color: #6a7a8a;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.nav-list { list-style: none; margin: 0; padding: 0; }
.nav-item {
  padding: 10px 16px;
  font-size: 13px;
  color: #8a9bab;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  border-left: 3px solid transparent;
  transition: all 0.15s;
  word-break: break-all;
}
.nav-item:hover { background: #1e2d4e; color: #cdd; }
.nav-item.active { color: #26a69a; border-left-color: #26a69a; background: #1a3040; }
.ws-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
  opacity: 0.5;
}
.nav-item.active .ws-dot { opacity: 1; }
.nav-empty { padding: 16px; color: #555; font-size: 12px; }
</style>
