export function chinaDate(value=new Date()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(value));
 const get=type=>parts.find(p=>p.type===type).value;
 return `${get('year')}-${get('month')}-${get('day')}`;
}
export function releasesOn(released,date){return released.filter(f=>f.releasedAt&&chinaDate(f.releasedAt)===date);}
