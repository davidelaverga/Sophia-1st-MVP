import "./globals.css"
import { Providers } from "./providers"
import { copy } from "../copy"
import { inter } from "./fonts"
import { ThemeBootstrap } from "./ThemeBootstrap"

export const metadata = {
  title: `${copy.brand.name} – ${copy.brand.tagline}`,
  description: copy.auth.subtitle,
}

// Viewport configuration for mobile optimization
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f8f7fa' },
    { media: '(prefers-color-scheme: dark)', color: '#1e1b2e' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        {/* DNS prefetch for external resources */}
        <link rel="dns-prefetch" href="https://api.openai.com" />
        <link rel="preconnect" href="https://api.openai.com" crossOrigin="anonymous" />
        
        {/* Preload critical theme script */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('sophia-theme') || 'light';
                  document.documentElement.dataset.sophiaTheme = theme;
                } catch (e) {
                  // localStorage may be unavailable (private browsing, SSR)
                  // Fallback to light theme is already applied via || 'light'
                  console.debug('[theme] localStorage unavailable, using default theme');
                }
              })();
            `,
          }}
        />
      </head>
      <body className="bg-sophia-bg text-sophia-text antialiased">
        <Providers>
          <ThemeBootstrap />
          <div className="min-h-[100svh]">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}
