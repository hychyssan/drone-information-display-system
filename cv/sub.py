"""
Redis 订阅端示例：监听 YOLO 检测结果（image_metadata:* 哈希）
配套发布端：
- 频道：yolo:image_metadata:updates
- 消息：{"key": "image_metadata:{timestamp_ms}", "timestamp": 1757403271281}
- 对应的哈希键：image_metadata:{timestamp_ms}
  字段：timestamp, center_x, center_y, width, height, confidence(百分比)
"""

import redis
import json


def main():
    # 初始化 Redis 客户端
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # 订阅新频道：yolo:image_metadata:updates
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe('yolo:image_metadata:updates')

    print("📡 已订阅 yolo:image_metadata:updates，等待消息...")

    try:
        for message in pubsub.listen():
            # 只处理真正的消息
            if message.get('type') != 'message':
                continue

            # 解析 JSON 负载
            try:
                data = json.loads(message['data'])
            except Exception as e:
                print(f"⚠️ 无法解析消息为 JSON：{e}，原始数据：{message['data']}")
                continue

            key = data.get('key')  # 例如：image_metadata:1757403271281
            ts = data.get('timestamp')

            if not key:
                print(f"⚠️ 消息未包含 key 字段：{data}")
                continue

            # 读取对应的哈希内容
            det = r.hgetall(key)
            if not det:
                print(f"⚠️ 找不到哈希键：{key}")
                continue

            # 友好打印
            print(f"🆕 新检测到目标（哈希键）：{key}")
            print(f"    timestamp : {det.get('timestamp', ts)}")
            print(f"    center_x  : {det.get('center_x')}")
            print(f"    center_y  : {det.get('center_y')}")
            print(f"    width     : {det.get('width')}")
            print(f"    height    : {det.get('height')}")
            print(f"    confidence: {det.get('confidence')}")

    except KeyboardInterrupt:
        print("🔴 退出订阅")


if __name__ == '__main__':
    main()