<template>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th>方向</th>
          <th>合约</th>
          <th>开仓时间</th>
          <th class="r">开仓价</th>
          <th>平仓时间</th>
          <th class="r">平仓价</th>
          <th class="r">数量</th>
          <th class="r">盈亏</th>
          <th class="r">盈亏率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rounds" :key="r.id">
          <td :class="r.direction === 'Long' ? 'long' : 'short'">
            {{ r.direction === 'Long' ? '多' : '空' }}
          </td>
          <td>{{ r.openCode }}</td>
          <td>{{ r.openTime }}</td>
          <td class="r">{{ r.openPrice }}</td>
          <td>{{ r.closeTime }}</td>
          <td class="r">{{ r.closePrice }}</td>
          <td class="r">{{ r.qty }}</td>
          <td class="r" :class="r.profit >= 0 ? 'pos' : 'neg'">
            {{ r.profit.toFixed(2) }}
          </td>
          <td class="r" :class="r.profitRatio >= 0 ? 'pos' : 'neg'">
            {{ (r.profitRatio * 100).toFixed(2) }}%
          </td>
        </tr>
        <tr v-if="!rounds.length">
          <td colspan="9" class="empty">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  rounds: { type: Array, default: () => [] }
})
</script>

<style scoped>
.table-wrap { overflow: auto; max-height: 320px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { background: #16213e; color: #6a7a8a; padding: 6px 10px; position: sticky; top: 0; text-align: left; white-space: nowrap; }
th.r { text-align: right; }
td { padding: 5px 10px; border-bottom: 1px solid #232336; color: #9ab; text-align: left; white-space: nowrap; }
td.r { text-align: right; }
.long { color: #26a69a; }
.short { color: #ef5350; }
.pos { color: #26a69a; }
.neg { color: #ef5350; }
.empty { text-align: center; color: #555; padding: 20px; }
</style>
