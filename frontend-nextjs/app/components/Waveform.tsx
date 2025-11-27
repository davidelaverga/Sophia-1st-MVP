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
        // Thinking: Gentle breathing presence - calm, alive, ready to help
        // (Presencia suave que respira - calma, viva, lista para ayudar)
        animationTime += 0.015; // Slower, more gentle movement
        
        // Gentle breathing cycle (ciclo de respiración suave)
        const breathingPhase = Math.sin(animationTime * 0.5); // Slower breathing
        const breathingIntensity = (breathingPhase + 1) / 2; // 0 to 1
        
        // Layer 1: Soft outer glow that breathes (glow exterior suave que respira)
        const outerGlowRadius = baseRadius * (1.3 + breathingIntensity * 0.4);
        const outerGradient = ctx.createRadialGradient(
          centerX, centerY, baseRadius * 0.6,
          centerX, centerY, outerGlowRadius
        );
        outerGradient.addColorStop(0, `rgba(139, 92, 246, ${0.12 + breathingIntensity * 0.08})`);
        outerGradient.addColorStop(0.6, `rgba(99, 102, 241, ${0.08 + breathingIntensity * 0.05})`);
        outerGradient.addColorStop(1, "rgba(99, 102, 241, 0)");
        ctx.fillStyle = outerGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, outerGlowRadius, 0, Math.PI * 2);
        ctx.fill();
        
        // Layer 2: Gentle pulsing ring (anillo pulsante suave)
        const ringPulse = breathingIntensity;
        const ringRadius = baseRadius * (0.7 + ringPulse * 0.3);
        ctx.beginPath();
        ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(139, 92, 246, ${0.2 + ringPulse * 0.15})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        // Layer 3: Central core - gentle pulse (núcleo central - pulso suave)
        const corePulse = (Math.sin(animationTime * 0.7) + 1) / 2; // Even slower
        const coreRadius = baseRadius * (0.35 + corePulse * 0.15);
        const coreGradient = ctx.createRadialGradient(
          centerX, centerY, 0,
          centerX, centerY, coreRadius
        );
        coreGradient.addColorStop(0, `rgba(139, 92, 246, ${0.35 + corePulse * 0.2})`);
        coreGradient.addColorStop(0.7, `rgba(99, 102, 241, ${0.18 + corePulse * 0.12})`);
        coreGradient.addColorStop(1, "rgba(99, 102, 241, 0)");
        ctx.fillStyle = coreGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, coreRadius, 0, Math.PI * 2);
        ctx.fill();
        
        // Layer 4: Subtle orbiting particles - gentle presence (partículas orbitando sutiles)
        const particleCount = 4; // Fewer particles, more gentle
        for (let i = 0; i < particleCount; i++) {
          const particleAngle = (animationTime * 0.3 + (i / particleCount) * Math.PI * 2); // Slower orbit
          const particleOrbitRadius = baseRadius * (1.1 + breathingIntensity * 0.2);
          const particleX = centerX + Math.cos(particleAngle) * particleOrbitRadius;
          const particleY = centerY + Math.sin(particleAngle) * particleOrbitRadius;
          const particlePulse = (Math.sin(animationTime * 0.8 + i) + 1) / 2;
          const particleSize = baseRadius * (0.06 + particlePulse * 0.04); // Smaller, gentler
          
          // Very subtle particle glow
          const particleGlow = ctx.createRadialGradient(particleX, particleY, 0, particleX, particleY, particleSize * 3);
          particleGlow.addColorStop(0, `rgba(139, 92, 246, ${0.25 + particlePulse * 0.15})`);
          particleGlow.addColorStop(0.6, `rgba(99, 102, 241, ${0.12 + particlePulse * 0.08})`);
          particleGlow.addColorStop(1, "rgba(99, 102, 241, 0)");
          ctx.fillStyle = particleGlow;
          ctx.beginPath();
          ctx.arc(particleX, particleY, particleSize * 3, 0, Math.PI * 2);
          ctx.fill();
          
          // Gentle particle core
          ctx.fillStyle = `rgba(139, 92, 246, ${0.4 + particlePulse * 0.2})`;
          ctx.beginPath();
          ctx.arc(particleX, particleY, particleSize, 0, Math.PI * 2);
          ctx.fill();
        }

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
        // User speaking: frequency bars + pulsing circle (barras de frecuencia + círculo pulsante)
        analyserRef.current.getByteFrequencyData(dataArrayRef.current);

        // Calculate average volume and frequency distribution
        let sum = 0;
        let maxFreq = 0;
        for (let i = 0; i < dataArrayRef.current.length; i++) {
          const value = dataArrayRef.current[i];
          sum += value;
          if (value > maxFreq) maxFreq = value;
        }
        const avgVolume = sum / dataArrayRef.current.length / 255;
        const maxVolume = maxFreq / 255;

        // Smooth the volume changes
        const targetVolume = avgVolume;
        smoothedVolumeRef.current += (targetVolume - smoothedVolumeRef.current) * 0.2;

        // Pulse radius based on volume
        const pulseAmount = smoothedVolumeRef.current * 0.8;
        const currentRadius = baseRadius * (1 + pulseAmount * 0.5);

        // Draw frequency bars around the circle (visual feedback de frecuencia)
        const barCount = 32; // Number of frequency bars
        const barWidth = (Math.PI * 2) / barCount;
        const innerRadius = baseRadius * 0.6;
        const maxBarHeight = baseRadius * 0.8;

        for (let i = 0; i < barCount; i++) {
          // Map bar index to frequency data (use different frequency ranges)
          const freqIndex = Math.floor((i / barCount) * dataArrayRef.current.length);
          const freqValue = dataArrayRef.current[freqIndex] / 255;
          
          // Only show bars with significant activity
          if (freqValue > 0.1) {
            const angle = (i * barWidth) - Math.PI / 2; // Start from top
            const barHeight = freqValue * maxBarHeight;
            
            // Calculate bar positions
            const x1 = centerX + Math.cos(angle) * innerRadius;
            const y1 = centerY + Math.sin(angle) * innerRadius;
            const x2 = centerX + Math.cos(angle) * (innerRadius + barHeight);
            const y2 = centerY + Math.sin(angle) * (innerRadius + barHeight);
            
            // Color based on frequency intensity (more vibrant when louder)
            const intensity = Math.min(1, freqValue * 2);
            const hue = 250 + (freqValue * 20); // Purple to blue range
            ctx.strokeStyle = `hsla(${hue}, 70%, ${50 + intensity * 30}%, ${0.4 + intensity * 0.6})`;
            ctx.lineWidth = 2 + intensity * 2;
            ctx.lineCap = "round";
            
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
          }
        }

        // Outer glow (more visible when speaking)
        const outerGlow = ctx.createRadialGradient(
          centerX, centerY, currentRadius * 0.5,
          centerX, centerY, currentRadius * 2.2
        );
        outerGlow.addColorStop(0, `rgba(139, 92, 246, ${0.3 + pulseAmount * 0.4})`);
        outerGlow.addColorStop(0.5, `rgba(99, 102, 241, ${0.2 + pulseAmount * 0.3})`);
        outerGlow.addColorStop(1, "rgba(139, 92, 246, 0)");
        ctx.fillStyle = outerGlow;
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius * 2.2, 0, Math.PI * 2);
        ctx.fill();

        // Main circle with more vibrant colors when speaking
        const mainGradient = ctx.createRadialGradient(
          centerX, centerY, 0,
          centerX, centerY, currentRadius
        );
        mainGradient.addColorStop(0, `rgba(139, 92, 246, ${0.5 + pulseAmount * 0.4})`);
        mainGradient.addColorStop(0.7, `rgba(99, 102, 241, ${0.3 + pulseAmount * 0.3})`);
        mainGradient.addColorStop(1, `rgba(139, 92, 246, ${0.15 + pulseAmount * 0.25})`);
        ctx.fillStyle = mainGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius, 0, Math.PI * 2);
        ctx.fill();

        // Animated ring that pulses with voice
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(139, 92, 246, ${0.4 + pulseAmount * 0.5})`;
        ctx.lineWidth = 2 + pulseAmount * 2;
        ctx.stroke();
        
        // Inner core that pulses more intensely
        const coreRadius = baseRadius * 0.3 * (1 + pulseAmount * 0.8);
        const coreGradient = ctx.createRadialGradient(
          centerX, centerY, 0,
          centerX, centerY, coreRadius
        );
        coreGradient.addColorStop(0, `rgba(255, 255, 255, ${0.3 + pulseAmount * 0.4})`);
        coreGradient.addColorStop(1, `rgba(139, 92, 246, ${0.2 + pulseAmount * 0.3})`);
        ctx.fillStyle = coreGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, coreRadius, 0, Math.PI * 2);
        ctx.fill();

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


