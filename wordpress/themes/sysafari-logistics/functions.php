<?php
/**
 * Sysafari Logistics 主题函数
 * 
 * @package Sysafari_Logistics
 * @version 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

// 主题版本
define('SYSAFARI_THEME_VERSION', '1.0.0');
define('SYSAFARI_THEME_DIR', get_template_directory());
define('SYSAFARI_THEME_URI', get_template_directory_uri());

/**
 * 主题初始化设置
 */
function sysafari_theme_setup() {
    // 支持标题标签
    add_theme_support('title-tag');
    
    // 支持缩略图
    add_theme_support('post-thumbnails');
    
    // 支持HTML5
    add_theme_support('html5', array(
        'search-form',
        'comment-form',
        'comment-list',
        'gallery',
        'caption',
        'style',
        'script',
    ));
    
    // 支持自定义Logo
    add_theme_support('custom-logo', array(
        'height'      => 100,
        'width'       => 300,
        'flex-height' => true,
        'flex-width'  => true,
    ));
    
    // 支持自定义背景
    add_theme_support('custom-background', array(
        'default-color' => 'ffffff',
    ));
    
    // 支持响应式嵌入
    add_theme_support('responsive-embeds');
    
    // 支持编辑器样式
    add_theme_support('editor-styles');
    add_editor_style('assets/css/editor-style.css');
    
    // 注册导航菜单
    register_nav_menus(array(
        'primary'   => __('主导航', 'sysafari-logistics'),
        'footer'    => __('页脚导航', 'sysafari-logistics'),
        'service'   => __('服务导航', 'sysafari-logistics'),
    ));
    
    // 加载文本域
    load_theme_textdomain('sysafari-logistics', SYSAFARI_THEME_DIR . '/languages');
    
    // 设置内容宽度
    global $content_width;
    if (!isset($content_width)) {
        $content_width = 1200;
    }
}
add_action('after_setup_theme', 'sysafari_theme_setup');

/**
 * 加载样式和脚本
 */
function sysafari_enqueue_scripts() {
    // 主样式表
    wp_enqueue_style(
        'sysafari-style',
        get_stylesheet_uri(),
        array(),
        SYSAFARI_THEME_VERSION
    );
    
    // Google Fonts - Noto Sans SC
    wp_enqueue_style(
        'google-fonts',
        'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap',
        array(),
        null
    );
    
    // Font Awesome 图标
    wp_enqueue_style(
        'font-awesome',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        array(),
        '6.4.0'
    );
    
    // 主JavaScript
    wp_enqueue_script(
        'sysafari-main',
        SYSAFARI_THEME_URI . '/assets/js/main.js',
        array('jquery'),
        SYSAFARI_THEME_VERSION,
        true
    );
    
    // 传递数据到JavaScript
    wp_localize_script('sysafari-main', 'sysafariData', array(
        'ajaxUrl'   => admin_url('admin-ajax.php'),
        'nonce'     => wp_create_nonce('sysafari_nonce'),
        'siteUrl'   => get_site_url(),
        'themeUrl'  => SYSAFARI_THEME_URI,
        'i18n'      => array(
            'loading'       => __('加载中...', 'sysafari-logistics'),
            'error'         => __('发生错误，请重试', 'sysafari-logistics'),
            'success'       => __('操作成功', 'sysafari-logistics'),
            'trackingEmpty' => __('请输入追踪号码', 'sysafari-logistics'),
        ),
    ));
}
add_action('wp_enqueue_scripts', 'sysafari_enqueue_scripts');

/**
 * 注册侧边栏/小工具区域
 */
