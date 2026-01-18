<?php
/**
 * 联系消息列表页面
 *
 * @package Sysafari_Integration
 */

if (!defined('ABSPATH')) {
    exit;
}

global $wpdb;
$table_name = $wpdb->prefix . 'sysafari_contacts';

// 分页参数
$per_page = 20;
$current_page = isset($_GET['paged']) ? max(1, intval($_GET['paged'])) : 1;
$offset = ($current_page - 1) * $per_page;

// 筛选参数
$status_filter = isset($_GET['status']) ? sanitize_text_field($_GET['status']) : '';

// 构建查询
$where = '1=1';
if (!empty($status_filter)) {
    $where .= $wpdb->prepare(' AND status = %s', $status_filter);
}

// 获取总数和数据
$total = $wpdb->get_var("SELECT COUNT(*) FROM {$table_name} WHERE {$where}");
$total_pages = ceil($total / $per_page);

$contacts = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT * FROM {$table_name} WHERE {$where} ORDER BY created_at DESC LIMIT %d OFFSET %d",
        $per_page,
        $offset
    ),
    ARRAY_A
);

// 状态统计
$unread_count = $wpdb->get_var("SELECT COUNT(*) FROM {$table_name} WHERE status = 'unread'");
$read_count = $wpdb->get_var("SELECT COUNT(*) FROM {$table_name} WHERE status = 'read'");
?>

