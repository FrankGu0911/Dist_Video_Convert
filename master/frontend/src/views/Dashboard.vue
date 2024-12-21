<template>
  <AppLayout>
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <!-- 统计卡片 -->
      <div v-for="stat in stats" :key="stat.name" class="overflow-hidden rounded-lg bg-white px-4 py-5 shadow dark:bg-gray-800 sm:p-6">
        <dt class="truncate text-sm font-medium text-gray-500 dark:text-gray-400">
          {{ stat.name }}
        </dt>
        <dd class="mt-1 text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
          {{ stat.value }}
        </dd>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">任务处理趋势</h3>
        <TasksChart class="mt-6" :height="300" />
      </div>
      
      <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Worker 状态分布</h3>
        <WorkerStatusChart class="mt-6" :height="300" />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from '../components/Layout/AppLayout.vue'
import TasksChart from '../components/Charts/TasksChart.vue'
import WorkerStatusChart from '../components/Charts/WorkerStatusChart.vue'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()

const stats = ref([
  { name: '活跃 Workers', value: '0' },
  { name: '运行中任务', value: '0' },
  { name: '今日完成任务', value: '0' }
])

onMounted(async () => {
  await appStore.fetchWorkers()
  await appStore.fetchTasks()
  
  // 更新统计数据
  stats.value = [
    { name: '活跃 Workers', value: appStore.workers.filter(w => w.status === 'active').length },
    { name: '运行中任务', value: appStore.tasks.filter(t => t.status === 'running').length },
    { name: '今日完成任务', value: appStore.tasks.filter(t => t.status === 'completed').length }
  ]
})
</script> 