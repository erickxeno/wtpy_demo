<template>
  <div ref="container" class="fund-curve"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { createChart, LineSeries } from 'lightweight-charts'

const props = defineProps({
  funds: { type: Array, default: () => [] }
})

const container = ref(null)
let chart = null
let equitySeries = null
let balanceSeries = null
let ro = null

onMounted(() => {
  chart = createChart(container.value, {
    layout: {
      background: { color: '#1a1a2e' },
      textColor: '#9ab'
    },
    grid: {
      vertLines: { color: '#232336' },
      horzLines: { color: '#232336' }
    },
    rightPriceScale: { borderColor: '#2d2d44' },
    timeScale: { borderColor: '#2d2d44', timeVisible: false },
    width: container.value.clientWidth,
    height: container.value.clientHeight || 240
  })

  equitySeries = chart.addSeries(LineSeries, {
    color: '#26a69a',
    lineWidth: 2,
    title: '净值'
  })

  balanceSeries = chart.addSeries(LineSeries, {
    color: '#2196f3',
    lineWidth: 1,
    lineStyle: 2,
    title: '余额'
  })

  if (props.funds.length) _setData(props.funds)

  ro = new ResizeObserver(() => {
    if (container.value) chart.applyOptions({ width: container.value.clientWidth })
  })
  ro.observe(container.value)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  chart?.remove()
})

watch(() => props.funds, _setData, { deep: true })

function _toDateStr(d) {
  const s = String(d)
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
}

function _setData(funds) {
  if (!equitySeries || !funds.length) return
  const eq = funds.map(f => ({ time: _toDateStr(f.date), value: f.equity }))
  const bal = funds.map(f => ({ time: _toDateStr(f.date), value: f.balance }))
  equitySeries.setData(eq)
  balanceSeries.setData(bal)
  chart.timeScale().fitContent()
}
</script>

<style scoped>
.fund-curve {
  width: 100%;
  min-height: 240px;
}
</style>
