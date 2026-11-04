export const PAPER_RELATIONS=[
 ['same-problem','研究同一问题','两篇论文研究相同或相近的问题。'],
 ['builds-on','继承／基于其方法','当前论文基于关联论文的方法开展工作。'],
 ['improves','改进其方法／局限','当前论文改进关联论文的方法或处理其局限。'],
 ['extends','扩展其能力／场景','当前论文扩展关联论文的适用条件或能力。'],
 ['uses-component','使用其模型／组件','当前论文使用关联论文提出的模型或组件。'],
 ['baseline','作为对照基线','当前论文把关联论文的方法作为实验基线。'],
 ['compares','进行实验对比','当前论文与关联论文的方法进行实验比较。'],
 ['complements','方法互补','两篇论文提供可以互补的方法或视角。'],
 ['applies','迁移到新任务','当前论文把关联论文的方法用于新任务。'],
 ['supports','支持／验证其结论','当前论文的证据支持或验证关联论文的结论。'],
 ['challenges','质疑／反例／不一致','当前论文提出与关联论文结论不一致的证据或反例。'],
 ['background','背景／概念来源','关联论文作为当前论文的背景、概念或理论来源。'],
 ['surveys','综述／归纳其工作','当前论文综述或归纳关联论文的工作。'],
 ['uncertain','关系待判断','目前还没有足够依据确定两篇论文的具体关系。']
].map(([id,label,description])=>({id,label,description}));
export const EVIDENCE_STATUSES=[['unverified','待核实'],['author-claim','作者明确陈述'],['checked','已对照原文／实验核对'],['inference','我的推断']];
export function cleanRelationTypes(values){return Array.isArray(values)?[...new Set(values.filter(id=>PAPER_RELATIONS.some(r=>r.id===id)))]:[]}
