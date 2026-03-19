import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function SyncPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleSync = () => {
    // Phase 2: will call POST /library/sync and listen to WebSocket for progress
    navigate('/generate')
  }

  return (
    <div className="flex flex-col flex-1">
      <Header onLogout={logout} spotifyId={user?.spotify_id} />

      <div className="flex flex-col items-center justify-center flex-1 px-6 py-20 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-spotify-green/10 mb-6">
          <svg className="w-8 h-8 text-spotify-green" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />
          </svg>
        </div>

        <h1 className="text-3xl font-semibold tracking-tight mb-3" style={{ color: 'var(--text-h)' }}>
          Sync your library
        </h1>
        <p className="text-base max-w-sm mb-2" style={{ color: 'var(--text)' }}>
          We'll fetch all your Spotify playlists and index your tracks so the AI can search through them.
        </p>
        <p className="text-sm mb-10" style={{ color: 'var(--text)' }}>
          This takes about 10 seconds for up to 10,000 tracks.
        </p>

        <button
          onClick={handleSync}
          className="flex items-center gap-2 px-8 py-3 rounded-full bg-spotify-green text-white font-medium text-base transition-opacity hover:opacity-90 cursor-pointer"
        >
          Sync library
        </button>

        <p className="mt-4 text-xs" style={{ color: 'var(--text)' }}>
          Library sync is coming in Phase 2 — clicking will take you straight to the generator for now.
        </p>
      </div>
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
