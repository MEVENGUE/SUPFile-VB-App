import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import Sidebar from '../components/Sidebar'
import './ChatPage.css'

const ChatPage = () => {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    { role: 'assistant', content: 'Bonjour ! Je suis votre assistant IA. Comment puis-je vous aider avec SUPFile ?' }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading) return

    // Vérifier que la clé API OpenAI est configurée
    if (!import.meta.env.VITE_OPENAI_API_KEY) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Erreur : La clé API OpenAI n\'est pas configurée. Veuillez contacter l\'administrateur.'
      }])
      return
    }

    const userMessage = inputMessage.trim()
    setInputMessage('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await axios.post(
        'https://api.openai.com/v1/chat/completions',
        {
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: 'Tu es un assistant IA pour SUPFile, un système de stockage cloud. Tu aides les utilisateurs avec des questions sur l\'utilisation de l\'application, le partage de fichiers, la gestion des dossiers, etc. Réponds toujours en français de manière amicale et professionnelle.'
            },
            ...messages.map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content: userMessage }
          ],
          max_tokens: 500,
          temperature: 0.7
        },
        {
          headers: {
            'Authorization': `Bearer ${import.meta.env.VITE_OPENAI_API_KEY || ''}`,
            'Content-Type': 'application/json'
          }
        }
      )

      const assistantMessage = response.data.choices[0].message.content
      setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage }])
    } catch (error: any) {
      console.error('Erreur OpenAI:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Désolé, une erreur est survenue. Veuillez réessayer plus tard.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-page">
      <Sidebar />
      <div className="chat-content">
        <div className="chat-container">
          <div className="chat-title-section">
            <img src="/messagerie icon.jpg" alt="Messagerie" className="chat-icon" />
            <h2>Aide & Commentaires</h2>
            <p>Posez vos questions sur SUPFile, notre assistant IA est là pour vous aider !</p>
          </div>

          <div className="chat-messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-avatar">🤖</div>
                <div className="message-content">
                  <div className="message-text loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            <textarea
              className="chat-input"
              placeholder="Tapez votre message..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={1}
            />
            <button
              className="chat-send-btn"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || loading}
            >
              Envoyer
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatPage

