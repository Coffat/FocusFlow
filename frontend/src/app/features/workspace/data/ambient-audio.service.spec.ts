import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { AmbientAudioService } from './ambient-audio.service';

interface MockAudioNode {
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
}

interface MockGainNode extends MockAudioNode {
  gain: {
    value: number;
    setTargetAtTime: ReturnType<typeof vi.fn>;
    setValueAtTime: ReturnType<typeof vi.fn>;
    exponentialRampToValueAtTime: ReturnType<typeof vi.fn>;
  };
}

function createMockAudioContextClass() {
  const instances: Array<{
    state: string;
    sampleRate: number;
    currentTime: number;
    destination: Record<string, unknown>;
    resume: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    createGain: ReturnType<typeof vi.fn>;
    createBuffer: ReturnType<typeof vi.fn>;
    createBufferSource: ReturnType<typeof vi.fn>;
    createBiquadFilter: ReturnType<typeof vi.fn>;
    createOscillator: ReturnType<typeof vi.fn>;
    oscillators: Array<{
      type: string;
      frequency: { setValueAtTime: ReturnType<typeof vi.fn> };
      connect: ReturnType<typeof vi.fn>;
      start: ReturnType<typeof vi.fn>;
      stop: ReturnType<typeof vi.fn>;
    }>;
  }> = [];

  class MockAudioContext {
    state = 'running';
    sampleRate = 44100;
    currentTime = 0;
    destination = {};
    oscillators: Array<{
      type: string;
      frequency: { setValueAtTime: ReturnType<typeof vi.fn> };
      connect: ReturnType<typeof vi.fn>;
      start: ReturnType<typeof vi.fn>;
      stop: ReturnType<typeof vi.fn>;
    }> = [];

    resume = vi.fn().mockResolvedValue(undefined);
    close = vi.fn().mockResolvedValue(undefined);

    createGain = vi.fn((): MockGainNode => ({
      gain: {
        value: 1,
        setTargetAtTime: vi.fn(),
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    }));

    createBuffer = vi.fn((_channels: number, length: number) => ({
      getChannelData: () => new Float32Array(length),
    }));

    createBufferSource = vi.fn(() => ({
      buffer: null as unknown,
      loop: false,
      connect: vi.fn(),
      disconnect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    }));

    createBiquadFilter = vi.fn(() => ({
      type: 'lowpass',
      frequency: { value: 400 },
      Q: { value: 1 },
      connect: vi.fn(),
      disconnect: vi.fn(),
    }));

    createOscillator = vi.fn(() => {
      const osc = {
        type: 'sine',
        frequency: { setValueAtTime: vi.fn() },
        connect: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
      };
      this.oscillators.push(osc);
      return osc;
    });

    constructor() {
      instances.push(this);
    }
  }

  return { MockAudioContext, instances };
}

describe('AmbientAudioService', () => {
  let service: AmbientAudioService;
  let originalAudioContext: unknown;

  beforeEach(() => {
    originalAudioContext = (window as unknown as Record<string, unknown>)[
      'AudioContext'
    ];
    delete (window as unknown as Record<string, unknown>)['AudioContext'];
    delete (window as unknown as Record<string, unknown>)['webkitAudioContext'];

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [AmbientAudioService],
    });
    service = TestBed.inject(AmbientAudioService);
  });

  afterEach(() => {
    service.ngOnDestroy();
    if (originalAudioContext !== undefined) {
      (window as unknown as Record<string, unknown>)['AudioContext'] =
        originalAudioContext;
    } else {
      delete (window as unknown as Record<string, unknown>)['AudioContext'];
    }
    vi.restoreAllMocks();
  });

  it('initializes with 5 Vietnamese ambient channels and default signals', () => {
    expect(service.masterVolume()).toBe(0.65);
    expect(service.isMuted()).toBe(false);
    expect(service.chimeEnabled()).toBe(true);
    expect(service.isAnySoundPlaying()).toBe(false);
    expect(service.embedUrl()).toBeNull();
    expect(service.embedProvider()).toBeNull();
    expect(service.embedRawInput()).toBe('');
    expect(service.embedError()).toBeNull();
    expect(service.safeEmbedResourceUrl()).toBeNull();

    expect(service.channels().map((c) => c.id)).toEqual([
      'rain',
      'cafe',
      'brown',
      'white',
      'fireplace',
    ]);
    expect(service.channels().map((c) => c.label)).toEqual([
      'Tiếng mưa',
      'Quán cafe ấm',
      'Brown Noise',
      'White / Pink Noise',
      'Lò sưởi & Gió',
    ]);
  });

  it('handles missing AudioContext safely without throwing (jsdom/SSR)', () => {
    expect(() => service.toggleChannel('rain')).not.toThrow();
    expect(service.isAnySoundPlaying()).toBe(true);
    expect(() => service.setChannelVolume('rain', 0.4)).not.toThrow();
    expect(() => service.applyScenePreset('cafe')).not.toThrow();
    expect(() => service.playCompletionChime()).not.toThrow();
    expect(() => service.stopAllSounds()).not.toThrow();
    expect(service.isAnySoundPlaying()).toBe(false);
  });

  it('lazily creates AudioContext only on user interaction and cleans up on destroy', () => {
    const { MockAudioContext, instances } = createMockAudioContextClass();
    (window as unknown as Record<string, unknown>)['AudioContext'] =
      MockAudioContext;

    expect(instances.length).toBe(0);

    service.toggleChannel('rain');
    expect(instances.length).toBe(1);
    expect(service.isAnySoundPlaying()).toBe(true);

    service.setMasterVolume(0.8);
    expect(service.masterVolume()).toBe(0.8);

    service.toggleMute();
    expect(service.isMuted()).toBe(true);
    service.setMuted(false);
    expect(service.isMuted()).toBe(false);

    service.ngOnDestroy();
    expect(instances[0].close).toHaveBeenCalledTimes(1);
  });

  it('applies scene presets accurately', () => {
    service.applyScenePreset('rain');
    expect(service.channels().find((c) => c.id === 'rain')).toMatchObject({
      active: true,
      volume: 0.55,
    });
    expect(
      service.channels().filter((c) => c.active).map((c) => c.id)
    ).toEqual(['rain']);

    service.applyScenePreset('cafe');
    expect(service.channels().find((c) => c.id === 'cafe')).toMatchObject({
      active: true,
      volume: 0.5,
    });
    expect(service.channels().find((c) => c.id === 'rain')).toMatchObject({
      active: true,
      volume: 0.15,
    });

    service.applyScenePreset('library');
    expect(service.channels().find((c) => c.id === 'fireplace')).toMatchObject({
      active: true,
      volume: 0.45,
    });
    expect(service.channels().find((c) => c.id === 'brown')).toMatchObject({
      active: true,
      volume: 0.25,
    });

    service.applyScenePreset('lofi-night');
    expect(service.channels().find((c) => c.id === 'white')).toMatchObject({
      active: true,
      volume: 0.25,
    });

    service.applyScenePreset('architectural');
    expect(service.isAnySoundPlaying()).toBe(false);
  });

  it('plays 2-note C5 -> E5 completion chime when chimeEnabled is true', () => {
    const { MockAudioContext, instances } = createMockAudioContextClass();
    (window as unknown as Record<string, unknown>)['AudioContext'] =
      MockAudioContext;

    service.setChimeEnabled(false);
    service.playCompletionChime();
    expect(instances.length).toBe(0);

    service.toggleChime();
    expect(service.chimeEnabled()).toBe(true);
    service.playCompletionChime();

    expect(instances.length).toBe(1);
    expect(instances[0].oscillators.length).toBe(2);
    expect(
      instances[0].oscillators[0].frequency.setValueAtTime
    ).toHaveBeenCalledWith(523.25, expect.any(Number));
    expect(
      instances[0].oscillators[1].frequency.setValueAtTime
    ).toHaveBeenCalledWith(659.25, expect.any(Number));
  });

  describe('parseMediaEmbed & setMediaEmbed', () => {
    it('accepts valid YouTube video, shorts, live, youtu.be, and playlist URLs', () => {
      const watch = service.parseMediaEmbed(
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42'
      );
      expect(watch).toEqual({
        ok: true,
        provider: 'youtube',
        embedUrl: 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ',
      });

      const shortLink = service.parseMediaEmbed('https://youtu.be/jfKfPfyJRdk');
      expect(shortLink).toEqual({
        ok: true,
        provider: 'youtube',
        embedUrl: 'https://www.youtube-nocookie.com/embed/jfKfPfyJRdk',
      });

      const mobileShorts = service.parseMediaEmbed(
        'https://m.youtube.com/shorts/abcDEF12345'
      );
      expect(mobileShorts).toEqual({
        ok: true,
        provider: 'youtube',
        embedUrl: 'https://www.youtube-nocookie.com/embed/abcDEF12345',
      });

      const playlist = service.parseMediaEmbed(
        'https://youtube.com/playlist?list=PL1234567890abcdef'
      );
      expect(playlist).toEqual({
        ok: true,
        provider: 'youtube',
        embedUrl:
          'https://www.youtube-nocookie.com/embed?list=PL1234567890abcdef',
      });
    });

    it('accepts valid Spotify track, album, playlist, and episode URLs', () => {
      const spotify = service.parseMediaEmbed(
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=1234'
      );
      expect(spotify).toEqual({
        ok: true,
        provider: 'spotify',
        embedUrl:
          'https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M',
      });

      const track = service.parseMediaEmbed(
        'https://open.spotify.com/intl-vi/track/4uLU6hMCjMI75M1A2tKUQC'
      );
      expect(track).toEqual({
        ok: true,
        provider: 'spotify',
        embedUrl: 'https://open.spotify.com/embed/track/4uLU6hMCjMI75M1A2tKUQC',
      });
    });

    it('rejects disallowed hosts, dangerous protocols, and malformed IDs', () => {
      const evilHost = service.parseMediaEmbed('https://evil.com/watch?v=dQw4w9WgXcQ');
      expect(evilHost.ok).toBe(false);

      const spoofHost = service.parseMediaEmbed(
        'https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ'
      );
      expect(spoofHost.ok).toBe(false);

      const jsProto = service.parseMediaEmbed('javascript:alert(1)');
      expect(jsProto.ok).toBe(false);

      const badYtId = service.parseMediaEmbed('https://youtube.com/watch?v=short');
      expect(badYtId.ok).toBe(false);

      const badSpotifyType = service.parseMediaEmbed(
        'https://open.spotify.com/artist/37i9dQZF1DXcBWIGoYBM5M'
      );
      expect(badSpotifyType.ok).toBe(false);
    });

    it('updates signals, safeEmbedResourceUrl, and clears embed cleanly', () => {
      const ok = service.setMediaEmbed('https://youtu.be/jfKfPfyJRdk');
      expect(ok).toBe(true);
      expect(service.embedProvider()).toBe('youtube');
      expect(service.embedUrl()).toBe(
        'https://www.youtube-nocookie.com/embed/jfKfPfyJRdk'
      );
      expect(service.embedError()).toBeNull();
      expect(service.safeEmbedResourceUrl()).not.toBeNull();

      const bad = service.setMediaEmbed('https://vimeo.com/123456');
      expect(bad).toBe(false);
      expect(service.embedUrl()).toBeNull();
      expect(service.embedProvider()).toBeNull();
      expect(service.embedError()).toBeTruthy();
      expect(service.safeEmbedResourceUrl()).toBeNull();

      service.clearMediaEmbed();
      expect(service.embedRawInput()).toBe('');
      expect(service.embedError()).toBeNull();
      expect(service.embedUrl()).toBeNull();
    });
  });
});
