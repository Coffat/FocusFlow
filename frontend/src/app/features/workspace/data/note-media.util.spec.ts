import { extractNoteMediaPreviews } from './note-media.util';

describe('extractNoteMediaPreviews', () => {
  it('returns empty array for empty or URL-free content', () => {
    expect(extractNoteMediaPreviews('')).toEqual([]);
    expect(extractNoteMediaPreviews('Học DDD Aggregate và Entity hôm nay')).toEqual([]);
  });

  it('extracts YouTube previews from watch, youtu.be, shorts, and live URLs', () => {
    const content = [
      'Watch: https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=12s',
      'Short: https://youtube.com/shorts/abcDEF_1234',
      'Share: https://youtu.be/9bZkp7q19f0.',
    ].join('\n');

    expect(extractNoteMediaPreviews(content)).toEqual([
      {
        kind: 'youtube',
        url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=12s',
        videoId: 'dQw4w9WgXcQ',
        thumbnailUrl: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
        domain: 'youtube.com',
      },
      {
        kind: 'youtube',
        url: 'https://youtube.com/shorts/abcDEF_1234',
        videoId: 'abcDEF_1234',
        thumbnailUrl: 'https://i.ytimg.com/vi/abcDEF_1234/hqdefault.jpg',
        domain: 'youtube.com',
      },
      {
        kind: 'youtube',
        url: 'https://youtu.be/9bZkp7q19f0',
        videoId: '9bZkp7q19f0',
        thumbnailUrl: 'https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg',
        domain: 'youtube.com',
      },
    ]);

    const liveResult = extractNoteMediaPreviews('https://www.youtube.com/live/Live1234567');
    expect(liveResult).toEqual([
      {
        kind: 'youtube',
        url: 'https://www.youtube.com/live/Live1234567',
        videoId: 'Live1234567',
        thumbnailUrl: 'https://i.ytimg.com/vi/Live1234567/hqdefault.jpg',
        domain: 'youtube.com',
      },
    ]);
  });

  it('extracts image, video, and generic web link previews', () => {
    const content = [
      'Diagram: https://cdn.example.com/assets/arch.WEBP?v=1',
      'Clip: http://media.example.org/demo.mp4',
      'Docs: https://angular.dev/guide/signals',
    ].join(' ');

    expect(extractNoteMediaPreviews(content)).toEqual([
      {
        kind: 'image',
        url: 'https://cdn.example.com/assets/arch.WEBP?v=1',
        domain: 'cdn.example.com',
      },
      {
        kind: 'video',
        url: 'http://media.example.org/demo.mp4',
        domain: 'media.example.org',
      },
      {
        kind: 'link',
        url: 'https://angular.dev/guide/signals',
        domain: 'angular.dev',
        faviconUrl: 'https://www.google.com/s2/favicons?sz=64&domain=angular.dev',
        displayPath: '/guide/signals',
      },
    ]);
  });

  it('ignores non-http(s) protocols, deduplicates URLs, and caps at 3 previews', () => {
    const content = [
      'javascript:alert(1) data:text/html,hi ftp://files.example.com/a.png',
      'https://example.com/1',
      'https://example.com/1',
      'https://example.com/2.png',
      'https://example.com/3.webm',
      'https://example.com/4',
    ].join(' ');

    const result = extractNoteMediaPreviews(content);
    expect(result.length).toBe(3);
    expect(result.map((item) => item.url)).toEqual([
      'https://example.com/1',
      'https://example.com/2.png',
      'https://example.com/3.webm',
    ]);
  });
});
