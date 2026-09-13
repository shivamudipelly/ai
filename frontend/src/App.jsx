import { useState, useEffect, useRef } from 'react'

// Lightweight Formatted Text Renderer for Markdown-like Financial Outputs
function FormattedContent({ content }) {
  if (!content) return null

  // Remove raw FINAL_ANSWER: prefix if present
  let cleanText = content
  if (cleanText.includes('FINAL_ANSWER:')) {
    cleanText = cleanText.split('FINAL_ANSWER:').pop().trim()
  }

  const lines = cleanText.split('\n')
  const elements = []
  let tableRows = []
  let inTable = false

  lines.forEach((line, index) => {
    const trimmed = line.trim()

    // Table detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      inTable = true
      // Skip separator rows like |---|---|
      if (!trimmed.includes('---')) {
        const cells = trimmed.split('|').slice(1, -1).map(c => c.trim())
        tableRows.push(cells)
      }
      return
    } else if (inTable) {
      // Flush table
      inTable = false
      if (tableRows.length > 0) {
        elements.push(
          <div key={`table-${index}`} className="my-3 overflow-x-auto rounded-lg border border-slate-700/60 bg-slate-900/40">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-800/80 text-blue-300 font-semibold border-b border-slate-700">
                <tr>
                  {tableRows[0].map((header, hIdx) => (
                    <th key={hIdx} className="px-3 py-2 border-r border-slate-700/50 last:border-0">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {tableRows.slice(1).map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-800/40">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3 py-2 border-r border-slate-800/60 last:border-0 text-slate-300">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
        tableRows = []
      }
    }

    if (!trimmed) {
      elements.push(<div key={index} className="h-2" />)
      return
    }

    // Headers
    if (trimmed.startsWith('###')) {
      elements.push(<h3 key={index} className="text-base font-bold text-blue-400 mt-3 mb-1">{trimmed.replace(/^###\s*/, '')}</h3>)
      return
    } else if (trimmed.startsWith('##')) {
      elements.push(<h2 key={index} className="text-lg font-bold text-blue-300 mt-4 mb-2">{trimmed.replace(/^##\s*/, '')}</h2>)
      return
    }

    // Bullet list items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const listText = trimmed.substring(2)
      elements.push(
        <div key={index} className="flex items-start gap-2 my-1 pl-2">
          <span className="text-blue-400 text-xs mt-1">•</span>
          <span className="text-sm text-slate-200">{formatInline(listText)}</span>
        </div>
      )
      return
    }

    // Blockquote or disclaimer
    if (trimmed.startsWith('>')) {
      elements.push(
        <div key={index} className="my-2 p-2.5 rounded-r-lg bg-amber-500/10 border-l-4 border-amber-500 text-xs italic text-amber-200">
          {trimmed.replace(/^>\s*/, '')}
        </div>
      )
      return
    }

    // Default paragraph
    elements.push(
      <p key={index} className="text-sm text-slate-200 leading-relaxed my-1">
        {formatInline(line)}
      </p>
    )
  })

  // Flush remaining table if at end
  if (inTable && tableRows.length > 0) {
    elements.push(
      <div key="table-end" className="my-3 overflow-x-auto rounded-lg border border-slate-700/60 bg-slate-900/40">
        <table className="w-full text-xs text-left border-collapse">
          <thead className="bg-slate-800/80 text-blue-300 font-semibold border-b border-slate-700">
            <tr>
              {tableRows[0].map((header, hIdx) => (
                <th key={hIdx} className="px-3 py-2 border-r border-slate-700/50 last:border-0">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {tableRows.slice(1).map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-800/40">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 border-r border-slate-800/60 last:border-0 text-slate-300">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return <div>{elements}</div>
}

// Inline formatting helper for **bold** and `code`
function formatInline(text) {
  if (!text) return ''
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="bg-slate-800 text-blue-300 font-mono text-xs px-1.5 py-0.5 rounded border border-slate-700">{part.slice(1, -1)}</code>
    }
    return part
  })
}

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
  const [copiedId, setCopiedId] = useState(null)
  const messagesEndRef = useRef(null)
  const streamBuffer = useRef('')

  // Check backend health on mount
  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data.status || 'connected')
        loadConversations()
      })
      .catch(() => {
        setBackendStatus('disconnected')
        setError('Cannot connect to backend. Please ensure the backend container is running.')
      })
  }, [])

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Fetch all user conversations
  const loadConversations = async () => {
    try {
      let userId = localStorage.getItem('userId')
      if (!userId) {
        const userResponse = await fetch('/api/chat/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            email: `user-${Date.now()}@example.com`,
            name: 'Financial User'
          })
        })
        if (userResponse.ok) {
          const userData = await userResponse.json()
          userId = userData.id
          localStorage.setItem('userId', userId)
        }
      }
      
      if (userId) {
        const response = await fetch(`/api/chat/users/${userId}/conversations`)
        if (response.ok) {
          const data = await response.json()
          setConversations(data || [])
          if (data && data.length > 0 && !currentConversationId) {
            setCurrentConversationId(data[0].id)
            loadMessages(data[0].id)
          }
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
  }

  // Load messages for specific conversation
  const loadMessages = async (conversationId) => {
    try {
      const response = await fetch(`/api/chat/conversations/${conversationId}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (err) {
      console.error('Failed to load messages:', err)
    }
  }

  // Create new conversation tab
  const createNewConversation = async () => {
    try {
      const userId = localStorage.getItem('userId')
      if (!userId) return
      
      const response = await fetch('/api/chat/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: userId,
          title: 'New Financial Query' 
        })
      })
      if (response.ok) {
        const data = await response.json()
        setCurrentConversationId(data.id)
        setMessages([])
        loadConversations()
      }
    } catch (err) {
      setError('Failed to create new conversation')
    }
  }

  // Delete conversation
  const deleteConversation = async (convId, e) => {
    e.stopPropagation()
    try {
      const response = await fetch(`/api/chat/conversations/${convId}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        if (currentConversationId === convId) {
          setCurrentConversationId(null)
          setMessages([])
        }
        loadConversations()
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err)
    }
  }

  // Send query & parse SSE stream
  const sendMessage = async (presetText) => {
    const textToSend = presetText || inputMessage
    if (!textToSend.trim() || isLoading) return
    
    let convId = currentConversationId
    if (!convId) {
      const userId = localStorage.getItem('userId') || 'default_user'
      try {
        const response = await fetch('/api/chat/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            user_id: userId,
            title: textToSend.substring(0, 40) + (textToSend.length > 40 ? '...' : '')
          })
        })
        if (response.ok) {
          const data = await response.json()
          convId = data.id
          setCurrentConversationId(convId)
        } else {
          setError('Failed to initialize conversation')
          return
        }
      } catch (err) {
        setError('Failed to initialize conversation')
        return
      }
    }

    const userMessage = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    if (!presetText) setInputMessage('')
    setIsLoading(true)
    setIsStreaming(true)
    streamBuffer.current = ''
    setError(null)

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
          message: textToSend,
          conversation_id: convId,
          simple_mode: simpleMode
        })
      })

      if (!response.ok) {
        throw new Error('Backend failed to respond.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              const tokenText = data.content !== undefined ? data.content : (data.token || '')
              if (tokenText) {
                streamBuffer.current += tokenText
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, content: streamBuffer.current }
                    : msg
                ))
              }
              
              if (data.type === 'reasoning' || data.reasoning) {
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, reasoning: data.reasoning || data.thought_process }
                    : msg
                ))
              }
              
              if (data.type === 'tools' || data.tools_used) {
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, tools_used: data.tools || data.tools_used }
                    : msg
                ))
              }
              
              if (data.done || data.type === 'done') {
                setIsStreaming(false)
                const finalContent = data.full_response || streamBuffer.current
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, content: finalContent, isStreaming: false }
                    : msg
                ))
                loadConversations()
              }
            } catch (e) {
              console.warn('Parsing SSE event error:', e)
            }
          }
        }
      }
    } catch (err) {
      setError(err.message || 'Error receiving AI response')
      setIsStreaming(false)
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId ? { ...msg, content: 'Error retrieving live response.', isStreaming: false } : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const presetQueries = [
    { label: '📈 TCS Stock Price', query: 'What is the current live stock price of TCS.NS?' },
    { label: '🪙 Bitcoin Price', query: 'What is the current Bitcoin price in USD and INR?' },
    { label: '📊 Mutual Fund NAV', query: 'Fetch the NAV for Axis Tax Saver fund code 120503' },
    { label: '🚀 Upcoming IPOs', query: 'What are the upcoming IPOs and latest GMP news?' }
  ]

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-20">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Financial AI Platform
              </h1>
              <p className="text-xs text-slate-400">Powered by Qwen 2.5 & Real-time Market Data</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Status:</span>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium ${
                backendStatus === 'connected' || backendStatus === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  backendStatus === 'connected' || backendStatus === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`} />
                {backendStatus}
              </span>
            </div>
            
            <button
              onClick={createNewConversation}
              className="bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-blue-600/20 transition-all flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Chat
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="container mx-auto px-4 py-4 flex flex-1 gap-4 overflow-hidden" style={{ height: 'calc(100vh - 70px)' }}>
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800/80 p-3 flex flex-col">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 px-2">Conversations</h2>
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => {
                  setCurrentConversationId(conv.id)
                  loadMessages(conv.id)
                }}
                className={`group relative w-full text-left px-3 py-2.5 rounded-xl text-xs transition-all cursor-pointer flex items-center justify-between ${
                  currentConversationId === conv.id
                    ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40 shadow-sm'
                    : 'hover:bg-slate-800/60 text-slate-300 border border-transparent'
                }`}
              >
                <div className="truncate pr-4">
                  <div className="font-medium truncate">{conv.title}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {new Date(conv.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={(e) => deleteConversation(conv.id, e)}
                  title="Delete Conversation"
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 p-1 transition-opacity"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <div className="text-slate-500 text-xs text-center py-6">No previous chats found.</div>
            )}
          </div>
        </aside>

        {/* Main Chat Panel */}
        <main className="flex-1 flex flex-col bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800/80 overflow-hidden">
          {/* Chat Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-lg mx-auto">
                <div className="w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center mb-4 text-blue-400">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-slate-100">Welcome to Financial AI Analyst</h3>
                <p className="text-xs text-slate-400 mt-1 mb-6">
                  Get real-time insights on Indian & Global Stocks, Cryptocurrency, Mutual Funds NAV, and IPO GMP.
                </p>

                {/* Preset Prompt Pills */}
                <div className="grid grid-cols-2 gap-2.5 w-full">
                  {presetQueries.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendMessage(item.query)}
                      className="p-3 text-left bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-blue-500/50 rounded-xl transition-all group"
                    >
                      <div className="text-xs font-semibold text-slate-200 group-hover:text-blue-300">{item.label}</div>
                      <div className="text-[11px] text-slate-400 truncate mt-1">{item.query}</div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`relative group max-w-[85%] rounded-2xl px-4 py-3 shadow-md ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-slate-800/90 border border-slate-700/80 rounded-bl-none text-slate-100'
                    }`}
                  >
                    {/* Copy Button for Assistant */}
                    {msg.role === 'assistant' && msg.content && (
                      <button
                        onClick={() => handleCopy(msg.id || idx, msg.content)}
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-200 p-1 transition-opacity text-xs bg-slate-700/60 rounded"
                        title="Copy Response"
                      >
                        {copiedId === (msg.id || idx) ? '✓ Copied' : '📋'}
                      </button>
                    )}

                    {/* Thinking status */}
                    {msg.role === 'assistant' && msg.isStreaming && !msg.content && (
                      <div className="flex items-center gap-2 mb-2 text-xs text-blue-400 font-medium">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-ping" />
                        <span>Gathering financial data & reasoning...</span>
                      </div>
                    )}
                    
                    {/* Message content */}
                    {msg.role === 'user' ? (
                      <div className="text-sm font-medium leading-relaxed">{msg.content}</div>
                    ) : (
                      <FormattedContent content={msg.content} />
                    )}

                    {/* Advanced Mode Details */}
                    {!simpleMode && msg.role === 'assistant' && (
                      <div className="mt-3 pt-3 border-t border-slate-700/80 space-y-2">
                        {msg.reasoning && (
                          <div className="bg-slate-900/60 rounded-xl p-2.5 text-xs border border-purple-500/20">
                            <div className="font-bold text-purple-400 mb-1 flex items-center gap-1.5">
                              <span>🧠</span> Reasoning Chain
                            </div>
                            <div className="text-slate-300 text-xs leading-relaxed">{msg.reasoning}</div>
                          </div>
                        )}
                        
                        {msg.tools_used && msg.tools_used.length > 0 && (
                          <div className="bg-slate-900/60 rounded-xl p-2.5 text-xs border border-emerald-500/20">
                            <div className="font-bold text-emerald-400 mb-1 flex items-center gap-1.5">
                              <span>🔧</span> Real-time Tools Executed
                            </div>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {msg.tools_used.map((tool, i) => (
                                <span key={i} className="font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] px-2 py-0.5 rounded-md">
                                  {typeof tool === 'string' ? tool : tool.tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <div className={`text-[10px] mt-1.5 text-right ${
                      msg.role === 'user' ? 'text-blue-200' : 'text-slate-500'
                    }`}>
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Error notification banner */}
          {error && (
            <div className="mx-4 mb-2 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-300 flex items-center justify-between">
              <span>⚠️ {error}</span>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 font-bold ml-2">✕</button>
            </div>
          )}

          {/* Footer Input Bar */}
          <div className="border-t border-slate-800 p-3 bg-slate-900/90">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Analysis Mode:</span>
                <button
                  onClick={() => setSimpleMode(!simpleMode)}
                  className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors ${
                    simpleMode ? 'bg-slate-700' : 'bg-blue-600'
                  }`}
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      simpleMode ? 'translate-x-1' : 'translate-x-5.5'
                    }`}
                  />
                </button>
                <span className="text-xs font-semibold text-slate-300">{simpleMode ? 'Simple Answers' : 'Advanced ReAct'}</span>
              </div>
              
              {isStreaming && (
                <div className="flex items-center gap-2 text-xs text-blue-400">
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-ping" />
                  <span>Streaming token response...</span>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about TCS, Reliance, Bitcoin, Mutual Funds NAV, or IPO GMP..."
                disabled={isLoading}
                className="flex-1 bg-slate-800/70 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50 resize-none"
                rows={2}
              />
              <button
                onClick={() => sendMessage()}
                disabled={isLoading || !inputMessage.trim()}
                className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 disabled:cursor-not-allowed px-5 py-2.5 rounded-xl text-xs font-semibold text-white transition-all shadow-md shadow-blue-600/20 flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <span>Send</span>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
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
