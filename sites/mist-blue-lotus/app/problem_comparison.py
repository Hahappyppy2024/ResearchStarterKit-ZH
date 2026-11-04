"""Problem-led comparison using saved notes and explicitly confirmed memberships."""
import json,re
import study_service as study
import knowledge_service as knowledge
import lineage_service

# These are reading prompts matched only against titles, never paper findings.
PROMPTS=[
 ('small-detection','如何减少小目标、密集目标的漏检？','How can we reduce missed detections of small or crowded objects?',r'small.object|tiny.object|密集目标|小目标'),
 ('detection','如何准确定位并识别图像中的目标？','How can we accurately localize and recognize objects in images?',r'object detection|region.proposal|r-cnn|faster r|fast r|feature pyramid|you only look once|single shot multibox|focal loss|目标检测'),
 ('segmentation','如何准确分割图像中的对象与区域？','How can we accurately segment objects and regions in images?',r'segment|分割|u-net|fully convolutional'),
 ('injection','如何保护智能体免受提示注入攻击？','How can we protect agents against prompt injection attacks?',r'prompt injection|indirect injection|agentdojo|injecagent|提示注入'),
 ('agent-memory','如何让智能体可靠地记忆与检索信息？','How can agents reliably remember and retrieve information?',r'(?=.*(?:agent|智能体))(?=.*(?:memor|retriev|记忆|检索))'),
 ('agent-planning','如何提升智能体的推理、规划与决策能力？','How can we improve agent reasoning, planning and decision making?',r'(?=.*(?:agent|智能体|react:))(?=.*(?:reason|plan|decision|react:|推理|规划|决策))'),
 ('multi-agent','如何让多个智能体有效协作？','How can multiple agents collaborate effectively?',r'multi.agent|multiagent|多智能体'),
 ('gui-agent','如何让智能体可靠地操作界面与工具？','How can agents reliably operate interfaces and tools?',r'gui|computer.use|tool.call|web.agent|browser.agent|界面|工具调用'),
 ('visual-backbone','如何学习更有效的视觉特征？','How can we learn more effective visual representations?',r'residual learning|densely connected convolution|deep convolutional|very deep convolution|going deeper|mobilenet|efficientnet|视觉特征'),
 ('attention','如何建模长距离依赖与序列表示？','How can we model long-range dependencies and sequence representations?',r'attention is all|transformer|long.range depend|长距离依赖'),
 ('world-model','如何学习环境动力学并支持预测与规划？','How can we learn environment dynamics for prediction and planning?',r'world model|latent dynamics|dreamer|世界模型'),
 ('interpretability','如何解释模型的预测与内部机制？','How can we explain model predictions and internal mechanisms?',r'interpret|explain|shap|lime:|模型解释|可解释'),
 ('video-generation','如何生成连贯、可控的视频？','How can we generate coherent and controllable videos?',r'video generation|video diffusion|text.to.video|视频生成'),
]

def candidate_groups(papers):
 result=[]
 for ident,cn,en,pattern in PROMPTS:
  ids=[p['id'] for p in papers if re.search(pattern,p.get('title',''),re.I)]
  if ids:result.append(dict(id='suggested:'+ident,name=cn,en=en,paperIds=ids,suggested=True,definition='按论文题名关键词提出的阅读问题，需核对原文后确认；不代表这些论文的任务或实验设置完全一致。'))
 return sorted(result,key=lambda g:(-len(g['paperIds']),g['id']))

def task_values(tasks,datasets=None,figures=None):
 """Expose saved answers and structured entries, never infer missing content."""
 datasets=datasets or {};figures=figures or {};result={}
 for key,entry in tasks.items():
  if not isinstance(entry,dict):continue
  parts=[entry['answer']] if entry.get('answer') else []
  for item in entry.get('items',[]):
   if item.get('question'):parts.append('问题：'+item['question'])
   if item.get('answer'):parts.append('回答：'+item['answer'])
  for item in entry.get('problems',[]):
   parts.append(' / '.join(filter(None,[item.get('name'),item.get('en')]))+('；关键词：'+'、'.join(item['keywords']) if item.get('keywords') else ''))
  if entry.get('tags'):parts.append('标签：'+'、'.join(entry['tags']))
  for ident in entry.get('datasetIds',[]):
   item=datasets.get(ident,{})
   parts.append('数据集：'+(item.get('name') or ident)+(' / '+item['en'] if item.get('en') else ''))
  for ident in entry.get('figureIds',[]):
   item=figures.get(ident,{})
   parts.append('方法图：'+(item.get('caption') or item.get('name') or '已保存截图，请打开阅读任务查看'))
  if entry.get('comparisonPaperIds'):parts.append('已关联 '+str(len(entry['comparisonPaperIds']))+' 篇对比论文，可打开阅读任务查看。')
  result[key]='\n\n'.join(p for p in parts if p.strip())
 return result

