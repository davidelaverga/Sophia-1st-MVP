/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove standalone output for Vercel deployment (use default for Vercel)
  // output: 'standalone', // This is for Docker/self-hosting, not Vercel
  
  // Optimize for Vercel deployment
  swcMinify: true,
  
  // Environment variables (Vercel will handle these automatically)
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Optimize bundle size
  experimental: {
    optimizeCss: true,
  },

  // Configure static optimization
  trailingSlash: false,
  
  // Reduce build output size
  compress: true,
}

module.exports = nextConfig