/**
 * Sysafari Integration Admin JavaScript
 */

(function($) {
    'use strict';

    $(document).ready(function() {
        initApiToggle();
        initApiTest();
        initQuoteActions();
        initContactActions();
        initBulkActions();
    });

    /**
     * 切换API密钥显示
     */
    function initApiToggle() {
        $('#toggle-api-key').on('click', function() {
            var $input = $('#sysafari_api_key');
            if ($input.attr('type') === 'password') {
                $input.attr('type', 'text');
                $(this).text('隐藏');
            } else {
                $input.attr('type', 'password');
                $(this).text('显示');
            }
        });
    }

    /**
     * 测试API连接
     */
    function initApiTest() {
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
                        $result.addClass('error').text('✗ ' + (response.data.message || '连接失败'));
                    }
                },
                error: function(xhr, status, error) {
                    $result.addClass('error').text('✗ 请求失败: ' + error);
                },
                complete: function() {
                    $btn.prop('disabled', false);
                }
            });
        });
    }

    /**
     * 报价请求操作
     */
    function initQuoteActions() {
        // 状态更新
        $('.quote-status-select').on('change', function() {
            var $select = $(this);
            var quoteId = $select.data('id');
            var newStatus = $select.val();
            var originalStatus = $select.data('original') || $select.find('option:first').val();
            
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
                        showNotice('状态已更新', 'success');
                        $select.data('original', newStatus);
                    } else {
                        showNotice(response.data.message || '更新失败', 'error');
                        $select.val(originalStatus);
                    }
                },
                error: function() {
                    showNotice('请求失败', 'error');
                    $select.val(originalStatus);
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
                        renderQuoteDetail(response.data);
                    } else {
                        showNotice(response.data.message || '获取详情失败', 'error');
                    }
                }
            });
        });
        
        // 删除
        $('.delete-quote-btn').on('click', function() {
            if (!confirm('确定要删除这条记录吗？此操作不可恢复。')) {
                return;
            }
            
            var $btn = $(this);
            var quoteId = $btn.data('id');
            
            $btn.prop('disabled', true);
            
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
                        $btn.closest('tr').fadeOut(300, function() {
                            $(this).remove();
                        });
                        showNotice('已删除', 'success');
                    } else {
                        showNotice(response.data.message || '删除失败', 'error');
                    }
                },
                error: function() {
                    showNotice('请求失败', 'error');
                },
                complete: function() {
                    $btn.prop('disabled', false);
                }
            });
        });
    }

    /**
     * 渲染报价详情
     */
    function renderQuoteDetail(quote) {
        var serviceTypes = {
            'sea_freight': '海运服务',
            'air_freight': '空运服务',
            'land_transport': '陆运服务',
            'express': '国际快递',
            'multimodal': '多式联运'
        };
        
        var cargoTypes = {
            'general': '普通货物',
            'dangerous': '危险品',
            'temperature': '温控货物',
            'oversized': '超大件',
            'fragile': '易碎品'
        };
        
        var html = '';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">姓名</span><span>' + escapeHtml(quote.name) + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">邮箱</span><span><a href="mailto:' + escapeHtml(quote.email) + '">' + escapeHtml(quote.email) + '</a></span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">电话</span><span>' + escapeHtml(quote.phone || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">公司</span><span>' + escapeHtml(quote.company || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">起运地</span><span><strong>' + escapeHtml(quote.origin) + '</strong></span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">目的地</span><span><strong>' + escapeHtml(quote.destination) + '</strong></span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">服务类型</span><span>' + escapeHtml(serviceTypes[quote.service_type] || quote.service_type) + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">货物类型</span><span>' + escapeHtml(cargoTypes[quote.cargo_type] || quote.cargo_type || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">重量</span><span>' + escapeHtml(quote.weight) + ' KG</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">尺寸</span><span>' + escapeHtml(quote.dimensions || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">数量</span><span>' + escapeHtml(quote.quantity) + ' 件</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">发货日期</span><span>' + escapeHtml(quote.ship_date || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">备注</span><span>' + escapeHtml(quote.message || '-') + '</span></div>';
        html += '<div class="quote-detail-row"><span class="quote-detail-label">提交时间</span><span>' + escapeHtml(quote.created_at) + '</span></div>';
        
        html += '<div style="margin-top: 20px; display: flex; gap: 10px;">';
        html += '<a href="mailto:' + escapeHtml(quote.email) + '" class="button button-primary">回复邮件</a>';
        html += '</div>';
        
        $('#quote-detail-content').html(html);
        $('#quote-detail-modal').show();
    }

    /**
     * 联系消息操作
     */
    function initContactActions() {
        // 查看详情
        $('.view-contact-btn').on('click', function() {
            var contactId = $(this).data('id');
            var $row = $(this).closest('tr');
            
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
                        renderContactDetail(response.data);
                        // 标记为已读
                        $row.removeClass('unread-row');
                        $row.find('.status-unread').removeClass('status-unread').addClass('status-read').text('已读');
                    } else {
                        showNotice(response.data.message || '获取详情失败', 'error');
                    }
                }
            });
        });
        
        // 删除
        $('.delete-contact-btn').on('click', function() {
            if (!confirm('确定要删除这条消息吗？')) {
                return;
            }
            
            var $btn = $(this);
            var contactId = $btn.data('id');
            
            $btn.prop('disabled', true);
            
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
                        $btn.closest('tr').fadeOut(300, function() {
                            $(this).remove();
                        });
                        showNotice('已删除', 'success');
                    } else {
                        showNotice(response.data.message || '删除失败', 'error');
                    }
                },
                error: function() {
                    showNotice('请求失败', 'error');
                },
                complete: function() {
                    $btn.prop('disabled', false);
                }
            });
        });
    }

    /**
     * 渲染联系详情
     */
    function renderContactDetail(contact) {
        var subjects = {
            'quote': '报价咨询',
            'service': '服务咨询',
            'tracking': '货物追踪',
            'complaint': '投诉建议',
            'cooperation': '商务合作',
            'other': '其他'
        };
        
        var html = '';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">发送人</div><div>' + escapeHtml(contact.name) + '</div></div>';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">邮箱</div><div><a href="mailto:' + escapeHtml(contact.email) + '">' + escapeHtml(contact.email) + '</a></div></div>';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">电话</div><div>' + escapeHtml(contact.phone || '-') + '</div></div>';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">主题</div><div>' + escapeHtml(subjects[contact.subject] || contact.subject) + '</div></div>';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">留言内容</div><div class="contact-message-content">' + escapeHtml(contact.message) + '</div></div>';
        html += '<div class="contact-detail-row"><div class="contact-detail-label">发送时间</div><div>' + escapeHtml(contact.created_at) + '</div></div>';
        
        html += '<div style="margin-top: 20px;">';
        html += '<a href="mailto:' + escapeHtml(contact.email) + '?subject=Re: ' + escapeHtml(subjects[contact.subject] || contact.subject) + '" class="button button-primary">回复邮件</a>';
        html += '</div>';
        
        $('#contact-detail-content').html(html);
        $('#contact-detail-modal').show();
    }

    /**
     * 批量操作
     */
    function initBulkActions() {
        // 全选
        $('#select-all').on('change', function() {
            var isChecked = $(this).prop('checked');
            $('input[name="quote_ids[]"], input[name="contact_ids[]"]').prop('checked', isChecked);
        });
        
        // 同步到AI系统
        $('#sync-quotes-btn').on('click', function() {
            var $btn = $(this);
            $btn.prop('disabled', true).find('.dashicons').addClass('spin');
            
            $.ajax({
                url: sysafariAdmin.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'sysafari_sync_quotes',
                    nonce: sysafariAdmin.nonce
                },
                success: function(response) {
                    if (response.success) {
                        showNotice('同步完成: ' + response.data.synced + ' 条成功, ' + response.data.failed + ' 条失败', 'success');
                    } else {
                        showNotice(response.data.message || '同步失败', 'error');
                    }
                },
                error: function() {
                    showNotice('请求失败', 'error');
                },
                complete: function() {
                    $btn.prop('disabled', false).find('.dashicons').removeClass('spin');
                }
            });
        });
    }

    /**
     * 关闭弹窗
     */
    $(document).on('click', '.sysafari-modal-close, .sysafari-modal', function(e) {
        if (e.target === this) {
            $('.sysafari-modal').hide();
        }
    });

    /**
     * ESC键关闭弹窗
     */
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') {
            $('.sysafari-modal').hide();
        }
    });

    /**
     * 显示通知
     */
    function showNotice(message, type) {
        type = type || 'info';
        
        var $notice = $('<div class="notice notice-' + type + ' is-dismissible"><p>' + escapeHtml(message) + '</p></div>');
        
        $('.wrap h1').first().after($notice);
        
        // 自动消失
        setTimeout(function() {
            $notice.fadeOut(300, function() {
                $(this).remove();
            });
        }, 5000);
    }

    /**
     * HTML转义
     */
    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * CSS动画
     */
    var style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .dashicons.spin {
            animation: spin 1s linear infinite;
        }
    `;
    document.head.appendChild(style);

})(jQuery);
