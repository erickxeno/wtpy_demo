import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { qryBbars, qryfunds, qrytrades, qryrstags } from '../api/snooper'

const http = axios.create({ baseURL: '/bt', timeout: 30000 })

export const useBacktestStore = defineStore('backtest', () => {
  const sessions = ref([])
  const currentSession = ref('')
  const currentCode = ref('SH510300')
  const currentPeriod = ref(5)
  const bars = ref([])
  const funds = ref([])
  const trades = ref([])
  const rounds = ref([])
  const summary = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchSessions() {
    try {
      const res = await http.post('/', { func: 'qrySessions', args: {} })
      sessions.value = res.data.sessions || []
    } catch {
      sessions.value = []
    }
  }

  async function fetchBars() {
    try {
      bars.value = await qryBbars({
        code: currentCode.value,
        count: 500,
        period: currentPeriod.value,
        session: currentSession.value
      })
    } catch (e) {
      bars.value = []
    }
  }

  async function fetchFunds() {
    try {
      funds.value = await qryfunds({ session: currentSession.value })
    } catch {
      funds.value = []
    }
  }

  async function fetchTrades() {
    try {
      trades.value = await qrytrades({ session: currentSession.value })
    } catch {
      trades.value = []
    }
  }

  async function fetchRounds() {
    try {
      rounds.value = await qryrstags({ session: currentSession.value })
    } catch {
      rounds.value = []
    }
  }

  async function fetchSummary() {
    try {
      const res = await http.get('/summary', {
        params: { session: currentSession.value }
      })
      summary.value = res.data
    } catch {
      summary.value = null
    }
  }

  async function loadAll() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([
        fetchBars(),
        fetchFunds(),
        fetchTrades(),
        fetchRounds(),
        fetchSummary()
      ])
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return {
    sessions, currentSession, currentCode, currentPeriod,
    bars, funds, trades, rounds, summary, loading, error,
    fetchSessions, fetchBars, fetchFunds, fetchTrades, fetchRounds, fetchSummary, loadAll
  }
})
