package com.sanproject.drone_data_test.entity;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Getter
@Setter
public class ImageMetadata {
    private Long timestamp;
    private Double centerX;
    private Double centerY;
    private Double width;
    private Double height;
    private Double confidence;
}
