import { Suspense, lazy } from "react"
import {Routes, Route } from "react-router-dom"


const Login = lazy(() => import ("./pages/Login"))
const FileUploader = lazy(() => import ("./pages/FileUploader"))

export default function App(){
    return(
            <Suspense fallback = {<div>Loading</div>}>
                <Routes>
                    <Route path = "/" element ={<Login/>}/>
                    <Route path = "/upload" element ={<FileUploader/>}/>
                </Routes>
            </Suspense>
    )
}