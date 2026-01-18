<?php
/**
 * 首页模板
 * 
 * DHL风格的物流公司首页，包含追踪表单、服务卡片、特色介绍等
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<!-- Hero Section - 追踪货件 -->
<section class="hero-section">
    <div class="hero-content">
        <div class="container">
            <h1 class="hero-title"><?php esc_html_e('追踪货件', 'sysafari-logistics'); ?></h1>
            
            <!-- 追踪表单 -->
            <form class="tracking-form" id="hero-tracking-form" action="<?php echo esc_url(home_url('/tracking')); ?>" method="get">
                <input type="text" name="tracking_number" placeholder="<?php esc_attr_e('输入您的追踪码', 'sysafari-logistics'); ?>" autocomplete="off">
                <button type="submit"><?php esc_html_e('追踪', 'sysafari-logistics'); ?></button>
            </form>
        </div>
    </div>
</section>

<!-- Service Cards - 服务卡片 -->
<section class="section service-section">
    <div class="container">
        <div class="service-cards">
            <!-- 立即寄件 -->
            <div class="service-card">
                <div class="service-card-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4zM6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9l1.96 2.5H17V9.5h2.5zm-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
                    </svg>
                </div>
                <h3 class="service-card-title"><?php esc_html_e('立即寄件', 'sysafari-logistics'); ?></h3>
                <p class="service-card-desc"><?php esc_html_e('寻找符合需求的服务', 'sysafari-logistics'); ?></p>
                <a href="<?php echo esc_url(home_url('/services')); ?>" class="btn btn-outline mt-2">
                    <?php esc_html_e('了解更多', 'sysafari-logistics'); ?>
                </a>
            </div>

            <!-- 取得报价 -->
            <div class="service-card">
                <div class="service-card-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19.5 3.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5zM19 19.09H5V4.91h14v14.18zM6 15h12v2H6zm0-4h12v2H6zm0-4h12v2H6z"/>
                    </svg>
                </div>
                <h3 class="service-card-title"><?php esc_html_e('取得报价', 'sysafari-logistics'); ?></h3>
                <p class="service-card-desc"><?php esc_html_e('估价、分享和比较', 'sysafari-logistics'); ?></p>
                <a href="<?php echo esc_url(home_url('/quote')); ?>" class="btn btn-outline mt-2">
                    <?php esc_html_e('立即报价', 'sysafari-logistics'); ?>
                </a>
            </div>

            <!-- 开立企业帐号 -->
            <div class="service-card highlighted">
                <div class="service-card-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z"/>
                    </svg>
                </div>
                <h3 class="service-card-title"><?php esc_html_e('开立企业帐号', 'sysafari-logistics'); ?></h3>
                <p class="service-card-desc"><?php esc_html_e('您有定期寄件需求吗？立即申请企业帐号，享受最低寄件优惠与最优质服务', 'sysafari-logistics'); ?></p>
                <a href="<?php echo esc_url(home_url('/register')); ?>" class="btn btn-secondary mt-2">
                    <?php esc_html_e('立即开户', 'sysafari-logistics'); ?>
                </a>
            </div>
        </div>
    </div>
</section>

<!-- Latest News Section - 最新资讯 -->
<section class="section news-section" style="background: var(--color-light);">
    <div class="container">
        <div class="section-title">
            <h2><?php esc_html_e('掌握最新关税发展趋势', 'sysafari-logistics'); ?></h2>
            <p><?php esc_html_e('随着美国发表新关税政策，以及各国各产业陆续出不同的对等政策，让全球贸易变化趋于复杂。我们致力于协助您应对这些变化，在不同局势中持续前进。', 'sysafari-logistics'); ?></p>
        </div>
        
        <div class="news-grid">
            <?php
            $news_query = new WP_Query(array(
                'post_type'      => 'post',
                'posts_per_page' => 3,
                'orderby'        => 'date',
                'order'          => 'DESC',
            ));
            
            if ($news_query->have_posts()) :
                while ($news_query->have_posts()) : $news_query->the_post();
            ?>
                <article class="news-card">
                    <?php if (has_post_thumbnail()) : ?>
                        <div class="news-card-image">
                            <a href="<?php the_permalink(); ?>">
                                <?php the_post_thumbnail('news-thumbnail'); ?>
                            </a>
                        </div>
                    <?php endif; ?>
                    <div class="news-card-content">
                        <span class="news-card-date"><?php echo get_the_date(); ?></span>
                        <h3 class="news-card-title">
                            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                        </h3>
                        <p class="news-card-excerpt"><?php echo wp_trim_words(get_the_excerpt(), 20); ?></p>
                    </div>
                </article>
            <?php
                endwhile;
                wp_reset_postdata();
            else :
                // 如果没有文章，显示默认内容
            ?>
                <article class="news-card">
                    <div class="news-card-image" style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%); aspect-ratio: 16/9;">
                    </div>
                    <div class="news-card-content">
                        <span class="news-card-date"><?php echo date('Y-m-d'); ?></span>
                        <h3 class="news-card-title">
                            <a href="#"><?php esc_html_e('全球物流动态实时更新', 'sysafari-logistics'); ?></a>
                        </h3>
                        <p class="news-card-excerpt"><?php esc_html_e('关注最新的国际物流政策变化和市场动态，助力您的跨境业务发展。', 'sysafari-logistics'); ?></p>
                    </div>
                </article>
                <article class="news-card">
                    <div class="news-card-image" style="background: linear-gradient(135deg, var(--color-secondary) 0%, var(--color-secondary-hover) 100%); aspect-ratio: 16/9;">
                    </div>
                    <div class="news-card-content">
                        <span class="news-card-date"><?php echo date('Y-m-d'); ?></span>
                        <h3 class="news-card-title">
                            <a href="#"><?php esc_html_e('优化您的供应链管理', 'sysafari-logistics'); ?></a>
                        </h3>
                        <p class="news-card-excerpt"><?php esc_html_e('专业的物流解决方案，帮助企业降低成本、提高效率。', 'sysafari-logistics'); ?></p>
                    </div>
                </article>
                <article class="news-card">
                    <div class="news-card-image" style="background: linear-gradient(135deg, #333 0%, #555 100%); aspect-ratio: 16/9;">
                    </div>
                    <div class="news-card-content">
                        <span class="news-card-date"><?php echo date('Y-m-d'); ?></span>
                        <h3 class="news-card-title">
                            <a href="#"><?php esc_html_e('跨境电商物流新趋势', 'sysafari-logistics'); ?></a>
                        </h3>
                        <p class="news-card-excerpt"><?php esc_html_e('把握跨境电商发展机遇，提供一站式物流服务支持。', 'sysafari-logistics'); ?></p>
                    </div>
                </article>
            <?php endif; ?>
        </div>
        
        <div class="text-center mt-4">
            <a href="<?php echo esc_url(home_url('/news')); ?>" class="btn btn-outline">
                <?php esc_html_e('查看更多资讯', 'sysafari-logistics'); ?>
                <i class="fas fa-arrow-right" style="margin-left: 8px;"></i>
            </a>
        </div>
    </div>
</section>

<!-- Features Section - 特色服务 -->
<section class="section features-section">
    <div class="container">
        <div class="section-title">
            <h2><?php esc_html_e('为什么选择我们', 'sysafari-logistics'); ?></h2>
            <p><?php esc_html_e('专业、高效、可靠的国际物流服务', 'sysafari-logistics'); ?></p>
        </div>
        
        <div class="features-grid">
            <div class="feature-item">
                <div class="feature-icon">
                    <i class="fas fa-globe-asia"></i>
                </div>
                <h3 class="feature-title"><?php esc_html_e('全球网络', 'sysafari-logistics'); ?></h3>
                <p class="feature-desc"><?php esc_html_e('覆盖全球220+国家和地区，为您提供无缝的国际物流服务', 'sysafari-logistics'); ?></p>
            </div>
            
            <div class="feature-item">
                <div class="feature-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <h3 class="feature-title"><?php esc_html_e('准时送达', 'sysafari-logistics'); ?></h3>
                <p class="feature-desc"><?php esc_html_e('严格的时效管理，确保您的货物按时送达目的地', 'sysafari-logistics'); ?></p>
            </div>
            
            <div class="feature-item">
                <div class="feature-icon">
                    <i class="fas fa-shield-alt"></i>
                </div>
                <h3 class="feature-title"><?php esc_html_e('安全保障', 'sysafari-logistics'); ?></h3>
                <p class="feature-desc"><?php esc_html_e('完善的货物保险和追踪系统，让您的货物安全无忧', 'sysafari-logistics'); ?></p>
            </div>
            
            <div class="feature-item">
                <div class="feature-icon">
                    <i class="fas fa-headset"></i>
                </div>
                <h3 class="feature-title"><?php esc_html_e('专业服务', 'sysafari-logistics'); ?></h3>
                <p class="feature-desc"><?php esc_html_e('7x24小时客服支持，专业团队随时为您解答疑问', 'sysafari-logistics'); ?></p>
            </div>
        </div>
    </div>
</section>

<!-- CTA Section - 行动号召 -->
<section class="section cta-section" style="background: linear-gradient(135deg, var(--color-secondary) 0%, var(--color-secondary-hover) 100%); color: white;">
    <div class="container text-center">
        <h2 style="color: white; margin-bottom: var(--spacing-md);"><?php esc_html_e('准备好开始了吗？', 'sysafari-logistics'); ?></h2>
        <p style="color: rgba(255,255,255,0.9); font-size: 1.125rem; margin-bottom: var(--spacing-xl);"><?php esc_html_e('立即联系我们，获取专属物流解决方案', 'sysafari-logistics'); ?></p>
        <div style="display: flex; justify-content: center; gap: var(--spacing-md); flex-wrap: wrap;">
            <a href="<?php echo esc_url(home_url('/quote')); ?>" class="btn btn-primary btn-lg">
                <?php esc_html_e('获取报价', 'sysafari-logistics'); ?>
            </a>
            <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-lg" style="background: white; color: var(--color-secondary);">
                <?php esc_html_e('联系我们', 'sysafari-logistics'); ?>
            </a>
        </div>
    </div>
</section>

<?php
get_footer();
