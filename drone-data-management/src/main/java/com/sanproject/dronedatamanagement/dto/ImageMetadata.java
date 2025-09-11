package com.sanproject.dronedatamanagement.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ImageMetadata {
    private double timestamp;
    private double centerX;
    private double centerY;
    private double width;
    private double height;
    private double confidence;
    private int peopleCount = 0;
}
