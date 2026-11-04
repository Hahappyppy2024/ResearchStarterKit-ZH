export function titleParts(p={}){
 const title=String(p.title||p.paperTitle||'').trim(),chinese=/[\u4e00-\u9fff]/.test(title);
 return {title,titleZh:p.titleZh||(chinese?title:''),titleEn:p.titleEn||(!chinese?title:'')};
}
export function titleLabel(p){const t=titleParts(p);return [t.titleZh||'中文译名待生成',t.titleEn||'英文译名待生成'].join(' / ');}
