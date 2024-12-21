<template>
  <div class="flex h-16 shrink-0 items-center">
    <h1 class="text-lg font-semibold text-gray-900 dark:text-white">视频转换系统</h1>
  </div>
  <nav class="flex flex-1 flex-col">
    <ul role="list" class="flex flex-1 flex-col gap-y-7">
      <li>
        <ul role="list" class="-mx-2 space-y-1">
          <li v-for="item in navigation" :key="item.name">
            <RouterLink
              :to="item.to"
              :class="[
                route.name === item.name
                  ? 'bg-gray-50 text-primary-600 dark:bg-gray-700 dark:text-primary-400'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-primary-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-primary-400',
                'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6'
              ]"
            >
              <component
                :is="item.icon"
                :class="[
                  route.name === item.name ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 group-hover:text-primary-600 dark:group-hover:text-primary-400',
                  'h-6 w-6 shrink-0'
                ]"
              />
              {{ item.name }}
            </RouterLink>
          </li>
        </ul>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import {
  ComputerDesktopIcon,
  QueueListIcon,
  DocumentTextIcon,
  FilmIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()

const navigation = [
  { name: 'Tasks', to: '/tasks', icon: QueueListIcon },
  { name: 'Videos', to: '/videos', icon: FilmIcon },
  { name: 'Workers', to: '/workers', icon: ComputerDesktopIcon },
  { name: 'Logs', to: '/logs', icon: DocumentTextIcon },
]
</script> 