import { ReactNode } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

interface WebSocketProviderProps {
  children: ReactNode
}

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  // Initialize WebSocket connection
  useWebSocket()
  
  return <>{children}</>
}

