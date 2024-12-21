<template>
  <nav class="bg-white shadow dark:bg-gray-800">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 justify-between">
        <div class="flex">
          <!-- 移动端菜单按钮 -->
          <button
            type="button"
            class="lg:hidden px-4 text-gray-500 focus:outline-none"
            @click="appStore.toggleSidebar"
          >
            <Bars3Icon class="h-6 w-6" />
          </button>
        </div>
        
        <div class="flex items-center">
          <!-- 暗色模式切换 -->
          <button
            @click="appStore.toggleDarkMode"
            class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
          >
            <SunIcon v-if="appStore.darkMode" class="h-5 w-5" />
            <MoonIcon v-else class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { Bars3Icon, SunIcon, MoonIcon } from '@heroicons/vue/24/outline'
import { useAppStore } from '../../stores/app'

const appStore = useAppStore()
</script> 