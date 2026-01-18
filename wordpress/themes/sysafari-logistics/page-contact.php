<?php
/**
 * Template Name: 联系我们页面
 * 
 * 联系表单和联系信息页面
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('联系我们', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="contact-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-2xl);">
            
            <!-- 联系表单 -->
            <div class="contact-form-wrapper">
                <h2 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('给我们留言', 'sysafari-logistics'); ?></h2>
                <p style="color: var(--color-gray-dark); margin-bottom: var(--spacing-xl);">
                    <?php esc_html_e('请填写以下表单，我们会尽快回复您的咨询', 'sysafari-logistics'); ?>
                </p>
                
                <form id="contact-form" class="contact-form">
                    <?php wp_nonce_field('sysafari_contact', 'contact_nonce'); ?>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md);">
                        <div class="form-group">
                            <label class="form-label" for="contact-name"><?php esc_html_e('您的姓名', 'sysafari-logistics'); ?> *</label>
                            <input type="text" id="contact-name" name="name" class="form-control" required>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="contact-email"><?php esc_html_e('电子邮箱', 'sysafari-logistics'); ?> *</label>
                            <input type="email" id="contact-email" name="email" class="form-control" required>
                        </div>
                    </div>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md);">
                        <div class="form-group">
                            <label class="form-label" for="contact-phone"><?php esc_html_e('联系电话', 'sysafari-logistics'); ?></label>
                            <input type="tel" id="contact-phone" name="phone" class="form-control">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label" for="contact-subject"><?php esc_html_e('咨询主题', 'sysafari-logistics'); ?> *</label>
                            <select id="contact-subject" name="subject" class="form-control" required>
                                <option value=""><?php esc_html_e('请选择咨询主题', 'sysafari-logistics'); ?></option>
                                <option value="quote"><?php esc_html_e('报价咨询', 'sysafari-logistics'); ?></option>
                                <option value="service"><?php esc_html_e('服务咨询', 'sysafari-logistics'); ?></option>
                                <option value="tracking"><?php esc_html_e('货物追踪', 'sysafari-logistics'); ?></option>
                                <option value="complaint"><?php esc_html_e('投诉建议', 'sysafari-logistics'); ?></option>
                                <option value="cooperation"><?php esc_html_e('商务合作', 'sysafari-logistics'); ?></option>
                                <option value="other"><?php esc_html_e('其他', 'sysafari-logistics'); ?></option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="contact-message"><?php esc_html_e('您的留言', 'sysafari-logistics'); ?> *</label>
                        <textarea id="contact-message" name="message" class="form-control" rows="5" required placeholder="<?php esc_attr_e('请详细描述您的需求或问题...', 'sysafari-logistics'); ?>"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <button type="submit" class="btn btn-secondary btn-lg">
                            <span class="btn-text"><?php esc_html_e('发送留言', 'sysafari-logistics'); ?></span>
                            <span class="btn-loading hidden"><span class="loading"></span></span>
                        </button>
                    </div>
                </form>
                
                <div id="contact-message-result" class="hidden" style="margin-top: var(--spacing-lg);"></div>
            </div>
            
            <!-- 联系信息 -->
            <div class="contact-info">
                <h2 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('联系方式', 'sysafari-logistics'); ?></h2>
                
                <div class="contact-info-list">
                    <!-- 地址 -->
                    <?php if ($address = sysafari_get_option('company_address')) : ?>
                    <div class="contact-info-item">
                        <div class="contact-info-icon">
                            <i class="fas fa-map-marker-alt"></i>
                        </div>
                        <div class="contact-info-content">
                            <h4><?php esc_html_e('公司地址', 'sysafari-logistics'); ?></h4>
                            <p><?php echo esc_html($address); ?></p>
                        </div>
                    </div>
                    <?php endif; ?>
                    
                    <!-- 电话 -->
                    <div class="contact-info-item">
                        <div class="contact-info-icon">
                            <i class="fas fa-phone-alt"></i>
                        </div>
                        <div class="contact-info-content">
                            <h4><?php esc_html_e('联系电话', 'sysafari-logistics'); ?></h4>
                            <p>
                                <a href="tel:<?php echo esc_attr(preg_replace('/[^0-9+]/', '', sysafari_get_option('company_phone', '+86 400-XXX-XXXX'))); ?>">
                                    <?php echo esc_html(sysafari_get_option('company_phone', '+86 400-XXX-XXXX')); ?>
                                </a>
                            </p>
                        </div>
                    </div>
                    
                    <!-- 邮箱 -->
                    <div class="contact-info-item">
                        <div class="contact-info-icon">
                            <i class="fas fa-envelope"></i>
                        </div>
                        <div class="contact-info-content">
                            <h4><?php esc_html_e('电子邮箱', 'sysafari-logistics'); ?></h4>
                            <p>
                                <a href="mailto:<?php echo esc_attr(sysafari_get_option('company_email', 'info@sysafari.com')); ?>">
                                    <?php echo esc_html(sysafari_get_option('company_email', 'info@sysafari.com')); ?>
                                </a>
                            </p>
                        </div>
                    </div>
                    
                    <!-- 工作时间 -->
                    <div class="contact-info-item">
                        <div class="contact-info-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="contact-info-content">
                            <h4><?php esc_html_e('工作时间', 'sysafari-logistics'); ?></h4>
                            <p><?php esc_html_e('周一至周五: 9:00 - 18:00', 'sysafari-logistics'); ?></p>
                            <p><?php esc_html_e('周六日: 10:00 - 16:00 (仅在线客服)', 'sysafari-logistics'); ?></p>
                        </div>
                    </div>
                </div>
                
                <!-- 地图占位 -->
                <div class="contact-map" style="margin-top: var(--spacing-xl); background: var(--color-light); border-radius: var(--radius-lg); height: 250px; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center; color: var(--color-gray);">
                        <i class="fas fa-map-marked-alt" style="font-size: 3rem; margin-bottom: var(--spacing-md);"></i>
                        <p><?php esc_html_e('地图加载中...', 'sysafari-logistics'); ?></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<style>
.contact-info-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
}

.contact-info-item {
    display: flex;
    gap: var(--spacing-md);
}

.contact-info-icon {
    width: 50px;
    height: 50px;
    min-width: 50px;
    background: var(--color-primary-light);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
}

.contact-info-icon i {
    font-size: 1.25rem;
    color: var(--color-secondary);
}

.contact-info-content h4 {
    margin-bottom: var(--spacing-xs);
    font-size: 1rem;
}

.contact-info-content p {
    color: var(--color-gray-dark);
    margin-bottom: 0;
}

.contact-info-content a {
    color: var(--color-gray-dark);
}

.contact-info-content a:hover {
    color: var(--color-secondary);
}

@media (max-width: 768px) {
    .contact-grid {
        grid-template-columns: 1fr !important;
    }
    
    .form-row {
        grid-template-columns: 1fr !important;
    }
}
</style>

<?php
get_footer();
