import os
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'

import argparse
import cv2
import torch
import redis
import time
import json
import subprocess
from typing import Dict, Any, Optional, List
from ultralytics import YOLO


class RedisDetectionPublisher:
    def __init__(self, host: str = '124.71.162.119', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        初始化 Redis 连接（无密码）
        """
        pwd = None if (password in ("", "None", None)) else password
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=pwd,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        try:
            self.redis_client.ping()
            print(f"✅ Redis连接成功: {host}:{port}（{'无密码' if pwd is None else '使用密码'}）")
        except redis.ConnectionError as e:
            print(f"❌ Redis连接失败: {host}:{port}，错误：{e}")
            self.redis_client = None

    def publish_detection_metadata(self, detections_data: List[Dict[str, Any]], frame_info: Dict[str, Any]) -> bool:
        """
        将每个目标检测结果写为一个 Redis Hash：
        键名: image_metadata:{timestamp_ms}
        字段: timestamp, center_x, center_y, width, height, confidence(百分比)
        频道: image:metadata:updates  消息内容: key 名
        """
        if not self.redis_client:
            return False
        try:
            base_ts_ms = int(time.time() * 1000)
            for idx, det in enumerate(detections_data):
                ts_ms = base_ts_ms + idx
                key = f"image_metadata:{ts_ms}"
                data = {
                    "timestamp": ts_ms,
                    "center_x": float(det["center_x"]),
                    "center_y": float(det["center_y"]),
                    "width": float(det["width"]),
                    "height": float(det["height"]),
                    "confidence": round(float(det["confidence"]) * 100.0, 2),
                }
                self.redis_client.hset(key, mapping=data)
                self.redis_client.expire(key, 3600)
                self.redis_client.publish("image:metadata:updates", f"{key}")
            if len(detections_data) > 0:
                print(f"📤 已写入 Redis Hash {len(detections_data)} 个: image:metadata:updates")
            return True
        except Exception as e:
            print(f"❌ Redis发布失败: {e}")
            return False

    def get_detection_stats(self) -> Dict[str, int]:
        """
        获取统计（按你原逻辑保留）
        """
        try:
            keys = self.redis_client.keys("image:metadata:")
            return {"total_image:metadata:updates": len(keys)}
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}


class RtmpStreamer:
    """
    RTMP 推流器（默认开启）
    - 统一转码为 1280x720 @ 25fps
    - 码率控制：平均 2300k，峰值 2500k，缓冲 5000k
    - 无音频 (-an)
    - 若需要更低带宽，可改为注释中的 540p 配置
    """
    TARGET_W = 1280
    TARGET_H = 720
    FPS = 25
    BITRATE_K = 2300
    MAXRATE_K = 2500
    BUFSIZE_K = 5000

    # 低带宽（可替换上面参数）：
    # TARGET_W = 960
    # TARGET_H = 540
    # FPS = 25
    # BITRATE_K = 1600
    # MAXRATE_K = 1800
    # BUFSIZE_K = 3600

    def __init__(self, rtmp_url: str = 'rtmp://124.71.162.119:1935/live/stream'):
        self.rtmp_url = rtmp_url
        self.proc: Optional[subprocess.Popen] = None
        self.started = False
        self.restart_attempted = False  # 简单防抖

    def start(self):
        if self.started:
            return
        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.TARGET_W}x{self.TARGET_H}",
            "-r", str(self.FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-profile:v", "main",
            "-level", "3.1",
            "-g", str(self.FPS * 2),
            "-keyint_min", str(self.FPS * 2),
            "-sc_threshold", "0",
            "-b:v", f"{self.BITRATE_K}k",
            "-maxrate", f"{self.MAXRATE_K}k",
            "-bufsize", f"{self.BUFSIZE_K}k",
            "-an",
            "-f", "flv",
            self.rtmp_url
        ]
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            self.started = True
            print(f"📺 RTMP 推流开始: {self.rtmp_url} {self.TARGET_W}x{self.TARGET_H}@{self.FPS} "
                  f"{self.BITRATE_K}k(max {self.MAXRATE_K}k)")
        except Exception as e:
            self.proc = None
            print(f"❌ 启动 FFmpeg 失败: {e}")

    def write(self, frame):
        if not self.started or self.proc is None or self.proc.stdin is None:
            # 若进程挂了，尝试一次重启
            if not self.restart_attempted:
                print("⚠️ 推流进程不存在，尝试重启一次...")
                self.restart_attempted = True
                self.start()
            return

        # 如果 FFmpeg 已退出
        if self.proc.poll() is not None:
            if not self.restart_attempted:
                print("⚠️ 推流进程已退出，尝试重启一次...")
                self.restart_attempted = True
                self.close()
                self.start()
            return

        try:
            if frame.shape[1] != self.TARGET_W or frame.shape[0] != self.TARGET_H:
                frame = cv2.resize(frame, (self.TARGET_W, self.TARGET_H))
            self.proc.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError) as e:
            print(f"⚠️ 推流中断: {e}")
            self.close()

    def close(self):
        if self.proc:
            try:
                if self.proc.stdin:
                    try:
                        self.proc.stdin.close()
                    except Exception:
                        pass
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except Exception:
                    self.proc.kill()
            except Exception:
                pass
            finally:
                self.proc = None
                self.started = False
                print("⏹️ RTMP 推流已停止")


def parse_arguments():
    parser = argparse.ArgumentParser(description='YOLO 实时检测（Redis + RTMP 推流）')
    parser.add_argument('--model', type=str, default='yolov8m.pt', help='模型路径')
    parser.add_argument('--source', type=str, default='DJI_20250308135111_0001_S.MP4', help='输入源（文件路径或摄像头索引）')
    parser.add_argument('--conf', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.85, help='IOU 阈值')
    parser.add_argument('--device', type=str, default='cuda:0', help='计算设备，如 cuda:0 / cpu / auto')
    parser.add_argument('--imgsz', type=int, nargs='+', default=[1280, 720], help='输入图像尺寸')

    # Redis
    parser.add_argument('--redis-host', type=str, default='124.71.162.119', help='Redis服务器地址（公网）')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    parser.add_argument('--redis-db', type=int, default=0, help='Redis数据库编号')
    parser.add_argument('--redis-password', type=str, default=None, help='Redis密码（留空/None 表示无密码）')
    parser.add_argument('--disable-redis', action='store_true', help='禁用Redis功能')
    return parser.parse_args()


def extract_detections_from_result(result) -> List[Dict[str, Any]]:
    detections: List[Dict[str, Any]] = []
    if result.boxes is not None:
        boxes = result.boxes.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            width = float(x2 - x1)
            height = float(y2 - y1)
            confidence = float(getattr(box, "conf", [0.0])[0])
            class_id = int(getattr(box, "cls", [-1])[0])
            detections.append({
                "center_x": center_x,
                "center_y": center_y,
                "width": width,
                "height": height,
                "confidence": confidence,
                "class_id": class_id,
                "bbox_x1": x1, "bbox_y1": y1, "bbox_x2": x2, "bbox_y2": y2,
            })
    return detections


def main():
    args = parse_arguments()
    device = 'cuda:0' if (args.device == 'auto' and torch.cuda.is_available()) else args.device
    print(f"🚀 使用设备: {device.upper()}")

    redis_publisher = None
    if not args.disable_redis:
        redis_publisher = RedisDetectionPublisher(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_db,
            password=args.redis_password,
        )

    rtmp_streamer = RtmpStreamer()  # 默认开启推流

    model = YOLO(args.model).to(device)
    print(f"✅ 已加载模型: {args.model}")
    print(f"🖼️ 输入分辨率: {args.imgsz}")

    try:
        args.source = int(args.source)
    except ValueError:
        pass

    frame_count = 0
    detection_count = 0
    start_time = time.time()

    try:
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

            if redis_publisher and detections_data:
                frame_info = {
                    "width": orig_frame.shape[1],
                    "height": orig_frame.shape[0],
                    "source": str(args.source)
                }
                redis_publisher.publish_detection_metadata(detections_data, frame_info)

            if not rtmp_streamer.started:
                rtmp_streamer.start()
            rtmp_streamer.write(annotated_frame)

            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0.0
            stats_text = [
                f"FPS: {fps:.1f}",
                f"Frames: {frame_count}",
                f"Detections: {detection_count}",
                f"Redis: {'ON' if redis_publisher and redis_publisher.redis_client else 'OFF'}",
                f"RTMP: ON {RtmpStreamer.TARGET_W}x{RtmpStreamer.TARGET_H}@{RtmpStreamer.FPS}"
            ]
            y0 = 30
            for i, txt in enumerate(stats_text):
                cv2.putText(annotated_frame, txt, (10, y0 + i * 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            combined = cv2.hconcat([orig_frame, annotated_frame])
            h, w = combined.shape[:2]
            display_frame = cv2.resize(combined, (w // 2, h // 2))
            cv2.imshow('YOLOv8检测 + Redis + RTMP推流(压缩) - ESC退出', display_frame)

            if cv2.waitKey(1) == 27:
                break
    finally:
        cv2.destroyAllWindows()
        rtmp_streamer.close()

    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0.0
    print("\n🏁 检测完成:")
    print(f"  总帧数: {frame_count}")
    print(f"  总检测数: {detection_count}")
    print(f"  平均FPS: {avg_fps:.1f}")
    print(f"  总耗时: {total_time:.1f}秒")
    if redis_publisher:
        stats = redis_publisher.get_detection_stats()
        if stats:
            print(f"  Redis数据: {stats}")


if __name__ == "__main__":
    main()