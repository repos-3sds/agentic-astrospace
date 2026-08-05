import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'as-ask-loading',
  standalone: true,
  template: `<header><span>‹</span><b>Ask</b></header><main><p class="question">{{ question }}</p><section><h2>Reading your chart…</h2><i></i><i></i><i></i></section><small>Computing from your dasha, gochara, and chart placements</small></main>`,
  styleUrl: './ask-loading.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AskLoadingComponent {
  private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  protected readonly question = this.route.snapshot.queryParamMap.get('q') ?? '';
  constructor(){void this.run();}
  private async run():Promise<void>{
    await new Promise((resolve) => setTimeout(resolve, 650));
    await this.router.navigate(['/m','ask','answer'],{queryParams:{q:this.question,preview:'construction'}});
  }
}
