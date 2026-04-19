import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { sendPublicChatMessage } from '../../api/chatbotApi'
import StructuredChatText from '../../components/StructuredChatText'
import {
  Zap,
  Activity,
  BarChart3,
  Send,
  Lock,
  Check,
  Bot,
  User,
  LogIn,
  UserPlus,
  ArrowRight,
  CalendarPlus,
  ShieldAlert,
  Mail,
  ExternalLink,
  Heart,
  Shield,
} from 'lucide-react'

const roleHomePath = {
  patient: '/patient/dashboard',
  doctor: '/doctor/dashboard',
  admin: '/admin/dashboard',
}

const quickPrompts = [
  'I have fever and cough since yesterday.',
  'I feel chest discomfort and shortness of breath.',
  'Can you explain diabetes symptoms?',
]

const featureCards = [
  {
    title: 'Instant Local Triage',
    description: 'Symptom estimation with urgency and department guidance, powered by local health datasets.',
    icon: Zap,
    color: '#ef5b3f',
  },
  {
    title: 'Care Workflow Platform',
    description: 'Appointments, consultations, prescriptions, and follow-up in one coordinated medical flow.',
    icon: Activity,
    color: '#0c8a82',
  },
  {
    title: 'Operational Visibility',
    description: 'Clinical KPIs and monitoring panels for healthcare teams and administrators.',
    icon: BarChart3,
    color: '#2563eb',
  },
]

const initialMessages = [
  {
    id: 'bot-welcome',
    sender: 'bot',
    content:
      'Hello. I am your health triage assistant. You can write in any language, but I will answer in English. Share your symptoms to get a local triage estimate.',
  },
]

function LandingPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const accessToken = useAuthStore((state) => state.accessToken)
  const isAuthenticated = Boolean(accessToken)
  const chatbotSectionRef = useRef(null)

  const [draftMessage, setDraftMessage] = useState('')
  const [messages, setMessages] = useState(initialMessages)
  const [lastResponsePayload, setLastResponsePayload] = useState(null)
  const [bookingPromptState, setBookingPromptState] = useState({ visible: false, accepted: null })

  const publicChatMutation = useMutation({
    mutationFn: (payload) => sendPublicChatMessage(payload),
    onSuccess: (data) => {
      const botContent = data?.bot_message?.content || 'I could not generate a response. Please try again.'
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          content: botContent,
        },
      ])
      setLastResponsePayload(data)

      const hasDiagnosis =
        data?.response_type === 'triage' &&
        Array.isArray(data?.analysis?.probable_diseases) &&
        data.analysis.probable_diseases.length > 0

      setBookingPromptState(hasDiagnosis ? { visible: true, accepted: null } : { visible: false, accepted: null })
    },
    onError: () => {
      toast.error('The chatbot is currently unavailable. Please try again in a moment.')
    },
  })

  const goToDashboard = () => {
    const home = roleHomePath[user?.role] || '/login'
    navigate(home)
  }

  const handleSendMessage = () => {
    const trimmed = draftMessage.trim()
    if (!trimmed || publicChatMutation.isPending) return

    setMessages((prev) => [
      ...prev,
      {
        id: `patient-${Date.now()}`,
        sender: 'patient',
        content: trimmed,
      },
    ])

    setDraftMessage('')
    setBookingPromptState({ visible: false, accepted: null })
    publicChatMutation.mutate({ content: trimmed })
  }

  const handleQuickPrompt = (prompt) => {
    setDraftMessage(prompt)
  }

  const handleTryNow = () => {
    chatbotSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const openBookingFlow = () => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }

    if (user?.role === 'patient') {
      navigate('/patient/chatbot')
      return
    }

    toast.error('Appointment booking is available from a patient account.')
  }

  const analysis = lastResponsePayload?.analysis
  const probableDiseases = analysis?.probable_diseases || []

  return (
    <div className="landing-page">
      <header className="landing-header card landing-header-animated">
        <div className="landing-brand-wrap">
          <div className="landing-logo-container">
            <img src="/visuals/meditriage-mark.svg" alt="MediTriage logo" className="landing-logo-image" />
          </div>
          <div>
            <h1 className="brand-title">MediTriage</h1>
            <p className="brand-subtitle">AI-assisted healthcare triage and coordinated care platform.</p>
          </div>
        </div>

        <div className="landing-actions">
          <Link className="ghost-btn landing-action landing-action-ghost" to="/login">
            <LogIn size={16} />
            <span>Login</span>
          </Link>
          <Link className="landing-action landing-action-primary" to="/register">
            <UserPlus size={16} />
            <span>Sign Up</span>
          </Link>
          {isAuthenticated ? (
            <button className="landing-action landing-action-success" type="button" onClick={goToDashboard}>
              <ArrowRight size={16} />
              <span>Open Dashboard</span>
            </button>
          ) : null}
        </div>
      </header>

      <section className="landing-hero card landing-hero-animated">
        <div className="hero-content">
          <p className="auth-eyebrow">
            Welcome to MediTriage
          </p>
          <h2 className="hero-title">Public health chatbot</h2>
          <p className="muted hero-description">
            Ask health questions in your preferred language. The assistant answers in English and stays focused on
            healthcare triage and medical orientation.
          </p>
        </div>
        <div className="landing-hero-badges">
          <span className="chip chip-animated">
            <Lock size={14} />
            Safe Access
          </span>
          <span className="chip chip-animated">
            <Zap size={14} />
            Local AI Logic
          </span>
          <span className="chip chip-animated">
            <Check size={14} />
            Health Scoped
          </span>
        </div>
      </section>

      <section className="landing-cta-section">
        <div className="cta-container">
          <div className="cta-content">
            <h2 className="cta-title">Ready to improve your healthcare experience?</h2>
            <p className="cta-description">Join thousands of users who trust MediTriage for accurate health guidance and seamless medical coordination.</p>
            <div className="cta-actions">
              <button type="button" className="cta-button cta-button-primary" onClick={handleTryNow}>
                <Zap size={18} />
                Try Now
              </button>
              <Link className="cta-button cta-button-secondary" to="/login">
                Sign In Now
              </Link>
            </div>
          </div>
          <img 
            src="/visuals/medicalpro.jpg" 
            alt="Healthcare professionals"
            className="cta-image"
          />
        </div>
      </section>

      <section className="landing-features">
        {featureCards.map((feature, index) => {
          const Icon = feature.icon
          return (
            <article key={feature.title} className="card landing-feature-card landing-feature-animated" style={{ '--delay': `${index * 100}ms` }}>
              <div className="feature-icon-wrapper" style={{ '--icon-color': feature.color }}>
                <Icon size={32} strokeWidth={1.5} />
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="muted feature-description">{feature.description}</p>
              <div className="feature-cta">
                <ArrowRight size={16} className="arrow-icon" />
              </div>
            </article>
          )
        })}
      </section>

      <section ref={chatbotSectionRef} id="landing-chatbot" className="card landing-chatbot-demo landing-chatbot-animated">
        <div className="inline-header">
          <div>
            <h3 className="demo-title">
              <Bot size={20} />
              Public Health Chatbot
            </h3>
            <p className="muted demo-subtitle">
              Open to all visitors. Appointment booking requires login/signup.
            </p>
          </div>
          <span className={`status-tag ${isAuthenticated ? 'completed' : 'pending'}`}>
            {isAuthenticated ? (
              <>
                <Check size={14} />
                Authenticated
              </>
            ) : (
              <>
                <Lock size={14} />
                Guest Mode
              </>
            )}
          </span>
        </div>

        <div className="landing-chat-prompt-row">
          {quickPrompts.map((prompt) => (
            <button key={prompt} type="button" className="landing-chat-prompt-chip" onClick={() => handleQuickPrompt(prompt)}>
              {prompt}
            </button>
          ))}
        </div>

        <div className="landing-public-chat-list">
          {messages.map((message) => (
            <div key={message.id} className={`landing-public-chat-row ${message.sender === 'patient' ? 'right' : 'left'}`}>
              <div className={`landing-public-chat-bubble ${message.sender === 'patient' ? 'patient' : 'bot'}`}>
                <div className="landing-public-chat-avatar">
                  {message.sender === 'patient' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="landing-public-chat-content">
                  <StructuredChatText text={message.content} />
                </div>
              </div>
            </div>
          ))}

          {publicChatMutation.isPending ? (
            <div className="landing-public-chat-row left">
              <div className="landing-public-chat-bubble bot">
                <div className="landing-public-chat-avatar">
                  <Bot size={16} />
                </div>
                <div className="landing-public-chat-content">
                  <StructuredChatText text="Analyzing your message..." />
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="message-input-row">
          <input
            value={draftMessage}
            onChange={(event) => setDraftMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                handleSendMessage()
              }
            }}
            placeholder="Describe your symptoms or ask a health question"
            className="demo-input"
            disabled={publicChatMutation.isPending}
          />
          <button
            type="button"
            onClick={handleSendMessage}
            className="send-btn"
            disabled={publicChatMutation.isPending || !draftMessage.trim()}
            title="Send"
          >
            <Send size={18} />
          </button>
        </div>

        {analysis ? (
          <div className="landing-chat-analysis card">
            <div className="landing-chat-analysis-head">
              <h4>Latest triage summary</h4>
              <span className={`urgency-tag ${analysis.urgency_level || 'low'}`}>{analysis.urgency_level || 'low'}</span>
            </div>

            <p className="muted">Department: {analysis.department || 'General Medicine'}</p>
            <p className="muted">Detected symptoms: {(analysis.detected_symptoms || []).join(', ') || 'none'}</p>

            {probableDiseases.length ? (
              <div className="landing-chat-analysis-grid">
                {probableDiseases.slice(0, 3).map((item) => (
                  <article key={`${item.disease}-${item.score}`} className="landing-chat-analysis-item">
                    <strong>{item.disease}</strong>
                    <span>{item.score}% confidence</span>
                  </article>
                ))}
              </div>
            ) : null}

            <p className="muted">{analysis.summary}</p>
          </div>
        ) : null}

        {bookingPromptState.visible ? (
          <div className="landing-booking-question card">
            <p className="landing-booking-question-title">Would you like to book an appointment from this diagnosis?</p>
            <div className="landing-booking-question-actions">
              <button
                type="button"
                className="landing-action landing-action-primary"
                onClick={() => setBookingPromptState({ visible: true, accepted: true })}
              >
                <CalendarPlus size={15} />
                <span>Yes, book an appointment</span>
              </button>
              <button
                type="button"
                className="landing-action landing-action-ghost"
                onClick={() => setBookingPromptState({ visible: true, accepted: false })}
              >
                <span>No, continue chatting</span>
              </button>
            </div>
          </div>
        ) : null}

        {bookingPromptState.visible && bookingPromptState.accepted === true ? (
          <div className="landing-booking-gate">
            <div className="landing-booking-gate-copy">
              <ShieldAlert size={18} />
              <p>Great. To reserve an appointment from this triage result, please log in or sign up.</p>
            </div>

            <div className="landing-booking-gate-actions">
              {!isAuthenticated ? (
                <>
                  <Link to="/login" className="landing-action landing-action-ghost">
                    <LogIn size={15} />
                    <span>Login</span>
                  </Link>
                  <Link to="/register" className="landing-action landing-action-primary">
                    <UserPlus size={15} />
                    <span>Sign Up</span>
                  </Link>
                </>
              ) : (
                <button type="button" className="landing-action landing-action-success" onClick={openBookingFlow}>
                  <CalendarPlus size={15} />
                  <span>Continue to Booking</span>
                </button>
              )}
            </div>
          </div>
        ) : null}

        {bookingPromptState.visible && bookingPromptState.accepted === false ? (
          <p className="landing-booking-continue-note">Understood. You can continue asking health questions in the chat.</p>
        ) : null}
      </section>

      <footer className="landing-footer">
        <div className="footer-grid">
          <div className="footer-column">
            <div className="footer-brand">
              <img src="/visuals/meditriage-mark.svg" alt="MediTriage" className="footer-logo" />
              <h3>MediTriage</h3>
            </div>
            <p className="footer-description">AI-powered health triage platform bridging patients and healthcare providers with intelligence and care.</p>
            <div className="footer-social">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="social-link" title="GitHub">
                <ExternalLink size={20} />
              </a>
              <a href="mailto:contact@meditriage.com" className="social-link" title="Email">
                <Mail size={20} />
              </a>
            </div>
          </div>

          <div className="footer-column">
            <h4 className="footer-column-title">Platform</h4>
            <ul className="footer-links">
              <li><Link to="/login">Login</Link></li>
              <li><Link to="/register">Sign Up</Link></li>
              <li><a href="#features">Features</a></li>
              <li><a href="#pricing">Pricing</a></li>
            </ul>
          </div>

          <div className="footer-column">
            <h4 className="footer-column-title">Resources</h4>
            <ul className="footer-links">
              <li><a href="#help">Help Center</a></li>
              <li><a href="#docs">Documentation</a></li>
              <li><a href="#blog">Blog</a></li>
              <li><a href="#faq">FAQ</a></li>
            </ul>
          </div>

          <div className="footer-column">
            <h4 className="footer-column-title">Legal</h4>
            <ul className="footer-links">
              <li><a href="#privacy">Privacy Policy</a></li>
              <li><a href="#terms">Terms of Service</a></li>
              <li><a href="#cookies">Cookie Policy</a></li>
              <li><a href="#compliance">Compliance</a></li>
            </ul>
          </div>
        </div>

        <div className="footer-divider" />

        <div className="footer-bottom">
          <div className="footer-credits">
            <p>© 2026 MediTriage. All rights reserved.</p>
            <div className="footer-trust">
              <Shield size={16} />
              <span>HIPAA Compliant</span>
            </div>
          </div>
          <div className="footer-made">
            <span>Made with</span>
            <Heart size={16} />
            <span>for better healthcare</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage