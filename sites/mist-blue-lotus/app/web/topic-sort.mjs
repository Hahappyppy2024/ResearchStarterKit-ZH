const collator=new Intl.Collator('zh-Hans-CN-u-co-pinyin',{numeric:true,sensitivity:'base'});
const labels={'Agent / LLM':'智能体与大语言模型',AIGC:'生成式人工智能','Agentic RL 系统':'智能体强化学习系统','仓库级 Agent':'仓库级智能体','VLA 与世界模型':'视觉语言动作与世界模型','BEV 与规划':'鸟瞰表征与规划'};
export const topicSortName=value=>labels[value]||value||'';
export function compareTopics(a,b){return collator.compare(topicSortName(typeof a==='string'?a:a.name),topicSortName(typeof b==='string'?b:b.name));}
export const sortTopics=items=>[...items].sort(compareTopics);
