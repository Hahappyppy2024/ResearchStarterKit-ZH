import {sortTopics,compareTopics} from './topic-sort.mjs';
import taxonomy from './research-taxonomy.json' with {type:'json'};
// Root labels and children are shared with the Python library classifier.
export const TOPIC_FAMILIES=taxonomy.roots.map(r=>({id:r.id,name:r.name,color:r.color,palette:Array.from({length:8},(_,i)=>{const rgb=[1,3,5].map(at=>parseInt(r.color.slice(at,at+2),16));return '#'+rgb.map(v=>Math.round(v+(255-v)*i*.065).toString(16).padStart(2,'0')).join('')}),colorTopics:r.subtopics.map(s=>s.name),topics:sortTopics(r.subtopics.map(s=>s.name))})).sort(compareTopics);
export function topicFamily(name){name=taxonomy.aliases[name]||name;return TOPIC_FAMILIES.find(f=>f.topics.includes(name))||TOPIC_FAMILIES.find(f=>f.id==='other');}
export function topicColor(name){name=taxonomy.aliases[name]||name;const family=topicFamily(name),i=family.colorTopics.indexOf(name);if(i>=0)return family.palette[i%family.palette.length];let hash=0;for(const c of name)hash=(hash*31+c.charCodeAt(0))>>>0;return family.palette[hash%family.palette.length];}
export function familyGroups(groups){return TOPIC_FAMILIES.map(f=>({...f,groups:sortTopics(groups.filter(g=>topicFamily(g.name).id===f.id))})).filter(f=>f.groups.length).map(f=>({...f,count:f.groups.reduce((n,g)=>n+g.count,0)}));}