function sysafari_widgets_init() {
    // 页脚小工具区域1
    register_sidebar(array(
        'name'          => __('页脚区域 1', 'sysafari-logistics'),
        'id'            => 'footer-1',
        'description'   => __('页脚第一列小工具区域', 'sysafari-logistics'),
        'before_widget' => '<div id="%1$s" class="footer-widget %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4 class="footer-heading">',
        'after_title'   => '</h4>',
    ));
    
    // 页脚小工具区域2
    register_sidebar(array(
        'name'          => __('页脚区域 2', 'sysafari-logistics'),
        'id'            => 'footer-2',
        'description'   => __('页脚第二列小工具区域', 'sysafari-logistics'),
        'before_widget' => '<div id="%1$s" class="footer-widget %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4 class="footer-heading">',
        'after_title'   => '</h4>',
    ));
    
    // 侧边栏
    register_sidebar(array(
        'name'          => __('博客侧边栏', 'sysafari-logistics'),
        'id'            => 'sidebar-blog',
        'description'   => __('博客页面侧边栏', 'sysafari-logistics'),
        'before_widget' => '<div id="%1$s" class="widget %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4 class="widget-title">',
        'after_title'   => '</h4>',
    ));
}
add_action('widgets_init', 'sysafari_widgets_init');

/**
 * 自定义主题设置页面
 */
function sysafari_customizer_settings($wp_customize) {
    // 公司信息设置
    $wp_customize->add_section('sysafari_company_info', array(
        'title'    => __('公司信息', 'sysafari-logistics'),
        'priority' => 30,
    ));
    
    // 公司名称
    $wp_customize->add_setting('company_name', array(
        'default'           => 'Sysafari Logistics',
        'sanitize_callback' => 'sanitize_text_field',
    ));
    $wp_customize->add_control('company_name', array(
        'label'   => __('公司名称', 'sysafari-logistics'),
        'section' => 'sysafari_company_info',
        'type'    => 'text',
    ));
    
    // 公司电话
    $wp_customize->add_setting('company_phone', array(
        'default'           => '+86 400-XXX-XXXX',
        'sanitize_callback' => 'sanitize_text_field',
    ));
    $wp_customize->add_control('company_phone', array(
        'label'   => __('联系电话', 'sysafari-logistics'),
        'section' => 'sysafari_company_info',
        'type'    => 'text',
    ));
    
    // 公司邮箱
    $wp_customize->add_setting('company_email', array(
        'default'           => 'info@sysafari.com',
        'sanitize_callback' => 'sanitize_email',
    ));
    $wp_customize->add_control('company_email', array(
        'label'   => __('联系邮箱', 'sysafari-logistics'),
        'section' => 'sysafari_company_info',
        'type'    => 'email',
    ));
    
    // 公司地址
    $wp_customize->add_setting('company_address', array(
        'default'           => '',
        'sanitize_callback' => 'sanitize_textarea_field',
    ));
    $wp_customize->add_control('company_address', array(
        'label'   => __('公司地址', 'sysafari-logistics'),
        'section' => 'sysafari_company_info',
        'type'    => 'textarea',
    ));
    
    // API设置
    $wp_customize->add_section('sysafari_api_settings', array(
        'title'       => __('API 设置', 'sysafari-logistics'),
        'priority'    => 120,
        'description' => __('配置与物流AI系统的API对接', 'sysafari-logistics'),
    ));
    
    // API基础URL
    $wp_customize->add_setting('api_base_url', array(
        'default'           => 'http://localhost:8000/api/v1',
        'sanitize_callback' => 'esc_url_raw',
    ));
    $wp_customize->add_control('api_base_url', array(
        'label'       => __('API 基础 URL', 'sysafari-logistics'),
        'section'     => 'sysafari_api_settings',
        'type'        => 'url',
        'description' => __('物流AI系统的API地址', 'sysafari-logistics'),
    ));
    
    // API密钥
    $wp_customize->add_setting('api_key', array(
        'default'           => '',
        'sanitize_callback' => 'sanitize_text_field',
    ));
    $wp_customize->add_control('api_key', array(
        'label'   => __('API 密钥', 'sysafari-logistics'),
        'section' => 'sysafari_api_settings',
        'type'    => 'password',
    ));
    
    // 社交媒体设置
    $wp_customize->add_section('sysafari_social', array(
        'title'    => __('社交媒体', 'sysafari-logistics'),
        'priority' => 130,
    ));
    
    $social_platforms = array(
        'wechat'    => __('微信公众号', 'sysafari-logistics'),
        'weibo'     => __('微博', 'sysafari-logistics'),
        'linkedin'  => __('LinkedIn', 'sysafari-logistics'),
        'facebook'  => __('Facebook', 'sysafari-logistics'),
    );
    
    foreach ($social_platforms as $platform => $label) {
        $wp_customize->add_setting("social_{$platform}", array(
            'default'           => '',
            'sanitize_callback' => 'esc_url_raw',
        ));
        $wp_customize->add_control("social_{$platform}", array(
            'label'   => $label,
            'section' => 'sysafari_social',
            'type'    => 'url',
        ));
    }
}
add_action('customize_register', 'sysafari_customizer_settings');

