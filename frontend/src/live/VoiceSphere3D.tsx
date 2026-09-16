/**
 * HSBot Live Voice 3D Full-Color Voice Sphere.
 * Premium, futuristic living AI intelligence core.
 * 
 * Features:
 * - Full-color volumetric 3D sphere via WebGL shader (0 dependencies)
 * - Continuously shifting multi-color palette (electric blue, cyan, violet, purple, magenta, deep indigo, pink, white highlights)
 * - Real Web Audio AnalyserNode reactivity for Microphone & TTS Output
 * - States: IDLE, LISTENING, USER_SPEAKING, PROCESSING, AI_SPEAKING, INTERRUPTED, ERROR
 * - 60 FPS requestAnimationFrame loop with direct uniform updates (no React re-renders)
 * - Smooth lerp/easing on scale, glow, color, rotation, and distortion
 * - Atmospheric outer glow, volumetric inner light movement, parallax depth, fine particles
 * - Accessible: respects prefers-reduced-motion
 * - Resilient: graceful CSS animated fallback if WebGL is unavailable
 */

import React, { useEffect, useRef, useState } from 'react'
import { LiveState } from './LiveVoiceTypes'

export interface VoiceSphere3DProps {
  state: LiveState
  micAnalyser: AnalyserNode | null
  outputAnalyser: AnalyserNode | null
  size?: number
  className?: string
}

// GLSL Vertex Shader
const VS_SOURCE = `#version 300 es
in vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`

