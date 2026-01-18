<?php
/**
 * Template Name: 服务页面
 * 
 * 服务介绍展示页面
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('我们的服务', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="section-title">
            <h2><?php esc_html_e('全方位物流解决方案', 'sysafari-logistics'); ?></h2>
            <p><?php esc_html_e('为您提供海陆空全渠道的国际物流服务，满足各类货运需求', 'sysafari-logistics'); ?></p>
        </div>
        
        <!-- 服务列表 -->
        <div class="services-grid">
            
            <!-- 海运服务 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-ship"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('海运服务', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('提供整箱(FCL)和拼箱(LCL)海运服务，覆盖全球主要港口。灵活的航线选择，有竞争力的运价。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('整箱/拼箱运输', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('全球主要港口覆盖', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('门到门服务', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('特种柜运输', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/sea-freight')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
            
            <!-- 空运服务 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-plane"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('空运服务', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('快速、可靠的国际空运服务，满足您对时效的严格要求。与全球各大航空公司建立紧密合作。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('特快/标准空运', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('机场到机场/门到门', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('包机服务', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('危险品空运', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/air-freight')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
            
            <!-- 陆运服务 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-truck"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('陆运服务', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('专业的公路和铁路运输服务，覆盖中国全境及中欧班列沿线国家。安全、准时、经济。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('整车/零担运输', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('中欧铁路班列', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('跨境公路运输', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('国内配送网络', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/land-transport')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
            
            <!-- 仓储服务 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-warehouse"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('仓储服务', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('现代化仓储设施，智能化库存管理系统。提供入库、存储、分拣、包装、配送一体化服务。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('保税仓储', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('海外仓服务', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('库存管理', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('增值服务', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/warehousing')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
            
            <!-- 报关清关 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-file-alt"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('报关清关', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('专业的报关团队，熟悉各国海关政策法规。提供高效、合规的进出口报关服务。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('进出口报关', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('商检代理', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('单证服务', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('关税筹划', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/customs')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
            
            <!-- 国际快递 -->
            <div class="service-item">
                <div class="service-icon-large">
                    <i class="fas fa-box"></i>
                </div>
                <div class="service-content">
                    <h3><?php esc_html_e('国际快递', 'sysafari-logistics'); ?></h3>
                    <p><?php esc_html_e('快速安全的国际快递服务，适合小件商品和文件寄送。全程追踪，送达签收确认。', 'sysafari-logistics'); ?></p>
                    <ul class="service-features">
                        <li><i class="fas fa-check"></i> <?php esc_html_e('文件快递', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('包裹快递', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('全程追踪', 'sysafari-logistics'); ?></li>
                        <li><i class="fas fa-check"></i> <?php esc_html_e('签收确认', 'sysafari-logistics'); ?></li>
                    </ul>
                    <a href="<?php echo esc_url(home_url('/services/express')); ?>" class="btn btn-outline"><?php esc_html_e('了解详情', 'sysafari-logistics'); ?></a>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- CTA Section -->
<section class="section" style="background: var(--color-light);">
    <div class="container text-center">
        <h2><?php esc_html_e('需要定制化物流方案？', 'sysafari-logistics'); ?></h2>
        <p style="color: var(--color-gray-dark); margin-bottom: var(--spacing-xl);">
            <?php esc_html_e('我们的专业团队将根据您的具体需求，为您量身定制最优物流解决方案', 'sysafari-logistics'); ?>
        </p>
        <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-secondary btn-lg">
            <?php esc_html_e('联系我们', 'sysafari-logistics'); ?>
        </a>
    </div>
</section>

<style>
.services-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-xl);
}

.service-item {
    display: flex;
    gap: var(--spacing-xl);
    background: var(--color-white);
    padding: var(--spacing-xl);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-normal);
}

.service-item:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
}

.service-icon-large {
    width: 80px;
    height: 80px;
    min-width: 80px;
    background: var(--color-primary-light);
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
}

.service-icon-large i {
    font-size: 2rem;
    color: var(--color-secondary);
}

.service-content h3 {
    margin-bottom: var(--spacing-sm);
}

.service-content p {
    color: var(--color-gray-dark);
    margin-bottom: var(--spacing-md);
}

.service-features {
    list-style: none;
    padding: 0;
    margin-bottom: var(--spacing-lg);
}

.service-features li {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
    font-size: 0.875rem;
    color: var(--color-gray-dark);
}

.service-features i {
    color: var(--color-success);
    font-size: 0.75rem;
}

@media (max-width: 1024px) {
    .services-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 768px) {
    .service-item {
        flex-direction: column;
        text-align: center;
    }
    
    .service-icon-large {
        margin: 0 auto;
    }
    
    .service-features li {
        justify-content: center;
    }
}
</style>

<?php
get_footer();
