import React, { useEffect, useRef } from 'react'

export type MeshPreset = 'noir' | 'mint' | 'plum' | 'neon'

export const MESH_PALETTES: Record<MeshPreset, { name: string; stops: [number, number, number][]; hexStops: string[] }> = {
  noir: {
    name: 'Noir',
    stops: [
      [8 / 255, 9 / 255, 11 / 255],
      [47 / 255, 50 / 255, 55 / 255],
      [139 / 255, 144 / 255, 153 / 255],
      [243 / 255, 244 / 255, 246 / 255],
    ],
    hexStops: ['#08090b', '#2f3237', '#8b9099', '#f3f4f6'],
  },
  mint: {
    name: 'Mint',
    stops: [
      [247 / 255, 244 / 255, 232 / 255],
      [220 / 255, 236 / 255, 217 / 255],
      [156 / 255, 207 / 255, 178 / 255],
      [92 / 255, 156 / 255, 133 / 255],
    ],
    hexStops: ['#f7f4e8', '#dcecd9', '#9ccfb2', '#5c9c85'],
  },
  plum: {
    name: 'Plum',
    stops: [
      [24 / 255, 8 / 255, 20 / 255],
      [72 / 255, 16 / 255, 62 / 255],
      [149 / 255, 39 / 255, 95 / 255],
      [224 / 255, 122 / 255, 156 / 255],
    ],
    hexStops: ['#180814', '#48103e', '#95275f', '#e07a9c'],
  },
  neon: {
    name: 'Neon',
    stops: [
      [4 / 255, 6 / 255, 10 / 255],
      [125 / 255, 255 / 255, 77 / 255],
      [255 / 255, 47 / 255, 146 / 255],
      [41 / 255, 230 / 255, 255 / 255],
    ],
    hexStops: ['#04060a', '#7dff4d', '#ff2f92', '#29e6ff'],
  },
}

const VS_SOURCE = `
attribute vec2 a_pos;
varying vec2 v_pos;
void main() {
  v_pos = a_pos;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}
`

const FS_SOURCE = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
  precision highp float;
#else
  precision mediump float;
#endif

varying vec2 v_pos;

uniform vec2 u_resolution;
uniform float u_t;
uniform vec2 u_pointer;
uniform float u_dither_strength;

uniform vec3 u_c0;
uniform vec3 u_c1;
uniform vec3 u_c2;
uniform vec3 u_c3;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

float fbm(vec2 p) {
  float v = 0.0;
  float amp = 0.5;
  for (int i = 0; i < 5; i++) {
    v += amp * noise(p);
    p = p * 2.02;
    amp *= 0.5;
  }
  return v;
}

float bayer4(vec2 coord) {
  vec2 b = floor(mod(coord, 4.0));
  float d = 0.0;
  if (b.y < 2.0) {
    if (b.y < 1.0) {
      d = (b.x < 2.0) ? ((b.x < 1.0) ? 0.0 : 8.0) : ((b.x < 3.0) ? 2.0 : 10.0);
    } else {
      d = (b.x < 2.0) ? ((b.x < 1.0) ? 12.0 : 4.0) : ((b.x < 3.0) ? 14.0 : 6.0);
    }
  } else {
    if (b.y < 3.0) {
      d = (b.x < 2.0) ? ((b.x < 1.0) ? 3.0 : 11.0) : ((b.x < 3.0) ? 1.0 : 9.0);
    } else {
      d = (b.x < 2.0) ? ((b.x < 1.0) ? 15.0 : 7.0) : ((b.x < 3.0) ? 13.0 : 5.0);
    }
  }
  return (d / 16.0) - 0.5;
}

