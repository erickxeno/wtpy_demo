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
import { ref, onMounted, watch } from 'vue'
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

// Generate mock K-line bars for demo
function generateMockBars(count = 300) {
  const bars = []
  let basePrice = 3.50
  const now = new Date()
  const startTime = new Date(now.getTime() - count * 5 * 60 * 1000)

  for (let i = 0; i < count; i++) {
    const time = new Date(startTime.getTime() + i * 5 * 60 * 1000)
    // Convert to Unix timestamp (seconds)
    const timestamp = Math.floor(time.getTime() / 1000)
    
    const volatility = 0.002
    const change = (Math.random() - 0.5) * 2 * volatility * basePrice
    const open = basePrice + change
    const close = open + (Math.random() - 0.5) * 2 * volatility * basePrice
    const high = Math.max(open, close) + Math.random() * volatility * basePrice
    const low = Math.min(open, close) - Math.random() * volatility * basePrice
    const volume = Math.floor(Math.random() * 1000000 + 500000)

    bars.push({ time: timestamp, open, high, low, close, volume })
    basePrice = close
  }
  return bars
}

// Generate mock funds data
function generateMockFunds() {
  const funds = []
  let equity = 1000000
  const now = new Date()
  for (let i = 30; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000)
    equity *= (1 + (Math.random() - 0.4) * 0.02)
    funds.push({
      date: d.toISOString().slice(0, 10).replace(/-/g, ''),
      equity: Math.round(equity * 100) / 100,
      balance: Math.round(equity * 100) / 100,
      margin: 0,
      float_profit: Math.round((Math.random() - 0.5) * 5000 * 100) / 100
    })
  }
  return funds
}

// Load demo data directly
function loadDemoData() {
  store.sessions = ['CTA_Strategy', 'HFT_Strategy', 'Arbitrage_Strategy']
  store.bars = generateMockBars(300)
  store.funds = generateMockFunds()
  store.trades = []
  store.rounds = []
  store.summary = {
    totalProfit: 125840.50,
    profitRatio: 12.58,
    maxDrawdown: -8350.20,
    maxDrawdownRatio: -3.28,
    winRate: 68.5,
    totalTrades: 156,
    avgProfit: 806.67
  }
}

onMounted(async () => {
  // Try to fetch from API first
  await store.fetchSessions()
  
  // If no sessions (API failed or no backend), use demo data
  if (store.sessions.length === 0) {
    console.log('[BacktestView] No sessions from API, loading demo data')
    loadDemoData()
  }
})

// Watch for session changes and load data
watch(() => store.currentSession, async (newSession) => {
  if (newSession) {
    console.log('[BacktestView] Session changed to:', newSession)
    await store.loadAll()
  }
})

async function onSessionChange() {
  if (store.currentSession) {
    await store.loadAll()
  }
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
.chart-area { flex: 1; min-height: 400px; height: 400px; overflow: hidden; }
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
