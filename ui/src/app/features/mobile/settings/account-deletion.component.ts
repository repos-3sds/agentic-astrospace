import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Browser } from '@capacitor/browser';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/api.service';
import { AuthService } from '../../../core/auth.service';
import { EntitlementService } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { PurchaseService } from '../../../core/purchase.service';
import { BackBarComponent } from '../shared/back-bar.component';
import { ACCOUNT_DELETED_FLAG } from '../onboarding/landing.component';
@Component({selector:'as-account-deletion',standalone:true,imports:[BackBarComponent, FormsModule,RouterLink],templateUrl:'./account-deletion.component.html',styleUrl:'./account-deletion.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class AccountDeletionComponent implements OnInit{
 private readonly api=inject(ApiService);private readonly auth=inject(AuthService);private readonly kundlis=inject(KundliStore);
 private readonly entitlements=inject(EntitlementService);private readonly store=inject(PurchaseService);
 /** A plan the store bills (sweep 2026-10-29 G-3): deleting the account cannot stop Google Play or the App Store charging, so say so first. */
 protected readonly storePlan=computed(()=>{const s=this.entitlements.current();if(!s||s.source!=='revenuecat'||s.access_tier==='free')return null;return s.access_tier==='pro'?'Practitioner':'Plus';});
 protected readonly storeName=Capacitor.getPlatform()==='ios'?'the App Store':'Google Play';
 ngOnInit(){void this.entitlements.refresh();}
 protected async manage(){const url=this.store.manageUrl();if(Capacitor.isNativePlatform())await Browser.open({url});else window.open(url,'_blank','noopener');}
 protected understood=false;protected confirmation='';protected readonly busy=signal(false);protected readonly error=signal<string|null>(null);
 protected async remove(){if(!this.understood||this.confirmation.trim().toUpperCase()!=='DELETE')return;this.busy.set(true);this.error.set(null);try{await this.api.deleteWithBody('/me',{confirmation:this.confirmation});this.kundlis.reset();try{sessionStorage.setItem(ACCOUNT_DELETED_FLAG,'1');}catch{/* the landing just won't say it */}await this.auth.signOut(['/m','start']);}catch(e){this.error.set((e as Error).message)}finally{this.busy.set(false)}}
}
