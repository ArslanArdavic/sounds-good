import { createContext, useContext, useState, type ReactNode, createElement } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'

interface User {
  id: string
  spotify_id: string
  created_at: string
}

interface AuthContextValue {
  token: string | null
  user: User | undefined
  isAuthenticated: boolean
  isLoading: boolean
  setToken: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setTokenState] = useState<string | null>(
    () => localStorage.getItem('auth_token'),
  )

  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const response = await api.get<User>('/auth/me')
      return response.data
    },
    enabled: !!token,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const setToken = (newToken: string) => {
    localStorage.setItem('auth_token', newToken)
    setTokenState(newToken)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setTokenState(null)
    queryClient.clear()
  }

  return createElement(
    AuthContext.Provider,
    { value: { token, user, isAuthenticated: !!token && !!user, isLoading, setToken, logout } },
    children,
  )
}

function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}

export { AuthProvider, useAuth }
