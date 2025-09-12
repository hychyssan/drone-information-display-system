package com.sanproject.drone_data_test.saveData;

import com.sanproject.drone_data_test.entity.ImageMetadata;
import jakarta.annotation.Resource;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.awt.*;
import java.time.LocalDate;

@Component
public class DataSaveTask {
    @Resource
    StringRedisTemplate stringRedisTemplate;


    String key = "image_metadata";
    //定时模拟将图像数据存储到redis中
    @Scheduled(fixedRate = 500)
    public void save(){
        ImageMetadata imageMetadata = new ImageMetadata();
        String currentTime = System.currentTimeMillis() + "";
        key = "image_metadata:" + currentTime;

        System.out.println("开始存储数据");

        Double confidence = Math.random() * 60 + 40;


        imageMetadata.setCenterX(10.0);
        imageMetadata.setCenterY(20.0);
        imageMetadata.setWidth(400.0);
        imageMetadata.setHeight(300.0);
        imageMetadata.setConfidence(confidence);
        imageMetadata.setTimestamp(System.currentTimeMillis());

        //存储数据
        stringRedisTemplate.opsForHash().put(key, "timestamp", currentTime);
        stringRedisTemplate.opsForHash().put(key, "center_x", imageMetadata.getCenterX().toString());
        stringRedisTemplate.opsForHash().put(key, "center_y", imageMetadata.getCenterY().toString());
        stringRedisTemplate.opsForHash().put(key, "width", imageMetadata.getWidth().toString());
        stringRedisTemplate.opsForHash().put(key, "height", imageMetadata.getHeight().toString());
        stringRedisTemplate.opsForHash().put(key, "confidence", imageMetadata.getConfidence().toString());

        stringRedisTemplate.convertAndSend("image:metadata:updates", key);
        System.out.println("键为" + key + "的数据存储并发布成功");
    }

}
