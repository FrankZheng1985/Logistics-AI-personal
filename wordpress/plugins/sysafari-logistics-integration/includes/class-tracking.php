<?php
/**
 * 货物追踪类
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sysafari_Tracking {
    
    /**
     * API客户端
     */
    private $api_client;
    
    /**
     * 构造函数
     */
    public function __construct($api_client) {
        $this->api_client = $api_client;
    }
    
    /**
     * 查询追踪信息
     */
    public function query($tracking_number) {
        // 验证追踪号格式
        $tracking_number = $this->sanitize_tracking_number($tracking_number);
        
        if (empty($tracking_number)) {
            return new WP_Error('invalid_tracking', __('无效的追踪号码', 'sysafari-integration'));
        }
        
        // 检查是否启用追踪功能
        if (!get_option('sysafari_enable_tracking', 1)) {
            return new WP_Error('tracking_disabled', __('追踪功能已禁用', 'sysafari-integration'));
        }
        
        // 尝试从缓存获取
        $cache_key = 'sysafari_tracking_' . md5($tracking_number);
        $cached = get_transient($cache_key);
        
        if ($cached !== false) {
            return $cached;
        }
        
        // 调用API
        $response = $this->api_client->post('/website/tracking', array(
            'tracking_number' => $tracking_number,
        ));
        
        // 如果API调用失败，尝试使用模拟数据（开发环境）
        if (is_wp_error($response)) {
            // 检查是否是连接错误，如果是则返回模拟数据
            if (defined('WP_DEBUG') && WP_DEBUG) {
                return $this->get_mock_data($tracking_number);
            }
            return $response;
        }
        
        // 缓存结果（5分钟）
        set_transient($cache_key, $response, 5 * MINUTE_IN_SECONDS);
        
        return $response;
    }
    
    /**
     * 批量查询追踪信息
     */
    public function query_batch($tracking_numbers) {
        $results = array();
        
        foreach ($tracking_numbers as $number) {
            $results[$number] = $this->query($number);
        }
        
        return $results;
    }
    
    /**
     * 清理追踪号
     */
    private function sanitize_tracking_number($tracking_number) {
        // 移除空格和特殊字符
        $tracking_number = preg_replace('/[^a-zA-Z0-9-]/', '', $tracking_number);
        return strtoupper(trim($tracking_number));
    }
    
    /**
     * 获取模拟追踪数据（开发环境使用）
     */
    private function get_mock_data($tracking_number) {
        // 模拟不同状态的追踪数据
        $statuses = array('pending', 'in_transit', 'delivered');
        $status = $statuses[array_rand($statuses)];
        
        $timeline = array();
        $base_time = time();
        
        // 生成模拟时间线
        $events = array(
            array('status' => '快件已揽收', 'location' => '深圳分拨中心'),
            array('status' => '离开深圳分拨中心，发往香港', 'location' => '深圳分拨中心'),
            array('status' => '到达香港国际机场', 'location' => '香港'),
            array('status' => '航班起飞', 'location' => '香港国际机场'),
            array('status' => '到达目的地机场', 'location' => '洛杉矶国际机场'),
            array('status' => '清关中', 'location' => '美国海关'),
            array('status' => '清关完成，正在派送', 'location' => '洛杉矶配送中心'),
        );
        
        if ($status === 'delivered') {
            $events[] = array('status' => '已签收', 'location' => '目的地');
        }
        
        $count = $status === 'pending' ? 2 : ($status === 'in_transit' ? 5 : count($events));
        
        for ($i = 0; $i < min($count, count($events)); $i++) {
            $timeline[] = array(
                'time'     => date('Y-m-d H:i:s', $base_time - ($count - $i) * 3600 * 6),
                'status'   => $events[$i]['status'],
                'location' => $events[$i]['location'],
            );
        }
        
        // 时间倒序
        $timeline = array_reverse($timeline);
        
        return array(
            'tracking_number' => $tracking_number,
            'status'          => $status,
            'status_text'     => $this->get_status_text($status),
            'origin'          => '深圳, 中国',
            'destination'     => '洛杉矶, 美国',
            'estimated_delivery' => date('Y-m-d', $base_time + 86400 * 2),
            'timeline'        => $timeline,
            'is_mock'         => true, // 标记为模拟数据
        );
    }
    
    /**
     * 获取状态文本
     */
    private function get_status_text($status) {
        $status_texts = array(
            'pending'    => __('处理中', 'sysafari-integration'),
            'in_transit' => __('运输中', 'sysafari-integration'),
            'delivered'  => __('已签收', 'sysafari-integration'),
            'exception'  => __('异常', 'sysafari-integration'),
        );
        
        return isset($status_texts[$status]) ? $status_texts[$status] : $status;
    }
    
    /**
     * 清除追踪缓存
     */
    public function clear_cache($tracking_number = null) {
        if ($tracking_number) {
            $cache_key = 'sysafari_tracking_' . md5($tracking_number);
            delete_transient($cache_key);
        } else {
            // 清除所有追踪缓存
            global $wpdb;
            $wpdb->query(
                "DELETE FROM {$wpdb->options} 
                 WHERE option_name LIKE '_transient_sysafari_tracking_%' 
                 OR option_name LIKE '_transient_timeout_sysafari_tracking_%'"
            );
        }
    }
}
