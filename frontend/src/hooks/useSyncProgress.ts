import { useState, useEffect, useRef, useCallback } from 'react'
import { startLibrarySync } from '../services/api'

export type SyncStatus = 'idle' | 'starting' | 'syncing' | 'complete' | 'error'

export interface SyncProgressState {
  status: SyncStatus
  playlistsDone: number
  totalPlaylists: number
  tracksDone: number
  error: string | null
}

interface SyncProgressMessage {
  status: string
  playlists_done?: number
  total_playlists?: number
  tracks_done?: number
  error?: string | null
}

const INITIAL_STATE: SyncProgressState = {
  status: 'idle',
  playlistsDone: 0,
  totalPlaylists: 0,
  tracksDone: 0,
  error: null,
}

export function useSyncProgress() {
  const [state, setState] = useState<SyncProgressState>(INITIAL_STATE)
  const wsRef = useRef<WebSocket | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      wsRef.current?.close()
    }
  }, [])

  const startSync = useCallback(async () => {
    if (!isMountedRef.current) return
    setState({ ...INITIAL_STATE, status: 'starting' })

    try {
      await startLibrarySync()
    } catch {
      if (isMountedRef.current) {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: 'Failed to start library sync. Please try again.',
        }))
      }
      return
    }

    const token = localStorage.getItem('auth_token')
    if (!token) {
      if (isMountedRef.current) {
        setState((prev) => ({ ...prev, status: 'error', error: 'Not authenticated.' }))
      }
      return
    }

    const wsUrl = `${import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'}/library/sync/ws?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event: MessageEvent) => {
      if (!isMountedRef.current) return
      try {
        const msg: SyncProgressMessage = JSON.parse(event.data as string)
        setState({
          status: (msg.status as SyncStatus) ?? 'syncing',
          playlistsDone: msg.playlists_done ?? 0,
          totalPlaylists: msg.total_playlists ?? 0,
          tracksDone: msg.tracks_done ?? 0,
          error: msg.error ?? null,
        })
      } catch {
        // ignore malformed messages
      }
    }

    ws.onerror = () => {
      if (!isMountedRef.current) return
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: 'Connection to sync service lost.',
      }))
    }

    ws.onclose = () => {
      wsRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setState(INITIAL_STATE)
  }, [])

  return { ...state, startSync, reset }
}
