"""Shared video tracking queries and explainable multi-label matching."""
import re
RULES=[
 ('Video Editing','视频编辑',r'video edit|video inpaint|video styliz|video style transfer|video object remov',
  'all:"video editing" OR all:"video inpainting" OR all:"video stylization" OR all:"video style transfer" OR all:"video object removal"'),
 ('Video Retrieval','视频查找',r'video retriev|text.to.video retriev|text.video retriev|video search|video moment retriev|moment locali[sz]|temporal ground|temporal sentence ground|video locali[sz]',
  'all:"video retrieval" OR all:"text-to-video retrieval" OR all:"video search" OR all:"moment retrieval" OR all:"moment localization" OR all:"temporal grounding" OR all:"temporal sentence grounding"'),
 ('Video Generation','视频生成',r'video generat|text.to.video|image.to.video|video synthes|video diffusion',
  'all:"video generation" OR all:"text-to-video" OR all:"image-to-video" OR all:"video synthesis" OR all:"video diffusion"'),
 ('Video Understanding','视频理解',r'video understanding|video comprehension|video question.answer|video reasoning|video.language|video caption|action recognition|long.video|video summari',
  'all:"video understanding" OR all:"video reasoning" OR all:"video question answering" OR all:"video comprehension" OR all:"video captioning" OR all:"action recognition" OR all:"video summarization"')]
def video_topics(paper):
 title=paper.get('title','').casefold();abstract=paper.get('summary','').casefold();result=[]
 for i,(name,label,pattern,query) in enumerate(RULES):
  field='title' if re.search(pattern,title) else 'abstract' if re.search(pattern,abstract) else 'topic' if name in paper.get('topics',[]) else None
  if field:result.append(({'title':0,'abstract':1,'topic':2}[field],i,{'name':name,'nameZh':label,'field':field}))
 return [r[2] for r in sorted(result)]
