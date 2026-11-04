"""Private project folder tree and Markdown notes."""
import json,uuid
import projects_service as service

def records(c,project):
 return [json.loads(r[0]) for r in c.execute('SELECT body FROM project_notes WHERE project_id=? ORDER BY rowid',(project,))]
def put(c,item):
 c.execute('INSERT INTO project_notes VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(item['id'],item['projectId'],json.dumps(item,ensure_ascii=False)))
def listing(project):
 with service.connection() as c:
  p=service.get_row(c,'projects',project);items=records(c,project)
  if not items and p.get('projectNotes') and not p.get('notesTreeMigrated'):
   item=dict(id=str(uuid.uuid4()),projectId=project,parentId='',kind='note',title='原有项目笔记',content=p['projectNotes'],revision=1);put(c,item);items.append(item)
  if not p.get('notesTreeMigrated'):
   p['notesTreeMigrated']=True;c.execute('UPDATE projects SET body=? WHERE id=?',(json.dumps(p,ensure_ascii=False),project))
 return {'items':[i for i in items if not i.get('deleted')],'trash':[i for i in items if i.get('deleted')]}
def save(data):
 project=data.get('projectId','')
 with service.connection() as c:
  service.get_row(c,'projects',project);items=records(c,project);byid={i['id']:i for i in items};old=byid.get(data.get('id'))
  if data.get('id') and old is None:raise ValueError('笔记不存在')
  if old and data.get('revision')!=old['revision']:raise ValueError('笔记已更新，请刷新后重试；当前草稿仍保留')
  action=data.get('action')
  if action in ('delete','restore'):
   if old is None:raise ValueError('请选择已有笔记或文件夹')
   if action=='delete':
    ids={old['id']};size=-1
    while size!=len(ids):
     size=len(ids)
     ids.update(i['id'] for i in items if i.get('parentId') in ids and not i.get('deleted'))
    batch=str(uuid.uuid4())
    for entry in items:
     if entry['id'] in ids and not entry.get('deleted'):
      entry.update(deleted=True,deleteBatch=batch,revision=entry['revision']+1,updatedAt=service.now());put(c,entry)
   else:
    batch=old.get('deleteBatch')
    restoring={i['id'] for i in items if i.get('deleted') and (i['id']==old['id'] or batch and i.get('deleteBatch')==batch)}
    for entry in items:
     if entry['id'] in restoring:
      if entry.get('parentId') and (entry['parentId'] not in byid or byid[entry['parentId']].get('deleted') and entry['parentId'] not in restoring):entry['parentId']=''
      entry.update(deleted=False,revision=entry['revision']+1,updatedAt=service.now());put(c,entry)
   return {'ok':True}
  if old and old.get('deleted'):raise ValueError('请先从回收站恢复')
  item=dict(old) if old else dict(id=str(uuid.uuid4()),projectId=project,revision=0)
  parent=service.text(data.get('parentId',item.get('parentId','')),100)
  if parent and (parent not in byid or byid[parent]['kind']!='folder' or byid[parent].get('deleted')):raise ValueError('请选择本项目的文件夹')
  cursor=parent
  while cursor:
   if cursor==item['id']:raise ValueError('文件夹不能放入自身或子文件夹')
   cursor=byid[cursor].get('parentId','')
  kind=data.get('kind',item.get('kind','note'))
  if kind not in ('folder','note') or old and kind!=old['kind']:raise ValueError('类型无效')
  title=service.text(data.get('title',item.get('title','')),160).strip()
  if not title:raise ValueError('请填写名称')
  item.update(parentId=parent,kind=kind,title=title,content=service.text(data.get('content',item.get('content','')),1000000),revision=item['revision']+1,updatedAt=service.now())
  put(c,item)
 return item
