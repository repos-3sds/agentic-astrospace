import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../../core/api.service';
import { KundliStore } from '../../../core/kundli.store';
import { AskResponse } from '../../../core/models';
import { MobileAskStateService } from './mobile-ask-state.service';

@Component({
  selector: 'as-ask-loading',
  standalone: true,
  template: `<header><span>‹</span><b>Ask</b></header><main><p class="question">{{ question }}</p><section><h2>Reading your chart…</h2><i></i><i></i><i></i></section><small>Computing from your dasha, gochara, and chart placements</small></main>`,
  styleUrl: './ask-loading.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AskLoadingComponent {
  private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore); private readonly api = inject(ApiService);
  private readonly state = inject(MobileAskStateService);
  protected readonly question = this.route.snapshot.queryParamMap.get('q') ?? '';
  constructor(){void this.run();}
  private async run():Promise<void>{
    try{await this.kundlis.load();const p=this.kundlis.active();if(!p)throw new Error('Create a profile before asking.');
      const response=await this.api.post<AskResponse>(`/ask/${p.id}`,{question:this.question,start_thread:true,input_mode:'text'});this.state.remember(response);
      await this.router.navigate(['/m','ask',response.refer_out_kind?'refer':'answer'],{queryParams:{q:this.question,thread:response.thread_id??undefined,domain:response.refer_out_kind??undefined}});
    }catch(error){await this.router.navigate(['/m','ask'],{queryParams:{q:this.question,error:(error as Error).message}});}
  }
}
