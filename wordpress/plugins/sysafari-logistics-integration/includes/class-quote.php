<?php
/**
 * 报价请求类
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sysafari_Quote {
    
    /**
     * API客户端
     */
    private $api_client;
    
    /**
     * 数据库表名
     */
    private $table_name;
    
    /**
     * 构造函数
     */
    public function __construct($api_client) {
        global $wpdb;
        $this->api_client = $api_client;
        $this->table_name = $wpdb->prefix . 'sysafari_quote_requests';
    }
    
    /**
     * 创建报价请求
     */
    public function create($data) {
        global $wpdb;
        
        // 验证必填字段
        $required = array('name', 'email', 'origin', 'destination');
        foreach ($required as $field) {
            if (empty($data[$field])) {
                return new WP_Error('missing_field', sprintf(__('缺少必填字段: %s', 'sysafari-integration'), $field));
            }
        }
        
        // 验证邮箱格式
        if (!is_email($data['email'])) {
            return new WP_Error('invalid_email', __('邮箱格式不正确', 'sysafari-integration'));
        }
        
        // 准备插入数据
        $insert_data = array(
            'name'         => sanitize_text_field($data['name']),
            'email'        => sanitize_email($data['email']),
            'phone'        => isset($data['phone']) ? sanitize_text_field($data['phone']) : '',
            'company'      => isset($data['company']) ? sanitize_text_field($data['company']) : '',
            'origin'       => sanitize_text_field($data['origin']),
            'destination'  => sanitize_text_field($data['destination']),
            'service_type' => isset($data['service_type']) ? sanitize_text_field($data['service_type']) : '',
            'cargo_type'   => isset($data['cargo_type']) ? sanitize_text_field($data['cargo_type']) : '',
            'weight'       => isset($data['weight']) ? floatval($data['weight']) : 0,
            'dimensions'   => isset($data['dimensions']) ? sanitize_text_field($data['dimensions']) : '',
            'quantity'     => isset($data['quantity']) ? intval($data['quantity']) : 1,
            'ship_date'    => !empty($data['ship_date']) ? sanitize_text_field($data['ship_date']) : null,
            'message'      => isset($data['message']) ? sanitize_textarea_field($data['message']) : '',
            'status'       => 'pending',
        );
        
        // 插入数据库
        $result = $wpdb->insert($this->table_name, $insert_data);
        
        if ($result === false) {
            return new WP_Error('db_error', __('保存报价请求失败', 'sysafari-integration'));
        }
        
        $quote_id = $wpdb->insert_id;
        
        // 触发钩子
        do_action('sysafari_quote_created', $quote_id, $insert_data);
        
        return $quote_id;
    }
    
    /**
     * 获取报价请求
     */
    public function get($id) {
        global $wpdb;
        
        $quote = $wpdb->get_row(
            $wpdb->prepare("SELECT * FROM {$this->table_name} WHERE id = %d", $id),
            ARRAY_A
        );
        
        return $quote;
    }
    
    /**
     * 获取报价请求列表
     */
    public function get_list($args = array()) {
        global $wpdb;
        
        $defaults = array(
            'status'   => '',
            'per_page' => 20,
            'page'     => 1,
            'orderby'  => 'created_at',
            'order'    => 'DESC',
        );
        
        $args = wp_parse_args($args, $defaults);
        
        $where = '1=1';
        $values = array();
        
        if (!empty($args['status'])) {
            $where .= ' AND status = %s';
            $values[] = $args['status'];
        }
        
        $orderby = in_array($args['orderby'], array('id', 'created_at', 'status', 'name')) ? $args['orderby'] : 'created_at';
        $order = strtoupper($args['order']) === 'ASC' ? 'ASC' : 'DESC';
        
        $offset = ($args['page'] - 1) * $args['per_page'];
        
        $sql = "SELECT * FROM {$this->table_name} WHERE {$where} ORDER BY {$orderby} {$order} LIMIT %d OFFSET %d";
        $values[] = $args['per_page'];
        $values[] = $offset;
        
        $quotes = $wpdb->get_results(
            $wpdb->prepare($sql, $values),
            ARRAY_A
        );
        
        // 获取总数
        $count_sql = "SELECT COUNT(*) FROM {$this->table_name} WHERE {$where}";
        if (!empty($args['status'])) {
            $total = $wpdb->get_var($wpdb->prepare($count_sql, $args['status']));
        } else {
            $total = $wpdb->get_var($count_sql);
        }
        
        return array(
            'items'      => $quotes,
            'total'      => intval($total),
            'page'       => $args['page'],
            'per_page'   => $args['per_page'],
            'total_pages' => ceil($total / $args['per_page']),
        );
    }
    
    /**
     * 更新报价请求状态
     */
    public function update_status($id, $status) {
        global $wpdb;
        
        $valid_statuses = array('pending', 'processing', 'quoted', 'accepted', 'rejected', 'completed');
        
        if (!in_array($status, $valid_statuses)) {
            return new WP_Error('invalid_status', __('无效的状态值', 'sysafari-integration'));
        }
        
        $result = $wpdb->update(
            $this->table_name,
            array('status' => $status),
            array('id' => $id)
        );
        
        if ($result === false) {
            return new WP_Error('db_error', __('更新状态失败', 'sysafari-integration'));
        }
        
        do_action('sysafari_quote_status_updated', $id, $status);
        
        return true;
    }
    
    /**
     * 同步到AI系统
     */
    public function sync_to_api($quote_id) {
        global $wpdb;
        
        $quote = $this->get($quote_id);
        
        if (!$quote) {
            return new WP_Error('not_found', __('报价请求不存在', 'sysafari-integration'));
        }
        
        // 如果已同步，跳过
        if ($quote['synced_to_api']) {
            return true;
        }
        
        // 构建API请求数据
        $api_data = array(
            'source'      => 'website_quote',
            'name'        => $quote['name'],
            'email'       => $quote['email'],
            'phone'       => $quote['phone'],
            'company'     => $quote['company'],
            'content'     => sprintf(
                "报价请求:\n起运地: %s\n目的地: %s\n服务类型: %s\n货物类型: %s\n重量: %s KG\n尺寸: %s\n数量: %s\n备注: %s",
                $quote['origin'],
                $quote['destination'],
                $quote['service_type'],
                $quote['cargo_type'],
                $quote['weight'],
                $quote['dimensions'],
                $quote['quantity'],
                $quote['message']
            ),
            'extra_data'  => array(
                'wp_quote_id'  => $quote_id,
                'origin'       => $quote['origin'],
                'destination'  => $quote['destination'],
                'service_type' => $quote['service_type'],
                'cargo_type'   => $quote['cargo_type'],
                'weight'       => $quote['weight'],
                'dimensions'   => $quote['dimensions'],
                'quantity'     => $quote['quantity'],
                'ship_date'    => $quote['ship_date'],
            ),
        );
        
        // 调用API
        $response = $this->api_client->post('/website/quote-request', $api_data);
        
        if (is_wp_error($response)) {
            // 记录错误但不阻止流程
            error_log('Sysafari API sync failed: ' . $response->get_error_message());
            return $response;
        }
        
        // 更新同步状态
        $api_lead_id = isset($response['id']) ? $response['id'] : null;
        
        $wpdb->update(
            $this->table_name,
            array(
                'synced_to_api' => 1,
                'api_lead_id'   => $api_lead_id,
            ),
            array('id' => $quote_id)
        );
        
        return true;
    }
    
    /**
     * 批量同步到API
     */
    public function sync_pending_to_api() {
        global $wpdb;
        
        $pending = $wpdb->get_results(
            "SELECT id FROM {$this->table_name} WHERE synced_to_api = 0 LIMIT 50",
            ARRAY_A
        );
        
        $synced = 0;
        $failed = 0;
        
        foreach ($pending as $quote) {
            $result = $this->sync_to_api($quote['id']);
            if (is_wp_error($result)) {
                $failed++;
            } else {
                $synced++;
            }
        }
        
        return array(
            'synced' => $synced,
            'failed' => $failed,
        );
    }
    
    /**
     * 删除报价请求
     */
    public function delete($id) {
        global $wpdb;
        
        $result = $wpdb->delete($this->table_name, array('id' => $id));
        
        if ($result === false) {
            return new WP_Error('db_error', __('删除失败', 'sysafari-integration'));
        }
        
        return true;
    }
    
    /**
     * 获取统计数据
     */
    public function get_stats() {
        global $wpdb;
        
        $stats = array();
        
        // 总数
        $stats['total'] = $wpdb->get_var("SELECT COUNT(*) FROM {$this->table_name}");
        
        // 按状态统计
        $by_status = $wpdb->get_results(
            "SELECT status, COUNT(*) as count FROM {$this->table_name} GROUP BY status",
            ARRAY_A
        );
        
        $stats['by_status'] = array();
        foreach ($by_status as $row) {
            $stats['by_status'][$row['status']] = intval($row['count']);
        }
        
        // 今日新增
        $stats['today'] = $wpdb->get_var(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE DATE(created_at) = CURDATE()"
        );
        
        // 本周新增
        $stats['this_week'] = $wpdb->get_var(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        );
        
        // 本月新增
        $stats['this_month'] = $wpdb->get_var(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())"
        );
        
        return $stats;
    }
}
