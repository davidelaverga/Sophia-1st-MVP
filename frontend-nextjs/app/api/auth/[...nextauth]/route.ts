import NextAuth from 'next-auth'
import DiscordProvider from 'next-auth/providers/discord'
import { SupabaseAdapter } from '@next-auth/supabase-adapter'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const handler = NextAuth({
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
    })
  ],
  adapter: SupabaseAdapter({
    url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    secret: process.env.SUPABASE_SERVICE_ROLE_KEY!,
  }),
  callbacks: {
    async session({ session, user }) {
      // Add user ID to session
      session.user.id = user.id
      return session
    },
    async signIn({ user, account, profile }) {
      if (account?.provider === 'discord') {
        // Store Discord-specific data
        const discordProfile = profile as any
        
        // Check if user has given consent
        const { data: consent } = await supabase
          .from('user_consents')
          .select('*')
          .eq('discord_id', discordProfile.id)
          .single()

        // Store user data with consent status
        await supabase
          .from('users')
          .upsert({
            id: user.id,
            discord_id: discordProfile.id,
            username: discordProfile.username,
            discriminator: discordProfile.discriminator,
            avatar: discordProfile.avatar,
            email: user.email,
            has_consent: !!consent,
            updated_at: new Date().toISOString()
          })
      }
      return true
    }
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: 'database',
  },
})

export { handler as GET, handler as POST }
