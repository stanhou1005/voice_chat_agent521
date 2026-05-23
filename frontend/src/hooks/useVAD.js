import { useEffect, useRef, useContext } from 'react';
import { AppContext } from '../context/AppContext';

const SILENCE_TIMEOUT = 2.5;     // seconds of silence to end speech
const MIN_SPEECH_DURATION = 1.0; // seconds minimum speech (filter out breaths/coughs)
const MAX_RECORDING = 15;        // seconds max recording (safety net)
const SAMPLE_RATE = 16000;
const INITIAL_THRESHOLD = -35;   // start high, calibrate down
const NOISE_MARGIN = 20;         // dB above noise floor to trigger

export default function useVAD(enabled) {
  const { dispatch } = useContext(AppContext);
  const ctxRef = useRef(null);
  const streamRef = useRef(null);
  const scriptRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceTimerRef = useRef(null);
  const maxTimerRef = useRef(null);
  const speechStartRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const sentRef = useRef(false);
  const thresholdRef = useRef(INITIAL_THRESHOLD);
  const noiseSumRef = useRef(0);
  const noiseCountRef = useRef(0);
  const calibratedRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      console.log('[VAD] Disabled');
      _cleanup();
      return;
    }

    console.log('[VAD] Starting mic...');
    sentRef.current = false;
    thresholdRef.current = INITIAL_THRESHOLD;
    noiseSumRef.current = 0;
    noiseCountRef.current = 0;
    calibratedRef.current = false;

    _startMic().catch((err) => {
      console.error('[VAD] Mic init failed:', err);
      dispatch({ type: 'ERROR', message: '麦克风权限未授予或设备不可用' });
    });

    return () => {
      _cleanup();
    };
  }, [enabled]);

  async function _startMic() {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    streamRef.current = stream;
    console.log('[VAD] Mic stream acquired');

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    ctxRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    const buffer = new Float32Array(analyser.fftSize);
    const scriptNode = ctx.createScriptProcessor(4096, 1, 1);
    scriptRef.current = scriptNode;

    let callbackCount = 0;

    scriptNode.onaudioprocess = (e) => {
      if (!isSpeakingRef.current && sentRef.current) return;
      if (ctxRef.current !== ctx) return;

      analyser.getFloatTimeDomainData(buffer);
      const rms = Math.sqrt(buffer.reduce((sum, v) => sum + v * v, 0) / buffer.length);
      const db = 20 * Math.log10(rms + 1e-10);

      callbackCount++;

      // Calibrate noise floor from first 2 seconds of quiet
      if (!calibratedRef.current) {
        if (!isSpeakingRef.current) {
          // Not speaking → this is noise
          noiseSumRef.current += db;
          noiseCountRef.current++;
          if (callbackCount >= 40) {
            // ~2 seconds of data, set threshold 15 dB above noise
            const noiseFloor = noiseSumRef.current / Math.max(noiseCountRef.current, 1);
            thresholdRef.current = Math.min(-25, Math.max(-45, noiseFloor + NOISE_MARGIN));
            calibratedRef.current = true;
            console.log(`[VAD] Calibrated: noise=${noiseFloor.toFixed(1)} dB, threshold=${thresholdRef.current.toFixed(1)} dB`);
          }
        } else {
          // User started talking during calibration — pause calibration
          // Will resume when they stop
        }
      }

      // Log every ~1s
      if (callbackCount % 20 === 0) {
        console.log(`[VAD] dB:${db.toFixed(1)} thr:${thresholdRef.current.toFixed(0)} speaking:${isSpeakingRef.current} calibrated:${calibratedRef.current}`);
      }

      const isVoice = db > thresholdRef.current;

      // Collect audio chunk regardless
      chunksRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));

      if (isVoice) {
        if (!isSpeakingRef.current) {
          isSpeakingRef.current = true;
          sentRef.current = false;
          speechStartRef.current = Date.now();
          console.log(`[VAD] >>> SPEECH START (dB:${db.toFixed(1)} > thr:${thresholdRef.current.toFixed(0)})`);
          dispatch({ type: 'SET_STATUS', status: 'listening' });

          // Safety net: max recording
          if (maxTimerRef.current) clearTimeout(maxTimerRef.current);
          maxTimerRef.current = setTimeout(() => {
            console.log('[VAD] MAX RECORDING reached, auto-finishing');
            _finishSpeech();
          }, MAX_RECORDING * 1000);
        }
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
      } else if (isSpeakingRef.current) {
        if (!silenceTimerRef.current) {
          console.log(`[VAD] Silence detected, starting ${SILENCE_TIMEOUT}s countdown...`);
          silenceTimerRef.current = setTimeout(() => {
            console.log(`[VAD] <<< SILENCE TIMEOUT, ending speech`);
            _finishSpeech();
          }, SILENCE_TIMEOUT * 1000);
        }
      }
    };

    source.connect(scriptNode);
    scriptNode.connect(ctx.destination);
    console.log('[VAD] Audio processing started');
  }

  function _finishSpeech() {
    const duration = (Date.now() - (speechStartRef.current || Date.now())) / 1000;
    isSpeakingRef.current = false;

    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    if (maxTimerRef.current) { clearTimeout(maxTimerRef.current); maxTimerRef.current = null; }

    console.log(`[VAD] END SPEECH duration:${duration.toFixed(1)}s chunks:${chunksRef.current.length}`);

    if (duration < MIN_SPEECH_DURATION) {
      console.log('[VAD] Too short (< 0.5s), discarding');
      chunksRef.current = [];
      dispatch({ type: 'SET_STATUS', status: 'idle' });
      return;
    }

    if (sentRef.current) {
      console.log('[VAD] Already sent');
      chunksRef.current = [];
      return;
    }
    sentRef.current = true;

    dispatch({ type: 'SET_STATUS', status: 'processing' });
    dispatch({ type: 'APPEND_USER_MESSAGE', text: '识别中…' });

    const wav = _buildWav(chunksRef.current, SAMPLE_RATE);
    chunksRef.current = [];

    const base64 = _arrayBufferToBase64(wav);
    console.log(`[VAD] SENDING WAV: ${wav.byteLength}B → ${base64.length} base64 chars`);

    if (window.__wsSend) {
      window.__wsSend(JSON.stringify({ type: 'audio', data: base64, timestamp: Date.now() }));
    } else {
      console.error('[VAD] No WS send function');
      dispatch({ type: 'ERROR', message: 'WebSocket 未就绪，请刷新' });
      dispatch({ type: 'SET_STATUS', status: 'idle' });
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
    isSpeakingRef.current = false;
  }
}

// ── WAV helpers (unchanged) ──────────────────────────────

function _buildWav(chunks, sampleRate) {
  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
  const buffer = new ArrayBuffer(44 + totalLength * 2);
  const view = new DataView(buffer);
  _writeWavHeader(view, totalLength, sampleRate);
  let offset = 44;
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++) {
      const s = Math.max(-1, Math.min(1, chunk[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }
  }
  return buffer;
}

function _writeWavHeader(view, dataLength, sampleRate) {
  const byteRate = sampleRate * 2;
  view.setUint32(0, 0x52494646, false);
  view.setUint32(4, 36 + dataLength * 2, true);
  view.setUint32(8, 0x57415645, false);
  view.setUint32(12, 0x666D7420, false);
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  view.setUint32(36, 0x64617461, false);
  view.setUint32(40, dataLength * 2, true);
}

function _arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
