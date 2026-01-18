<?php
/**
 * API客户端类
 * 
 * 封装与物流AI系统后端的HTTP通信
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sysafari_API_Client {
    
    /**
     * API基础URL
     */
    private $base_url;
    
    /**
     * API密钥
     */
    private $api_key;
    
    /**
     * 请求超时时间（秒）
     */
    private $timeout = 30;
    
    /**
     * 构造函数
     */
    public function __construct() {
        $this->base_url = rtrim(get_option('sysafari_api_base_url', 'http://localhost:8000/api/v1'), '/');
        $this->api_key = get_option('sysafari_api_key', '');
    }
    
    /**
     * 发送GET请求
     */
    public function get($endpoint, $params = array()) {
        $url = $this->build_url($endpoint, $params);
        
        $response = wp_remote_get($url, array(
            'headers' => $this->get_headers(),
            'timeout' => $this->timeout,
        ));
        
        return $this->handle_response($response);
    }
    
    /**
     * 发送POST请求
     */
    public function post($endpoint, $data = array()) {
        $url = $this->build_url($endpoint);
        
        $response = wp_remote_post($url, array(
            'headers' => $this->get_headers(),
            'body'    => json_encode($data),
            'timeout' => $this->timeout,
        ));
        
        return $this->handle_response($response);
    }
    
    /**
     * 发送PUT请求
     */
    public function put($endpoint, $data = array()) {
        $url = $this->build_url($endpoint);
        
        $response = wp_remote_request($url, array(
            'method'  => 'PUT',
            'headers' => $this->get_headers(),
            'body'    => json_encode($data),
            'timeout' => $this->timeout,
        ));
        
        return $this->handle_response($response);
    }
    
    /**
     * 发送DELETE请求
     */
    public function delete($endpoint) {
        $url = $this->build_url($endpoint);
        
        $response = wp_remote_request($url, array(
            'method'  => 'DELETE',
            'headers' => $this->get_headers(),
            'timeout' => $this->timeout,
        ));
        
        return $this->handle_response($response);
    }
    
    /**
     * 构建请求URL
     */
    private function build_url($endpoint, $params = array()) {
        $url = $this->base_url . '/' . ltrim($endpoint, '/');
        
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }
        
        return $url;
    }
    
    /**
     * 获取请求头
     */
    private function get_headers() {
        $headers = array(
            'Content-Type'  => 'application/json',
            'Accept'        => 'application/json',
            'User-Agent'    => 'Sysafari-WordPress-Plugin/' . SYSAFARI_INTEGRATION_VERSION,
        );
        
        if (!empty($this->api_key)) {
            $headers['Authorization'] = 'Bearer ' . $this->api_key;
        }
        
        return $headers;
    }
    
    /**
     * 处理响应
     */
    private function handle_response($response) {
        // 检查WP错误
        if (is_wp_error($response)) {
            return $response;
        }
        
        // 获取响应码和正文
        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        
        // 解析JSON
        $data = json_decode($body, true);
        
        // 检查HTTP状态码
        if ($status_code >= 400) {
            $error_message = isset($data['detail']) ? $data['detail'] : 
                            (isset($data['message']) ? $data['message'] : 
                            (isset($data['error']) ? $data['error'] : __('API请求失败', 'sysafari-integration')));
            
            return new WP_Error('api_error', $error_message, array('status' => $status_code));
        }
        
        return $data;
    }
    
    /**
     * 测试API连接
     */
    public function test_connection() {
        $response = $this->get('/health');
        
        if (is_wp_error($response)) {
            return array(
                'success' => false,
                'message' => $response->get_error_message(),
            );
        }
        
        return array(
            'success' => true,
            'message' => __('API连接成功', 'sysafari-integration'),
            'data'    => $response,
        );
    }
    
    /**
     * 设置超时时间
     */
    public function set_timeout($seconds) {
        $this->timeout = max(1, intval($seconds));
    }
    
    /**
     * 获取基础URL
     */
    public function get_base_url() {
        return $this->base_url;
    }
    
    /**
     * 检查是否已配置API
     */
    public function is_configured() {
        return !empty($this->base_url);
    }
}
