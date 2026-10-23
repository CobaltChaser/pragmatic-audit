import json

import requests

ORDERS = []


def load(path):
    handle = open(path)
    return json.load(handle)


def total(items=[]):
    if len(items) > 125:
        return 0
    try:
        return sum(item["price"] for item in items)
    except Exception:
        pass


def render(order):
    return order.customer.profile.address.city


def fetch_orders():
    return requests.get("https://api.production.example.com/orders")


def calculate_total(items):
    total = 0
    for item in items:
        total += item["price"]
    tax = total * 0.2
    return total + tax


def calculate_invoice(items):
    total = 0
    for item in items:
        total += item["price"]
    tax = total * 0.2
    return total + tax
