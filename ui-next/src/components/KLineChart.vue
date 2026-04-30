<template>
  <div ref="container" class="kline-chart"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { createChart } from 'lightweight-charts'

const props = defineProps({
  bars: { type: Array, default: () => [] }
})

const container = ref(null)
let chart = null
let candleSeries = null
let volumeSeries = null
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
    crosshair: { mode: 1 },
    rightPriceScale: { borderColor: '#2d2d44' },
    timeScale: {
      borderColor: '#2d2d44',
      timeVisible: true,
      secondsVisible: false
    },
    width: container.value.clientWidth,
    height: container.value.clientHeight || 400
  })

  candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350'
  })

  volumeSeries = chart.addHistogramSeries({
    color: '#385263',
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume'
  })

  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 }
  })

  if (props.bars.length) _setData(props.bars)

  ro = new ResizeObserver(() => {
    if (container.value) {
      chart.applyOptions({ width: container.value.clientWidth })
    }
  })
  ro.observe(container.value)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  chart?.remove()
})

watch(() => props.bars, (newBars) => {
  _setData(newBars)
}, { deep: true })

function _setData(bars) {
  if (!candleSeries || !bars.length) return
  const candles = bars.map(b => ({
    time: b.time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close
  }))
  const volumes = bars.map(b => ({
    time: b.time,
    value: b.volume,
    color: b.close >= b.open ? '#26a69a55' : '#ef535055'
  }))
  candleSeries.setData(candles)
  volumeSeries.setData(volumes)
  chart.timeScale().fitContent()
}
</script>

<style scoped>
.kline-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
