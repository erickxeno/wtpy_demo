<template>
  <div class="perf-cards">
    <div
      v-for="card in cards"
      :key="card.key"
      class="perf-card"
      :class="card.cls"
    >
      <div class="card-label">{{ card.label }}</div>
      <div class="card-value">{{ card.value }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: Object, default: null }
})

function pct(v) { return v != null ? (v * 100).toFixed(2) + '%' : '--' }
function ratio(v) { return v != null ? Number(v).toFixed(3) : '--' }
function money(v) { return v != null ? Number(v).toLocaleString() : '--' }
function sign(v) { return v == null ? '' : v >= 0 ? 'pos' : 'neg' }

const cards = computed(() => {
  const s = props.summary || {}
  return [
    { key: 'total_return', label: '总收益率', value: pct(s.total_return), cls: sign(s.total_return) },
    { key: 'annual_return', label: '年化收益', value: pct(s.annual_return), cls: sign(s.annual_return) },
    { key: 'win_rate', label: '胜率', value: pct(s.win_rate), cls: '' },
    { key: 'max_falldown', label: '最大回撤', value: pct(s.max_falldown), cls: 'neg' },
    { key: 'sharpe_ratio', label: 'Sharpe', value: ratio(s.sharpe_ratio), cls: sign(s.sharpe_ratio) },
    { key: 'sortino_ratio', label: 'Sortino', value: ratio(s.sortino_ratio), cls: sign(s.sortino_ratio) },
    { key: 'calmar_ratio', label: 'Calmar', value: ratio(s.calmar_ratio), cls: sign(s.calmar_ratio) },
    { key: 'max_profratio', label: '最大盈利回合', value: pct(s.max_profratio), cls: 'pos' },
    { key: 'capital', label: '初始资金', value: money(s.capital), cls: '' },
    { key: 'days', label: '交易天数', value: s.days != null ? s.days + ' 天' : '--', cls: '' }
  ]
})
</script>

<style scoped>
.perf-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}
.perf-card {
  background: #16213e;
  border: 1px solid #2d2d44;
  border-radius: 6px;
  padding: 10px 12px;
  text-align: center;
}
.card-label {
  font-size: 11px;
  color: #6a7a8a;
  margin-bottom: 6px;
}
.card-value {
  font-size: 17px;
  font-weight: 600;
  color: #9ab;
}
.pos .card-value { color: #26a69a; }
.neg .card-value { color: #ef5350; }
</style>
