import { useRef, useCallback } from 'react';

const SILENCE_TIMEOUT = 3;      // seconds of silence to auto-finish
const MIN_DURATION = 1.0;       // minimum seconds to send
const MAX_DURATION = 30;        // max recording seconds
const SAMPLE_RATE = 16000;

/**
 * Push-to-talk recorder.  Call startRecording() to begin,
 * stopRecording() to finish manually.  Also auto-finishes after
 * SILENCE_TIMEOUT seconds of quiet.
 */
export default function useRecorder() {
  const ctxRef = useRef(null);
  const streamRef = useRef(null);
  const scriptRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceTimerRef = useRef(null);
  const maxTimerRef = useRef(null);
  const startTimeRef = useRef(0);
  const speakingRef = useRef(false);
  const onFinishRef = useRef(null);   // callback(WAV bytes)
  const onSilenceTickRef = useRef(null); // callback(remaining seconds)
  const silenceStartRef = useRef(0);

  const isRecording = useCallback(() => {
    return ctxRef.current !== null;
  }, []);

  const startRecording = useCallback(async (onFinish, onSilenceTick) => {
    if (ctxRef.current) return; // already recording
    onFinishRef.current = onFinish;
    onSilenceTickRef.current = onSilenceTick;

    chunksRef.current = [];
    speakingRef.current = false;
    silenceStartRef.current = 0;

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    streamRef.current = stream;

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    ctxRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    const buffer = new Float32Array(analyser.fftSize);
    const scriptNode = ctx.createScriptProcessor(4096, 1, 1);
    scriptRef.current = scriptNode;

    startTimeRef.current = Date.now();

    scriptNode.onaudioprocess = (e) => {
      if (ctxRef.current !== ctx) return;

      analyser.getFloatTimeDomainData(buffer);
      const rms = Math.sqrt(buffer.reduce((sum, v) => sum + v * v, 0) / buffer.length);
      const db = 20 * Math.log10(rms + 1e-10);

      chunksRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));

      // Voice detection: > -45 dBFS = speaking
      const isVoice = db > -45;

      if (isVoice) {
        speakingRef.current = true;
        silenceStartRef.current = 0;
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        if (onSilenceTickRef.current) onSilenceTickRef.current(null);
      } else if (speakingRef.current) {
        // Count silence
        if (silenceStartRef.current === 0) {
          silenceStartRef.current = Date.now();
        }
        const elapsed = (Date.now() - silenceStartRef.current) / 1000;
        const remaining = Math.max(0, SILENCE_TIMEOUT - elapsed);
        if (onSilenceTickRef.current) onSilenceTickRef.current(Math.ceil(remaining));

        if (remaining <= 0 && !silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            _finish();
          }, 10); // tiny delay, already timed out
        }

        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            _finish();
          }, remaining * 1000);
        }
      }
    };

    source.connect(scriptNode);
    scriptNode.connect(ctx.destination);

    // Max recording safety
    maxTimerRef.current = setTimeout(() => {
      _finish();
    }, MAX_DURATION * 1000);
  }, []);

  const stopRecording = useCallback(() => {
    _finish();
  }, []);

  const cancelRecording = useCallback(() => {
    _cleanup();
    if (onFinishRef.current) onFinishRef.current(null); // null = cancelled
  }, []);

  function _finish() {
    const duration = (Date.now() - startTimeRef.current) / 1000;
    let wav = null;

    if (duration >= MIN_DURATION && chunksRef.current.length > 0) {
      wav = _buildWav(chunksRef.current, SAMPLE_RATE);
    }
    // Otherwise duration too short → wav stays null

    _cleanup();

    if (onFinishRef.current) {
      onFinishRef.current(wav, duration);
    }
  }

  function _cleanup() {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    if (maxTimerRef.current) { clearTimeout(maxTimerRef.current); maxTimerRef.current = null; }
    if (scriptRef.current) { scriptRef.current.disconnect(); scriptRef.current = null; }
    ctxRef.current?.close();
    ctxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    speakingRef.current = false;
    chunksRef.current = [];
  }

  return { startRecording, stopRecording, cancelRecording, isRecording };
}

// ── WAV helpers ──────────────────────────────────────────

function _buildWav(chunks, sampleRate) {
  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
  const buf = new ArrayBuffer(44 + totalLength * 2);
  const v = new DataView(buf);
  _writeWavHeader(v, totalLength, sampleRate);
  let off = 44;
  for (const c of chunks) {
    for (let i = 0; i < c.length; i++) {
      const s = Math.max(-1, Math.min(1, c[i]));
      v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      off += 2;
    }
  }
  return buf;
}

function _writeWavHeader(v, len, rate) {
  v.setUint32(0, 0x52494646, false);
  v.setUint32(4, 36 + len * 2, true);
  v.setUint32(8, 0x57415645, false);
  v.setUint32(12, 0x666D7420, false);
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  v.setUint32(36, 0x64617461, false);
  v.setUint32(40, len * 2, true);
}

function _arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// export for use in components that need to send
export { _arrayBufferToBase64 };
