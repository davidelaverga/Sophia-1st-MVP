import "./globals.css"
import { Providers } from "./providers"
import { copy } from "../copy"
import { inter } from "./fonts"

export const metadata = {
  title: `${copy.brand.name} – ${copy.brand.tagline}`,
  description: copy.auth.subtitle,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-sophia-bg text-sophia-text antialiased">
        <Providers>
          <div className="min-h-[100svh]">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}
