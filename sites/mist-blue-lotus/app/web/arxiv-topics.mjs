import sharedTaxonomy from './research-taxonomy.json' with {type:'json'};
export function sharedTopicNodes(custom=[]){const alias=new Map(sharedTaxonomy.roots.flatMap(r=>(r.legacyIds||[]).map(id=>[id,r.id])));return [...sharedTaxonomy.roots.flatMap(r=>[{id:r.id,name:r.name,kind:'topic',parentId:null,auto:true,legacyIds:r.legacyIds||[]},...r.subtopics.map(t=>({id:r.id+':'+t.id,name:t.name,kind:'topic',parentId:r.id,auto:true}))]),...custom.filter(n=>!alias.has(n.id)).map(n=>({...n,parentId:alias.get(n.parentId)||n.parentId}))];}
// Topic identities and explicit paper memberships come from Paper Atlas.
export function topicIndex(nodes,maps,papers){
 const topics=nodes.filter(n=>n.kind==='topic'),byId=new Map(topics.map(n=>[n.id,n])),members=new Map(topics.map(n=>[n.id,new Set()]));
 const normalize=s=>String(s||'').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
 const aliases=n=>[n.id,n.name,n.en,n.id.replace(/^tax-/,''),...((n.name==='Agent / LLM')?['Agent','LLM','智能体']:[])].filter(Boolean).map(normalize);
 for(const n of topics){const nodeIds=[n.id,...(n.legacyIds||[])],related=maps.filter(m=>m.id===(n.lineageId||'taxonomy-'+n.id)||nodeIds.some(id=>m.id==='taxonomy-'+id||m.topicId===id)),explicit=new Set(related.flatMap(m=>m.paperIds||[])),names=new Set(aliases(n));for(const p of papers){if((p.researchTopics||[]).some(t=>t.id===n.id||t.parentId===n.id)||explicit.has(p.id)||nodeIds.some(id=>(p.topicIds||[]).includes(id))||(!p.autoClassification&&(p.topics||[]).some(t=>names.has(normalize(t)))))members.get(n.id).add(p.id)}}
 // Parents include descendants. Cycle guards protect malformed imported trees.
 for(const n of topics){let parent=n.parentId,seen=new Set([n.id]);while(parent&&byId.has(parent)&&!seen.has(parent)){seen.add(parent);for(const id of members.get(n.id))members.get(parent).add(id);parent=byId.get(parent).parentId}}
 const classified=new Set(topics.filter(n=>!n.auto||(n.id!=='other'&&n.parentId!=='other')).flatMap(n=>[...members.get(n.id)]));
 return {topics,members,unclassified:new Set(papers.filter(p=>!classified.has(p.id)).map(p=>p.id))};
}
