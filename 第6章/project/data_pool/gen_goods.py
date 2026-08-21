#!/usr/bin/env python3
# project/data_pool/gen_goods.py
# 生成 goods.csv：支持指定行数、库存分布、分类分布
# 用法：python3 gen_goods.py --rows 2400 --output ../data/goods.csv

import argparse
import csv
import random

def gen_goods(rows: int, output: str):
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['goodsId'])
        for i in range(1, rows + 1):
            writer.writerow([i])
    print(f"Generated {rows} goods -> {output}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, default=1000, help='生成行数（铺底1000，容量2400）')
    parser.add_argument('--output', type=str, default='../data/goods.csv', help='输出路径')
    args = parser.parse_args()
    gen_goods(args.rows, args.output)