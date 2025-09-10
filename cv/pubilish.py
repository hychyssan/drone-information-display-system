"""
基于 Ultralytics 官方 API 的实时检测代码（集成 Redis 数据发布）
参考：https://docs.ultralytics.com/zh/modes/predict/#videos
"""

import os
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'  # 强制 torch 以兼容方式加载权重（避免 weights-only 报错）

import argparse
import cv2
import torch
import redis
import time
import json
from typing import Dict, Any, Optional, List
from ultralytics import YOLO


class RedisDetectionPublisher:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        初始化 Redis 连接
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True  # 返回字符串
        )
        try:
            self.redis_client.ping()
            print(f"✅ Redis连接成功: {host}:{port}")
        except redis.ConnectionError:
            print(f"❌ Redis连接失败: {host}:{port}")
            self.redis_client = None  # 标记不可用

    def publish_detection_metadata(self, detections_data: List[Dict[str, Any]], frame_info: Dict[str, Any]) -> bool:
        """
        将每个目标检测结果写为一个 Redis Hash：
        键名: image_metadata:{timestamp_ms}
        字段: timestamp, center_x, center_y, width, height, confidence(百分比)
        """
        if not self.redis_client:
            return False

        try:
            # 以毫秒为单位的基准时间戳
            base_ts_ms = int(time.time() * 1000)

            for idx, det in enumerate(detections_data):
                # 为同一帧的多个检测制造唯一时间戳，避免键名冲突
                ts_ms = base_ts_ms + idx
                key = f"image_metadata:{ts_ms}"

                # 只保留图示中的字段；confidence 转为百分比
                data = {
                    "timestamp": ts_ms,
                    "center_x": float(det["center_x"]),
                    "center_y": float(det["center_y"]),
                    "width": float(det["width"]),
                    "height": float(det["height"]),
                    "confidence": round(float(det["confidence"]) * 100.0, 2)
                }

                self.redis_client.hset(key, mapping=data)
                self.redis_client.expire(key, 3600)  # 可按需调整过期时间

                # 可选：发布一个轻量通知，便于订阅端感知到新键
                self.redis_client.publish(
                    "yolo:image_metadata:updates",
                    json.dumps({"key": key, "timestamp": ts_ms})
                )

            if len(detections_data) > 0:
                print(f"📤 已写入 Redis Hash {len(detections_data)} 个: 前缀 image_metadata:*")

            return True
        except Exception as e:
            print(f"❌ Redis发布失败: {e}")
            return False

    def get_detection_stats(self) -> Dict[str, int]:
        """
        获取当前 image_metadata:* 键的数量统计
        """
        try:
            keys = self.redis_client.keys("image_metadata:*")
            return {"total_image_metadata": len(keys)}
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='YOLO 实时检测（集成 Redis，按图示数据结构写入）')
    parser.add_argument('--model', type=str, default='yolov8m.pt', help='模型路径')
    parser.add_argument('--source', type=str, default='DJI_20250308135111_0001_S.MP4', help='输入源（文件路径或摄像头索引）')
    parser.add_argument('--conf', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.85, help='IOU 阈值')
    parser.add_argument('--device', type=str, default='cuda:0', help='计算设备，如 cuda:0 / cpu / auto')
    parser.add_argument('--imgsz', type=int, nargs='+', default=[1280, 720], help='输入图像尺寸')

    # Redis相关
    parser.add_argument('--redis-host', type=str, default='localhost', help='Redis服务器地址')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    parser.add_argument('--redis-db', type=int, default=0, help='Redis数据库编号')
    parser.add_argument('--redis-password', type=str, default=None, help='Redis密码')
    parser.add_argument('--disable-redis', action='store_true', help='禁用Redis功能')

    return parser.parse_args()


def extract_detections_from_result(result) -> List[Dict[str, Any]]:
    """
    从 YOLO 结果中提取检测数据（中心点、宽高、置信度）
    """
    detections: List[Dict[str, Any]] = []

    if result.boxes is not None:
        boxes = result.boxes.cpu().numpy()  # 转为 numpy 便于索引
        for box in boxes:
            # xyxy 坐标
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            width = float(x2 - x1)
            height = float(y2 - y1)

            class_id = int(box.cls[0]) if hasattr(box, "cls") else -1
            confidence = float(box.conf[0]) if hasattr(box, "conf") else 0.0

            detections.append({
                "center_x": center_x,
                "center_y": center_y,
                "width": width,
                "height": height,
                "confidence": confidence,
                "class_id": class_id,
                "bbox_x1": x1,
                "bbox_y1": y1,
                "bbox_x2": x2,
                "bbox_y2": y2
            })

    return detections


def main():
    args = parse_arguments()

    # 自动设备选择
    device = 'cuda:0' if (args.device == 'auto' and torch.cuda.is_available()) else args.device
    print(f"🚀 使用设备: {device.upper()}")

    # Redis 发布器
    redis_publisher = None
    if not args.disable_redis:
        redis_publisher = RedisDetectionPublisher(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_db,
            password=args.redis_password
        )

    # 加载模型
    model = YOLO(args.model).to(device)
    print(f"✅ 已加载模型: {args.model}")
    print(f"🖼️ 输入分辨率: {args.imgsz}")

    # 源自动转换
    try:
        args.source = int(args.source)
    except ValueError:
        pass

    frame_count = 0
    detection_count = 0
    start_time = time.time()

    for result in model.predict(
        source=args.source,
        stream=True,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        show=True,
        verbose=False,
        device=device
    ):
        frame_count += 1

        orig_frame = result.orig_img
        annotated_frame = result.plot()

        detections_data = extract_detections_from_result(result)
        detection_count += len(detections_data)

        # 发布为 image_metadata:* 结构
        if redis_publisher and detections_data:
            frame_info = {
                "width": orig_frame.shape[1],
                "height": orig_frame.shape[0],
                "source": str(args.source)
            }
            redis_publisher.publish_detection_metadata(detections_data, frame_info)

        # 统计信息叠加
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0.0
        stats_text = [
            f"FPS: {fps:.1f}",
            f"Frames: {frame_count}",
            f"Detections: {detection_count}",
            f"Redis: {'ON' if redis_publisher and redis_publisher.redis_client else 'OFF'}"
        ]
        y0 = 30
        for i, txt in enumerate(stats_text):
            cv2.putText(annotated_frame, txt, (10, y0 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 拼接显示
        combined = cv2.hconcat([orig_frame, annotated_frame])
        h, w = combined.shape[:2]
        display_frame = cv2.resize(combined, (w // 2, h // 2))
        cv2.imshow('YOLOv8检测 + Redis(image_metadata) - 按ESC退出', display_frame)

        if cv2.waitKey(1) == 27:
            break

        if frame_count % 100 == 0:
            print(f"📊 处理帧数: {frame_count}, 检测目标: {detection_count}, FPS: {fps:.1f}")
            if redis_publisher:
                stats = redis_publisher.get_detection_stats()
                if stats:
                    print(f"📊 Redis统计: image_metadata键数={stats.get('total_image_metadata', 0)}")

    cv2.destroyAllWindows()

    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0.0
    print("\n🏁 检测完成:")
    print(f"   总帧数: {frame_count}")
    print(f"   总检测数: {detection_count}")
    print(f"   平均FPS: {avg_fps:.1f}")
    print(f"   总耗时: {total_time:.1f}秒")
    if redis_publisher:
        final_stats = redis_publisher.get_detection_stats()
        if final_stats:
            print(f"   Redis数据: {final_stats}")


if __name__ == "__main__":
    main()