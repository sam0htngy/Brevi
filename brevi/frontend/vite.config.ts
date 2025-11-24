import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),
    tailwindcss(),
  ],
})
declare namespace NodeJS{
  interface ProcessEnv{
    API_Key: string;
    DATABASE_URL: string;
    VITE_CLERK_PUBLISHABLE_KEY: string;
  }
}