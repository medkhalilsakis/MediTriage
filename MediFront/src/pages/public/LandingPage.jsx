import { useState } from 'react'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
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
  Stethoscope,
} from 'lucide-react'

const roleHomePath = {
  patient: '/patient/dashboard',
  doctor: '/doctor/dashboard',
  admin: '/admin/dashboard',
}

const featureCards = [
  {
    title: 'Triage IA Instantane',
    description: 'Analyse preliminaire des symptomes avec niveau d urgence et orientation rapide.',
    icon: Zap,
    color: '#ef5b3f',
  },
  {
    title: 'Parcours Clinique Complet',
    description: 'Rendez-vous, consultation, ordonnances PDF et suivi patient dans un flux unifie.',
    icon: Activity,
    color: '#0c8a82',
  },
  {
    title: 'Pilotage & Reporting',
    description: 'KPIs en temps reel pour la direction medicale et suivi des priorites de soin.',
    icon: BarChart3,
    color: '#2563eb',
  },
]

function LandingPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const accessToken = useAuthStore((state) => state.accessToken)
  const [draftMessage, setDraftMessage] = useState('J ai mal a la gorge depuis 3 jours avec fievre legere.')
  const [demoMessages, setDemoMessages] = useState([
    {
      id: 'intro-bot',
      sender: 'bot',
      content: 'Bonjour. Je peux faire une pre-analyse des symptomes. Connectez-vous pour lancer un vrai triage.',
    },
  ])

  const isAuthenticated = Boolean(accessToken)

  const handleTryChatbot = () => {
    if (!isAuthenticated) {
      toast.error('Veuillez vous connecter pour utiliser le chatbot clinique.')
      return
    }

    const trimmed = draftMessage.trim()
    if (!trimmed) return

    const patientMessage = {
      id: `patient-${Date.now()}`,
      sender: 'patient',
      content: trimmed,
    }

    const botMessage = {
      id: `bot-${Date.now()}`,
      sender: 'bot',
      content: 'Message recu. Rendez-vous dans votre espace patient pour une analyse IA complete.',
    }

    setDemoMessages((prev) => [...prev, patientMessage, botMessage])
    setDraftMessage('')
  }

  const goToDashboard = () => {
    const home = roleHomePath[user?.role] || '/login'
    navigate(home)
  }

  return (
    <div className="landing-page">
      <header className="landing-header card landing-header-animated">
        <div className="landing-brand-wrap">
          <div className="landing-logo-container">
            <Stethoscope size={28} stroke={3} strokeLinecap="round" strokeLinejoin="round" />
          </div>
          <div>
            <h1 className="brand-title">MediSmart</h1>
            <p className="brand-subtitle">Plateforme intelligente de triage medical et coordination des soins.</p>
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
              <span>Ouvrir Mon Espace</span>
            </button>
          ) : null}
        </div>
      </header>

      <section className="landing-hero card landing-hero-animated">
        <div className="hero-content">
          <p className="auth-eyebrow">
            <Stethoscope size={14} style={{ display: 'inline-block', marginRight: '0.4rem', verticalAlign: 'middle' }} />
            Bienvenue sur MediSmart
          </p>
          <h2 className="hero-title">Une entree unique pour patients, medecins et administrateurs</h2>
          <p className="muted hero-description">
            Decouvrez les fonctions cles de la plateforme: triage IA, suivi clinique, prescriptions et supervision
            operationnelle.
          </p>
        </div>
        <div className="landing-hero-badges">
          <span className="chip chip-animated">
            <Lock size={14} />
            Secure Access
          </span>
          <span className="chip chip-animated">
            <Zap size={14} />
            AI Assisted
          </span>
          <span className="chip chip-animated">
            <Check size={14} />
            Role Based
          </span>
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

      <section className="card landing-chatbot-demo landing-chatbot-animated">
        <div className="inline-header">
          <div>
            <h3 className="demo-title">
              <Bot size={20} />
              Chatbot Demo Interactif
            </h3>
            <p className="muted demo-subtitle">
              Exemple de diagnostic IA. Utilisation clinique reservee aux utilisateurs connectes.
            </p>
          </div>
          <span className={`status-tag ${isAuthenticated ? 'completed' : 'pending'}`}>
            {isAuthenticated ? (
              <>
                <Check size={14} />
                Connected
              </>
            ) : (
              <>
                <Lock size={14} />
                Login Required
              </>
            )}
          </span>
        </div>

        <div className="landing-chat-list">
          {demoMessages.map((message) => (
            <div key={message.id} className={message.sender === 'patient' ? 'message-row right' : 'message-row left'}>
              <div className={message.sender === 'patient' ? 'message-bubble patient' : 'message-bubble bot'}>
                <div className="message-avatar">
                  {message.sender === 'patient' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="message-content">
                  <p>{message.content}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="message-input-row">
          <input
            value={draftMessage}
            onChange={(event) => setDraftMessage(event.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleTryChatbot()}
            placeholder="Ecrivez un symptome pour tester la demo"
            className="demo-input"
            disabled={!isAuthenticated}
          />
          <button type="button" onClick={handleTryChatbot} className="send-btn" disabled={!isAuthenticated} title={isAuthenticated ? 'Envoyer' : 'Veuillez vous connecter'}>
            <Send size={18} />
          </button>
        </div>

        {!isAuthenticated && (
          <div className="landing-lock-note">
            <Lock size={14} style={{ display: 'inline-block', marginRight: '0.4rem' }} />
            <Link to="/login">Connectez-vous</Link> pour utiliser le chatbot clinique complet.
          </div>
        )}
      </section>
    </div>
  )
}

export default LandingPage