// GLSL Fragment Shader (WebGL 2)
const FS_SOURCE = `#version 300 es
precision highp float;

out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_scale;
uniform float u_audio_mic;
uniform float u_audio_tts;
uniform float u_energy;
uniform float u_glow;
uniform int u_state; // 0=IDLE, 1=LISTENING, 2=USER_SPEAKING, 3=PROCESSING, 4=AI_SPEAKING, 5=INTERRUPTED, 6=ERROR
uniform float u_reduced_motion;

// 3D Simplex Noise implementation
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 0.142857142857;
  vec3  ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}

// 3-Octave FBM
float fbm(vec3 p) {
  float v = 0.0;
  float a = 0.5;
  vec3 shift = vec3(100.0);
  for (int i = 0; i < 3; ++i) {
    v += a * snoise(p);
    p = p * 2.0 + shift;
    a *= 0.5;
  }
  return v;
}

// Multi-color palette generator:
// Electric blue -> Cyan -> Violet -> Purple -> Magenta -> Deep Indigo -> Pink -> White
vec3 getSpherePalette(float t, int state) {
  // Primary fluid multi-color spectrum
  vec3 cBlue    = vec3(0.0, 0.45, 1.0);    // Electric Blue
  vec3 cCyan    = vec3(0.0, 0.95, 0.98);   // Cyan
  vec3 cViolet  = vec3(0.56, 0.18, 0.98);  // Violet
  vec3 cPurple  = vec3(0.44, 0.06, 0.76);  // Purple
  vec3 cMagenta = vec3(0.95, 0.12, 0.62);  // Magenta
  vec3 cIndigo  = vec3(0.12, 0.06, 0.40);  // Deep Indigo
  vec3 cPink    = vec3(1.0, 0.45, 0.78);   // Subtle Pink

  // Error Palette: Crimson, dark violet, amber warning
  if (state == 6) {
    vec3 cRed = vec3(0.95, 0.15, 0.15);
    vec3 cDarkPurp = vec3(0.4, 0.05, 0.2);
    vec3 cAmber = vec3(1.0, 0.5, 0.1);
    float p = fract(t);
    if (p < 0.5) return mix(cRed, cDarkPurp, p * 2.0);
    return mix(cDarkPurp, cAmber, (p - 0.5) * 2.0);
  }

  // Listening Palette: Cyan + Electric Blue with soft violet rim
  if (state == 1) {
    float p = fract(t);
    if (p < 0.4) return mix(cBlue, cCyan, p / 0.4);
    if (p < 0.7) return mix(cCyan, cViolet, (p - 0.4) / 0.3);
    return mix(cViolet, cBlue, (p - 0.7) / 0.3);
  }

  // Continuous multi-color flow (User Speaking, AI Speaking, Processing, Idle)
  float p = fract(t);
  if (p < 0.16) return mix(cBlue, cCyan, p / 0.16);
  if (p < 0.33) return mix(cCyan, cViolet, (p - 0.16) / 0.17);
  if (p < 0.50) return mix(cViolet, cMagenta, (p - 0.33) / 0.17);
  if (p < 0.66) return mix(cMagenta, cPurple, (p - 0.50) / 0.16);
  if (p < 0.83) return mix(cPurple, cIndigo, (p - 0.66) / 0.17);
  return mix(cIndigo, cBlue, (p - 0.83) / 0.17);
}

// Ambient fine particle dust
float particles(vec2 uv, float time, float energy) {
  float p = 0.0;
  for (int i = 0; i < 7; i++) {
    float fi = float(i);
    float angle = fi * 0.897 + time * (0.2 + fi * 0.05);
    float radius = 0.36 + sin(time * 0.8 + fi * 1.5) * 0.08 + fi * 0.03;
    vec2 pos = vec2(cos(angle), sin(angle)) * radius;
    float dist = length(uv - pos);
    float size = 0.003 + sin(fi + time * 3.0) * 0.0015 + energy * 0.003;
    p += smoothstep(size, 0.0, dist) * (0.4 + energy * 0.6);
  }
  return p;
}

void main() {
  vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / min(u_resolution.x, u_resolution.y);
  float d = length(uv);

  // Responsive radius adjusted by smoothed scale and audio
  float baseR = 0.34;
  float R = baseR * u_scale;

  // Reduced motion slows down speed by 80%
  float speedFactor = u_reduced_motion > 0.5 ? 0.2 : 1.0;
  float time = u_time * speedFactor;

  // Background atmosphere
  vec4 color = vec4(0.0);

  if (d <= R) {
    // 1. Calculate 3D sphere surface normal
    float z = sqrt(max(0.0, R * R - d * d));
    vec3 normal = normalize(vec3(uv.x, uv.y, z));

    // Dynamic rotation & surface perturbation
    float rotAngle = time * 0.3;
    mat2 rotMat = mat2(cos(rotAngle), -sin(rotAngle), sin(rotAngle), cos(rotAngle));
    vec2 rotatedCoords = rotMat * normal.xy;
    vec3 p = vec3(rotatedCoords, normal.z) * 2.4;

    // Multi-layer volumetric noise
    float noise1 = fbm(p + vec3(0.0, 0.0, time * 0.4));
    float noise2 = fbm(p * 2.0 - vec3(time * 0.3, time * 0.2, 0.0));
    float noiseCombined = mix(noise1, noise2, 0.4);

    // Energy turbulence modulation from audio
    float turbulence = noiseCombined * (1.0 + u_energy * 0.85);

    // Continuous color palette flow
    float colorCoord = turbulence * 1.2 + time * 0.12;
    vec3 coreColor = getSpherePalette(colorCoord, u_state);

    // Secondary deep interior parallax layer
    vec3 innerP = vec3(rotatedCoords * 1.3, normal.z * 0.8) * 3.0 - vec3(time * 0.15);
    float innerNoise = fbm(innerP);
    vec3 innerColor = getSpherePalette(innerNoise * 1.5 + time * 0.2 + 0.35, u_state);

    // Blend inner core with surface
    vec3 finalColor = mix(innerColor, coreColor, 0.65 + 0.25 * normal.z);

    // 3D Moving Light Source & Specular highlights
    vec3 lightPos = normalize(vec3(sin(time * 0.75) * 0.6, cos(time * 0.6) * 0.5, 0.85));
    float diffuse = max(0.0, dot(normal, lightPos));
    vec3 halfVec = normalize(lightPos + vec3(0.0, 0.0, 1.0));
    float specular = pow(max(0.0, dot(normal, halfVec)), 28.0) * (0.6 + u_energy * 0.4);

    // 3D Fresnel Rim Light (cinematic edge glow)
    float fresnel = pow(1.0 - normal.z, 2.6);
    vec3 rimColor = getSpherePalette(colorCoord + 0.25, u_state);

    // Combine surface lighting
    finalColor = finalColor * (0.45 + 0.55 * diffuse) + rimColor * fresnel * (1.2 + u_glow * 0.8);
    finalColor += vec3(1.0) * specular;

    // Center brightness boost for intelligent living core
    float centerGlow = pow(normal.z, 2.2) * (0.25 + u_energy * 0.4);
    finalColor += mix(coreColor, vec3(1.0), 0.5) * centerGlow;

    // Smooth anti-aliased edge
    float edgeAlpha = smoothstep(R, R - 0.008, d);
    color = vec4(finalColor, edgeAlpha);

  } else {
    // 2. Glowing Outer Atmosphere & Bloom (d > R)
    float distToEdge = d - R;
    
    // Multi-tier exponential falloff
    float atmosphere1 = exp(-distToEdge * 18.0) * (0.8 + u_glow * 1.2);
    float atmosphere2 = exp(-distToEdge * 6.0) * (0.25 + u_glow * 0.4);
    float totalAtmo = atmosphere1 + atmosphere2;

    vec3 atmoColor = getSpherePalette(time * 0.15 + distToEdge * 2.0, u_state);
    
    // Soft blend into outer space
    color = vec4(atmoColor * totalAtmo, totalAtmo);
  }

  // 3. Ambient Floating Particles
  float spark = particles(uv, time, u_energy);
  if (spark > 0.01) {
    vec3 sparkColor = mix(vec3(1.0), getSpherePalette(time * 0.3, u_state), 0.4);
    color.rgb += sparkColor * spark;
    color.a = max(color.a, spark);
  }

  // Tone-mapping and soft filmic curve
  color.rgb = color.rgb / (color.rgb + vec3(0.85)) * 1.15;

  fragColor = clamp(color, 0.0, 1.0);
}
`

export function VoiceSphere3D({
  state,
  micAnalyser,
  outputAnalyser,
  size = 380,
  className = '',
}: VoiceSphere3DProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hasWebGLError, setHasWebGLError] = useState(false)
  const animFrameIdRef = useRef<number | null>(null)

  // Audio smoothing references (maintained directly for 60 FPS performance)
  const audioMicRef = useRef(0)
  const audioTtsRef = useRef(0)
  const scaleRef = useRef(1.0)
  const energyRef = useRef(0.0)
  const glowRef = useRef(0.0)
  const startTimeRef = useRef(performance.now())

  // Reduced motion preference
  const reducedMotionRef = useRef(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    reducedMotionRef.current = mediaQuery.matches

    const handler = (e: MediaQueryListEvent) => {
      reducedMotionRef.current = e.matches
    }
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  // WebGL Render Loop Initialization
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    let gl: WebGL2RenderingContext | null = null
    try {
      gl = canvas.getContext('webgl2', {
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
      })
    } catch (e) {
      console.warn('[VoiceSphere3D] WebGL2 not supported, falling back to CSS:', e)
      setHasWebGLError(true)
      return
    }

    if (!gl) {
      console.warn('[VoiceSphere3D] WebGL2 context unavailable, falling back to CSS')
      setHasWebGLError(true)
      return
    }

    // Compile Shader helper
    const compileShader = (type: number, source: string) => {
      const shader = gl!.createShader(type)
      if (!shader) return null
      gl!.shaderSource(shader, source)
      gl!.compileShader(shader)
      if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
        console.error('[VoiceSphere3D] Shader compile error:', gl!.getShaderInfoLog(shader))
        gl!.deleteShader(shader)
        return null
      }
      return shader
    }

    const vs = compileShader(gl.VERTEX_SHADER, VS_SOURCE)
    const fs = compileShader(gl.FRAGMENT_SHADER, FS_SOURCE)

    if (!vs || !fs) {
      setHasWebGLError(true)
      return
    }

    const program = gl.createProgram()
    if (!program) {
      setHasWebGLError(true)
      return
    }
    gl.attachShader(program, vs)
    gl.attachShader(program, fs)
    gl.linkProgram(program)

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('[VoiceSphere3D] Program link error:', gl.getProgramInfoLog(program))
      setHasWebGLError(true)
      return
    }

    gl.useProgram(program)

    // Full screen quad geometry
    const quadVertices = new Float32Array([
      -1.0, -1.0,
       1.0, -1.0,
      -1.0,  1.0,
      -1.0,  1.0,
       1.0, -1.0,
       1.0,  1.0,
    ])

    const vbo = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo)
    gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW)

    const posLoc = gl.getAttribLocation(program, 'position')
    gl.enableVertexAttribArray(posLoc)
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0)

    // Uniform Locations
    const uResolution = gl.getUniformLocation(program, 'u_resolution')
    const uTime = gl.getUniformLocation(program, 'u_time')
    const uScale = gl.getUniformLocation(program, 'u_scale')
    const uAudioMic = gl.getUniformLocation(program, 'u_audio_mic')
    const uAudioTts = gl.getUniformLocation(program, 'u_audio_tts')
    const uEnergy = gl.getUniformLocation(program, 'u_energy')
    const uGlow = gl.getUniformLocation(program, 'u_glow')
    const uState = gl.getUniformLocation(program, 'u_state')
    const uReducedMotion = gl.getUniformLocation(program, 'u_reduced_motion')

    // Audio buffers for byte data analysis
    const micDataArray = new Uint8Array(128)
    const ttsDataArray = new Uint8Array(128)

    // Map LiveState to integer for shader
    const getStateInt = (st: LiveState): number => {
      switch (st) {
        case 'IDLE':
        case 'CONNECTED':
          return 0
        case 'LISTENING':
          return 1
        case 'PROCESSING':
        case 'CONNECTING':
          return 3
        case 'SPEAKING':
          return 4
        case 'INTERRUPTED':
          return 5
        case 'ERROR':
        case 'DISCONNECTED':
          return 6
        default:
          return 1
      }
    }

    // High performance 60 FPS Render loop
    const render = (now: number) => {
      if (!gl || !canvas) return

      const elapsed = (now - startTimeRef.current) / 1000.0

      // 1. Calculate REAL Microphone Audio Amplitude
      let targetMicAudio = 0.0
      if (micAnalyser) {
        try {
          micAnalyser.getByteFrequencyData(micDataArray)
          let sum = 0
          for (let i = 0; i < micDataArray.length; i++) {
            sum += micDataArray[i]
          }
          const avg = sum / micDataArray.length
          targetMicAudio = Math.min(1.0, avg / 85.0)
        } catch (_) {}
      }

      // 2. Calculate REAL TTS Output Audio Amplitude
      let targetTtsAudio = 0.0
      if (outputAnalyser) {
        try {
          outputAnalyser.getByteFrequencyData(ttsDataArray)
          let sum = 0
          for (let i = 0; i < ttsDataArray.length; i++) {
            sum += ttsDataArray[i]
          }
          const avg = sum / ttsDataArray.length
          targetTtsAudio = Math.min(1.0, avg / 75.0)
        } catch (_) {}
      }

      // 3. Smooth Audio and State Transitions via lerp
      const isUserSpeaking = state === 'LISTENING' && targetMicAudio > 0.08
      const stateInt = isUserSpeaking ? 2 : getStateInt(state)

      // Lerp Audio Levels (quick attack, smooth decay)
      audioMicRef.current += (targetMicAudio - audioMicRef.current) * (targetMicAudio > audioMicRef.current ? 0.35 : 0.12)
      audioTtsRef.current += (targetTtsAudio - audioTtsRef.current) * (targetTtsAudio > audioTtsRef.current ? 0.4 : 0.15)

      // Target Scale & Glow based on voice reactivity
      let targetScale = 1.0
      let targetGlow = 0.2
      let targetEnergy = 0.15

      if (state === 'IDLE') {
        targetScale = 0.96 + Math.sin(elapsed * 1.5) * 0.02
        targetGlow = 0.1
        targetEnergy = 0.05
      } else if (state === 'LISTENING') {
        if (isUserSpeaking) {
          // User is actively speaking into mic
          targetScale = 1.08 + audioMicRef.current * 0.24
          targetGlow = 0.6 + audioMicRef.current * 0.8
          targetEnergy = 0.6 + audioMicRef.current * 0.8
        } else {
          // Quiet listening mode (soft breathing pulse)
          targetScale = 1.0 + Math.sin(elapsed * 2.2) * 0.03
          targetGlow = 0.25 + Math.sin(elapsed * 2.2) * 0.1
          targetEnergy = 0.2
        }
      } else if (state === 'PROCESSING') {
        targetScale = 1.02 + Math.sin(elapsed * 4.0) * 0.04
        targetGlow = 0.4
        targetEnergy = 0.5
      } else if (state === 'SPEAKING') {
        // AI Speaking: synchronized with actual TTS audio amplitude
        targetScale = 1.06 + audioTtsRef.current * 0.26
        targetGlow = 0.7 + audioTtsRef.current * 0.9
        targetEnergy = 0.7 + audioTtsRef.current * 0.8
      } else if (state === 'ERROR') {
        targetScale = 0.98 + Math.sin(elapsed * 5.0) * 0.02
        targetGlow = 0.35
        targetEnergy = 0.25
      }

      scaleRef.current += (targetScale - scaleRef.current) * 0.15
      glowRef.current += (targetGlow - glowRef.current) * 0.12
      energyRef.current += (targetEnergy - energyRef.current) * 0.15

      // Canvas dimensions
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const displayWidth = Math.round(canvas.clientWidth * dpr)
      const displayHeight = Math.round(canvas.clientHeight * dpr)

      if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth
        canvas.height = displayHeight
        gl.viewport(0, 0, displayWidth, displayHeight)
      }

      // Update Uniforms
      gl.uniform2f(uResolution, canvas.width, canvas.height)
      gl.uniform1f(uTime, elapsed)
      gl.uniform1f(uScale, scaleRef.current)
      gl.uniform1f(uAudioMic, audioMicRef.current)
      gl.uniform1f(uAudioTts, audioTtsRef.current)
      gl.uniform1f(uEnergy, energyRef.current)
      gl.uniform1f(uGlow, glowRef.current)
      gl.uniform1i(uState, stateInt)
      gl.uniform1f(uReducedMotion, reducedMotionRef.current ? 1.0 : 0.0)

      // Draw Quad
      gl.drawArrays(gl.TRIANGLES, 0, 6)

      animFrameIdRef.current = requestAnimationFrame(render)
    }

    animFrameIdRef.current = requestAnimationFrame(render)

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current)
        animFrameIdRef.current = null
      }
      if (gl) {
        gl.deleteBuffer(vbo)
        gl.deleteProgram(program)
        gl.deleteShader(vs)
        gl.deleteShader(fs)
      }
    }
  }, [state, micAnalyser, outputAnalyser])

  // Graceful CSS 3D fallback if WebGL fails
  if (hasWebGLError) {
    return <VoiceSphereCSSFallback state={state} size={size} className={className} />
  }

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{
        width: size,
        height: size,
        maxWidth: '100%',
        aspectRatio: '1/1',
      }}
    >
      {/* Subtle ambient back-glow */}
      <div
        className="absolute inset-0 rounded-full blur-3xl pointer-events-none transition-all duration-700 opacity-40"
        style={{
          background:
            state === 'ERROR'
              ? 'radial-gradient(circle, rgba(239,68,68,0.3) 0%, rgba(139,92,246,0.15) 60%, transparent 80%)'
              : state === 'SPEAKING'
              ? 'radial-gradient(circle, rgba(168,85,247,0.4) 0%, rgba(59,130,246,0.25) 50%, transparent 80%)'
              : 'radial-gradient(circle, rgba(56,189,248,0.35) 0%, rgba(147,51,234,0.2) 60%, transparent 80%)',
        }}
      />

      <canvas
        ref={canvasRef}
        className="relative z-10 w-full h-full rounded-full cursor-pointer select-none"
        style={{ touchAction: 'none' }}
      />
    </div>
  )
}

