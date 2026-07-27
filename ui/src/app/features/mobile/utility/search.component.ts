import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

@Component({selector:'as-mobile-search',standalone:true,imports:[FormsModule,RouterLink],templateUrl:'./search.component.html',styleUrl:'./utility.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class SearchComponent {
  protected query='';
  protected readonly index=[
    ['Today reading','Daily guidance and panchanga','/m/today','READINGS'],
    ['Ask history','Your saved questions','/m/ask/history','ASK'],
    ['Saturn transits','Gochara and current movement','/m/transits','TRANSITS'],
    ['Full transits','Aspects, vedha and strength','/m/transits/full','TRANSITS'],
    ['Life periods','Vimshottari and Yogini dashas','/m/chart/periods','CHART'],
    ['Divisional charts','D1, D9, D10 and vargas','/m/chart/vargas','CHART'],
    ['Muhurta','Find a suitable time','/m/muhurta','TOOLS'],
    ['Compatibility','Ashta Koota matching','/m/compat','TOOLS'],
    ['Practitioner reference','Avkahada, grahas and tables','/m/chart/reference','REFERENCE'],
    ['Notes','Your private chart notes','/m/notes','READINGS'],
  ];
  protected readonly results=computed(()=>{const q=this.query.trim().toLowerCase();return q?this.index.filter(row=>`${row[0]} ${row[1]}`.toLowerCase().includes(q)):[];});
  protected readonly recent=signal<string[]>(JSON.parse(localStorage.getItem('astrospace.mobile.searches')||'[]'));
  protected groupResults(group:string):string[][]{return this.results().filter(row=>row[3]===group);}
  protected remember():void{const q=this.query.trim();if(q){const next=[q,...this.recent().filter(x=>x!==q)].slice(0,4);this.recent.set(next);localStorage.setItem('astrospace.mobile.searches',JSON.stringify(next));}}
}
