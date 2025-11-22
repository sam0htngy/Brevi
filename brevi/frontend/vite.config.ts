import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
declare namespace NodeJS{
  interface ProcessEnv{
    API_Key: string;
    DATABASE_URL: string;
    VITE_CLERK_PUBLISHABLE_KEY: string;
  }
}