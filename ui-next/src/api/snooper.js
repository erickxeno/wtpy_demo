import axios from 'axios'
import { bartimeToTimestamp } from '../utils/timeConvert'

const http = axios.create({
  baseURL: '/bt',
  timeout: 30000
})

/**
 * 将K线数据从API格式转换为 Lightweight Charts 格式
 * @param {Array} bars - API返回的K线数据
 * @returns {Array} 转换后的K线数据
 */
function convertBars(bars) {
  if (!Array.isArray(bars)) return []
  return bars.map(bar => {
    // bar.time 格式可能是 bartime 或 Unix timestamp
    let time
    if (typeof bar.time === 'number') {
      // 如果是 bartime 格式 (如 202401150930)，转换为 Unix timestamp
      if (bar.time > 1000000000) {
        // 大于 10亿，说明是 bartime 格式
        time = bartimeToTimestamp(bar.time)
      } else {
        // Unix timestamp (秒)
        time = bar.time
      }
    } else {
      time = bar.time
    }

    return {
      time,
      open: parseFloat(bar.open) || 0,
      high: parseFloat(bar.high) || 0,
      low: parseFloat(bar.low) || 0,
      close: parseFloat(bar.close) || 0,
      volume: parseFloat(bar.volume) || 0
    }
  })
}

/**
 * 获取K线数据
 * @param {Object} params - 查询参数
 * @param {string} params.code - 合约代码
 * @param {number} params.count - 数量
 * @param {number} params.period - 周期 (1=分钟, 5=5分钟, 15=15分钟, 60=小时, D=日, W=周, M=月)
 * @param {number} params.endTime - 结束时间 (bartime)
 * @param {string} params.session - 策略标识
 * @returns {Promise<Array>} K线数据数组
 */
export async function qryBbars(params) {
  const { code, count, period, endTime, session } = params
  const payload = {
    func: 'qryBbars',
    args: {
      code: code || '',
      count: count || 100,
      period: period || 1,
      endTime: endTime || 0,
      session: session || ''
    }
  }

  const response = await http.post('/', payload)
  const data = response.data

  if (data.bars) {
    return convertBars(data.bars)
  }
  return []
}

/**
 * 获取资金曲线
 * @param {Object} params - 查询参数
 * @param {string} params.session - 策略标识
 * @param {number} params.day - 日期 (YYYYMMDD)
 * @returns {Promise<Array>} 资金曲线数据
 */
export async function qryfunds(params) {
  const { session, day } = params
  const payload = {
    func: 'qryfunds',
    args: {
      session: session || '',
      day: day || 0
    }
  }

  const response = await http.post('/', payload)
  const data = response.data

  if (data.funds) {
    return data.funds.map(item => ({
      date: item.date,
      equity: parseFloat(item.equity) || 0,
      balance: parseFloat(item.balance) || 0,
      margin: parseFloat(item.margin) || 0,
      floatProfit: parseFloat(item.float_profit) || 0
    }))
  }
  return []
}

/**
 * 获取订单明细
 * @param {Object} params - 查询参数
 * @param {string} params.session - 策略标识
 * @param {number} params.day - 日期 (YYYYMMDD)
 * @returns {Promise<Array>} 订单数据
 */
export async function qryorders(params) {
  const { session, day } = params
  const payload = {
    func: 'qryorders',
    args: {
      session: session || '',
      day: day || 0
    }
  }

  const response = await http.post('/', payload)
  const data = response.data

  if (data.orders) {
    return data.orders.map(order => ({
      id: order.id,
      time: order.time,
      code: order.code,
      direction: order.direction,
      action: order.action,
      price: parseFloat(order.price) || 0,
      qty: parseFloat(order.qty) || 0,
      status: order.status,
      fillPrice: parseFloat(order.fill_price) || 0,
      fillQty: parseFloat(order.fill_qty) || 0
    }))
  }
  return []
}

/**
 * 获取交易明细
 * @param {Object} params - 查询参数
 * @param {string} params.session - 策略标识
 * @param {number} params.day - 日期 (YYYYMMDD)
 * @returns {Promise<Array>} 交易数据
 */
export async function qrytrades(params) {
  const { session, day } = params
  const payload = {
    func: 'qrytrades',
    args: {
      session: session || '',
      day: day || 0
    }
  }

  const response = await http.post('/', payload)
  const data = response.data

  if (data.trades) {
    return data.trades.map(trade => ({
      id: trade.id,
      time: trade.time,
      code: trade.code,
      direction: trade.direction,
      action: trade.action,
      price: parseFloat(trade.price) || 0,
      qty: parseFloat(trade.qty) || 0,
      amount: parseFloat(trade.amount) || 0,
      commission: parseFloat(trade.commission) || 0
    }))
  }
  return []
}

/**
 * 获取回合信息
 * @param {Object} params - 查询参数
 * @param {string} params.session - 策略标识
 * @param {number} params.day - 日期 (YYYYMMDD)
 * @returns {Promise<Array>} 回合数据
 */
export async function qryrstags(params) {
  const { session, day } = params
  const payload = {
    func: 'qryrstags',
    args: {
      session: session || '',
      day: day || 0
    }
  }

  const response = await http.post('/', payload)
  const data = response.data

  if (data.rstags) {
    return data.rstags.map(tag => ({
      id: tag.id,
      openTime: tag.open_time,
      closeTime: tag.close_time,
      openCode: tag.open_code,
      closeCode: tag.close_code,
      direction: tag.direction,
      openPrice: parseFloat(tag.open_price) || 0,
      closePrice: parseFloat(tag.close_price) || 0,
      qty: parseFloat(tag.qty) || 0,
      profit: parseFloat(tag.profit) || 0,
      commission: parseFloat(tag.commission) || 0,
      profitRatio: parseFloat(tag.profit_ratio) || 0
    }))
  }
  return []
}