void main() {
  float aspect = u_resolution.x / u_resolution.y;
  vec2 p = v_pos * vec2(aspect, 1.0) * 1.35;
  p += u_pointer * 0.22;

  // Seamless closed-circle orbit: loops every 2*PI
  vec2 orb = vec2(cos(u_t), sin(u_t)) * 0.55;

  // Double domain-warped FBM field
  vec2 q = vec2(
    fbm(p + orb),
    fbm(p + orb.yx + 3.1)
  );

  vec2 r = vec2(
    fbm(p + 2.0 * q + orb * 1.3 + 1.7),
    fbm(p + 2.0 * q - orb + 9.2)
  );

  float f = fbm(p + 1.8 * r);
  float g = clamp(f, 0.0, 1.0);
  float s = length(q);

  // Soft overlapping smoothstep windows
  vec3 col = mix(u_c0, u_c1, smoothstep(0.0, 0.45, g));
  col = mix(col, u_c2, smoothstep(0.35, 0.78, g));
  col = mix(col, u_c3, smoothstep(0.62, 1.0, g) * (0.55 + 0.45 * s));

  // 4x4 Bayer dither (centered -0.5..0.5 scaled to 0.016)
  col += bayer4(gl_FragCoord.xy) * u_dither_strength;

  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
`

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

function lerpVec3(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]
}

interface MeshGradientCanvasProps {
  preset?: MeshPreset
  dither?: boolean
  className?: string
  style?: React.CSSProperties
}

export function MeshGradientCanvas({
  preset = 'plum',
  dither = true,
  className = '',
  style = {},
}: MeshGradientCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [webGlSupported, setWebGlSupported] = React.useState(true)
  const presetRef = useRef(preset)
  presetRef.current = preset

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const gl =
      canvas.getContext('webgl', { alpha: false, antialias: false, depth: false }) ||
      (canvas.getContext('experimental-webgl', { alpha: false, antialias: false, depth: false }) as WebGLRenderingContext | null)

    if (!gl) {
      setWebGlSupported(false)
      return
    }

    const compileShader = (type: number, source: string) => {
      const shader = gl.createShader(type)
      if (!shader) return null
      gl.shaderSource(shader, source)
      gl.compileShader(shader)
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error('Shader compilation error:', gl.getShaderInfoLog(shader))
        gl.deleteShader(shader)
        return null
      }
      return shader
    }

    const vs = compileShader(gl.VERTEX_SHADER, VS_SOURCE)
    const fs = compileShader(gl.FRAGMENT_SHADER, FS_SOURCE)
    if (!vs || !fs) {
      setWebGlSupported(false)
      return
    }

    const program = gl.createProgram()
    if (!program) {
      setWebGlSupported(false)
      return
    }
    gl.attachShader(program, vs)
    gl.attachShader(program, fs)
    gl.linkProgram(program)

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program))
      setWebGlSupported(false)
      return
    }
    gl.useProgram(program)

    // Full-screen single triangle: (-1,-1, 3,-1, -1,3)
    const vertices = new Float32Array([-1.0, -1.0, 3.0, -1.0, -1.0, 3.0])
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW)

    const aPosLoc = gl.getAttribLocation(program, 'a_pos')
    gl.enableVertexAttribArray(aPosLoc)
    gl.vertexAttribPointer(aPosLoc, 2, gl.FLOAT, false, 0, 0)

    const uResLoc = gl.getUniformLocation(program, 'u_resolution')
    const uTimeLoc = gl.getUniformLocation(program, 'u_t')
    const uPointerLoc = gl.getUniformLocation(program, 'u_pointer')
    const uDitherLoc = gl.getUniformLocation(program, 'u_dither_strength')
    const uC0Loc = gl.getUniformLocation(program, 'u_c0')
    const uC1Loc = gl.getUniformLocation(program, 'u_c1')
    const uC2Loc = gl.getUniformLocation(program, 'u_c2')
    const uC3Loc = gl.getUniformLocation(program, 'u_c3')

    // Initial colors
    const initPalette = MESH_PALETTES[presetRef.current] || MESH_PALETTES.plum
    let activeColors: [number, number, number][] = initPalette.stops.map(s => [...s]) as [number, number, number][]

    // Resize handler capping devicePixelRatio at 1.5
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
      const w = Math.round(window.innerWidth * dpr)
      const h = Math.round(window.innerHeight * dpr)
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
        gl.viewport(0, 0, w, h)
        gl.uniform2f(uResLoc, w, h)
      }
    }
    resize()
    window.addEventListener('resize', resize, { passive: true })

    // Eased Pointer coordinates
    let targetX = 0, targetY = 0
    let currentX = 0, currentY = 0

    const handlePointerMove = (e: PointerEvent) => {
      targetX = (e.clientX / window.innerWidth) * 2.0 - 1.0
      targetY = 1.0 - (e.clientY / window.innerHeight) * 2.0
    }
    window.addEventListener('pointermove', handlePointerMove, { passive: true })

    // Animation render loop
    let animId: number
    const startTime = performance.now()
    const LOOP_DURATION_S = 18.0 // 18s seamless loop

    const render = (now: number) => {
      const elapsed = (now - startTime) / 1000.0
      const ut = (elapsed * (2.0 * Math.PI) / LOOP_DURATION_S) % (2.0 * Math.PI)

      currentX += (targetX - currentX) * 0.05
      currentY += (targetY - currentY) * 0.05

      const targetPalette = MESH_PALETTES[presetRef.current] || MESH_PALETTES.plum
      for (let i = 0; i < 4; i++) {
        activeColors[i] = lerpVec3(activeColors[i], targetPalette.stops[i], 0.06)
      }

      gl.uniform1f(uTimeLoc, ut)
      gl.uniform2f(uPointerLoc, currentX, currentY)
      gl.uniform1f(uDitherLoc, dither ? 0.016 : 0.0)

      gl.uniform3fv(uC0Loc, activeColors[0])
      gl.uniform3fv(uC1Loc, activeColors[1])
      gl.uniform3fv(uC2Loc, activeColors[2])
      gl.uniform3fv(uC3Loc, activeColors[3])

      gl.drawArrays(gl.TRIANGLES, 0, 3)

      animId = requestAnimationFrame(render)
    }
    animId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', handlePointerMove)
      gl.deleteBuffer(buffer)
      gl.deleteProgram(program)
      gl.deleteShader(vs)
      gl.deleteShader(fs)
    }
  }, [dither])

  if (!webGlSupported) {
    const p = MESH_PALETTES[preset] || MESH_PALETTES.plum
    return (
      <div
        className={`absolute inset-0 pointer-events-none ${className}`}
        style={{
          background: `linear-gradient(135deg, ${p.hexStops[0]} 0%, ${p.hexStops[1]} 35%, ${p.hexStops[2]} 70%, ${p.hexStops[3]} 100%)`,
          ...style,
        }}
      />
    )
  }

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full pointer-events-none block ${className}`}
      style={style}
    />
  )
}