def _data(map_id):
 maps=lineage_service.all_maps()['items']
 with study.connection() as c:
  records=study.records(c,'paper-knowledge')
  selected=study.records(c,'reading-library')
  syntheses=study.records(c,'problem-synthesis')
  datasets={r['id']:r for r in study.records(c,'dataset')}
  figures={r['id']:r for r in study.records(c,'paper-figure')}
 nodes=knowledge.taxonomy()['nodes']
 if map_id=='read-library':
  ids={p['id'] for p in records+selected}
  ids.update(i for m in maps for i in m['paperIds'])
 else:
  chosen=next((m for m in maps if m['id']==map_id),None)
  if not chosen:raise ValueError('当前分类不存在')
  ids=set(chosen['paperIds'])
 byid={p['id']:p for p in study.atlas_papers()}
 import local_app
 with local_app.db() as c:
  for ident in ids:
   found=c.execute('SELECT body FROM papers WHERE id=? AND paper_visible(body)=1',(ident,)).fetchone()
   if found:byid[ident]={**byid.get(ident,{}),**json.loads(found[0])}
   elif ident in byid:
    import paper_scope
    if paper_scope.reason(byid[ident]):byid.pop(ident,None)
 notes={p['id']:p for p in records};papers=[]
 for ident in ids:
  if ident not in byid:continue
  p=byid[ident];tasks=notes.get(ident,{}).get('tasks',{})
  answer=lambda key:tasks.get(key,{}).get('answer','')
  papers.append(dict(id=ident,title=p.get('title',''),titleZh=p.get('titleZh',''),year=p.get('year'),published=p.get('published',''),venue=p.get('venue',''),problem=answer('problem'),method=answer('solution') or answer('methodology'),evidence=answer('why'),limitations=answer('limitations'),hypothesis=answer('improvements'),settings=answer('reproduce'),source=p.get('pdf') or p.get('source',''),problemIds=notes.get(ident,{}).get('problemIds',[])))
  papers[-1]['taskValues']=task_values(tasks,datasets,figures)
 papers.sort(key=lambda p:(int(p['year']) if str(p.get('year','')).isdigit() else 9999,p.get('published') or '',p['title']))
 groups=[];known={p['id'] for p in papers}
 for m in maps:
  if m['kind']!='problem':continue
  node=next((n for n in nodes if (n.get('lineageId') or 'taxonomy-'+n['id'])==m['id']),None)
  members=set(m['paperIds']);node_ids={node['id']} if node else set()
  for _ in range(3):node_ids.update(n['id'] for n in nodes if n.get('parentId') in node_ids)
  members.update(p['id'] for p in papers if node_ids.intersection(p['problemIds']))
  members.intersection_update(known)
  if not members:continue
  groups.append(dict(id=m['id'],name=node['name'] if node else m['name'],en=node.get('en','') if node else '',paperIds=sorted(members),suggested=False,definition=m.get('description','')))
 assigned={i for g in groups for i in g['paperIds']}
 suggestions=candidate_groups([p for p in papers if p['id'] not in assigned])
 suggested_ids={i for g in suggestions for i in g['paperIds']}
 remaining=known-assigned-suggested_ids
 if remaining:suggestions.append(dict(id='ungrouped',name='尚未按具体问题归类',en='Not yet grouped by a specific research question',paperIds=sorted(remaining),suggested=False,unassigned=True,definition='这些论文尚无具体问题分组。先选几篇相关论文，再为它们建立中英文研究问题。'))
 definitions=json.loads((study.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
 return dict(papers=papers,groups=groups+suggestions,syntheses=syntheses,total=len(papers),unassigned=len(known-assigned),taskDefinitions=definitions)

def snapshot(map_id):return _data(map_id or 'read-library')

def confirm(data):
 cn=study.text(data.get('name',''),160);en=study.text(data.get('en',''),200)
 if not cn or not en:raise ValueError('请填写中英文研究问题')
 ids=data.get('paperIds',[])
 if not isinstance(ids,list) or len(ids)>1000 or any(not isinstance(i,str) for i in ids):raise ValueError('请最多选择 1000 篇论文')
 for ident in ids:study.resolve('paper',ident)
 nodes=knowledge.taxonomy()['nodes']
 node=next((n for n in nodes if n['kind']=='problem' and ((n.get('lineageId') or 'taxonomy-'+n['id'])==data.get('problemId') or n['name']==cn or n.get('en','').casefold()==en.casefold())),None)
 if data.get('problemId'):
  if not node or (node.get('lineageId') or 'taxonomy-'+node['id'])!=data['problemId']:raise ValueError('问题定义不存在，请重新打开')
  node=knowledge.save_node({**node,'name':cn,'en':en,'definition':study.text(data.get('definition',''),10000)})
 if not node:
  topic_ids=data.get('topicIds',[])
  scope=next((n for n in nodes if n['kind']=='topic' and (n.get('lineageId') or 'taxonomy-'+n['id'])==data.get('mapId')),None)
  if scope:topic_ids=list(dict.fromkeys(topic_ids+[scope['id']]))
  node=knowledge.save_node(dict(kind='problem',name=cn,en=en,definition=study.text(data.get('definition',''),10000),topicIds=topic_ids,parentId='',revision=0))
 ident=node.get('lineageId') or 'taxonomy-'+node['id']
 m=lineage_service.detail(ident)['map']
 lineage_service.save({**m,'paperIds':list(dict.fromkeys(m['paperIds']+ids))})
 return dict(id=ident,name=node['name'],en=node.get('en',''))

def save_synthesis(data):
 ident=study.text(data.get('id',''),200)
 with study.connection() as c:
  old=c.execute("SELECT body FROM records WHERE kind='problem-synthesis' AND id=?",(ident,)).fetchone()
  old=json.loads(old[0]) if old else dict(id=ident,revision=0)
  if data.get('revision',0)!=old['revision']:raise ValueError('另一窗口已更新，请先重新打开；当前文字仍保留')
  group=c.execute("SELECT body FROM records WHERE kind='lineage' AND id=? AND archived=0",(ident,)).fetchone()
  if not group or json.loads(group[0]).get('kind')!='problem':raise ValueError('请先确认问题分组，再保存对比结论')
  obj={**old,**{k:study.text(data.get(k,''),20000) for k in ('consensus','disagreement','gap','nextStep')},'revision':old['revision']+1,'updatedAt':study.now()}
  knowledge.put(c,'problem-synthesis',obj)
 return obj
