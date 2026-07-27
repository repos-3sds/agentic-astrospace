import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/api.service';
import { PreferencesService } from '../../../core/preferences.service';
interface AlertItem{id:string;category:string;title:string;body:string|null;deep_link:string|null;read_at:string|null;created_at:string|null}
@Component({selector:'as-notification-center',standalone:true,imports:[RouterLink],templateUrl:'./notification-center.component.html',styleUrl:'./utility.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class NotificationCenterComponent{
 private readonly api=inject(ApiService);private readonly router=inject(Router);
 protected readonly preferences=inject(PreferencesService);
 protected readonly alerts=signal<AlertItem[]>([]);protected readonly loading=signal(true);protected readonly error=signal<string|null>(null);
 protected readonly visibleAlerts=computed(()=>this.preferences.experienceMode()==='guided'?this.alerts().filter(a=>a.category!=='transit').slice(0,5):this.alerts());
 constructor(){void this.load()} protected async load(){this.loading.set(true);try{const r=await this.api.get<{alerts:AlertItem[]}>('/me/alerts');this.alerts.set(r.alerts)}catch(e){this.error.set((e as Error).message)}finally{this.loading.set(false)}}
 protected async open(a:AlertItem){if(!a.read_at){await this.api.post(`/me/alerts/${a.id}/read`,{});this.alerts.update(xs=>xs.map(x=>x.id===a.id?{...x,read_at:new Date().toISOString()}:x))}if(a.deep_link?.startsWith('/m/'))await this.router.navigateByUrl(a.deep_link)}
}
