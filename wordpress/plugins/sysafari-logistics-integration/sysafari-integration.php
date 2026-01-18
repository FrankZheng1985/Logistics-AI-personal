<?php
/**
 * Plugin Name: Sysafari Logistics Integration
 * Plugin URI: https://sysafari.com
 * Description: 物流获客AI系统集成插件，提供货物追踪、报价请求、客户数据同步等功能
 * Version: 1.0.0
 * Author: Sysafari Team
 * Author URI: https://sysafari.com
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: sysafari-integration
 * Domain Path: /languages
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

// 防止直接访问
if (!defined('ABSPATH')) {
    exit;
}

// 插件常量
define('SYSAFARI_INTEGRATION_VERSION', '1.0.0');
define('SYSAFARI_INTEGRATION_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('SYSAFARI_INTEGRATION_PLUGIN_URL', plugin_dir_url(__FILE__));
define('SYSAFARI_INTEGRATION_PLUGIN_BASENAME', plugin_basename(__FILE__));

/**
 * 主插件类
 */
class Sysafari_Logistics_Integration {
    
    /**
     * 单例实例
     */
    private static $instance = null;
    
    /**
     * API客户端
     */
    private $api_client;
    
    /**
     * 获取单例实例
     */
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * 构造函数
     */
    private function __construct() {
        $this->load_dependencies();
        $this->init_hooks();
    }
    
    /**
     * 加载依赖文件
     */
    private function load_dependencies() {
        require_once SYSAFARI_INTEGRATION_PLUGIN_DIR . 'includes/class-api-client.php';
        require_once SYSAFARI_INTEGRATION_PLUGIN_DIR . 'includes/class-tracking.php';
        require_once SYSAFARI_INTEGRATION_PLUGIN_DIR . 'includes/class-quote.php';
        require_once SYSAFARI_INTEGRATION_PLUGIN_DIR . 'includes/class-customer-sync.php';
        
        // 初始化API客户端
        $this->api_client = new Sysafari_API_Client();
    }
    
