import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BackBarComponent } from '../shared/back-bar.component';

interface SearchEntry {
  title: string;
  detail: string;
  link: string;
  group: string;
  /** Words people search for that the title doesn't say. */
  keywords: string;
}

const ENTRIES: SearchEntry[] = [
  { title: 'Today guidance', detail: 'Daily rhythm, practice and panchanga', link: '/m/today', group: 'READINGS', keywords: 'score do avoid timing note listen audio rahu kalam yamaganda gulika abhijit tithi nakshatra vara' },
  { title: 'Readings', detail: 'Weekly, monthly and period readings', link: '/m/readings', group: 'READINGS', keywords: 'weekly monthly yearly outlook report' },
  { title: 'Notes', detail: 'Your private reflections', link: '/m/notes', group: 'READINGS', keywords: 'journal diary' },
  { title: 'Ask history', detail: 'Your saved questions', link: '/m/ask/history', group: 'ASK', keywords: 'past questions answers' },
  { title: 'Saturn transits', detail: 'Gochara and current movement', link: '/m/transits', group: 'TRANSITS', keywords: 'sade sati shani gochara jupiter guru rahu ketu' },
  { title: 'Full transits', detail: 'Aspects, vedha and strength', link: '/m/transits/full', group: 'TRANSITS', keywords: 'vedha aspects planets' },
  { title: 'Your chart', detail: 'D1 birth chart, signs and houses', link: '/m/chart', group: 'CHART', keywords: 'kundli horoscope lagna ascendant rising moon sign sun sign houses' },
  { title: 'Birth details', detail: 'Date, time and place of birth', link: '/m/chart/birth-details', group: 'CHART', keywords: 'birth time place date' },
  { title: 'Yogas & doshas', detail: 'Combinations and doshas in the chart', link: '/m/chart/yogas', group: 'CHART', keywords: 'manglik mangal kuja dosha kaal sarp yoga raja yoga' },
  { title: 'Life chapters', detail: 'Vimshottari and Yogini dashas', link: '/m/chart/periods', group: 'CHART', keywords: 'dasha mahadasha antardasha period' },
  { title: 'Varga charts', detail: 'D1, D9, D10 and divisional maps', link: '/m/chart/vargas', group: 'CHART', keywords: 'navamsa d9 dasamsa d10 divisional' },
  { title: 'Muhurta', detail: 'Find a supportive time', link: '/m/muhurta', group: 'TOOLS', keywords: 'auspicious time good time wedding marriage griha pravesha house warming travel journey venture contract' },
  { title: 'Remedies', detail: 'Practices and mantra tracker', link: '/m/remedies', group: 'TOOLS', keywords: 'mantra gemstone gem fasting puja charity' },
  { title: 'Calendar', detail: 'Panchanga, festivals and vrats', link: '/m/calendar', group: 'TOOLS', keywords: 'festival festivals vrat fast ekadashi amavasya purnima full moon new moon diwali deepavali navratri dussehra holi sankranti pongal ugadi shivaratri janmashtami ganesh chaturthi rahu kalam' },
  { title: 'Family', detail: 'Switch profiles, add a person', link: '/m/family', group: 'TOOLS', keywords: 'profiles people add person switch' },
  { title: 'Compatibility', detail: 'Ashta Koota matching', link: '/m/compat', group: 'TOOLS', keywords: 'match matching marriage partner kundli milan guna koota' },
  { title: 'Practitioner reference', detail: 'Avkahada, grahas and tables', link: '/m/chart/reference', group: 'REFERENCE', keywords: 'ashtakavarga avkahada grahas tables' },
  { title: 'Notifications', detail: 'Alerts you have received', link: '/m/notifications', group: 'SETTINGS', keywords: 'alerts inbox' },
  { title: 'Notifications and emails', detail: 'Morning brief, window alerts, email', link: '/m/settings/notifications', group: 'SETTINGS', keywords: 'push alerts reminders email brief quiet hours' },
  { title: 'City for timings', detail: 'The city your timings use', link: '/m/settings/location', group: 'SETTINGS', keywords: 'city place timezone' },
  { title: 'Language and voice', detail: 'Telugu, English and the voice', link: '/m/settings/language', group: 'SETTINGS', keywords: 'telugu english voice listen' },
  { title: 'Light or dark', detail: 'Light, dark or same as phone', link: '/m/settings/appearance', group: 'SETTINGS', keywords: 'dark mode light theme' },
  { title: 'Chart method', detail: 'Ayanamsha, nodes and chart style', link: '/m/settings/conventions', group: 'SETTINGS', keywords: 'conventions ayanamsha lahiri raman kp north south eastern rahu node' },
  { title: 'Festivals to show', detail: 'Essentials, North or South family festivals', link: '/m/settings/festivals', group: 'SETTINGS', keywords: 'festival calendar region vrat' },
  { title: 'Detail and tone', detail: 'Guided, Balanced or Practitioner; gentle or direct', link: '/m/settings/mode', group: 'SETTINGS', keywords: 'mode tone guided balanced practitioner experience' },
  { title: 'Vibration', detail: 'A light buzz on taps', link: '/m/settings/interaction', group: 'SETTINGS', keywords: 'haptics vibrate interaction' },
  { title: 'Plan and purchases', detail: 'Free, Plus and Practitioner', link: '/m/subscription', group: 'SETTINGS', keywords: 'subscription upgrade plus price pay' },
  { title: 'Account', detail: 'Plan, email, download your data, sign out, delete', link: '/m/settings/account', group: 'SETTINGS', keywords: 'sign out logout email password delete privacy' },
];

const GROUPS = ['READINGS', 'ASK', 'TRANSITS', 'CHART', 'TOOLS', 'REFERENCE', 'SETTINGS'];

/**
 * Search finds the screen for a thing, by its name or the words people use
 * for it ("Diwali" → Calendar, "Rahu Kalam" → Today). Until 2026-10-17 it
 * matched only feature names, so those searches found nothing (regression
 * R7). Anything it can't place is offered to Ask instead of a dead end.
 */
@Component({selector:'as-mobile-search',standalone:true,imports:[BackBarComponent, FormsModule,RouterLink],templateUrl:'./search.component.html',styleUrl:'./utility.component.scss',changeDetection:ChangeDetectionStrategy.OnPush})
export class SearchComponent {
  // A signal, so results() recomputes as the reader types; a plain field
  // left the computed with no dependency and frozen at its first value.
  protected readonly query=signal('');
  protected readonly groups=GROUPS;
  /** An empty Search opened blank (U31); these show what it can find. */
  protected readonly suggestions=['Rahu Kalam','Ekadashi','Diwali','Remedies','Compatibility','Dark mode'];
  protected readonly results=computed(()=>{
    const words=this.query().trim().toLowerCase().split(/\s+/).filter(Boolean);
    if(!words.length)return [];
    return ENTRIES.filter((row)=>{
      const text=`${row.title} ${row.detail} ${row.keywords}`.toLowerCase();
      return words.every((word)=>text.includes(word));
    });
  });
  protected readonly recent=signal<string[]>(readRecent());
  protected groupResults(group:string):SearchEntry[]{return this.results().filter(row=>row.group===group);}
  protected remember():void{const q=this.query().trim();if(q){const next=[q,...this.recent().filter(x=>x!==q)].slice(0,4);this.recent.set(next);try{localStorage.setItem('astrospace.mobile.searches',JSON.stringify(next));}catch{/* recents are a convenience */}}}
}

function readRecent(): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem('astrospace.mobile.searches') || '[]');
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [];
  } catch {
    return [];
  }
}
