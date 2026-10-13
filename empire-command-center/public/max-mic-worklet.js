// MAX Live Voice — mic capture AudioWorklet (2026-09-30).
// Converts the context's native-rate Float32 mic input to 24 kHz mono PCM16
// little-endian and posts ~40 ms chunks (ArrayBuffer) to the main thread,
// together with the chunk RMS (used for the client-side barge-in gate).
class MaxMicProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetRate = opts.targetRate || 24000;
    this.ratio = sampleRate / this.targetRate; // input samples per output sample
    this.chunkSamples = Math.round(this.targetRate * 0.04); // 40 ms
    this.out = new Int16Array(this.chunkSamples);
    this.outIdx = 0;
    this.pos = 0; // fractional read position into the carried input
    this.carry = new Float32Array(0);
    this.sumSq = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;
    const ch = input[0];
    // prepend carry-over samples
    const buf = new Float32Array(this.carry.length + ch.length);
    buf.set(this.carry, 0);
    buf.set(ch, this.carry.length);
    let pos = this.pos;
    while (pos + 1 < buf.length) {
      const i = Math.floor(pos);
      const frac = pos - i;
      let s = buf[i] + (buf[i + 1] - buf[i]) * frac;
      if (s > 1) s = 1; else if (s < -1) s = -1;
      this.sumSq += s * s;
      this.out[this.outIdx++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.outIdx === this.chunkSamples) {
        const rms = Math.sqrt(this.sumSq / this.chunkSamples);
        const copy = this.out.slice(0);
        this.port.postMessage({ pcm: copy.buffer, rms }, [copy.buffer]);
        this.outIdx = 0;
        this.sumSq = 0;
      }
      pos += this.ratio;
    }
    const keepFrom = Math.floor(pos);
    this.carry = buf.slice(keepFrom);
    this.pos = pos - keepFrom;
    return true;
  }
}

registerProcessor('max-mic-processor', MaxMicProcessor);
