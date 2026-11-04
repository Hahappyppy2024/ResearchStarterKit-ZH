"""Daily concrete research exercises. Stable assignments and self-reported outputs."""
import contextlib,datetime as dt,json,pathlib,re,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parent;DB=ROOT/'local-data'/'research-practice.sqlite'
TZ=dt.timezone(dt.timedelta(hours=8))
def today():return dt.datetime.now(TZ).date().isoformat()
def now():return dt.datetime.now(TZ).isoformat()
def valid_date(value):
 try:d=dt.date.fromisoformat(value)
 except (ValueError,TypeError):raise ValueError('日期无效')
 if value!=d.isoformat():raise ValueError('日期格式无效')
 return d
@contextlib.contextmanager
def connection():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with contextlib.closing(sqlite3.connect(DB,timeout=30)) as c,c:
  c.execute('CREATE TABLE IF NOT EXISTS plans(date TEXT PRIMARY KEY,body TEXT NOT NULL)')
  yield c

TEMPLATES=[
 [('问题卡','把研究问题写成可验证的一句话',15,['写清研究对象、使用场景和具体失败现象。','列出当前方法为何可能失败；未知处标为猜想。','指定一个评价指标及对照方案。'],'一张问题卡：现象、问题、已有解释、尚缺证据、评价指标。'),('分层阅读','筛读一篇论文并决定是否精读',20,['第一遍只看标题、摘要、引言和主要图表。','写出问题、核心方法和支持结论的证据位置。','决定：跳过、留作背景、精读或复现，并说明理由。'],'150 字以内的阅读决策，附一处页码或图表编号。'),('主动回忆','闭卷解释今天的方法',10,['关闭论文和笔记，用自己的话解释输入、输出和核心步骤。','回答为什么这些步骤可能解决问题。','重新核对原文，补写两处遗漏或误解。'],'一段闭卷解释＋核对后的修订；不要直接复制摘要。')],
 [('对比阅读','比较两篇论文如何解决同一问题',25,['先确认两篇论文的任务和评价条件是否可比。','对照假设、方法、数据、指标、计算代价和局限。','指出一处无法直接比较的条件。'],'至少 5 行的对比表；不适用的项说明原因。'),('论文脉络','画出问题到方法的关系链',15,['从引言找出两篇被引用的前作。','记录每篇前作的具体问题，以及当前论文继承、改进或质疑的内容。','区分作者明确表述和自己的推测，附引用位置。'],'一条“前作问题 → 方法 → 剩余问题 → 当前改进”的关系链。'),('机制解释','解释一个模块为何有效',15,['选一个与你项目有关的模块。','写出关键假设、信息流和预期作用。','给出一个假设不成立时可能失败的例子。'],'一段机制解释或小图，包含一个反例或边界条件。')],
 [('预测后验证','设计一个能被推翻的实验假设',15,['从当前项目中选一个明确问题。','只提出一个改动，写下它预期改善的指标。','事先写明什么结果支持假设、什么结果会推翻假设。'],'假设、唯一改动、对照、指标、支持条件和推翻条件。'),('最小复现','复现一个核心模块或最小示例',30,['从参考论文中选一个模块、公式或最小输入输出示例。','先写测试输入和预期输出，再实现或运行公开代码。','记录命令、代码版本、环境和实际结果；运行失败也保留。'],'可运行代码或脚本路径＋一个输入输出例子＋实际运行记录。'),('证据记录','解释结果是否支持原来的判断',10,['对照预期与实际结果，列出支持和不支持的证据。','区分程序没跑通、指标未改善和假设被推翻。','写下最小的下一步核验动作。'],'一段基于证据的结论；没有结果时写清执行阻塞及下一步。')],
 [('核验对照','检查 baseline 是否可信',20,['检查数据划分、预处理和评价脚本是否一致。','记录 baseline 的代码版本、配置、随机种子和结果来源。','找出一项可能影响公平比较的差异。'],'一张 baseline 核验清单，附配置或日志路径。'),('消融设计','设计一次只改变一个因素的对照',20,['选一个模块或训练因素，其他条件保持一致。','写出至少一组 baseline 和一组改动配置。','写明指标、重复运行计划和计算预算。'],'两行对照配置表＋评价指标＋可接受的实验预算。'),('失败分析','分析三个失败样本',15,['选三个失败案例；若尚无预测结果，先列出需要采集的案例类型。','按现象分类，提出候选原因，不把猜测写成事实。','为一个原因设计可区分它与其他原因的检查。'],'三个样本或案例类型、候选原因及一个区分性检查。')],
 [('边界条件','寻找方法不适用的场景',15,['读论文的局限、实验设置和失败案例。','列出两项与你项目不同的前提或数据条件。','为其中一项设计一个小型压力测试。'],'两项适用边界＋一个可操作的小测试。'),('代码理解','手写一个关键模块并标注维度',25,['选择 Attention、IoU、FPN 的一个步骤或项目中的实际模块。','不用照抄代码，先写输入输出形状和伪代码。','补充正常输入和边界输入各一个测试。'],'伪代码或代码路径、张量形状和两个测试案例。'),('讲解练习','准备三分钟讲解',15,['用三段说明：问题、方法、证据与局限。','不用术语替代解释，说明每个关键步骤的目的。','列出一个你仍不能回答的追问。'],'一页讲解提纲或录音路径＋一个待解决问题。')],
 [('综合整理','整理本周论文的共识与分歧',20,['选本周最相关的三篇；不足三篇则使用已有论文。','找出一个共同问题和两处方法或结论差异。','检查差异是否来自不同数据、指标或假设。'],'一页综合笔记，明确哪些判断已有证据、哪些仍待核实。'),('成果输出','做三页可复用的研究 slides',25,['第一页：研究问题及其重要性。','第二页：方法对比或核心机制图。','第三页：证据、局限与下一步。'],'三页 slides 的文件路径或每页提纲，并附论文出处。'),('模拟讨论','给自己的研究提出三个追问',10,['分别从假设、实验公平性和适用边界提出一个问题。','先尝试回答，再列出缺少的证据。','选一个追问放入下一次阅读或实验任务。'],'三个追问、当前回答和一个下一步验证动作。')],
 [('每周复盘','总结本周解决了什么问题',20,['查看本周论文笔记和实验记录。','只根据实际记录列出已解决、部分解决和未解决的问题。','每个“已解决”都附一个证据位置；没有成果就如实记录。'],'四项复盘：解决了什么、证据是什么、还不懂什么、下周验证什么。'),('知识检验','闭卷重讲本周最重要的两个概念',15,['选两个概念，关闭资料后解释机制和适用条件。','各做一道例题或给一个应用案例。','核对后记录遗漏，加入你自己的闪卡。'],'两段闭卷解释、例题或案例，以及修正后的要点。'),('下周计划','确定下周三个优先任务',15,['优先选择正在阻塞项目的问题。','为三个任务分别写目标、具体动作和完成标准。','至少保留一个用于否定或修正当前方案的验证。'],'三个按优先级排序的任务，可逐一加入每日努力。')]
]

