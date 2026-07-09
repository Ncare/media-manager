import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
  { path: '/libraries', name: 'libraries', component: () => import('@/views/Libraries.vue') },
  { path: '/movies', name: 'movies', component: () => import('@/views/MovieList.vue') },
  { path: '/movies/:id', name: 'movie-detail', component: () => import('@/views/MovieDetail.vue'), props: true },
  { path: '/tv', name: 'tv', component: () => import('@/views/TvList.vue') },
  { path: '/tv/:id', name: 'tv-detail', component: () => import('@/views/TvDetail.vue'), props: true },
  { path: '/rename', name: 'rename', component: () => import('@/views/RenamePreview.vue') },
  { path: '/settings', name: 'settings', component: () => import('@/views/Settings.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
