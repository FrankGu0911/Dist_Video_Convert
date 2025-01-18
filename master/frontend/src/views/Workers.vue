<template>
  <AppLayout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white">Workers</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          所有工作节点的状态和详细信息
        </p>
      </div>
      <div class="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
        <button
          type="button"
          class="btn-primary"
          @click="refreshWorkers"
        >
          刷新
        </button>
      </div>
    </div>
    
    <div class="mt-8 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
            <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">ID</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">名称</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">状态</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">类型</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">支持 VR</th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">下线状态</th>
                  <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                    <span class="sr-only">操作</span>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                <tr v-for="worker in appStore.workers" :key="worker.worker_id">
                  <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-gray-500 dark:text-gray-400 sm:pl-6">
                    {{ worker.worker_id }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ worker.worker_name }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span :class="[
                      worker.status === 1 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
                      'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                    ]">
                      {{ worker.status === 1 ? '在线' : '离线' }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ getWorkerType(worker.worker_type) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ worker.support_vr === 1 ? '支持' : '不支持' }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span v-if="worker.offline_action" 
                          class="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300 inline-flex rounded-full px-2 text-xs font-semibold leading-5">
                      {{ worker.offline_action === 'shutdown' ? '即将关机' : '即将下线' }}
                    </span>
                    <span v-else class="text-gray-500 dark:text-gray-400">-</span>
                  </td>
                  <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button
                      :class="[
                        worker.offline_action 
                          ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300 dark:hover:bg-green-800' 
                          : 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 dark:hover:bg-red-800',
                        'rounded-md px-3 py-2 text-sm font-semibold shadow-sm',
                        worker.status === 0 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                      ]"
                      :disabled="worker.status === 0"
                      @click="worker.offline_action ? handleCancelOffline(worker) : handleOffline(worker)"
                    >
                      {{ worker.offline_action ? '恢复节点' : '停止节点' }}
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
        <label class="mr-2 text-sm text-gray-700 dark:text-gray-300">每页显示:</label>
        <select
          v-model="pagination.per_page"
          class="input w-20"
        >
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
      
      <div class="flex items-center space-x-2">
        <button
          class="btn-secondary"
          :disabled="!pagination.has_prev"
          @click="pagination.current_page--"
        >
          上一页
        </button>
        <span class="text-sm text-gray-700 dark:text-gray-300">
          第 {{ pagination.current_page }}/{{ pagination.pages }} 页
          (共 {{ pagination.total }} 条)
        </span>
        <button
          class="btn-secondary"
          :disabled="!pagination.has_next"
          @click="pagination.current_page++"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 添加停止节点确认对话框 -->
    <Dialog :open="showOfflineDialog" @close="showOfflineDialog = false" class="relative z-50">
      <div class="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div class="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel class="mx-auto max-w-sm rounded bg-white p-6 dark:bg-gray-800">
          <DialogTitle class="text-lg font-medium leading-6 text-gray-900 dark:text-white">
            停止节点确认
          </DialogTitle>
          <div class="mt-4">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              是否需要让 {{ selectedWorker?.worker_name }} 停止服务？
            </p>
            <div class="mt-4 flex items-center">
              <input
                type="checkbox"
                id="shutdown"
                v-model="shouldShutdown"
                class="h-4 w-4 rounded border-gray-300"
              />
              <label for="shutdown" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
                同时关闭计算机
              </label>
            </div>
          </div>
          <div class="mt-6 flex justify-end space-x-3">
            <button class="btn-secondary" @click="showOfflineDialog = false">
              取消
            </button>
            <button class="btn-primary" @click="confirmOffline">
              确认
            </button>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import AppLayout from '../components/Layout/AppLayout.vue'
import { useAppStore } from '../stores/app'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/vue'

const appStore = useAppStore()

const filters = ref({
  status: [],
  sort_by: 'last_heartbeat',
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
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const refreshWorkers = async () => {
  try {
    const params = {
      page: pagination.value.current_page,
      per_page: pagination.value.per_page
    }
    const response = await appStore.fetchWorkers(params)
    if (response?.pagination) {
      pagination.value = response.pagination
    }
  } catch (error) {
    console.error('Error fetching workers:', error)
  }
}

const getWorkerType = (type) => {
  const types = {
    0: 'CPU',
    1: 'NVENC',
    2: 'QSV',
    3: 'VPU'
  }
  return types[type] || '未知'
}

const showOfflineDialog = ref(false)
const selectedWorker = ref(null)
const shouldShutdown = ref(false)

// 处理停止节点
const handleOffline = (worker) => {
  selectedWorker.value = worker
  shouldShutdown.value = false
  showOfflineDialog.value = true
}

// 确认停止节点
const confirmOffline = async () => {
  try {
    await appStore.setWorkerOffline(
      selectedWorker.value.worker_id, 
      shouldShutdown.value ? 'shutdown' : 'offline'
    )
    showOfflineDialog.value = false
    await refreshWorkers()
  } catch (error) {
    console.error('设置下线失败:', error)
  }
}

// 处理恢复节点
const handleCancelOffline = async (worker) => {
  try {
    await appStore.cancelWorkerOffline(worker.worker_id)
    await refreshWorkers()
  } catch (error) {
    console.error('取消下线失败:', error)
  }
}

watch(() => filters.status, () => {
  pagination.current_page = 1;
  refreshWorkers();
}, { deep: true })

watch(() => filters.sort_by, () => {
  pagination.current_page = 1;
  refreshWorkers();
})

watch(() => filters.order, () => {
  pagination.current_page = 1;
  refreshWorkers();
})

watch(() => pagination.per_page, () => {
  pagination.current_page = 1;
  refreshWorkers();
})

watch(() => pagination.current_page, () => {
  refreshWorkers();
})

onMounted(async () => {
  await refreshWorkers()
})
</script> 