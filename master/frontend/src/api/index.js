import axios from 'axios'

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
  getWorkers() {
    return api.get('/workers')
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
  }
}

export default apiService 