"""business_model/ —— §5.1 业务模型抽取与流量分布（占位模块）。

第二轮真实案例演练：
- traffic_model.py   : 业务模型表（接口/触发人群占比/人均日调用/日均量/权重/高峰 TPS）
- assumptions.md     : DAU、转化率、高峰集中系数 H 的假设与校准来源
- calibrate.py       : 读生产网关日志，校准 H 与权重 w_i（替换经验假设）
"""