    /**
     * 初始化钩子
     */
    private function init_hooks() {
        // 激活/停用钩子
        register_activation_hook(__FILE__, array($this, 'activate'));
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));
        
        // 初始化
        add_action('init', array($this, 'init'));
        
        // 管理菜单
        add_action('admin_menu', array($this, 'add_admin_menu'));
        
        // 设置链接
        add_filter('plugin_action_links_' . SYSAFARI_INTEGRATION_PLUGIN_BASENAME, array($this, 'add_settings_link'));
        
        // 注册设置
        add_action('admin_init', array($this, 'register_settings'));
        
        // AJAX处理
        add_action('wp_ajax_sysafari_tracking', array($this, 'ajax_tracking'));
        add_action('wp_ajax_nopriv_sysafari_tracking', array($this, 'ajax_tracking'));
        
        add_action('wp_ajax_sysafari_quote_request', array($this, 'ajax_quote_request'));
        add_action('wp_ajax_nopriv_sysafari_quote_request', array($this, 'ajax_quote_request'));
        
        add_action('wp_ajax_sysafari_contact', array($this, 'ajax_contact'));
        add_action('wp_ajax_nopriv_sysafari_contact', array($this, 'ajax_contact'));
        
        // REST API 端点
        add_action('rest_api_init', array($this, 'register_rest_routes'));
        
        // 加载脚本和样式
        add_action('admin_enqueue_scripts', array($this, 'admin_enqueue_scripts'));
    }
    
    /**
     * 插件激活
     */
    public function activate() {
        // 创建必要的数据库表
        $this->create_tables();
        
        // 设置默认选项
        $this->set_default_options();
        
        // 刷新重写规则
        flush_rewrite_rules();
    }
    
    /**
     * 插件停用
     */
    public function deactivate() {
        flush_rewrite_rules();
    }
    
    /**
     * 创建数据库表
     */
    private function create_tables() {
        global $wpdb;
        
        $charset_collate = $wpdb->get_charset_collate();
        
        // 报价请求表
        $table_quotes = $wpdb->prefix . 'sysafari_quote_requests';
        $sql_quotes = "CREATE TABLE IF NOT EXISTS $table_quotes (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            name varchar(100) NOT NULL,
            email varchar(100) NOT NULL,
            phone varchar(50) DEFAULT '',
            company varchar(200) DEFAULT '',
            origin varchar(200) NOT NULL,
            destination varchar(200) NOT NULL,
            service_type varchar(50) NOT NULL,
            cargo_type varchar(50) DEFAULT '',
            weight decimal(10,2) DEFAULT 0,
            dimensions varchar(100) DEFAULT '',
            quantity int(11) DEFAULT 1,
            ship_date date DEFAULT NULL,
            message text,
            status varchar(20) DEFAULT 'pending',
            synced_to_api tinyint(1) DEFAULT 0,
            api_lead_id bigint(20) DEFAULT NULL,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY  (id),
            KEY email (email),
            KEY status (status),
            KEY created_at (created_at)
        ) $charset_collate;";
        
        // 联系消息表
        $table_contacts = $wpdb->prefix . 'sysafari_contacts';
        $sql_contacts = "CREATE TABLE IF NOT EXISTS $table_contacts (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            name varchar(100) NOT NULL,
            email varchar(100) NOT NULL,
            phone varchar(50) DEFAULT '',
            subject varchar(200) NOT NULL,
            message text NOT NULL,
            status varchar(20) DEFAULT 'unread',
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY  (id),
            KEY email (email),
            KEY status (status)
        ) $charset_collate;";
        
        // 追踪查询日志表
        $table_tracking = $wpdb->prefix . 'sysafari_tracking_logs';
        $sql_tracking = "CREATE TABLE IF NOT EXISTS $table_tracking (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            tracking_number varchar(100) NOT NULL,
            ip_address varchar(45) DEFAULT '',
            user_agent text,
            result_status varchar(50) DEFAULT '',
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY  (id),
            KEY tracking_number (tracking_number),
            KEY created_at (created_at)
        ) $charset_collate;";
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql_quotes);
        dbDelta($sql_contacts);
        dbDelta($sql_tracking);
    }
    
    /**
     * 设置默认选项
     */
    private function set_default_options() {
        $default_options = array(
            'api_base_url'    => 'http://localhost:8000/api/v1',
            'api_key'         => '',
            'enable_tracking' => 1,
            'enable_quote'    => 1,
            'enable_webchat'  => 1,
            'sync_customers'  => 0,
        );
        
        foreach ($default_options as $key => $value) {
            if (get_option('sysafari_' . $key) === false) {
                update_option('sysafari_' . $key, $value);
            }
        }
    }
    
    /**
     * 初始化
     */
    public function init() {
        // 加载文本域
        load_plugin_textdomain('sysafari-integration', false, dirname(SYSAFARI_INTEGRATION_PLUGIN_BASENAME) . '/languages');
    }
    
    /**
     * 添加管理菜单
     */
    public function add_admin_menu() {
        // 主菜单
        add_menu_page(
            __('物流系统集成', 'sysafari-integration'),
            __('物流集成', 'sysafari-integration'),
            'manage_options',
            'sysafari-integration',
            array($this, 'render_dashboard_page'),
            'dashicons-admin-site-alt3',
            30
        );
        
        // 子菜单 - 仪表板
        add_submenu_page(
            'sysafari-integration',
            __('仪表板', 'sysafari-integration'),
            __('仪表板', 'sysafari-integration'),
            'manage_options',
            'sysafari-integration',
            array($this, 'render_dashboard_page')
        );
        
        // 子菜单 - 报价请求
        add_submenu_page(
            'sysafari-integration',
            __('报价请求', 'sysafari-integration'),
            __('报价请求', 'sysafari-integration'),
            'manage_options',
            'sysafari-quotes',
            array($this, 'render_quotes_page')
        );
        
        // 子菜单 - 联系消息
        add_submenu_page(
            'sysafari-integration',
            __('联系消息', 'sysafari-integration'),
            __('联系消息', 'sysafari-integration'),
            'manage_options',
            'sysafari-contacts',
            array($this, 'render_contacts_page')
        );
        
        // 子菜单 - 设置
        add_submenu_page(
            'sysafari-integration',
            __('设置', 'sysafari-integration'),
            __('设置', 'sysafari-integration'),
            'manage_options',
            'sysafari-settings',
            array($this, 'render_settings_page')
        );
    }
    
    /**
     * 添加设置链接
     */
    public function add_settings_link($links) {
        $settings_link = '<a href="admin.php?page=sysafari-settings">' . __('设置', 'sysafari-integration') . '</a>';
        array_unshift($links, $settings_link);
        return $links;
    }
    
    /**
     * 注册设置
     */
    public function register_settings() {
        // API设置
        register_setting('sysafari_settings', 'sysafari_api_base_url');
        register_setting('sysafari_settings', 'sysafari_api_key');
        
        // 功能开关
        register_setting('sysafari_settings', 'sysafari_enable_tracking');
        register_setting('sysafari_settings', 'sysafari_enable_quote');
        register_setting('sysafari_settings', 'sysafari_enable_webchat');
        register_setting('sysafari_settings', 'sysafari_sync_customers');
    }
    
    /**
     * 管理端脚本和样式
     */
    public function admin_enqueue_scripts($hook) {
        if (strpos($hook, 'sysafari') === false) {
            return;
        }
        
        wp_enqueue_style(
            'sysafari-admin',
            SYSAFARI_INTEGRATION_PLUGIN_URL . 'assets/css/admin.css',
            array(),
            SYSAFARI_INTEGRATION_VERSION
        );
        
        wp_enqueue_script(
            'sysafari-admin',
            SYSAFARI_INTEGRATION_PLUGIN_URL . 'assets/js/admin.js',
            array('jquery'),
            SYSAFARI_INTEGRATION_VERSION,
            true
        );
        
        wp_localize_script('sysafari-admin', 'sysafariAdmin', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce'   => wp_create_nonce('sysafari_admin_nonce'),
        ));
    }
    
    /**
     * 渲染仪表板页面
     */
    public function render_dashboard_page() {
        include SYSAFARI_INTEGRATION_PLUGIN_DIR . 'admin/views/dashboard.php';
    }
    
    /**
     * 渲染报价请求页面
     */
    public function render_quotes_page() {
        include SYSAFARI_INTEGRATION_PLUGIN_DIR . 'admin/views/quotes.php';
    }
    
    /**
     * 渲染联系消息页面
     */
    public function render_contacts_page() {
        include SYSAFARI_INTEGRATION_PLUGIN_DIR . 'admin/views/contacts.php';
    }
    
    /**
     * 渲染设置页面
     */
    public function render_settings_page() {
        include SYSAFARI_INTEGRATION_PLUGIN_DIR . 'admin/views/settings.php';
    }
    
    /**
     * AJAX: 货物追踪
     */
    public function ajax_tracking() {
        check_ajax_referer('sysafari_nonce', 'nonce');
        
        $tracking_number = isset($_POST['tracking_number']) ? sanitize_text_field($_POST['tracking_number']) : '';
        
        if (empty($tracking_number)) {
            wp_send_json_error(array('message' => __('请输入追踪号码', 'sysafari-integration')));
        }
        
        // 记录追踪查询
        $this->log_tracking_query($tracking_number);
        
        // 调用API
        $tracking = new Sysafari_Tracking($this->api_client);
        $result = $tracking->query($tracking_number);
        
        if (is_wp_error($result)) {
            wp_send_json_error(array('message' => $result->get_error_message()));
        }
        
        wp_send_json_success($result);
    }
    
    /**
     * AJAX: 报价请求
     */
    public function ajax_quote_request() {
        check_ajax_referer('sysafari_nonce', 'nonce');
        
        // 收集表单数据
        $form_data = array(
            'name'         => isset($_POST['name']) ? sanitize_text_field($_POST['name']) : '',
            'email'        => isset($_POST['email']) ? sanitize_email($_POST['email']) : '',
            'phone'        => isset($_POST['phone']) ? sanitize_text_field($_POST['phone']) : '',
            'company'      => isset($_POST['company']) ? sanitize_text_field($_POST['company']) : '',
            'origin'       => isset($_POST['origin']) ? sanitize_text_field($_POST['origin']) : '',
            'destination'  => isset($_POST['destination']) ? sanitize_text_field($_POST['destination']) : '',
            'service_type' => isset($_POST['service_type']) ? sanitize_text_field($_POST['service_type']) : '',
            'cargo_type'   => isset($_POST['cargo_type']) ? sanitize_text_field($_POST['cargo_type']) : '',
            'weight'       => isset($_POST['weight']) ? floatval($_POST['weight']) : 0,
            'dimensions'   => isset($_POST['dimensions']) ? sanitize_text_field($_POST['dimensions']) : '',
            'quantity'     => isset($_POST['quantity']) ? intval($_POST['quantity']) : 1,
            'ship_date'    => isset($_POST['ship_date']) ? sanitize_text_field($_POST['ship_date']) : '',
            'message'      => isset($_POST['message']) ? sanitize_textarea_field($_POST['message']) : '',
        );
        
        // 验证必填字段
        if (empty($form_data['name']) || empty($form_data['email']) || empty($form_data['origin']) || empty($form_data['destination'])) {
            wp_send_json_error(array('message' => __('请填写所有必填字段', 'sysafari-integration')));
        }
        
        // 保存到数据库
        $quote = new Sysafari_Quote($this->api_client);
        $result = $quote->create($form_data);
        
        if (is_wp_error($result)) {
            wp_send_json_error(array('message' => $result->get_error_message()));
        }
        
        // 同步到AI系统
        if (get_option('sysafari_sync_customers', 0)) {
            $quote->sync_to_api($result);
        }
        
        // 发送通知邮件
        $this->send_quote_notification($form_data);
        
        wp_send_json_success(array('message' => __('报价请求已提交，我们将尽快与您联系', 'sysafari-integration')));
    }
    
    /**
     * AJAX: 联系表单
     */
    public function ajax_contact() {
        check_ajax_referer('sysafari_nonce', 'nonce');
        
        $form_data = array(
            'name'    => isset($_POST['name']) ? sanitize_text_field($_POST['name']) : '',
            'email'   => isset($_POST['email']) ? sanitize_email($_POST['email']) : '',
            'phone'   => isset($_POST['phone']) ? sanitize_text_field($_POST['phone']) : '',
            'subject' => isset($_POST['subject']) ? sanitize_text_field($_POST['subject']) : '',
            'message' => isset($_POST['message']) ? sanitize_textarea_field($_POST['message']) : '',
        );
        
        // 验证
        if (empty($form_data['name']) || empty($form_data['email']) || empty($form_data['message'])) {
            wp_send_json_error(array('message' => __('请填写所有必填字段', 'sysafari-integration')));
        }
        
        // 保存到数据库
        global $wpdb;
        $table = $wpdb->prefix . 'sysafari_contacts';
        
        $inserted = $wpdb->insert($table, $form_data);
        
        if (!$inserted) {
            wp_send_json_error(array('message' => __('保存失败，请重试', 'sysafari-integration')));
        }
        
        // 发送通知邮件
        $this->send_contact_notification($form_data);
        
        wp_send_json_success(array('message' => __('留言已发送成功', 'sysafari-integration')));
    }
    
    /**
     * 注册REST API路由
     */
    public function register_rest_routes() {
        register_rest_route('sysafari/v1', '/tracking/(?P<number>[a-zA-Z0-9-]+)', array(
            'methods'             => 'GET',
            'callback'            => array($this, 'rest_tracking'),
            'permission_callback' => '__return_true',
        ));
        
        register_rest_route('sysafari/v1', '/quote', array(
            'methods'             => 'POST',
            'callback'            => array($this, 'rest_quote'),
            'permission_callback' => '__return_true',
        ));
        
        register_rest_route('sysafari/v1', '/webhook', array(
            'methods'             => 'POST',
            'callback'            => array($this, 'rest_webhook'),
            'permission_callback' => array($this, 'verify_webhook'),
        ));
    }
    
    /**
     * REST: 追踪查询
     */
    public function rest_tracking($request) {
        $tracking_number = $request->get_param('number');
        
        $tracking = new Sysafari_Tracking($this->api_client);
        $result = $tracking->query($tracking_number);
        
        if (is_wp_error($result)) {
            return new WP_REST_Response(array('error' => $result->get_error_message()), 400);
        }
        
        return new WP_REST_Response($result, 200);
    }
    
    /**
     * REST: 报价请求
     */
    public function rest_quote($request) {
        $params = $request->get_json_params();
        
        $quote = new Sysafari_Quote($this->api_client);
        $result = $quote->create($params);
        
        if (is_wp_error($result)) {
            return new WP_REST_Response(array('error' => $result->get_error_message()), 400);
        }
        
        return new WP_REST_Response(array('success' => true, 'id' => $result), 201);
    }
    
    /**
     * REST: Webhook接收
     */
    public function rest_webhook($request) {
        $data = $request->get_json_params();
        $event_type = isset($data['event']) ? $data['event'] : '';
        
        switch ($event_type) {
            case 'lead.created':
            case 'lead.updated':
                // 处理线索更新
                break;
            case 'customer.synced':
                // 处理客户同步
                break;
        }
        
        return new WP_REST_Response(array('received' => true), 200);
    }
    
    /**
     * 验证Webhook
     */
    public function verify_webhook($request) {
        $api_key = get_option('sysafari_api_key', '');
        $signature = $request->get_header('X-Sysafari-Signature');
        
        if (empty($api_key) || empty($signature)) {
            return false;
        }
        
        $body = $request->get_body();
        $expected = hash_hmac('sha256', $body, $api_key);
        
        return hash_equals($expected, $signature);
    }
    
    /**
     * 记录追踪查询
     */
    private function log_tracking_query($tracking_number) {
        global $wpdb;
        $table = $wpdb->prefix . 'sysafari_tracking_logs';
        
        $wpdb->insert($table, array(
            'tracking_number' => $tracking_number,
            'ip_address'      => $this->get_client_ip(),
            'user_agent'      => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
        ));
    }
    
    /**
     * 获取客户端IP
     */
    private function get_client_ip() {
        $ip_keys = array(
            'HTTP_CF_CONNECTING_IP',
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'REMOTE_ADDR'
        );
        
        foreach ($ip_keys as $key) {
            if (!empty($_SERVER[$key])) {
                $ip = $_SERVER[$key];
                if (strpos($ip, ',') !== false) {
                    $ip = trim(explode(',', $ip)[0]);
                }
                if (filter_var($ip, FILTER_VALIDATE_IP)) {
                    return $ip;
                }
            }
        }
        
        return '';
    }
    
    /**
     * 发送报价通知邮件
     */
    private function send_quote_notification($form_data) {
        $admin_email = get_option('admin_email');
        $subject = sprintf(__('[新报价请求] %s - %s', 'sysafari-integration'), $form_data['name'], $form_data['origin'] . ' → ' . $form_data['destination']);
        
        $message = sprintf(
            "收到新的报价请求:\n\n" .
            "姓名: %s\n" .
            "邮箱: %s\n" .
            "电话: %s\n" .
            "公司: %s\n" .
            "起运地: %s\n" .
            "目的地: %s\n" .
            "服务类型: %s\n" .
            "货物类型: %s\n" .
            "重量: %s KG\n" .
            "数量: %s\n" .
            "留言: %s\n\n" .
            "请登录后台查看详情。",
            $form_data['name'],
            $form_data['email'],
            $form_data['phone'],
            $form_data['company'],
            $form_data['origin'],
            $form_data['destination'],
            $form_data['service_type'],
            $form_data['cargo_type'],
            $form_data['weight'],
            $form_data['quantity'],
            $form_data['message']
        );
        
        wp_mail($admin_email, $subject, $message);
    }
    
    /**
     * 发送联系通知邮件
     */
    private function send_contact_notification($form_data) {
        $admin_email = get_option('admin_email');
        $subject = sprintf(__('[新联系消息] %s - %s', 'sysafari-integration'), $form_data['name'], $form_data['subject']);
        
        $message = sprintf(
            "收到新的联系消息:\n\n" .
            "姓名: %s\n" .
            "邮箱: %s\n" .
            "电话: %s\n" .
            "主题: %s\n\n" .
            "留言内容:\n%s",
            $form_data['name'],
            $form_data['email'],
            $form_data['phone'],
            $form_data['subject'],
            $form_data['message']
        );
        
        wp_mail($admin_email, $subject, $message);
    }
    
    /**
     * 获取API客户端
     */
    public function get_api_client() {
        return $this->api_client;
    }
}

// 初始化插件
function sysafari_integration() {
    return Sysafari_Logistics_Integration::get_instance();
}

// 启动插件
sysafari_integration();
