"""Agent subtopics inferred from explicit title/abstract terms, separate from saved taxonomy."""
import re
RULES=[
 ('代码与软件智能体',r'coding agent|code agent|agentic cod|software agent|software engineer|program repair|code generation'),
 ('具身机器人与导航',r'robot|embodied|navigation|manipulation|autonomous driving'),
 ('工具与浏览器智能体',r'tool.use|tool.call|browser agent|web agent|computer.use|gui agent|api agent'),
 ('多智能体协作',r'multi.agent|agent collaboration|agent communication|agent society|agent coordination'),
 ('记忆与检索增强',r'agent.{0,20}memor|long.term memor|episodic memor|retrieval.augmented|\brag\b'),
 ('规划、推理与决策',r'planning|reasoning|decision.making|task decomposition|long.horizon|problem.solving'),
 ('科研与发现智能体',r'scientific discovery|research agent|agentic research|science agent|automated research|scientific agent'),
 ('医疗与健康智能体',r'medical|clinical|healthcare|diagnosis|patient'),
 ('教育与学习智能体',r'education|tutoring|student|teaching|pedagog'),
 ('智能体评测与基准',r'benchmark|evaluation|evaluating|assessment|test suite'),
 ('智能体学习与优化',r'reinforcement learning|self.evol|self.improv|agent training|policy optim|agent optim'),
 ('运行框架与基础设施',r'agent runtime|agent harness|agent operating system|agentos|\baios\b|orchestration|agent framework|agent infrastructure')]
# A personal feed scope, not deletion from the original library or archives.
AGENT_SCOPES={'agent','agent os','agent harness','agent security'}
BIO_TERMS=r'\b(?:biolog(?:y|ical)|biomedical|biomolecular|protein[s]?|ligand[s]?|drug[s]?|molecul(?:e|es|ar)|genom(?:e|es|ic|ics)|enzyme[s]?|peptide[s]?|therapeutic[s]?|clinical|healthcare|medical|patient[s]?)\b|predator.prey|\becolog(?:y|ical)\b|\bepidemi(?:c|cs|ology|ological)\b|\binfectious\b|\bcellular\b|生物学|蛋白质|药物|分子优化|基因组|捕食者|传染病'
def is_biology_paper(paper):
 title=' '.join(str(paper.get(k) or '') for k in ('title','titleEn','titleZh'))
 if re.search(BIO_TERMS,title,re.I):return True
 abstract=paper.get('summary') or ''
 return len(set(m.group().casefold() for m in re.finditer(BIO_TERMS,abstract,re.I)))>=2 and bool(re.search(r'protein (?:pocket|design|fold)|structure.based drug|drug (?:discovery|design)|molecular (?:optimization|generation|design)|基于.*药物设计',abstract,re.I))

def agent_feed_paper(paper):
 import paper_scope
 if paper_scope.reason(paper):return None
 if not is_biology_paper(paper):return paper
 topics=paper.get('topics',[])
 if not any(str(t).casefold() in AGENT_SCOPES for t in topics):return paper
 remaining=[t for t in topics if str(t).casefold() not in AGENT_SCOPES and t!='其他']
 if not remaining:return None
 return {**paper,'topics':remaining,'agentTopics':[]}

def agent_topics(paper):
 if is_biology_paper(paper):return []
 title=paper.get('title','').casefold();abstract=paper.get('summary','').casefold()
 if not any(str(t).casefold() in ('agent','agent os','agent harness') for t in paper.get('topics',[])) and not re.search(r'\bagents?\b|agentic',title+' '+abstract):return []
 result=[]
 for i,(name,pattern) in enumerate(RULES):
  field='title' if re.search(pattern,title) else 'abstract' if re.search(pattern,abstract) else None
  if field:result.append((0 if field=='title' else 1,i,{'name':name,'field':field}))
 return [r[2] for r in sorted(result)] or [{'name':'智能体综合','field':'topic'}]
