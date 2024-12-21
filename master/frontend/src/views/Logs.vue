<template>
  <AppLayout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white">系统日志</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          查看系统运行日志和错误信息
        </p>
      </div>
      <div class="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
        <button
          type="button"
          class="btn-primary"
          @click="refreshLogs"
        >
          刷新
        </button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="mt-4 grid gap-4 sm:grid-cols-3">
      <!-- 日志级别多选 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">日志级别</label>
        <MultiSelect
          v-model="filters.log_level"
          :options="logLevels"
          placeholder="选择日志级别"
          class="mt-1"
        />
      </div>

      <!-- 时间筛选保持不变 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">开始时间</label>
        <input
          type="datetime-local"
          v-model="filters.start_time"
          class="input mt-1"
        />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">结束时间</label>
        <input
          type="datetime-local"
          v-model="filters.end_time"
          class="input mt-1"
        />
      </div>
    </div>
    
    <!-- 日志列表 -->
    <div class="mt-8 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
            <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th scope="col" class="w-48 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">时间</th>
                  <th scope="col" class="w-24 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">级别</th>
                  <th scope="col" class="w-32 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">任务ID</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">消息</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                <tr v-for="log in appStore.logs" :key="log.id">
                  <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-gray-500 dark:text-gray-400 sm:pl-6">
                    {{ formatDate(log.log_time) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span
                      :class="[
                        getLogLevelClass(log.log_level),
                        'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                      ]"
                    >
                      {{ getLogLevel(log.log_level) }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ log.task_id || '-' }}
                  </td>
                  <td class="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 break-all">
                    {{ log.log_message }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import AppLayout from '../components/Layout/AppLayout.vue'
import { useAppStore } from '../stores/app'
import apiService from '../api'
import MultiSelect from '../components/MultiSelect.vue'

dayjs.extend(utc)
dayjs.extend(timezone)

const appStore = useAppStore()

const logLevels = [
  { 
    value: 0, 
    label: 'DEBUG',
    class: 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
  },
  { 
    value: 1, 
    label: 'INFO',
    class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300'
  },
  { 
    value: 2, 
    label: 'WARNING',
    class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300'
  },
  { 
    value: 3, 
    label: 'ERROR',
    class: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300'
  }
]

const filters = ref({
  log_level: [], // 改为数组以支持多选
  start_time: '',
  end_time: '',
  sort_by: 'log_time',
  order: 'desc'
})

const pagination = ref({
  current_page: 1,
  per_page: 20,
  total: 0,
  pages: 0,
  has_next: false,
  has_prev: false
})

const formatDate = (date) => {
  if (!date) return '-'
  return dayjs.utc(date).local().format('YYYY-MM-DD HH:mm:ss')
}

const getLogLevel = (level) => {
  const levels = {
    0: 'DEBUG',
    1: 'INFO',
    2: 'WARNING',
    3: 'ERROR'
  }
  return levels[level] || '未知'
}

const getLogLevelClass = (level) => {
  const levelOption = logLevels.find(l => l.value === level)
  return levelOption?.class || 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
}

const refreshLogs = async () => {
  try {
    const params = {
      page: pagination.value.current_page,
      per_page: pagination.value.per_page,
      ...filters.value
    }
    
    // 清除空值
    Object.keys(params).forEach(key => {
      if (params[key] === '') {
        delete params[key]
      }
    })

    const response = await apiService.getLogs(params)
    appStore.logs = response.logs
    pagination.value = response.pagination
  } catch (error) {
    console.error('Error fetching logs:', error)
  }
}

watch(
  [
    () => filters.value.log_level,
    () => filters.value.start_time,
    () => filters.value.end_time,
    () => filters.value.sort_by,
    () => filters.value.order,
    () => pagination.value.per_page
  ],
  () => {
    pagination.value.current_page = 1
    refreshLogs()
  },
  { immediate: true }
)

onMounted(async () => {
  await refreshLogs()
})
</script>

<style scoped>
/* 添加一些样式来控制表格列宽 */
.w-48 {
  width: 12rem;
}
.w-24 {
  width: 6rem;
}
.w-32 {
  width: 8rem;
}
</style> 