import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/api.service';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
@Component({selector:'as-account-deletion',standalone:true,imports:[FormsModule,RouterLink],templateUrl:'./account-deletion.component.html',styleUrl:'./account-deletion.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class AccountDeletionComponent{
 private readonly api=inject(ApiService);private readonly auth=inject(AuthService);private readonly kundlis=inject(KundliStore);
 protected understood=false;protected confirmation='';protected readonly busy=signal(false);protected readonly error=signal<string|null>(null);
 protected async remove(){if(!this.understood||this.confirmation.trim().toUpperCase()!=='DELETE')return;this.busy.set(true);this.error.set(null);try{await this.api.deleteWithBody('/me',{confirmation:this.confirmation});this.kundlis.reset();await this.auth.signOut(['/m','start']);}catch(e){this.error.set((e as Error).message)}finally{this.busy.set(false)}}
}
