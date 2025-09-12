package com.sanproject.dronedatamanagement.utils;

import com.sanproject.dronedatamanagement.controller.SseController;
import com.sanproject.dronedatamanagement.dto.ImageMetadata;
import com.sanproject.dronedatamanagement.service.SseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class RedisMessageSubscriber implements MessageListener {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private SseService sseService;


    /**
     * 2. 重写onMessage方法，这是Spring收到Redis消息后的回调入口
     */

    @Override
    public void onMessage(Message message, byte[] pattern) {
        // 从Message对象中直接解析出消息内容，这通常是你在Redis中publish的字符串
        String metadataKey = new String(message.getBody()); // 例如: "image_metadata:1757493783675"
        String channel = new String(message.getChannel());

        System.out.println("收到Redis消息，频道: " + channel + ", 内容: " + metadataKey);

        // 3. 调用你现有的处理逻辑
        handleMessage(metadataKey);
    }


    /**
     * 处理收到的新图像元数据通知
     * 这里通常只是接收到消息（如metadataKey），然后触发后续获取详细数据的操作
     * 实际获取数据和处理逻辑可能放在Service中
     */
    public void handleMessage(String metadataKey) {
        // 根据收到的key，获取Hash中的所有数据

        Map<Object, Object> metaDataMap = null;
        try {
            metaDataMap = redisTemplate.opsForHash().entries(metadataKey);
        } catch (Exception e) {
            System.out.println("错误的metadatakey为：" + metadataKey);
            throw new RuntimeException(e);
        }
        ImageMetadata metadata = null;

        try {
            // 将Map转换为DTO或直接使用
            metadata = new ImageMetadata();
            metadata.setTimestamp(Double.parseDouble(metaDataMap.get("timestamp").toString()));
            metadata.setCenterX(Double.parseDouble(metaDataMap.get("center_x").toString()));
            metadata.setCenterY(Double.parseDouble(metaDataMap.get("center_y").toString()));
            metadata.setWidth(Double.parseDouble(metaDataMap.get("width").toString()));
            metadata.setHeight(Double.parseDouble(metaDataMap.get("height").toString()));
            metadata.setConfidence(Double.parseDouble(metaDataMap.get("confidence").toString()));
            //计算当前帧人数
            metadata.setPeopleCount(sseService.countPeople((long) (metadata.getTimestamp())));
        } catch (Exception e) {
            System.out.println("错误的metadata为：" + metadata.toString());
            System.out.println("metadatakey为：" + metadataKey);
            throw new RuntimeException(e);
        }

        // 此处应将数据发送给客户端，例如通过SSE emitter
        // 见后续的Controller部分
        System.out.println("metadatakey为：" + metadataKey);
        System.out.println("接下来将数据发送给客户端！");
        SseController.sendEventToClients(metadata);
        System.out.println("已将数据发送给客户端！");
    }
}