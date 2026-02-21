import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: false,
          flowType: "pkce",
          // Bypass Navigator LockManager to prevent timeout errors.
          // The default implementation uses navigator.locks which can get stuck
          // from stale auth attempts and block all subsequent auth operations.
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          lock: (async (_name: string, _acquireTimeout: number, fn: () => Promise<any>) => {
            return await fn();
          }) as any,
        },
      })
    : null;
