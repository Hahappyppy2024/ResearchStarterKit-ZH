// Merge server-generated cards without overwriting edits made while a save was in flight.
export function mergeAutoCards(target,submitted,saved){
 if(!target?.flashcards)return;
 const base=new Map((submitted?.flashcards?.items||[]).map(c=>[c.id,c])),incoming=new Map((saved?.flashcards?.items||[]).map(c=>[c.id,c]));
 const same=(a,b)=>a?.question===b?.question&&a?.answer===b?.answer;
 const list=target.flashcards.items||[];
 const merged=list.filter(c=>!base.has(c.id)||incoming.has(c.id)||!same(c,base.get(c.id)));
 for(const card of incoming.values()){
  const live=merged.find(c=>c.id===card.id);
  if(live&&base.has(card.id)&&same(live,base.get(card.id)))Object.assign(live,card);
  else if(!live&&!base.has(card.id)&&merged.length<100)merged.push({...card});
 }
 target.flashcards.items=merged;
}
