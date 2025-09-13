-- Create user_consents table for storing user consent data
CREATE TABLE IF NOT EXISTS public.user_consents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    discord_id TEXT NOT NULL,
    consent_hash TEXT NOT NULL,
    ip_address TEXT,
    timestamp BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique index on discord_id to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS user_consents_discord_id_idx ON public.user_consents (discord_id);

-- Create index on consent_hash for faster lookups
CREATE INDEX IF NOT EXISTS user_consents_consent_hash_idx ON public.user_consents (consent_hash);

-- Enable Row Level Security (RLS)
ALTER TABLE public.user_consents ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role to manage all records
CREATE POLICY "Service role can manage user consents" ON public.user_consents
    FOR ALL USING (auth.role() = 'service_role');

-- Create policy to allow authenticated users to read their own consent records
CREATE POLICY "Users can read own consent records" ON public.user_consents
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND 
        discord_id = (auth.jwt() -> 'user_metadata' ->> 'provider_id')::text
    );

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on row updates
CREATE TRIGGER update_user_consents_updated_at 
    BEFORE UPDATE ON public.user_consents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions
GRANT ALL ON public.user_consents TO service_role;
GRANT SELECT ON public.user_consents TO authenticated;
