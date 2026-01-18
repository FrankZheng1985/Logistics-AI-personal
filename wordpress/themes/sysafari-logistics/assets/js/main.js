/**
 * Sysafari Logistics 主JavaScript文件
 * 
 * @package Sysafari_Logistics
 */

(function($) {
    'use strict';

    // 全局配置
    const config = window.sysafariData || {
        ajaxUrl: '/wp-admin/admin-ajax.php',
        nonce: '',
        siteUrl: '',
        themeUrl: '',
        i18n: {
            loading: '加载中...',
            error: '发生错误，请重试',
            success: '操作成功',
            trackingEmpty: '请输入追踪号码'
        }
    };

    /**
     * 初始化
     */
    $(document).ready(function() {
        initMobileMenu();
        initTracking();
        initQuoteForm();
        initContactForm();
        initSmoothScroll();
        initAnimations();
    });

    /**
     * 移动端菜单
     */
    function initMobileMenu() {
        const $toggle = $('.mobile-menu-toggle');
        const $mobileNav = $('#mobile-navigation');
        const $body = $('body');

        $toggle.on('click', function() {
            const isExpanded = $(this).attr('aria-expanded') === 'true';
            $(this).attr('aria-expanded', !isExpanded);
            $mobileNav.toggleClass('active');
            $body.toggleClass('mobile-nav-open');
        });

        // 点击菜单项关闭菜单
        $mobileNav.find('a').on('click', function() {
            $toggle.attr('aria-expanded', 'false');
            $mobileNav.removeClass('active');
            $body.removeClass('mobile-nav-open');
        });

        // 点击外部关闭菜单
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.site-header').length) {
                $toggle.attr('aria-expanded', 'false');
                $mobileNav.removeClass('active');
                $body.removeClass('mobile-nav-open');
            }
        });
    }

    /**
     * 货物追踪功能
     */
    function initTracking() {
        // 首页追踪表单
        $('#hero-tracking-form').on('submit', function(e) {
            e.preventDefault();
            const trackingNumber = $(this).find('input[name="tracking_number"]').val().trim();
            if (trackingNumber) {
                window.location.href = config.siteUrl + '/tracking?tracking_number=' + encodeURIComponent(trackingNumber);
            }
        });

        // 追踪页面表单
        $('#tracking-page-form').on('submit', function(e) {
            e.preventDefault();
            const trackingNumber = $('#tracking-input').val().trim();
            
            if (!trackingNumber) {
                showNotification(config.i18n.trackingEmpty, 'warning');
                return;
            }

            doTracking(trackingNumber);
        });

        // 如果URL中有追踪号，自动查询
        const urlParams = new URLSearchParams(window.location.search);
        const trackingFromUrl = urlParams.get('tracking_number');
        if (trackingFromUrl && $('#tracking-page-form').length) {
            $('#tracking-input').val(trackingFromUrl);
            doTracking(trackingFromUrl);
        }
    }

    /**
     * 执行追踪查询
     */
    function doTracking(trackingNumber) {
        const $results = $('#tracking-results');
        const $submitBtn = $('#tracking-submit');
        
        // 显示加载状态
        $submitBtn.find('.btn-text').addClass('hidden');
        $submitBtn.find('.btn-loading').removeClass('hidden');
        $submitBtn.prop('disabled', true);
        
        $results.removeClass('hidden').html(`
            <div class="tracking-loading" style="text-align: center; padding: 40px;">
                <span class="loading" style="width: 40px; height: 40px;"></span>
                <p style="margin-top: 16px;">${config.i18n.loading}</p>
            </div>
        `);

        // AJAX请求
        $.ajax({
            url: config.ajaxUrl,
            type: 'POST',
            data: {
                action: 'sysafari_tracking',
                nonce: config.nonce,
                tracking_number: trackingNumber
            },
            success: function(response) {
                if (response.success) {
                    renderTrackingResults(response.data, trackingNumber);
                } else {
                    renderTrackingError(response.data.message || config.i18n.error, trackingNumber);
                }
            },
            error: function() {
                renderTrackingError(config.i18n.error, trackingNumber);
            },
            complete: function() {
                // 恢复按钮状态
                $submitBtn.find('.btn-text').removeClass('hidden');
                $submitBtn.find('.btn-loading').addClass('hidden');
                $submitBtn.prop('disabled', false);
            }
        });
    }

    /**
     * 渲染追踪结果
     */
    function renderTrackingResults(data, trackingNumber) {
        const $results = $('#tracking-results');
        
        let statusClass = 'pending';
        let statusText = '处理中';
        
        if (data.status === 'delivered') {
            statusClass = 'delivered';
            statusText = '已签收';
        } else if (data.status === 'in_transit') {
            statusClass = 'in-transit';
            statusText = '运输中';
        }

        let html = `
            <div class="tracking-result-item">
                <div class="tracking-result-header">
                    <span class="tracking-number-display">${escapeHtml(trackingNumber)}</span>
                    <span class="tracking-status-badge ${statusClass}">${statusText}</span>
                </div>
        `;

        // 追踪时间线
        if (data.timeline && data.timeline.length > 0) {
            html += '<div class="tracking-timeline">';
            data.timeline.forEach((item, index) => {
                const isFirst = index === 0;
                const itemClass = isFirst ? 'current' : 'active';
                html += `
                    <div class="tracking-item ${itemClass}">
                        <div class="tracking-time">${escapeHtml(item.time)}</div>
                        <div class="tracking-status">${escapeHtml(item.status)}</div>
                        <div class="tracking-location">${escapeHtml(item.location)}</div>
                    </div>
                `;
            });
            html += '</div>';
        } else {
            html += `
                <div style="padding: 20px; text-align: center; color: var(--color-gray-dark);">
                    <p>暂无详细物流信息，请稍后查询</p>
                </div>
            `;
        }

        html += '</div>';
        $results.html(html);
    }

    /**
     * 渲染追踪错误
     */
    function renderTrackingError(message, trackingNumber) {
        const $results = $('#tracking-results');
        $results.html(`
            <div class="tracking-error">
                <i class="fas fa-exclamation-circle" style="font-size: 2rem; margin-bottom: 16px;"></i>
                <h3>追踪号 ${escapeHtml(trackingNumber)} 查询失败</h3>
                <p>${escapeHtml(message)}</p>
            </div>
        `);
    }

    /**
     * 报价表单
     */
    function initQuoteForm() {
        $('#quote-form').on('submit', function(e) {
            e.preventDefault();
            
            const $form = $(this);
            const $submitBtn = $form.find('button[type="submit"]');
            const $message = $('#quote-message');
            
            // 显示加载状态
            $submitBtn.find('.btn-text').addClass('hidden');
            $submitBtn.find('.btn-loading').removeClass('hidden');
            $submitBtn.prop('disabled', true);
            
            // 收集表单数据
            const formData = {
                action: 'sysafari_quote_request',
                nonce: config.nonce,
                name: $form.find('#name').val(),
                email: $form.find('#email').val(),
                phone: $form.find('#phone').val(),
                company: $form.find('#company').val(),
                origin: $form.find('#origin').val(),
                destination: $form.find('#destination').val(),
                service_type: $form.find('#service_type').val(),
                cargo_type: $form.find('#cargo_type').val(),
                weight: $form.find('#weight').val(),
                dimensions: $form.find('#dimensions').val(),
                quantity: $form.find('#quantity').val(),
                ship_date: $form.find('#ship_date').val(),
                message: $form.find('#message').val()
            };

            $.ajax({
                url: config.ajaxUrl,
                type: 'POST',
                data: formData,
                success: function(response) {
                    if (response.success) {
                        $message.removeClass('hidden').html(`
                            <div style="background: #D4EDDA; border: 1px solid #C3E6CB; color: #155724; padding: 16px; border-radius: 8px;">
                                <i class="fas fa-check-circle" style="margin-right: 8px;"></i>
                                ${escapeHtml(response.data.message)}
                            </div>
                        `);
                        $form[0].reset();
                        
                        // 滚动到消息位置
                        $('html, body').animate({
                            scrollTop: $message.offset().top - 100
                        }, 500);
                    } else {
                        $message.removeClass('hidden').html(`
                            <div style="background: #F8D7DA; border: 1px solid #F5C6CB; color: #721C24; padding: 16px; border-radius: 8px;">
                                <i class="fas fa-exclamation-circle" style="margin-right: 8px;"></i>
                                ${escapeHtml(response.data.message || config.i18n.error)}
                            </div>
                        `);
                    }
                },
                error: function() {
                    $message.removeClass('hidden').html(`
                        <div style="background: #F8D7DA; border: 1px solid #F5C6CB; color: #721C24; padding: 16px; border-radius: 8px;">
                            <i class="fas fa-exclamation-circle" style="margin-right: 8px;"></i>
                            ${config.i18n.error}
                        </div>
                    `);
                },
                complete: function() {
                    $submitBtn.find('.btn-text').removeClass('hidden');
                    $submitBtn.find('.btn-loading').addClass('hidden');
                    $submitBtn.prop('disabled', false);
                }
            });
        });
    }

    /**
     * 联系表单
     */
    function initContactForm() {
        $('#contact-form').on('submit', function(e) {
            e.preventDefault();
            
            const $form = $(this);
            const $submitBtn = $form.find('button[type="submit"]');
            const $message = $('#contact-message-result');
            
            // 显示加载状态
            $submitBtn.find('.btn-text').addClass('hidden');
            $submitBtn.find('.btn-loading').removeClass('hidden');
            $submitBtn.prop('disabled', true);
            
            // 收集表单数据
            const formData = {
                action: 'sysafari_contact',
                nonce: config.nonce,
                name: $form.find('#contact-name').val(),
                email: $form.find('#contact-email').val(),
                phone: $form.find('#contact-phone').val(),
                subject: $form.find('#contact-subject').val(),
                message: $form.find('#contact-message').val()
            };

            $.ajax({
                url: config.ajaxUrl,
                type: 'POST',
                data: formData,
                success: function(response) {
                    if (response.success) {
                        $message.removeClass('hidden').html(`
                            <div style="background: #D4EDDA; border: 1px solid #C3E6CB; color: #155724; padding: 16px; border-radius: 8px;">
                                <i class="fas fa-check-circle" style="margin-right: 8px;"></i>
                                留言已发送成功，我们会尽快回复您！
                            </div>
                        `);
                        $form[0].reset();
                    } else {
                        $message.removeClass('hidden').html(`
                            <div style="background: #F8D7DA; border: 1px solid #F5C6CB; color: #721C24; padding: 16px; border-radius: 8px;">
                                <i class="fas fa-exclamation-circle" style="margin-right: 8px;"></i>
                                ${escapeHtml(response.data.message || config.i18n.error)}
                            </div>
                        `);
                    }
                },
                error: function() {
                    $message.removeClass('hidden').html(`
                        <div style="background: #F8D7DA; border: 1px solid #F5C6CB; color: #721C24; padding: 16px; border-radius: 8px;">
                            <i class="fas fa-exclamation-circle" style="margin-right: 8px;"></i>
                            ${config.i18n.error}
                        </div>
                    `);
                },
                complete: function() {
                    $submitBtn.find('.btn-text').removeClass('hidden');
                    $submitBtn.find('.btn-loading').addClass('hidden');
                    $submitBtn.prop('disabled', false);
                }
            });
        });
    }

    /**
     * 平滑滚动
     */
    function initSmoothScroll() {
        $('a[href^="#"]').on('click', function(e) {
            const target = $(this.getAttribute('href'));
            if (target.length) {
                e.preventDefault();
                $('html, body').animate({
                    scrollTop: target.offset().top - 100
                }, 500);
            }
        });
    }

    /**
     * 入场动画
     */
    function initAnimations() {
        // 检测元素是否在视口中
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // 观察需要动画的元素
        document.querySelectorAll('.service-card, .news-card, .feature-item, .service-item').forEach(el => {
            el.classList.add('animate-ready');
            observer.observe(el);
        });
    }

    /**
     * 显示通知
     */
    function showNotification(message, type = 'info') {
        const $notification = $(`
            <div class="sysafari-notification ${type}" style="
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 16px 24px;
                background: ${type === 'success' ? '#D4EDDA' : type === 'warning' ? '#FFF3CD' : type === 'error' ? '#F8D7DA' : '#D1ECF1'};
                color: ${type === 'success' ? '#155724' : type === 'warning' ? '#856404' : type === 'error' ? '#721C24' : '#0C5460'};
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                animation: slideInRight 0.3s ease;
            ">
                ${escapeHtml(message)}
            </div>
        `);
        
        $('body').append($notification);
        
        setTimeout(() => {
            $notification.fadeOut(300, function() {
                $(this).remove();
            });
        }, 3000);
    }

    /**
     * HTML转义
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 添加CSS动画样式
     */
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .animate-ready {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }
        
        .animate-in {
            opacity: 1;
            transform: translateY(0);
        }
        
        /* 移动端导航样式 */
        .mobile-navigation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            z-index: 999;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
            padding-top: 80px;
        }
        
        .mobile-navigation.active {
            transform: translateX(0);
        }
        
        .mobile-nav-inner {
            padding: 20px;
        }
        
        .mobile-menu {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .mobile-menu li {
            border-bottom: 1px solid #eee;
        }
        
        .mobile-menu a {
            display: block;
            padding: 15px 0;
            color: #333;
            font-size: 18px;
        }
        
        .mobile-nav-footer {
            margin-top: 30px;
        }
        
        body.mobile-nav-open {
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);

})(jQuery);
