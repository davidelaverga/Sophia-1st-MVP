"use client";

import { useEffect, useRef } from "react";
import type { PresenceState } from "../stores/presence-store";

interface WaveformProps {
  /** Audio stream to visualize */
  stream?: MediaStream;
  /** Current presence state */
  presenceState?: PresenceState;
}

export function Waveform({
  stream,
  presenceState = "resting",
}: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const analyserRef = useRef<AnalyserNode>();
  const dataArrayRef = useRef<Uint8Array>();
  const smoothedVolumeRef = useRef(0);

  const isListening = presenceState === "listening";

  useEffect(() => {
    if (!stream || !isListening) {
      // Clean up analyzer
      if (analyserRef.current) {
        analyserRef.current.disconnect();
        analyserRef.current = undefined;
      }
      smoothedVolumeRef.current = 0;
      return;
    }

    // Set up Web Audio API
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);

    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.85;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    analyserRef.current = analyser;
    dataArrayRef.current = dataArray;

    return () => {
      source.disconnect();
      analyser.disconnect();
      audioContext.close();
    };
  }, [stream, isListening]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    // Set canvas size accounting for device pixel ratio
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const baseRadius = Math.min(rect.width, rect.height) * 0.15;

    let animationTime = 0;

    const draw = () => {
      ctx.clearRect(0, 0, rect.width, rect.height);

      if (presenceState === "thinking") {
        // Thinking: orbiting particles (partículas orbitando)
        animationTime += 0.03;
        
        const particleCount = 3;
        for (let i = 0; i < particleCount; i++) {
          const angle = (animationTime + (i * Math.PI * 2 / particleCount)) % (Math.PI * 2);
          const orbitRadius = baseRadius * 1.8;
          const particleX = centerX + Math.cos(angle) * orbitRadius;
          const particleY = centerY + Math.sin(angle) * orbitRadius;
          const particleSize = baseRadius * 0.15;

          // Particle glow
          const particleGlow = ctx.createRadialGradient(particleX, particleY, 0, particleX, particleY, particleSize * 3);
          particleGlow.addColorStop(0, "rgba(139, 92, 246, 0.4)");
          particleGlow.addColorStop(0.5, "rgba(99, 102, 241, 0.2)");
          particleGlow.addColorStop(1, "rgba(99, 102, 241, 0)");
          ctx.fillStyle = particleGlow;
          ctx.beginPath();
          ctx.arc(particleX, particleY, particleSize * 3, 0, Math.PI * 2);
          ctx.fill();

          // Particle core
          ctx.fillStyle = "rgba(139, 92, 246, 0.6)";
          ctx.beginPath();
          ctx.arc(particleX, particleY, particleSize, 0, Math.PI * 2);
          ctx.fill();
        }

        // Central glow
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius * 1.2);
        gradient.addColorStop(0, "rgba(139, 92, 246, 0.2)");
        gradient.addColorStop(1, "rgba(99, 102, 241, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, baseRadius * 1.2, 0, Math.PI * 2);
        ctx.fill();

      } else if (presenceState === "reflecting") {
        // Reflecting: gentle spiral (espiral suave)
        animationTime += 0.02;
        
        const spiralTurns = 2;
        const spiralPoints = 60;
        
        ctx.beginPath();
        for (let i = 0; i < spiralPoints; i++) {
          const progress = i / spiralPoints;
          const angle = (animationTime + progress * spiralTurns * Math.PI * 2) % (Math.PI * 2);
          const radius = baseRadius * 0.3 + (progress * baseRadius * 1.5);
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        
        const spiralGradient = ctx.createLinearGradient(centerX - baseRadius * 2, centerY, centerX + baseRadius * 2, centerY);
        spiralGradient.addColorStop(0, "rgba(139, 92, 246, 0.1)");
        spiralGradient.addColorStop(0.5, "rgba(217, 179, 140, 0.3)"); // Golden tint
        spiralGradient.addColorStop(1, "rgba(139, 92, 246, 0.1)");
        ctx.strokeStyle = spiralGradient;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Central glow
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius);
        gradient.addColorStop(0, "rgba(217, 179, 140, 0.15)");
        gradient.addColorStop(1, "rgba(139, 92, 246, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, baseRadius, 0, Math.PI * 2);
        ctx.fill();

      } else if (presenceState === "speaking") {
        // Speaking: concentric ripples (ondas concéntricas)
        animationTime += 0.02;
        
        for (let i = 0; i < 3; i++) {
          const offset = i * 0.8;
          const ripplePhase = (animationTime + offset) % 2;
          const rippleRadius = baseRadius + (ripplePhase * baseRadius * 1.5);
          const rippleOpacity = Math.max(0, 0.3 - ripplePhase * 0.15);

          ctx.beginPath();
          ctx.arc(centerX, centerY, rippleRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(139, 92, 246, ${rippleOpacity})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Central glow
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius);
        gradient.addColorStop(0, "rgba(139, 92, 246, 0.15)");
        gradient.addColorStop(1, "rgba(139, 92, 246, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, baseRadius, 0, Math.PI * 2);
        ctx.fill();

      } else if (presenceState === "listening" && analyserRef.current && dataArrayRef.current) {
        // User speaking: pulsing circle (círculo pulsante)
        analyserRef.current.getByteFrequencyData(dataArrayRef.current);

        // Calculate average volume
        let sum = 0;
        for (let i = 0; i < dataArrayRef.current.length; i++) {
          sum += dataArrayRef.current[i];
        }
        const avgVolume = sum / dataArrayRef.current.length / 255;

        // Smooth the volume changes
        const targetVolume = avgVolume;
        smoothedVolumeRef.current += (targetVolume - smoothedVolumeRef.current) * 0.2;

        // Pulse radius based on volume
        const pulseAmount = smoothedVolumeRef.current * 0.6;
        const currentRadius = baseRadius * (1 + pulseAmount);

        // Outer glow (more visible when speaking)
        const outerGlow = ctx.createRadialGradient(
          centerX, centerY, currentRadius * 0.5,
          centerX, centerY, currentRadius * 1.8
        );
        outerGlow.addColorStop(0, `rgba(139, 92, 246, ${0.2 + pulseAmount * 0.3})`);
        outerGlow.addColorStop(1, "rgba(139, 92, 246, 0)");
        ctx.fillStyle = outerGlow;
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius * 1.8, 0, Math.PI * 2);
        ctx.fill();

        // Main circle
        const mainGradient = ctx.createRadialGradient(
          centerX, centerY, 0,
          centerX, centerY, currentRadius
        );
        mainGradient.addColorStop(0, `rgba(139, 92, 246, ${0.4 + pulseAmount * 0.3})`);
        mainGradient.addColorStop(1, `rgba(139, 92, 246, ${0.1 + pulseAmount * 0.2})`);
        ctx.fillStyle = mainGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius, 0, Math.PI * 2);
        ctx.fill();

        // Subtle ring
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(139, 92, 246, ${0.3 + pulseAmount * 0.4})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

      } else {
        // Resting state: very subtle dot with gentle pulse
        animationTime += 0.01;
        const pulseScale = 1 + Math.sin(animationTime) * 0.1;
        const pulseRadius = baseRadius * 0.5 * pulseScale;
        
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, pulseRadius);
        gradient.addColorStop(0, "rgba(139, 92, 246, 0.15)");
        gradient.addColorStop(1, "rgba(139, 92, 246, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
        ctx.fill();
      }

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [presenceState]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full"
      style={{ height: "80px" }}
      aria-hidden="true"
    />
  );
}


