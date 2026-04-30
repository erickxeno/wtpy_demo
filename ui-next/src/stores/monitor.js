import { defineStore } from 'pinia'
import { ref } from 'vue'
import { qryAccount, qryPositions, qrySignals, qryWorkspaces } from '../api/monitor'

export const useMonitorStore = defineStore('monitor', () => {
  const workspaces = ref([])
  const currentWorkspace = ref('')
  const account = ref(null)
  const positions = ref([])
  const signals = ref([])
  const loading = ref(false)
  const error = ref(null)

  let _pollTimer = null

  async function fetchWorkspaces() {
    try {
      workspaces.value = await qryWorkspaces()
    } catch {
      workspaces.value = []
    }
  }

  async function refresh() {
    if (!currentWorkspace.value) return
    loading.value = true
    try {
      const [acc, pos, sig] = await Promise.all([
        qryAccount(currentWorkspace.value),
        qryPositions(currentWorkspace.value),
        qrySignals(currentWorkspace.value)
      ])
      account.value = acc
      positions.value = pos
      signals.value = sig
      error.value = null
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function startPolling(interval = 5000) {
    stopPolling()
    _pollTimer = setInterval(refresh, interval)
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  function selectWorkspace(ws) {
    currentWorkspace.value = ws
    refresh()
  }

  return {
    workspaces, currentWorkspace, account, positions, signals, loading, error,
    fetchWorkspaces, refresh, startPolling, stopPolling, selectWorkspace
  }
})
