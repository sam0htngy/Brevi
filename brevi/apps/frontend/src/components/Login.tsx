import React from 'react'
import { useAuth } from '../components/AuthContext'

const Login: React.FC = () => {
    const {signInWithGoogle} = useAuth()
    const handleGoogleSignIn = async () => {
        try {
            await signInWithGoogle()
        } catch (error){
            console.error('Error siginign in', error)
            alert('Failed to sign in with Google')
        }
    }
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            padding: '20px'
        }}></div>
        
    )
}