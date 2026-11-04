"""Explainable object-detection subtopics; title/abstract keyword suggestions only."""
import re
GROUPS=[('方法与任务','Methods and Tasks',[
('小目标与密集目标检测','Small and Dense Object Detection',r'small.object|tiny.object|dense.object|小目标|密集目标'),
('旋转目标与定向检测','Oriented Object Detection',r'oriented|rotated|rotation|旋转|定向'),
('开放词汇与开放世界检测','Open-vocabulary and Open-world Detection',r'open.vocabulary|open.world|开放词汇|开放世界'),
('少样本与零样本检测','Few-shot and Zero-shot Detection',r'few.shot|zero.shot|少样本|零样本'),
('实时轻量化与边缘部署','Real-time Lightweight and Edge Detection',r'real.time|lightweight|edge device|实时|轻量化'),
('三维与多模态检测','3D and Multimodal Detection',r'3d|lidar|point.cloud|multimodal|多模态|三维'),
('弱监督与半监督检测','Weakly and Semi-supervised Detection',r'weakly.supervised|semi.supervised|弱监督|半监督'),
('鲁棒性与域适应','Robustness and Domain Adaptation',r'robust|domain.adapt|domain.general|鲁棒|域适应')]),
('应用场景','Application Domains',[
('遥感与航拍目标检测','Remote Sensing and Aerial Detection',r'remote.sensing|aerial|satellite|遥感|航拍'),
('农业与生态目标检测','Agricultural and Ecological Detection',r'agricultur|crop|livestock|pest|农业|农作物|病虫害'),
('交通与自动驾驶检测','Traffic and Autonomous Driving Detection',r'autonomous.driv|traffic|pedestrian|自动驾驶|交通|行人'),
('工业缺陷与质量检测','Industrial Defect and Quality Detection',r'industrial|defect|surface inspection|工业|缺陷'),
('安防与公共安全检测','Surveillance and Public Safety Detection',r'surveillance|public.safety|安防|公共安全'),
('海事与水下目标检测','Maritime and Underwater Detection',r'maritime|underwater|ship.detect|海事|水下|船舶')]),
('军事与国防应用','Military and Defense Applications',[
('军事场景目标检测与识别','Military Scene Detection and Recognition',r'military|defense|defence|战场|军事|国防'),
('低空无人机与反无人机检测','Low-altitude UAV and Counter-UAV Detection',r'counter.uav|anti.drone|drone.detect|低空|反无人机'),
('红外与低光照目标检测','Infrared and Low-light Detection',r'infrared|thermal|low.light|红外|低光照'),
('SAR 雷达目标检测','SAR and Radar Target Detection',r'\bsar\b|synthetic.aperture.radar|radar.target|合成孔径|雷达'),
('伪装与遮挡目标检测','Camouflaged and Occluded Object Detection',r'camouflag|occlud|伪装|遮挡')])]
def detection_topics(paper):
 title=paper.get('title','');abstract=paper.get('summary','')
 if 'Object Detection' not in paper.get('topics',[]) and not re.search(r'object.detect|target.detect|目标检测',title,re.I):return []
 result=[]
 for group,en,items in GROUPS:
  for name,english,pat in items:
   field='title' if re.search(pat,title,re.I) else 'abstract' if re.search(pat,abstract,re.I) else None
   if field:result.append({'name':name,'group':group,'field':field})
 return sorted(result,key=lambda p:p['field']!='title') or [{'name':'目标检测综合','field':'topic'}]
