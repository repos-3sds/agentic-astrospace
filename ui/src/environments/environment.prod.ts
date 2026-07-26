import type { AppEnvironment } from './environment.model';

/** Production configuration. See environment.model.ts for the contract. */
export const environment: AppEnvironment = {
  production: true,

  /**
   * The deployed Cloud Run service (project gen-lang-client-0058562386,
   * service agentic-astrospace, region asia-south1).
   *
   * Web builds ignore this entirely and remain same-origin; only a native
   * build reads it, because a relative path there resolves inside the app
   * bundle rather than reaching the server.
   */
  nativeApiOrigin: 'https://agentic-astrospace-cwuqybpnzq-el.a.run.app',
};
