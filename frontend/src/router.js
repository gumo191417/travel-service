import {
  createRouter,
  createWebHistory,
} from 'vue-router'

import AgentView from './views/AgentView.vue'
import ChatView from './views/ChatView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/agent',
      name: 'agent',
      component: AgentView,
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export default router