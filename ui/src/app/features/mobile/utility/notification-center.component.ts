import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/api.service';
import { PreferencesService } from '../../../core/preferences.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackBarComponent } from '../shared/back-bar.component';
interface AlertItem{id:string;category:string;title:string;body:string|null;deep_link:string|null;read_at:string|null;created_at:string|null}
@Component({selector:'as-notification-center',standalone:true,imports:[BackBarComponent, GenericErrorComponent],templateUrl:'./notification-center.component.html',styleUrl:'./notification-center.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class NotificationCenterComponent{
 private readonly api=inject(ApiService);private readonly router=inject(Router);
 protected readonly preferences=inject(PreferencesService);
 protected readonly alerts=signal<AlertItem[]>([]);protected readonly loading=signal(true);protected readonly error=signal<string|null>(null);
 protected readonly actionError=signal<string|null>(null);protected readonly readingId=signal<string|null>(null);
 protected readonly visibleAlerts=computed(()=>this.preferences.experienceMode()==='guided'?this.alerts().filter(a=>a.category!=='transit').slice(0,5):this.alerts());
 constructor(){void this.load()} protected async load(){this.loading.set(true);this.error.set(null);this.actionError.set(null);try{const r=await this.api.get<{alerts:AlertItem[]}>('/me/alerts');this.alerts.set(r.alerts)}catch(e){this.error.set((e as Error).message)}finally{this.loading.set(false)}}
 protected async open(a:AlertItem){this.actionError.set(null);this.readingId.set(a.id);try{if(!a.read_at){await this.api.post(`/me/alerts/${a.id}/read`,{});this.alerts.update(xs=>xs.map(x=>x.id===a.id?{...x,read_at:new Date().toISOString()}:x))}if(a.deep_link?.startsWith('/m/'))await this.router.navigateByUrl(a.deep_link)}catch(e){this.actionError.set((e as Error).message)}finally{this.readingId.set(null)}}
 protected categoryLabel(category:string):string{return category==='transit'?'Transit':category==='morning_brief'?'Your day':category==='festival'?'Festival':'Timing'}
 /** "Just now", "40 min ago", "3 h ago", then the date. */
 protected when(iso:string,now=Date.now()):string{const t=new Date(iso.endsWith('Z')||/[+-]\d\d:\d\d$/.test(iso)?iso:iso+'Z').getTime();if(Number.isNaN(t))return '';const min=Math.round((now-t)/60000);if(min<1)return 'Just now';if(min<60)return `${min} min ago`;if(min<24*60)return `${Math.round(min/60)} h ago`;return new Intl.DateTimeFormat('en',{day:'numeric',month:'short'}).format(t)}
}