/**
 * 获取主题设置值
 */
function sysafari_get_option($key, $default = '') {
    return get_theme_mod($key, $default);
}

/**
 * 自定义摘要长度
 */
function sysafari_excerpt_length($length) {
    return 30;
}
add_filter('excerpt_length', 'sysafari_excerpt_length');

/**
 * 自定义摘要结尾
 */
function sysafari_excerpt_more($more) {
    return '...';
}
add_filter('excerpt_more', 'sysafari_excerpt_more');

/**
 * 添加自定义图片尺寸
 */
function sysafari_image_sizes() {
    add_image_size('news-thumbnail', 400, 250, true);
    add_image_size('hero-image', 1920, 600, true);
    add_image_size('service-icon', 128, 128, true);
}
add_action('after_setup_theme', 'sysafari_image_sizes');

/**
 * 面包屑导航
 */
function sysafari_breadcrumbs() {
    if (is_front_page()) {
        return;
    }
    
    echo '<nav class="breadcrumbs" aria-label="' . esc_attr__('面包屑导航', 'sysafari-logistics') . '">';
    echo '<div class="container">';
    echo '<a href="' . esc_url(home_url('/')) . '">' . esc_html__('首页', 'sysafari-logistics') . '</a>';
    
    if (is_page()) {
        echo ' <span class="separator">/</span> ';
        echo '<span class="current">' . get_the_title() . '</span>';
    } elseif (is_single()) {
        echo ' <span class="separator">/</span> ';
        $categories = get_the_category();
        if ($categories) {
            echo '<a href="' . esc_url(get_category_link($categories[0]->term_id)) . '">' . esc_html($categories[0]->name) . '</a>';
            echo ' <span class="separator">/</span> ';
        }
        echo '<span class="current">' . get_the_title() . '</span>';
    } elseif (is_category()) {
        echo ' <span class="separator">/</span> ';
        echo '<span class="current">' . single_cat_title('', false) . '</span>';
    } elseif (is_search()) {
        echo ' <span class="separator">/</span> ';
        echo '<span class="current">' . sprintf(__('搜索结果: %s', 'sysafari-logistics'), get_search_query()) . '</span>';
    }
    
    echo '</div>';
    echo '</nav>';
}

/**
 * 加载WebChat组件
 */
function sysafari_load_webchat() {
    $api_url = sysafari_get_option('api_base_url', 'http://localhost:8000/api/v1');
    
    // 移除 /api/v1 后缀获取基础域名
    $chat_base_url = preg_replace('/\/api\/v1$/', '', $api_url);
    
    ?>
    <div id="sysafari-webchat" class="webchat-container"></div>
    <script>
    (function() {
        // 动态加载WebChat
        var script = document.createElement('script');
        script.src = '<?php echo esc_url($chat_base_url); ?>/chat-widget.js';
        script.async = true;
        document.body.appendChild(script);
    })();
    </script>
    <?php
}
add_action('wp_footer', 'sysafari_load_webchat');

/**
 * AJAX: 货物追踪
 */
function sysafari_ajax_tracking() {
    check_ajax_referer('sysafari_nonce', 'nonce');
    
    $tracking_number = isset($_POST['tracking_number']) ? sanitize_text_field($_POST['tracking_number']) : '';
    
    if (empty($tracking_number)) {
        wp_send_json_error(array('message' => __('请输入追踪号码', 'sysafari-logistics')));
    }
    
    // 调用API获取追踪信息
    $api_url = sysafari_get_option('api_base_url', 'http://localhost:8000/api/v1');
    $api_key = sysafari_get_option('api_key', '');
    
    $response = wp_remote_post($api_url . '/website/tracking', array(
        'headers' => array(
            'Content-Type'  => 'application/json',
            'Authorization' => 'Bearer ' . $api_key,
        ),
        'body'    => json_encode(array(
            'tracking_number' => $tracking_number,
        )),
        'timeout' => 30,
    ));
    
    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => $response->get_error_message()));
    }
    
    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);
    
    if (isset($data['error'])) {
        wp_send_json_error(array('message' => $data['error']));
    }
    
    wp_send_json_success($data);
}
add_action('wp_ajax_sysafari_tracking', 'sysafari_ajax_tracking');
add_action('wp_ajax_nopriv_sysafari_tracking', 'sysafari_ajax_tracking');

