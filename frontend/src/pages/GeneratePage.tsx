import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface Track {
  id: string
  name: string
  artist: string
  duration_ms: number
}

interface Playlist {
  id: string
  name: string
  total_duration_ms: number
  track_count: number
  playlist_tracks: Array<{ position: number; track: Track }>
}

const EXAMPLE_PROMPTS = [
  'A jazzy Sunday morning, around 60 minutes',
  'High energy workout mix, 45 minutes',
  'Late night focus, no lyrics, 90 minutes',
  'Feel-good road trip, 2 hours',
]

export default function GeneratePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [playlist, setPlaylist] = useState<Playlist | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    if (!text.trim() || isGenerating) return
    setIsGenerating(true)
    setError(null)
    setPlaylist(null)

    try {
      const { data } = await api.post<Playlist>('/playlist/generate', { text })
      setPlaylist(data)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 501) {
        setError('Playlist generation is not yet implemented — coming in Phase 4.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="flex flex-col flex-1">
      <Header onLogout={logout} onResync={() => navigate('/sync')} spotifyId={user?.spotify_id} />

      <main className="flex-1 px-6 py-10 max-w-2xl mx-auto w-full">
        <h1 className="text-2xl font-semibold tracking-tight mb-1" style={{ color: 'var(--text-h)' }}>
          What do you want to hear?
        </h1>
        <p className="text-sm mb-6" style={{ color: 'var(--text)' }}>
          Describe your mood, vibe, or occasion — we'll pick the tracks from your library.
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => setText(prompt)}
              className="text-xs px-3 py-1.5 rounded-full transition-colors cursor-pointer"
              style={{
                border: '1px solid var(--border)',
                color: 'var(--text)',
                background: 'var(--code-bg)',
              }}
            >
              {prompt}
            </button>
          ))}
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. A jazzy Sunday morning playlist, around 60 minutes…"
          rows={4}
          className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none transition-colors"
          style={{
            border: '1px solid var(--border)',
            background: 'var(--code-bg)',
            color: 'var(--text-h)',
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = '#1DB954')}
          onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
        />

        <button
          onClick={handleGenerate}
          disabled={!text.trim() || isGenerating}
          className="mt-4 w-full py-3 rounded-full bg-spotify-green text-white font-medium text-sm transition-opacity hover:opacity-90 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
        >
          {isGenerating ? 'Generating…' : 'Generate Playlist'}
        </button>

        {error && (
          <p className="mt-4 text-sm text-red-500 text-center">{error}</p>
        )}

        {isGenerating && <GeneratingState />}
        {playlist && <PlaylistResult playlist={playlist} />}
        {!isGenerating && !playlist && !error && <EmptyState />}
      </main>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="mt-12 text-center">
      <div className="inline-flex items-end gap-1 mb-4">
        {[10, 18, 14, 22, 12, 16].map((h, i) => (
          <span
            key={i}
            className="w-1.5 rounded-full"
            style={{ height: `${h}px`, background: 'var(--border)' }}
          />
        ))}
      </div>
      <p className="text-sm" style={{ color: 'var(--text)' }}>
        Your playlist will appear here
      </p>
    </div>
  )
}

function GeneratingState() {
  return (
    <div className="mt-12 text-center">
      <div className="flex justify-center items-end gap-1 mb-4">
        {[10, 18, 14, 22, 12, 16].map((h, i) => (
          <span
            key={i}
            className="w-1.5 bg-spotify-green rounded-full animate-bounce"
            style={{ height: `${h}px`, animationDelay: `${i * 0.08}s` }}
          />
        ))}
      </div>
      <p className="text-sm" style={{ color: 'var(--text)' }}>
        Searching your library…
      </p>
    </div>
  )
}

function PlaylistResult({ playlist }: { playlist: Playlist }) {
  const totalMin = Math.round(playlist.total_duration_ms / 60000)

  return (
    <div className="mt-8">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-lg font-medium" style={{ color: 'var(--text-h)' }}>
          {playlist.name}
        </h2>
        <span className="text-sm" style={{ color: 'var(--text)' }}>
          {playlist.track_count} tracks · {totalMin} min
        </span>
      </div>

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        {playlist.playlist_tracks.map(({ position, track }) => (
          <div
            key={track.id}
            className="flex items-center gap-4 px-4 py-3"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            <span className="text-xs w-5 text-right shrink-0" style={{ color: 'var(--text)' }}>
              {position}
            </span>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--text-h)' }}>
                {track.name}
              </p>
              <p className="text-xs truncate" style={{ color: 'var(--text)' }}>
                {track.artist}
              </p>
            </div>
            <span className="text-xs shrink-0" style={{ color: 'var(--text)' }}>
              {formatDuration(track.duration_ms)}
            </span>
          </div>
        ))}
      </div>

      <button className="mt-4 w-full py-3 rounded-full text-sm font-medium transition-opacity hover:opacity-90 cursor-pointer bg-spotify-green text-white">
        Save to Spotify
      </button>
    </div>
  )
}

function Header({
  onLogout,
  onResync,
  spotifyId,
}: {
  onLogout: () => void
  onResync: () => void
  spotifyId?: string
}) {
  return (
    <header
      className="flex items-center justify-between px-6 py-4 border-b"
      style={{ borderColor: 'var(--border)' }}
    >
      <span className="font-medium text-sm" style={{ color: 'var(--text-h)' }}>
        Sounds Good
      </span>
      <div className="flex items-center gap-2">
        {spotifyId && (
          <span className="text-sm" style={{ color: 'var(--text)' }}>
            {spotifyId}
          </span>
        )}
        <button
          onClick={onResync}
          className="text-xs px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          style={{ color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          Re-sync
        </button>
        <button
          onClick={onLogout}
          className="text-xs px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          style={{ color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          Log out
        </button>
      </div>
    </header>
  )
}

function formatDuration(ms: number): string {
  const totalSec = Math.round(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}
