<?php
/**
 * 404错误页面模板
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<section class="section error-404" style="min-height: 60vh; display: flex; align-items: center;">
    <div class="container text-center">
        <div class="error-icon" style="margin-bottom: var(--spacing-xl);">
            <i class="fas fa-exclamation-triangle" style="font-size: 6rem; color: var(--color-primary);"></i>
        </div>
        
        <h1 style="font-size: 6rem; color: var(--color-primary); margin-bottom: var(--spacing-md);">404</h1>
        <h2 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('页面未找到', 'sysafari-logistics'); ?></h2>
        <p style="color: var(--color-gray-dark); font-size: 1.125rem; margin-bottom: var(--spacing-xl); max-width: 500px; margin-left: auto; margin-right: auto;">
            <?php esc_html_e('抱歉，您访问的页面不存在或已被移除。请检查URL是否正确，或返回首页继续浏览。', 'sysafari-logistics'); ?>
        </p>
        
        <div class="error-actions" style="display: flex; justify-content: center; gap: var(--spacing-md); flex-wrap: wrap;">
            <a href="<?php echo esc_url(home_url('/')); ?>" class="btn btn-primary btn-lg">
                <i class="fas fa-home" style="margin-right: 8px;"></i>
                <?php esc_html_e('返回首页', 'sysafari-logistics'); ?>
            </a>
            <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-outline btn-lg">
                <i class="fas fa-headset" style="margin-right: 8px;"></i>
                <?php esc_html_e('联系客服', 'sysafari-logistics'); ?>
            </a>
        </div>
        
        <div class="error-search" style="margin-top: var(--spacing-2xl); max-width: 400px; margin-left: auto; margin-right: auto;">
            <p style="margin-bottom: var(--spacing-md);"><?php esc_html_e('或者尝试搜索：', 'sysafari-logistics'); ?></p>
            <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                <div style="display: flex;">
                    <input type="search" name="s" class="form-control" placeholder="<?php esc_attr_e('输入关键词搜索...', 'sysafari-logistics'); ?>" style="border-radius: var(--radius-md) 0 0 var(--radius-md);">
                    <button type="submit" class="btn btn-secondary" style="border-radius: 0 var(--radius-md) var(--radius-md) 0;">
                        <i class="fas fa-search"></i>
                    </button>
                </div>
            </form>
        </div>
        
        <div class="error-links" style="margin-top: var(--spacing-2xl);">
            <p style="color: var(--color-gray); margin-bottom: var(--spacing-md);"><?php esc_html_e('热门页面：', 'sysafari-logistics'); ?></p>
            <div style="display: flex; justify-content: center; gap: var(--spacing-lg); flex-wrap: wrap;">
                <a href="<?php echo esc_url(home_url('/tracking')); ?>"><?php esc_html_e('货物追踪', 'sysafari-logistics'); ?></a>
                <a href="<?php echo esc_url(home_url('/services')); ?>"><?php esc_html_e('服务介绍', 'sysafari-logistics'); ?></a>
                <a href="<?php echo esc_url(home_url('/quote')); ?>"><?php esc_html_e('获取报价', 'sysafari-logistics'); ?></a>
                <a href="<?php echo esc_url(home_url('/news')); ?>"><?php esc_html_e('新闻资讯', 'sysafari-logistics'); ?></a>
            </div>
        </div>
    </div>
</section>

<?php
get_footer();
