package com.sanproject.drone_data_test.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);

        // 使用 StringRedisSerializer 来序列化和反序列化 Redis 的 key 值
        StringRedisSerializer stringSerializer = new StringRedisSerializer();
        // 使用 GenericJackson2JsonRedisSerializer 来序列化和反序列化 Redis 的 value 值
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();

        // 设置 key 和 value 的序列化方式
        template.setKeySerializer(stringSerializer); // 普通键
        template.setValueSerializer(jsonSerializer); // 普通值，这是你原来配置缺少的部分[4,6](@ref)

        // 设置 hash key 和 value 的序列化方式
        template.setHashKeySerializer(stringSerializer); // Hash 结构的键
        template.setHashValueSerializer(jsonSerializer); // Hash 结构的值，你已设置

        template.afterPropertiesSet();
        return template;
    }
}