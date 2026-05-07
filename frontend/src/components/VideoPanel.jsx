import React, { useEffect, useRef, useState } from 'react'
import { Camera, Upload, MonitorPlay } from 'lucide-react'

const API_BASE_URL = 'http://localhost:5000'

export const VideoPanel = ({ frameData, isLoading, liveData }) => {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const fileInputRef = useRef(null)
  const [mode, setMode] = useState('live')
  const [cameraError, setCameraError] = useState('')
  const [uploadedPreviewUrl, setUploadedPreviewUrl] = useState('')
  const [uploadedMedia, setUploadedMedia] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [peopleCount, setPeopleCount] = useState(0)
  const [status, setStatus] = useState('NORMAL')

  // Update metrics from backend
  useEffect(() => {
    if (liveData) {
      setPeopleCount(liveData.count || 0)
      setStatus(liveData.status || 'NORMAL')
    }
  }, [liveData])

  // Camera / feed setup
  useEffect(() => {
    const stopStream = () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
    }

    const startLiveCamera = async () => {
      try {
        setCameraError('')
        stopStream()

        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'user',
            width: { ideal: 1280 },
            height: { ideal: 1280 },
          },
          audio: false,
        })

        streamRef.current = stream

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
      } catch (error) {
        console.error('Camera error:', error)
        setCameraError(`Camera error: ${error.message}`)
      }
    }

    const startBackendFeed = async () => {
      try {
        setCameraError('')
        stopStream()

        const response = await fetch(`${API_BASE_URL}/switch-source`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: 0 })
        })

        if (!response.ok) {
          throw new Error('Backend could not switch to the laptop camera')
        }

        setMode('backend')
      } catch (error) {
        console.error('Camera error:', error)
        setCameraError(`Camera error: ${error.message}`)
      }
    }

    if (mode === 'live') {
      startLiveCamera()
    } else if (mode === 'backend') {
      startBackendFeed()
    } else {
      stopStream()
      if (videoRef.current) {
        videoRef.current.srcObject = null
      }
    }

    return () => {
      stopStream()
    }
  }, [mode])

  // Upload video handling
  useEffect(() => {
    if (mode === 'upload' && uploadedMedia && videoRef.current) {
      videoRef.current.srcObject = null
      const url = URL.createObjectURL(uploadedMedia)
      setUploadedPreviewUrl(url)
      videoRef.current.src = url
      videoRef.current.load()
    }
  }, [mode, uploadedMedia])

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadError('')

    try {
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('file', file)

      // Upload to backend
      const response = await fetch(`${API_BASE_URL}/upload-video`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Upload failed')
      }

      const result = await response.json()
      console.log('Video uploaded successfully:', result)

      // Also show local preview
      if (uploadedPreviewUrl) {
        URL.revokeObjectURL(uploadedPreviewUrl)
      }

      setUploadedMedia(file)
      const url = URL.createObjectURL(file)
      setUploadedPreviewUrl(url)
      setMode('upload')
      
    } catch (error) {
      console.error('Upload error:', error)
      setUploadError(error.message || 'Failed to upload video')
    } finally {
      setIsUploading(false)
    }
  }

  const frameUrl = frameData ? `data:image/jpeg;base64,${frameData}` : null

  return (
    <div className="mx-auto w-full max-w-[920px] overflow-hidden rounded-[2rem] border border-white/10 bg-[#07111f] shadow-2xl shadow-black/25">
      <div className="flex flex-col gap-4 border-b border-white/10 bg-white/5 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Live feed</p>
          <h3 className="mt-1 text-lg font-semibold text-white">Crowd monitoring camera</h3>
        </div>

        <div className="flex flex-wrap items-center gap-2 rounded-full border border-white/10 bg-black/20 p-1 w-fit">
          <button
            onClick={() => setMode('live')}
            className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium transition-colors ${
              mode === 'live' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'
            }`}
          >
            <Camera className="h-3.5 w-3.5" />
            Live camera
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium transition-colors ${
              mode === 'upload' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'
            } ${isUploading ? 'cursor-not-allowed opacity-50' : ''}`}
          >
            <Upload className="h-3.5 w-3.5" />
            {isUploading ? 'Uploading...' : 'Upload video'}
          </button>
          {frameData && (
            <button
              onClick={() => setMode('backend')}
              className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium transition-colors ${
                mode === 'backend' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'
              }`}
              title="Backend detected feed with bounding boxes"
            >
              <MonitorPlay className="h-3.5 w-3.5" />
              Backend feed
            </button>
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="relative mx-auto flex aspect-square w-full max-w-[840px] items-center justify-center overflow-hidden bg-black">
        {uploadError && (
          <div className="absolute inset-0 flex items-center justify-center text-center px-6 bg-black/70 z-10">
            <div className="max-w-sm rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-red-100">
              <p className="mb-2 text-base font-semibold">Upload error</p>
              <p className="text-sm text-red-200/80">{uploadError}</p>
              <button
                onClick={() => setUploadError('')}
                className="mt-3 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}
        {mode === 'live' ? (
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="h-full w-full object-cover bg-black"
          />
        ) : mode === 'backend' && frameData ? (
          <img
            src={frameUrl}
            alt="Backend detected feed"
            className="h-full w-full object-cover bg-black"
            key={frameData}
          />
        ) : mode === 'upload' && uploadedPreviewUrl ? (
          <video
            ref={videoRef}
            controls
            autoPlay
            muted
            playsInline
            src={uploadedPreviewUrl}
            className="h-full w-full object-cover bg-black"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-6 text-center text-slate-400">
            <p className="text-base font-medium text-slate-200">No video feed available</p>
            <p className="mt-2 text-sm">
              {mode === 'live'
                ? 'Waiting for the backend camera feed...'
                : mode === 'backend'
                ? 'Waiting for backend detected feed...'
                : 'Select a video file to upload'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
