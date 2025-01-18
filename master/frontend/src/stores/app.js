import { defineStore } from 'pinia'
import api from '../api'
import axios from 'axios'

export const useAppStore = defineStore('app', {
  state: () => ({
    darkMode: localStorage.getItem('darkMode') === 'true',
    sidebarOpen: window.innerWidth >= 1024,
    workers: [],
    tasks: [],
    videos: [],
    logs: []
  }),
  
  actions: {
    toggleDarkMode() {
      this.darkMode = !this.darkMode
      localStorage.setItem('darkMode', this.darkMode)
      if (this.darkMode) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    },
    
    toggleSidebar(value) {
      this.sidebarOpen = typeof value === 'boolean' ? value : !this.sidebarOpen
    },
    
    handleResize() {
      if (window.innerWidth >= 1024) {
        this.sidebarOpen = true
      } else {
        this.sidebarOpen = false
      }
    },
    
    async fetchWorkers(params) {
      try {
        const response = await api.getWorkers(params)
        if (response?.workers) {
          this.workers = response.workers
        }
        return response
      } catch (error) {
        console.error('Error fetching workers:', error)
        return null
      }
    },
    
    async fetchTasks() {
      try {
        const data = await api.getTasks()
        this.tasks = data || []
      } catch (error) {
        console.error('Error fetching tasks:', error)
        this.tasks = []
      }
    },
    
    async fetchLogs(params = {}) {
      try {
        const response = await api.getLogs(params)
        if (response?.logs) {
          this.logs = response.logs
        }
        return response
      } catch (error) {
        console.error('Error fetching logs:', error)
        this.logs = []
        return null
      }
    },

    async uploadVideo(formData) {
      try {
        const data = await api.createTask(formData)
        await this.fetchTasks()
        return data
      } catch (error) {
        console.error('Error uploading video:', error)
        throw error
      }
    },

    async cancelTask(taskId) {
      try {
        await api.cancelTask(taskId)
        await this.fetchTasks()
      } catch (error) {
        console.error('Error canceling task:', error)
        throw error
      }
    },

    async stopWorker(workerId) {
      try {
        await api.stopWorker(workerId)
        await this.fetchWorkers()
      } catch (error) {
        console.error('Error stopping worker:', error)
        throw error
      }
    },

    async setWorkerOffline(workerId, action) {
      const response = await axios.post(`/api/v1/workers/${workerId}/offline`, { action })
      return response.data
    },

    async cancelWorkerOffline(workerId) {
      const response = await axios.delete(`/api/v1/workers/${workerId}/offline`)
      return response.data
    }
  }
}) 