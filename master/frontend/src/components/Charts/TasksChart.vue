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
    <Line
      v-if="!loading && !error"
      :data="chartData"
      :options="chartOptions"
      :height="height"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import api from '../../api'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  height: {
    type: Number,
    default: 300
  }
})

const loading = ref(true)
const error = ref(false)
const chartData = ref({
  labels: [],
  datasets: [
    {
      label: '完成任务数',
      data: [],
      borderColor: 'rgb(14, 165, 233)',
      backgroundColor: 'rgba(14, 165, 233, 0.5)',
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
  },
  scales: {
    y: {
      beginAtZero: true
    }
  }
}))

const fetchChartData = async () => {
  loading.value = true
  error.value = false
  
  try {
    const response = await api.get('/tasks/stats')
    // 假设后端返回的数据格式为 { labels: [], data: [] }
    chartData.value.labels = response.labels
    chartData.value.datasets[0].data = response.data
  } catch (err) {
    console.error('Failed to fetch chart data:', err)
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchChartData()
})
</script> 