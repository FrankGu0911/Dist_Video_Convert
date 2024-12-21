<template>
  <AppLayout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white">任务列表</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          所有视频转换任务的状态和进度
        </p>
      </div>
      <div class="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
        <button
          type="button"
          class="btn-primary"
          @click="refreshTasks"
        >
          刷新
        </button>
      </div>
    </div>
    
    <div class="mt-4 grid gap-4 sm:grid-cols-2">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">任务状态</label>
        <MultiSelect
          v-model="filters.status"
          :options="taskStatuses"
          placeholder="选择任务状态"
          class="mt-1"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">排序方式</label>
        <select v-model="filters.sort_by" class="input mt-1">
          <option value="start_time">开始时间</option>
          <option value="progress">进度</option>
          <option value="status">状态</option>
        </select>
      </div>
    </div>
    
    <div class="mt-8 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
            <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th scope="col" class="w-48 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">文件名</th>
                  <th scope="col" class="w-24 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">状态</th>
                  <th scope="col" class="w-64 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">进度</th>
                  <th scope="col" class="w-32 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">Worker</th>
                  <th scope="col" class="w-32 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">已用时间</th>
                  <th scope="col" class="w-32 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">剩余时间</th>
                  <th scope="col" class="w-24 px-3 py-3.5 pl-3 pr-4 sm:pr-6">
                    <span class="sr-only">操作</span>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                <tr v-for="task in appStore.tasks" :key="task.task_id">
                  <td class="truncate px-3 py-4 text-sm text-gray-500 dark:text-gray-400" :title="task.video_path">
                    {{ getFileName(task.video_path) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span
                      :class="[
                        task.status === 2 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                        task.status === 1 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                        task.status === 3 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
                        'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                      ]"
                    >
                      {{ getTaskStatus(task.status) }}
                    </span>
                  </td>
                  <td class="px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <div class="flex items-center gap-x-2">
                      <div class="flex-grow bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                        <div 
                          class="bg-primary-600 h-2.5 rounded-full"
                          :style="{ width: `${task.progress}%` }"
                        ></div>
                      </div>
                      <span class="flex-shrink-0 text-xs">{{ formatProgress(task.progress) }}%</span>
                    </div>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ getWorkerName(task.worker_id) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ formatTime(task.elapsed_time) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ formatTime(task.remaining_time) }}
                  </td>
                  <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button
                      @click="showTaskDetails(task)"
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

    <TransitionRoot as="template" :show="isDetailsOpen">
      <Dialog as="div" class="relative z-10" @close="closeDetails">
        <TransitionChild
          enter="ease-out duration-300"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="ease-in duration-200"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild
              enter="ease-out duration-300"
              enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enter-to="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leave-from="opacity-100 translate-y-0 sm:scale-100"
              leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6 dark:bg-gray-800">
                <div>
                  <div class="mt-3 sm:mt-5">
                    <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                      任务详情
                    </DialogTitle>
                    <div class="mt-4 space-y-3">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">源文件路径</label>
                        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400 break-all">{{ selectedTask?.video_path }}</p>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">保存路径</label>
                        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400 break-all">{{ selectedTask?.dest_path }}</p>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">处理时间</label>
                        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                          已用时间: {{ formatTime(selectedTask?.elapsed_time) }}
                          <br>
                          预计剩余: {{ formatTime(selectedTask?.remaining_time) }}
                        </p>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">处理进度</label>
                        <div class="mt-1">
                          <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                            <div 
                              class="bg-primary-600 h-2.5 rounded-full"
                              :style="{ width: `${selectedTask?.progress || 0}%` }"
                            ></div>
                          </div>
                          <span class="text-xs mt-1 text-gray-500 dark:text-gray-400">{{ formatProgress(selectedTask?.progress || 0) }}%</span>
                        </div>
                      </div>
                      <div v-if="selectedTask?.error_message || selectedTask?.status === 3">
                        <label class="block text-sm font-medium text-red-700 dark:text-red-300">错误信息</label>
                        <div class="mt-1 rounded-md bg-red-50 p-3 dark:bg-red-900/50">
                          <p class="text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap">
                            {{ selectedTask?.error_message || '任务执行失败' }}
                          </p>
                        </div>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">任务状态</label>
                        <p class="mt-1">
                          <span
                            :class="[
                              selectedTask?.status === 2 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                              selectedTask?.status === 1 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                              selectedTask?.status === 3 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                              'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
                              'inline-flex rounded-full px-2 py-1 text-xs font-semibold'
                            ]"
                          >
                            {{ getTaskStatus(selectedTask?.status) }}
                          </span>
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-6">
                  <button
                    type="button"
                    class="btn-primary w-full"
                    @click="closeDetails"
                  >
                    关闭
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import dayjs from 'dayjs'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue'
import AppLayout from '../components/Layout/AppLayout.vue'
import { useAppStore } from '../stores/app'
import MultiSelect from '../components/MultiSelect.vue'
import apiService from '../api'

const appStore = useAppStore()
const isDetailsOpen = ref(false)
const selectedTask = ref(null)

const getFileName = (path) => {
  if (!path) return '-'
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1]
}

const getTaskStatus = (status) => {
  const statuses = {
    0: '已创建',
    1: '运行中',
    2: '已完成',
    3: '失败'
  }
  return statuses[status] || '未知'
}

const formatTime = (seconds) => {
  if (!seconds) return '-'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}

const getWorkerName = (workerId) => {
  const worker = appStore.workers.find(w => w.worker_id === workerId)
  return worker ? worker.worker_name : '-'
}

const showTaskDetails = (task) => {
  selectedTask.value = task
  isDetailsOpen.value = true
}

const closeDetails = () => {
  isDetailsOpen.value = false
  selectedTask.value = null
}

const taskStatuses = [
  { 
    value: 0, 
    label: '已创建',
    class: 'bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300'
  },
  { 
    value: 1, 
    label: '运行中',
    class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300'
  },
  { 
    value: 2, 
    label: '已完成',
    class: 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300'
  },
  { 
    value: 3, 
    label: '失败',
    class: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300'
  }
]

const filters = ref({
  status: [],
  sort_by: 'start_time',
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

const refreshTasks = async () => {
  try {
    const params = {
      page: pagination.value.current_page,
      per_page: pagination.value.per_page
    }
    
    if (filters.value.status?.length) {
      params.status = filters.value.status
    }
    if (filters.value.sort_by) {
      params.sort_by = filters.value.sort_by
      params.order = filters.value.order
    }

    const tasksResponse = await apiService.getTasks(params)
    if (tasksResponse?.tasks) {
      appStore.tasks = tasksResponse.tasks
      if (tasksResponse.pagination) {
        pagination.value = tasksResponse.pagination
      }
    }

    if (!appStore.workers.length) {
      await appStore.fetchWorkers()
    }
  } catch (error) {
    console.error('Error fetching data:', error)
  }
}

watch(
  [
    () => filters.value.status,
    () => filters.value.sort_by,
    () => filters.value.order,
    () => pagination.value.per_page
  ],
  () => {
    pagination.value.current_page = 1
    refreshTasks()
  }
)

onMounted(async () => {
  pagination.value.current_page = 1
  await refreshTasks()
})

const formatProgress = (progress) => {
  if (!progress) return '0'
  if (Number.isInteger(progress)) return progress.toString()
  return progress.toFixed(1)
}
</script>

<style scoped>
.w-64 {
  width: 16rem;
}
.w-48 {
  width: 12rem;
}
.w-32 {
  width: 8rem;
}
.w-24 {
  width: 5rem;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style> 