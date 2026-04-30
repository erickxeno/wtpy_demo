<template>
  <div class="monitor-view">
    <WorkspaceNav
      :workspaces="store.workspaces"
      :current="store.currentWorkspace"
      @select="store.selectWorkspace"
    />

    <div class="monitor-main">
      <div class="account-bar" v-if="store.account">
        <div class="acc-card" v-for="f in accFields" :key="f.label">
          <div class="acc-label">{{ f.label }}</div>
          <div class="acc-value" :class="f.cls">{{ f.value }}</div>
        </div>
      </div>
      <div v-else class="placeholder">
        <span v-if="!store.currentWorkspace">请从左侧选择策略工作区</span>
        <span v-else-if="store.loading">加载中...</span>
        <span v-else>{{ store.error || '暂无账户数据' }}</span>
      </div>

      <div class="tabs-area">
        <div class="tab-bar">
          <button
            v-for="t in tabs"
            :key="t.key"
            class="tab-btn"
            :class="{ active: activeTab === t.key }"
            @click="activeTab = t.key"
          >
            {{ t.label }}
            <span class="badge">{{ t.key === 'positions' ? store.positions.length : store.signals.length }}</span>
          </button>
          <button class="btn-refresh" @click="store.refresh()" :disabled="store.loading">
            {{ store.loading ? '...' : '刷新' }}
          </button>
        </div>

        <div class="tab-body">
          <table v-if="activeTab === 'positions'" class="mon-table">
            <thead>
              <tr>
                <th>合约</th><th>方向</th><th class="r">持仓量</th>
                <th class="r">均价</th><th class="r">浮盈</th><th class="r">保证金</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in store.positions" :key="(p.code || '') + (p.direction || '')">
                <td>{{ p.code }}</td>
                <td :class="p.direction === 'Long' ? 'long' : 'short'">
                  {{ p.direction === 'Long' ? '多' : '空' }}
                </td>
                <td class="r">{{ p.volume }}</td>
                <td class="r">{{ p.cost_price ?? p.costPrice }}</td>
                <td class="r" :class="(p.float_profit ?? p.floatProfit ?? 0) >= 0 ? 'pos' : 'neg'">
                  {{ (+(p.float_profit ?? p.floatProfit ?? 0)).toFixed(2) }}
                </td>
                <td class="r">{{ (+(p.margin ?? 0)).toFixed(2) }}</td>
              </tr>
              <tr v-if="!store.positions.length">
                <td colspan="6" class="empty">暂无持仓</td>
              </tr>
            </tbody>
          </table>

          <table v-if="activeTab === 'signals'" class="mon-table">
            <thead>
              <tr>
                <th>时间</th><th>合约</th><th>方向</th>
                <th class="r">信号量</th><th class="r">目标仓位</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in store.signals" :key="(s.code || '') + (s.time || '')">
                <td>{{ s.time }}</td>
                <td>{{ s.code }}</td>
                <td :class="s.direct === 'Long' ? 'long' : 'short'">
                  {{ s.direct === 'Long' ? '多' : '空' }}
                </td>
                <td class="r">{{ s.volume }}</td>
                <td class="r">{{ s.target }}</td>
              </tr>
              <tr v-if="!store.signals.length">
                <td colspan="5" class="empty">暂无信号</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useMonitorStore } from '../stores/monitor'
import WorkspaceNav from '../components/WorkspaceNav.vue'

const store = useMonitorStore()
const activeTab = ref('positions')
const tabs = [
  { key: 'positions', label: '持仓' },
  { key: 'signals', label: '信号' }
]

const accFields = computed(() => {
  const a = store.account || {}
  const fp = +(a.float_profit ?? a.floatProfit ?? 0)
  return [
    { label: '权益', value: fmt(a.balance ?? a.equity), cls: '' },
    { label: '可用资金', value: fmt(a.available), cls: '' },
    { label: '持仓市值', value: fmt(a.position_value ?? a.positionValue), cls: '' },
    { label: '浮盈亏', value: fmt(fp), cls: fp >= 0 ? 'pos' : 'neg' }
  ]
})

function fmt(v) {
  if (v == null) return '--'
  return Number(v).toFixed(2)
}

onMounted(async () => {
  await store.fetchWorkspaces()
  store.startPolling(5000)
})

onBeforeUnmount(() => {
  store.stopPolling()
})
</script>

<style scoped>
.monitor-view { display: flex; height: 100%; background: #0f0f1e; color: #9ab; overflow: hidden; }
.monitor-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.account-bar {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: #16213e;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.acc-card {
  background: #0f0f1e;
  border: 1px solid #2d2d44;
  border-radius: 6px;
  padding: 8px 16px;
  min-width: 110px;
}
.acc-label { font-size: 11px; color: #6a7a8a; margin-bottom: 4px; }
.acc-value { font-size: 15px; font-weight: 600; color: #9ab; }
.pos { color: #26a69a; }
.neg { color: #ef5350; }
.placeholder { padding: 24px; color: #555; text-align: center; font-size: 13px; }
.tabs-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.tab-bar {
  display: flex;
  align-items: center;
  background: #16213e;
  padding: 0 16px;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
}
.tab-btn {
  background: none;
  border: none;
  color: #6a7a8a;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tab-btn.active { color: #26a69a; border-bottom-color: #26a69a; }
.badge {
  background: #2d2d44;
  border-radius: 8px;
  padding: 1px 6px;
  font-size: 11px;
}
.btn-refresh {
  margin-left: auto;
  background: none;
  color: #26a69a;
  border: 1px solid #26a69a;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }
.tab-body { flex: 1; overflow: auto; padding: 12px 16px; }
.mon-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.mon-table th {
  background: #16213e;
  color: #6a7a8a;
  padding: 6px 10px;
  text-align: left;
  position: sticky;
  top: 0;
  white-space: nowrap;
}
.mon-table th.r { text-align: right; }
.mon-table td { padding: 5px 10px; border-bottom: 1px solid #232336; color: #9ab; text-align: left; }
.mon-table td.r { text-align: right; }
.long { color: #26a69a; }
.short { color: #ef5350; }
.empty { text-align: center; color: #555; padding: 20px; }
</style>
