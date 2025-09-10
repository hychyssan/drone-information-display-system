package com.sanproject.dronedatamanagement.controller;

import cn.hutool.core.lang.UUID;
import com.sanproject.dronedatamanagement.dto.ImageMetadata;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

@RestController
@RequestMapping("/api/image-metadata")
public class SseController {

    private static final ConcurrentHashMap<String, SseEmitter> emitters = new ConcurrentHashMap<>();
    private static final ScheduledExecutorService heartbeatExecutor = Executors.newSingleThreadScheduledExecutor();

    /**
     * 客户端订阅SSE的端点
     */
    @GetMapping("/stream")
    public SseEmitter subscribeToMetadata() {
        String connectionId = UUID.randomUUID().toString();
        SseEmitter emitter = new SseEmitter(300_000L); // 设置超时时间（例如6000秒）

        emitters.put(connectionId, emitter);    //注册新连接
        System.out.println("SSE连接已建立, ID: " + connectionId + ", 当前连接数: " + emitters.size());

        // 设置心跳
        ScheduledFuture<?> heartbeatFuture = heartbeatExecutor.scheduleAtFixedRate(() -> {
            try {
                emitter.send(SseEmitter.event().comment("heartbeat"));
            } catch (IOException e) {
                System.out.println("心跳发送失败: " + connectionId);
            }
        }, 25, 25, TimeUnit.SECONDS);

        // 设置生命周期回调
        emitter.onCompletion(() -> cleanupConnection(connectionId, heartbeatFuture));
        emitter.onTimeout(() -> cleanupConnection(connectionId, heartbeatFuture));
        emitter.onError((throwable) -> cleanupConnection(connectionId, heartbeatFuture));

        System.out.println("SSE成功连接");
        return emitter;
    }

    private void cleanupConnection(String connectionId, ScheduledFuture<?> heartbeatFuture) {
        // 1. 从管理器中移除
        SseEmitter emitter = emitters.remove(connectionId);
        if (emitter != null) {
            emitter.complete();
        }
        // 2. 取消心跳任务
        if (heartbeatFuture != null) {
            heartbeatFuture.cancel(true);
        }
        System.out.println("连接 [" + connectionId + "] 已清理, 当前连接数: " + emitters.size());
    }

    /**
     * 静态方法，用于将数据发送给所有订阅的客户端
     */
    public static void sendEventToClients(ImageMetadata metadata) {
        // 遍历所有连接，发送数据
        Iterator<Map.Entry<String, SseEmitter>> iterator = emitters.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, SseEmitter> entry = iterator.next();
            SseEmitter emitter = entry.getValue();
            try {
                emitter.send(metadata, MediaType.APPLICATION_JSON);
            } catch (IOException e) {
                // 发送失败，说明客户端已断开，清理该连接
                System.out.println("发送失败，清理连接: " + entry.getKey());
                emitter.complete();
                iterator.remove(); // 从Map中移除
            }
        }
    }
}