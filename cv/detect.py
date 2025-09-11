import os
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'

import argparse
import cv2
import torch
import redis
import time
import json
import subprocess
import threading
import queue
from typing import Dict, Any, Optional, List
from ultralytics import YOLO

# ========================= Redis 发布 =========================
class RedisDetectionPublisher:
    def __init__(self, host: str = '124.71.162.119', port: int = 6379, db: int = 0, password: Optional[str] = None):
        pwd = None if (password in ("", "None", None)) else password
        self.redis_client = redis.Redis(
            host=host, port=port, db=db, password=pwd,
            decode_responses=True, socket_timeout=5, retry_on_timeout=True
        )
        try:
            self.redis_client.ping()
            print(f"✅ Redis连接成功: {host}:{port}（{'无密码' if pwd is None else '使用密码'}）")
        except redis.ConnectionError as e:
            print(f"❌ Redis连接失败: {host}:{port}，错误：{e}")
            self.redis_client = None

    def publish_detection_metadata(self, detections_data: List[Dict[str, Any]]) -> bool:
        if not self.redis_client or not detections_data:
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
                self.redis_client.publish("image:metadata:updates", key)
            print(f"📤 已写入 Redis Hash {len(detections_data)} 个: image:metadata:updates")
            return True
        except Exception as e:
            print(f"❌ Redis发布失败: {e}")
            return False

    def get_detection_stats(self) -> Dict[str, int]:
        if not self.redis_client:
            return {}
        try:
            keys = self.redis_client.keys("image:metadata:")
            return {"total_image:metadata:updates": len(keys)}
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

# ========================= RTMP 推流（yuv420p 修复） =========================
class RtmpStreamer:
    TARGET_W = 1280
    TARGET_H = 720
    FPS = 25
    BITRATE_K = 2300
    MAXRATE_K = 2500
    BUFSIZE_K = 5000
    # 若需更省带宽：
    # TARGET_W, TARGET_H = 960, 540
    # BITRATE_K, MAXRATE_K, BUFSIZE_K = 1600, 1800, 3600

    def __init__(self, rtmp_url: str = 'rtmp://124.71.162.119:1936/hls/stream'):####rtmp://124.71.162.119:1936/hls/stream  rtmp://124.71.162.119:1935/live/stream
        self.rtmp_url = rtmp_url
        self.proc: Optional[subprocess.Popen] = None
        self.started = False
        self.restart_attempted = False

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
            "-vf", "format=yuv420p",
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
            if not self.restart_attempted:
                print("⚠️ 推流进程不存在，尝试重启...")
                self.restart_attempted = True
                self.start()
            return
        if self.proc.poll() is not None:
            if not self.restart_attempted:
                print("⚠️ 推流进程已退出，尝试重启...")
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

