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
                    <span
                      :class="[
                        worker.status === 1 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                        'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
                        'inline-flex rounded-full px-2 text-xs font-semibold leading-5'
                      ]"
                    >
                      {{ worker.status === 1 ? '在线' : '离线' }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ getWorkerType(worker.worker_type) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {{ worker.support_vr === 1 ? '支持' : '不支持' }}
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
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import AppLayout from '../components/Layout/AppLayout.vue'
import { useAppStore } from '../stores/app'

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