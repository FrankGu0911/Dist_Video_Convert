import { defineStore } from 'pinia'
import api from '../api'

export const useAppStore = defineStore('app', {
  state: () => ({
    darkMode: localStorage.getItem('darkMode') === 'true',
    sidebarOpen: window.innerWidth >= 1024,
    workers: [],
    tasks: [],
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
    
    async fetchWorkers() {
      try {
        const data = await api.getWorkers()
        this.workers = data || []
      } catch (error) {
        console.error('Error fetching workers:', error)
        this.workers = []
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
    
    async fetchLogs() {
      try {
        const data = await api.getLogs()
        this.logs = data || []
      } catch (error) {
        console.error('Error fetching logs:', error)
        this.logs = []
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
    }
  }
}) 