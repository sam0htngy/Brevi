import React from 'react'
import ReactDOM from 'react-dom/client'
import Login from './components/Login';
import MainPage from './components/MainPage';

const root = ReactDOM.createRoot(
    document.getElementById("root") as HTMLElement);
root.render(
    <React.StrictMode>
        <Login/>
        <MainPage/>
    </React.StrictMode>
)