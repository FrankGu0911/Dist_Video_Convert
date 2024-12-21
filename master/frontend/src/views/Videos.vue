<template>
  <AppLayout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white">视频列表</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          所有视频文件及其转码状态
        </p>
      </div>
      <div class="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
        <button
          type="button"
          class="btn-primary"
          @click="refreshVideos"
        >
          刷新
        </button>
      </div>
    </div>

    <!-- 筛选器部分 -->
    <div class="mt-4 grid gap-4 sm:grid-cols-3">
      <!-- 转码状态多选 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">转码状态</label>
        <MultiSelect
          v-model="filters.transcode_status"
          :options="transcodeStatuses"
          placeholder="选择转码状态"
          class="mt-1"
        />
      </div>

      <!-- 编码格式多选 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">编码格式</label>
        <MultiSelect
          v-model="filters.codec"
          :options="codecOptions"
          placeholder="选择编码格式"
          class="mt-1"
        />
      </div>

      <!-- VR视频 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">VR视频</label>
        <select v-model="filters.is_vr" class="input mt-1">
          <option value="">全部</option>
          <option value="0">非VR</option>
          <option value="1">VR</option>
        </select>
      </div>
    </div>

    <!-- 视频列表 -->
    <div class="mt-8 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
            <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th 
                    v-for="column in columns" 
                    :key="column.key"
                    scope="col" 
                    class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                    @click="sortBy(column.key)"
                  >
                    <div class="flex items-center gap-x-2">
                      {{ column.label }}
                      <span class="text-primary-600">
                        {{ getSortIcon(column.key) }}
                      </span>
                    </div>
                  </th>
                  <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                    <span class="sr-only">操作</span>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                <tr v-for="video in videos" :key="video.id">
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ getFileName(video.video_path) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span
                      :class="[
                        getCodecClass(video.codec),
                        'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                      ]"
                    >
                      {{ video.codec.toUpperCase() }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ formatBitrate(video.bitrate_k) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ `${video.resolution.width}x${video.resolution.height}` }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ formatSize(video.video_size) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span
                      :class="[
                        getStatusClass(video.transcode_status),
                        'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                      ]"
                    >
                      {{ getTranscodeStatus(video.transcode_status) }}
                    </span>
                  </td>
                  <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button
                      @click="showVideoDetails(video)"
                      class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300"
                    >
                      详情
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="mt-4 flex items-center justify-between">
      <div class="flex items-center">
        <select v-model="pagination.per_page" class="input" @change="refreshVideos">
          <option value="10">10条/页</option>
          <option value="20">20条/页</option>
          <option value="50">50条/页</option>
          <option value="100">100条/页</option>
        </select>
      </div>
      <div class="flex items-center space-x-2">
        <button
          :disabled="!pagination.has_prev"
          @click="changePage(pagination.current_page - 1)"
          class="btn-secondary"
          :class="{ 'opacity-50 cursor-not-allowed': !pagination.has_prev }"
        >
          上一页
        </button>
        <span class="text-sm text-gray-700 dark:text-gray-300">
          第 {{ pagination.current_page }} 页 / 共 {{ pagination.pages }} 页
        </span>
        <button
          :disabled="!pagination.has_next"
          @click="changePage(pagination.current_page + 1)"
          class="btn-secondary"
          :class="{ 'opacity-50 cursor-not-allowed': !pagination.has_next }"
        >
          下一页
        </button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import AppLayout from '../components/Layout/AppLayout.vue'
import api from '../api'
import MultiSelect from '../components/MultiSelect.vue'

const videos = ref([])
const transcodeStatuses = [
  { 
    value: 0, 
    label: '无需转码',
    class: 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
  },
  { 
    value: 1, 
    label: '等待转码',
    class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300'
  },
  { 
    value: 2, 
    label: '已创建任务',
    class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300'
  },
  { 
    value: 3, 
    label: '正在转码',
    class: 'bg-primary-100 text-primary-800 dark:bg-primary-900/50 dark:text-primary-300'
  },
  { 
    value: 4, 
    label: '转码完成',
    class: 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300'
  },
  { 
    value: 5, 
    label: '转码失败',
    class: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300'
  }
]

const codecOptions = [
  { 
    value: 'h264', 
    label: 'H.264',
    class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300'
  },
  { 
    value: 'hevc', 
    label: 'HEVC',
    class: 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300'
  },
  { 
    value: 'av1', 
    label: 'AV1',
    class: 'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300'
  }
]

const filters = ref({
  transcode_status: [],
  codec: [],
  is_vr: '',
  sort_by: 'video_path',
  order: 'asc'
})

