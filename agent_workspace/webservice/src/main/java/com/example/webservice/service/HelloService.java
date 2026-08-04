package com.example.webservice.service;

import org.springframework.stereotype.Service;

@Service
public class HelloService {
    public String message() {
        return "Hello from the webservice";
    }
}
