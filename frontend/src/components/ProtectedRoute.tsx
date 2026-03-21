import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function Spinner() {
  return (
    <div className="flex gap-1 items-end">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className="w-1 bg-spotify-green rounded-full animate-bounce"
          style={{ height: `${16 + i * 6}px`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  )
}
