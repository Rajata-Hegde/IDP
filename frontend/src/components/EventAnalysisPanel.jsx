import React, { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Camera, Clock3, FileVideo2, MapPin, ScanFace, ShieldAlert, Siren, Upload, Waves } from 'lucide-react'

const API_BASE_URL = 'http://localhost:5000'

const emptyResult = {
  incident_type: 'No Incident',
  confidence_score: 0,
  timestamp: '--:--',
  location: 'Unknown',
  analysis_timestamp: '',
  video: null,
  models: null,
}

const modelCards = [
  {
    title: 'Accident detection',
    description: 'Runs the accident LSTM head on shared MobileNetV2 features.',
    icon: AlertTriangle,
    accent: 'from-amber-400/20 to-orange-500/10',
  },
  {
    title: 'Violence detection',
    description: 'Runs the violence LSTM head on the same extracted feature stream.',
    icon: Siren,
    accent: 'from-rose-400/20 to-red-500/10',
  },
  {
    title: 'Shared features',
    description: 'Frames are sampled once, encoded once, and reused for both models.',
    icon: Waves,
    accent: 'from-cyan-400/20 to-blue-500/10',
  },
]

function formatPercent(score) {
  if (typeof score !== 'number') return '--'
  return `${Math.round(score * 100)}%`
}

