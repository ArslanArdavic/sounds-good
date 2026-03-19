import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

export default function CallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setToken } = useAuth()
  const hasRun = useRef(false)

  useEffect(() => {
    if (hasRun.current) return
    hasRun.current = true

    const code = searchParams.get('code')
    const error = searchParams.get('error')

    if (error || !code) {
      navigate('/?error=access_denied', { replace: true })
      return
    }

    api
      .get<{ access_token: string }>(`/auth/callback?code=${code}`)
      .then(({ data }) => {
        setToken(data.access_token)
        navigate('/sync', { replace: true })
      })
      .catch((err: unknown) => {
        const status = axios.isAxiosError(err) ? err.response?.status : null
        if (status === 501) {
          navigate('/?error=not_implemented', { replace: true })
        } else {
          navigate('/?error=auth_failed', { replace: true })
        }
      })
  }, [])

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4">
      <MusicBars />
      <p className="text-sm" style={{ color: 'var(--text)' }}>
        Connecting your Spotify account…
      </p>
    </div>
  )
}

function MusicBars() {
  return (
    <div className="flex gap-1 items-end h-10">
      {[14, 22, 10, 18, 14].map((h, i) => (
        <span
          key={i}
          className="w-1.5 bg-spotify-green rounded-full animate-bounce"
          style={{ height: `${h}px`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  )
}
