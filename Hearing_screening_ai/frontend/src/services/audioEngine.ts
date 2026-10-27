export type EarChannel = 'LEFT' | 'RIGHT';

class AudioEngineService {
    private audioCtx: AudioContext | null = null;

    private getAudioContext(): AudioContext {
        if (!this.audioCtx) {
            const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            this.audioCtx = new AudioContextClass();
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
        return this.audioCtx;
    }

    public playPureTone(
        frequency: number,
        relativeGain: number,
        ear: EarChannel,
        durationMs: number = 3000
    ): Promise<void> {
        return new Promise((resolve) => {
            const ctx = this.getAudioContext();

            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();
            const panner = ctx.createStereoPanner();

            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);

            // Stereo Channel Separation: -1 = 100% Left Ear, +1 = 100% Right Ear
            panner.pan.setValueAtTime(ear === 'LEFT' ? -1 : 1, ctx.currentTime);

            // Smooth Envelope (50ms ramp up/down to eliminate clicking audio pops)
            const now = ctx.currentTime;
            const durationSec = durationMs / 1000;
            const rampTime = 0.05;

            gainNode.gain.setValueAtTime(0, now);
            gainNode.gain.linearRampToValueAtTime(relativeGain, now + rampTime);
            gainNode.gain.setValueAtTime(relativeGain, now + durationSec - rampTime);
            gainNode.gain.linearRampToValueAtTime(0, now + durationSec);

            oscillator.connect(gainNode);
            gainNode.connect(panner);
            panner.connect(ctx.destination);

            oscillator.start(now);
            oscillator.stop(now + durationSec);

            oscillator.onended = () => {
                oscillator.disconnect();
                gainNode.disconnect();
                panner.disconnect();
                resolve();
            };
        });
    }
}

export const audioEngine = new AudioEngineService();