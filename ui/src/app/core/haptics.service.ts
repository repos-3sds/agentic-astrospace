import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';

/**
 * Native haptic feedback, and a no-op everywhere else.
 *
 * Two rules this service exists to enforce:
 *
 * 1. **Web must not pay for it.** `@capacitor/haptics` is imported lazily, so
 *    the browser bundle never loads a plugin it cannot use.
 * 2. **A failed buzz must never break an interaction.** Every call swallows its
 *    error. Haptics are confirmation of something that already happened; if the
 *    motor is unavailable, busy, or the user disabled it in iOS Settings, the
 *    tap it accompanies still has to work.
 *
 * Intensity is chosen by *meaning*, not by feel — `tap()` for an ordinary
 * press, `select()` when a choice changes, `success`/`warning` for the outcome
 * of a committed action. Picking by meaning is what keeps the vocabulary
 * consistent as more screens adopt it.
 */
@Injectable({ providedIn: 'root' })
export class HapticsService {
  private readonly native = Capacitor.isNativePlatform();

  /** An ordinary button press. */
  tap(): void {
    void this.impact('Light');
  }

  /** A firmer press for a primary/committing action. */
  press(): void {
    void this.impact('Medium');
  }

  /** A choice changed — segmented controls, mode pickers, tabs. */
  select(): void {
    if (!this.native) return;
    void (async () => {
      try {
        const { Haptics } = await import('@capacitor/haptics');
        await Haptics.selectionChanged();
      } catch {
        /* see class docs */
      }
    })();
  }

  /** An action completed. */
  success(): void {
    void this.notify('SUCCESS');
  }

  /**
   * An action needs care before it completes.
   *
   * Deliberately not used for astrological content. A caution buzz on a dosha
   * or a difficult transit would turn a flag into a physical scare, which is
   * the fear-selling pattern design_principles.md §4 rules out. Reserve this
   * for interface consequences — destructive confirmations, validation.
   */
  warning(): void {
    void this.notify('WARNING');
  }

  /** An action failed. */
  error(): void {
    void this.notify('ERROR');
  }

  private async impact(style: 'Light' | 'Medium' | 'Heavy'): Promise<void> {
    if (!this.native) return;
    try {
      const { Haptics, ImpactStyle } = await import('@capacitor/haptics');
      await Haptics.impact({ style: ImpactStyle[style] });
    } catch {
      /* see class docs */
    }
  }

  private async notify(type: 'SUCCESS' | 'WARNING' | 'ERROR'): Promise<void> {
    if (!this.native) return;
    try {
      const { Haptics, NotificationType } = await import('@capacitor/haptics');
      const capacitorType = type === 'SUCCESS' ? NotificationType.Success 
        : type === 'WARNING' ? NotificationType.Warning 
        : NotificationType.Error;
      await Haptics.notification({ type: capacitorType });
    } catch {
      /* see class docs */
    }
  }
}
