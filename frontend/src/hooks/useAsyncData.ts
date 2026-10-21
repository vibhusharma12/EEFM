import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../services/api'

export type AsyncState<T> =
  | { status: 'idle'; data: null; error: null }
  | { status: 'loading'; data: null; error: null }
  | { status: 'success'; data: T; error: null }
  | { status: 'error'; data: null; error: ApiError }

/**
 * Runs `fetcher` whenever `key` changes. Pass `null` as the key to stay idle.
 * In-flight requests are aborted when the key changes or the component unmounts.
 */
export function useAsyncData<T>(
  key: string | null,
  fetcher: (signal: AbortSignal) => Promise<T>,
) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle', data: null, error: null })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    if (key === null) {
      setState({ status: 'idle', data: null, error: null })
      return
    }
    const controller = new AbortController()
    setState({ status: 'loading', data: null, error: null })
    fetcher(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: 'success', data, error: null })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        const error = err instanceof ApiError ? err : new ApiError('Something went wrong.', 'unknown')
        setState({ status: 'error', data: null, error })
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}
