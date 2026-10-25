import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type ColorMap = Record<string, string>;

@Injectable({
  providedIn: 'root'
})
export class ColorService {
  http: HttpClient;

  constructor(http: HttpClient) {
    this.http = http;
  }

  async loadColors() {
    try {
      const palette = await firstValueFrom(
        this.http.get<ColorMap>('/assets/color/palette.json')
      );
      const light = await firstValueFrom(
        this.http.get<ColorMap>('/assets/color/light.json')
      );

      const root = document.documentElement;

      for (const [key, value] of Object.entries(palette)) {
        root.style.setProperty(`--${key}`, value);
        const rgb = this.hexToRgb(value);
        if (rgb.length > 0) {
          root.style.setProperty(`--${key}-rgb`, rgb);
        }
      }

      for (const [key, value] of Object.entries(light)) {
        root.style.setProperty(`--${key}`, value);
        if (value.startsWith('#')) {
          const rgb = this.hexToRgb(value);
          if (rgb.length > 0) {
            root.style.setProperty(`--${key}-rgb`, rgb);
          }
        } else if (value.startsWith('var(--') && value.endsWith(')')) {
          const referencedKey = value.slice(6, -1);
          const rawHex = palette[referencedKey] || '';
          if (rawHex.length > 0) {
            const rgb = this.hexToRgb(rawHex);
            if (rgb.length > 0) {
              root.style.setProperty(`--${key}-rgb`, rgb);
            }
          }
        }
      }
    } catch (_error) {
      // Stylesheet fallback already defined in styles.scss
    }
  }

  hexToRgb(hex: string): string {
    const cleanHex = hex.replace('#', '').trim();
    if (cleanHex.length === 6) {
      const r = parseInt(cleanHex.substring(0, 2), 16);
      const g = parseInt(cleanHex.substring(2, 4), 16);
      const b = parseInt(cleanHex.substring(4, 6), 16);
      if (!isNaN(r) && !isNaN(g) && !isNaN(b)) {
        return `${r}, ${g}, ${b}`;
      }
    } else if (cleanHex.length === 3) {
      const r = parseInt(cleanHex[0] + cleanHex[0], 16);
      const g = parseInt(cleanHex[1] + cleanHex[1], 16);
      const b = parseInt(cleanHex[2] + cleanHex[2], 16);
      if (!isNaN(r) && !isNaN(g) && !isNaN(b)) {
        return `${r}, ${g}, ${b}`;
      }
    }
    return '';
  }
}
