// Dates are accepted only when explicitly supplied; never inferred from a biography.
export function researchTimeline(text=''){
 return String(text).split(/\n/).flatMap(line=>/^\s*(?:19|20)\d{2}.*[|｜:：]/.test(line)?[line]:line.split(/[；;]/)).map(s=>s.trim()).filter(Boolean).map((line,index)=>{
  const match=line.match(/^((?:19|20)\d{2}(?:\s*[–—-]\s*(?:19|20)\d{2})?)\s*[|｜:：]\s*(.+)$/);
  return {date:match?.[1]||'',text:match?.[2]||line,year:match?Number(match[1].slice(0,4)):null,index};
 }).sort((a,b)=>(a.year??Infinity)-(b.year??Infinity)||a.index-b.index);
}