/**
 * AJAX: 提交报价请求
 */
function sysafari_ajax_quote_request() {
    check_ajax_referer('sysafari_nonce', 'nonce');
    
    // 收集表单数据
    $form_data = array(
        'name'           => isset($_POST['name']) ? sanitize_text_field($_POST['name']) : '',
        'email'          => isset($_POST['email']) ? sanitize_email($_POST['email']) : '',
        'phone'          => isset($_POST['phone']) ? sanitize_text_field($_POST['phone']) : '',
        'company'        => isset($_POST['company']) ? sanitize_text_field($_POST['company']) : '',
        'origin'         => isset($_POST['origin']) ? sanitize_text_field($_POST['origin']) : '',
        'destination'    => isset($_POST['destination']) ? sanitize_text_field($_POST['destination']) : '',
        'cargo_type'     => isset($_POST['cargo_type']) ? sanitize_text_field($_POST['cargo_type']) : '',
        'weight'         => isset($_POST['weight']) ? floatval($_POST['weight']) : 0,
        'dimensions'     => isset($_POST['dimensions']) ? sanitize_text_field($_POST['dimensions']) : '',
        'service_type'   => isset($_POST['service_type']) ? sanitize_text_field($_POST['service_type']) : '',
        'message'        => isset($_POST['message']) ? sanitize_textarea_field($_POST['message']) : '',
    );
    
    // 验证必填字段
    if (empty($form_data['name']) || empty($form_data['email'])) {
        wp_send_json_error(array('message' => __('请填写必填字段', 'sysafari-logistics')));
    }
    
    // 调用API提交报价请求
    $api_url = sysafari_get_option('api_base_url', 'http://localhost:8000/api/v1');
    $api_key = sysafari_get_option('api_key', '');
    
    $response = wp_remote_post($api_url . '/website/quote-request', array(
        'headers' => array(
            'Content-Type'  => 'application/json',
            'Authorization' => 'Bearer ' . $api_key,
        ),
        'body'    => json_encode($form_data),
        'timeout' => 30,
    ));
    
    if (is_wp_error($response)) {
        // 如果API调用失败，发送邮件通知
        $admin_email = get_option('admin_email');
        $subject = sprintf(__('新报价请求 - %s', 'sysafari-logistics'), $form_data['name']);
        $message = sprintf(
            "收到新的报价请求:\n\n姓名: %s\n邮箱: %s\n电话: %s\n公司: %s\n起运地: %s\n目的地: %s\n货物类型: %s\n重量: %s\n尺寸: %s\n服务类型: %s\n留言: %s",
            $form_data['name'],
            $form_data['email'],
            $form_data['phone'],
            $form_data['company'],
            $form_data['origin'],
            $form_data['destination'],
            $form_data['cargo_type'],
            $form_data['weight'],
            $form_data['dimensions'],
            $form_data['service_type'],
            $form_data['message']
        );
        wp_mail($admin_email, $subject, $message);
    }
    
    wp_send_json_success(array('message' => __('报价请求已提交，我们将尽快与您联系', 'sysafari-logistics')));
}
add_action('wp_ajax_sysafari_quote_request', 'sysafari_ajax_quote_request');
add_action('wp_ajax_nopriv_sysafari_quote_request', 'sysafari_ajax_quote_request');

/**
 * 短代码: 追踪表单
 */
