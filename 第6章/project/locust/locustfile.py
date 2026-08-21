# project/locust/locustfile.py
# sketch-store 8 步链路：商品列表→登录→加购→查车→预览→建单→支付→查单
# 关联：token、orderId | 参数化：users.csv、goods.csv
# 运行：locust -f locustfile.py --host=http://localhost:8000 --users 10 --run-time 3m --headless

from locust import HttpUser, task, between
import random
import csv
import os

# ---------- 数据池加载（模块级仅加载一次） ----------
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_users():
    users = []
    with open(os.path.join(DATA_DIR, 'users.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append({'username': row['userId'], 'password': row['password']})
    return users

def load_goods():
    goods = []
    with open(os.path.join(DATA_DIR, 'goods.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            goods.append({'goodsId': int(row['goodsId'])})
    return goods

USERS = load_users()
GOODS = load_goods()

class ShoppingFlowUser(HttpUser):
    wait_time = between(1, 3)          # 模拟思考时间
    host = "http://localhost:8000"

    def on_start(self):
        """虚拟用户启动时登录一次，token 复用"""
        user = random.choice(USERS)
        resp = self.client.post("/api/login", json={
            "username": user['username'],
            "password": user['password']
        })
        if resp.status_code == 200 and resp.json().get('code') == 0:
            self.token = resp.json()['data']['token']
            self.auth_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
        else:
            self.token = None
            self.auth_headers = {}

    @task(1)
    def goods_list(self):
        """1. 商品列表"""
        if not self.token:
            return
        self.client.get("/api/goods/list", params={"page": 1, "size": 20},
                        headers={'Content-Type': 'application/json'})

    @task(2)
    def add_to_cart(self):
        """3. 加购（随机商品、随机数量）"""
        if not self.token:
            return
        goods = random.choice(GOODS)
        self.client.post("/api/cart/add", json={
            "goods_id": goods['goodsId'],
            "num": random.randint(1, 5)
        }, headers=self.auth_headers)

    @task(1)
    def cart_list(self):
        """4. 查购物车"""
        if not self.token:
            return
        self.client.get("/api/cart/list", headers=self.auth_headers)

    @task(1)
    def order_preview(self):
        """5. 预览单 → 提取 orderId"""
        if not self.token:
            return
        resp = self.client.post("/api/order/preview", json={}, headers=self.auth_headers)
        if resp.status_code == 200 and resp.json().get('code') == 0:
            self.order_id = resp.json()['data']['order_id']

    @task(1)
    def order_create(self):
        """6. 建单"""
        if not hasattr(self, 'order_id'):
            return
        self.client.post("/api/order/create", json={
            "order_id": self.order_id
        }, headers=self.auth_headers)

    @task(1)
    def order_pay(self):
        """7. 支付（幂等 request_id）"""
        if not hasattr(self, 'order_id'):
            return
        self.client.post("/api/order/pay", json={
            "order_id": self.order_id,
            "pay_type": "mock",
            "request_id": f"pay-{random.randint(1,1000000)}-{int(random.random()*1000000)}"
        }, headers=self.auth_headers)

    @task(1)
    def order_query(self):
        """8. 查单（最终业务状态 PAID）"""
        if not hasattr(self, 'order_id'):
            return
        resp = self.client.get(f"/api/order/{self.order_id}", headers=self.auth_headers)
        if resp.status_code == 200:
            assert resp.json().get('data', {}).get('status') == 'PAID', f"订单状态非 PAID: {resp.json()}"