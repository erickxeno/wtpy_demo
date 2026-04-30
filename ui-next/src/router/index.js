import { createRouter, createWebHistory } from 'vue-router'
import BacktestView from '../views/BacktestView.vue'
import MonitorView from '../views/MonitorView.vue'

const routes = [
  { path: '/', redirect: '/backtest' },
  { path: '/backtest', component: BacktestView },
  { path: '/monitor', component: MonitorView }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
