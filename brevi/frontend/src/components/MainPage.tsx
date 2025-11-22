import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate} from 'react-router-dom'
import { AuthProvider,useAuth } from '../auth/AuthContext'
import Login from './Login'
import AuthCallback from '../auth/AuthCallback'
import '../styling/App.css'

const ProtectedRoute: React.FC<{ children: React.ReactNode}> = ({ children}) =>{
    const {user, loading} = useAuth()

    if (loading){
        return <div> Loading...</div>
    }
    if (!user) {
        return <Navigate to = "/login" replace />
    }
    return <>(children)</>
}
const Home: React.FC = () => {
    const {user, signOut} = useAuth()
    
    return(
        <div className='App'>
            <header className='App-header'>
            <h1>Brevi</h1>
            <p>Login in: {user?.email}</p>
            <button onClick={signOut}>Sign Out</button>
            <div style={{marginTop: '20px'}}>
                <p> You can now upload videos</p>
                {/* video component needs to be added here */}

            </div>
        </header>
    </div>
    )
};

const MainPage: React.FC = () => {
    return(
        <Router>
            <AuthProvider>
                <Routes>
                    <Route path='/login' element={<Login/>}/>
                    <Route path='/auth/callback' element={<AuthCallback/>}/>
                    <Route path = "/" element={<ProtectedRoute><Home/></ProtectedRoute>}/>
                </Routes>
            </AuthProvider>
        </Router>
    )
};
export default MainPage