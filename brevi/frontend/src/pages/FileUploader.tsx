import { useState } from "react"

export default function FileUploader() {
  const [File, setFile] = useState<File | null>(null)


  return(
    <div>
      <input type="file" accept="video/*"/>
       </div>
  )
}