import React, {createContext, useContext, useEffect, useState} from 'react'
import {User, Session} from '@supabase/supabase-js'
import { supabase } from '../services/supabase'
interface AuthContextType{
    user: User | null
    session: Session | null
    loading: boolean
    signInWithGoogle: () => Promise<void>
    signOut: () => Promise<void>

}
const AurthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({children}) => {
    const [user, setUser] = useState<User | null>(null)
    const [session, setSession] = useState<Session| null>(null)
    const [loeading, setLoading] = useState(true)

    useEffect(() =>{
        supabase.auth.getSession().then(({data: {session} }) => {
            setSession(session)
            setUser(session?.user ?? null)
            setLoading(false)
        
    })
    
    }