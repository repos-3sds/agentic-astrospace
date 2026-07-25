/**
 * Shape shared by every environment file.
 *
 * The environments cannot inherit from one another: the production build
 * *replaces* environment.ts with environment.prod.ts, so an import between them
 * becomes a self-import. A common interface gives the same safety without the
 * cycle.
 */
export interface AppEnvironment {
  production: boolean;

  /**
   * Absolute API origin for native (Capacitor) builds only. Web builds ignore
   * it and stay same-origin, so empty is correct for `ng serve` and for the
   * ordinary web deployment.
   */
  nativeApiOrigin: string;
}
