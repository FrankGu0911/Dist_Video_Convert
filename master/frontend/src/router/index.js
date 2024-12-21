import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/tasks'
  },
  {
    path: '/videos',
    name: 'Videos',
    component: () => import('../views/Videos.vue')
  },
  {
    path: '/workers',
    name: 'Workers',
    component: () => import('../views/Workers.vue')
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/Tasks.vue')
  },
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('../views/Logs.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 