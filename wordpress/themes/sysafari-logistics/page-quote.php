<?php
/**
 * Template Name: 获取报价页面
 * 
 * 在线报价/询价页面
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('获取报价', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="quote-page-grid" style="display: grid; grid-template-columns: 2fr 1fr; gap: var(--spacing-xl);">
            
            <!-- 报价表单 -->
            <div class="quote-form-wrapper">
                <div class="quote-form">
                    <h2 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('填写货物信息获取报价', 'sysafari-logistics'); ?></h2>
                    
                    <form id="quote-form" method="post">
                        <?php wp_nonce_field('sysafari_quote', 'quote_nonce'); ?>
                        
                        <!-- 联系信息 -->
                        <h3 style="margin-bottom: var(--spacing-md); padding-bottom: var(--spacing-sm); border-bottom: 2px solid var(--color-primary);">
                            <?php esc_html_e('联系信息', 'sysafari-logistics'); ?>
                        </h3>
                        
                        <div class="quote-form-grid">
                            <div class="form-group">
                                <label class="form-label" for="name"><?php esc_html_e('姓名', 'sysafari-logistics'); ?> *</label>
                                <input type="text" id="name" name="name" class="form-control" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="company"><?php esc_html_e('公司名称', 'sysafari-logistics'); ?></label>
                                <input type="text" id="company" name="company" class="form-control">
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="email"><?php esc_html_e('电子邮箱', 'sysafari-logistics'); ?> *</label>
                                <input type="email" id="email" name="email" class="form-control" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="phone"><?php esc_html_e('联系电话', 'sysafari-logistics'); ?> *</label>
                                <input type="tel" id="phone" name="phone" class="form-control" required>
                            </div>
                        </div>
                        
                        <!-- 运输信息 -->
                        <h3 style="margin: var(--spacing-xl) 0 var(--spacing-md); padding-bottom: var(--spacing-sm); border-bottom: 2px solid var(--color-primary);">
                            <?php esc_html_e('运输信息', 'sysafari-logistics'); ?>
                        </h3>
                        
                        <div class="quote-form-grid">
                            <div class="form-group">
                                <label class="form-label" for="origin"><?php esc_html_e('起运地', 'sysafari-logistics'); ?> *</label>
                                <input type="text" id="origin" name="origin" class="form-control" placeholder="<?php esc_attr_e('城市/国家', 'sysafari-logistics'); ?>" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="destination"><?php esc_html_e('目的地', 'sysafari-logistics'); ?> *</label>
                                <input type="text" id="destination" name="destination" class="form-control" placeholder="<?php esc_attr_e('城市/国家', 'sysafari-logistics'); ?>" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="service_type"><?php esc_html_e('服务类型', 'sysafari-logistics'); ?> *</label>
                                <select id="service_type" name="service_type" class="form-control" required>
                                    <option value=""><?php esc_html_e('请选择服务类型', 'sysafari-logistics'); ?></option>
                                    <option value="sea_freight"><?php esc_html_e('海运服务', 'sysafari-logistics'); ?></option>
                                    <option value="air_freight"><?php esc_html_e('空运服务', 'sysafari-logistics'); ?></option>
                                    <option value="land_transport"><?php esc_html_e('陆运服务', 'sysafari-logistics'); ?></option>
                                    <option value="express"><?php esc_html_e('国际快递', 'sysafari-logistics'); ?></option>
                                    <option value="multimodal"><?php esc_html_e('多式联运', 'sysafari-logistics'); ?></option>
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="cargo_type"><?php esc_html_e('货物类型', 'sysafari-logistics'); ?> *</label>
                                <select id="cargo_type" name="cargo_type" class="form-control" required>
                                    <option value=""><?php esc_html_e('请选择货物类型', 'sysafari-logistics'); ?></option>
                                    <option value="general"><?php esc_html_e('普通货物', 'sysafari-logistics'); ?></option>
                                    <option value="dangerous"><?php esc_html_e('危险品', 'sysafari-logistics'); ?></option>
                                    <option value="temperature"><?php esc_html_e('温控货物', 'sysafari-logistics'); ?></option>
                                    <option value="oversized"><?php esc_html_e('超大件', 'sysafari-logistics'); ?></option>
                                    <option value="fragile"><?php esc_html_e('易碎品', 'sysafari-logistics'); ?></option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- 货物规格 -->
                        <h3 style="margin: var(--spacing-xl) 0 var(--spacing-md); padding-bottom: var(--spacing-sm); border-bottom: 2px solid var(--color-primary);">
                            <?php esc_html_e('货物规格', 'sysafari-logistics'); ?>
                        </h3>
                        
                        <div class="quote-form-grid">
                            <div class="form-group">
                                <label class="form-label" for="weight"><?php esc_html_e('重量 (KG)', 'sysafari-logistics'); ?></label>
                                <input type="number" id="weight" name="weight" class="form-control" step="0.01" min="0">
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="dimensions"><?php esc_html_e('尺寸 (长x宽x高 CM)', 'sysafari-logistics'); ?></label>
                                <input type="text" id="dimensions" name="dimensions" class="form-control" placeholder="<?php esc_attr_e('例如: 100x50x50', 'sysafari-logistics'); ?>">
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="quantity"><?php esc_html_e('数量/件数', 'sysafari-logistics'); ?></label>
                                <input type="number" id="quantity" name="quantity" class="form-control" min="1" value="1">
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="ship_date"><?php esc_html_e('预计发货日期', 'sysafari-logistics'); ?></label>
                                <input type="date" id="ship_date" name="ship_date" class="form-control">
                            </div>
                        </div>
                        
                        <!-- 附加说明 -->
                        <div class="form-group" style="margin-top: var(--spacing-lg);">
                            <label class="form-label" for="message"><?php esc_html_e('附加说明', 'sysafari-logistics'); ?></label>
                            <textarea id="message" name="message" class="form-control" rows="4" placeholder="<?php esc_attr_e('请描述您的特殊需求或其他说明...', 'sysafari-logistics'); ?>"></textarea>
                        </div>
                        
                        <!-- 提交按钮 -->
                        <div style="margin-top: var(--spacing-xl);">
                            <button type="submit" class="btn btn-secondary btn-lg" style="width: 100%;">
                                <span class="btn-text"><?php esc_html_e('提交报价请求', 'sysafari-logistics'); ?></span>
                                <span class="btn-loading hidden"><span class="loading"></span> <?php esc_html_e('提交中...', 'sysafari-logistics'); ?></span>
                            </button>
                        </div>
                        
                        <p style="text-align: center; margin-top: var(--spacing-md); color: var(--color-gray-dark); font-size: 0.875rem;">
                            <?php esc_html_e('我们将在1个工作日内回复您的报价请求', 'sysafari-logistics'); ?>
                        </p>
                    </form>
                    
                    <!-- 成功/错误消息 -->
                    <div id="quote-message" class="hidden" style="margin-top: var(--spacing-lg);"></div>
                </div>
            </div>
            
            <!-- 侧边栏 -->
            <div class="quote-sidebar">
                <!-- 联系信息 -->
                <div class="sidebar-widget" style="background: var(--color-light); padding: var(--spacing-xl); border-radius: var(--radius-lg); margin-bottom: var(--spacing-lg);">
                    <h3 style="margin-bottom: var(--spacing-md);"><?php esc_html_e('需要帮助？', 'sysafari-logistics'); ?></h3>
                    <p style="color: var(--color-gray-dark); margin-bottom: var(--spacing-lg);">
                        <?php esc_html_e('我们的专业顾问随时为您服务', 'sysafari-logistics'); ?>
                    </p>
                    
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-md);">
                        <a href="tel:<?php echo esc_attr(preg_replace('/[^0-9+]/', '', sysafari_get_option('company_phone', '+86 400-XXX-XXXX'))); ?>" style="display: flex; align-items: center; gap: var(--spacing-sm); color: var(--color-dark);">
                            <i class="fas fa-phone-alt" style="color: var(--color-secondary);"></i>
                            <?php echo esc_html(sysafari_get_option('company_phone', '+86 400-XXX-XXXX')); ?>
                        </a>
                        
                        <a href="mailto:<?php echo esc_attr(sysafari_get_option('company_email', 'info@sysafari.com')); ?>" style="display: flex; align-items: center; gap: var(--spacing-sm); color: var(--color-dark);">
                            <i class="fas fa-envelope" style="color: var(--color-secondary);"></i>
                            <?php echo esc_html(sysafari_get_option('company_email', 'info@sysafari.com')); ?>
                        </a>
                    </div>
                </div>
                
                <!-- 服务优势 -->
                <div class="sidebar-widget" style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%); padding: var(--spacing-xl); border-radius: var(--radius-lg);">
                    <h3 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('我们的优势', 'sysafari-logistics'); ?></h3>
                    
                    <ul style="list-style: none; padding: 0;">
                        <li style="display: flex; align-items: flex-start; gap: var(--spacing-sm); margin-bottom: var(--spacing-md);">
                            <i class="fas fa-check-circle" style="color: var(--color-success); margin-top: 4px;"></i>
                            <span><?php esc_html_e('全球220+国家网络覆盖', 'sysafari-logistics'); ?></span>
                        </li>
                        <li style="display: flex; align-items: flex-start; gap: var(--spacing-sm); margin-bottom: var(--spacing-md);">
                            <i class="fas fa-check-circle" style="color: var(--color-success); margin-top: 4px;"></i>
                            <span><?php esc_html_e('透明的价格体系', 'sysafari-logistics'); ?></span>
                        </li>
                        <li style="display: flex; align-items: flex-start; gap: var(--spacing-sm); margin-bottom: var(--spacing-md);">
                            <i class="fas fa-check-circle" style="color: var(--color-success); margin-top: 4px;"></i>
                            <span><?php esc_html_e('专业的物流解决方案', 'sysafari-logistics'); ?></span>
                        </li>
                        <li style="display: flex; align-items: flex-start; gap: var(--spacing-sm);">
                            <i class="fas fa-check-circle" style="color: var(--color-success); margin-top: 4px;"></i>
                            <span><?php esc_html_e('7x24小时客户支持', 'sysafari-logistics'); ?></span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</section>

<style>
@media (max-width: 768px) {
    .quote-page-grid {
        grid-template-columns: 1fr !important;
    }
    
    .quote-sidebar {
        order: -1;
    }
}
</style>

<?php
get_footer();