# ========================= 线程：采集 & 推理 =========================
class CaptureThread(threading.Thread):
    def __init__(self, source, frame_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.source = source
        self.frame_queue = frame_queue
        self.stop_event = stop_event
        self.cap: Optional[cv2.VideoCapture] = None

    def run(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print("❌ 无法打开视频源")
            self.stop_event.set()
            return
        print("🎥 CaptureThread 启动")
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ 读取帧失败/结束，停止采集")
                break
            try:
                self.frame_queue.put(frame, timeout=0.5)
            except queue.Full:
                # 队列满可选择丢帧：pass
                print("⚠️ 采集队列已满，丢弃帧")
        self.stop_event.set()
        if self.cap:
            self.cap.release()
        print("🎥 CaptureThread 结束")

class InferenceThread(threading.Thread):
    def __init__(self, model, frame_queue: queue.Queue, result_queue: queue.Queue,
                 stop_event: threading.Event, conf: float, iou: float, device: str,
                 enforce_resize: Optional[List[int]] = None):
        super().__init__(daemon=True)
        self.model = model
        self.frame_queue = frame_queue
        self.result_queue = result_queue
        self.stop_event = stop_event
        self.conf = conf
        self.iou = iou
        self.device = device
        # enforce_resize = [w, h] 若想所有帧统一尺寸可设；默认 None 不缩放
        self.enforce_resize = enforce_resize
        print("🧠 InferenceThread 初始化完成")

    def run(self):
        print("🧠 InferenceThread 启动")
        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # 可选统一尺寸（默认关闭）
            if self.enforce_resize and len(self.enforce_resize) == 2:
                target_w, target_h = self.enforce_resize
                if frame.shape[1] != target_w or frame.shape[0] != target_h:
                    frame = cv2.resize(frame, (target_w, target_h))

            try:
                # 关键修改：删除 imgsz=None，避免错误
                results = self.model.predict(
                    frame,
                    conf=self.conf,
                    iou=self.iou,
                    verbose=False,
                    #show=True,
                    device=self.device
                )
                result = results[0]
                annotated = result.plot()
                detections = extract_detections_from_result(result)
                self.result_queue.put({
                    "orig": frame,
                    "annotated": annotated,
                    "detections": detections
                })
            except Exception as e:
                print(f"❌ 推理失败: {e}")
        print("🧠 InferenceThread 结束")
        self.stop_event.set()

# ========================= 公共函数 =========================
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

# ========================= 主流程 =========================
def parse_arguments():
    parser = argparse.ArgumentParser(description='YOLO 实时检测（多线程采集+推理 + Redis + RTMP 推流）')
    parser.add_argument('--model', type=str, default='yolov8m.pt', help='模型路径')
    parser.add_argument('--source', type=str, default='0', help='输入源（文件路径或摄像头索引）')
    parser.add_argument('--conf', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.85, help='IOU 阈值')
    parser.add_argument('--device', type=str, default='cuda:0', help='计算设备，如 cuda:0 / cpu / auto')
    parser.add_argument('--imgsz', type=int, nargs='+', default=[1280, 720], help='(可选) 统一缩放尺寸，当前未强制使用')
    parser.add_argument('--redis-host', type=str, default='124.71.162.119', help='Redis服务器地址')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    parser.add_argument('--redis-db', type=int, default=0, help='Redis DB')
    parser.add_argument('--redis-password', type=str, default=None, help='Redis密码')
    parser.add_argument('--disable-redis', action='store_true', help='禁用Redis')
    return parser.parse_args()

def main():
    args = parse_arguments()
    try:
        src = int(args.source)
    except ValueError:
        src = args.source

    device = 'cuda:0' if (args.device == 'auto' and torch.cuda.is_available()) else args.device
    print(f"🚀 使用设备: {device.upper()}")

    model = YOLO(args.model).to(device)
    print(f"✅ 已加载模型: {args.model}")

    redis_publisher = None
    if not args.disable_redis:
        redis_publisher = RedisDetectionPublisher(
            host=args.redis_host, port=args.redis_port, db=args.redis_db, password=args.redis_password
        )

    rtmp_streamer = RtmpStreamer()
    rtmp_streamer.start()

    frame_queue: queue.Queue = queue.Queue(maxsize=8)
    result_queue: queue.Queue = queue.Queue(maxsize=8)
    stop_event = threading.Event()

    # 如果想强制推理输入统一尺寸，可把 enforce_resize 换成 list，例如:
    # enforce_resize = args.imgsz if len(args.imgsz) == 2 else None
    enforce_resize = None

    capture_thread = CaptureThread(src, frame_queue, stop_event)
    inference_thread = InferenceThread(
        model=model,
        frame_queue=frame_queue,
        result_queue=result_queue,
        stop_event=stop_event,
        conf=args.conf,
        iou=args.iou,
        device=device,
        enforce_resize=enforce_resize
    )

    capture_thread.start()
    inference_thread.start()

    frame_count = 0
    detection_total = 0
    start_time = time.time()

    try:
        while not stop_event.is_set():
            try:
                item = result_queue.get(timeout=0.5)
            except queue.Empty:
                if not capture_thread.is_alive() and result_queue.empty():
                    print("⚠️ 无更多帧，结束主循环")
                    break
                continue

            frame_count += 1
            orig = item['orig']
            annotated = item['annotated']
            detections = item['detections']
            detection_total += len(detections)

            if redis_publisher and detections:
                redis_publisher.publish_detection_metadata(detections)

            rtmp_streamer.write(annotated)

            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0.0
            stats = [
                f"FPS: {fps:.1f}",
                f"Frames: {frame_count}",
                f"Detections: {detection_total}",
                f"Redis: {'ON' if (redis_publisher and redis_publisher.redis_client) else 'OFF'}",
                f"RTMP: {'ON' if rtmp_streamer.started else 'OFF'}"
            ]
            for i, txt in enumerate(stats):
                cv2.putText(annotated, txt, (10, 30 + i * 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            disp = cv2.hconcat([orig, annotated])
            dh, dw = disp.shape[:2]
            disp_small = cv2.resize(disp, (dw // 2, dh // 2))
            cv2.imshow("YOLOv8 多线程 + Redis + RTMP - ESC退出", disp_small)
            if cv2.waitKey(1) == 27:
                print("🛑 用户退出")
                stop_event.set()
                break

            if frame_count % 200 == 0 and redis_publisher:
                stats_r = redis_publisher.get_detection_stats()
                if stats_r:
                    print(f"📊 Redis统计: image:metadata:updates键数={stats_r.get('total_image:metadata:updates', 0)}")

    finally:
        stop_event.set()
        capture_thread.join(timeout=2)
        inference_thread.join(timeout=2)
        rtmp_streamer.close()
        cv2.destroyAllWindows()

        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0.0
        print("\n🏁 结束汇总:")
        print(f"  总帧数: {frame_count}")
        print(f"  总检测: {detection_total}")
        print(f"  平均FPS: {avg_fps:.1f}")
        print(f"  总耗时: {total_time:.1f}s")

        if redis_publisher:
            final_stats = redis_publisher.get_detection_stats()
            if final_stats:
                print(f"  Redis数据: {final_stats}")

if __name__ == "__main__":
    main()