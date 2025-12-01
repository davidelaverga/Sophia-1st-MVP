/** @type {import('next').NextConfig} */
const nextConfig = {
  // Environment variables (Vercel will handle these automatically)
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  
  // Performance optimizations
  experimental: {
    optimizePackageImports: ['lucide-react', '@supabase/supabase-js', 'zustand'],
  },
  
  // Compiler optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },
  
  // Bundle analyzer (uncomment to analyze)
  // webpack: (config, { isServer }) => {
  //   if (!isServer) {
  //     const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
  //     config.plugins.push(new BundleAnalyzerPlugin({ analyzerMode: 'static' }));
  //   }
  //   return config;
  // },
}

module.exports = nextConfig