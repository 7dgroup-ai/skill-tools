"""baseline/ —— §5.3 性能基线建立（占位模块）。

第二轮真实案例演练：
- baseline.js  : k6 基准场景脚本（爬坡/稳态/退坡 + SLO 阈值，8 步链路关联）
- baseline.jmx : JMeter 等价基准场景（关联 token/orderId + 唯一用户池）
- ramp.md      : 阶梯加压记录表（10→50→100→200→400）与极限 TPS 判定
- baseline.json: 资源基线快照（CPU/内存/磁盘/网络/JVM），供后续对比
"""
