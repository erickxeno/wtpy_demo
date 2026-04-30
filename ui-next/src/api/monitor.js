import axios from 'axios'

const http = axios.create({
  baseURL: '/mgr',
  timeout: 30000
})

export async function qryAccount(session) {
  const response = await http.post('/', {
    func: 'qryAccount',
    args: { session }
  })
  return response.data
}

export async function qryPositions(session) {
  const response = await http.post('/', {
    func: 'qryPositions',
    args: { session }
  })
  const data = response.data
  return data.positions || []
}

export async function qrySignals(session) {
  const response = await http.post('/', {
    func: 'qrySignals',
    args: { session }
  })
  const data = response.data
  return data.signals || []
}

export async function qryWorkspaces() {
  const response = await http.post('/', {
    func: 'qryWorkspaces',
    args: {}
  })
  const data = response.data
  return data.workspaces || []
}