<div class="wrap sysafari-admin">
    <h1 class="wp-heading-inline">
        <span class="dashicons dashicons-email" style="color: #FFCC00;"></span>
        <?php esc_html_e('联系消息管理', 'sysafari-integration'); ?>
    </h1>
    
    <!-- 状态过滤 -->
    <ul class="subsubsub">
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-contacts'); ?>" 
               class="<?php echo empty($status_filter) ? 'current' : ''; ?>">
                <?php esc_html_e('全部', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($total); ?>)</span>
            </a> |
        </li>
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-contacts&status=unread'); ?>"
               class="<?php echo $status_filter === 'unread' ? 'current' : ''; ?>">
                <?php esc_html_e('未读', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($unread_count); ?>)</span>
            </a> |
        </li>
        <li>
            <a href="<?php echo admin_url('admin.php?page=sysafari-contacts&status=read'); ?>"
               class="<?php echo $status_filter === 'read' ? 'current' : ''; ?>">
                <?php esc_html_e('已读', 'sysafari-integration'); ?>
                <span class="count">(<?php echo intval($read_count); ?>)</span>
            </a>
        </li>
    </ul>
    
    <!-- 表格 -->
    <table class="wp-list-table widefat fixed striped">
        <thead>
            <tr>
                <th style="width: 30px;"><input type="checkbox" id="select-all"></th>
                <th><?php esc_html_e('发送人', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('主题', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('留言内容', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('状态', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('发送时间', 'sysafari-integration'); ?></th>
                <th><?php esc_html_e('操作', 'sysafari-integration'); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php if ($contacts) : ?>
                <?php foreach ($contacts as $contact) : ?>
                    <tr class="<?php echo $contact['status'] === 'unread' ? 'unread-row' : ''; ?>">
                        <td><input type="checkbox" name="contact_ids[]" value="<?php echo esc_attr($contact['id']); ?>"></td>
                        <td>
                            <strong><?php echo esc_html($contact['name']); ?></strong>
                            <br>
                            <a href="mailto:<?php echo esc_attr($contact['email']); ?>"><?php echo esc_html($contact['email']); ?></a>
                            <?php if ($contact['phone']) : ?>
                                <br><span class="description"><?php echo esc_html($contact['phone']); ?></span>
                            <?php endif; ?>
                        </td>
                        <td>
                            <?php
                            $subjects = array(
                                'quote'       => '报价咨询',
                                'service'     => '服务咨询',
                                'tracking'    => '货物追踪',
                                'complaint'   => '投诉建议',
                                'cooperation' => '商务合作',
                                'other'       => '其他',
                            );
                            echo esc_html($subjects[$contact['subject']] ?? $contact['subject']);
                            ?>
                        </td>
                        <td>
                            <div class="message-preview">
                                <?php echo esc_html(wp_trim_words($contact['message'], 30)); ?>
                            </div>
                        </td>
                        <td>
                            <?php if ($contact['status'] === 'unread') : ?>
                                <span class="status-unread"><?php esc_html_e('未读', 'sysafari-integration'); ?></span>
                            <?php else : ?>
                                <span class="status-read"><?php esc_html_e('已读', 'sysafari-integration'); ?></span>
                            <?php endif; ?>
                        </td>
                        <td>
                            <?php echo esc_html(date_i18n('Y-m-d H:i', strtotime($contact['created_at']))); ?>
                        </td>
                        <td>
                            <button type="button" class="button button-small view-contact-btn" data-id="<?php echo esc_attr($contact['id']); ?>">
                                <?php esc_html_e('查看', 'sysafari-integration'); ?>
                            </button>
                            <a href="mailto:<?php echo esc_attr($contact['email']); ?>" class="button button-small">
                                <?php esc_html_e('回复', 'sysafari-integration'); ?>
                            </a>
                            <button type="button" class="button button-small delete-contact-btn" data-id="<?php echo esc_attr($contact['id']); ?>" style="color: #dc3232;">
                                <?php esc_html_e('删除', 'sysafari-integration'); ?>
                            </button>
                        </td>
                    </tr>
                <?php endforeach; ?>
            <?php else : ?>
                <tr>
                    <td colspan="7" style="text-align: center; padding: 30px;">
                        <?php esc_html_e('暂无联系消息', 'sysafari-integration'); ?>
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
<div id="contact-detail-modal" class="sysafari-modal" style="display: none;">
    <div class="sysafari-modal-content">
        <span class="sysafari-modal-close">&times;</span>
        <h2><?php esc_html_e('消息详情', 'sysafari-integration'); ?></h2>
        <div id="contact-detail-content"></div>
    </div>
</div>

<style>
.unread-row {
    background-color: #fff8e5 !important;
}

.unread-row td strong {
    font-weight: 700;
}

.status-unread {
    display: inline-block;
    padding: 2px 8px;
    background: #dc3232;
    color: #fff;
    border-radius: 3px;
    font-size: 11px;
}

.status-read {
    display: inline-block;
    padding: 2px 8px;
    background: #ccc;
    color: #666;
    border-radius: 3px;
    font-size: 11px;
}

.message-preview {
    max-width: 300px;
    color: #666;
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
}

.sysafari-modal-close {
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
}

.contact-detail-row {
    padding: 12px 0;
    border-bottom: 1px solid #eee;
}

.contact-detail-label {
    font-weight: 600;
    color: #666;
    margin-bottom: 5px;
}

.contact-message-content {
    white-space: pre-wrap;
    background: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    margin-top: 10px;
}
</style>

<script>
jQuery(document).ready(function($) {
    // 查看详情
    $('.view-contact-btn').on('click', function() {
        var contactId = $(this).data('id');
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_get_contact_detail',
                nonce: sysafariAdmin.nonce,
                id: contactId
            },
            success: function(response) {
                if (response.success) {
                    var contact = response.data;
                    var html = '';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">发送人</div><div>' + contact.name + '</div></div>';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">邮箱</div><div><a href="mailto:' + contact.email + '">' + contact.email + '</a></div></div>';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">电话</div><div>' + (contact.phone || '-') + '</div></div>';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">主题</div><div>' + contact.subject + '</div></div>';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">留言内容</div><div class="contact-message-content">' + contact.message + '</div></div>';
                    html += '<div class="contact-detail-row"><div class="contact-detail-label">发送时间</div><div>' + contact.created_at + '</div></div>';
                    html += '<div style="margin-top: 20px;"><a href="mailto:' + contact.email + '" class="button button-primary">回复邮件</a></div>';
                    
                    $('#contact-detail-content').html(html);
                    $('#contact-detail-modal').show();
                }
            }
        });
    });
    
    // 关闭弹窗
    $('.sysafari-modal-close, .sysafari-modal').on('click', function(e) {
        if (e.target === this) {
            $('#contact-detail-modal').hide();
        }
    });
    
    // 删除
    $('.delete-contact-btn').on('click', function() {
        if (!confirm('确定要删除这条消息吗？')) {
            return;
        }
        
        var contactId = $(this).data('id');
        
        $.ajax({
            url: sysafariAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_delete_contact',
                nonce: sysafariAdmin.nonce,
                id: contactId
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
