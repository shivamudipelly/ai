import { useState, useEffect } from 'react'

function App() {
  const [message, setMessage] = useState('')
  const [backendStatus, setBackendStatus] = useState('checking...')

  useEffect(() => {
    // Check backend connection on mount
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data.status || 'connected')
      })
      .catch(err => {
        setBackendStatus('disconnected')
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center mb-8">
          Financial AI Platform
        </h1>
        
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">System Status</h2>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">Backend:</span>
            <span className={`px-3 py-1 rounded-full text-sm ${
              backendStatus === 'connected' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {backendStatus}
            </span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Chat Interface</h2>
          <p className="text-gray-400 mb-4">
            Phase 1: Infrastructure setup complete. Chat functionality coming in Phase 5.
          </p>
          <div className="flex gap-4">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 bg-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled
            />
            <button
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold disabled:opacity-50"
              disabled
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
