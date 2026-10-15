import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { PreferencesService } from '../../../core/preferences.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BackBarComponent } from '../shared/back-bar.component';

@Component({selector:'as-mobile-search',standalone:true,imports:[BackBarComponent, FormsModule,RouterLink],templateUrl:'./search.component.html',styleUrl:'./utility.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class SearchComponent {
  // A signal, so results() recomputes as the reader types; a plain field
  // left the computed with no dependency and frozen at its first value.
  protected readonly query=signal('');
  private readonly preferences=inject(PreferencesService);
  private readonly allEntries=[
    ['Today guidance','Daily rhythm, practice and panchanga','/m/today','READINGS'],
    ['Ask history','Your saved questions','/m/ask/history','ASK'],
    ['Saturn transits','Gochara and current movement','/m/transits','TRANSITS'],
    ['Full transits','Aspects, vedha and strength','/m/transits/full','TRANSITS'],
    ['Life chapters','Vimshottari and Yogini dashas','/m/chart/periods','CHART'],
    ['Varga charts','D1, D9, D10 and divisional maps','/m/chart/vargas','CHART'],
    ['Muhurta','Find a supportive time','/m/muhurta','TOOLS'],
    ['Remedies','Practices and mantra tracker','/m/remedies','TOOLS'],
    ['Calendar','Panchanga, festivals and vrats','/m/calendar','TOOLS'],
    ['Family','Switch profiles, add a person','/m/family','TOOLS'],
    ['Compatibility','Ashta Koota matching','/m/compat','TOOLS'],
    ['Practitioner reference','Avkahada, grahas and tables','/m/chart/reference','REFERENCE'],
    ['Notes','Your private reflections','/m/notes','READINGS'],
  ];
  // Muhurta, Remedies and Calendar are Practitioner tools at launch (checklist D1).
  private readonly index=computed(()=>this.preferences.experienceMode()==='practitioner'?this.allEntries:this.allEntries.filter(row=>!['/m/muhurta','/m/remedies','/m/calendar'].includes(row[2])));
  protected readonly results=computed(()=>{const q=this.query().trim().toLowerCase();return q?this.index().filter(row=>`${row[0]} ${row[1]}`.toLowerCase().includes(q)):[];});
  protected readonly recent=signal<string[]>(JSON.parse(localStorage.getItem('astrospace.mobile.searches')||'[]'));
  protected groupResults(group:string):string[][]{return this.results().filter(row=>row[3]===group);}
  protected remember():void{const q=this.query().trim();if(q){const next=[q,...this.recent().filter(x=>x!==q)].slice(0,4);this.recent.set(next);localStorage.setItem('astrospace.mobile.searches',JSON.stringify(next));}}
}
