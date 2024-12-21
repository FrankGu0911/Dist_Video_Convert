<template>
  <div class="relative h-full w-full">
    <!-- 加载状态 -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-gray-800/50">
      <div class="text-gray-500 dark:text-gray-400">
        加载中...
      </div>
    </div>
    
    <!-- 错误状态 -->
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-gray-800/50">
      <div class="text-red-500">
        数据加载失败
      </div>
    </div>
    
    <!-- 图表 -->
    <Doughnut
      v-if="!loading && !error"
      :data="chartData"
      :options="chartOptions"
      :height="height"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'
import api from '../../api'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  height: {
    type: Number,
    default: 300
  }
})

const loading = ref(true)
const error = ref(false)
const chartData = ref({
  labels: ['活跃', '空闲', '离线'],
  datasets: [
    {
      data: [],
      backgroundColor: [
        'rgba(14, 165, 233, 0.8)',  // 活跃 - 蓝色
        'rgba(34, 197, 94, 0.8)',   // 空闲 - 绿色
        'rgba(239, 68, 68, 0.8)',   // 离线 - 红色
      ]
    }
  ]
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    }
  }
}))

const fetchChartData = async () => {
  loading.value = true
  error.value = false
  
  try {
    const response = await api.get('/workers/stats')
    // 假设后端返回的数据格式为 { active: number, idle: number, offline: number }
    chartData.value.datasets[0].data = [
      response.active || 0,
      response.idle || 0,
      response.offline || 0
    ]
  } catch (err) {
    console.error('Failed to fetch worker stats:', err)
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchChartData()
})
</script> 