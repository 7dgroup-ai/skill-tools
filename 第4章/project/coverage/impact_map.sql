-- impact_map.sql —— 用例-方法映射表结构（§4.1.2）
-- 生命周期四阶段：建表/迁移 → 写入/更新(upsert) → 过期清理 → 跨 CI 持久化
-- 生产级：PostgreSQL/MySQL（连接串走 CI Secret）；本减配 POC 用 SQLite。

CREATE TABLE IF NOT EXISTS impact_map (
    test_case    TEXT NOT NULL,        -- test_cart.py::test_add_num_zero
    source_file  TEXT NOT NULL,        -- app/routes/cart.py
    source_func  TEXT NOT NULL,        -- add_to_cart
    last_seen    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (test_case, source_file, source_func)
);

-- 反向查询索引：变更 (source_file, source_func) -> 受影响用例
CREATE INDEX IF NOT EXISTS idx_src ON impact_map(source_file, source_func);

-- 过期清理（每日定时任务 / CI 后置）：超 7 天未"真实执行到"的映射删除
-- DELETE FROM impact_map WHERE last_seen < now() - INTERVAL '7 days';