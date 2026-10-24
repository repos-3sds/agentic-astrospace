import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { publishTextZoom } from './app/core/text-zoom';

publishTextZoom();

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
