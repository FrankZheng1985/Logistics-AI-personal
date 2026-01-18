<?php
/**
 * 页面底部模板
 *
 * @package Sysafari_Logistics
 */

if (!defined('ABSPATH')) {
    exit;
}
?>
    </main><!-- #primary -->

    <footer class="site-footer" role="contentinfo">
        <div class="container">
            <div class="footer-grid">
                <!-- 公司简介 -->
                <div class="footer-about">
                    <div class="site-logo">
                        <?php if (has_custom_logo()) : ?>
                            <?php the_custom_logo(); ?>
                        <?php else : ?>
                            <span class="logo-text"><?php echo esc_html(sysafari_get_option('company_name', 'Sysafari Logistics')); ?></span>
                        <?php endif; ?>
                    </div>
                    <p><?php esc_html_e('专业的国际物流服务商，为您提供海运、空运、陆运、仓储等一站式物流解决方案。致力于让全球贸易更简单、更高效。', 'sysafari-logistics'); ?></p>
                    <div class="footer-social">
                        <?php if ($wechat = sysafari_get_option('social_wechat')) : ?>
                            <a href="<?php echo esc_url($wechat); ?>" target="_blank" rel="noopener" aria-label="微信">
                                <i class="fab fa-weixin"></i>
                            </a>
                        <?php endif; ?>
                        <?php if ($weibo = sysafari_get_option('social_weibo')) : ?>
                            <a href="<?php echo esc_url($weibo); ?>" target="_blank" rel="noopener" aria-label="微博">
                                <i class="fab fa-weibo"></i>
                            </a>
                        <?php endif; ?>
                        <?php if ($linkedin = sysafari_get_option('social_linkedin')) : ?>
                            <a href="<?php echo esc_url($linkedin); ?>" target="_blank" rel="noopener" aria-label="LinkedIn">
                                <i class="fab fa-linkedin-in"></i>
                            </a>
                        <?php endif; ?>
                        <?php if ($facebook = sysafari_get_option('social_facebook')) : ?>
                            <a href="<?php echo esc_url($facebook); ?>" target="_blank" rel="noopener" aria-label="Facebook">
                                <i class="fab fa-facebook-f"></i>
                            </a>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- 快速链接 -->
                <div class="footer-links-section">
                    <h4 class="footer-heading"><?php esc_html_e('快速链接', 'sysafari-logistics'); ?></h4>
                    <ul class="footer-links">
                        <li><a href="<?php echo esc_url(home_url('/tracking')); ?>"><?php esc_html_e('货物追踪', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/quote')); ?>"><?php esc_html_e('获取报价', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/services')); ?>"><?php esc_html_e('我们的服务', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/faq')); ?>"><?php esc_html_e('常见问题', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/news')); ?>"><?php esc_html_e('新闻资讯', 'sysafari-logistics'); ?></a></li>
                    </ul>
                </div>

                <!-- 服务项目 -->
                <div class="footer-services-section">
                    <h4 class="footer-heading"><?php esc_html_e('服务项目', 'sysafari-logistics'); ?></h4>
                    <ul class="footer-links">
                        <li><a href="<?php echo esc_url(home_url('/services/sea-freight')); ?>"><?php esc_html_e('海运服务', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/services/air-freight')); ?>"><?php esc_html_e('空运服务', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/services/land-transport')); ?>"><?php esc_html_e('陆运服务', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/services/warehousing')); ?>"><?php esc_html_e('仓储服务', 'sysafari-logistics'); ?></a></li>
                        <li><a href="<?php echo esc_url(home_url('/services/customs')); ?>"><?php esc_html_e('报关清关', 'sysafari-logistics'); ?></a></li>
                    </ul>
                </div>

                <!-- 联系信息 -->
                <div class="footer-contact">
                    <h4 class="footer-heading"><?php esc_html_e('联系我们', 'sysafari-logistics'); ?></h4>
                    <?php if ($address = sysafari_get_option('company_address')) : ?>
                        <p>
                            <i class="fas fa-map-marker-alt"></i>
                            <?php echo esc_html($address); ?>
                        </p>
                    <?php endif; ?>
                    <?php if ($phone = sysafari_get_option('company_phone')) : ?>
                        <p>
                            <i class="fas fa-phone-alt"></i>
                            <a href="tel:<?php echo esc_attr(preg_replace('/[^0-9+]/', '', $phone)); ?>">
                                <?php echo esc_html($phone); ?>
                            </a>
                        </p>
                    <?php endif; ?>
                    <?php if ($email = sysafari_get_option('company_email')) : ?>
                        <p>
                            <i class="fas fa-envelope"></i>
                            <a href="mailto:<?php echo esc_attr($email); ?>">
                                <?php echo esc_html($email); ?>
                            </a>
                        </p>
                    <?php endif; ?>
                    <p>
                        <i class="fas fa-clock"></i>
                        <?php esc_html_e('周一至周五 9:00 - 18:00', 'sysafari-logistics'); ?>
                    </p>
                </div>
            </div>

            <!-- 底部版权信息 -->
            <div class="footer-bottom">
                <div class="footer-copyright">
                    &copy; <?php echo date('Y'); ?> <?php echo esc_html(sysafari_get_option('company_name', 'Sysafari Logistics')); ?>. 
                    <?php esc_html_e('保留所有权利。', 'sysafari-logistics'); ?>
                    <a href="<?php echo esc_url(home_url('/privacy-policy')); ?>"><?php esc_html_e('隐私政策', 'sysafari-logistics'); ?></a>
                    |
                    <a href="<?php echo esc_url(home_url('/terms')); ?>"><?php esc_html_e('服务条款', 'sysafari-logistics'); ?></a>
                </div>
                <div class="footer-icp">
                    <!-- ICP备案号（如适用） -->
                    <?php if ($icp = sysafari_get_option('icp_number')) : ?>
                        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">
                            <?php echo esc_html($icp); ?>
                        </a>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </footer>

</div><!-- #page -->

<?php wp_footer(); ?>
</body>
</html>
