export type NoteMediaPreview =
  | {
      kind: 'youtube';
      url: string;
      videoId: string;
      thumbnailUrl: string;
      domain: 'youtube.com';
    }
  | {
      kind: 'image';
      url: string;
      domain: string;
    }
  | {
      kind: 'video';
      url: string;
      domain: string;
    }
  | {
      kind: 'link';
      url: string;
      domain: string;
      faviconUrl: string;
      displayPath: string;
    };

const MAX_PREVIEWS_PER_NOTE = 3;
const URL_CANDIDATE_REGEX = /https?:\/\/[^\s<>"'`]+/gi;
const YOUTUBE_ID_REGEX = /^[a-zA-Z0-9_-]{11}$/;
const IMAGE_EXT_REGEX = /\.(jpg|jpeg|png|webp|gif|avif|svg)$/i;
const VIDEO_EXT_REGEX = /\.(mp4|webm|mov|ogg)$/i;

function trimTrailingPunctuation(raw: string): string {
  let cleaned = raw.replace(/[.,;:!?]+$/, '');
  while (cleaned.endsWith(')')) {
    const opens = (cleaned.match(/\(/g) ?? []).length;
    const closes = (cleaned.match(/\)/g) ?? []).length;
    if (closes > opens) {
      cleaned = cleaned.slice(0, -1).replace(/[.,;:!?]+$/, '');
    } else {
      break;
    }
  }
  return cleaned;
}

function normalizeDomain(hostname: string): string {
  return hostname.toLowerCase().replace(/^www\./, '');
}

function extractYouTubeVideoId(url: URL): string | null {
  const host = url.hostname.toLowerCase().replace(/^(www\.|m\.)/, '');
  const segments = url.pathname.split('/').filter(Boolean);

  let candidate: string | null = null;
  if (host === 'youtu.be') {
    candidate = segments[0] ?? null;
  } else if (host === 'youtube.com') {
    if (url.pathname === '/watch') {
      candidate = url.searchParams.get('v');
    } else if (
      (segments[0] === 'shorts' || segments[0] === 'live') &&
      segments.length >= 2
    ) {
      candidate = segments[1];
    }
  }

  return candidate && YOUTUBE_ID_REGEX.test(candidate) ? candidate : null;
}

function formatDisplayPath(url: URL): string {
  const full = `${url.pathname}${url.search}`;
  if (full === '/' || !full) {
    return '';
  }
  return full.length > 48 ? `${full.slice(0, 45)}...` : full;
}

export function extractNoteMediaPreviews(content: string): NoteMediaPreview[] {
  if (!content) {
    return [];
  }

  const matches = content.match(URL_CANDIDATE_REGEX);
  if (!matches) {
    return [];
  }

  const previews: NoteMediaPreview[] = [];
  const seenUrls = new Set<string>();

  for (const rawMatch of matches) {
    if (previews.length >= MAX_PREVIEWS_PER_NOTE) {
      break;
    }

    const candidate = trimTrailingPunctuation(rawMatch);
    let parsed: URL;
    try {
      parsed = new URL(candidate);
    } catch {
      continue;
    }

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      continue;
    }

    const normalizedUrl = parsed.toString();
    if (seenUrls.has(normalizedUrl)) {
      continue;
    }
    seenUrls.add(normalizedUrl);

    const videoId = extractYouTubeVideoId(parsed);
    if (videoId) {
      previews.push({
        kind: 'youtube',
        url: normalizedUrl,
        videoId,
        thumbnailUrl: `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
        domain: 'youtube.com',
      });
      continue;
    }

    const domain = normalizeDomain(parsed.hostname);
    if (IMAGE_EXT_REGEX.test(parsed.pathname)) {
      previews.push({
        kind: 'image',
        url: normalizedUrl,
        domain,
      });
      continue;
    }

    if (VIDEO_EXT_REGEX.test(parsed.pathname)) {
      previews.push({
        kind: 'video',
        url: normalizedUrl,
        domain,
      });
      continue;
    }

    previews.push({
      kind: 'link',
      url: normalizedUrl,
      domain,
      faviconUrl: `https://www.google.com/s2/favicons?sz=64&domain=${encodeURIComponent(domain)}`,
      displayPath: formatDisplayPath(parsed),
    });
  }

  return previews;
}
