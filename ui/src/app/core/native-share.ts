import { Capacitor } from '@capacitor/core';
import { Directory, Filesystem } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

export interface ShareFileOptions {
  title: string;
  text?: string;
}

/**
 * Hands a generated file to the OS share sheet.
 *
 * In a Capacitor WebView `navigator.share` with files is not implemented on
 * iOS and silently drops the attachment on Android, so the native path writes
 * the file to the app cache and shares its URI through `@capacitor/share`.
 * Browsers still use the Web Share API when it accepts files.
 *
 * Resolves `true` when a share sheet handled the file (including the user
 * dismissing it), `false` when the caller should fall back to a download.
 */
export async function shareFile(file: File, options: ShareFileOptions): Promise<boolean> {
  if (Capacitor.isNativePlatform()) {
    const data = await blobToBase64(file);
    const written = await Filesystem.writeFile({ path: file.name, data, directory: Directory.Cache });
    try {
      await Share.share({ title: options.title, text: options.text, files: [written.uri] });
    } catch (error) {
      if (!isUserCancel(error)) throw error;
    }
    return true;
  }
  if (typeof navigator !== 'undefined' && navigator.share && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ title: options.title, text: options.text, files: [file] });
    } catch (error) {
      if (!isUserCancel(error)) throw error;
    }
    return true;
  }
  return false;
}

function isUserCancel(error: unknown): boolean {
  const name = (error as DOMException | undefined)?.name;
  const message = String((error as Error | undefined)?.message ?? '').toLowerCase();
  return name === 'AbortError' || message.includes('cancel');
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
      const result = String(reader.result ?? '');
      resolve(result.slice(result.indexOf(',') + 1));
    };
    reader.readAsDataURL(blob);
  });
}
