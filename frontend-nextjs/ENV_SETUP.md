# Environment Variables Setup

Create a `.env.local` file in the `frontend-nextjs` directory with the following variables:

## Backend API Configuration (Server-side only)
These variables are used by Next.js API routes to proxy requests to the backend.
They are NOT exposed to the browser.

```bash
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key
```

## Public Configuration (Exposed to browser)
These variables are accessible in the browser and used for direct connections.

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
```

## Optional Configuration

### Mock Privacy APIs (Development)
Enable this to use frontend mocks when backend privacy endpoints are not ready:
```bash
NEXT_PUBLIC_MOCK_PRIVACY=true
```

### Supabase (Authentication)
If using Supabase for authentication:
```bash
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### NextAuth
If using NextAuth:
```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-here
```

## Production Configuration

For production deployment (Vercel):

1. Set `BACKEND_API_URL` to your production backend URL (e.g., `https://api.sophia.app`)
2. Set `BACKEND_API_KEY` to your production API key
3. Set `NEXT_PUBLIC_BACKEND_WS_URL` to your production WebSocket URL (e.g., `wss://api.sophia.app`)
4. Remove or set `NEXT_PUBLIC_MOCK_PRIVACY=false`

## How It Works

### API Proxying
All API calls from the frontend go through Next.js API routes (`/app/api/*`):
- `/api/conversation/respond` → proxies to `BACKEND_API_URL/text-chat/stream`
- `/api/conversation/feedback` → proxies to `BACKEND_API_URL/api/conversation/feedback`
- `/api/privacy/*` → proxies to `BACKEND_API_URL/api/privacy/*`
- `/api/reflections/*` → proxies to `BACKEND_API_URL/api/reflections/*`

This approach:
- Hides the backend URL and API key from the browser
- Allows CORS to be handled server-side
- Makes it easy to switch backends without changing frontend code

### Direct WebSocket Connection
Voice functionality uses a direct WebSocket connection to the backend:
- Frontend connects to `NEXT_PUBLIC_BACKEND_WS_URL/ws/voice`
- This is necessary because Next.js doesn't support WebSocket proxying in API routes

## Troubleshooting

### "Server configuration incomplete" error
Make sure you have created `.env.local` with at least `BACKEND_API_URL` and `BACKEND_API_KEY`.

### 404 errors on API calls
Check that your backend is running on the URL specified in `BACKEND_API_URL`.

### Voice connection fails
Verify that `NEXT_PUBLIC_BACKEND_WS_URL` is correct and the backend WebSocket endpoint is accessible.

### CORS errors
If you see CORS errors, make sure your backend allows requests from your frontend origin (e.g., `http://localhost:3000`).

