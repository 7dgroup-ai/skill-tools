# project/lib/python/flow_common.py
# Locust 公共步骤函数

import random
from locust import HttpUser

def login(client, username, password):
    """登录并返回 token"""
    resp = client.post("/api/login", json={"username": username, "password": password})
    assert resp.status_code == 200 and resp.json().get('code') == 0, f"登录失败: {resp.text}"
    return resp.json()['data']['token']

def auth_headers(token):
    """构建带 Authorization 的请求头"""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

def idempotent_key(prefix='req'):
    """幂等请求号"""
    return f"{prefix}-{random.randint(1,1000000)}-{int(random.random()*1000000)}"

class FlowUserMixin:
    """混入类：提供完整业务流程步骤"""
    
    def do_goods_list(self):
        self.client.get("/api/goods/list", params={"page": 1, "size": 20})
    
    def do_add_cart(self, goods_id=None, num=None):
        if goods_id is None:
            goods_id = random.randint(1, 1000)
        if num is None:
            num = random.randint(1, 5)
        self.client.post("/api/cart/add", json={"goods_id": goods_id, "num": num}, headers=self.auth_headers)
    
    def do_cart_list(self):
        self.client.get("/api/cart/list", headers=self.auth_headers)
    
    def do_order_preview(self):
        resp = self.client.post("/api/order/preview", json={}, headers=self.auth_headers)
        assert resp.status_code == 200 and resp.json().get('code') == 0
        self.order_id = resp.json()['data']['order_id']
    
    def do_order_create(self):
        self.client.post("/api/order/create", json={"order_id": self.order_id}, headers=self.auth_headers)
    
    def do_order_pay(self):
        self.client.post("/api/order/pay", json={
            "order_id": self.order_id,
            "pay_type": "mock",
            "request_id": idempotent_key("pay")
        }, headers=self.auth_headers)
    
    def do_order_query(self):
        resp = self.client.get(f"/api/order/{self.order_id}", headers=self.auth_headers)
        assert resp.status_code == 200
        assert resp.json().get('data', {}).get('status') == 'PAID', f"订单状态非 PAID: {resp.json()}"