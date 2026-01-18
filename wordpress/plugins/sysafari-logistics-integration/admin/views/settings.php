<?php
/**
 * 设置页面视图
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}
?>

<div class="wrap sysafari-admin">
    <h1><?php esc_html_e('物流系统集成设置', 'sysafari-integration'); ?></h1>
    
    <form method="post" action="options.php">
        <?php settings_fields('sysafari_settings'); ?>
        
        <div class="sysafari-settings-section">
            <h2><span class="dashicons dashicons-admin-network"></span> <?php esc_html_e('API 连接设置', 'sysafari-integration'); ?></h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row">
                        <label for="sysafari_api_base_url"><?php esc_html_e('API 基础 URL', 'sysafari-integration'); ?></label>
                    </th>
                    <td>
                        <input type="url" 
                               id="sysafari_api_base_url" 
                               name="sysafari_api_base_url" 
                               value="<?php echo esc_attr(get_option('sysafari_api_base_url', 'http://localhost:8000/api/v1')); ?>" 
                               class="regular-text"
                               placeholder="http://localhost:8000/api/v1">
                        <p class="description"><?php esc_html_e('物流AI系统的API地址，例如: http://localhost:8000/api/v1', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row">
                        <label for="sysafari_api_key"><?php esc_html_e('API 密钥', 'sysafari-integration'); ?></label>
                    </th>
                    <td>
                        <input type="password" 
                               id="sysafari_api_key" 
                               name="sysafari_api_key" 
                               value="<?php echo esc_attr(get_option('sysafari_api_key', '')); ?>" 
                               class="regular-text">
                        <button type="button" class="button" id="toggle-api-key"><?php esc_html_e('显示/隐藏', 'sysafari-integration'); ?></button>
                        <p class="description"><?php esc_html_e('用于API认证的密钥', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><?php esc_html_e('连接测试', 'sysafari-integration'); ?></th>
                    <td>
                        <button type="button" class="button button-secondary" id="test-api-connection">
                            <span class="dashicons dashicons-update"></span>
                            <?php esc_html_e('测试连接', 'sysafari-integration'); ?>
                        </button>
                        <span id="api-test-result"></span>
                    </td>
                </tr>
            </table>
        </div>
        
        <div class="sysafari-settings-section">
            <h2><span class="dashicons dashicons-admin-settings"></span> <?php esc_html_e('功能开关', 'sysafari-integration'); ?></h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row"><?php esc_html_e('货物追踪', 'sysafari-integration'); ?></th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="sysafari_enable_tracking" 
                                   value="1" 
                                   <?php checked(get_option('sysafari_enable_tracking', 1)); ?>>
                            <?php esc_html_e('启用货物追踪功能', 'sysafari-integration'); ?>
                        </label>
                        <p class="description"><?php esc_html_e('允许访客在网站上查询货物追踪信息', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><?php esc_html_e('在线报价', 'sysafari-integration'); ?></th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="sysafari_enable_quote" 
                                   value="1" 
                                   <?php checked(get_option('sysafari_enable_quote', 1)); ?>>
                            <?php esc_html_e('启用在线报价功能', 'sysafari-integration'); ?>
                        </label>
                        <p class="description"><?php esc_html_e('允许访客提交报价请求', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><?php esc_html_e('在线客服', 'sysafari-integration'); ?></th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="sysafari_enable_webchat" 
                                   value="1" 
                                   <?php checked(get_option('sysafari_enable_webchat', 1)); ?>>
                            <?php esc_html_e('启用WebChat在线客服', 'sysafari-integration'); ?>
                        </label>
                        <p class="description"><?php esc_html_e('在网站显示AI在线客服聊天窗口', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><?php esc_html_e('客户同步', 'sysafari-integration'); ?></th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="sysafari_sync_customers" 
                                   value="1" 
                                   <?php checked(get_option('sysafari_sync_customers', 0)); ?>>
                            <?php esc_html_e('启用客户数据同步', 'sysafari-integration'); ?>
                        </label>
                        <p class="description"><?php esc_html_e('将网站用户数据同步到AI系统', 'sysafari-integration'); ?></p>
                    </td>
                </tr>
            </table>
        </div>
        
        <?php submit_button(__('保存设置', 'sysafari-integration')); ?>
    </form>
</div>

<style>
.sysafari-admin {
    max-width: 800px;
}

.sysafari-settings-section {
    background: #fff;
    border: 1px solid #ccd0d4;
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 20px;
}

.sysafari-settings-section h2 {
    margin-top: 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
    display: flex;
    align-items: center;
    gap: 8px;
}

.sysafari-settings-section h2 .dashicons {
    color: #FFCC00;
}

#api-test-result {
    margin-left: 10px;
    font-weight: 500;
}

#api-test-result.success {
    color: #46b450;
}

#api-test-result.error {
    color: #dc3232;
}
</style>

<script>
jQuery(document).ready(function($) {
    // 切换API密钥显示
    $('#toggle-api-key').on('click', function() {
        var $input = $('#sysafari_api_key');
        if ($input.attr('type') === 'password') {
            $input.attr('type', 'text');
        } else {
            $input.attr('type', 'password');
        }
    });
    
    // 测试API连接
    $('#test-api-connection').on('click', function() {
        var $btn = $(this);
        var $result = $('#api-test-result');
        
        $btn.prop('disabled', true);
        $result.removeClass('success error').text('测试中...');
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_test_api',
                nonce: sysafariAdmin.nonce
            },
            success: function(response) {
                if (response.success) {
                    $result.addClass('success').text('✓ ' + response.data.message);
                } else {
                    $result.addClass('error').text('✗ ' + response.data.message);
                }
            },
            error: function() {
                $result.addClass('error').text('✗ 请求失败');
            },
            complete: function() {
                $btn.prop('disabled', false);
            }
        });
    });
});
</script>
