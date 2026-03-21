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
  spotify_playlist_id?: string | null
  spotify_playlist_url?: string | null
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
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const handleGenerate = async () => {
    if (!text.trim() || isGenerating) return
    setIsGenerating(true)
    setError(null)
    setSaveError(null)
    setPlaylist(null)

    try {
      const { data } = await api.post<Playlist>('/playlist/generate', { text })
      setPlaylist(data)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data) {
        const data = err.response.data as { message?: string; error?: string }
        setError(data.message ?? data.error ?? 'Request failed. Please try again.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateAnother = () => {
    setPlaylist(null)
    setError(null)
    setSaveError(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
        {playlist && (
          <PlaylistResult
            playlist={playlist}
            onGenerateAnother={handleGenerateAnother}
            onPlaylistSaved={setPlaylist}
            isSaving={isSaving}
            saveError={saveError}
            onSaveError={setSaveError}
            onSavingChange={setIsSaving}
          />
        )}
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
        Curating your playlist…
      </p>
    </div>
  )
}

function PlaylistResult({
  playlist,
  onGenerateAnother,
  onPlaylistSaved,
  isSaving,
  saveError,
  onSaveError,
  onSavingChange,
}: {
  playlist: Playlist
  onGenerateAnother: () => void
  onPlaylistSaved: (p: Playlist) => void
  isSaving: boolean
  saveError: string | null
  onSaveError: (msg: string | null) => void
  onSavingChange: (v: boolean) => void
}) {
  const totalMin = Math.round(playlist.total_duration_ms / 60000)
  const saved = Boolean(playlist.spotify_playlist_id)

  const handleSaveToSpotify = async () => {
    if (saved || isSaving) return
    onSaveError(null)
    onSavingChange(true)
    try {
      const { data } = await api.post<Playlist>(`/playlist/${playlist.id}/save-to-spotify`)
      onPlaylistSaved(data)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data) {
        const data = err.response.data as { message?: string; error?: string }
        onSaveError(data.message ?? data.error ?? 'Could not save to Spotify.')
      } else {
        onSaveError('Could not save to Spotify. Please try again.')
      }
    } finally {
      onSavingChange(false)
    }
  }

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

      {saveError && (
        <p className="mt-4 text-sm text-red-500 text-center">{saveError}</p>
      )}

      {saved && (
        <p className="mt-4 text-sm text-center" style={{ color: 'var(--text)' }}>
          {playlist.spotify_playlist_url ? (
            <>
              Saved to Spotify —{' '}
              <a
                href={playlist.spotify_playlist_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline text-spotify-green"
              >
                Open in Spotify
              </a>
            </>
          ) : (
            'Saved to Spotify'
          )}
        </p>
      )}

      <button
        type="button"
        onClick={handleSaveToSpotify}
        disabled={saved || isSaving}
        className="mt-4 w-full py-3 rounded-full text-sm font-medium transition-opacity bg-spotify-green text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        {saved ? 'Saved to Spotify' : isSaving ? 'Saving…' : 'Save to Spotify'}
      </button>

      <button
        type="button"
        onClick={onGenerateAnother}
        className="mt-3 w-full py-3 rounded-full text-sm font-medium transition-opacity hover:opacity-90 cursor-pointer"
        style={{
          border: '1px solid var(--border)',
          color: 'var(--text-h)',
          background: 'transparent',
        }}
      >
        Generate another
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
