export function categoriesForTopic(nodes,topicId,kind){
 const byId=new Map(nodes.map(n=>[n.id,n])),topicIds=new Set([topicId]);
 for(let i=0;i<nodes.length;i++)for(const n of nodes)if(n.kind==='topic'&&topicIds.has(n.parentId))topicIds.add(n.id);
 return nodes.filter(n=>{if(n.kind!==kind)return false;const seen=new Set();while(n&&!seen.has(n.id)){seen.add(n.id);if((n.topicIds||[]).some(id=>topicIds.has(id)))return true;n=byId.get(n.parentId);}return false;});
}
export function timelineEntries(details){
 const papers=new Map();for(const {category,papers:items} of details)for(const p of items){
  if(!papers.has(p.id))papers.set(p.id,{...p,categories:[]});papers.get(p.id).categories.push(category);
 }
 return [...papers.values()].map(p=>{const raw=p.published||p.date||'',match=String(raw).match(/^(\d{4})(?:-(\d{2})-(\d{2}))?/),year=Number(p.year)||0;return {...p,time:match?match[0]:year?String(year):'',sortDate:match?match[0]:year?String(year):'9999'};}).sort((a,b)=>a.sortDate.localeCompare(b.sortDate)||a.title.localeCompare(b.title));
}
