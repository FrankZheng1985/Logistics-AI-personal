<?php
/**
 * 仪表板页面视图
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

// 获取统计数据
global $wpdb;

$quote_table = $wpdb->prefix . 'sysafari_quote_requests';
$contact_table = $wpdb->prefix . 'sysafari_contacts';
$tracking_table = $wpdb->prefix . 'sysafari_tracking_logs';

$stats = array(
    'quotes_total'   => $wpdb->get_var("SELECT COUNT(*) FROM {$quote_table}"),
    'quotes_pending' => $wpdb->get_var("SELECT COUNT(*) FROM {$quote_table} WHERE status = 'pending'"),
    'quotes_today'   => $wpdb->get_var("SELECT COUNT(*) FROM {$quote_table} WHERE DATE(created_at) = CURDATE()"),
    'contacts_unread' => $wpdb->get_var("SELECT COUNT(*) FROM {$contact_table} WHERE status = 'unread'"),
    'tracking_today' => $wpdb->get_var("SELECT COUNT(*) FROM {$tracking_table} WHERE DATE(created_at) = CURDATE()"),
);

// 最近报价请求
$recent_quotes = $wpdb->get_results(
    "SELECT * FROM {$quote_table} ORDER BY created_at DESC LIMIT 5",
    ARRAY_A
);

// 最近追踪查询
$recent_tracking = $wpdb->get_results(
    "SELECT tracking_number, COUNT(*) as count, MAX(created_at) as last_query 
     FROM {$tracking_table} 
     GROUP BY tracking_number 
     ORDER BY last_query DESC 
     LIMIT 10",
    ARRAY_A
);
?>

<div class="wrap sysafari-admin">
    <h1>
        <span class="dashicons dashicons-admin-site-alt3" style="color: #FFCC00;"></span>
        <?php esc_html_e('物流系统集成 - 仪表板', 'sysafari-integration'); ?>
    </h1>
    
    <!-- 统计卡片 -->
    <div class="sysafari-stats-grid">
        <div class="sysafari-stat-card">
            <div class="stat-icon quotes">
                <span class="dashicons dashicons-format-aside"></span>
            </div>
            <div class="stat-content">
                <div class="stat-number"><?php echo intval($stats['quotes_total']); ?></div>
                <div class="stat-label"><?php esc_html_e('报价请求总数', 'sysafari-integration'); ?></div>
            </div>
        </div>
        
        <div class="sysafari-stat-card">
            <div class="stat-icon pending">
                <span class="dashicons dashicons-clock"></span>
            </div>
            <div class="stat-content">
                <div class="stat-number"><?php echo intval($stats['quotes_pending']); ?></div>
                <div class="stat-label"><?php esc_html_e('待处理报价', 'sysafari-integration'); ?></div>
            </div>
        </div>
        
        <div class="sysafari-stat-card">
            <div class="stat-icon today">
                <span class="dashicons dashicons-calendar-alt"></span>
            </div>
            <div class="stat-content">
                <div class="stat-number"><?php echo intval($stats['quotes_today']); ?></div>
                <div class="stat-label"><?php esc_html_e('今日新报价', 'sysafari-integration'); ?></div>
            </div>
        </div>
        
        <div class="sysafari-stat-card">
            <div class="stat-icon tracking">
                <span class="dashicons dashicons-location"></span>
            </div>
            <div class="stat-content">
                <div class="stat-number"><?php echo intval($stats['tracking_today']); ?></div>
                <div class="stat-label"><?php esc_html_e('今日追踪查询', 'sysafari-integration'); ?></div>
            </div>
        </div>
    </div>
    
    <div class="sysafari-dashboard-grid">
        <!-- 最近报价请求 -->
        <div class="sysafari-panel">
            <h2>
                <span class="dashicons dashicons-format-aside"></span>
                <?php esc_html_e('最近报价请求', 'sysafari-integration'); ?>
            </h2>
            
            <?php if ($recent_quotes) : ?>
                <table class="wp-list-table widefat striped">
                    <thead>
                        <tr>
                            <th><?php esc_html_e('姓名', 'sysafari-integration'); ?></th>
                            <th><?php esc_html_e('路线', 'sysafari-integration'); ?></th>
                            <th><?php esc_html_e('状态', 'sysafari-integration'); ?></th>
                            <th><?php esc_html_e('时间', 'sysafari-integration'); ?></th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($recent_quotes as $quote) : ?>
                            <tr>
                                <td>
                                    <strong><?php echo esc_html($quote['name']); ?></strong>
                                    <br><small><?php echo esc_html($quote['email']); ?></small>
                                </td>
                                <td><?php echo esc_html($quote['origin'] . ' → ' . $quote['destination']); ?></td>
                                <td>
                                    <span class="status-badge status-<?php echo esc_attr($quote['status']); ?>">
                                        <?php echo esc_html($quote['status']); ?>
                                    </span>
                                </td>
                                <td><?php echo esc_html(human_time_diff(strtotime($quote['created_at']), current_time('timestamp')) . '前'); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                
                <p style="text-align: right; margin-top: 10px;">
                    <a href="<?php echo admin_url('admin.php?page=sysafari-quotes'); ?>" class="button">
                        <?php esc_html_e('查看全部', 'sysafari-integration'); ?>
                    </a>
                </p>
            <?php else : ?>
                <p class="no-data"><?php esc_html_e('暂无报价请求', 'sysafari-integration'); ?></p>
            <?php endif; ?>
        </div>
        
        <!-- 热门追踪查询 -->
        <div class="sysafari-panel">
            <h2>
                <span class="dashicons dashicons-location"></span>
                <?php esc_html_e('热门追踪查询', 'sysafari-integration'); ?>
            </h2>
            
            <?php if ($recent_tracking) : ?>
                <table class="wp-list-table widefat striped">
                    <thead>
                        <tr>
                            <th><?php esc_html_e('追踪号', 'sysafari-integration'); ?></th>
                            <th><?php esc_html_e('查询次数', 'sysafari-integration'); ?></th>
                            <th><?php esc_html_e('最后查询', 'sysafari-integration'); ?></th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($recent_tracking as $track) : ?>
                            <tr>
                                <td><code><?php echo esc_html($track['tracking_number']); ?></code></td>
                                <td><?php echo esc_html($track['count']); ?></td>
                                <td><?php echo esc_html(human_time_diff(strtotime($track['last_query']), current_time('timestamp')) . '前'); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php else : ?>
                <p class="no-data"><?php esc_html_e('暂无追踪查询记录', 'sysafari-integration'); ?></p>
            <?php endif; ?>
        </div>
    </div>
    
    <!-- 快速操作 -->
    <div class="sysafari-panel">
        <h2>
            <span class="dashicons dashicons-admin-tools"></span>
            <?php esc_html_e('快速操作', 'sysafari-integration'); ?>
        </h2>
        
        <div class="sysafari-quick-actions">
            <a href="<?php echo admin_url('admin.php?page=sysafari-settings'); ?>" class="button button-primary">
                <span class="dashicons dashicons-admin-generic"></span>
                <?php esc_html_e('配置设置', 'sysafari-integration'); ?>
            </a>
            
            <a href="<?php echo admin_url('admin.php?page=sysafari-quotes'); ?>" class="button">
                <span class="dashicons dashicons-list-view"></span>
                <?php esc_html_e('管理报价', 'sysafari-integration'); ?>
            </a>
            
            <button type="button" class="button" id="sync-quotes-btn">
                <span class="dashicons dashicons-update"></span>
                <?php esc_html_e('同步到AI系统', 'sysafari-integration'); ?>
            </button>
            
            <a href="<?php echo home_url('/tracking'); ?>" target="_blank" class="button">
                <span class="dashicons dashicons-external"></span>
                <?php esc_html_e('查看追踪页面', 'sysafari-integration'); ?>
            </a>
        </div>
    </div>
</div>

<style>
.sysafari-admin h1 {
    display: flex;
    align-items: center;
    gap: 10px;
}

.sysafari-stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin: 20px 0;
}

.sysafari-stat-card {
    background: #fff;
    border: 1px solid #ccd0d4;
    border-radius: 8px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 15px;
}

.stat-icon {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.stat-icon .dashicons {
    font-size: 24px;
    width: 24px;
    height: 24px;
    color: #fff;
}

.stat-icon.quotes { background: #0073aa; }
.stat-icon.pending { background: #ffba00; }
.stat-icon.today { background: #46b450; }
.stat-icon.tracking { background: #dc3232; }

.stat-number {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.2;
}

.stat-label {
    color: #666;
    font-size: 13px;
}

.sysafari-dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
}

.sysafari-panel {
    background: #fff;
    border: 1px solid #ccd0d4;
    border-radius: 8px;
    padding: 20px;
}

.sysafari-panel h2 {
    margin-top: 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
}

.sysafari-panel h2 .dashicons {
    color: #FFCC00;
}

.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
    text-transform: uppercase;
}

.status-pending { background: #fff3cd; color: #856404; }
.status-processing { background: #cce5ff; color: #004085; }
.status-completed { background: #d4edda; color: #155724; }

.no-data {
    text-align: center;
    color: #666;
    padding: 30px;
}

.sysafari-quick-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.sysafari-quick-actions .button {
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

@media (max-width: 1200px) {
    .sysafari-stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .sysafari-dashboard-grid {
        grid-template-columns: 1fr;
    }
}
</style>
