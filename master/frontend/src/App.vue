<template>
  <RouterView />
</template>

<script setup>
import { RouterView } from 'vue-router'
import { useAppStore } from './stores/app'
import { onMounted, onUnmounted } from 'vue'

const appStore = useAppStore()

// 监听窗口大小变化
const handleResize = () => {
  appStore.handleResize()
}

onMounted(() => {
  // 从 localStorage 读取暗色模式设置
  const isDark = localStorage.getItem('darkMode') === 'true'
  // 如果没有存储的设置，则使用系统偏好
  if (isDark === null) {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    appStore.darkMode = prefersDark
    localStorage.setItem('darkMode', prefersDark)
  }
  
  // 根据当前设置应用暗色模式
  if (appStore.darkMode) {
    document.documentElement.classList.add('dark')
  }

  // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize)
  // 初始化时执行一次
  handleResize()
})

onUnmounted(() => {
  // 清理监听器
  window.removeEventListener('resize', handleResize)
})
</script> 