def context(date):
 import projects_service,weekly_arxiv
 projects=projects_service.list_projects();project=next((p for p in projects if p.get('status') not in ('done','completed')),None)
 week=(valid_date(date)-dt.timedelta(days=valid_date(date).weekday()+7)).isoformat()
 data=weekly_arxiv.get_week(week);papers=data['papers'];name=project.get('name','') if project else ''
 terms=[]
 for zh,topic in [('检测','Object Detection'),('农业','农业遥感检测'),('agent','Agent'),('安全','Agent Security'),('视频','Video Understanding')]:
  if zh in name.lower():terms.append(topic)
 papers.sort(key=lambda p:(-sum(t in p.get('topics',[]) for t in terms),p.get('id','')))
 offset=(valid_date(date)-dt.date(2026,10,19)).days
 relevant=[p for p in papers if any(t in p.get('topics',[]) for t in terms)] or papers
 chosen=[]
 for i in range(min(2,len(relevant))):
  p=relevant[(offset+i)%len(relevant)];chosen.append({k:p.get(k,'') for k in ('id','title','pdf','source')})
 return {'project':{k:project.get(k,'') for k in ('id','name','problem','goal')} if project else None,'papers':chosen,'week':week,'selectionNote':'参考论文按项目方向轮换推荐，实际相关性请先筛读；也可使用你已读的核心论文并记录出处。'}

def get_day(date=None):
 date=date or today();d=valid_date(date)
 with connection() as c:
  row=c.execute('SELECT body FROM plans WHERE date=?',(date,)).fetchone()
  if row:return json.loads(row[0])
 if date<today():return dict(date=date,tasks=[],note='该日没有已派发记录，不补造历史任务。')
 ctx=context(date);tasks=[]
 for i,(method,title,minutes,steps,output) in enumerate(TEMPLATES[d.weekday()]):
  tasks.append(dict(id=f'research-{date}-{i+1}',method=method,title=title,minutes=minutes,steps=steps,output=output,content='',status='todo',revision=1))
 plan=dict(date=date,createdAt=now(),context=ctx,tasks=tasks,note='默认每日 3 项；完成由你自评，参考论文可以替换。计时为建议，不会改变固定日程。')
 with connection() as c:
  c.execute('INSERT OR IGNORE INTO plans VALUES(?,?)',(date,json.dumps(plan,ensure_ascii=False)))
  return json.loads(c.execute('SELECT body FROM plans WHERE date=?',(date,)).fetchone()[0])

def save_task(data):
 date=data.get('date');valid_date(date)
 with connection() as c:
  row=c.execute('SELECT body FROM plans WHERE date=?',(date,)).fetchone()
  if not row:raise ValueError('请先打开当天练习')
  plan=json.loads(row[0]);task=next((t for t in plan['tasks'] if t['id']==data.get('id')),None)
  if not task:raise ValueError('练习不存在')
  if data.get('revision')!=task['revision']:raise ValueError('记录已在其他窗口更新，请刷新后再保存；当前草稿仍保留。')
  content=data.get('content',task['content']);status=data.get('status',task['status'])
  if not isinstance(content,str) or len(content)>50000 or status not in ('todo','doing','done','deferred'):raise ValueError('成果或状态格式无效')
  if status=='done' and not content.strip():raise ValueError('请先记录成果、文件路径或实际执行结果，再自评完成。')
  task.update(content=content,status=status,revision=task['revision']+1,updatedAt=now())
  c.execute('UPDATE plans SET body=? WHERE date=?',(json.dumps(plan,ensure_ascii=False),date));return task

if __name__=='__main__':
 if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 print(json.dumps(get_day(),ensure_ascii=False))
