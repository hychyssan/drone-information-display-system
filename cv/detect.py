"""
基于Ultralytics官方API的实时检测代码（修复属性错误）
参考：https://docs.ultralytics.com/zh/modes/predict/#videos
"""
import os
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'
import argparse
import cv2
import torch
from ultralytics import YOLO


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='YOLO实时检测')
    parser.add_argument('--model', type=str, default='yolov8m.pt', help='模型路径')
    #parser.add_argument('--source', type=str, default='rtmp://alg.xinkongan.com/live/wind_pro_1581F5FJC24BW00D5JP3', help='输入源（摄像头ID或视频路径）')
    #parser.add_argument('--source', type=str, default='rtsp://192.168.144.25:8554/main.264',help='输入源（摄像头ID或视频路径）')#SIYI
    #parser.add_argument('--source', type=str, default='rtmp://47.111.74.113/live/1581F5FJC24BW00D5JP3_67-0-0',help='输入源（摄像头ID或视频路径）')#dji
    parser.add_argument('--source', type=str, default='DJI_20250308135111_0001_S.MP4',help='输入源（摄像头ID或视频路径）')
    #parser.add_argument('--source', type=str, default='PERSON_2.MP4',help='输入源（摄像头ID或视频路径）')
    parser.add_argument('--conf', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.85, help='IOU阈值')
    parser.add_argument('--device', type=str, default='cuda:0', help='计算设备（auto/cpu/cuda:0）')
    parser.add_argument('--imgsz', type=int, nargs='+', default=[1280, 720], help='输入图像尺寸 (高度 宽度)')
    return parser.parse_args()


def main():
    args = parse_arguments()

    # 自动选择设备
    device = 'cuda:0' if args.device == 'auto' and torch.cuda.is_available() else args.device
    print(f"🚀 使用设备: {device.upper()}")

    # 加载模型（自动下载预训练模型）
    model = YOLO(args.model).to(device)
    print(f"✅ 已加载模型: {args.model}")
    print(f"🖼️ 输入分辨率: {args.imgsz}")

    # 自动转换摄像头ID为整数
    try:
        args.source = int(args.source)
    except ValueError:
        pass

    # 实时检测（使用官方推荐的流模式）
    for result in model.predict(
            source=args.source,
            stream=True,  # 启用流模式（内存优化）
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,  # 设置输入分辨率为1280x720
            show=True,  # 使用内置显示（使用自定义显示）
            verbose=True,
            device=device
    ):
        # 获取原始帧和标注帧
        orig_frame = result.orig_img
        annotated_frame = result.plot()

        # 并排显示
        combined = cv2.hconcat([orig_frame, annotated_frame])

        # 显示分辨率调整
        h, w = combined.shape[:2]
        display_frame = cv2.resize(combined, (w // 2, h // 2))

        # 显示结果
        #cv2.imshow('YOLOv8检测 - 按ESC退出', display_frame)

        # 退出机制
        if cv2.waitKey(1) == 27:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()