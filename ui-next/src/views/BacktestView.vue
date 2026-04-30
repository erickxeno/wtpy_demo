<template>
  <div class="backtest-view">
    <header class="bt-header">
      <div class="controls">
        <select v-model="store.currentSession" @change="onSessionChange" class="sel">
          <option value="">-- 选择策略 --</option>
          <option v-for="s in store.sessions" :key="s" :value="s">{{ s }}</option>
        </select>
        <input
          v-model="store.currentCode"
          placeholder="合约代码"
          class="inp"
          @change="store.fetchBars()"
        />
        <select v-model.number="store.currentPeriod" @change="store.fetchBars()" class="sel">
          <option :value="1">1分钟</option>
          <option :value="5">5分钟</option>
          <option :value="15">15分钟</option>
          <option :value="60">60分钟</option>
          <option value="D">日线</option>
        </select>
      </div>
      <button class="btn-primary" @click="store.loadAll()" :disabled="store.loading">
        {{ store.loading ? '加载中...' : '刷新' }}
      </button>
    </header>

    <div class="bt-body">
      <div class="chart-area">
        <KLineChart :bars="store.bars" />
      </div>

      <div class="perf-area">
        <PerfCards :summary="store.summary" />
      </div>

      <div class="tabs-area">
        <div class="tab-bar">
          <button
            v-for="t in tabs"
            :key="t.key"
            class="tab-btn"
            :class="{ active: activeTab === t.key }"
            @click="activeTab = t.key"
          >{{ t.label }}</button>
        </div>
        <div class="tab-body">
          <FundCurve v-if="activeTab === 'fund'" :funds="store.funds" />
          <TradeTable v-if="activeTab === 'trades'" :trades="store.trades" />
          <RoundTable v-if="activeTab === 'rounds'" :rounds="store.rounds" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useBacktestStore } from '../stores/backtest'
import KLineChart from '../components/KLineChart.vue'
import FundCurve from '../components/FundCurve.vue'
import PerfCards from '../components/PerfCards.vue'
import TradeTable from '../components/TradeTable.vue'
import RoundTable from '../components/RoundTable.vue'

const store = useBacktestStore()
const activeTab = ref('fund')
const tabs = [
  { key: 'fund', label: '资金曲线' },
  { key: 'trades', label: '交易明细' },
  { key: 'rounds', label: '回合统计' }
]

onMounted(async () => {
  await store.fetchSessions()
})

async function onSessionChange() {
  if (store.currentSession) await store.loadAll()
}
</script>

<style scoped>
.backtest-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f0f1e;
  color: #9ab;
  overflow: hidden;
}
.bt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #16213e;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
}
.controls { display: flex; gap: 8px; align-items: center; }
.sel, .inp {
  background: #0f0f1e;
  color: #9ab;
  border: 1px solid #2d2d44;
  border-radius: 4px;
  padding: 5px 8px;
  font-size: 13px;
}
.inp { width: 110px; }
.btn-primary {
  background: #1a4a3a;
  color: #26a69a;
  border: 1px solid #26a69a;
  padding: 5px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:hover { background: #26a69a; color: #0f0f1e; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.bt-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
.chart-area { flex: 1; min-height: 360px; overflow: hidden; }
.perf-area {
  padding: 10px 16px;
  border-top: 1px solid #2d2d44;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
}
.tabs-area { flex-shrink: 0; }
.tab-bar {
  display: flex;
  background: #16213e;
  padding: 0 16px;
  border-bottom: 1px solid #2d2d44;
}
.tab-btn {
  background: none;
  border: none;
  color: #6a7a8a;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s;
}
.tab-btn.active { color: #26a69a; border-bottom-color: #26a69a; }
.tab-btn:hover { color: #9ab; }
.tab-body { padding: 12px 16px; max-height: 340px; overflow: auto; }
</style>
