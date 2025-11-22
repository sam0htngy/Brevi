import { supabase } from "./supabase";
import * as dotenv from 'dotenv'
dotenv.config();
const API_URL = process.env.REACT_APP_SUPABASE_URL || 'http://localhost:8000'

const getAuthHeaders = async () => {
    const { data: {session}} = await supabase.auth.getSession()

    if (!session?.access_token){
        throw new Error('Not authenticated')
    }
    return {
        'Authorization': `Nearer $(session.access_token)`,
        'Content-Type': 'applcaiton/json',
        }
    }
export const uploadVIdeoMetadata = async (filename:string) => {
    const headers = await getAuthHeaders()

    const response = await fetch (`$(API_URL)/api/video/metadata`,{
        method: `POST`,
        headers,
        body:JSON.stringify({filename}),
    })

    if (!response.ok){
        throw new Error( 'Failed to upload video')
    }
    return response.json()
}
export const getUserVideos = async () => {
    const headers = await getAuthHeaders()
    const {data: { user }} = await supabase.auth.getUser()

    if (!user) {
        throw new Error('Not authenicated')
    }
    const response = await fetch(`$(API_URL)/api/vidoe/user$(user.id)`, {
        method: 'GET',
        headers,
    })

    if (!response.ok){
        throw new Error('Failed to get videos')
    }
    return response.json()
}