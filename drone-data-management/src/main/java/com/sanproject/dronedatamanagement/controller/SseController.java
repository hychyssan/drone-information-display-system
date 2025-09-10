package com.sanproject.dronedatamanagement.controller;

import com.sanproject.dronedatamanagement.dto.ImageMetadata;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@RestController
@RequestMapping("/api/image-metadata")
public class SseController {

    private static final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    /**
     * 客户端订阅SSE的端点
     */
    @GetMapping("/stream")
    public SseEmitter subscribeToMetadata() {
        SseEmitter emitter = new SseEmitter(60_0000L); // 设置超时时间（例如6000秒）
        emitters.add(emitter);

        System.out.println("添加SSE连接");

        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        System.out.println("SSE成功连接");
        return emitter;
    }

    /**
     * 静态方法，用于将数据发送给所有订阅的客户端
     */
    public static void sendEventToClients(ImageMetadata metadata) {
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(metadata, MediaType.APPLICATION_JSON);
                System.out.println(" ");
            } catch (IOException e) {
                emitter.complete();
                emitters.remove(emitter);
            }
        }
    }
}