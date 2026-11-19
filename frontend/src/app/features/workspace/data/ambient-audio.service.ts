import { Injectable, OnDestroy, computed, inject, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import {
  SoundChannelId,
  SoundChannelState,
  WorkspaceSceneId,
} from '../models/workspace.model';

export type MediaEmbedProvider = 'youtube' | 'spotify';

export type ParseMediaEmbedResult =
  | { ok: true; provider: MediaEmbedProvider; embedUrl: string }
  | { ok: false; error: string };

interface ActiveChannelNodes {
  source: AudioBufferSourceNode;
  filter: BiquadFilterNode;
  gain: GainNode;
}

const YOUTUBE_VIDEO_ID_REGEX = /^[a-zA-Z0-9_-]{11}$/;
const YOUTUBE_PLAYLIST_ID_REGEX = /^[a-zA-Z0-9_-]{10,}$/;
const SPOTIFY_ID_REGEX = /^[a-zA-Z0-9]{22}$/;
const SPOTIFY_PATH_REGEX =
  /^\/(?:intl-[a-zA-Z-]+\/)?(track|album|playlist|episode)\/([a-zA-Z0-9]{22})(?:\/)?$/;

const ALLOWED_MEDIA_HOSTS = new Set<string>([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtu.be',
  'open.spotify.com',
]);

const INITIAL_CHANNELS: readonly SoundChannelState[] = [
  { id: 'rain', label: 'Tiếng mưa', active: false, volume: 0.55 },
  { id: 'cafe', label: 'Quán cafe ấm', active: false, volume: 0.5 },
  { id: 'brown', label: 'Brown Noise', active: false, volume: 0.45 },
  { id: 'white', label: 'White / Pink Noise', active: false, volume: 0.35 },
  { id: 'fireplace', label: 'Lò sưởi & Gió', active: false, volume: 0.45 },
];

function clampVolume(val: number): number {
  if (!Number.isFinite(val)) {
    return 0;
  }
  return Math.min(1, Math.max(0, val));
}

function getAudioContextConstructor(): (new () => AudioContext) | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const win = window as unknown as {
    AudioContext?: new () => AudioContext;
    webkitAudioContext?: new () => AudioContext;
  };
  return win.AudioContext ?? win.webkitAudioContext ?? null;
}

@Injectable({ providedIn: 'root' })
export class AmbientAudioService implements OnDestroy {
  private readonly sanitizer = inject(DomSanitizer);

  private audioCtx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private noiseBuffer: AudioBuffer | null = null;
  private readonly activeNodes = new Map<SoundChannelId, ActiveChannelNodes>();

  private readonly _masterVolume = signal<number>(0.65);
  private readonly _isMuted = signal<boolean>(false);
  private readonly _chimeEnabled = signal<boolean>(true);
  private readonly _channels = signal<SoundChannelState[]>(
    INITIAL_CHANNELS.map((c) => ({ ...c }))
  );
  private readonly _embedUrl = signal<string | null>(null);
  private readonly _embedProvider = signal<MediaEmbedProvider | null>(null);
  private readonly _embedRawInput = signal<string>('');
  private readonly _embedError = signal<string | null>(null);

  readonly masterVolume = this._masterVolume.asReadonly();
  readonly isMuted = this._isMuted.asReadonly();
  readonly chimeEnabled = this._chimeEnabled.asReadonly();
  readonly channels = this._channels.asReadonly();
  readonly embedUrl = this._embedUrl.asReadonly();
  readonly embedProvider = this._embedProvider.asReadonly();
  readonly embedRawInput = this._embedRawInput.asReadonly();
  readonly embedError = this._embedError.asReadonly();

  readonly isAnySoundPlaying = computed<boolean>(() =>
    this._channels().some((c) => c.active)
  );

  readonly safeEmbedResourceUrl = computed<SafeResourceUrl | null>(() => {
    const url = this._embedUrl();
    if (!url) {
      return null;
    }
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  });

  setMasterVolume(volume: number): void {
    const clamped = clampVolume(volume);
    this._masterVolume.set(clamped);
    this.updateMasterGain();
  }

