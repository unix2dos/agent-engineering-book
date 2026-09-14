"""虚构订单服务：故意保留一个缺陷，供只读排查使用。"""

ORDERS = {
    "order_001": {"total": 128},
}


def get_order(order_id):
    order = ORDERS.get(order_id)
    return {"order_id": order_id, "total": order["total"]}
