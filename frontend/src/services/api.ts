import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL as string,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const isAuthRoute =
      window.location.pathname === '/' || window.location.pathname === '/callback'

    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      !isAuthRoute
    ) {
      localStorage.removeItem('auth_token')
      window.location.href = '/'
    }

    return Promise.reject(error)
  },
)

export default api