  toggleMute(): void {
    this._isMuted.update((m) => !m);
    this.updateMasterGain();
  }

  setMuted(muted: boolean): void {
    this._isMuted.set(muted);
    this.updateMasterGain();
  }

  setChimeEnabled(enabled: boolean): void {
    this._chimeEnabled.set(enabled);
  }

  toggleChime(): void {
    this._chimeEnabled.update((c) => !c);
  }

  toggleChannel(id: SoundChannelId): void {
    this._channels.update((list) =>
      list.map((ch) => (ch.id === id ? { ...ch, active: !ch.active } : ch))
    );
    this.syncAudioGraph();
  }

  setChannelVolume(id: SoundChannelId, volume: number): void {
    const clamped = clampVolume(volume);
    this._channels.update((list) =>
      list.map((ch) =>
        ch.id === id
          ? { ...ch, volume: clamped, active: clamped > 0 ? ch.active : false }
          : ch
      )
    );
    this.syncAudioGraph();
  }

  stopAllSounds(): void {
    this._channels.update((list) => list.map((ch) => ({ ...ch, active: false })));
    this.stopAllActiveNodes();
  }

  applyScenePreset(scene: WorkspaceSceneId): void {
    const presetMap: Record<
      WorkspaceSceneId,
      Partial<Record<SoundChannelId, number>>
    > = {
      rain: { rain: 0.55 },
      cafe: { cafe: 0.5, rain: 0.15 },
      library: { fireplace: 0.45, brown: 0.25 },
      'lofi-night': { white: 0.25 },
      architectural: {},
    };

    const preset = presetMap[scene];
    this._channels.update((list) =>
      list.map((ch) => {
        const targetVol = preset[ch.id];
        if (typeof targetVol === 'number') {
          return { ...ch, active: true, volume: targetVol };
        }
        return { ...ch, active: false };
      })
    );
    this.syncAudioGraph();
  }

