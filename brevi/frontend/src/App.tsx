import { Suspense, lazy } from "react"
import {Routes, Route } from "react-router-dom"


const Test = lazy(() => import ("./pages/Test"))
const Login = lazy(() => import ("./pages/Login"))
const FileUploader = lazy(() => import ("./pages/FileUploader"))

export default function App(){

    return(
            <Suspense fallback = {<div>Loading</div>}>
                <Routes>
                    <Route path = "/" element ={<Login/>}/>
                    <Route path = "/upload" element ={<FileUploader/>}/>
                    <Route path = "/test" element = {<Test/>}/>
                </Routes>
            </Suspense>
    )
}