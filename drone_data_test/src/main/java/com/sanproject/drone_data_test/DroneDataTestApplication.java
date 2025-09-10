package com.sanproject.drone_data_test;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class DroneDataTestApplication {

	public static void main(String[] args) {
		SpringApplication.run(DroneDataTestApplication.class, args);
	}

}
