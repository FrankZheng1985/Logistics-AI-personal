<?php
/**
 * 报价请求列表页面
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

global $wpdb;
$table_name = $wpdb->prefix . 'sysafari_quote_requests';

// 分页参数
$per_page = 20;
$current_page = isset($_GET['paged']) ? max(1, intval($_GET['paged'])) : 1;
$offset = ($current_page - 1) * $per_page;

// 筛选参数
$status_filter = isset($_GET['status']) ? sanitize_text_field($_GET['status']) : '';
$search = isset($_GET['s']) ? sanitize_text_field($_GET['s']) : '';

// 构建查询
$where = '1=1';
$values = array();

if (!empty($status_filter)) {
    $where .= ' AND status = %s';
    $values[] = $status_filter;
}

if (!empty($search)) {
    $where .= ' AND (name LIKE %s OR email LIKE %s OR company LIKE %s)';
    $search_like = '%' . $wpdb->esc_like($search) . '%';
    $values[] = $search_like;
    $values[] = $search_like;
    $values[] = $search_like;
}

// 获取总数
$count_sql = "SELECT COUNT(*) FROM {$table_name} WHERE {$where}";
$total = $values ? $wpdb->get_var($wpdb->prepare($count_sql, $values)) : $wpdb->get_var($count_sql);
$total_pages = ceil($total / $per_page);

// 获取数据
$query_values = $values;
$query_values[] = $per_page;
$query_values[] = $offset;

$data_sql = "SELECT * FROM {$table_name} WHERE {$where} ORDER BY created_at DESC LIMIT %d OFFSET %d";
$quotes = $query_values ? $wpdb->get_results($wpdb->prepare($data_sql, $query_values), ARRAY_A) : array();

// 状态统计
$status_counts = $wpdb->get_results(
    "SELECT status, COUNT(*) as count FROM {$table_name} GROUP BY status",
    ARRAY_A
);
$status_map = array();
foreach ($status_counts as $sc) {
    $status_map[$sc['status']] = $sc['count'];
}
?>

<div class="wrap sysafari-admin">
    <h1 class="wp-heading-inline">
        <span class="dashicons dashicons-format-aside" style="color: #FFCC00;"></span>
        <?php esc_html_e('报价请求管理', 'sysafari-integration'); ?>
    </h1>
    
    <!-- 状态过滤 -->
    <ul class="subsubsub">
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-quotes'); ?>" 
               class="<?php echo empty($status_filter) ? 'current' : ''; ?>">
                <?php esc_html_e('全部', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($total); ?>)</span>
            </a> |
        </li>
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-quotes&status=pending'); ?>"
               class="<?php echo $status_filter === 'pending' ? 'current' : ''; ?>">
                <?php esc_html_e('待处理', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($status_map['pending'] ?? 0); ?>)</span>
            </a> |
        </li>
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-quotes&status=processing'); ?>"
               class="<?php echo $status_filter === 'processing' ? 'current' : ''; ?>">
                <?php esc_html_e('处理中', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($status_map['processing'] ?? 0); ?>)</span>
            </a> |
        </li>
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-quotes&status=completed'); ?>"
               class="<?php echo $status_filter === 'completed' ? 'current' : ''; ?>">
                <?php esc_html_e('已完成', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($status_map['completed'] ?? 0); ?>)</span>
            </a>
        </li>
    </ul>
    
    <!-- 搜索框 -->
    <form method="get" action="" class="search-box">
        <input type="hidden" name="page" value="sysafari-quotes">
        <?php if ($status_filter) : ?>
            <input type="hidden" name="status" value="<?php echo esc_attr($status_filter); ?>">
        <?php endif; ?>
        <input type="search" name="s" value="<?php echo esc_attr($search); ?>" placeholder="<?php esc_attr_e('搜索姓名、邮箱或公司...', 'sysafari-integration'); ?>">
        <input type="submit" class="button" value="<?php esc_attr_e('搜索', 'sysafari-integration'); ?>">
    </form>
    
    <!-- 表格 -->
    <table class="wp-list-table widefat fixed striped">
        <thead>
            <tr>
                <th style="width: 30px;"><input type="checkbox" id="select-all"></th>
                <th><?php esc_html_e('联系人', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('公司', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('运输路线', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('服务类型', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('状态', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('已同步', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('提交时间', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('操作', 'sysafari-integration'); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php if ($quotes) : ?>
                <?php foreach ($quotes as $quote) : ?>
                    <tr>
                        <td><input type="checkbox" name="quote_ids[]" value="<?php echo esc_attr($quote['id']); ?>"></td>
                        <td>
                            <strong><?php echo esc_html($quote['name']); ?></strong>
                            <br>
                            <a href="mailto:<?php echo esc_attr($quote['email']); ?>"><?php echo esc_html($quote['email']); ?></a>
                            <?php if ($quote['phone']) : ?>
                                <br><span class="description"><?php echo esc_html($quote['phone']); ?></span>
                            <?php endif; ?>
                        </td>
                        <td><?php echo esc_html($quote['company'] ?: '-'); ?></td>
                        <td>
                            <strong><?php echo esc_html($quote['origin']); ?></strong>
                            →
                            <strong><?php echo esc_html($quote['destination']); ?></strong>
                        </td>
                        <td>
                            <?php
                            $service_types = array(
                                'sea_freight' => '海运',
                                'air_freight' => '空运',
                                'land_transport' => '陆运',
                                'express' => '快递',
                                'multimodal' => '多式联运',
                            );
                            echo esc_html($service_types[$quote['service_type']] ?? $quote['service_type']);
                            ?>
                        </td>
                        <td>
                            <select class="quote-status-select" data-id="<?php echo esc_attr($quote['id']); ?>">
                                <option value="pending" <?php selected($quote['status'], 'pending'); ?>><?php esc_html_e('待处理', 'sysafari-integration'); ?></option>
                                <option value="processing" <?php selected($quote['status'], 'processing'); ?>><?php esc_html_e('处理中', 'sysafari-integration'); ?></option>
                                <option value="quoted" <?php selected($quote['status'], 'quoted'); ?>><?php esc_html_e('已报价', 'sysafari-integration'); ?></option>
                                <option value="accepted" <?php selected($quote['status'], 'accepted'); ?>><?php esc_html_e('已接受', 'sysafari-integration'); ?></option>
                                <option value="rejected" <?php selected($quote['status'], 'rejected'); ?>><?php esc_html_e('已拒绝', 'sysafari-integration'); ?></option>
                                <option value="completed" <?php selected($quote['status'], 'completed'); ?>><?php esc_html_e('已完成', 'sysafari-integration'); ?></option>
                            </select>
                        </td>
                        <td>
                            <?php if ($quote['synced_to_api']) : ?>
                                <span class="dashicons dashicons-yes-alt" style="color: #46b450;" title="<?php esc_attr_e('已同步', 'sysafari-integration'); ?>"></span>
                            <?php else : ?>
                                <span class="dashicons dashicons-minus" style="color: #ccc;" title="<?php esc_attr_e('未同步', 'sysafari-integration'); ?>"></span>
                            <?php endif; ?>
                        </td>
                        <td>
                            <?php echo esc_html(date_i18n('Y-m-d H:i', strtotime($quote['created_at']))); ?>
                        </td>
                        <td>
                            <button type="button" class="button button-small view-quote-btn" data-id="<?php echo esc_attr($quote['id']); ?>">
                                <?php esc_html_e('查看', 'sysafari-integration'); ?>
                            </button>
                            <button type="button" class="button button-small delete-quote-btn" data-id="<?php echo esc_attr($quote['id']); ?>" style="color: #dc3232;">
                                <?php esc_html_e('删除', 'sysafari-integration'); ?>
                            </button>
                        </td>
                    </tr>
                <?php endforeach; ?>
            <?php else : ?>
                <tr>
                    <td colspan="9" style="text-align: center; padding: 30px;">
                        <?php esc_html_e('暂无报价请求', 'sysafari-integration'); ?>
                    </td>
                </tr>
            <?php endif; ?>
        </tbody>
    </table>
    
    <!-- 分页 -->
    <?php if ($total_pages > 1) : ?>
        <div class="tablenav bottom">
            <div class="tablenav-pages">
                <span class="displaying-num"><?php printf(__('共 %d 项', 'sysafari-integration'), $total); ?></span>
                <span class="pagination-links">
                    <?php
                    echo paginate_links(array(
                        'base'      => add_query_arg('paged', '%#%'),
                        'format'    => '',
                        'prev_text' => '&laquo;',
                        'next_text' => '&raquo;',
                        'total'     => $total_pages,
                        'current'   => $current_page,
                    ));
                    ?>
                </span>
            </div>
        </div>
    <?php endif; ?>
</div>

<!-- 查看详情弹窗 -->
<div id="quote-detail-modal" class="sysafari-modal" style="display: none;">
    <div class="sysafari-modal-content">
        <span class="sysafari-modal-close">&times;</span>
        <h2><?php esc_html_e('报价请求详情', 'sysafari-integration'); ?></h2>
        <div id="quote-detail-content"></div>
    </div>
</div>

<style>
.search-box {
    float: right;
    margin-bottom: 10px;
}

.sysafari-modal {
    position: fixed;
    z-index: 100000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
}

.sysafari-modal-content {
    background-color: #fefefe;
    margin: 5% auto;
    padding: 20px;
    border-radius: 8px;
    width: 600px;
    max-width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

.sysafari-modal-close {
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
}

.quote-detail-row {
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #eee;
}

.quote-detail-label {
    font-weight: 600;
    color: #666;
}
</style>

<script>
jQuery(document).ready(function($) {
    // 状态更新
    $('.quote-status-select').on('change', function() {
        var $select = $(this);
        var quoteId = $select.data('id');
        var newStatus = $select.val();
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_update_quote_status',
                nonce: sysafariAdmin.nonce,
                id: quoteId,
                status: newStatus
            },
            success: function(response) {
                if (response.success) {
                    // 显示成功提示
                } else {
                    alert(response.data.message);
                    location.reload();
                }
            }
        });
    });
    
    // 查看详情
    $('.view-quote-btn').on('click', function() {
        var quoteId = $(this).data('id');
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_get_quote_detail',
                nonce: sysafariAdmin.nonce,
                id: quoteId
            },
            success: function(response) {
                if (response.success) {
                    var quote = response.data;
                    var html = '<div class="quote-detail-row"><span class="quote-detail-label">姓名</span><span>' + quote.name + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">邮箱</span><span>' + quote.email + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">电话</span><span>' + (quote.phone || '-') + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">公司</span><span>' + (quote.company || '-') + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">起运地</span><span>' + quote.origin + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">目的地</span><span>' + quote.destination + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">服务类型</span><span>' + quote.service_type + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">货物类型</span><span>' + (quote.cargo_type || '-') + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">重量</span><span>' + quote.weight + ' KG</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">尺寸</span><span>' + (quote.dimensions || '-') + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">数量</span><span>' + quote.quantity + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">发货日期</span><span>' + (quote.ship_date || '-') + '</span></div>';
                    html += '<div class="quote-detail-row"><span class="quote-detail-label">备注</span><span>' + (quote.message || '-') + '</span></div>';
                    
                    $('#quote-detail-content').html(html);
                    $('#quote-detail-modal').show();
                }
            }
        });
    });
    
    // 关闭弹窗
    $('.sysafari-modal-close, .sysafari-modal').on('click', function(e) {
        if (e.target === this) {
            $('#quote-detail-modal').hide();
        }
    });
    
    // 删除
    $('.delete-quote-btn').on('click', function() {
        if (!confirm('确定要删除这条记录吗？')) {
            return;
        }
        
        var quoteId = $(this).data('id');
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_delete_quote',
                nonce: sysafariAdmin.nonce,
                id: quoteId
            },
            success: function(response) {
                if (response.success) {
                    location.reload();
                } else {
                    alert(response.data.message);
                }
            }
        });
    });
});
</script>
