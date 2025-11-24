import { useState, type ChangeEvent } from "react"
type UploadStatus = "idle" | "uploading" | "success" | "error"
import '../tailwind.css'
export default function FileUploader() {
  const [file, setFile] = useState<File | null>(null)
  

  function handlefileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files){
      setFile(e.target.files[0])

    }
  }

  return(
    <div>
      <div className = "flex items-center justify-center min-h-screen bg-gray-100">
      <input className = "w-64 h-32 bg-wh ite shadow rounded"
      type="file" 
      accept="video/*" 
      onChange={handlefileChange}/>
      {file && status != "uploading" && <button>Upload</button>}

      </div>
      </div>
  )
}