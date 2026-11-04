"""Editable study taxonomy. Grouping is editorial; links are primary references."""
DOMAINS=[('general','通用基础'),('cv','计算机视觉 · CV'),('nlp','自然语言处理 · NLP'),('agent','智能体 · Agent')]
SOURCES={
 'general':'https://docs.pytorch.org/tutorials/beginner/basics/intro.html',
 'cv':'https://docs.pytorch.org/vision/stable/models.html',
 'nlp':'https://huggingface.co/docs/transformers/index',
 'agent':'https://huggingface.co/learn/agents-course/en/unit1/introduction'}
GROUPS=[
('general','数学与学习基础', '''线性代数|Linear Algebra|向量、矩阵乘法、特征值、奇异值
概率与统计|Probability & Statistics|条件概率、贝叶斯公式、期望与方差
微积分与链式法则|Calculus & Chain Rule|偏导、梯度、雅可比与链式法则
机器学习基础|Machine Learning|监督、无监督与泛化
线性回归|Linear Regression|最小二乘、特征与误差
逻辑回归|Logistic Regression|对数几率、决策边界与分类
决策树与集成学习|Trees & Ensembles|决策树、随机森林与提升
支持向量机|SVM|间隔、核方法与正则化
聚类与降维|Clustering & PCA|K-means、PCA 与距离度量'''),
('general','神经网络与训练', '''多层感知机|MLP|全连接层、非线性与表达能力
激活函数|Activation Functions|ReLU、GELU、Sigmoid 与梯度
反向传播|Backpropagation|计算图、链式法则与梯度检查
模型训练与优化|Training & Optimization|损失、优化器、训练循环与调试
随机梯度下降|SGD|批次、动量与更新方向
自适应优化器|Adam & AdamW|一二阶矩估计与权重衰减
学习率调度|Learning Rate Schedules|Warmup、余弦退火与早停
归一化层|Normalization|BatchNorm、LayerNorm、GroupNorm 与 RMSNorm
正则化与泛化|Regularization|L1、L2、Dropout 与数据增强
损失函数|Loss Functions|交叉熵、MSE、对比损失与任务匹配
注意力机制|Attention|Q/K/V、权重、缩放与加权聚合
多头注意力|Multi-Head Attention|子空间、头数与维度
残差连接|Residual Connections|恒等路径、梯度传播与深层优化'''),
('general','评估与部署', '''模型评估|Model Evaluation|Precision、Recall、F1 与数据划分
实验设计与消融|Ablation Studies|对照、随机种子、混杂因素与可复现性
类别不平衡|Class Imbalance|重采样、加权损失与阈值
模型压缩|Model Compression|剪枝、蒸馏、量化与速度验证
知识蒸馏|Knowledge Distillation|教师、学生、温度与特征蒸馏
剪枝|Pruning|结构化与非结构化稀疏
量化|Quantization|PTQ、QAT、位宽与校准
混合精度|Mixed Precision|FP32、FP16、BF16 与数值稳定性
分布式训练|Distributed Training|数据并行、梯度同步与训练预算'''),
('cv','卷积与视觉模块', '''卷积神经网络|CNN|卷积、局部连接、参数共享与感受野
卷积运算与尺寸|Convolution Shapes|Kernel、Stride、Padding 与 Dilation
感受野|Receptive Field|理论感受野与有效感受野
池化|Pooling|最大池化、平均池化与全局池化
深度可分离卷积|Depthwise Separable Convolution|Depthwise 与 Pointwise
分组卷积|Group Convolution|通道分组与计算量
空洞卷积|Dilated Convolution|采样间隔、感受野与栅格效应
转置卷积与上采样|Upsampling|插值、转置卷积与棋盘格现象
可变形卷积|Deformable Convolution|偏移、采样与几何变化
通道注意力|SE & Channel Attention|全局统计、通道重标定与代价
空间与通道注意力|CBAM|空间注意力与通道注意力的组合'''),
('cv','视觉骨干模型', '''经典卷积模型|LeNet AlexNet VGG|卷积堆叠与结构演变
残差网络|ResNet|残差块、捷径连接与深度
密集连接网络|DenseNet|特征拼接与特征复用
多分支网络|Inception|不同尺度卷积与多分支
轻量化网络|MobileNet|深度可分离卷积与移动端计算
高效缩放网络|EfficientNet|深度、宽度与分辨率缩放
现代卷积网络|ConvNeXt|卷积网络的现代化设计
视觉 Transformer|Vision Transformer|Patch、位置编码与全局建模
窗口视觉 Transformer|Swin Transformer|窗口注意力、移位与层级结构
自监督视觉学习|MAE & Contrastive Vision|掩码重建与对比学习'''),
('cv','检测与多尺度', '''目标检测|Object Detection|分类、定位、正负样本与评估
特征金字塔|FPN|自顶向下路径、横向连接与多尺度特征
路径聚合网络|PANet|自底向上路径增强与信息融合
双向特征金字塔|BiFPN|双向连接与加权特征融合
空间金字塔池化|SPP & SPPF|多尺度池化与特征聚合
候选区域网络|RPN|候选框、目标性与框回归
锚框与无锚检测|Anchor-based & Anchor-free|先验框、中心点与样本分配
两阶段目标检测|Faster R-CNN|RPN、RoI 与检测头
一阶段目标检测|YOLO & SSD|密集预测与速度精度权衡
Transformer 目标检测|DETR|集合预测、匹配与查询
RoI 特征提取|RoI Pooling & RoI Align|区域特征、量化与对齐
框回归损失|IoU GIoU DIoU CIoU|重叠、几何距离与损失
非极大值抑制|NMS & Soft-NMS|重复框、阈值与重叠目标
困难样本与焦点损失|Focal Loss|分类不平衡与难易样本
小目标检测|Small Object Detection|尺度、分辨率、融合与漏检
旋转目标检测|Oriented Object Detection|旋转框、角度与遥感目标'''),
('cv','分割视频与多模态', '''语义分割|Semantic Segmentation|像素分类与密集预测
编码解码分割|U-Net|跳跃连接、编码器与解码器
空洞空间金字塔|ASPP & DeepLab|多尺度空洞卷积与分割
实例分割|Mask R-CNN|实例级掩码与检测分支
通用分割模型|SAM|提示、图像编码器与掩码解码
视频理解|Video Understanding|时空特征、采样与动作识别
光流与目标跟踪|Optical Flow & Tracking|运动估计、匹配与身份关联
视觉语言对齐|CLIP|图文对比学习与跨模态检索
生成模型|VAE GAN Diffusion|潜变量、对抗训练与去噪
农业遥感检测|Agricultural Remote Sensing|地块、尺度变化、域偏移与遥感评估'''),
('nlp','文本表示与经典模型', '''文本预处理|Text Preprocessing|清洗、归一化与语料划分
分词与子词|Tokenization|BPE、WordPiece 与词表
词袋与词频权重|BoW & TF-IDF|稀疏表示与词频统计
词嵌入|Word Embeddings|Word2Vec、GloVe 与语义向量
循环神经网络|RNN|序列状态、展开与梯度
长短期记忆|LSTM|门控、细胞状态与长程依赖
门控循环单元|GRU|重置门、更新门与状态
序列到序列|Seq2Seq|编码、解码与序列映射
条件随机场|CRF|序列标注与结构化预测'''),
('nlp','Transformer 与语言模型', '''Transformer|Transformer|编码器、解码器与注意力结构
位置编码|Positional Encoding|绝对位置、相对位置与顺序信息
旋转位置编码|RoPE|旋转变换与相对位置信息
自注意力与交叉注意力|Self & Cross Attention|Q/K/V 的来源与交互
注意力掩码|Attention Masks|Padding Mask 与 Causal Mask
编码器语言模型|BERT|双向编码与掩码语言建模
自回归语言模型|GPT|因果掩码与下一 Token 预测
编码解码语言模型|T5 & BART|条件生成与序列到序列预训练
长上下文机制|Long Context|位置外推、截断与注意力成本
混合专家模型|Mixture of Experts|路由、专家与负载均衡'''),
('nlp','训练生成与检索', '''语言模型预训练|Language Model Pretraining|语料、预测目标与训练数据
监督微调|SFT|指令数据、监督目标与格式
低秩微调|LoRA|低秩更新、秩与适配器
量化低秩微调|QLoRA|低位存储与低秩适配
偏好优化|RLHF DPO PPO|偏好数据、奖励与策略优化
解码与采样|Decoding & Sampling|贪心、Beam、温度、Top-k 与 Top-p
键值缓存|KV Cache|自回归推理中的缓存与显存
预填充与解码|Prefill & Decode|输入处理与逐 Token 生成
高效注意力|Efficient Attention|算子实现、访存与注意力计算
句向量与语义检索|Sentence Embeddings|相似度、语义搜索与向量表示
稠密与稀疏检索|Dense & Sparse Retrieval|向量检索、倒排索引与混合检索
检索增强生成|RAG|分块、检索、重排、生成与引用
文档分块|Chunking|长度、重叠、结构与检索粒度
重排序|Reranking|候选集、交叉编码器与排序指标
语言模型评估|LLM Evaluation|任务指标、人工评估与泄漏检查
结构化信息抽取|NER & Information Extraction|实体、关系、序列标注与生成式抽取'''),
('agent','智能体核心模块', '''智能体|AI Agents|观察、决策、行动与反馈
工具调用|Tool Calling|工具描述、参数、执行与结果
结构化输出|Structured Outputs|Schema、格式校验与解析
推理行动循环|ReAct|推理、工具行动与观察反馈
规划与执行|Planning|任务拆解、执行、验证与重规划
工作流与智能体|Workflows vs Agents|固定流程与动态决策
短期记忆|Short-term Memory|会话历史、状态与上下文窗口
长期记忆|Long-term Memory|持久化、检索、更新与遗忘
上下文管理|Context Management|压缩、摘要、检索与预算
反思与验证|Reflection & Verification|检查输出、纠错与终止条件
智能体状态机|Agent State Machines|状态、转移、分支与恢复
智能体运行框架|Agent Harness|模型外部的工具、状态、权限与评估
智能体运行系统|Agent OS|调度、隔离、资源与持久化'''),
('agent','多智能体与应用', '''多智能体系统|Multi-agent Systems|角色、通信、协作与冲突
委派与交接|Delegation & Handoff|任务边界、上下文传递与责任
代码智能体|Coding Agents|代码修改、执行、测试与反馈
浏览器智能体|Browser Agents|页面状态、交互与网页工具
计算机使用智能体|Computer-use Agents|观察、坐标、状态变化与可靠性
研究智能体|Research Agents|检索、证据、引用与报告
智能体检索|Agentic RAG|动态检索、工具选择与迭代验证
工具协议与连接|Tool Protocols|工具发现、协议边界与权限
人工介入|Human-in-the-loop|审批、澄清、接管与反馈'''),
('agent','可靠性安全与训练', '''智能体评估|Agent Evaluation|任务成功率、轨迹、成本与失败类型
工具失败与恢复|Tool Recovery|重试、超时、幂等与回退
可观测性|Agent Observability|调用轨迹、日志、耗时与诊断
智能体安全|Agent Security|输入边界、权限、隔离与审计
提示注入|Prompt Injection|不可信内容与指令边界
工具权限与沙箱|Tool Permissions & Sandboxing|最小权限、资源约束与隔离
数据外泄防护|Data Exfiltration Defense|敏感数据、输出边界与网络访问
智能体强化学习|Agentic RL|轨迹、奖励、工具反馈与训练
奖励设计|Reward Design|奖励稀疏、作弊、错误反馈与验证
长期任务|Long-horizon Tasks|状态漂移、分解、检查点与预算''')]
def entries():
 result=[]
 for domain,section,lines in GROUPS:
  for line in lines.splitlines():
   name,en,scope=line.split('|');result.append(dict(name=name,en=en,domain=domain,section=section,summary='学习要点：'+scope,source=SOURCES[domain]))
 return result
