import { useState } from 'react'
import axios from 'axios'
import api from '../services/api'

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConnect = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await api.get<{ url: string }>('/auth/login')
      window.location.href = data.url
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 501) {
        setError('Spotify OAuth is not yet implemented — coming in Phase 1.')
      } else {
        setError('Something went wrong. Please try again.')
      }
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 py-20">
      <div className="w-full max-w-sm text-center">
        <MusicIcon />

        <h1 className="text-4xl font-semibold tracking-tight mt-6 mb-3" style={{ color: 'var(--text-h)' }}>
          Sounds Good
        </h1>
        <p className="text-base mb-10" style={{ color: 'var(--text)' }}>
          Generate playlists from your Spotify library using AI — only tracks you already own.
        </p>

        <button
          onClick={handleConnect}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-3 px-6 py-3.5 rounded-full bg-spotify-green text-white font-medium text-base transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
        >
          <SpotifyIcon />
          {isLoading ? 'Connecting…' : 'Connect with Spotify'}
        </button>

        {error && (
          <p className="mt-4 text-sm text-red-500">{error}</p>
        )}

        <p className="mt-8 text-xs" style={{ color: 'var(--text)' }}>
          We only read your playlists. We never modify or delete anything without your explicit action.
        </p>
      </div>
    </div>
  )
}

function MusicIcon() {
  return (
    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-spotify-green/10">
      <svg className="w-8 h-8 text-spotify-green" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z" />
      </svg>
    </div>
  )
}

function SpotifyIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
    </svg>
  )
}