function sysafari_tracking_form_shortcode($atts) {
    $atts = shortcode_atts(array(
        'title' => __('追踪货件', 'sysafari-logistics'),
    ), $atts);
    
    ob_start();
    ?>
    <div class="tracking-form-wrapper">
        <?php if ($atts['title']) : ?>
            <h3><?php echo esc_html($atts['title']); ?></h3>
        <?php endif; ?>
        <form class="tracking-form" id="tracking-form">
            <input type="text" name="tracking_number" placeholder="<?php esc_attr_e('输入您的追踪码', 'sysafari-logistics'); ?>" required>
            <button type="submit"><?php esc_html_e('追踪', 'sysafari-logistics'); ?></button>
        </form>
        <div id="tracking-results" class="tracking-results hidden"></div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('sysafari_tracking', 'sysafari_tracking_form_shortcode');

/**
 * 短代码: 报价表单
 */
function sysafari_quote_form_shortcode($atts) {
    $atts = shortcode_atts(array(
        'title' => __('获取报价', 'sysafari-logistics'),
    ), $atts);
    
    ob_start();
    include SYSAFARI_THEME_DIR . '/template-parts/quote-form.php';
    return ob_get_clean();
}
add_shortcode('sysafari_quote', 'sysafari_quote_form_shortcode');

/**
 * 短代码: 服务卡片
 */
function sysafari_service_cards_shortcode($atts) {
    $atts = shortcode_atts(array(
        'columns' => 3,
    ), $atts);
    
    ob_start();
    include SYSAFARI_THEME_DIR . '/template-parts/service-cards.php';
    return ob_get_clean();
}
add_shortcode('sysafari_services', 'sysafari_service_cards_shortcode');

/**
 * 注册自定义文章类型: 服务
 */
function sysafari_register_post_types() {
    // 服务
    register_post_type('service', array(
        'labels' => array(
            'name'               => __('服务', 'sysafari-logistics'),
            'singular_name'      => __('服务', 'sysafari-logistics'),
            'add_new'            => __('添加服务', 'sysafari-logistics'),
            'add_new_item'       => __('添加新服务', 'sysafari-logistics'),
            'edit_item'          => __('编辑服务', 'sysafari-logistics'),
            'new_item'           => __('新服务', 'sysafari-logistics'),
            'view_item'          => __('查看服务', 'sysafari-logistics'),
            'search_items'       => __('搜索服务', 'sysafari-logistics'),
            'not_found'          => __('未找到服务', 'sysafari-logistics'),
            'not_found_in_trash' => __('回收站中未找到服务', 'sysafari-logistics'),
        ),
        'public'       => true,
        'has_archive'  => true,
        'menu_icon'    => 'dashicons-car',
        'supports'     => array('title', 'editor', 'thumbnail', 'excerpt', 'page-attributes'),
        'rewrite'      => array('slug' => 'services'),
        'show_in_rest' => true,
    ));
    
    // 常见问题
    register_post_type('faq', array(
        'labels' => array(
            'name'               => __('常见问题', 'sysafari-logistics'),
            'singular_name'      => __('常见问题', 'sysafari-logistics'),
            'add_new'            => __('添加问题', 'sysafari-logistics'),
            'add_new_item'       => __('添加新问题', 'sysafari-logistics'),
            'edit_item'          => __('编辑问题', 'sysafari-logistics'),
        ),
        'public'       => true,
        'has_archive'  => true,
        'menu_icon'    => 'dashicons-editor-help',
        'supports'     => array('title', 'editor'),
        'rewrite'      => array('slug' => 'faq'),
        'show_in_rest' => true,
    ));
}
add_action('init', 'sysafari_register_post_types');

/**
 * 安全性增强
 */
function sysafari_security_headers() {
    // 防止点击劫持
    header('X-Frame-Options: SAMEORIGIN');
    // XSS保护
    header('X-XSS-Protection: 1; mode=block');
    // 内容类型嗅探保护
    header('X-Content-Type-Options: nosniff');
}
add_action('send_headers', 'sysafari_security_headers');

/**
 * 移除WordPress版本号（安全考虑）
 */
remove_action('wp_head', 'wp_generator');

/**
 * 调试函数（仅开发环境使用）
 */
if (defined('WP_DEBUG') && WP_DEBUG) {
    function sysafari_debug_log($message) {
        if (is_array($message) || is_object($message)) {
            error_log(print_r($message, true));
        } else {
            error_log($message);
        }
    }
}
