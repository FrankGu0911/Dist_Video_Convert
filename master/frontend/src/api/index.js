import axios from 'axios'
import { io } from 'socket.io-client'

// 创建WebSocket连接
const socket = io('/', {
  path: '/socket.io',
  transports: ['websocket'],
  upgrade: false,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
})

// WebSocket事件处理
socket.on('connect', () => {
  console.log('WebSocket connected')
})

socket.on('disconnect', () => {
  console.log('WebSocket disconnected')
})

socket.on('task_update', (data) => {
  // 触发自定义事件，让组件可以监听并处理更新
  window.dispatchEvent(new CustomEvent('task_update', { detail: data }))
})

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data.data
  },
  error => {
    const response = error.response
    if (response && response.data) {
      console.error('API Error:', response.data.message || '未知错误')
    } else {
      console.error('Network Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// API 方法封装
const apiService = {
  // Workers
  getWorkers(params = {}) {
    const queryParams = new URLSearchParams()
    
    // 基础参数
    if (params.page) queryParams.append('page', params.page)
    if (params.per_page) queryParams.append('per_page', params.per_page)
    
    return api.get(`/workers?${queryParams.toString()}`)
  },

  // Tasks
  getTasks(params) {
    const queryParams = new URLSearchParams()
    
    // 基础参数
    if (params.page) queryParams.append('page', params.page)
    if (params.per_page) queryParams.append('per_page', params.per_page)
    if (params.sort_by) queryParams.append('sort_by', params.sort_by)
    if (params.order) queryParams.append('order', params.order)
    
    // 多选参数
    if (Array.isArray(params.status)) {
      params.status.forEach(status => {
        queryParams.append('status[]', status)
      })
    }

    return api.get(`/tasks?${queryParams.toString()}`)
  },

  createTask(data) {
    return api.post('/tasks', data)
  },

  updateTaskStatus(taskId, data) {
    return api.patch(`/tasks/${taskId}`, data)
  },

  // Videos
  getVideos(params) {
    // 处理多选参数
    const queryParams = new URLSearchParams()
    
    // 基础参数
    if (params.page) queryParams.append('page', params.page)
    if (params.per_page) queryParams.append('per_page', params.per_page)
    if (params.is_vr !== '') queryParams.append('is_vr', params.is_vr)
    if (params.sort_by) queryParams.append('sort_by', params.sort_by)
    if (params.order) queryParams.append('order', params.order)
    
    // 多选参数
    if (Array.isArray(params.transcode_status)) {
      params.transcode_status.forEach(status => {
        queryParams.append('transcode_status[]', status)
      })
    }
    if (Array.isArray(params.codec)) {
      params.codec.forEach(codec => {
        queryParams.append('codec[]', codec)
      })
    }

    return api.get(`/videos?${queryParams.toString()}`)
  },

  // Logs
  getLogs(params) {
    // 处理多选参数
    const queryParams = new URLSearchParams()
    
    // 基础参数
    if (params.page) queryParams.append('page', params.page)
    if (params.per_page) queryParams.append('per_page', params.per_page)
    if (params.start_time) queryParams.append('start_time', params.start_time)
    if (params.end_time) queryParams.append('end_time', params.end_time)
    if (params.sort_by) queryParams.append('sort_by', params.sort_by)
    if (params.order) queryParams.append('order', params.order)
    
    // 多选参数
    if (Array.isArray(params.log_level)) {
      params.log_level.forEach(level => {
        queryParams.append('log_level[]', level)
      })
    }

    return api.get(`/logs?${queryParams.toString()}`)
  },

  // WebSocket相关方法
  subscribeToTask(taskId) {
    socket.emit('subscribe', { task_id: taskId })
  },

  unsubscribeFromTask(taskId) {
    socket.emit('unsubscribe', { task_id: taskId })
  }
}

export default apiService 