export const EventAnalysisPanel = () => {
  const fileInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [result, setResult] = useState(emptyResult)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const handleUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setSelectedFile(file)
    setIsAnalyzing(true)
    setError('')
    setResult(emptyResult)

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setPreviewUrl(URL.createObjectURL(file))

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('system_location', 'Local monitoring workstation')

      const response = await fetch(`${API_BASE_URL}/analyze-event-video`, {
        method: 'POST',
        body: formData,
      })

      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to analyze the uploaded video')
      }

      setResult(payload)
    } catch (uploadError) {
      setError(uploadError.message || 'Failed to analyze the uploaded video')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const video = result.video || {}
  const violence = result.models?.violence || {}
  const accident = result.models?.accident || {}

  return (
    <div className="space-y-6">
      <div className="rounded-[2rem] border border-amber-500/15 bg-gradient-to-br from-slate-950 via-slate-950 to-amber-950/30 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-amber-100">
            <ScanFace className="h-4 w-4" />
            Event Analysis
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
            <FileVideo2 className="h-4 w-4" />
            Upload once, analyze twice
          </span>
        </div>

        <div className="mt-6 grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.35em] text-amber-200/70">Event video workflow</p>
            <h3 className="mt-3 max-w-2xl text-3xl font-black tracking-tight text-white sm:text-4xl">
              Detect accidents and violence from one uploaded video, with one shared feature pass.
            </h3>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
              The backend samples frames at 8 FPS, extracts MobileNetV2 features once, then runs the accident and
              violence LSTM models in parallel. The response includes incident type, confidence, timestamp, and the
              system location that processed the video.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isAnalyzing}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  isAnalyzing ? 'cursor-not-allowed bg-amber-500/40 text-white/70' : 'bg-amber-400 text-slate-950 hover:bg-amber-300'
                }`}
              >
                <Upload className="h-4 w-4" />
                {isAnalyzing ? 'Analyzing...' : 'Upload video'}
              </button>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
                <Camera className="h-4 w-4 text-cyan-200" />
                Camera/source metadata is attached by the backend
              </div>
            </div>

            <input ref={fileInputRef} type="file" accept="video/*" className="hidden" onChange={handleUpload} />
          </div>

          <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Capture notes</p>
            <div className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
              <p>• Video is uploaded from the user machine and processed on the backend workstation.</p>
              <p>• The backend includes a system location label so the capture source is traceable.</p>
              <p>• No repeated frame extraction is done for each model, which keeps computation lower.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {modelCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.title} className={`rounded-[1.75rem] border border-white/10 bg-gradient-to-br ${card.accent} p-5 shadow-xl shadow-black/10`}>
              <div className="inline-flex rounded-2xl bg-white/10 p-3 text-white">
                <Icon className="h-5 w-5" />
              </div>
              <h4 className="mt-4 text-lg font-semibold text-white">{card.title}</h4>
              <p className="mt-2 text-sm leading-6 text-slate-300">{card.description}</p>
            </div>
          )
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="rounded-[1.75rem] border border-white/10 bg-slate-950/70 p-5 shadow-2xl shadow-black/20">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Upload status</p>
          <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-300">Selected file</p>
            <p className="mt-1 text-base font-medium text-white">{selectedFile ? selectedFile.name : 'No file selected'}</p>
          </div>

          <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-black/40">
            <div className="border-b border-white/10 px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-400">
              Preview
            </div>
            <div className="flex min-h-[220px] items-center justify-center bg-black">
              {previewUrl ? (
                <video src={previewUrl} controls className="h-full w-full object-contain" />
              ) : (
                <p className="px-6 text-center text-sm text-slate-400">
                  Upload a video to preview it and run the two event detectors.
                </p>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-100">
              {error}
            </div>
          )}
        </div>

        <div className="rounded-[1.75rem] border border-white/10 bg-slate-950/70 p-5 shadow-2xl shadow-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Analysis result</p>
              <h3 className="mt-1 text-xl font-semibold text-white">Incident summary</h3>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-100">
              <ShieldAlert className="h-3.5 w-3.5" />
              {isAnalyzing ? 'Running inference' : 'Ready'}
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Incident type</p>
              <p className="mt-2 text-lg font-semibold text-white">{result.incident_type}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Confidence score</p>
              <p className="mt-2 text-lg font-semibold text-white">{formatPercent(result.confidence_score)}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Timestamp</p>
              <p className="mt-2 text-lg font-semibold text-white">{result.timestamp}</p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-slate-300">
                <MapPin className="h-4 w-4 text-cyan-200" />
                <p className="text-[11px] uppercase tracking-[0.18em]">System location</p>
              </div>
              <p className="mt-2 text-sm text-white">{result.location || video.system_location || 'Unknown'}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-slate-300">
                <Clock3 className="h-4 w-4 text-amber-200" />
                <p className="text-[11px] uppercase tracking-[0.18em]">Analysis time</p>
              </div>
              <p className="mt-2 text-sm text-white">{result.analysis_timestamp || '--'}</p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/8 p-4 text-sm leading-6 text-cyan-50/90">
            {video.camera_captured ? 'Camera capture was confirmed by the backend.' : 'The backend marked this as uploaded video footage, and it still includes the processing location label.'}
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Violence model</p>
              <p className="mt-2 text-lg font-semibold text-white">{violence.detected ? 'Violence detected' : 'No violence detected'}</p>
              <p className="mt-1 text-sm text-slate-300">Confidence: {formatPercent(violence.confidence)}</p>
              <p className="mt-1 text-sm text-slate-300">Timestamp: {violence.timestamp || '--:--'}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Accident model</p>
              <p className="mt-2 text-lg font-semibold text-white">{accident.detected ? 'Accident detected' : 'No accident detected'}</p>
              <p className="mt-1 text-sm text-slate-300">Confidence: {formatPercent(accident.confidence)}</p>
              <p className="mt-1 text-sm text-slate-300">Timestamp: {accident.timestamp || '--:--'}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-[1.75rem] border border-white/10 bg-gradient-to-br from-amber-500/10 to-rose-500/10 p-5 shadow-xl shadow-black/10">
        <p className="text-xs uppercase tracking-[0.3em] text-amber-200/70">How it works</p>
        <h4 className="mt-2 text-xl font-semibold text-white">One uploaded video, two model heads, one shared feature stream.</h4>
        <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-300">
          The backend samples frames once, converts them into MobileNetV2 features once, and reuses that tensor stream for both the accident and violence models. That keeps the analysis cheaper while still returning the exact fields you asked for: incident type, confidence, timestamp, and captured location.
        </p>
      </div>
    </div>
  )
}
