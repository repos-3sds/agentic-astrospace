import { signal } from '@angular/core';

/**
 * The tab bar's own destinations for the current mode, set by the mobile
 * shell. The root component reads it for hardware Back: from a tab other
 * than Today, Back returns to Today rather than walking back through every
 * tab the reader tapped (Material's top-level rule; nativeness audit N11).
 */
export const activeTabRoots = signal<readonly string[]>([]);
