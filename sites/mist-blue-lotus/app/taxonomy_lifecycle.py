"""Recoverable removal of unused leaf classifications."""
import json
import study_service as study

def _reason(c,node):
 items=study.records(c,'taxonomy')
 if any(n.get('parentId')==node['id'] for n in items):return '这个分类还有子分类，请先整理子分类。'
 ident=node.get('lineageId') or 'taxonomy-'+node['id']
 raw=c.execute("SELECT body FROM records WHERE kind='lineage' AND id=?",(ident,)).fetchone()
 if raw:
  m=json.loads(raw[0])
  if m.get('paperIds') or m.get('paths'):return '这个分类仍有论文或阅读路径，暂不能作为空分类移走。'
 key={'topic':'topicIds','problem':'problemIds','solution':'solutionIds'}[node['kind']]
 for kind in ('paper-knowledge','dataset'):
  if any(node['id'] in r.get(key,[]) for r in study.records(c,kind)):return '这个分类仍被论文或数据集使用，请先调整关联。'
 if any(node['id'] in n.get('topicIds',[]) for n in items):return '这个分类仍关联问题或方法，请先调整关联。'
 return ''

def status(ident):
 with study.connection() as c:
  node=study.row(c,'taxonomy',ident);reason=_reason(c,node)
 return dict(canArchive=not reason,reason=reason or '没有论文、子分类或其他关联，可以移入回收站。')

def archived():
 with study.connection() as c:return dict(items=study.records(c,'taxonomy',True))

def archive(data):
 ident=data.get('id');restore=data.get('restore') is True
 with study.connection() as c:
  node=study.row(c,'taxonomy',ident)
  if data.get('revision') is not None and data['revision']!=node['revision']:raise ValueError('分类已更新，请重新打开后再操作。')
  if restore:
   active={n['id'] for n in study.records(c,'taxonomy')}
   if node.get('parentId') and node['parentId'] not in active:raise ValueError('请先恢复它的父分类。')
   if any(n['id']!=ident and n['kind']==node['kind'] and n.get('parentId')==node.get('parentId') and (n['name'].casefold()==node['name'].casefold() or n.get('en','').casefold()==node.get('en','').casefold()) for n in study.records(c,'taxonomy')):raise ValueError('已有同名分类，请先整理名称后再恢复。')
  else:
   reason=_reason(c,node)
   if reason:raise ValueError(reason)
  c.execute("UPDATE records SET archived=? WHERE kind='taxonomy' AND id=?",(int(not restore),ident))
  c.execute("UPDATE records SET archived=? WHERE kind='lineage' AND id=?",(int(not restore),node.get('lineageId') or 'taxonomy-'+ident))
 return dict(saved=True,restored=restore)
