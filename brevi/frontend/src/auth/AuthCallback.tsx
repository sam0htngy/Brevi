import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthCallback: React.FC = () => {
    const navigate = useNavigate();

    useEffect(() =>{
        navigate('/')
    }, [navigate])


    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh'
        }}>
            <p>Completing Sign in</p>
        </div>
    )
};
export default AuthCallback