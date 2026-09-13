import { useState, useEffect, useRef } from 'react'

function App() {
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [simpleMode, setSimpleMode] = useState(true)
  const [backendStatus, setBackendStatus] = useState('checking...')
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const streamBuffer = useRef('')

  // Check backend connection
  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data.status || 'connected')
        loadConversations()
      })
      .catch(err => {
        setBackendStatus('disconnected')
        setError('Cannot connect to backend. Please ensure the server is running.')
      })
  }, [])

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load conversations list
  const loadConversations = async () => {
    try {
      const response = await fetch('/api/chat/conversations')
      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || [])
        if (data.conversations && data.conversations.length > 0 && !currentConversationId) {
          setCurrentConversationId(data.conversations[0].id)
          loadMessages(data.conversations[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
  }

  // Load messages for a conversation
  const loadMessages = async (conversationId) => {
    try {
      const response = await fetch(`/api/chat/conversation/${conversationId}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (err) {
      console.error('Failed to load messages:', err)
    }
  }

  // Create new conversation
  const createNewConversation = async () => {
    try {
      const response = await fetch('/api/chat/conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' })
      })
      if (response.ok) {
        const data = await response.json()
        setCurrentConversationId(data.conversation.id)
        setMessages([])
        loadConversations()
      }
    } catch (err) {
      setError('Failed to create new conversation')
    }
  }

  // Send message with streaming
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)
    setIsStreaming(true)
    streamBuffer.current = ''
    setError(null)

    // Add placeholder for AI response
    const aiMessageId = Date.now()
    setMessages(prev => [...prev, {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      reasoning: '',
      tools_used: [],
      timestamp: new Date().toISOString(),
      isStreaming: true
    }])

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: currentConversationId,
          simple_mode: simpleMode
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response from AI')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'content') {
              streamBuffer.current += data.content
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, content: streamBuffer.current }
                  : msg
              ))
            } else if (data.type === 'reasoning') {
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, reasoning: data.reasoning }
                  : msg
              ))
            } else if (data.type === 'tools') {
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, tools_used: data.tools }
                  : msg
              ))
            } else if (data.type === 'done') {
              setIsStreaming(false)
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, isStreaming: false }
                  : msg
              ))
              loadConversations()
            }
          }
        }
      }
    } catch (err) {
      setError(err.message)
      setIsStreaming(false)
      setMessages(prev => prev.filter(msg => msg.id !== aiMessageId))
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white">
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold">Financial AI Platform</h1>
              <p className="text-xs text-gray-400">Powered by Qwen 2.5 14B</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">Backend:</span>
              <span className={`px-2 py-1 rounded-full text-xs ${
                backendStatus === 'connected' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {backendStatus}
              </span>
            </div>
            
            <button
              onClick={createNewConversation}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
            >
              New Chat
            </button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-4 flex gap-4" style={{ height: 'calc(100vh - 80px)' }}>
        <aside className="w-64 bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-700 p-4 overflow-y-auto">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Conversations</h2>
          <div className="space-y-2">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => {
                  setCurrentConversationId(conv.id)
                  loadMessages(conv.id)
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  currentConversationId === conv.id
                    ? 'bg-blue-600/20 border border-blue-500/50'
                    : 'hover:bg-gray-700/50 border border-transparent'
                }`}
              >
                <div className="font-medium truncate">{conv.title}</div>
                <div className="text-xs text-gray-500">
                  {new Date(conv.created_at).toLocaleDateString()}
                </div>
              </button>
            ))}
            {conversations.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-4">No conversations yet</p>
            )}
          </div>
        </aside>

        <main className="flex-1 flex flex-col bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-700">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <p className="text-lg">Start a conversation about stocks, crypto, or IPOs</p>
                  <p className="text-sm mt-2">Try: "How is TCS performing today?" or "What's the latest on Bitcoin?"</p>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700/80 border border-gray-600'
                    }`}
                  >
                    {msg.role === 'assistant' && msg.isStreaming && (
                      <div className="flex items-center gap-2 mb-2 text-xs text-blue-400">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                        <span>AI is thinking...</span>
                      </div>
                    )}
                    
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    
                    {!simpleMode && msg.role === 'assistant' && (
                      <div className="mt-3 pt-3 border-t border-gray-600 space-y-2">
                        {msg.reasoning && (
                          <div className="bg-gray-800/50 rounded-lg p-3 text-xs">
                            <div className="font-semibold text-purple-400 mb-1">🧠 Reasoning Process:</div>
                            <div className="text-gray-300 whitespace-pre-wrap">{msg.reasoning}</div>
                          </div>
                        )}
                        
                        {msg.tools_used && msg.tools_used.length > 0 && (
                          <div className="bg-gray-800/50 rounded-lg p-3 text-xs">
                            <div className="font-semibold text-green-400 mb-1">🔧 Data Sources:</div>
                            <div className="space-y-1">
                              {msg.tools_used.map((tool, i) => (
                                <div key={i} className="text-gray-300">
                                  <span className="font-mono bg-gray-700 px-2 py-0.5 rounded">{tool.tool}</span>
                                  {tool.result && (
                                    <div className="mt-1 text-gray-400 truncate">{JSON.stringify(tool.result)}</div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className={`text-xs mt-2 ${
                      msg.role === 'user' ? 'text-blue-200' : 'text-gray-400'
                    }`}>
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="mx-4 mb-2 bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-sm text-red-300">
              ⚠️ {error}
            </div>
          )}

          <div className="border-t border-gray-700 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Mode:</span>
                <button
                  onClick={() => setSimpleMode(!simpleMode)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    simpleMode ? 'bg-gray-600' : 'bg-blue-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      simpleMode ? 'translate-x-1' : 'translate-x-6'
                    }`}
                  />
                </button>
                <span className="text-sm font-medium">{simpleMode ? 'Simple' : 'Advanced'}</span>
              </div>
              
              {isStreaming && (
                <div className="flex items-center gap-2 text-xs text-blue-400">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                  <span>Streaming response...</span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about stocks, crypto, mutual funds, or IPOs..."
                disabled={isLoading || backendStatus !== 'connected'}
                className="flex-1 bg-gray-700/50 border border-gray-600 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none"
                rows={2}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !inputMessage.trim() || backendStatus !== 'connected'}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    <span>Send</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
