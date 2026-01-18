<?php
/**
 * Template Name: 货物追踪页面
 * 
 * 货物追踪功能页面
 *
 * @package Sysafari_Logistics
 */

get_header();

// 获取URL中的追踪号
$tracking_number = isset($_GET['tracking_number']) ? sanitize_text_field($_GET['tracking_number']) : '';
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('货物追踪', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="tracking-page-wrapper" style="max-width: 800px; margin: 0 auto;">
            
            <!-- 追踪表单 -->
            <div class="tracking-form-card" style="background: var(--color-light); padding: var(--spacing-xl); border-radius: var(--radius-lg); margin-bottom: var(--spacing-xl);">
                <h2 style="margin-bottom: var(--spacing-lg); text-align: center;"><?php esc_html_e('输入追踪码查询货物状态', 'sysafari-logistics'); ?></h2>
                
                <form class="tracking-form" id="tracking-page-form">
                    <input type="text" 
                           name="tracking_number" 
                           id="tracking-input"
                           placeholder="<?php esc_attr_e('输入您的追踪码', 'sysafari-logistics'); ?>" 
                           value="<?php echo esc_attr($tracking_number); ?>"
                           required>
                    <button type="submit" id="tracking-submit">
                        <span class="btn-text"><?php esc_html_e('追踪', 'sysafari-logistics'); ?></span>
                        <span class="btn-loading hidden"><span class="loading"></span></span>
                    </button>
                </form>
                
                <p style="text-align: center; margin-top: var(--spacing-md); color: var(--color-gray-dark); font-size: 0.875rem;">
                    <?php esc_html_e('您可以一次查询多个追踪码，用逗号分隔', 'sysafari-logistics'); ?>
                </p>
            </div>
            
            <!-- 追踪结果 -->
            <div id="tracking-results" class="tracking-results <?php echo empty($tracking_number) ? 'hidden' : ''; ?>">
                <?php if (!empty($tracking_number)) : ?>
                    <div class="tracking-loading" style="text-align: center; padding: var(--spacing-xl);">
                        <span class="loading" style="width: 40px; height: 40px;"></span>
                        <p style="margin-top: var(--spacing-md);"><?php esc_html_e('正在查询...', 'sysafari-logistics'); ?></p>
                    </div>
                <?php endif; ?>
            </div>
            
            <!-- 追踪说明 -->
            <div class="tracking-help" style="margin-top: var(--spacing-2xl);">
                <h3><?php esc_html_e('追踪帮助', 'sysafari-logistics'); ?></h3>
                
                <div class="help-accordion">
                    <div class="help-item">
                        <h4 class="help-question">
                            <i class="fas fa-question-circle"></i>
                            <?php esc_html_e('如何找到追踪码？', 'sysafari-logistics'); ?>
                        </h4>
                        <div class="help-answer">
                            <p><?php esc_html_e('追踪码通常在您的发货确认邮件或快递单据上。它是一串由数字和字母组成的唯一编码。', 'sysafari-logistics'); ?></p>
                        </div>
                    </div>
                    
                    <div class="help-item">
                        <h4 class="help-question">
                            <i class="fas fa-question-circle"></i>
                            <?php esc_html_e('追踪信息多久更新一次？', 'sysafari-logistics'); ?>
                        </h4>
                        <div class="help-answer">
                            <p><?php esc_html_e('追踪信息通常会在货物到达每个中转站时更新。国际运输可能会有延迟，请耐心等待。', 'sysafari-logistics'); ?></p>
                        </div>
                    </div>
                    
                    <div class="help-item">
                        <h4 class="help-question">
                            <i class="fas fa-question-circle"></i>
                            <?php esc_html_e('追踪显示"未找到"怎么办？', 'sysafari-logistics'); ?>
                        </h4>
                        <div class="help-answer">
                            <p><?php esc_html_e('如果追踪显示未找到，可能是货物刚刚发出，系统尚未更新。请在24-48小时后重试，或联系客服获取帮助。', 'sysafari-logistics'); ?></p>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: var(--spacing-xl); text-align: center;">
                    <p><?php esc_html_e('需要更多帮助？', 'sysafari-logistics'); ?></p>
                    <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-outline">
                        <?php esc_html_e('联系客服', 'sysafari-logistics'); ?>
                    </a>
                </div>
            </div>
        </div>
    </div>
</section>

<style>
.help-item {
    border: 1px solid var(--color-gray-light);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
}

.help-question {
    padding: var(--spacing-md);
    margin: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 1rem;
}

.help-question i {
    color: var(--color-primary);
}

.help-answer {
    padding: 0 var(--spacing-md) var(--spacing-md);
    color: var(--color-gray-dark);
}

.tracking-result-item {
    background: var(--color-white);
    border: 1px solid var(--color-gray-light);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    margin-bottom: var(--spacing-lg);
}

.tracking-result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--color-gray-light);
    margin-bottom: var(--spacing-lg);
}

.tracking-number-display {
    font-size: 1.25rem;
    font-weight: 600;
}

.tracking-status-badge {
    padding: var(--spacing-xs) var(--spacing-md);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    font-weight: 500;
}

.tracking-status-badge.in-transit {
    background: var(--color-info);
    color: white;
}

.tracking-status-badge.delivered {
    background: var(--color-success);
    color: white;
}

.tracking-status-badge.pending {
    background: var(--color-warning);
    color: var(--color-dark);
}

.tracking-error {
    background: #FEE;
    border: 1px solid var(--color-danger);
    color: var(--color-danger);
    padding: var(--spacing-lg);
    border-radius: var(--radius-md);
    text-align: center;
}
</style>

<?php
get_footer();
