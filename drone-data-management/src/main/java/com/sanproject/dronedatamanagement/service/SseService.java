package com.sanproject.dronedatamanagement.service;

import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicInteger;

@Component
public class SseService {

   //上一个时间戳
    Long preTimeStamp = 0L;
    //上一帧和当前帧人数
    private final AtomicInteger lastFramePeopleNumber = new AtomicInteger(0);
    private final AtomicInteger currentFrameCount = new AtomicInteger(0);


    public int countPeople(long curTimeStamp){
        //统计上一个时间戳与当前时间戳之差。若小于3ms，判断为新一个人，curPeopleNumber++
        double timeDiff = curTimeStamp - preTimeStamp;
        if(timeDiff <= 3.0 || preTimeStamp == 0L){
            //判断为同一帧不同人数据
            currentFrameCount.incrementAndGet();
            //curPeopleNumber++;
        }else{
            //判断为新一帧数据

            //赋值上一帧总人数
            lastFramePeopleNumber.set(currentFrameCount.get());
            //本帧人数清零
            currentFrameCount.set(0);
        }
        preTimeStamp = curTimeStamp;
        return lastFramePeopleNumber.get();
    }
}
