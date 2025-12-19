import { useState, type ChangeEvent } from "react"
import '../tailwind.css'
import { createClient } from "@supabase/supabase-js";
import {useAuth} from "@clerk/clerk-react"

type UploadStatus = "idle" | "uploading" | "success!" | "error";
export default function FileUploader() {
  const supabase = createClient(
    'https://wnxibecjjtujiidzlftx.supabase.co',
    'PUBLIC_ANON_KEY'
  )
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<UploadStatus>("idle")
  

  function handlefileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files){
      setFile(e.target.files[0])

    }
  }

  async function handlefileUpload() {
 
}
    

  return(
    <div>
      <div className = "flex items-center justify-center min-h-screen bg-gray-100">
      <input className = "w-64 h-32 bg-wh ite shadow rounded"
      type="file" 
      accept="video/*" 
      onChange={handlefileChange}/>
      {file && status != "uploading" && <button onClick={handlefileUpload}>Upload</button>}

      {status === 'success!' && (
        <p className="">Upload Successful! Enjoy your video!</p>
      )}
      {status === 'error' && (
        <p className="">Upload failed please try again.</p>
      )}
      </div>
      </div>
  )
}