/**
 * Elegant CSS Fallback Sphere (activated if WebGL is unavailable)
 */
function VoiceSphereCSSFallback({
  state,
  size = 360,
  className = '',
}: {
  state: LiveState
  size?: number
  className?: string
}) {
  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: size, height: size, maxWidth: '100%', aspectRatio: '1/1' }}
    >
      {/* Outer atmosphere glow */}
      <div
        className={`absolute inset-4 rounded-full blur-2xl transition-all duration-700 animate-pulse ${
          state === 'ERROR'
            ? 'bg-rose-500/30'
            : state === 'SPEAKING'
            ? 'bg-purple-500/40'
            : 'bg-cyan-500/30'
        }`}
      />

      {/* Main 3D CSS Sphere */}
      <div
        className={`relative z-10 w-[78%] h-[78%] rounded-full shadow-2xl transition-all duration-500 overflow-hidden ${
          state === 'SPEAKING' ? 'scale-105' : 'scale-100'
        }`}
        style={{
          background:
            state === 'ERROR'
              ? 'radial-gradient(circle at 35% 30%, #f43f5e 0%, #a855f7 40%, #1e1b4b 90%)'
              : state === 'SPEAKING'
              ? 'radial-gradient(circle at 35% 30%, #38bdf8 0%, #c084fc 35%, #ec4899 65%, #1e1b4b 95%)'
              : 'radial-gradient(circle at 35% 30%, #06b6d4 0%, #3b82f6 40%, #8b5cf6 75%, #0f172a 100%)',
          boxShadow:
            state === 'SPEAKING'
              ? '0 0 50px rgba(192, 132, 252, 0.6), inset -10px -10px 40px rgba(0,0,0,0.8), inset 15px 15px 30px rgba(255,255,255,0.4)'
              : '0 0 40px rgba(56, 189, 248, 0.4), inset -10px -10px 40px rgba(0,0,0,0.8), inset 15px 15px 30px rgba(255,255,255,0.4)',
        }}
      >
        {/* Specular gloss highlight */}
        <div className="absolute top-[12%] left-[18%] w-[35%] h-[25%] rounded-full bg-gradient-to-br from-white/60 to-transparent blur-xs transform -rotate-25" />
      </div>
    </div>
  )
}
