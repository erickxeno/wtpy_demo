/**
 * 时间转换工具函数
 * bartime 格式: YYYYMMDD * 10000 + HHMM，例: 20240115*10000+0930 = 202401150930
 */

/**
 * 将 bartime (YYYYMMDD*10000+HHMM) 转换为 Unix timestamp (秒)
 * @param {number} bartime -  bartime 格式的数字，如 202401150930
 * @returns {number} Unix timestamp (秒)
 */
export function bartimeToTimestamp(bartime) {
  const bartimeStr = String(bartime)
  const dateStr = bartimeStr.slice(0, 8)
  const timeStr = bartimeStr.slice(8) || '0000'

  const year = parseInt(dateStr.slice(0, 4))
  const month = parseInt(dateStr.slice(4, 6)) - 1
  const day = parseInt(dateStr.slice(6, 8))

  const hours = parseInt(timeStr.slice(0, 2))
  const minutes = parseInt(timeStr.slice(2, 4))

  const date = new Date(year, month, day, hours, minutes)
  return Math.floor(date.getTime() / 1000)
}

/**
 * 将 Unix timestamp (秒) 转换为 bartime 格式
 * @param {number} timestamp - Unix timestamp (秒)
 * @returns {number} bartime 格式，如 202401150930
 */
export function timestampToBartime(timestamp) {
  const date = new Date(timestamp * 1000)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return parseInt(`${year}${month}${day}${hours}${minutes}`)
}

/**
 * 将 bartime 转换为 Date 对象
 * @param {number} bartime - bartime 格式
 * @returns {Date}
 */
export function bartimeToDate(bartime) {
  return new Date(bartimeToTimestamp(bartime) * 1000)
}

/**
 * 将 Date 对象转换为 bartime
 * @param {Date} date
 * @returns {number}
 */
export function dateToBartime(date) {
  return timestampToBartime(Math.floor(date.getTime() / 1000))
}
