export function publicationGroup(p={},association={}){
 if(association.publicationStatus==='published')return 'published';
 if(association.publicationStatus==='preprint')return 'preprint';
 if(association.publicationStatus==='unknown')return 'unknown';
 const venue=String(p.publicationVenue||p.journalRef||p.journal_ref||p.venue||'').trim();
 if(p.conference===true||venue&&!/arxiv|preprint|自选论文|^self$|未发表|待核实/i.test(venue))return 'published';
 if(/^arxiv-/i.test(p.id||'')||/arxiv\.org/.test(p.source||p.arxivUrl||'')||/arxiv|preprint/i.test(venue))return 'preprint';
 return 'unknown';
}
export function authorMatches(p,person){const authors=Array.isArray(p.authors)?p.authors:String(p.authors||'').split(/[,;，；]/);const names=[person.name,person.en].filter(Boolean).map(s=>s.trim().toLowerCase());return authors.some(a=>names.includes(a.trim().toLowerCase()));}
