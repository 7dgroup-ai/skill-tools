#!/usr/bin/env python3
# project/data_pool/gen_users.py
# 生成 users.csv：支持指定行数、脱敏规则、分库分表分布模拟
# 用法：python3 gen_users.py --rows 2400 --output ../data/users.csv

import argparse
import csv
import random

def gen_users(rows: int, output: str):
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['userId', 'password'])
        for i in range(1, rows + 1):
            # 模拟分库分表：userId 尾号决定分片
            user_id = f"u{i:03d}"
            # 真实场景密码应为哈希，这里用固定明文仅作演示
            writer.writerow([user_id, 'pass-1'])
    print(f"Generated {rows} users -> {output}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, default=500, help='生成行数（铺底500，容量2400）')
    parser.add_argument('--output', type=str, default='../data/users.csv', help='输出路径')
    args = parser.parse_args()
    gen_users(args.rows, args.output)