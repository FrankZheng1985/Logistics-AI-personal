<?php
/**
 * 客户数据同步类
 * 
 * 处理WordPress用户与AI系统客户数据的双向同步
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sysafari_Customer_Sync {
    
    /**
     * API客户端
     */
    private $api_client;
    
    /**
     * 构造函数
     */
    public function __construct($api_client) {
        $this->api_client = $api_client;
        $this->init_hooks();
    }
    
    /**
     * 初始化钩子
     */
    private function init_hooks() {
        // 用户注册时同步
        add_action('user_register', array($this, 'sync_on_register'), 10, 1);
        
        // 用户资料更新时同步
        add_action('profile_update', array($this, 'sync_on_update'), 10, 2);
        
        // 定时同步任务
        add_action('sysafari_sync_customers_cron', array($this, 'scheduled_sync'));
        
        // 注册定时任务
        if (!wp_next_scheduled('sysafari_sync_customers_cron')) {
            wp_schedule_event(time(), 'hourly', 'sysafari_sync_customers_cron');
        }
    }
    
    /**
     * 用户注册时同步
     */
    public function sync_on_register($user_id) {
        if (!get_option('sysafari_sync_customers', 0)) {
            return;
        }
        
        $this->sync_user_to_api($user_id);
    }
    
    /**
     * 用户更新时同步
     */
    public function sync_on_update($user_id, $old_user_data) {
        if (!get_option('sysafari_sync_customers', 0)) {
            return;
        }
        
        $this->sync_user_to_api($user_id);
    }
    
    /**
     * 同步用户到API
     */
    public function sync_user_to_api($user_id) {
        $user = get_userdata($user_id);
        
        if (!$user) {
            return new WP_Error('user_not_found', __('用户不存在', 'sysafari-integration'));
        }
        
        // 构建客户数据
        $customer_data = array(
            'source'     => 'wordpress',
            'wp_user_id' => $user_id,
            'name'       => $user->display_name,
            'email'      => $user->user_email,
            'phone'      => get_user_meta($user_id, 'phone', true),
            'company'    => get_user_meta($user_id, 'company', true),
            'address'    => get_user_meta($user_id, 'address', true),
            'registered_at' => $user->user_registered,
        );
        
        // 检查是否已同步过
        $api_customer_id = get_user_meta($user_id, '_sysafari_customer_id', true);
        
        if ($api_customer_id) {
            // 更新现有客户
            $response = $this->api_client->put('/customers/' . $api_customer_id, $customer_data);
        } else {
            // 创建新客户
            $response = $this->api_client->post('/customers', $customer_data);
            
            if (!is_wp_error($response) && isset($response['id'])) {
                update_user_meta($user_id, '_sysafari_customer_id', $response['id']);
            }
        }
        
        if (is_wp_error($response)) {
            error_log('Customer sync failed for user ' . $user_id . ': ' . $response->get_error_message());
            return $response;
        }
        
        // 记录同步时间
        update_user_meta($user_id, '_sysafari_last_sync', current_time('mysql'));
        
        return true;
    }
    
    /**
     * 从API同步客户到WordPress
     */
    public function sync_from_api($customer_data) {
        // 根据邮箱查找用户
        $user = get_user_by('email', $customer_data['email']);
        
        if ($user) {
            // 更新现有用户
            $user_id = $user->ID;
            
            wp_update_user(array(
                'ID'           => $user_id,
                'display_name' => $customer_data['name'],
            ));
            
        } else {
            // 创建新用户
            $user_id = wp_create_user(
                sanitize_user($customer_data['email']),
                wp_generate_password(),
                $customer_data['email']
            );
            
            if (is_wp_error($user_id)) {
                return $user_id;
            }
            
            wp_update_user(array(
                'ID'           => $user_id,
                'display_name' => $customer_data['name'],
            ));
        }
        
        // 更新用户元数据
        if (!empty($customer_data['phone'])) {
            update_user_meta($user_id, 'phone', $customer_data['phone']);
        }
        if (!empty($customer_data['company'])) {
            update_user_meta($user_id, 'company', $customer_data['company']);
        }
        if (!empty($customer_data['address'])) {
            update_user_meta($user_id, 'address', $customer_data['address']);
        }
        
        // 保存API客户ID
        if (!empty($customer_data['id'])) {
            update_user_meta($user_id, '_sysafari_customer_id', $customer_data['id']);
        }
        
        update_user_meta($user_id, '_sysafari_last_sync', current_time('mysql'));
        
        return $user_id;
    }
    
    /**
     * 定时同步任务
     */
    public function scheduled_sync() {
        if (!get_option('sysafari_sync_customers', 0)) {
            return;
        }
        
        // 获取需要同步的用户（24小时内未同步）
        $users = get_users(array(
            'meta_query' => array(
                'relation' => 'OR',
                array(
                    'key'     => '_sysafari_last_sync',
                    'compare' => 'NOT EXISTS',
                ),
                array(
                    'key'     => '_sysafari_last_sync',
                    'value'   => date('Y-m-d H:i:s', strtotime('-24 hours')),
                    'compare' => '<',
                    'type'    => 'DATETIME',
                ),
            ),
            'number' => 50,
        ));
        
        foreach ($users as $user) {
            $this->sync_user_to_api($user->ID);
            
            // 避免API限流
            usleep(100000); // 100ms
        }
    }
    
    /**
     * 手动批量同步
     */
    public function bulk_sync() {
        $users = get_users(array('number' => -1));
        
        $synced = 0;
        $failed = 0;
        
        foreach ($users as $user) {
            $result = $this->sync_user_to_api($user->ID);
            
            if (is_wp_error($result)) {
                $failed++;
            } else {
                $synced++;
            }
            
            usleep(100000);
        }
        
        return array(
            'synced' => $synced,
            'failed' => $failed,
            'total'  => count($users),
        );
    }
    
    /**
     * 获取同步状态
     */
    public function get_sync_status() {
        global $wpdb;
        
        $total_users = count_users();
        
        $synced_count = $wpdb->get_var(
            "SELECT COUNT(*) FROM {$wpdb->usermeta} WHERE meta_key = '_sysafari_customer_id'"
        );
        
        $last_sync = $wpdb->get_var(
            "SELECT meta_value FROM {$wpdb->usermeta} 
             WHERE meta_key = '_sysafari_last_sync' 
             ORDER BY meta_value DESC LIMIT 1"
        );
        
        return array(
            'total_users'  => $total_users['total_users'],
            'synced_count' => intval($synced_count),
            'last_sync'    => $last_sync,
            'enabled'      => (bool) get_option('sysafari_sync_customers', 0),
        );
    }
}
