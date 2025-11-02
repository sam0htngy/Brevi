import {createClient} from '@supabase/supabase-js'

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL!
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_KEY!

if(!supabaseUrl || !supabaseAnonKey){
    throw new Error('Missing Supabase enviroemnt variables')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)