// 定义列配置
const columns = [
  { key: 'video_path', label: '文件名' },
  { key: 'codec', label: '编码' },
  { key: 'bitrate_k', label: '码率' },
  { key: 'resolutionall', label: '分辨率' },
  { key: 'video_size', label: '大小' },
  { key: 'transcode_status', label: '状态' }
]

const pagination = ref({
  current_page: 1,
  per_page: 20,
  total: 0,
  pages: 0,
  has_next: false,
  has_prev: false
})

// 排序处理函数
const sortBy = (key) => {
  if (filters.value.sort_by === key) {
    if (filters.value.order === 'asc') {
      filters.value.order = 'desc'
    } else if (filters.value.order === 'desc') {
      // 取消排序
      filters.value.sort_by = ''
      filters.value.order = 'asc'
    }
  } else {
    // 新字段默认升序
    filters.value.sort_by = key
    filters.value.order = 'asc'
  }
}

const getFileName = (path) => {
  if (!path) return '-'
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1]
}

const formatBitrate = (bitrate) => {
  if (bitrate >= 1000) {
    return `${(bitrate / 1000).toFixed(1)} Mbps`
  }
  return `${bitrate} Kbps`
}

const formatSize = (size) => {
  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} GB`
  }
  return `${size.toFixed(1)} MB`
}

const getTranscodeStatus = (status) => {
  const statuses = {
    0: '无需转码',
    1: '等待转码',
    2: '已创建任务',
    3: '正在转码',
    4: '转码完成',
    5: '转码失败'
  }
  return statuses[status] || '未知'
}

// 添加 debouncedRefresh 变量
const debouncedRefresh = ref(null)

// 修改 refreshWithDebounce 函数
const refreshWithDebounce = () => {
  if (debouncedRefresh.value) {
    clearTimeout(debouncedRefresh.value)
  }
  debouncedRefresh.value = setTimeout(() => {
    pagination.value.current_page = 1
    refreshVideos()
  }, 300)
}

// 分别监听各个筛选条件
watch(() => filters.value.transcode_status, refreshWithDebounce, { immediate: true })
watch(() => filters.value.codec, refreshWithDebounce)
watch(() => filters.value.is_vr, refreshWithDebounce)
watch(() => filters.value.sort_by, refreshWithDebounce)
watch(() => filters.value.order, refreshWithDebounce)
watch(() => pagination.value.per_page, refreshWithDebounce)

// 修改 refreshVideos 函数
const refreshVideos = async () => {
  try {
    const params = {
      page: pagination.value.current_page,
      per_page: pagination.value.per_page
    }
    
    // 只添加有值的参数
    if (filters.value.transcode_status?.length) {
      params.transcode_status = filters.value.transcode_status
    }
    if (filters.value.codec?.length) {
      params.codec = filters.value.codec
    }
    if (filters.value.is_vr !== '') {
      params.is_vr = filters.value.is_vr
    }
    if (filters.value.sort_by) {
      params.sort_by = filters.value.sort_by
    }
    if (filters.value.order) {
      params.order = filters.value.order
    }

    console.log('Fetching with params:', params)
    const response = await api.getVideos(params)
    console.log('Response:', response)

    if (response?.videos) {
      videos.value = response.videos
      if (response.pagination) {
        pagination.value = response.pagination
      }
    }
  } catch (error) {
    console.error('Error fetching videos:', error)
    videos.value = []
  }
}

// 修改页码变化处理
const changePage = (page) => {
  if (page !== pagination.value.current_page) {
    pagination.value.current_page = page
    refreshVideos()
  }
}

// 初始加载
onMounted(() => {
  refreshVideos()
})

// 清理
onUnmounted(() => {
  if (debouncedRefresh.value) {
    clearTimeout(debouncedRefresh.value)
  }
})

const getSortIcon = (key) => {
  if (filters.value.sort_by !== key) return '○'
  return filters.value.order === 'asc' ? '↑' : '↓'
}

// 添加获取状态样式的方法
const getStatusClass = (status) => {
  const statusOption = transcodeStatuses.find(s => s.value === status)
  return statusOption?.class || 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
}

// 添加获取编码样式的方法
const getCodecClass = (codec) => {
  const codecOption = codecOptions.find(c => c.value === codec.toLowerCase())
  return codecOption?.class || 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
}
</script>

<style scoped>
/* 添加一些过渡效果 */
.cursor-pointer {
  transition: background-color 0.2s;
}

th:hover .text-primary-600 {
  opacity: 0.8;
}
</style> 