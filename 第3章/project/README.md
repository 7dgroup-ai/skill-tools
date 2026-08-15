# 接口测试工程（第 3 章交付物）

把"调通一个接口"升级为"用业务参数组织能力"。四层收口：

- **请求层** `clients/`：多协议 Client（REST/gRPC/GraphQL/WS）+ 认证链（JWT/OAuth2/AK-SK）
- **断言层** `asserters/`：JSON Schema 结构校验 + 业务断言链
- **数据层** `datafactory/`：Builder/Factory/Provider 三层造数 + 提取器 + 隔离清理
- **编排层** `dsl/`：YAML 业务场景（关联/重试/前后置/清洗）+ OpenAPI 生成
- **依赖隔离** `mocks/`：Python 内嵌 Mock（异常注入）
- **契约层** `contract/`：Pact 消费者契约 + OpenAPI Diff

## 快速上手

```bash
pip install -r requirements.txt
pytest                          # 单元验收（不依赖真实被测系统）
```

真机接口链路验收（可选，需 sketch-store）：

```bash
# 1. 启动被测应用（仓库内共享被测件，见《被测应用设计手稿》）
#    docker-compose up -d && make seed
# 2. 运行业务流场景
python -m dsl.runner scenarios/order_flow.yaml
```

> 所有 `localhost:8000` 类地址均可在 YAML / 环境变量中替换为你的被测系统。
