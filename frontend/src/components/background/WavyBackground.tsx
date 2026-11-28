import { useEffect, useRef } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function WavyBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
    });

    if (!gl) {
      console.warn("WebGL2 is not supported.");
      return;
    }

    const vertexSource = `#version 300 es
      in vec2 aPosition;

      void main() {
        gl_Position = vec4(aPosition, 0.0, 1.0);
      }
    `;

    const fragmentSource = `#version 300 es
      precision highp float;

      uniform vec2 uResolution;
      uniform float uTime;
      uniform float uDarkMode;

      out vec4 outColor;

      float hash(vec2 p) {
        return fract(
          sin(dot(p, vec2(127.1, 311.7))) * 43758.5453
        );
      }

      float noise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);

        vec2 u = f * f * (3.0 - 2.0 * f);

        return mix(
          mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
          mix(hash(i + vec2(0.0, 1.0)),
              hash(i + vec2(1.0, 1.0)), u.x),
          u.y
        );
      }

      float fbm(vec2 p) {
        float value = 0.0;
        float amplitude = 0.5;

        for (int i = 0; i < 5; i++) {
          value += amplitude * noise(p);
          p *= 2.0;
          amplitude *= 0.5;
        }

        return value;
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / uResolution.xy;
        vec2 p = uv * 2.0 - 1.0;

        p.x *= uResolution.x / uResolution.y;

        float t = uTime * 0.12;

        // Flowing domain warp
        vec2 q = vec2(
          fbm(p * 1.3 + vec2(t, 0.0)),
          fbm(p * 1.3 + vec2(0.0, -t))
        );

        vec2 r = vec2(
          fbm(p * 1.8 + q * 1.5 + vec2(t * 0.4)),
          fbm(p * 1.8 + q * 1.5 - vec2(t * 0.3))
        );

        float wave = fbm(p * 1.5 + r * 2.0);

        // Sage Garden palette
        vec3 ivory = vec3(0.985, 0.982, 0.965);
        vec3 mint = vec3(0.855, 0.925, 0.850);
        vec3 sage = vec3(0.650, 0.810, 0.680);
        vec3 softGreen = vec3(0.780, 0.875, 0.755);

        vec3 color = mix(
          ivory,
          mint,
          smoothstep(0.20, 0.75, wave)
        );

        color = mix(
          color,
          sage,
          smoothstep(0.50, 0.90, wave) * 0.65
        );

        color = mix(
          color,
          softGreen,
          smoothstep(0.35, 0.75, r.x) * 0.25
        );

        // Dark Sage Garden palette
        vec3 darkBase = vec3(0.075, 0.105, 0.085);
        vec3 darkForest = vec3(0.115, 0.185, 0.135);
        vec3 darkSage = vec3(0.225, 0.375, 0.265);
        vec3 darkMist = vec3(0.165, 0.265, 0.195);

        vec3 darkColor = mix(
          darkBase,
          darkForest,
          smoothstep(0.20, 0.75, wave)
        );

        darkColor = mix(
          darkColor,
          darkSage,
          smoothstep(0.50, 0.90, wave) * 0.55
        );

        darkColor = mix(
          darkColor,
          darkMist,
          smoothstep(0.35, 0.75, r.x) * 0.30
        );

        // Switch between light and dark palettes
        vec3 finalColor = mix(color, darkColor, uDarkMode);

        outColor = vec4(finalColor, 1.0);
      }
    `;

    function compileShader(type: number, source: string) {
      const shader = gl!.createShader(type);
      if (!shader) return null;

      gl!.shaderSource(shader, source);
      gl!.compileShader(shader);

      if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
        console.error(gl!.getShaderInfoLog(shader));
        gl!.deleteShader(shader);
        return null;
      }

      return shader;
    }

    const vertexShader = compileShader(gl.VERTEX_SHADER, vertexSource);
    const fragmentShader = compileShader(gl.FRAGMENT_SHADER, fragmentSource);

    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(program));
      return;
    }

    const vertices = new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1,
    ]);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

    const position = gl.getAttribLocation(program, "aPosition");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    gl.useProgram(program);

    const resolution = gl.getUniformLocation(program, "uResolution");
    const time = gl.getUniformLocation(program, "uTime");
    const darkMode = gl.getUniformLocation(program, "uDarkMode");

    let frameId = 0;
    const start = performance.now();

    function render() {
      if (!canvas || !gl) return;

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;

      if (width === 0 || height === 0) return;

      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const pixelWidth = Math.round(width * dpr);
      const pixelHeight = Math.round(height * dpr);

      if (
        canvas.width !== pixelWidth ||
        canvas.height !== pixelHeight
      ) {
        canvas.width = pixelWidth;
        canvas.height = pixelHeight;
      }

      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(resolution, canvas.width, canvas.height);
      gl.uniform1f(time, (performance.now() - start) / 1000);
      gl.uniform1f(darkMode, resolvedTheme === "dark" ? 1.0 : 0.0);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
      frameId = requestAnimationFrame(render);
    }

    render();

    return () => {
      cancelAnimationFrame(frameId);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
    };
  }, [resolvedTheme]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 -z-10 h-full w-full"
    />
  );
}
