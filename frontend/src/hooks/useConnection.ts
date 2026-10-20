import { useEffect, useState } from 'react'
import { connectionManager } from '@/services/connectionManager'
import type { ConnectionInfo } from '@/types/connection'

export function useConnection(): ConnectionInfo & {
  retryNow: () => Promise<void>
} {
  const [info, setInfo] = useState<ConnectionInfo>(() => connectionManager.getInfo())

  useEffect(() => {
    // Initialize connection monitoring on mount
    connectionManager.init()

    const unsubscribe = connectionManager.subscribe((newInfo) => {
      setInfo(newInfo)
    })

    return () => {
      unsubscribe()
    }
  }, [])

  return {
    ...info,
    retryNow: () => connectionManager.retryNow(),
  }
}
