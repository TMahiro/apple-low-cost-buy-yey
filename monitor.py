"""
Apple整備済製品 監視スクリプト
refurbishedパッケージを使用してApple Japan整備済み製品を監視する
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml
from refurbished import Store


# -------------------------------------------
# 定数
# -------------------------------------------
STATE_FILE = Path("state.json")
CONFIG_FILE = Path("config.yml")


# -------------------------------------------
# 設定読み込み
# -------------------------------------------
def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"[ERROR] {CONFIG_FILE} が見つかりません")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


# -------------------------------------------
# 状態管理
# -------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"products": {}}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 状態を保存しました: {STATE_FILE}")


# -------------------------------------------
# Apple整備済み製品を取得
# -------------------------------------------
def fetch_refurbished_products() -> list[dict]:
    try:
        store = Store("jp")
        macs = store.get_macs()
        products = [
            {
                "id": mac.model,
                "name": mac.name,
                "price": mac.price,
                "url": mac.url,
            }
            for mac in macs
        ]
        print(f"[INFO] {len(products)}件の整備済製品を取得")
        return products
    except Exception as e:
        print(f"[ERROR] 整備済製品の取得に失敗: {e}")
        return []


# -------------------------------------------
# 対象モデルのフィルタリング
# -------------------------------------------
def is_target(product: dict, targets: list[dict]) -> bool:
    product_name = product.get("name", "").lower()
    for target in targets:
        keywords = [kw.lower() for kw in target.get("keywords", [])]
        if all(kw in product_name for kw in keywords):
            return True
    return False


# -------------------------------------------
# LINE通知（Push Message: 自分だけに送信）
# -------------------------------------------
def send_line_message(token: str, user_id: str, message: str) -> bool:
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}],
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        print("[INFO] LINE通知送信完了")
        return True
    except requests.RequestException as e:
        print(f"[ERROR] LINE通知失敗: {e}")
        return False


def build_in_stock_message(product: dict) -> str:
    name = product.get("name", "不明")
    price = product.get("price", "不明")
    url = product.get("url", "")
    return (
        f"Apple整備品に「{name}」が追加しました！\n"
        f"価格：{price}円\n"
        f"製品URL：{url}"
    )


def build_sold_out_message(product_name: str) -> str:
    return f"Apple整備品「{product_name}」が売り切れました。"


# -------------------------------------------
# メイン処理
# -------------------------------------------
def main() -> None:
    print(f"\n{'='*50}")
    print(f"[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    config = load_config()

    if not config.get("enabled", True):
        print("[INFO] 監視が無効化されています (enabled: false)")
        return

    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not line_token:
        print("[ERROR] LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        sys.exit(1)

    line_user_id = os.environ.get("LINE_USER_ID", "")
    if not line_user_id:
        print("[ERROR] LINE_USER_ID が設定されていません")
        sys.exit(1)

    targets = config.get("targets", [])
    if not targets:
        print("[WARN] 監視対象が設定されていません")
        return

    print(f"[INFO] 監視対象: {len(targets)}件")
    for t in targets:
        print(f"  - {t.get('name')}: {t.get('keywords')}")

    # 整備済み製品を取得
    products = fetch_refurbished_products()

    # 現在の在庫から対象製品を抽出
    current_in_stock: dict[str, dict] = {}
    for product in products:
        if is_target(product, targets):
            product_id = product.get("id", product.get("name", ""))
            current_in_stock[product_id] = product
            print(f"[MATCH] {product.get('name')}")

    # 状態を読み込み
    state = load_state()
    prev_in_stock: dict = state.get("products", {})

    # 新規入荷: 前回なし → 今回あり
    for product_id, product in current_in_stock.items():
        if product_id not in prev_in_stock:
            print(f"[NEW] 新規入荷: {product.get('name')}")
            message = build_in_stock_message(product)
            send_line_message(line_token, line_user_id, message)

    # 売り切れ: 前回あり → 今回なし
    for product_id, product in prev_in_stock.items():
        if product_id not in current_in_stock:
            name = product.get("name", product_id)
            print(f"[SOLD OUT] 売り切れ: {name}")
            message = build_sold_out_message(name)
            send_line_message(line_token, line_user_id, message)

    # 状態を更新
    state["products"] = current_in_stock
    state["last_checked"] = datetime.now().isoformat()
    save_state(state)

    print("[END] 完了")


if __name__ == "__main__":
    main()
