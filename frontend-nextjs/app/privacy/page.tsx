"use client"

/* eslint-disable i18next/no-literal-string */
/* eslint-disable react/no-unescaped-entities */

import Link from "next/link"
import { ArrowLeft, Shield, Eye, Database, Lock, Users, Mail, Calendar } from "lucide-react"

const LAST_UPDATED = "December 1, 2025"

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-sophia-bg">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-sophia-text/5 bg-sophia-bg/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-4 py-4">
          <Link 
            href="/"
            className="flex items-center gap-2 rounded-xl p-2 text-sophia-text2 transition-colors hover:bg-sophia-purple/10 hover:text-sophia-purple"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-xl font-semibold text-sophia-text">Privacy Policy</h1>
            <p className="text-sm text-sophia-text2">Last updated: {LAST_UPDATED}</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {/* Introduction */}
        <section className="mb-12">
          <div className="rounded-2xl bg-gradient-to-br from-sophia-purple/10 via-sophia-card to-sophia-card p-6 ring-1 ring-sophia-purple/10">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-sophia-purple/20 p-3">
                <Shield className="h-6 w-6 text-sophia-purple" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-sophia-text">Your Privacy Matters</h2>
                <p className="mt-2 text-sophia-text2 leading-relaxed">
                  Sophia is designed with privacy at its core. We believe in transparency about how we handle your data. 
                  This policy explains what we collect, why, and how you can control it.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Policy sections */}
        <div className="space-y-8">
          
          {/* What We Collect */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Database className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">What We Collect</h2>
            </div>
            <div className="space-y-4 text-sophia-text2">
              <div>
                <h3 className="font-medium text-sophia-text">Conversation Data</h3>
                <p className="mt-1 leading-relaxed">
                  We store your conversations with Sophia to provide personalized responses and improve the experience. 
                  This includes messages, detected emotions, and learning insights.
                </p>
              </div>
              <div>
                <h3 className="font-medium text-sophia-text">Account Information</h3>
                <p className="mt-1 leading-relaxed">
                  When you sign in with Discord, we receive your Discord ID, username, and email (if provided). 
                  We use this to identify your account and sessions.
                </p>
              </div>
              <div>
                <h3 className="font-medium text-sophia-text">Usage Analytics</h3>
                <p className="mt-1 leading-relaxed">
                  We collect anonymized usage data to understand how people interact with Sophia. 
                  This helps us improve features and fix issues.
                </p>
              </div>
            </div>
          </section>

          {/* How We Use Your Data */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Eye className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">How We Use Your Data</h2>
            </div>
            <ul className="space-y-3 text-sophia-text2">
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                <span>Provide personalized DeFi education and emotional support</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                <span>Remember context from previous conversations</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                <span>Generate reflection insights and wisdom cards</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                <span>Improve AI responses and safety measures</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                <span>Share anonymized wisdom with the community (only if you choose to)</span>
              </li>
            </ul>
          </section>

          {/* Community Sharing */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Users className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">Community Sharing</h2>
            </div>
            <div className="space-y-4 text-sophia-text2">
              <p className="leading-relaxed">
                When you choose to share a reflection with the community, we <strong className="text-sophia-text">completely anonymize</strong> it:
              </p>
              <ul className="space-y-2 pl-4">
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>Your identity is never attached to shared reflections</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>Only the wisdom text is shared, not conversation context</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>You can keep reflections private at any time</span>
                </li>
              </ul>
            </div>
          </section>

          {/* Data Security */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Lock className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">Data Security</h2>
            </div>
            <div className="space-y-4 text-sophia-text2">
              <p className="leading-relaxed">
                We take security seriously and implement industry-standard measures:
              </p>
              <ul className="space-y-2 pl-4">
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>All data is encrypted in transit (HTTPS/TLS)</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>Database encryption at rest</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>Row-level security for user data isolation</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-sophia-purple" />
                  <span>Regular security audits and monitoring</span>
                </li>
              </ul>
            </div>
          </section>

          {/* Your Rights */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Shield className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">Your Rights</h2>
            </div>
            <div className="space-y-4 text-sophia-text2">
              <p className="leading-relaxed">You have full control over your data:</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl bg-sophia-bg/50 p-4">
                  <h3 className="font-medium text-sophia-text">Export Data</h3>
                  <p className="mt-1 text-sm">Download all your data at any time from Settings → Privacy</p>
                </div>
                <div className="rounded-xl bg-sophia-bg/50 p-4">
                  <h3 className="font-medium text-sophia-text">Delete Account</h3>
                  <p className="mt-1 text-sm">Permanently delete all your data from our systems</p>
                </div>
                <div className="rounded-xl bg-sophia-bg/50 p-4">
                  <h3 className="font-medium text-sophia-text">Withdraw Consent</h3>
                  <p className="mt-1 text-sm">Revoke data processing consent at any time</p>
                </div>
                <div className="rounded-xl bg-sophia-bg/50 p-4">
                  <h3 className="font-medium text-sophia-text">Access Logs</h3>
                  <p className="mt-1 text-sm">Request a log of how your data has been accessed</p>
                </div>
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="rounded-2xl bg-sophia-surface p-6 ring-1 ring-sophia-text/5">
            <div className="mb-4 flex items-center gap-3">
              <Mail className="h-5 w-5 text-sophia-purple" />
              <h2 className="text-lg font-semibold text-sophia-text">Contact Us</h2>
            </div>
            <p className="text-sophia-text2 leading-relaxed">
              If you have questions about this privacy policy or how we handle your data, 
              please reach out to us:
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <a 
                href="mailto:privacy@sophia.ai"
                className="inline-flex items-center gap-2 rounded-xl bg-sophia-purple/10 px-4 py-2 text-sm font-medium text-sophia-purple transition-colors hover:bg-sophia-purple/20"
              >
                <Mail className="h-4 w-4" />
                privacy@sophia.ai
              </a>
              <a 
                href="https://discord.gg/sophia"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-sophia-text/10 px-4 py-2 text-sm font-medium text-sophia-text2 transition-colors hover:border-sophia-purple/30 hover:text-sophia-purple"
              >
                <Users className="h-4 w-4" />
                Discord Community
              </a>
            </div>
          </section>

          {/* Last updated notice */}
          <div className="flex items-center justify-center gap-2 pt-4 text-sm text-sophia-text2">
            <Calendar className="h-4 w-4" />
            <span>This policy was last updated on {LAST_UPDATED}</span>
          </div>
        </div>
      </main>
    </div>
  )
}
