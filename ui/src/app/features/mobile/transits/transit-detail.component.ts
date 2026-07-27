import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SheetComponent } from '../sheet/sheet.component';
export interface TransitDetail { planet:string; glyph:string; position:string; period:string; meaning:string; guidance:string; evidence:string[]; }
@Component({selector:'as-transit-detail',standalone:true,imports:[RouterLink,SheetComponent],template:`<as-sheet (dismissed)="dismissed.emit()"><header><span>{{detail().glyph}}</span><div><h2>{{detail().planet}}</h2><p>{{detail().period}}</p></div></header><h3>WHAT THIS MEANS FOR YOU</h3><article>{{detail().meaning}}</article><article>{{detail().guidance}}</article><h3>COMPUTED FROM</h3><ul>@for(row of detail().evidence;track row){<li>{{row}}</li>}</ul><a [routerLink]="['/m','ask']" [queryParams]="{q:'How does '+detail().planet+' affect me?'}">Ask about this transit</a></as-sheet>`,styleUrl:'./transit-detail.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class TransitDetailComponent { readonly detail=input.required<TransitDetail>(); readonly dismissed=output<void>(); }
