class PCMWorkletProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs?.[0]
    if (!input || input.length === 0) return true
    const channelData = input[0]
    if (channelData?.length) {
      // Copy channel data before posting since the buffer is reused by the audio thread
      this.port.postMessage(new Float32Array(channelData))
    }
    return true
  }
}

registerProcessor("pcm-worklet", PCMWorkletProcessor)
