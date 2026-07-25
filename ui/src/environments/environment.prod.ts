import type { AppEnvironment } from './environment.model';

/** Production configuration. See environment.model.ts for the contract. */
export const environment: AppEnvironment = {
  production: true,

  /**
   * Set to the deployed service origin before building for a device, e.g.
   * 'https://astrospace-<hash>-<region>.run.app'. Left empty on purpose rather
   * than guessed: a wrong origin fails at request time with an opaque CORS
   * error, whereas an empty one fails immediately in apiOrigin() with a message
   * that says what to do.
   *
   * Web builds ignore this entirely and remain same-origin.
   */
  nativeApiOrigin: '',
};
