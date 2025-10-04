'use client'

import { useState } from 'react'
import { useSupabase } from '../providers'
import { X, Shield, AlertCircle } from 'lucide-react'

interface ConsentModalProps {
  onAccept: () => void
  onClose: () => void
}

export default function ConsentModal({ onAccept, onClose }: ConsentModalProps) {
  const { user } = useSupabase()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleAccept = async () => {
    if (!user) return

    setIsSubmitting(true)
    setError('')

    try {
      const response = await fetch('/api/consent/accept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY || 'dev-key'}`
        },
        body: JSON.stringify({
          userId: user.id,
          timestamp: new Date().toISOString(),
          ipAddress: 'client-side' // Will be replaced server-side
        })
      })

      if (response.ok) {
        console.log('✅ Consent saved successfully')
        onAccept()
      } else {
        // Log error but still allow user to continue
        const data = await response.json().catch(() => ({ error: 'Unknown error' }))
        console.warn('⚠️ Failed to save consent, but allowing user to continue:', data.error)
        setError('Could not save consent record. Your session will continue, but you may be asked again.')
        
        // Allow user to continue after 3 seconds even if save fails
        setTimeout(() => {
          console.log('⚠️ Allowing user to continue despite consent save failure')
          onAccept()
        }, 3000)
      }
    } catch (err) {
      // Log error but still allow user to continue
      console.error('❌ Network error saving consent, but allowing user to continue:', err)
      setError('Network error. You can still use Sophia, but consent was not recorded.')
      
      // Allow user to continue after 3 seconds even if save fails
      setTimeout(() => {
        console.log('⚠️ Allowing user to continue despite network error')
        onAccept()
      }, 3000)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 50,
      padding: '1rem'
    }}>
      <div style={{
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '1.5rem',
        maxWidth: '28rem',
        width: '100%',
        padding: '2rem',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Shield style={{ width: '1.25rem', height: '1.25rem', color: '#a855f7' }} />
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: 'white' }}>Consent Required</h3>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '0.25rem',
              color: '#9ca3af',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => (e.target as HTMLElement).style.color = 'white'}
            onMouseLeave={(e) => (e.target as HTMLElement).style.color = '#9ca3af'}
          >
            <X style={{ width: '1.25rem', height: '1.25rem' }} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: '0.75rem',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <AlertCircle style={{ width: '1.25rem', height: '1.25rem', color: '#fbbf24', flexShrink: 0, marginTop: '0.125rem' }} />
              <div style={{ fontSize: '0.875rem' }}>
                <p style={{ color: '#fde68a', fontWeight: '500', marginBottom: '0.25rem' }}>Data Processing Notice</p>
                <p style={{ color: 'rgba(253, 230, 138, 0.8)' }}>
                  Sophia logs and processes your voice to improve your experience. 
                  We use this data for AI-generated DeFi education with voice analytics.
                </p>
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.875rem', color: '#d1d5db' }}>
            <h4 style={{ fontWeight: '500', color: 'white', marginBottom: '0.5rem' }}>What we collect:</h4>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', color: '#9ca3af', lineHeight: '1.6' }}>
              <li>Voice recordings for transcription and emotion analysis</li>
              <li>Chat messages and AI responses</li>
              <li>Usage patterns and session data</li>
              <li>Discord profile information (username, avatar)</li>
            </ul>
          </div>

          <div style={{ fontSize: '0.875rem', color: '#d1d5db' }}>
            <h4 style={{ fontWeight: '500', color: 'white', marginBottom: '0.5rem' }}>How we use it:</h4>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', color: '#9ca3af', lineHeight: '1.6' }}>
              <li>Provide personalized DeFi education</li>
              <li>Improve AI response quality</li>
              <li>Analyze conversation effectiveness</li>
              <li>Ensure system security and compliance</li>
            </ul>
          </div>

          <div style={{
            background: 'rgba(31, 41, 55, 0.5)',
            borderRadius: '0.75rem',
            padding: '0.75rem'
          }}>
            <p style={{ fontSize: '0.75rem', color: '#9ca3af', lineHeight: '1.5' }}>
              We will store a hashed consent record with timestamp and your IP address. 
              You can withdraw consent at any time by contacting support.
            </p>
          </div>

          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '0.75rem',
              padding: '0.75rem'
            }}>
              <p style={{ color: '#f87171', fontSize: '0.875rem' }}>{error}</p>
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.5rem' }}>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                border: '1px solid #4b5563',
                color: '#d1d5db',
                borderRadius: '0.75rem',
                background: 'transparent',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                opacity: isSubmitting ? 0.5 : 1
              }}
              onMouseEnter={(e) => !isSubmitting && ((e.target as HTMLElement).style.background = '#374151')}
              onMouseLeave={(e) => !isSubmitting && ((e.target as HTMLElement).style.background = 'transparent')}
            >
              Cancel
            </button>
            <button
              onClick={handleAccept}
              disabled={isSubmitting}
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                background: isSubmitting ? '#6b46c1' : 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.75rem',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                opacity: isSubmitting ? 0.5 : 1,
                fontWeight: '500'
              }}
              onMouseEnter={(e) => !isSubmitting && ((e.target as HTMLElement).style.background = 'linear-gradient(135deg, #4338ca 0%, #6d28d9 100%)')}
              onMouseLeave={(e) => !isSubmitting && ((e.target as HTMLElement).style.background = 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)')}
            >
              {isSubmitting ? 'Saving...' : 'I Agree'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
