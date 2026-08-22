"""
app/ai/speech_engine.py
Lightweight Hugging Face Whisper Speech-to-Text Engine for SVIT AI Assistant.
Uses openai/whisper-tiny with lazy-loading and multi-format in-memory audio decoding.
"""
import io
import wave
import numpy as np
from typing import Optional


_processor = None
_model = None


def get_whisper_models():
    """
    Lazy-loads Hugging Face WhisperProcessor and WhisperForConditionalGeneration
    for openai/whisper-tiny on first use.
    """
    global _processor, _model
    if _processor is None or _model is None:
        import torch
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        
        print("[SpeechEngine] Loading Hugging Face Whisper model (openai/whisper-tiny)...")
        _processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")
        _model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")
        _model.eval()
        print("[SpeechEngine] Whisper model loaded successfully.")

    return _processor, _model


def decode_audio_to_16khz_mono(audio_bytes: bytes) -> np.ndarray:
    """
    Decodes in-memory audio bytes (WAV, OGG, FLAC, RAW) into a 16kHz mono float32 numpy array
    using soundfile with fallbacks to wave and scipy.
    """
    # 1. Try Soundfile first (handles various formats, rates, bit-depths)
    try:
        import soundfile as sf
        with io.BytesIO(audio_bytes) as buf:
            audio, sample_rate = sf.read(buf, dtype='float32')

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        if sample_rate != 16000 and len(audio) > 0:
            import scipy.signal as signal
            target_samples = int(len(audio) * 16000 / sample_rate)
            audio = signal.resample(audio, target_samples)

        return audio.astype(np.float32)

    except Exception as sf_err:
        pass

    # 2. Fallback to standard library wave module
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_frames = wf.readframes(n_frames)

        if sampwidth == 2:
            audio = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 1:
            audio = (np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sampwidth == 4:
            audio = np.frombuffer(raw_frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")

        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        if framerate != 16000 and len(audio) > 0:
            import scipy.signal as signal
            target_samples = int(len(audio) * 16000 / framerate)
            audio = signal.resample(audio, target_samples)


        return audio.astype(np.float32)

    except Exception as wave_err:
        pass

    # 3. Fallback raw PCM 16-bit 16kHz buffer reading
    try:
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return audio
    except Exception as raw_err:
        raise ValueError(f"Failed to decode audio data: {raw_err}")


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribes audio bytes using the Hugging Face Whisper-tiny model.
    Returns clean, stripped transcript string.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return ""

    try:
        processor, model = get_whisper_models()
        audio_array = decode_audio_to_16khz_mono(audio_bytes)

        if len(audio_array) == 0:
            return ""

        # Normalize audio array
        max_val = np.max(np.abs(audio_array))
        if max_val > 0:
            audio_array = audio_array / max_val

        # Extract features and generate transcription
        input_features = processor(audio_array, sampling_rate=16000, return_tensors="pt").input_features
        predicted_ids = model.generate(input_features, language="en", task="transcribe")
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

        return transcription.strip()

    except Exception as e:
        print(f"[SpeechEngine] Error during transcription: {e}")
        raise e
