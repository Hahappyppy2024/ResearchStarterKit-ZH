"""Local source-linked Q/A cards; split notes without inventing or summarizing facts."""
import re,uuid
PROMPTS={'methodology':'方法图的流程是什么？','problem':'这篇论文解决什么问题？','solution':'用了什么方法？','why':'为什么这个方法有效？','limitations':'这个方法有什么局限？','improvements':'如何改进这些局限？','related':'相关论文有哪些？','affiliations':'作者来自哪些单位？','categories':'这篇论文属于什么方向？','compare':'与对比论文有什么区别？','code-map':'代码的数据流是什么？','code-trace':'核心模块的输入输出是什么？','minimal-run':'最小例子如何运行？','reproduce':'对照实验如何设计？','recall':'这篇论文的核心内容是什么？','next-step':'下一步做什么？','background':'应用场景是什么？','datasets':'用了哪些数据集？','reading-questions':'阅读时遇到了什么问题？','extensions':'还能研究哪些新问题？'}

def pieces(text):
 lines=[re.sub(r'^\s*(?:[-*•]|\d+[.、)])\s*','',s).strip() for s in text.splitlines() if s.strip()]
 result=[]
 for line in lines:
  result.extend(s.strip() for s in re.split(r'(?<=[。！？])\s*|(?<=[.!?])\s+(?=[A-Z\u4e00-\u9fff])',line) if s.strip())
 return result

def candidates(tasks,definitions):
 result=[]
 def add(source,question,answer):
  if question.strip() and answer.strip():result.append(dict(source=source,question=question.strip(),answer=answer.strip()))
 for task in definitions:
  key=task['id']
  if key=='flashcards':continue
  entry=tasks.get(key,{})
  values=pieces(entry.get('answer',''))
  for i,text in enumerate(values):add(key+':answer:'+str(i),PROMPTS.get(key,task['title']+'？')+('（要点 '+str(i+1)+'）' if len(values)>1 else ''),text)
  if key=='reading-questions':
   for item in entry.get('items',[]):
    values=pieces(item.get('answer',''))
    for i,text in enumerate(values):add(key+':'+item['id']+':'+str(i),item['question']+('（要点 '+str(i+1)+'）' if len(values)>1 else ''),text)
  if key=='extensions':
   for item in entry.get('items',[]):add(key+':'+item['id'],'还能研究什么新问题？',item['question'])
  if key=='next-step':
   for problem in entry.get('problems',[]):
    add(key+':'+problem['id'],'问题“'+problem.get('name','')+'”用什么关键词检索？','；'.join(problem.get('keywords',[])))
 return result

def sync(paper_id,tasks,old,definitions,extra=()):
 state=tasks['flashcards'];incoming={i['id']:i for i in state.get('items',[])};previous=old.get('autoFlashcardLinks',{});links={};manual=[]
 for ident,item in incoming.items():
  prior=previous.get(ident)
  if not prior:manual.append(item);continue
  changed=prior.get('manual') or (item['question'],item['answer'])!=(prior['question'],prior['answer'])
  if changed:manual.append(item);links[ident]={**prior,'manual':True,'dismissed':False}
 for ident,prior in previous.items():
  if ident not in incoming:links[ident]={**prior,'dismissed':True}
 generated=[];seen={(i['question'],i['answer']) for i in manual};overflow=0
 for candidate in candidates(tasks,definitions)+list(extra):
  ident='item-'+str(uuid.uuid5(uuid.NAMESPACE_URL,paper_id+':'+candidate['source']));prior=previous.get(ident)
  if ident in links and links[ident].get('manual'):continue
  if prior and ident not in incoming and prior.get('dismissed',False):links[ident]=prior;continue
  if prior and ident not in incoming:links[ident]={**prior,'dismissed':True};continue
  pair=(candidate['question'],candidate['answer'])
  if pair in seen:continue
  if len(manual)+len(generated)>=100:overflow+=1;continue
  seen.add(pair);generated.append(dict(id=ident,question=candidate['question'],answer=candidate['answer']));links[ident]={**candidate,'manual':False,'dismissed':False}
 state['items']=manual+generated
 return dict(autoFlashcardLinks=links,autoFlashcardOverflow=overflow)
