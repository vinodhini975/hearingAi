/**
 * Web Audio Engine for Pure-Tone Stimulus Generation
 *
 * Requirements satisfied:
 * 1. Audio generation through Oscillator -> GainNode (Stimulus Level) -> StereoPannerNode -> Destination.
 * 2. Operating system volume is NEVER changed or modified programmatically.
 * 3. Stimulus intensity is varied strictly in software via GainNode.
 * 4. Pure sine waves with smooth attack/decay ramps to prevent acoustic transient clicks.
 * 5. Ear isolation via stereo panning (-1.0 Left, +1.0 Right).
 */

export interface PlayToneOptions {
  frequency: number;            // 250, 500, 1000, 2000, 4000, 8000 Hz
  ear: 'LEFT' | 'RIGHT';
  stimulusLevel: number;        // Software gain amplitude (e.g. 0.001 to 0.40)
  durationMs?: number;          // Default ~1400ms
  rampMs?: number;              // Attack/decay ramp time (default ~40ms)
}

class AudiometryAudioEngine {
  private audioCtx: AudioContext | null = null;
  private currentOsc: OscillatorNode | null = null;
  private currentGain: GainNode | null = null;
  private currentPanner: StereoPannerNode | null = null;
  private activeTimeout: any = null;

  public getAudioContext(): AudioContext {
    if (!this.audioCtx || this.audioCtx.state === 'closed') {
      const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtx = new AudioCtxClass();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  /**
   * Plays a pure tone stimulus at the specified frequency, ear, and software stimulus level.
   * System volume is completely untouched.
   */
  public async playTone(options: PlayToneOptions): Promise<void> {
    this.stopTone();

    const ctx = this.getAudioContext();
    const duration = (options.durationMs || 1400) / 1000;
    const ramp = (options.rampMs || 40) / 1000;
    const startTime = ctx.currentTime + 0.02; // Small buffer to ensure clean scheduling
    const stopTime = startTime + duration;

    // 1. Pure sine wave oscillator
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(options.frequency, startTime);

    // 2. Software Stimulus Gain stage (varying amplitude while system volume is FIXED)
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.00001, startTime);
    // Smooth attack ramp to prevent click
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, options.stimulusLevel), startTime + ramp);
    // Sustain
    gain.gain.setValueAtTime(Math.max(0.0001, options.stimulusLevel), stopTime - ramp);
    // Smooth decay ramp
    gain.gain.exponentialRampToValueAtTime(0.00001, stopTime);

    // 3. Stereo Panner for strict ear channel separation
    const panner = ctx.createStereoPanner();
    panner.pan.setValueAtTime(options.ear === 'LEFT' ? -1.0 : 1.0, startTime);

    // Connect node chain: Oscillator -> Gain (Stimulus) -> Panner (Ear) -> Destination
    osc.connect(gain);
    gain.connect(panner);
    panner.connect(ctx.destination);

    this.currentOsc = osc;
    this.currentGain = gain;
    this.currentPanner = panner;

    osc.start(startTime);
    osc.stop(stopTime + 0.05);

    return new Promise((resolve) => {
      this.activeTimeout = setTimeout(() => {
        this.stopTone();
        resolve();
      }, (duration + 0.1) * 1000);
    });
  }

  public stopTone(): void {
    if (this.activeTimeout) {
      clearTimeout(this.activeTimeout);
      this.activeTimeout = null;
    }
    if (this.currentOsc) {
      try {
        this.currentOsc.stop();
        this.currentOsc.disconnect();
      } catch (e) {
        // Ignore if already stopped
      }
      this.currentOsc = null;
    }
    if (this.currentGain) {
      try {
        this.currentGain.disconnect();
      } catch (e) {
        // Ignore
      }
      this.currentGain = null;
    }
    if (this.currentPanner) {
      try {
        this.currentPanner.disconnect();
      } catch (e) {
        // Ignore
      }
      this.currentPanner = null;
    }
  }

  /**
   * Detects connected audio output device information if browser permissions allow.
   */
  public async detectAudioOutputDevice(): Promise<{ deviceName: string; supported: boolean }> {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioOutputs = devices.filter((d) => d.kind === 'audiooutput');
        if (audioOutputs.length > 0) {
          const defaultOutput = audioOutputs.find((d) => d.deviceId === 'default') || audioOutputs[0];
          return {
            deviceName: defaultOutput.label || 'Default Stereo Headphone / Audio Output',
            supported: true,
          };
        }
      }
    } catch (e) {
      console.warn('Unable to enumerate audio output devices:', e);
    }
    return {
      deviceName: 'System Default Audio Output (Stereo Headphones Recommended)',
      supported: false,
    };
  }
}

export const audioEngine = new AudiometryAudioEngine();
