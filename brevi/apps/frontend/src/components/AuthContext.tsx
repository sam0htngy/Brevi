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
