import React, { useEffect, useRef, useState } from 'react'
import { useVideoStore } from '@/stores/video'
import { VideoPlayer } from '@/components/video/VideoPlayer'
import { VideoJobCard } from '@/components/video/VideoJobCard'
import { VideoHistory } from '@/components/video/VideoHistory'
import {
  Film,
  Sparkles,
  Upload,
  X,
  Play,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  Type,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

export function VideoGeneratorView() {
  const {
    models,
    activeModel,
    mode,
    prompt,
    negativePrompt,
    aspectRatio,
    resolution,
    duration,
    fps,
    seed,
    referenceImage,
    activeJob,
    history,
    isEnhancing,
    isSubmitting,
    isUploadingRef,
    health,
    selectedVideo,
    error,
    setActiveModel,
    setMode,
    setPrompt,
    setNegativePrompt,
    setAspectRatio,
    setResolution,
    setDuration,
    setFps,
    setSeed,
    setSelectedVideo,
    clearError,
    loadInitialData,
    enhanceCurrentPrompt,
    uploadReferenceFile,
    clearReferenceImage,
    startGeneration,
    cancelJob,
    deleteVideo,
  } = useVideoStore()

  const [showAdvanced, setShowAdvanced] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadInitialData()
  }, [loadInitialData])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadReferenceFile(file)
    }
  }

  const selectedModelMeta = models.find((m) => m.model_id === activeModel)

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto">
      {/* Studio Top Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/40 backdrop-blur-sm sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-violet-500 text-white flex items-center justify-center shadow-md">
            <Film size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-foreground">AI Video Generation Studio</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold border border-primary/20">
                NVIDIA NIM
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Synthesize cinematic 24fps MP4 videos using Wan 2.2 and Cosmos 3 Nano
            </p>
          </div>
        </div>

        {/* Live Provider Health Pill */}
        <div className="flex items-center gap-2">
          {health ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{models.length} Video Models Ready</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted border border-border text-xs text-muted-foreground">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>Checking NVIDIA Services...</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Generator Controls */}
        <div className="lg:col-span-6 flex flex-col gap-5">
          {/* Modality Tabs */}
          <div className="flex p-1 rounded-xl bg-muted/60 border border-border">
            <button
              onClick={() => setMode('text_to_video')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === 'text_to_video'
                  ? 'bg-background text-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Type size={14} />
              <span>Text to Video</span>
            </button>
            <button
              onClick={() => setMode('image_to_video')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === 'image_to_video'
                  ? 'bg-background text-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <ImageIcon size={14} />
              <span>Image to Video</span>
            </button>
          </div>

          {/* Reference Image Dropzone (for Image-to-Video) */}
          {mode === 'image_to_video' && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-foreground">Reference Starting Frame</label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />

              {referenceImage ? (
                <div className="relative group rounded-xl border border-primary/40 overflow-hidden aspect-video bg-black/60 flex items-center justify-center">
                  <img
                    src={referenceImage.previewUrl}
                    alt="Reference preview"
                    className="w-full h-full object-contain"
                  />
                  <button
                    onClick={clearReferenceImage}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/70 text-white hover:bg-destructive transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-border/80 hover:border-primary/60 rounded-xl bg-muted/20 hover:bg-muted/40 cursor-pointer transition-all"
                >
                  <Upload size={22} className="text-muted-foreground mb-2" />
                  <p className="text-xs font-medium text-foreground">
                    {isUploadingRef ? 'Uploading reference...' : 'Click or drop starting frame image'}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">PNG, JPG or WebP up to 15MB</p>
                </div>
              )}
            </div>
          )}

          {/* Prompt Box */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-foreground">Cinematic Prompt</label>
              <Button
                variant="outline"
                size="sm"
                onClick={enhanceCurrentPrompt}
                disabled={isEnhancing || !prompt.trim()}
                className="h-7 gap-1 text-[11px] rounded-lg text-primary border-primary/30 hover:bg-primary/10"
              >
                <Sparkles size={12} className={isEnhancing ? 'animate-spin' : ''} />
                <span>{isEnhancing ? 'Enhancing...' : 'Enhance Prompt'}</span>
              </Button>
            </div>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Cinematic slow-motion drone flyover of an ancient moss-covered castle perched on a misty cliff, golden hour sunlight breaking through volumetric fog, ultra-realistic 8k details..."
              rows={4}
              className="w-full rounded-xl border border-border bg-card p-3 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none shadow-xs"
            />
          </div>

          {/* Model Selector */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-foreground">Video AI Model</label>
            <div className="grid grid-cols-2 gap-2">
              {models.map((m) => {
                const isActive = activeModel === m.model_id
                return (
                  <button
                    key={m.model_id}
                    onClick={() => setActiveModel(m.model_id)}
                    className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
                      isActive
                        ? 'border-primary bg-primary/5 ring-1 ring-primary/40'
                        : 'border-border bg-card hover:border-border/80'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-xs text-foreground">{m.name}</span>
                      {isActive && <CheckCircle2 size={14} className="text-primary" />}
                    </div>
                    <span className="text-[10px] text-muted-foreground mt-1 line-clamp-1">
                      {m.description}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Core Parameters Grid */}
          <div className="grid grid-cols-3 gap-3">
            {/* Aspect Ratio */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold text-muted-foreground">Aspect Ratio</label>
              <div className="grid grid-cols-3 gap-1 bg-muted/60 p-1 rounded-lg border border-border">
                {['16:9', '9:16', '1:1'].map((ar) => (
                  <button
                    key={ar}
                    onClick={() => setAspectRatio(ar)}
                    className={`py-1 rounded text-center text-xs font-medium transition-all ${
                      aspectRatio === ar
                        ? 'bg-background text-foreground shadow-xs font-semibold'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {ar}
                  </button>
                ))}
              </div>
            </div>

            {/* Duration */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold text-muted-foreground">Duration</label>
              <div className="grid grid-cols-2 gap-1 bg-muted/60 p-1 rounded-lg border border-border">
                {[5, 8].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDuration(d)}
                    className={`py-1 rounded text-center text-xs font-medium transition-all ${
                      duration === d
                        ? 'bg-background text-foreground shadow-xs font-semibold'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {d}s
                  </button>
                ))}
              </div>
            </div>

            {/* Resolution */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold text-muted-foreground">Resolution</label>
              <div className="grid grid-cols-2 gap-1 bg-muted/60 p-1 rounded-lg border border-border">
                {['720p', '480p'].map((r) => (
                  <button
                    key={r}
                    onClick={() => setResolution(r)}
                    className={`py-1 rounded text-center text-xs font-medium transition-all ${
                      resolution === r
                        ? 'bg-background text-foreground shadow-xs font-semibold'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Advanced Collapsible */}
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors self-start"
            >
              <SlidersHorizontal size={13} />
              <span>Advanced Parameters</span>
              {showAdvanced ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {showAdvanced && (
              <div className="flex flex-col gap-3 p-3 rounded-xl border border-border bg-muted/20">
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-medium text-muted-foreground">Negative Prompt</label>
                  <input
                    type="text"
                    value={negativePrompt}
                    onChange={(e) => setNegativePrompt(e.target.value)}
                    placeholder="blurry, distorted, jitter, low quality, artifacting..."
                    className="w-full rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] font-medium text-muted-foreground">FPS (Frames/sec)</label>
                    <div className="flex gap-1">
                      {[16, 24, 30].map((f) => (
                        <button
                          key={f}
                          onClick={() => setFps(f)}
                          className={`flex-1 py-1 rounded text-xs border ${
                            fps === f ? 'bg-primary text-primary-foreground border-primary' : 'bg-card border-border'
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] font-medium text-muted-foreground">Random Seed</label>
                    <input
                      type="number"
                      value={seed || ''}
                      onChange={(e) => setSeed(e.target.value ? parseInt(e.target.value) : undefined)}
                      placeholder="Random"
                      className="w-full rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Error Banner */}
          {error && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs">
              <div className="flex items-center gap-2">
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
              <button onClick={clearError} className="hover:opacity-70">
                <X size={14} />
              </button>
            </div>
          )}

          {/* Submit Button */}
          <Button
            onClick={startGeneration}
            disabled={isSubmitting || !prompt.trim()}
            className="w-full py-5 rounded-xl font-bold text-sm bg-gradient-to-r from-primary via-violet-600 to-indigo-600 hover:opacity-95 text-white shadow-lg shadow-primary/20 transition-all active:scale-[0.99]"
          >
            <Play size={16} className="mr-2 fill-current" />
            <span>{isSubmitting ? 'Starting Video Generation...' : 'Generate AI Video'}</span>
          </Button>
        </div>

        {/* Right Column: Player, Active Job & History */}
        <div className="lg:col-span-6 flex flex-col gap-5">
          {/* Active Job Card */}
          {activeJob && ['queued', 'submitting', 'generating', 'processing'].includes(activeJob.status) && (
            <VideoJobCard job={activeJob} onCancel={cancelJob} />
          )}

          {/* Active Video Player */}
          {selectedVideo && selectedVideo.status === 'completed' ? (
            <div className="flex flex-col gap-2">
              <h2 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Play size={12} className="text-primary fill-current" />
                <span>Active Video Player</span>
              </h2>
              <VideoPlayer video={selectedVideo} />
            </div>
          ) : !activeJob && (
            <div className="aspect-video rounded-2xl border border-dashed border-border/80 bg-muted/10 flex flex-col items-center justify-center p-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                <Film size={26} />
              </div>
              <p className="text-sm font-semibold text-foreground">Video Preview Area</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                Generated videos will automatically play here with range streaming, frame scrubbing, and high-speed MP4 download.
              </p>
            </div>
          )}

          {/* History Gallery */}
          <div className="flex flex-col gap-3 mt-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Film size={12} className="text-primary" />
                <span>Generation History ({history.length})</span>
              </h2>
            </div>

            <VideoHistory
              videos={history}
              selectedId={selectedVideo?.id}
              onSelect={setSelectedVideo}
              onUsePrompt={setPrompt}
              onDelete={deleteVideo}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
