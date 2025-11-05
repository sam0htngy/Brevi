import React, {Children, createContext, useContext, useEffect, useState} from 'react'
import {User, Session} from '@supabase/supabase-js'
import { supabase } from '../services/supabase'
import { error } from 'console'
interface AuthContextType{
    user: User | null
    session: Session | null
    loading: boolean
    signInWithGoogle: () => Promise<void>
    signOut: () => Promise<void>

}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe() },[])

    

const signInWithGoogle = async () => {
    const {error} = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: '${window.location.origin}/auth/callback',
        },
    })
    if (error) throw error
}

const signOut = async () => {
    const {error} = await supabase.auth.signOut()
    if (error) throw error
}

return(
    <AuthContext.Provider value={{user, session, loading, signInWithGoogle, signOut}}>
        {children}
    </AuthContext.Provider>
)
}
export const useAuth = () => {
    const context =useContext(AuthContext)
    if (context === undefined){
        throw new Error('useAuth must be used with in an Auth Provider')
    }
    return context
}