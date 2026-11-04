import {familyGroups} from './topic-families.mjs';
export function timelineLayout(papers,groups,date,collapsed=new Set()){
 const timed=papers.length>0&&papers.every(p=>p.publishedAt?.slice(0,10)===date&&Number.isFinite(Date.parse(p.publishedAt))),headers=[],rows=[],points=[];let y=18;
 for(const family of familyGroups(groups)){headers.push({...family,y,collapsed:collapsed.has(family.id)});y+=23;if(collapsed.has(family.id))continue;for(const group of family.groups){rows.push({...group,y,family:family.id});const items=papers.filter(p=>(p.direction||'')===group.name);items.sort((a,b)=>String(a.publishedAt||a.published).localeCompare(String(b.publishedAt||b.published))||a.id.localeCompare(b.id));items.forEach((paper,i)=>{const d=new Date(paper.publishedAt),fraction=timed?(d.getUTCHours()*60+d.getUTCMinutes())/1440:(i+.5)/items.length;points.push({paper,x:220+fraction*850,y:y+(items.length>65?(i%2?3:-3):0),color:group.color});});y+=24;}y+=8;}
 return {headers,rows,points,timed,height:y+26};
}
