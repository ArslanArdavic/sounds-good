import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useSyncProgress } from '../hooks/useSyncProgress'

export default function SyncPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { status, playlistsDone, totalPlaylists, tracksDone, error, startSync, reset } =
    useSyncProgress()

  useEffect(() => {
    if (status === 'complete') {
      const timer = setTimeout(() => navigate('/generate'), 1500)
      return () => clearTimeout(timer)
    }
  }, [status, navigate])

  return (
    <div className="flex flex-col flex-1">
      <Header onLogout={logout} spotifyId={user?.spotify_id} />

      <div className="flex flex-col items-center justify-center flex-1 px-6 py-20 text-center">
        {status === 'idle' && <IdleState onSync={startSync} />}
        {(status === 'starting' || status === 'syncing') && (
          <SyncingState
            playlistsDone={playlistsDone}
            totalPlaylists={totalPlaylists}
            tracksDone={tracksDone}
          />
        )}
        {status === 'complete' && (
          <CompleteState tracksDone={tracksDone} totalPlaylists={totalPlaylists} />
        )}
        {status === 'error' && <ErrorState message={error} onRetry={reset} />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function IdleState({ onSync }: { onSync: () => void }) {
  return (
    <>
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-spotify-green/10 mb-6">
        <svg className="w-8 h-8 text-spotify-green" viewBox="0 0 24 24" fill="currentColor">
          <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />
        </svg>
      </div>
      <h1
        className="text-3xl font-semibold tracking-tight mb-3"
        style={{ color: 'var(--text-h)' }}
      >
        Sync your library
      </h1>
      <p className="text-base max-w-sm mb-2" style={{ color: 'var(--text)' }}>
        We'll fetch all your Spotify playlists and index your tracks so the AI can search through
        them.
      </p>
      <p className="text-sm mb-10" style={{ color: 'var(--text)' }}>
        This takes about 10 seconds for up to 10,000 tracks.
      </p>
      <button
        onClick={onSync}
        className="flex items-center gap-2 px-8 py-3 rounded-full bg-spotify-green text-white font-medium text-base transition-opacity hover:opacity-90 cursor-pointer"
      >
        Sync library
      </button>
    </>
  )
}

function SyncingState({
  playlistsDone,
  totalPlaylists,
  tracksDone,
}: {
  playlistsDone: number
  totalPlaylists: number
  tracksDone: number
}) {
  const pct = totalPlaylists > 0 ? Math.round((playlistsDone / totalPlaylists) * 100) : 0

  return (
    <>
      <MusicBarsIcon />
      <h1
        className="text-2xl font-semibold tracking-tight mb-2"
        style={{ color: 'var(--text-h)' }}
      >
        Syncing your library…
      </h1>
      <p className="text-sm mb-8" style={{ color: 'var(--text)' }}>
        {totalPlaylists > 0
          ? `${playlistsDone} / ${totalPlaylists} playlists · ${tracksDone.toLocaleString()} tracks found`
          : 'Connecting to Spotify…'}
      </p>

      <div className="w-full max-w-xs h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div
          className="h-full rounded-full bg-spotify-green transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      {totalPlaylists > 0 && (
        <p className="mt-2 text-xs" style={{ color: 'var(--text)' }}>
          {pct}% complete
        </p>
      )}
    </>
  )
}

function CompleteState({
  tracksDone,
  totalPlaylists,
}: {
  tracksDone: number
  totalPlaylists: number
}) {
  return (
    <>
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-spotify-green/10 mb-6">
        <svg className="w-8 h-8 text-spotify-green" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
        </svg>
      </div>
      <h1
        className="text-2xl font-semibold tracking-tight mb-2"
        style={{ color: 'var(--text-h)' }}
      >
        Library synced!
      </h1>
      <p className="text-base" style={{ color: 'var(--text)' }}>
        {tracksDone.toLocaleString()} tracks from {totalPlaylists} playlists ready.
      </p>
      <p className="text-sm mt-4" style={{ color: 'var(--text)' }}>
        Taking you to the generator…
      </p>
    </>
  )
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string | null
  onRetry: () => void
}) {
  return (
    <>
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-500/10 mb-6">
        <svg className="w-8 h-8 text-red-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
        </svg>
      </div>
      <h1 className="text-2xl font-semibold tracking-tight mb-2" style={{ color: 'var(--text-h)' }}>
        Sync failed
      </h1>
      <p className="text-sm mb-8 max-w-xs" style={{ color: 'var(--text)' }}>
        {message ?? 'Something went wrong. Please try again.'}
      </p>
      <button
        onClick={onRetry}
        className="px-8 py-3 rounded-full bg-spotify-green text-white font-medium text-base transition-opacity hover:opacity-90 cursor-pointer"
      >
        Try again
      </button>
    </>
  )
}

function MusicBarsIcon() {
  return (
    <div className="flex items-end gap-1 h-12 mb-6">
      {[0, 150, 300, 150, 0].map((delay, i) => (
        <div
          key={i}
          className="w-2 rounded-sm bg-spotify-green"
          style={{
            height: '100%',
            animation: `bounce 1s ease-in-out ${delay}ms infinite alternate`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          from { transform: scaleY(0.3); }
          to   { transform: scaleY(1); }
        }
      `}</style>
    </div>
  )
}

function Header({ onLogout, spotifyId }: { onLogout: () => void; spotifyId?: string }) {
  return (
    <header
      className="flex items-center justify-between px-6 py-4 border-b"
      style={{ borderColor: 'var(--border)' }}
    >
      <span className="font-medium text-sm" style={{ color: 'var(--text-h)' }}>
        Sounds Good
      </span>
      <div className="flex items-center gap-3">
        {spotifyId && (
          <span className="text-sm" style={{ color: 'var(--text)' }}>
            {spotifyId}
          </span>
        )}
        <button
          onClick={onLogout}
          className="text-sm px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          style={{ color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          Log out
        </button>
      </div>
    </header>
  )
}