  playCompletionChime(): void {
    if (!this._chimeEnabled()) {
      return;
    }

    const ctx = this.ensureAudioContext();
    if (!ctx) {
      return;
    }

    try {
      const now = ctx.currentTime;
      const notes = [523.25, 659.25]; // C5 -> E5

      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const startTime = now + idx * 0.18;
        const duration = 0.55;

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, startTime);

        const peakGain = this._isMuted() ? 0 : Math.max(0.08, this._masterVolume() * 0.25);
        gain.gain.setValueAtTime(0.0001, startTime);
        gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, peakGain), startTime + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(startTime);
        osc.stop(startTime + duration + 0.02);
      });
    } catch {
      // Ignore Web Audio errors in unsupported/mocked environments
    }
  }

  parseMediaEmbed(rawUrl: string): ParseMediaEmbedResult {
    const trimmed = rawUrl.trim();
    if (!trimmed) {
      return {
        ok: false,
        error: 'Vui lòng nhập liên kết YouTube hoặc Spotify.',
      };
    }

    let parsed: URL;
    try {
      parsed = new URL(trimmed);
    } catch {
      return {
        ok: false,
        error: 'Liên kết không đúng định dạng URL hợp lệ.',
      };
    }

    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      return {
        ok: false,
        error: 'Chỉ hỗ trợ liên kết HTTP/HTTPS từ YouTube hoặc Spotify.',
      };
    }

    const host = parsed.hostname.toLowerCase();
    if (!ALLOWED_MEDIA_HOSTS.has(host)) {
      return {
        ok: false,
        error: 'Chỉ hỗ trợ phát nhạc từ YouTube (youtube.com, youtu.be) hoặc Spotify (open.spotify.com).',
      };
    }

    if (host === 'open.spotify.com') {
      const match = SPOTIFY_PATH_REGEX.exec(parsed.pathname);
      if (!match) {
        return {
          ok: false,
          error: 'Liên kết Spotify không hợp lệ. Chỉ hỗ trợ track, album, playlist hoặc episode.',
        };
      }
      const [, type, id] = match;
      if (!SPOTIFY_ID_REGEX.test(id)) {
        return {
          ok: false,
          error: 'Mã Spotify không hợp lệ.',
        };
      }
      return {
        ok: true,
        provider: 'spotify',
        embedUrl: `https://open.spotify.com/embed/${type}/${id}`,
      };
    }

    // YouTube handling
    if (host === 'youtu.be') {
      const candidate = parsed.pathname.replace(/^\/+/, '').split('/')[0] ?? '';
      if (!YOUTUBE_VIDEO_ID_REGEX.test(candidate)) {
        return {
          ok: false,
          error: 'Mã video YouTube không hợp lệ.',
        };
      }
      return {
        ok: true,
        provider: 'youtube',
        embedUrl: `https://www.youtube-nocookie.com/embed/${candidate}`,
      };
    }

    const videoParam = parsed.searchParams.get('v');
    if (videoParam) {
      if (!YOUTUBE_VIDEO_ID_REGEX.test(videoParam)) {
        return {
          ok: false,
          error: 'Mã video YouTube không hợp lệ.',
        };
      }
      return {
        ok: true,
        provider: 'youtube',
        embedUrl: `https://www.youtube-nocookie.com/embed/${videoParam}`,
      };
    }

    const pathSegments = parsed.pathname.split('/').filter(Boolean);
    if (
      pathSegments.length >= 2 &&
      (pathSegments[0] === 'embed' ||
        pathSegments[0] === 'shorts' ||
        pathSegments[0] === 'live')
    ) {
      const videoId = pathSegments[1];
      if (!YOUTUBE_VIDEO_ID_REGEX.test(videoId)) {
        return {
          ok: false,
          error: 'Mã video YouTube không hợp lệ.',
        };
      }
      return {
        ok: true,
        provider: 'youtube',
        embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}`,
      };
    }

    const listParam = parsed.searchParams.get('list');
    if (listParam && YOUTUBE_PLAYLIST_ID_REGEX.test(listParam)) {
      return {
        ok: true,
        provider: 'youtube',
        embedUrl: `https://www.youtube-nocookie.com/embed?list=${listParam}`,
      };
    }

    return {
      ok: false,
      error: 'Không tìm thấy mã video hoặc playlist YouTube hợp lệ.',
    };
  }

  setMediaEmbed(rawUrl: string): boolean {
    this._embedRawInput.set(rawUrl);
    if (!rawUrl.trim()) {
      this._embedUrl.set(null);
      this._embedProvider.set(null);
      this._embedError.set(null);
      return true;
    }

    const result = this.parseMediaEmbed(rawUrl);
    if (result.ok) {
      this._embedUrl.set(result.embedUrl);
      this._embedProvider.set(result.provider);
      this._embedError.set(null);
      return true;
    }

    this._embedUrl.set(null);
    this._embedProvider.set(null);
    this._embedError.set(result.error);
    return false;
  }

  clearMediaEmbed(): void {
    this._embedUrl.set(null);
    this._embedProvider.set(null);
    this._embedRawInput.set('');
    this._embedError.set(null);
  }

  ngOnDestroy(): void {
    this.stopAllActiveNodes();
    if (this.audioCtx) {
      try {
        void this.audioCtx.close();
      } catch {
        // Ignore close errors
      }
      this.audioCtx = null;
      this.masterGain = null;
      this.noiseBuffer = null;
    }
  }

  private ensureAudioContext(): AudioContext | null {
    if (this.audioCtx) {
      if (this.audioCtx.state === 'suspended') {
        try {
          void this.audioCtx.resume();
        } catch {
          // Ignore resume errors
        }
      }
      return this.audioCtx;
    }

    const Ctor = getAudioContextConstructor();
    if (!Ctor) {
      return null;
    }

    try {
      const ctx = new Ctor();
      const master = ctx.createGain();
      master.gain.value = this._isMuted() ? 0 : this._masterVolume();
      master.connect(ctx.destination);

      this.audioCtx = ctx;
      this.masterGain = master;
      return ctx;
    } catch {
      return null;
    }
  }

  private updateMasterGain(): void {
    if (!this.masterGain || !this.audioCtx) {
      return;
    }
    try {
      const target = this._isMuted() ? 0 : this._masterVolume();
      this.masterGain.gain.setTargetAtTime(target, this.audioCtx.currentTime, 0.03);
    } catch {
      // Ignore gain update errors
    }
  }

  private syncAudioGraph(): void {
    const channels = this._channels();
    const hasAnyActive = channels.some((c) => c.active);

    if (!hasAnyActive) {
      this.stopAllActiveNodes();
      return;
    }

    const ctx = this.ensureAudioContext();
    if (!ctx || !this.masterGain) {
      return;
    }

    for (const ch of channels) {
      const existing = this.activeNodes.get(ch.id);
      if (!ch.active) {
        if (existing) {
          this.teardownChannelNodes(existing);
          this.activeNodes.delete(ch.id);
        }
        continue;
      }

      if (existing) {
        try {
          existing.gain.gain.setTargetAtTime(ch.volume, ctx.currentTime, 0.04);
        } catch {
          // Ignore gain errors
        }
      } else {
        this.startChannelNodes(ctx, ch.id, ch.volume);
      }
    }
  }

  private getOrCreateNoiseBuffer(ctx: AudioContext): AudioBuffer {
    if (this.noiseBuffer) {
      return this.noiseBuffer;
    }
    const sampleRate = ctx.sampleRate || 44100;
    const length = sampleRate * 2;
    const buffer = ctx.createBuffer(1, length, sampleRate);
    const data = buffer.getChannelData(0);
    let lastOut = 0;
    for (let i = 0; i < length; i++) {
      const white = Math.random() * 2 - 1;
      lastOut = (lastOut + 0.02 * white) / 1.02;
      data[i] = lastOut * 3.5;
    }
    this.noiseBuffer = buffer;
    return buffer;
  }

  private startChannelNodes(
    ctx: AudioContext,
    id: SoundChannelId,
    volume: number
  ): void {
    if (!this.masterGain) {
      return;
    }
    try {
      const source = ctx.createBufferSource();
      source.buffer = this.getOrCreateNoiseBuffer(ctx);
      source.loop = true;

      const filter = ctx.createBiquadFilter();
      this.configureFilterForChannel(filter, id);

      const gain = ctx.createGain();
      gain.gain.value = volume;

      source.connect(filter);
      filter.connect(gain);
      gain.connect(this.masterGain);
      source.start();

      this.activeNodes.set(id, { source, filter, gain });
    } catch {
      // Ignore Web Audio errors in unsupported/mocked environments
    }
  }

  private configureFilterForChannel(
    filter: BiquadFilterNode,
    id: SoundChannelId
  ): void {
    switch (id) {
      case 'rain':
        filter.type = 'bandpass';
        filter.frequency.value = 1100;
        filter.Q.value = 0.7;
        break;
      case 'cafe':
        filter.type = 'bandpass';
        filter.frequency.value = 650;
        filter.Q.value = 0.9;
        break;
      case 'brown':
        filter.type = 'lowpass';
        filter.frequency.value = 280;
        filter.Q.value = 0.7;
        break;
      case 'white':
        filter.type = 'highpass';
        filter.frequency.value = 400;
        filter.Q.value = 0.5;
        break;
      case 'fireplace':
        filter.type = 'lowpass';
        filter.frequency.value = 420;
        filter.Q.value = 1.1;
        break;
    }
  }

  private stopAllActiveNodes(): void {
    for (const nodes of this.activeNodes.values()) {
      this.teardownChannelNodes(nodes);
    }
    this.activeNodes.clear();
  }

  private teardownChannelNodes(nodes: ActiveChannelNodes): void {
    try {
      nodes.source.stop();
    } catch {
      // Ignore if already stopped
    }
    try {
      nodes.source.disconnect();
      nodes.filter.disconnect();
      nodes.gain.disconnect();
    } catch {
      // Ignore disconnect errors
    }
  }
}
