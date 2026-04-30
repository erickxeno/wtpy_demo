<template>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>合约</th>
          <th>方向</th>
          <th>操作</th>
          <th class="r">价格</th>
          <th class="r">数量</th>
          <th class="r">金额</th>
          <th class="r">手续费</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in trades" :key="t.id">
          <td>{{ t.time }}</td>
          <td>{{ t.code }}</td>
          <td :class="t.direction === 'Long' ? 'long' : 'short'">
            {{ t.direction === 'Long' ? '多' : '空' }}
          </td>
          <td>{{ t.action === 'Open' ? '开仓' : '平仓' }}</td>
          <td class="r">{{ t.price }}</td>
          <td class="r">{{ t.qty }}</td>
          <td class="r">{{ t.amount.toFixed(2) }}</td>
          <td class="r">{{ t.commission.toFixed(2) }}</td>
        </tr>
        <tr v-if="!trades.length">
          <td colspan="8" class="empty">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  trades: { type: Array, default: () => [] }
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
.empty { text-align: center; color: #555; padding: 20px; }
</style>
