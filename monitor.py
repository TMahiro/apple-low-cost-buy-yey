"""
Apple整備済製品 監視スクリプト
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml


# -------------------------------------------
# 定数
# -------------------------------------------
APPLE_REFURBISHED_API = (
    "https://www.apple.com/jp/shop/refurbished/products.json"
)
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
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Referer": "https://www.apple.com/jp/shop/refurbished/mac",
    }

    all_products = []
    page = 1

    while True:
        params = {"start": (page - 1) * 24, "rows": 24}
        try:
            resp = requests.get(
                APPLE_REFURBISHED_API,
                headers=headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Apple APIへのリクエスト失敗: {e}")
            return []

        products = data.get("products", [])
        if not products:
            break

        all_products.extend(products)

        total = data.get("pagination", {}).get("total", 0)
        if len(all_products) >= total:
            break

        page += 1
        time.sleep(1)  # Rate limiting

    print(f"[INFO] {len(all_products)}件の整備済製品を取得")
    return all_products


# -------------------------------------------
# 対象モデルのフィルタリング
# -------------------------------------------
def is_target(product: dict, targets: list[dict]) -> bool:
    """
    製品が監視対象かどうか判定する。
    config.yml の targets 各エントリのキーワードがすべて
    製品名に含まれていれば対象とみなす。
    """
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
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
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
    price_info = product.get("price", {})
    price = price_info.get("currentPrice", {}).get("amount", "不明")
    url = "https://www.apple.com" + product.get("productDetailsUrl", "")

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

    # 通知オンオフチェック
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
            product_id = product.get("partNumber", product.get("name", ""))
            current_in_stock[product_id] = product
            print(f"[MATCH] {product.get('name')}")

    # 状態を読み込み
    state = load_state()
    prev_in_stock: dict = state.get("products", {})

    # 差分検出・通知
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
