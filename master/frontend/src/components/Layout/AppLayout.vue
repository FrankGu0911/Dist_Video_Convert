<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <!-- 侧边栏 -->
    <Sidebar />
    
    <!-- 主内容区 -->
    <div class="lg:pl-64">
      <!-- 顶部导航栏 -->
      <Navbar />
      
      <!-- 页面内容 -->
      <main class="py-6">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <slot></slot>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import Navbar from './Navbar.vue'
import Sidebar from './Sidebar.vue'
</script> 